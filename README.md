# RAG-Private-Wiki

RAG-Private-Wiki is a secure enterprise knowledge management system that allows users to ask questions, manage documents, and monitor AI analytics. It utilizes a modern Retrieval-Augmented Generation (RAG) architecture powered by LlamaIndex, Pinecone, and Groq.

## 🚀 Core Features

* **Role-Based Access Control (RBAC)**: Users authenticate through a secure portal and are assigned clearance levels such as Employee, Client, Manager, or CEO. User credentials and roles are securely hashed and stored in a PostgreSQL database.
* **Intelligent Document Ingestion**: The system processes uploaded documents into a vector space. It utilizes LlamaParse for advanced unstructured document parsing and pandas for structured CSV or Excel files.
* **Hybrid & Semantic Search**: The application queries the knowledge base using either Semantic or Hybrid retrieval strategies. This search is powered by a Pinecone serverless vector database, Groq LLMs, and Google GenAI embeddings.
* **Surgical Data Purging**: Administrators can execute data purges targeting specific filenames or even specific document pages. This is achieved by mapping exact vector chunk IDs via a PostgreSQL ledger to safely and accurately remove them from the Pinecone cluster.
* **AI Telemetry & Diagnostics**: The system includes a telemetry suite to benchmark AI model performance against ground-truth datasets. It uses the RAGAS framework to measure metrics like Faithfulness, Answer Relevancy, Context Precision, and Context Recall.

## 🛠️ Technology Stack

* **Frontend:** Streamlit
* **Backend:** Python, PostgreSQL (`psycopg2`)
* **AI & LLM Framework:** LlamaIndex, Groq (`llama-3.1-8b-instant`), Google GenAI Embeddings (`gemini-embedding-2-preview`)
* **Document Parsing:** LlamaParse, Pandas
* **Vector Database:** Pinecone
* **Evaluation:** Ragas, Instructor

## ⚙️ Installation & Setup

### 1. Clone the repository
```bash
git clone [https://github.com/hamza6143/RAG-Private-Wiki.git](https://github.com/hamza6143/RAG-Private-Wiki.git)
cd RAG-Private-Wiki
