# 🚀 Claim AI Assistant  

An AI-powered assistant that helps you analyze and interact with **insurance claims data** using **Natural Language Queries**.  
It supports both **Text-to-SQL** queries (for structured analysis) and **RAG (Retrieval-Augmented Generation)** for complex business questions.  
The system provides a **ChatGPT-like interface** where you can upload claim datasets (CSV), ask questions, and get insights instantly.  

---

<p align="center">
  <img src="https://i.ibb.co/TDckb4XG/Screenshot-2025-08-23-222459.png" alt="Claim AI Assistant Screenshot" width="800"/>
</p>

## ✨ Features  

- 💬 **ChatGPT-style UI** (React + Tailwind + shadcn/ui)  
- 🗂 **Upload CSV claims data** → data stored in **Postgres**  
- 📊 **Text-to-SQL Querying** → get instant answers from structured DB  
- 📖 **RAG Support** → for complex, reasoning-based queries  
- 🧹 **Clear Data** option → delete all claim records from DB  
- ⚡ **Streaming Responses** → answers stream like ChatGPT  
- 🔄 **Reset Chat** option → start a new analysis session  

---

## 🛠️ Tech Stack  

**Backend**  
- [FastAPI](https://fastapi.tiangolo.com/)  
- [PostgreSQL](https://www.postgresql.org/)  
- [SQLAlchemy](https://www.sqlalchemy.org/)  
- [LangChain / RAG pipeline]  

**Frontend**  
- [React (Vite + TypeScript)](https://vitejs.dev/)  
- [Tailwind CSS](https://tailwindcss.com/)  
- [shadcn/ui](https://ui.shadcn.com/)  

---
