import os
import re
import hashlib
import json
import psycopg2
from typing import Tuple, List, Dict, Optional

# Helper function to establish a connection pool/session
def get_db_connection():
    return psycopg2.connect(os.environ.get("DATABASE_URL"))

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 1. User Authentication Registry
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            username TEXT PRIMARY KEY,
            password_hash TEXT NOT NULL,
            salt TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'employee',
            org_namespace TEXT NOT NULL
        )
    """)
    
    # 2. Production Document Meta-Ledger
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS documents (
            doc_id TEXT PRIMARY KEY,
            file_name TEXT NOT NULL,
            org_namespace TEXT NOT NULL,
            allowed_roles TEXT NOT NULL,
            indexing_method TEXT DEFAULT 'Semantic',
            uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # In PostgreSQL 11+, we can elegantly add columns if they don't exist
    cursor.execute("ALTER TABLE documents ADD COLUMN IF NOT EXISTS indexing_method TEXT DEFAULT 'Semantic'")
    
    # 3. Granular Vector Chunk ID Tracker
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS document_chunks (
            chunk_id TEXT PRIMARY KEY,
            doc_id TEXT NOT NULL,
            page_number INTEGER NOT NULL,
            FOREIGN KEY (doc_id) REFERENCES documents(doc_id) ON DELETE CASCADE
        )
    """)
    
    conn.commit()
    cursor.close()
    conn.close()

# --- DOCUMENT LEDGER DATABASE METRICS ---

def check_document_state(org_namespace: str, file_name: str, doc_id: str) -> Tuple[str, Optional[str]]:
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Exact duplicate check
    cursor.execute(
        "SELECT doc_id FROM documents WHERE org_namespace = %s AND file_name = %s AND doc_id = %s", 
        (org_namespace, file_name, doc_id)
    )
    if cursor.fetchone():
        cursor.close()
        conn.close()
        return "DUPLICATE", None

    # Version tracking update check
    cursor.execute(
        "SELECT doc_id FROM documents WHERE org_namespace = %s AND file_name = %s", 
        (org_namespace, file_name)
    )
    row = cursor.fetchone()
    cursor.close()
    conn.close()
    
    if row:
        return "UPDATE", row[0]
    return "NEW", None

def commit_document_to_ledger(doc_id: str, file_name: str, org_namespace: str, allowed_roles: List[str], chunks: List[Dict], indexing_method: str = "Semantic"):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        # PostgreSQL Upsert Logic (ON CONFLICT)
        cursor.execute("""
            INSERT INTO documents (doc_id, file_name, org_namespace, allowed_roles, indexing_method)
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (doc_id) DO UPDATE 
            SET file_name = EXCLUDED.file_name, 
                org_namespace = EXCLUDED.org_namespace, 
                allowed_roles = EXCLUDED.allowed_roles, 
                indexing_method = EXCLUDED.indexing_method
        """, (doc_id, file_name, org_namespace, json.dumps(allowed_roles), indexing_method))
        
        for chunk in chunks:
            cursor.execute("""
                INSERT INTO document_chunks (chunk_id, doc_id, page_number)
                VALUES (%s, %s, %s)
                ON CONFLICT (chunk_id) DO UPDATE 
                SET doc_id = EXCLUDED.doc_id, 
                    page_number = EXCLUDED.page_number
            """, (chunk["chunk_id"], doc_id, chunk["page_number"]))
            
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        cursor.close()
        conn.close()

def get_chunks_for_deletion(org_namespace: str, file_name: str, specific_pages: List[int] = None) -> Tuple[List[str], List[str]]:
    conn = get_db_connection()
    cursor = conn.cursor()
    
    if specific_pages:
        placeholders = ",".join("%s" for _ in specific_pages)
        query = f"""
            SELECT c.chunk_id, d.doc_id FROM document_chunks c
            JOIN documents d ON c.doc_id = d.doc_id
            WHERE d.org_namespace = %s AND d.file_name = %s AND c.page_number IN ({placeholders})
        """
        cursor.execute(query, [org_namespace, file_name] + specific_pages)
    else:
        query = """
            SELECT c.chunk_id, d.doc_id FROM document_chunks c
            JOIN documents d ON c.doc_id = d.doc_id
            WHERE d.org_namespace = %s AND d.file_name = %s
        """
        cursor.execute(query, (org_namespace, file_name))
        
    rows = cursor.fetchall()
    cursor.close()
    conn.close()
    
    chunk_ids = [row[0] for row in rows]
    doc_ids = list(set([row[1] for row in rows]))
    return chunk_ids, doc_ids

def clear_ledger_records(chunk_ids: List[str], doc_ids: List[str] = None, full_delete: bool = False):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        if chunk_ids:
            placeholders = ",".join("%s" for _ in chunk_ids)
            cursor.execute(f"DELETE FROM document_chunks WHERE chunk_id IN ({placeholders})", chunk_ids)
            
        if full_delete and doc_ids:
            placeholders = ",".join("%s" for _ in doc_ids)
            cursor.execute(f"DELETE FROM documents WHERE doc_id IN ({placeholders})", doc_ids)
            
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        cursor.close()
        conn.close()

# --- USER INFRASTRUCTURE AND ACCESS METHODS ---

def hash_password(password: str, salt: str = None) -> Tuple[str, str]:
    if not salt:
        salt = os.urandom(16).hex()
    hashed = hashlib.sha256((password + salt).encode('utf-8')).hexdigest()
    return hashed, salt

def register_user(username: str, password: str, role: str, org_name: str) -> Tuple[bool, str]:
    username = username.strip().lower()
    org_name = org_name.strip().lower()
    
    if not username or not password or not org_name:
        return False, "All initialization fields must be provided."
    
    org_namespace = re.sub(r'[^a-zA-Z0-9-]', '', org_name)
    if not org_namespace:
        return False, "Invalid organization name structure."

    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT username FROM users WHERE username = %s", (username,))
        if cursor.fetchone():
            return False, "Account user handle already exists."
        
        hashed_pw, salt = hash_password(password)
        cursor.execute("""
            INSERT INTO users (username, password_hash, salt, role, org_namespace) 
            VALUES (%s, %s, %s, %s, %s)
        """, (username, hashed_pw, salt, role.lower(), org_namespace))
        conn.commit()
        return True, f"Registration complete! Assigned Namespace: '{org_namespace}'."
    except Exception as e:
        return False, f"Database exception: {str(e)}"
    finally:
        cursor.close()
        conn.close()

def authenticate_user(username: str, password: str) -> Tuple[bool, dict]:
    username = username.strip().lower()
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT password_hash, salt, role, org_namespace FROM users WHERE username = %s", (username,))
    row = cursor.fetchone()
    cursor.close()
    conn.close()
    
    if row:
        stored_hash, salt, role, org_namespace = row
        computed_hash, _ = hash_password(password, salt)
        if computed_hash == stored_hash:
            return True, {"username": username, "role": role, "org_namespace": org_namespace}
    return False, {}

def get_namespace_documents(org_namespace: str) -> List[dict]:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT file_name, uploaded_at, allowed_roles, indexing_method 
        FROM documents 
        WHERE org_namespace = %s 
        ORDER BY uploaded_at DESC
    """, (org_namespace,))
    rows = cursor.fetchall()
    cursor.close()
    conn.close()
    
    return [{
        "file_name": r[0], 
        "uploaded_at": r[1], 
        "allowed_roles": json.loads(r[2]),
        "indexing_method": r[3] if len(r) > 3 and r[3] else "Semantic"
    } for r in rows]

init_db()