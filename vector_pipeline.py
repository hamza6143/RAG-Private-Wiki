import os
import json
import hashlib
import asyncio
import uuid
from typing import List
from dotenv import load_dotenv
from llama_index.core.schema import NodeRelationship
from pinecone import ServerlessSpec
from llama_index.embeddings.google_genai import GoogleGenAIEmbedding
from pinecone import Pinecone
from llama_index.core import VectorStoreIndex, StorageContext, Settings
from llama_index.core.node_parser import SentenceSplitter
from llama_index.vector_stores.pinecone import PineconeVectorStore
from llama_index.llms.groq import Groq             
from llama_index.core.postprocessor import LLMRerank
from llama_index.core.query_engine import RetrieverQueryEngine

from document_parser import advanced_parser_async
import database_manager as db  # Use updated SQL engine functions

load_dotenv()

Settings.llm = Groq(
    model="llama-3.1-8b-instant", 
    api_key=os.environ.get("GROQ_API_KEY")
)
Settings.embed_model = GoogleGenAIEmbedding(
    model_name="gemini-embedding-2-preview", 
    api_key=os.environ.get("GEMINI_API_KEY")
)

pc = Pinecone(api_key=os.environ.get("PINECONE_API_KEY", "your-key"))
SHARED_COMPANY_INDEX = "central-enterprise-rag-v3"

def init_central_pinecone_index():
    if SHARED_COMPANY_INDEX not in pc.list_indexes().names():
        pc.create_index(
            name=SHARED_COMPANY_INDEX,
            dimension=3072,
            metric="dotproduct", # 🚨 CHANGED: Required to support Hybrid Search
            spec=ServerlessSpec(cloud="aws", region="us-east-1")
        )
    return pc.Index(SHARED_COMPANY_INDEX)

async def process_single_file_async(org_namespace: str, file_name: str, file_bytes: bytes, allowed: list, indexing_method: str = "Semantic") -> str:
    # Generate content-addressed tracking ID mapping
    doc_id = hashlib.sha256(file_bytes).hexdigest()
    
    # Check relational ledger state context
    state, old_doc_id = db.check_document_state(org_namespace, file_name, doc_id)
    
    if state == "DUPLICATE":
        return f"Skipped '{file_name}': Match already exists in this namespace."
        
    index_obj = init_central_pinecone_index()
    
    # If the file has changed, execute an explicit, surgical deletion sequence
    if state == "UPDATE":
        try:
            # Query ledger for old chunk IDs linked to this filename
            old_chunk_ids, _ = db.get_chunks_for_deletion(org_namespace, file_name)
            if old_chunk_ids:
                index_obj.delete(ids=old_chunk_ids, namespace=org_namespace)
                db.clear_ledger_records(chunk_ids=old_chunk_ids, doc_ids=[old_doc_id], full_delete=True)
        except Exception as purge_err:
            print(f"Non-blocking Update Purge Warning for {file_name}: {str(purge_err)}")

    # 🚨 FIXED BUG: Generate unique file paths to prevent race conditions during async batching
    temp_dir = "temp_uploads"
    os.makedirs(temp_dir, exist_ok=True)
    unique_filename = f"{uuid.uuid4().hex}_{file_name}"
    temp_path = os.path.join(temp_dir, unique_filename)
    
    with open(temp_path, "wb") as f:
        f.write(file_bytes)
        
    try:
        raw_docs = await advanced_parser_async(file_name, file_bytes, temp_path)
        
        for doc in raw_docs:
            doc.metadata["allowed_roles"] = allowed
            doc.excluded_llm_metadata_keys = ["allowed_roles"]
            doc.metadata_template = "[Document Source: {key} = {value}]"
            
        splitter = SentenceSplitter(chunk_size=400, chunk_overlap=30)
        nodes = splitter.get_nodes_from_documents(raw_docs)
        
        chunks_to_register = []
        for idx, node in enumerate(nodes):
            p_num = node.metadata.get("page_number", 1)
            node.id_ = f"{doc_id}#c{idx}"
            node.relationships.pop(NodeRelationship.SOURCE, None)  # stops PineconeVectorStore.add() from prefixing a random ref_doc_id
            chunks_to_register.append({
                "chunk_id": node.id_,
                "page_number": p_num
            })
            
        # --- ENABLE HYBRID IF SELECTED ---
        is_hybrid = (indexing_method == "Hybrid")
        vector_store = PineconeVectorStore(
            pinecone_index=index_obj, 
            namespace=org_namespace, 
            add_sparse_vector=is_hybrid
        )
        storage_context = StorageContext.from_defaults(vector_store=vector_store)
        
        VectorStoreIndex(nodes, storage_context=storage_context)
        
        # Atomically update SQL database metadata ledger entries
        db.commit_document_to_ledger(doc_id, file_name, org_namespace, allowed, chunks_to_register, indexing_method)
        
        action_verb = "updated" if state == "UPDATE" else "processed"
        return f"Successfully {action_verb} '{file_name}' ({len(nodes)} chunks embedded via {indexing_method} logic)."
        
    except Exception as e:
        return f"Failed processing '{file_name}': {str(e)}"
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)

def delete_document_data(org_namespace: str, file_name: str, specific_pages: List[int] = None) -> str:
    """Production-grade surgical deletion matching exact vector chunk IDs via SQL records."""
    try:
        # Fetch the explicit vector chunk tracking strings from the ledger
        target_chunk_ids, associated_doc_ids = db.get_chunks_for_deletion(org_namespace, file_name, specific_pages)
        
        if not target_chunk_ids:
            return f"No active data vectors found matching '{file_name}' inside this namespace partition."
            
        index_obj = init_central_pinecone_index()
        
        # Surgically delete the exact list of vector IDs from Pinecone
        index_obj.delete(ids=target_chunk_ids, namespace=org_namespace)
        
        # Update the relational ledger
        is_full_delete = specific_pages is None
        db.clear_ledger_records(chunk_ids=target_chunk_ids, doc_ids=associated_doc_ids, full_delete=is_full_delete)
        
        if specific_pages:
            return f"Successfully removed pages {specific_pages} of '{file_name}' from the index store cluster."
        return f"Successfully purged '{file_name}' entirely from the enterprise knowledge cluster."
        
    except Exception as e:
        return f"Surgical Deletion Pipeline Error: {str(e)}"

# --- NEW: Accepts indexing_method from the UI ---
async def process_batch_files_async(org_namespace: str, uploaded_files_list, target_audience: str, indexing_method: str = "Semantic") -> List[str]:
    if target_audience == "Employees Only":
        allowed = ["employee", "manager", "ceo"]
    elif target_audience == "Clients Only":
        allowed = ["client", "manager", "ceo"]
    else:
        allowed = ["manager", "ceo"]

    tasks = [
        process_single_file_async(org_namespace, file.name, file.getvalue(), allowed, indexing_method)
        for file in uploaded_files_list
    ]
    return await asyncio.gather(*tasks)

# --- NEW: Dynamic Search Mode Routing ---
def query_secure_namespace(org_namespace: str, user_role: str, query: str, search_mode: str = "Semantic"):
    # 🚨 FIXED BUG: Changed "$eq" to "$in" to correctly filter list/array structures
    access_filter = {"allowed_roles": {"$in": [user_role.lower()]}}
    index_obj = init_central_pinecone_index()
    
    is_hybrid = (search_mode == "Hybrid")
    
    vector_store = PineconeVectorStore(
        pinecone_index=index_obj, 
        namespace=org_namespace, 
        add_sparse_vector=is_hybrid
    )
    
    index = VectorStoreIndex.from_vector_store(
        vector_store=vector_store,
        embed_model=Settings.embed_model
    )
    
    # Dynamically inject Hybrid vs Semantic Retriever kwargs
    retriever = index.as_retriever(
        similarity_top_k=8, 
        vector_store_query_mode="hybrid" if is_hybrid else "default",
        alpha=0.5 if is_hybrid else None, # Balances sparse/dense 50/50
        vector_store_kwargs={"filter": access_filter}
    )
    
    reranker = LLMRerank(llm=Settings.llm, top_n=3)
    
    query_engine = RetrieverQueryEngine.from_args(
        retriever=retriever, 
        node_postprocessors=[reranker]
    )
    return query_engine.query(query)