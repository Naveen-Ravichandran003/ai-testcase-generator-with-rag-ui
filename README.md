# AI Test Case Generator using RAG, Langflow & Batch Processing with UI

![Python](https://img.shields.io/badge/Python-3.10-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-Backend-green)
![Streamlit](https://img.shields.io/badge/Streamlit-UI-red)
![Langflow](https://img.shields.io/badge/Langflow-RAG-purple)

An enterprise-grade AI Test Case Generator that leverages RAG (Retrieval-Augmented Generation), Langflow pipelines, and LLMs (Groq / Llama3) to generate scalable, high-quality test cases from JIRA or feature inputs.

The system uses batch processing to overcome LLM token limits and integrates a Streamlit UI with a FastAPI backend for seamless user interaction.

## 💡 Why This Project?
LLMs cannot generate large volumes of structured output (e.g., 500 test cases) in a single request due to token limitations.

This project solves that problem using:
- Batch processing
- RAG architecture
- Prompt engineering
- Deduplication strategies

This ensures scalability, accuracy, and high-quality output.

## 🚀 Features
- **✅ Batch-based Generation:** Generates large volumes (500+) using controlled batching (20 per batch)
- **✅ Perfect Sequential Numbering:** Ensures TC001 → TC500 without gaps
- **✅ Dynamic Makeup Engine:** Automatically fills missing test cases if a batch under-produces
- **✅ Rate Limit Handling:** Detects API limits (429) and retries intelligently
- **✅ Auto-Save System:** Saves outputs in Markdown and JSON formats
- **✅ Multi-layer Deduplication:** Prevents duplicate scenarios using contextual memory
- **✅ Circuit Breakers:** Stops execution safely during repeated failures

## 🏗️ Architecture Diagram

```mermaid
graph TD
    A[User Input Jira/Feature] --> B[Streamlit UI]
    B --> C[FastAPI Backend Batch Processing]
    C -->|20 cases/batch| D[Langflow RAG Pipeline]
    
    subgraph Langflow Core
        D -->|Generate Test Cases| E[LLM llama/Groq/Gemini]
        E --> F[Test Cases]
        F --> G[Embeddings + Chunking]
        G --> H[(Chroma DB Vector Storage)]
        I[User Query] --> J[RAG Retrieval Semantic Search]
        H -.-> J
        J --> K[Context-Aware LLM Response]
    end
    
    K --> L[API Integration Response]
    L --> M[Export Formats CSV/Text/Excel]
```

## 🧩 Workflow

1. User Input  
   → JIRA ticket or feature description via UI  

2. Batch Processing  
   → Splits generation into batches (20 test cases each)  

3. LLM Generation  
   → Langflow orchestrates prompt-based test case creation  

4. RAG Storage  
   → Test cases converted to embeddings and stored in Chroma DB  

5. Retrieval  
   → Relevant test cases fetched using semantic search  

6. Response Generation  
   → LLM generates context-aware output  

7. Export  
   → Outputs saved as CSV / Markdown / JSON  

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

---
**Developed by Naveen Ravichandran**
