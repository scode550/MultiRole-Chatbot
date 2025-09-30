# Multi-Stakeholder Financial Document Chatbot

An intelligent chatbot system designed to answer role-specific queries about financial documents. This project uses a multi-model RAG (Retrieval-Augmented Generation) pipeline to provide accurate, context-aware, and cited answers for different stakeholders, including Product Leads, Tech Leads, and Compliance Leads.

### Architecture

The system is built on a decoupled frontend-backend architecture. The Streamlit UI acts as a client to a powerful FastAPI backend that orchestrates a pipeline of specialized AI models.



**Workflow:**
1.  **Ingestion:** User selects a role and uploads documents (PDF, TXT, CSV).
2.  **Processing:** The backend uses a pipeline to:
    * Parse and chunk the documents.
    * Classify the document type (e.g., "Compliance Report").
    * Extract named entities (NER) from each chunk.
    * Create text embeddings for each chunk.
3.  **Storage:** Embeddings and rich metadata (doc type, entities, source file) are stored in a ChromaDB vector database.
4.  **Querying:** When a user asks a question:
    * The system checks if the question is relevant to the user's role.
    * It uses a "Multi-Query Extraction & Synthesis" pipeline to find exact snippets from the document and then uses an LLM to format them into a comprehensive, cited answer.

### Features

* **Role-Based Access & Logic:** Provides tailored answers based on the selected stakeholder role.
* **Multi-Document Support:** Chat with one or more documents (`.pdf`, `.txt`, `.csv`) in a single session.
* **Fact-Grounded Responses:** Uses an "Extract-then-Refine" pipeline to ensure answers are built from the exact text of the documents.
* **Source Citations:** All answers are accompanied by citations pointing to the source document.
* **Multi-Model Pipeline:** Utilizes specialized models for Document Classification, Named Entity Recognition (NER), and Question Answering.
* **Persistent Chat History:** Chats are saved and can be revisited.

### Tech Stack

* **Backend:** Python, FastAPI, Uvicorn
* **Frontend:** Streamlit
* **AI / ML:** PyTorch, Hugging Face Transformers, Sentence-Transformers
* **Vector Database:** ChromaDB
* **Document Parsing:** PyMuPDF

### Setup and Installation

#### Using Docker (Recommended)

This is the easiest way to run the entire application.
1.  Ensure you have Docker and Docker Compose installed.
2.  From the project's root directory, build and run the containers:
    ```bash
    docker-compose up --build
    ```
3.  Access the Streamlit UI at `http://localhost:8501`.
4.  The FastAPI backend will be available at `http://localhost:8000`.

#### Local (Manual) Setup

1.  **Backend:**
    ```bash
    cd backend
    python -m venv venv
    source venv/bin/activate  # On Windows: venv\Scripts\activate
    pip install -r requirements.txt
    uvicorn main:app --reload
    ```
2.  **Frontend (in a separate terminal):**
    ```bash
    # Make sure you are in the project's root directory
    python -m venv venv
    source venv/bin/activate # On Windows: venv\Scripts\activate
    pip install -r frontend_requirements.txt
    streamlit run app.py
    ```

### Project Structure

```
.
├── app.py                   # Streamlit frontend application
├── backend/
│   ├── main.py              # FastAPI application
│   ├── rag_handler.py       # Core RAG and AI model logic
│   ├── requirements.txt     # Backend Python dependencies
│   ├── Dockerfile           # Docker instructions for backend
│   └── ...
├── docker-compose.yml       # Docker Compose configuration
├── frontend_requirements.txt # Streamlit Python dependencies
└── README.md
```
