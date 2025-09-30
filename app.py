import streamlit as st
import requests
import json
from typing import List, Dict

# --- Configuration ---
FASTAPI_URL = "http://127.0.0.1:8000"
ROLES = ["Product Lead", "Tech Lead", "Compliance Lead", "Bank Alliance Lead"]

# --- State Management ---
if "messages" not in st.session_state:
    st.session_state.messages = []
if "chat_id" not in st.session_state:
    st.session_state.chat_id = None
if "role" not in st.session_state:
    st.session_state.role = None
if "past_chats" not in st.session_state:
    st.session_state.past_chats = []

# --- API Functions ---
def get_past_chats():
    """Fetches the list of past chat sessions from the backend."""
    try:
        response = requests.get(f"{FASTAPI_URL}/chats")
        response.raise_for_status()
        st.session_state.past_chats = response.json()
    except requests.exceptions.RequestException as e:
        st.sidebar.error(f"Failed to fetch chats: {e}")
        st.session_state.past_chats = []

def load_chat_history(chat_id: str):
    """Loads the history for a selected chat."""
    try:
        response = requests.get(f"{FASTAPI_URL}/history/{chat_id}")
        response.raise_for_status()
        
        history = response.json() if isinstance(response.json(), list) else []
        sanitized_history = [
            {
                "role": msg.get("role", "assistant"),
                "content": msg.get("content", "Invalid content"),
                "sources": msg.get("sources", [])
            } for msg in history
        ]
        
        st.session_state.messages = sanitized_history
        st.session_state.chat_id = chat_id
        for chat in st.session_state.past_chats:
            if chat['chat_id'] == chat_id:
                st.session_state.role = chat['role']
                break

    except requests.exceptions.RequestException as e:
        st.error(f"Failed to load chat history: {e}")

# --- Sidebar UI ---
with st.sidebar:
    st.header("Chatbot Setup")

    def reset_chat():
        st.session_state.messages = []
        st.session_state.chat_id = None
        st.session_state.role = None
    
    st.button("➕ New Chat", on_click=reset_chat, use_container_width=True)

    st.subheader("1. Select Role")
    selected_role = st.radio(
        "Choose your role:",
        options=ROLES,
        key="role_selection",
        disabled=(st.session_state.chat_id is not None),
        horizontal=False,
    )

    st.subheader("2. Upload Document(s)")
    uploaded_files = st.file_uploader(
        "Upload PDF, TXT, or CSV documents",
        type=["pdf", "txt", "csv"], # MODIFIED: Added txt and csv
        accept_multiple_files=True,
        key="file_uploader",
        disabled=(st.session_state.chat_id is not None)
    )

    if st.button("Upload & Start Chat", use_container_width=True, disabled=(not uploaded_files or st.session_state.chat_id is not None)):
        with st.spinner("Processing documents... This may take a moment."):
            try:
                files_for_upload = [("files", (file.name, file.getvalue(), file.type)) for file in uploaded_files]
                
                response = requests.post(
                    f"{FASTAPI_URL}/upload",
                    data={"role": selected_role},
                    files=files_for_upload
                )
                response.raise_for_status()
                result = response.json()
                
                reset_chat()
                st.session_state.chat_id = result['chat_id']
                st.session_state.role = result['role']
                get_past_chats()
                st.rerun()
                
            except requests.exceptions.RequestException as e:
                st.error(f"Upload failed: {e.response.json().get('detail', 'Unknown error')}")

    st.divider()
    st.subheader("Past Chats")
    
    if not st.session_state.past_chats:
        get_past_chats()

    for chat in st.session_state.past_chats:
        filenames = ", ".join(chat['filenames'])
        label = f"**{chat['role']}**: {filenames}"
        if st.button(label, key=chat['chat_id'], use_container_width=True):
            load_chat_history(chat['chat_id'])
            st.rerun()

# --- Main Chat Interface ---
st.title(f"Multi-Stakeholder Chatbot")
if st.session_state.role:
    st.caption(f"Chatting as: **{st.session_state.role}** | Chat ID: `{st.session_state.chat_id}`")

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        sources = message.get("sources", [])
        if sources:
            st.caption("Sources:")
            for source in sources:
                st.caption(f"- {source['source_file']} (Type: {source['doc_type']})")

if prompt := st.chat_input("Ask a question about the documents..."):
    if not st.session_state.chat_id:
        st.error("Please start a new chat by uploading documents first.")
    else:
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                try:
                    response = requests.post(
                        f"{FASTAPI_URL}/chat",
                        json={"chat_id": st.session_state.chat_id, "message": prompt}
                    )
                    response.raise_for_status()
                    assistant_response = response.json()
                    
                    st.markdown(assistant_response.get("answer", "No answer received."))
                    sources = assistant_response.get("sources", [])
                    if sources:
                        st.caption("Sources:")
                        for source in sources:
                            st.caption(f"- {source['source_file']} (Type: {source['doc_type']})")
                    
                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": assistant_response.get("answer"),
                        "sources": sources
                    })
                    
                except requests.exceptions.RequestException as e:
                    st.error(f"Failed to get response: {e.response.json().get('detail', 'Unknown error')}")