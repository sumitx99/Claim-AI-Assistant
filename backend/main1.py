from fastapi import FastAPI, Depends, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import text
from sqlalchemy.dialects.postgresql import insert as pg_insert
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from langchain_google_genai import ChatGoogleGenerativeAI
import contextlib
import pandas as pd
import io
from typing import List
import json
import asyncio

# --- Imports ---
from .database import engine, get_db, Base
from . import models
from .rag_service import rag_service


@contextlib.asynccontextmanager
async def lifespan(app: FastAPI):
    print("Startup: Creating DB tables...")
    Base.metadata.create_all(bind=engine)
    yield
    print("Application shutdown.")


app = FastAPI(title="Claims AI Pipeline", version="2.0.0", lifespan=lifespan)
origins = ["http://localhost:8080"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ChatQuery(BaseModel):
    query: str


llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash-lite")

# ✅ Expanded few-shot examples (PostgreSQL style)
TABLE_SCHEMA = "Table: claims. Columns: claim_id, policy_number, claim_date, claim_amount, claim_status, claim_type, settlement_amount, processing_days, diagnosis_code, provider_id"

FEW_SHOT_EXAMPLES = """
Question: 'How many approved claims?' -> SQL: SELECT COUNT(*) FROM claims WHERE claim_status = 'Approved';
Question: 'How many claims were submitted in 2023?' -> SQL: SELECT COUNT(*) FROM claims WHERE EXTRACT(YEAR FROM claim_date) = 2023;
Question: 'What is the average settlement amount in 2022?' -> SQL: SELECT AVG(settlement_amount) FROM claims WHERE EXTRACT(YEAR FROM claim_date) = 2022;
Question: 'Which claim type has the highest average claim_amount?' -> SQL: SELECT claim_type, AVG(claim_amount) AS avg_amt FROM claims GROUP BY claim_type ORDER BY avg_amt DESC LIMIT 1;
Question: 'What percentage of claims are pending?' -> SQL: SELECT ROUND(100.0 * COUNT(*) / (SELECT COUNT(*) FROM claims), 2) AS pending_percentage FROM claims WHERE claim_status = 'Pending';
Question: 'List all claims with settlement amount greater than 50000' -> SQL: SELECT * FROM claims WHERE settlement_amount > 50000;
Question: 'How many claims are associated with provider_id P123?' -> SQL: SELECT COUNT(*) FROM claims WHERE provider_id = 'P123';
Question: 'Give me the count of claims for each claim_status' -> SQL: SELECT claim_status, COUNT(*) FROM claims GROUP BY claim_status;
"""

@app.get("/")
def read_root():
    return {"status": "ok"}


# ------------------------
# Upload CSV into Postgres
# ------------------------
@app.post("/api/upload")
async def upload_claims_data(
    files: List[UploadFile] = File(...), db: Session = Depends(get_db)
):
    total_records_processed = 0
    all_files_df = pd.DataFrame()
    for file in files:
        try:
            contents = await file.read()
            buffer = io.StringIO(contents.decode("utf-8"))
            df = pd.read_csv(buffer)
            all_files_df = pd.concat([all_files_df, df], ignore_index=True)

            data_to_upsert = df.to_dict(orient="records")
            if not data_to_upsert:
                continue

            stmt = pg_insert(models.Claim).values(data_to_upsert)
            update_columns = {
                col.name: col for col in stmt.excluded if col.name != "claim_id"
            }
            stmt = stmt.on_conflict_do_update(
                index_elements=["claim_id"], set_=update_columns
            )

            db.execute(stmt)
            db.commit()
            total_records_processed += len(data_to_upsert)
        except Exception as e:
            db.rollback()
            print(f"ERROR: {e}")
            raise HTTPException(
                status_code=500, detail=f"Error processing file {file.filename}."
            )

    if not all_files_df.empty:
        print("Starting post-upload RAG pipeline...")
        summary_text = rag_service.generate_summary_from_dataframe(all_files_df)
        rag_service.create_vector_store_from_text(summary_text)

    return {
        "message": f"Successfully processed {total_records_processed} records. (New records inserted, existing records updated)."
    }


# ------------------------
# Clear Data
# ------------------------
@app.post("/api/data/clear")
async def clear_data(db: Session = Depends(get_db)):
    deleted_rows = db.query(models.Claim).delete()
    db.commit()
    rag_service.clear_vector_store()
    return {
        "message": f"Successfully deleted {deleted_rows} records and cleared knowledge base."
    }


# ------------------------
# Chat (ChatGPT-style)
# ------------------------
@app.post("/api/chat")
async def chat(query: ChatQuery, db: Session = Depends(get_db)):
    user_question = query.query

    async def stream_generator():
        try:
            # Step 1: Router (internal only)
            router_prompt = f"""
            Analyze the user's question: '{user_question}'.
            Decide whether it should be answered with SQL (database query) or SEMANTIC (knowledge base/RAG).
            Respond with only 'SQL' or 'SEMANTIC'.
            """
            decision = llm.invoke(router_prompt).content.strip()

            # Step 2: SQL mode
            if "SQL" in decision:
                sql_prompt = f"Schema: {TABLE_SCHEMA}\nExamples: {FEW_SHOT_EXAMPLES}\nQuestion: {user_question}\nSQL Query:"
                generated_sql = llm.invoke(sql_prompt).content.strip().replace("`", "").replace(";", "")

                result_proxy = db.execute(text(generated_sql))
                data = [dict(row) for row in result_proxy.mappings()]

                analysis_prompt = (
                    f"User asked: '{user_question}'.\n"
                    f"Here are the SQL results: {json.dumps(data, default=str)}.\n"
                    f"Answer the question naturally, like ChatGPT. "
                    f"Be clear, insightful, and conversational. "
                    f"Do not show SQL or raw rows."
                )

                final_summary = ""
                async for chunk in llm.astream(analysis_prompt):
                    final_summary += chunk.content
                    yield json.dumps(
                        {"type": "final_summary_chunk", "content": chunk.content}
                    ) + "\n"

                yield json.dumps({"type": "done", "content": final_summary}) + "\n"

            # Step 3: RAG mode
            else:
                context = rag_service.query_vector_store(user_question)
                summarizing_prompt = (
                    f"User asked: '{user_question}'.\n"
                    f"Context: '{context}'.\n"
                    f"Answer the question in a clear, conversational way like ChatGPT. "
                    f"Focus on insights, not database details."
                )

                final_summary = ""
                async for chunk in llm.astream(summarizing_prompt):
                    final_summary += chunk.content
                    yield json.dumps(
                        {"type": "final_summary_chunk", "content": chunk.content}
                    ) + "\n"

                yield json.dumps({"type": "done", "content": final_summary}) + "\n"

        except Exception as e:
            print(f"ERROR in chat stream: {e}")
            yield json.dumps(
                {"type": "error", "content": f"An error occurred: {str(e)}"}
            ) + "\n"

    return StreamingResponse(stream_generator(), media_type="text/event-stream")
