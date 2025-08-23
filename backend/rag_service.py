import pandas as pd
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
from langchain_google_genai import GoogleGenerativeAIEmbeddings, ChatGoogleGenerativeAI
import os
from dotenv import load_dotenv
from google.generativeai.types import HarmCategory, HarmBlockThreshold

# Load .env file
basedir = os.path.abspath(os.path.dirname(__file__))
dotenv_path = os.path.join(basedir, '.env')
load_dotenv(dotenv_path=dotenv_path)

class RAGService:
    def __init__(self):
        google_api_key = os.getenv("GOOGLE_API_KEY")
        if not google_api_key:
            raise ValueError("GOOGLE_API_KEY not found in .env file.")

        self.vector_store = None
        self.embeddings = GoogleGenerativeAIEmbeddings(
            model="models/embedding-001",
            google_api_key=google_api_key
        )

        self.llm = ChatGoogleGenerativeAI(
            model="gemini-2.5-flash-lite",
            google_api_key=google_api_key,
            safety_settings={
                HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
                HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
                HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
                HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
            }
        )
        print("RAG Service Initialized Successfully")

    def generate_summary_from_dataframe(self, df: pd.DataFrame) -> str:
        summary_prompt = (
            f"Analyze the following claims data and provide a high-level summary. "
            f"Focus on number of claims, distribution of types and statuses, and patterns in amounts.\n\n"
            f"Data sample:\n{df.head().to_string()}"
        )
        print("Generating data summary with Gemini...")
        summary = self.llm.invoke(summary_prompt)
        return summary.content

    def create_vector_store_from_text(self, text: str):
        text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=100)
        chunks = text_splitter.split_text(text)
        print(f"Creating vector store from {len(chunks)} text chunks...")
        self.vector_store = FAISS.from_texts(texts=chunks, embedding=self.embeddings)
        print("Vector store created successfully.")

    def query_vector_store(self, query: str) -> str:
        if not self.vector_store:
            return "No knowledge base has been created yet. Please upload data first."
        print(f"Searching for documents related to: {query}")
        docs = self.vector_store.similarity_search(query, k=3)
        return "\n".join([doc.page_content for doc in docs])

    def clear_vector_store(self):
        self.vector_store = None
        print("In-memory knowledge base cleared.")


# ✅ Instantiate service once
rag_service = RAGService()
