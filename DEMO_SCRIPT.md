# Demonstration Script

### 1. Initial State
-   Start both the backend and frontend servers.
-   Show the clean Streamlit UI. The "Past Chats" section is empty.

### 2. Tech Lead Scenario
-   **Action:** In the sidebar, select the **"Tech Lead"** role.
-   **Action:** Upload a `bank_api_logs.pdf` document.
-   **Narration:** "As a Tech Lead, I need to check the system's health. I'm uploading today's API integration logs. The backend is now processing this document—parsing it, classifying it as a 'Bank API integration response', extracting entities, and creating embeddings."
-   **Action:** Wait for the "Upload successful" message. The chat window is now active.
-   **Action (Q1):** Ask, "Are there any API integration failures today?"
-   **Narration:** "The system retrieves the relevant context and uses the QA model to find the exact details about failures. The LLM then formats this into a clean answer with citations."
-   **Action (Q2):** Ask, "What is the average response time?"
-   **Action (Q3 - Irrelevant):** Ask, "What was our revenue last quarter?"
-   **Narration:** "Because I'm in the 'Tech Lead' role, the system correctly identifies this as a business question and politely declines to answer, maintaining the stakeholder separation."

### 3. Compliance Lead Scenario
-   **Action:** Click "➕ New Chat". The UI resets.
-   **Action:** Select the **"Compliance Lead"** role.
-   **Action:** Upload a `compliance_audit.pdf` document.
-   **Action (Q1):** Ask, "Show me the audit trail for high-value transactions."
-   **Narration:** "Now acting as a Compliance Lead, the chatbot provides details relevant to my role from the new document."

### 4. Show Persistence
-   **Action:** Refresh the browser.
-   **Narration:** "The application state is preserved. Notice the two previous chats are now listed in the 'Past Chats' section."
-   **Action:** Click on the first "Tech Lead" chat.
-   **Narration:** "I can instantly load and continue any previous conversation."
-   **Action:** Delete the chat using the '✖' icon.