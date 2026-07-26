# Nexus Hub: Enterprise Knowledge Management

Nexus Hub is a secure enterprise knowledge management system that allows users to ask questions, manage documents, and monitor AI analytics. It utilizes a modern Retrieval-Augmented Generation (RAG) architecture powered by LlamaIndex, Pinecone, and Groq.

## 🚀 Core Features

* **Role-Based Access Control (RBAC)**: Users authenticate through a secure portal and are assigned clearance levels such as Employee, Client, Manager, or CEO[cite: 1]. User credentials and roles are securely hashed and stored in a PostgreSQL database.
* **Intelligent Document Ingestion**: The system processes uploaded documents into a vector space[cite: 1]. It utilizes LlamaParse for advanced unstructured document parsing and pandas for structured CSV or Excel files[cite: 3].
* **Hybrid & Semantic Search**: The application queries the knowledge base using either Semantic or Hybrid retrieval strategies[cite: 1]. This search is powered by a Pinecone serverless vector database, Groq LLMs, and Google GenAI embeddings.
* **Surgical Data Purging**: Administrators can execute data purges targeting specific filenames or even specific document pages[cite: 1]. This is achieved by mapping exact vector chunk IDs via a PostgreSQL ledger to safely and accurately remove them from the Pinecone cluster.
* **AI Telemetry & Diagnostics**: The system includes a telemetry suite to benchmark AI model performance against ground-truth datasets[cite: 1]. It uses the RAGAS framework to measure metrics like Faithfulness, Answer Relevancy, Context Precision, and Context Recall[cite: 4].

## 🛠️ Technology Stack

* **Frontend:** Streamlit[cite: 1]
* **Backend:** Python, PostgreSQL (`psycopg2`)[cite: 1, 2]
* **AI & LLM Framework:** LlamaIndex, Groq (`llama-3.1-8b-instant`), Google GenAI Embeddings (`gemini-embedding-2-preview`)[cite: 5]
* **Document Parsing:** LlamaParse, Pandas[cite: 3]
* **Vector Database:** Pinecone[cite: 5]
* **Evaluation:** Ragas, Instructor[cite: 4]

## ⚙️ Installation & Setup

### 1. Clone the repository
```bash
git clone [https://github.com/your-username/nexus-hub.git](https://github.com/your-username/nexus-hub.git)
cd nexus-hub
