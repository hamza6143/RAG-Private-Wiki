# 🚀 Nexus Hub: Secure Enterprise Knowledge Management

Nexus Hub is a full-stack, secure Retrieval-Augmented Generation (RAG) application. It acts as a private AI search engine for organizational documents. Built with a focus on data security, it features role-based access control, hybrid search capabilities, and an automated AI telemetry suite to grade its own answers.

## 🛠️ Tech Stack
* **Frontend:** Streamlit (with custom responsive CSS)
* **Vector Database:** Pinecone (Serverless)
* **Relational Database:** PostgreSQL (Hosted on Supabase)
* **Orchestration:** LlamaIndex
* **Embedding Model:** Google Gemini (`gemini-embedding-2-preview`)
* **LLM Engine:** Groq (`llama-3.1-8b-instant`)
* **Evaluation/Telemetry:** Ragas & Instructor

---

## 🏗️ System Architecture & Function Breakdown

The backend is modularized into distinct pipelines to handle authentication, ingestion, retrieval, and evaluation. Here is a detailed breakdown of every function powering the application.

### 1. `database_manager.py` (Relational Ledger & Auth)
Manages PostgreSQL connections to Supabase. It tracks document metadata, vector chunk IDs, and handles secure user authentication.

* **`get_db_connection()`**: Establishes a secure session pool with the PostgreSQL/Supabase database using the environment's `DATABASE_URL`.
* **`init_db()`**: Bootstraps the relational ledger. Creates the `users`, `documents`, and `document_chunks` tables with strict foreign key constraints if they do not already exist.
* **`hash_password(password, salt)`**: Cryptographically secures user passwords using SHA-256 hashing and a randomized salt.
* **`register_user(username, password, role, org_name)`**: Validates and provisions a new user account, sanitizes their organization namespace, and commits their hashed credentials to the database.
* **`authenticate_user(username, password)`**: Verifies login attempts by matching the computed hash against the stored hash, returning the user's role and organization context.
* **`check_document_state(org_namespace, file_name, doc_id)`**: Checks if a file has been uploaded before. Returns states like `NEW`, `DUPLICATE`, or `UPDATE` to prevent redundant vectorization.
* **`commit_document_to_ledger(...)`**: Uses PostgreSQL upsert (`ON CONFLICT`) logic to atomically register a document and its individual chunk IDs into the ledger after successful Pinecone ingestion.
* **`get_chunks_for_deletion(...)`**: Queries the relational database to fetch specific vector chunk IDs associated with a file (or specific pages) so they can be accurately targeted for deletion in Pinecone.
* **`clear_ledger_records(...)`**: Wipes document and chunk metadata from the PostgreSQL database after a successful vector purge.
* **`get_namespace_documents(org_namespace)`**: Retrieves a list of all active documents available to a specific organization for display in the UI.

### 2. `document_parser.py` (Data Ingestion)
Handles the extraction of raw text and metadata from various file formats.

* **`advanced_parser_async(file_name, file_bytes, temp_path)`**: An asynchronous router that reads files based on their extension. It uses `pandas` to serialize rows in `.csv` and `.xlsx` files, and leverages `LlamaParse` to parse unstructured data (like PDFs and Word docs) into clean Markdown. 

### 3. `vector_pipeline.py` (Embedding & Retrieval)
The core RAG engine. It orchestrates the chunking, embedding, and querying of vector data.

* **`init_central_pinecone_index()`**: Initializes the Pinecone index (configured for 768 dimensions and cosine similarity to support Gemini embeddings) if it does not already exist.
* **`process_single_file_async(...)`**: The core ingestion loop. It hashes the file, checks the SQL ledger for duplicates, chunks the text into nodes, strips conflicting LlamaIndex graph relationships, embeds the data, pushes it to Pinecone, and logs the IDs in Supabase.
* **`process_batch_files_async(...)`**: A wrapper that takes multiple uploaded files and processes them concurrently using `asyncio.gather`.
* **`delete_document_data(...)`**: Executes a surgical data purge. It fetches the exact vector IDs from the SQL database and deletes them directly from the Pinecone cluster, ensuring no ghost data remains.
* **`query_secure_namespace(...)`**: The main search engine. It builds a retriever (supporting both Semantic and Hybrid search modes), enforces strict role-based access filtering (e.g., ensuring an 'Employee' cannot query 'CEO' documents), and routes the retrieved context to Groq for the final synthesized answer.

### 4. `eval_pipeline.py` (AI Telemetry & Benchmarking)
An automated diagnostic suite that uses the `ragas` framework to grade the AI's performance.

* **`_build_llm(api_key)`**: Constructs an asynchronous, `instructor`-wrapped Gemini client to handle structured evaluation outputs required by Ragas.
* **`_build_embeddings(api_key)`**: Adapts the LlamaIndex Google GenAI embedding model into a format compatible with Ragas base metrics.
* **`_score_case(metrics, case_inputs)`**: Evaluates a single Q&A test case against four distinct metrics (Faithfulness, Answer Relevancy, Context Precision, and Context Recall). Incorporates a deliberate rate-limit throttle to prevent API cap crashes.
* **`run_uploaded_evaluation_workflow(...)`**: Orchestrates the entire telemetry suite. It parses an uploaded JSON benchmark dataset, runs the queries through the live vector pipeline, scores the results, and returns a Pandas DataFrame containing the diagnostic report.

### 5. `app.py` (Streamlit Frontend)
The user interface, featuring a custom responsive CSS framework. It handles session state, secure routing, and provides the three main workspace tabs: Intelligence Search, Data Library (for ingestion/purging), and System Analytics (for telemetry).

---

## 🚀 Running the Project

### Prerequisites
You will need API keys for the following services:
* Supabase (PostgreSQL connection string)
* Pinecone 
* Groq
* Google Gemini

### Installation
1. Clone the repository.
2. Install the exact dependencies from the requirements file to ensure compatibility:
   ```bash
   pip install -r requirements.txt
