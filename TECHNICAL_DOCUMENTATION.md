# Technical Documentation: Multi-Stakeholder Chatbot

### 1. Architecture Overview
The system employs a decoupled microservices architecture with a Streamlit frontend and a FastAPI backend. This separation allows the UI and the AI logic to be developed, scaled, and maintained independently.

-   **Frontend (Streamlit):** A pure Python, interactive web application for user interaction, file uploads, and displaying chat history.
-   **Backend (FastAPI):** A high-performance Python API that serves as the brain of the operation. It handles all AI model inference, data processing, and database interactions.
-   **Vector Database (ChromaDB):** A persistent local vector store used to save document embeddings and their associated metadata for efficient semantic search.

### 2. Model Selection Rationale

The models were chosen to balance performance, efficiency, and suitability for the specified tasks, with a key constraint of being able to run on local, non-GPU hardware.

-   **Embedding Model (`BAAI/bge-large-en-v1.5`):** Chosen for its state-of-the-art performance on the MTEB benchmark, ensuring the most accurate retrieval of document context.
-   **Document Classifier (Fine-tuned `distilbert-base-uncased`):** A custom-trained model to accurately categorize incoming documents into one of the four specified types (UPI log, Compliance report, etc.). DistilBERT was chosen for its small size and speed.
-   **NER Model (Fine-tuned `distilbert-base-uncased`):** A custom-trained model for extracting financial and domain-specific entities.
-   **Extractive QA Model (Fine-tuned `distilbert-base-uncased`):** This model is the core of the fact-extraction step. It is trained to find precise, literal answer snippets from a given context.
-   **LLM for Synthesis (`google/flan-t5-base`):** A small but powerful instruction-tuned LLM. It is used *only* for reasoning (generating sub-questions) and formatting (synthesizing extracted snippets into a clean answer). Its use is strictly controlled by prompts to prevent hallucination.

### 3. Vector Database Schema
We use ChromaDB to store embeddings. Each vector is associated with a rich metadata object to enable powerful, context-aware retrieval.

-   **`doc_type`:** The category of the document (e.g., "Compliance audit report"), as determined by the classifier.
-   **`entities`:** A JSON string containing a list of named entities (e.g., organization, date, amount) found in the chunk.
-   **`source_file`:** The original filename of the document.
-   **`chunk_id`:** A unique identifier for the specific chunk within its document.

### 4. Stakeholder-Specific Query Handling Logic
The system uses an advanced **"Multi-Query Extraction & Synthesis"** pipeline to ensure answers are comprehensive, factually grounded, and role-specific.

1.  **Role-Relevance Check:** The user's question is first classified against a list of topics relevant to their selected role. Irrelevant questions are rejected early.
2.  **Deconstruct:** The LLM generates several targeted sub-questions from the user's original query.
3.  **Extract:** The fine-tuned extractive QA model runs on each sub-question, gathering multiple word-for-word snippets from the retrieved document context.
4.  **Synthesize:** The LLM receives these exact snippets and is given a strict prompt to assemble them into a single, well-formatted answer, add citations, and not introduce any outside information.