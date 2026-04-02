# AI Test Case Generator with RAG UI

An enterprise-grade, highly resilient AI Test Case Generator. This application seamlessly integrates a beautiful Streamlit frontend with a robust FastAPI backend, orchestrating generation tasks through Langflow RAG pipelines and LLMs (Groq / Llama3 / Gemini). 

## 🚀 Features
- **Perfect Sequential Numbering & Ghost-Count Fixes:** Ensures gapless sequential numbering (e.g. TC-001, TC-002...) regardless of AI variation or intermittent batch failures.
- **Smart Quota & Rate Limit Guardian:** Dynamically intercepts `HTTP 429` Rate Limits from Groq/LLMs. Deciphers exact "Retry After" backoffs and automatically pauses, or cleanly aborts with a user-friendly UI timer.
- **Dynamic Makeup Engine:** If the LLM produces fewer test cases than requested per batch (e.g., 17 instead of 20), the engine dynamically spins up calculated "makeup batches" at the tail end to hit your exact target (e.g., exactly 500 scenarios).
- **Auto-Save & Structured Markdown:** Every generation is safely auto-saved locally into `saved_test_cases/` as cleanly formatted `.md` documents and raw `.json` metadata. No work is lost even if the connection drops.
- **Multi-Layer Category Deduplication:** Uses an advanced rotating cache to inject previously generated module contexts directly into the AI prompt to enforce 100% unique edge-cases.
- **Circuit Breakers:** Aborts cleanly if upstream AI models experience extended outages (3 consecutive failures).

## 🛠️ Tech Stack
- **Frontend:** Streamlit 
- **Backend:** FastAPI, Uvicorn, Python `requests`
- **AI Processing:** Langflow 

## 📦 Installation & Usage

1. **Clone the repo**
   ```bash
   git clone https://github.com/Naveen-Ravichandran003/ai-testcase-generator-with-rag-ui.git
   cd ai-testcase-generator-with-rag-ui
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Start the FastAPI Backend**
   ```bash
   uvicorn main:app --reload --port 8000
   ```

4. **Start the Streamlit UI**
   ```bash
   streamlit run app.py --server.port 8501
   ```

5. **Start Generating**
   - Access the UI at `http://localhost:8501`.
   - Enter your Jira User Story and your Langflow ID.
   - Adjust your target count (up to 1,000 cases).
   - Let the dynamic pipeline do the heavy lifting!

## 💾 Saved Exports
All runs are securely cached in the `saved_test_cases/` directory and structurally exported with metadata tracking. You can access these structured `.md` files at any point for Jira imports or local review.
