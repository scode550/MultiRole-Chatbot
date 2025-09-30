import torch
import logging
import chromadb
import fitz  # PyMuPDF
from transformers import pipeline
from sentence_transformers import SentenceTransformer
import re
import json
import os
from typing import List, Dict, Any

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- MODEL AND CLIENT INITIALIZATION ---
llm_pipeline = None
qa_pipeline = None
embedding_model = None
classification_pipeline = None
ner_pipeline = None
relevance_checker_pipeline = None
chroma_client = None

HF_USERNAME = "epraneeth" 

ROLE_TOPICS = {
    "Product Lead": ["business metrics", "user behavior", "product performance"],
    "Tech Lead": ["technical issues", "system performance", "integration status"],
    "Compliance Lead": ["regulatory adherence", "risk factors", "audit trails"],
    "Bank Alliance Lead": ["partnership performance", "integration health", "SLA compliance"]
}

try:
    if torch.cuda.is_available(): device = "cuda"
    elif torch.backends.mps.is_available(): device = "mps"
    else: device = "cpu"
    logging.info(f"Using device: {device}")

    qa_model_id = f"{HF_USERNAME}/distilbert-finetuned-financial-qa" 
    logging.info(f"Initializing Extractive QA pipeline ({qa_model_id})...")
    qa_pipeline = pipeline("question-answering", model=qa_model_id, device=0 if device == "cuda" else -1)

    logging.info("Initializing LLM pipeline for synthesis (google/flan-t5-base)...")
    llm_pipeline = pipeline("text2text-generation", model="google/flan-t5-base", device=0 if device == "cuda" else -1)
    
    classifier_model_id = f"{HF_USERNAME}/distilbert-finetuned-financial-doc-classifier"
    logging.info(f"Initializing Fine-tuned Classification pipeline from: {classifier_model_id}")
    classification_pipeline = pipeline("text-classification", model=classifier_model_id, device=0 if device == "cuda" else -1)

    ner_model_id = f"{HF_USERNAME}/distilbert-finetuned-financial-ner"
    logging.info(f"Initializing Fine-tuned NER pipeline from: {ner_model_id}")
    ner_pipeline = pipeline("ner", model=ner_model_id, aggregation_strategy="simple", device=0 if device == "cuda" else -1)

    logging.info("Initializing Relevance Check pipeline (facebook/bart-large-mnli)...")
    relevance_checker_pipeline = pipeline("zero-shot-classification", model="facebook/bart-large-mnli", device=0 if device == "cuda" else -1)

    # --- MODEL CHANGE ---
    embedding_model_id = "BAAI/bge-large-en-v1.5"
    logging.info(f"Initializing Embedding model ({embedding_model_id})...")
    embedding_model = SentenceTransformer(embedding_model_id, device=device)
    
    logging.info("Initializing ChromaDB client...")
    chroma_client = chromadb.PersistentClient(path="./chroma_db")
    
    logging.info("All models and clients initialized successfully.")

except Exception as e:
    logging.error(f"Error during model or client initialization: {e}", exc_info=True)
    logging.error("Please ensure you have replaced 'YOUR_HF_USERNAME' with your actual Hugging Face username and that your models are public.")


def classify_document(text: str) -> str:
    if not classification_pipeline: raise ConnectionError("Document classifier not initialized.")
    result = classification_pipeline(text[:512])
    return result[0]['label']

def extract_entities(text: str) -> list:
    if not ner_pipeline: raise ConnectionError("NER pipeline not initialized.")
    try:
        entities = ner_pipeline(text)
        return [{"word": entity['word'].strip(), "entity": entity['entity_group']} for entity in entities]
    except Exception as e:
        logging.error(f"Error during entity extraction: {e}")
        return []

def process_documents_and_create_collection(files: list, collection_name: str):
    if not all([chroma_client, embedding_model]): raise ConnectionError("Core services not initialized.")
    all_chunks, all_metadatas, all_ids = [], [], []
    doc_id_counter = 0
    
    for file_path in files:
        doc_id_counter += 1
        file_basename = os.path.basename(file_path)
        logging.info(f"Processing document {doc_id_counter}: {file_basename}")
        text = ""
        try:
            with fitz.open(file_path) as doc:
                for page_num, page in enumerate(doc, start=1):
                    text += page.get_text("text") + f"\n--- Page {page_num} ---\n"
        except Exception as e:
            raise ValueError(f"Could not read the PDF file {file_basename}. Error: {e}")

        if not text.strip(): continue

        doc_type = classify_document(text)
        chunks = [text[i:i+1000] for i in range(0, len(text), 800) if text[i:i+1000].strip()]
        
        for chunk_idx, chunk in enumerate(chunks, start=1):
            chunk_id = f"doc{doc_id_counter}_chunk{chunk_idx}"
            entities = extract_entities(chunk)
            
            all_chunks.append(chunk)
            all_metadatas.append({
                'doc_type': doc_type, 'entities': json.dumps(entities),
                'source_file': file_basename, 'chunk_id': chunk_id
            })
            all_ids.append(chunk_id)

    if not all_chunks: raise ValueError("No text could be extracted from the provided documents.")
    try:
        if collection_name in [c.name for c in chroma_client.list_collections()]:
            chroma_client.delete_collection(name=collection_name)
    except Exception as e:
        logging.warning(f"Could not delete collection '{collection_name}': {e}")

    collection = chroma_client.create_collection(name=collection_name)
    embeddings = embedding_model.encode(all_chunks, show_progress_bar=True).tolist()
    
    collection.add(embeddings=embeddings, documents=all_chunks, metadatas=all_metadatas, ids=all_ids)


def is_query_relevant_for_role(query: str, role: str) -> bool:
    if not relevance_checker_pipeline: raise ConnectionError("Relevance checker pipeline not initialized.")
    if role not in ROLE_TOPICS: return True
    
    result = relevance_checker_pipeline(query, ROLE_TOPICS[role])
    logging.info(f"Query relevance for role '{role}': Top topic '{result['labels'][0]}' with score {result['scores'][0]:.4f}")
    return result['scores'][0] > 0.2

def query_rag_pipeline(question: str, collection_name: str, role: str, chat_history: List[Dict]) -> Dict[str, Any]:
    if not all([qa_pipeline, llm_pipeline, embedding_model, chroma_client]): raise ConnectionError("Core models not initialized.")
    
    if not is_query_relevant_for_role(question, role):
        answer = f"This question does not seem related to the typical responsibilities of a {role}."
        return {"answer": answer, "sources": []}

    collection = chroma_client.get_collection(name=collection_name)
    question_embedding = embedding_model.encode(question).tolist()
    
    results = collection.query(query_embeddings=[question_embedding], n_results=5, include=['documents', 'metadatas'])
    sources = results['metadatas'][0] if results['metadatas'] else []
    context_docs = results['documents'][0] if results['documents'] else []
    
    if not context_docs:
        return {"answer": "Could not find relevant information in the uploaded documents.", "sources": []}
    
    context = " ".join(context_docs)

    sub_question_prompt = f"Based on the user's question, generate up to 3 simple, specific questions to find evidence in a document. User Question: {question}"
    sub_questions_response = llm_pipeline(sub_question_prompt, max_new_tokens=100)
    sub_questions = [q.strip() for q in sub_questions_response[0]['generated_text'].split('\n') if q.strip() and '?' in q]
    sub_questions.append(question)
    
    extracted_answers = set()
    for q in sub_questions:
        result = qa_pipeline(question=q, context=context)
        if result['score'] > 0.1:
            clean_answer = result['answer'].strip(" ,.;:-")
            if clean_answer: extracted_answers.add(clean_answer)
    
    if not extracted_answers:
        return {"answer": f"I could not find a confident answer in the documents for a {role}.", "sources": []}

    synthesis_prompt = f"""
    You are an expert assistant acting as a {role}. Synthesize a single, comprehensive answer to the user's original question based ONLY on the following extracted quotes.
    - Assemble the quotes into a clean, well-formatted response (paragraphs or bullets).
    - You MUST use the exact word-for-word quotes. Do not add any new information.
    - After the answer, cite all sources provided in the format.

    User's Original Question: "{question}"
    Extracted Quotes:
    - {"\n- ".join(extracted_answers)}
    Sources: {", ".join(set(s['source_file'] for s in sources))}
    Synthesized Answer:
    """
    
    final_response = llm_pipeline(synthesis_prompt, max_new_tokens=512, clean_up_tokenization_spaces=True)
    final_answer = final_response[0]['generated_text']

    unique_sources = []
    seen_files = set()
    for source in sources:
        if source['source_file'] not in seen_files:
            unique_sources.append({'source_file': source['source_file'], 'doc_type': source.get('doc_type', 'N/A')})
            seen_files.add(source['source_file'])

    return {"answer": final_answer, "sources": unique_sources}