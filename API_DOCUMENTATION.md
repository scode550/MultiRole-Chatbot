# API Documentation

The backend is served via FastAPI at `http://localhost:8000`.

### `POST /upload`
-   **Description:** Uploads one or more documents, processes them, and creates a new chat session.
-   **Request:** `multipart/form-data`
    -   `role` (form field, string, required): The stakeholder role for this chat (e.g., "Tech Lead").
    -   `files` (file field, required): One or more files (`.pdf`, `.txt`, `.csv`).
-   **Response (200 OK):**
    ```json
    {
      "chat_id": "a1b2c3d4-...",
      "filenames": ["report-q1.pdf", "agreement.pdf"],
      "role": "Tech Lead"
    }
    ```

### `POST /chat`
-   **Description:** Sends a user's question for an active chat and gets a response.
-   **Request:** `application/json`
    ```json
    {
      "chat_id": "a1b2c3d4-...",
      "message": "Are there any API integration failures today?"
    }
    ```
-   **Response (200 OK):**
    ```json
    {
      "answer": "The document mentions several API integration failures with Bank X today.",
      "sources": [
        {
          "source_file": "bank_logs.pdf",
          "doc_type": "Bank API integration response"
        }
      ]
    }
    ```

### `GET /chats`
-   **Description:** Retrieves metadata for all past chat sessions.
-   **Response (200 OK):**
    ```json
    [
      {
        "chat_id": "a1b2c3d4-...",
        "filenames": ["report-q1.pdf"],
        "role": "Tech Lead"
      },
      {
        "chat_id": "e5f6g7h8-...",
        "filenames": ["compliance_audit.pdf"],
        "role": "Compliance Lead"
      }
    ]
    ```

### `GET /history/{chat_id}`
-   **Description:** Retrieves the full message history for a specific chat.
-   **Response (200 OK):**
    ```json
    [
      { "role": "user", "content": "Any failures today?" },
      {
        "role": "assistant",
        "content": "Yes, there were failures with Bank X.",
        "sources": [...]
      }
    ]
    ```

### `DELETE /chat/{chat_id}`
-   **Description:** Deletes a chat session and its associated data.
-   **Response (200 OK):**
    ```json
    {
      "status": "success",
      "message": "Chat session a1b2c3d4-... deleted."
    }
    ```