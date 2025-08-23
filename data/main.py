import uvicorn
from fastapi import FastAPI, Depends, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import text
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from langchain_google_genai import ChatGoogleGenerativeAI
import contextlib
import pandas as pd
import io
from typing import List
import json
import asyncio
import os

# --- Import from our 'backend' package ---
from .database import engine, get_db, Base
from . import models
from .rag_service import rag_service # <-- Import our new RAG service

# --- Lifespan Event to Create Database Tables ---
@contextlib.asynccontextmanager
async def lifespan(app: FastAPI):
    print("Application startup: Creating database tables if they don't exist...")
    Base.metadata.create_all(bind=engine)
    yield
    print("Application shutdown.")

# --- Initialize the FastAPI App ---
app = FastAPI(
    title="Claims AI Pipeline (Gemini Edition)",
    version="2.0.0",
    lifespan=lifespan
)

# --- CORS Middleware ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Pydantic Models ---
class ChatQuery(BaseModel):
    query: str

# --- Global Services & Constants ---
# Initialize Gemini LLM. It will automatically use the GOOGLE_API_KEY from your .env file
llm = ChatGoogleGenerativeAI(model="gemini-pro")

TABLE_SCHEMA = """
Table Name: claims
Columns: claim_id, policy_number, claim_date, claim_amount, claim_status, claim_type, settlement_amount, processing_days, diagnosis_code, provider_id
"""
FEW_SHOT_EXAMPLES = """
---
Question: "How many claims were approved?"
SQL Query: SELECT COUNT(*) FROM claims WHERE claim_status = 'Approved';
---
"""

# --- API Endpoints ---
@app.get("/")
def read_root():
    return {"status": "ok"}

@app.post("/api/upload")
async def upload_claims_data(files: List[UploadFile] = File(...), db: Session = Depends(get_db)):
    total_records_imported = 0
    all_files_df = pd.DataFrame()

    for file in files:
        try:
            contents = await file.read()
            buffer = io.StringIO(contents.decode('utf-8'))
            df = pd.read_csv(buffer)
            
            # Combine data from all files for summary
            all_files_df = pd.concat([all_files_df, df], ignore_index=True)

            # Insert data into the database
            data = df.to_dict(orient='records')
            db.bulk_insert_mappings(models.Claim, data)
            db.commit()
            total_records_imported += len(data)
        except Exception as e:
            db.rollback()
            print(f"ERROR processing file {file.filename}: {e}")
            raise HTTPException(status_code=500, detail=f"Error processing file {file.filename}.")
    
    # --- NEW RAG PIPELINE TRIGGER ---
    if not all_files_df.empty:
        print("Starting post-upload RAG pipeline...")
        # 1. Generate a text summary of the combined data
        summary_text = rag_service.generate_summary_from_dataframe(all_files_df)
        
        # 2. Create the vector store from that summary
        rag_service.create_vector_store_from_text(summary_text)

    return {"message": f"Successfully imported {total_records_imported} records and updated knowledge base."}

@app.post("/api/data/clear")
async def clear_data(db: Session = Depends(get_db)):
    deleted_rows = db.query(models.Claim).delete()
    db.commit()
    # Also clear the in-memory vector store
    rag_service.clear_vector_store()
    return {"message": f"Successfully deleted {deleted_rows} records and cleared knowledge base."}

@app.post("/api/chat")
async def chat(query: ChatQuery, db: Session = Depends(get_db)):
    user_question = query.query

    async def stream_generator():
        # --- Step 1: The Smart Router ---
        router_prompt = f"""Analyze the user's question and decide if it's better answered by a precise SQL query or by a semantic search of a text knowledge base.
        - Use 'SQL' for questions asking for specific numbers, counts, sums, averages, lists of data, or direct calculations.
        - Use 'SEMANTIC' for questions asking for general insights, patterns, reasons, "why", summaries, or qualitative analysis.

        Question: "{user_question}"
        Decision (respond with only 'SQL' or 'SEMANTIC'):"""
        
        decision = llm.invoke(router_prompt).content.strip()
        yield json.dumps({"type": "thinking", "content": f"Decision: '{decision}'. Proceeding with chosen method..."}) + "\n"
        
        context = ""
        try:
            if "SQL" in decision:
                # --- Execute the Text-to-SQL RAG flow ---
                sql_prompt = f"Schema: {TABLE_SCHEMA}\nExamples: {FEW_SHOT_EXAMPLES}\nUser Question: {user_question}\nSQL Query:"
                generated_sql = llm.invoke(sql_prompt).content.strip().replace("`", "").replace(";", "")
                yield json.dumps({"type": "sql_generated", "content": generated_sql}) + "\n"
                
                result_proxy = db.execute(text(generated_sql))
                data = [dict(row) for row in result_proxy.mappings()]
                context = json.dumps(data, default=str)
                yield json.dumps({"type": "query_result", "data": data}) + "\n"

            else: # Assumes SEMANTIC
                # --- Execute the Semantic Search RAG flow ---
                yield json.dumps({"type": "semantic_search", "content": "Searching knowledge base for insights..."}) + "\n"
                context = rag_service.query_vector_store(user_question)

            # --- Step 2: Final Generation (same for both flows) ---
            yield json.dumps({"type": "summarizing", "content": "Generating final response..."}) + "\n"
            final_prompt = f"The user asked: '{user_question}'. I have retrieved the following context to help answer the question:\n\nCONTEXT:\n{context}\n\nPlease generate a comprehensive, final answer based on the user's question and the provided context."
            
            final_summary = ""
            async for chunk in llm.astream(final_prompt):
                final_summary += chunk.content
                yield json.dumps({"type": "final_summary_chunk", "content": chunk.content}) + "\n"
            
            yield json.dumps({"type": "done", "content": final_summary}) + "\n"
        
        except Exception as e:
            print(f"ERROR in chat stream: {e}")
            yield json.dumps({"type": "error", "content": f"An error occurred: {str(e)}"}) + "\n"

    return StreamingResponse(stream_generator(), media_type="text/event-stream")