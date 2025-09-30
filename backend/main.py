import os
import uuid
import sqlite3
import json
import logging
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Any

# Import the functions from your AI logic file
from rag_handler import (
    process_documents_and_create_collection, 
    query_rag_pipeline, 
    chroma_client
)

# --- Basic Setup ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
os.makedirs("documents", exist_ok=True)
os.makedirs("chroma_db", exist_ok=True)
app = FastAPI()

# --- CORS Middleware ---
# Allows your Streamlit (and old React) frontend to communicate with this backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8501", "http://localhost:5173"], # 8501 is Streamlit's default port
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Database Setup ---
DB_NAME = "chat_history.db"

def init_db():
    """Initializes the SQLite database and creates the table with all necessary columns."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS chat_histories (
            chat_id TEXT PRIMARY KEY,
            filenames TEXT,
            role TEXT,
            history TEXT
        )
    """)
    # Handle migrations for older table schemas if they exist
    try:
        cursor.execute("ALTER TABLE chat_histories ADD COLUMN role TEXT;")
    except sqlite3.OperationalError:
        pass # Column already exists
    try:
        # This handles a rename from a previous version, safe to keep
        cursor.execute("ALTER TABLE chat_histories RENAME COLUMN filename to filenames;")
    except sqlite3.OperationalError:
        pass # Column was already renamed or never existed with the old name
        
    conn.commit()
    conn.close()
    logging.info("SQLite database initialized.")

init_db()

# --- Pydantic Models for Data Validation ---
class ChatMessage(BaseModel):
    chat_id: str
    message: str

class ChatSessionMetadata(BaseModel):
    chat_id: str
    filenames: List[str]
    role: str

class ChatResponse(BaseModel):
    answer: str
    sources: List[Dict[str, Any]]

# --- API Endpoints ---
@app.post("/upload")
async def upload_documents(role: str = Form(...), files: List[UploadFile] = File(...)):
    """Handles multi-document upload, processing, and chat session creation."""
    if not role:
        raise HTTPException(status_code=400, detail="A role must be selected.")
    
    saved_files = []
    filenames = []
    try:
        for file in files:
            # Use a unique name for the saved file to prevent conflicts
            unique_filename = f"{uuid.uuid4()}_{file.filename}"
            file_path = os.path.join("documents", unique_filename)
            with open(file_path, "wb") as buffer:
                buffer.write(await file.read())
            saved_files.append(file_path)
            filenames.append(file.filename)
        
        chat_id = str(uuid.uuid4())
        
        process_documents_and_create_collection(files=saved_files, collection_name=chat_id)
        
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO chat_histories (chat_id, filenames, role, history) VALUES (?, ?, ?, ?)", 
            (chat_id, json.dumps(filenames), role, json.dumps([]))
        )
        conn.commit()
        conn.close()
        
        return {"chat_id": chat_id, "filenames": filenames, "role": role}
    except Exception as e:
        # Clean up any partially saved files if an error occurs
        for file_path in saved_files: 
            if os.path.exists(file_path):
                os.remove(file_path)
        logging.error(f"Error during document upload: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/chats", response_model=List[ChatSessionMetadata])
async def get_all_chat_sessions():
    """Retrieves metadata for all past chat sessions."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT chat_id, filenames, role FROM chat_histories ORDER BY rowid DESC")
    results = cursor.fetchall()
    conn.close()
    return [{"chat_id": cid, "filenames": json.loads(fnames or '[]'), "role": r} for cid, fnames, r in results if r]

@app.post("/chat", response_model=ChatResponse)
async def chat_with_document(request: ChatMessage):
    """Handles an incoming chat message and returns an AI-generated response."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT history, role FROM chat_histories WHERE chat_id = ?", (request.chat_id,))
    result = cursor.fetchone()
    if not result:
        conn.close()
        raise HTTPException(status_code=404, detail="Chat session not found.")
        
    current_history, role = json.loads(result[0]), result[1]
    
    try:
        response = query_rag_pipeline(
            question=request.message,
            collection_name=request.chat_id,
            role=role,
            chat_history=current_history 
        )
        
        # Save the new turn to the history
        current_history.append({"role": "user", "content": request.message})
        current_history.append({"role": "assistant", "content": response["answer"], "sources": response["sources"]})
        
        cursor.execute("UPDATE chat_histories SET history = ? WHERE chat_id = ?", (json.dumps(current_history), request.chat_id))
        conn.commit()
        
        # Debugging: Print the response to the terminal
        print(f"--- Sending Response to Frontend ---\n{response}\n---------------------------------")
        
        return response
    except Exception as e:
        logging.error(f"Error processing chat: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to process chat message: {e}")
    finally:
        conn.close()

@app.get("/history/{chat_id}", response_model=List[dict])
async def get_chat_history(chat_id: str):
    """Retrieves the full message history for a specific chat."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT history FROM chat_histories WHERE chat_id = ?", (chat_id,))
    result = cursor.fetchone()
    conn.close()
    if not result:
        raise HTTPException(status_code=404, detail="Chat history not found.")
    
    # Debugging: Print the history to the terminal
    print(f"--- Sending History to Frontend ---\n{result[0]}\n---------------------------------")
    
    return json.loads(result[0])

@app.delete("/chat/{chat_id}")
async def delete_chat_session(chat_id: str):
    """Deletes a chat session from the database and the vector store."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM chat_histories WHERE chat_id = ?", (chat_id,))
    conn.commit()
    deleted_rows = cursor.rowcount
    conn.close()
    
    if deleted_rows > 0:
        try:
            if chroma_client:
                chroma_client.delete_collection(name=chat_id)
                logging.info(f"Successfully deleted ChromaDB collection for chat_id '{chat_id}'")
            return {"status": "success", "message": f"Chat session {chat_id} deleted."}
        except Exception as e:
            logging.warning(f"Could not delete ChromaDB collection for '{chat_id}': {e}")
            return {"status": "partial", "message": "DB entry deleted, but vector collection cleanup failed."}
    else:
        raise HTTPException(status_code=404, detail="Chat session not found.")