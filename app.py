import os
import json
from dotenv import load_dotenv
load_dotenv()

import streamlit as st
import pandas as pd
import nest_asyncio
import asyncio

# Kept all your original backend module imports[cite: 1]
import database_manager as db
import vector_pipeline as pipeline
import eval_pipeline

nest_asyncio.apply()

# --- PAGE CONFIGURATION ---
st.set_page_config(
    page_title="Enterprise Knowledge Hub",
    page_icon="✨",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- MASSIVE CSS OVERHAUL (THE UI MAGIC) ---
st.markdown("""
<style>
    /* Global App Background & Typography */
    .stApp {
        background-color: #F8FAFC;
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    }
    
    /* Center Content Container */
    .main .block-container {
        padding-top: 2rem;
        padding-bottom: 4rem;
        max-width: 1100px;
    }
    
    /* Sleek Typography */
    h1, h2, h3 {
        color: #0F172A !important;
        font-weight: 800 !important;
        letter-spacing: -0.5px;
    }
    p, .stMarkdown {
        color: #334155;
    }
    
    /* Modern Floating Cards for st.container(border=True) */
    [data-testid="stVerticalBlockBorderWrapper"] {
        background-color: #FFFFFF;
        border: 1px solid #E2E8F0 !important;
        border-radius: 12px !important;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05), 0 2px 4px -2px rgba(0, 0, 0, 0.05) !important;
        padding: 1rem;
        transition: transform 0.2s ease, box-shadow 0.2s ease;
    }
    
    /* Vibrant Primary Buttons */
    .stButton>button[kind="primary"] {
        background: linear-gradient(135deg, #2563EB 0%, #1D4ED8 100%) !important;
        border: none !important;
        border-radius: 8px !important;
        padding: 0.6rem 1.2rem !important;
        transition: all 0.3s ease !important;
        box-shadow: 0 4px 6px rgba(37, 99, 235, 0.2) !important;
    }

    /* Force white text on the button and its inner elements */
    .stButton>button[kind="primary"],
    .stButton>button[kind="primary"] p,
    .stButton>button[kind="primary"] div {
        color: #FFFFFF !important;
        font-weight: 600 !important;
    }
    
    .stButton>button[kind="primary"]:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 12px rgba(37, 99, 235, 0.3) !important;
    }

    /* Secondary Buttons */
    .stButton>button[kind="secondary"] {
        border-radius: 8px !important;
        border: 1px solid #CBD5E1 !important;
        font-weight: 600 !important;
        color: #475569 !important;
    }
    
    /* Clean Text Inputs */
    .stTextInput>div>div>input {
        border-radius: 8px !important;
        border: 1px solid #CBD5E1 !important;
        padding: 0.75rem !important;
        box-shadow: inset 0 1px 2px rgba(0, 0, 0, 0.02);
    }
    .stTextInput>div>div>input:focus {
        border-color: #2563EB !important;
        box-shadow: 0 0 0 2px rgba(37, 99, 235, 0.2) !important;
    }
    
    /* Styled Metric Cards */
    [data-testid="stMetricValue"] {
        font-size: 2.2rem !important;
        font-weight: 800 !important;
        color: #2563EB !important;
    }
    [data-testid="stMetricLabel"] {
        font-size: 0.95rem !important;
        color: #64748B !important;
        font-weight: 600 !important;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }

    /* Badges */
    .role-badge {
        display: inline-block;
        padding: 4px 12px;
        font-size: 0.75rem;
        font-weight: 700;
        border-radius: 20px;
        color: #2563EB;
        background-color: #DBEAFE;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        border: 1px solid #BFDBFE;
    }
    
    /* Refined Expander (For AI Sources) */
    .streamlit-expanderHeader {
        background-color: #F8FAFC !important;
        border-radius: 8px !important;
        font-weight: 600 !important;
        color: #1E293B !important;
    }
</style>
""", unsafe_allow_html=True)

# --- SESSION STATE INITIALIZATION ---
# Preserved your original session states for auth and logging[cite: 1]
if "user_info" not in st.session_state:
    st.session_state.user_info = None

if "last_ingestion_logs" not in st.session_state:
    st.session_state.last_ingestion_logs = None

if "last_deletion_msg" not in st.session_state:
    st.session_state.last_deletion_msg = None


# =====================================================================
# 🔐 AUTHENTICATION VIEW (Sleek Centered Portal)
# =====================================================================
if st.session_state.user_info is None:
    # Use spacing to push the login card down to the center
    st.write("")
    st.write("")
    st.write("")
    
    # Restructured into a tighter, central column layout
    _, center_col, _ = st.columns([1.5, 2, 1.5])
    
    with center_col:
        st.markdown("<h1 style='text-align: center; font-size: 2.5rem; margin-bottom: 0;'>Nexus Hub</h1>", unsafe_allow_html=True)
        st.markdown("<p style='text-align: center; color: #64748B; margin-bottom: 2rem;'>Secure Enterprise Knowledge Management</p>", unsafe_allow_html=True)

        with st.container(border=True):
            tab_login, tab_register = st.tabs(["Secure Login", "Create Account"])
            
            with tab_login:
                st.write("")
                with st.form("login_form", clear_on_submit=False):
                    l_user = st.text_input("Corporate ID / Username", placeholder="e.g., alex_smith", key="l_uid")
                    l_pass = st.text_input("Password", type="password", placeholder="••••••••", key="l_pwd")
                    st.write("")
                    submit_login = st.form_submit_button("Authenticate Access", use_container_width=True, type="primary")
                    
                if submit_login:
                    if not l_user.strip() or not l_pass.strip():
                        st.error("Authentication failed: Missing credentials.")
                    else:
                        success, info = db.authenticate_user(l_user, l_pass)
                        if success:
                            st.session_state.user_info = info
                            st.success("Connection established. Redirecting...")
                            st.rerun()
                        else:
                            st.error("Invalid credentials. Please contact IT support if the issue persists.")

            with tab_register:
                st.write("")
                with st.form("registration_form"):
                    r_user = st.text_input("Preferred Username", key="r_uid")
                    r_pass = st.text_input("Password", type="password", key="r_pwd")
                    r_org = st.text_input("Organization Workspace", key="r_org")
                    r_role = st.selectbox(
                        "Requested Role Level",
                        ["Employee", "Client", "Manager", "CEO"]
                    )
                    st.write("")
                    submit_registration = st.form_submit_button("Provision Account", use_container_width=True)
                    
                if submit_registration:
                    if not r_user.strip() or not r_pass.strip() or not r_org.strip():
                        st.error("All fields are required for provisioning.")
                    else:
                        normalized_role = "manager" if r_role.lower() in ["manager", "ceo"] else r_role.lower()
                        status, feedback = db.register_user(r_user, r_pass, normalized_role, r_org)
                        if status:
                            st.success("Account provisioned successfully. You may now login.")
                        else:
                            st.error(feedback)

# =====================================================================
# 🚀 MAIN APPLICATION WORKSPACE
# =====================================================================
else:
    user_context = st.session_state.user_info
    user_role = user_context['role'].lower()
    is_admin = user_role in ["manager", "ceo"]

    # --- ENHANCED SIDEBAR CONTROL PANEL ---
    with st.sidebar:
        st.markdown("<h2 style='text-align: center;'>Nexus</h2>", unsafe_allow_html=True)
        st.markdown("---")
        
        st.markdown("<p style='color: #64748B; font-size: 0.8rem; font-weight: 700; margin-bottom: 0;'>ACTIVE PROFILE</p>", unsafe_allow_html=True)
        st.markdown(f"**{user_context['username']}**")
        st.markdown(f"<span class='role-badge'>{user_context['role']}</span>", unsafe_allow_html=True)
        
        st.write("")
        st.write("")
        
        st.markdown("<p style='color: #64748B; font-size: 0.8rem; font-weight: 700; margin-bottom: 0;'>WORKSPACE DATA</p>", unsafe_allow_html=True)
        st.markdown(f"**{user_context['org_namespace'].capitalize()} Environment**")
        st.caption(f"Index Node: `{pipeline.SHARED_COMPANY_INDEX}`")
        
        st.markdown("---")
        if st.button("Secure Logout", use_container_width=True):
            st.session_state.user_info = None
            st.session_state.last_ingestion_logs = None
            st.session_state.last_deletion_msg = None
            st.rerun()

    # --- MAIN TOP HEADER ---
    col_head, _ = st.columns([3, 1])
    with col_head:
        st.markdown(f"<h1>{user_context['org_namespace'].capitalize()} Workspace</h1>", unsafe_allow_html=True)
        st.markdown("<p style='font-size: 1.1rem;'>Ask questions, manage documents, and monitor AI analytics.</p>", unsafe_allow_html=True)
    st.write("")

    # --- NAVIGATION TABS ---
    tab_search, tab_ingest, tab_eval = st.tabs([
        "🔍 Intelligence Search", 
        "📂 Data Library", 
        "📊 System Analytics"
    ])

    # =================================================================
    # TAB 1: SEARCH & ASK AI (Hero Layout)
    # =================================================================
    with tab_search:
        st.write("")
        
        # Wrapped the search in a prominent central card
        with st.container(border=True):
            st.markdown("### Ask the Knowledge Base")
            
            search_mode = st.radio(
                "Retrieval Strategy:", 
                ["Semantic", "Hybrid"], 
                horizontal=True,
                label_visibility="collapsed"
            )
            
            search_prompt = st.text_input(
                "Search",
                placeholder="e.g., What is our remote work policy according to the latest handbook?",
                label_visibility="collapsed",
                key="user_search_input"
            )
            
            # Use columns to strictly right-align the search button
            _, btn_col = st.columns([4, 1])
            with btn_col:
                submit_query = st.button("Extract Insight", type="primary", use_container_width=True)

        if submit_query and search_prompt:
            st.write("")
            with st.spinner(f"Running {search_mode.lower()} analysis across {user_context['org_namespace']} index..."):
                try:
                    # Kept your original querying logic[cite: 1]
                    response_payload = pipeline.query_secure_namespace(
                        org_namespace=user_context['org_namespace'],
                        user_role=user_context['role'],
                        query=search_prompt,
                        search_mode=search_mode
                    )
                    
                    st.markdown("### Synthesized Response")
                    # Used a styled container instead of standard info box for a premium look
                    with st.container(border=True):
                        st.markdown(f"<div style='font-size: 1.1rem; line-height: 1.6;'>{response_payload.response}</div>", unsafe_allow_html=True)
                    
                    st.write("")
                    st.markdown("#### Source Citations")
                    if not response_payload.source_nodes:
                        st.warning("No matching document passages were found for this question.")
                    else:
                        for idx, matched_node in enumerate(response_payload.source_nodes, start=1):
                            node_meta = matched_node.node.metadata
                            file_name = node_meta.get("file_name", "Unknown Document")
                            page_num = node_meta.get("page_number", "N/A")
                            score = round(matched_node.score, 4) if matched_node.score else "N/A"
                            
                            with st.expander(f"📄 {file_name} (Page {page_num}) — Relevance: {score}"):
                                st.markdown(f"**Chunk ID:** `{matched_node.node.id_}`")
                                st.json(node_meta)
                                st.text(matched_node.node.get_content())
                                
                except Exception as query_err:
                    st.error(f"Error executing search query: {str(query_err)}")

    # =================================================================
    # TAB 2: DOCUMENT LIBRARY & MANAGEMENT
    # =================================================================
    with tab_ingest:
        st.write("")
        st.markdown("### Active Document Assets")
        
        # Kept your existing database fetch logic[cite: 1]
        all_docs = db.get_namespace_documents(user_context['org_namespace'])
        visible_docs = []
        
        for doc in all_docs:
            if is_admin or user_role in doc['allowed_roles']:
                idx_method = doc.get("indexing_method", "Semantic")
                visible_docs.append({
                    "File Name": doc["file_name"],
                    "Engine": idx_method,
                    "Timestamp": doc["uploaded_at"],
                    "Clearance Level": ", ".join([role.capitalize() for role in doc["allowed_roles"]])
                })
        
        if not visible_docs:
            st.info("The knowledge repository is currently empty.")
        else:
            with st.container(border=True):
                df_docs = pd.DataFrame(visible_docs)
                st.dataframe(df_docs, use_container_width=True, hide_index=True)

        st.write("")
        
        if not is_admin:
            st.warning("🔒 Administrative clearance required to modify repository assets.")
        else:
            col_add, col_remove = st.columns([1, 1])
            
            # SECTION A: UPLOAD
            with col_add:
                st.markdown("#### Upload Assets")
                with st.container(border=True):
                    with st.form("ingestion_form"):
                        target_audience = st.selectbox(
                            "Clearance Requirement",
                            ["Employees Only", "Clients Only", "Management Only"]
                        )
                        indexing_method = st.radio(
                            "Processing Engine",
                            ["Semantic", "Hybrid"],
                            horizontal=True
                        )
                            
                        uploaded_files = st.file_uploader(
                            "Drop files here", 
                            type=["txt", "csv", "xlsx", "pdf", "docx"],
                            accept_multiple_files=True
                        )
                        st.write("")
                        submit_ingest = st.form_submit_button("Process & Index Assets", type="primary", use_container_width=True)
                    
                if submit_ingest:
                    if not uploaded_files:
                        st.warning("Select files to proceed.")
                    else:
                        st.session_state.last_deletion_msg = None
                        with st.spinner("Processing documents into vector space..."):
                            logs = asyncio.run(pipeline.process_batch_files_async(
                                org_namespace=user_context['org_namespace'],
                                uploaded_files_list=uploaded_files,
                                target_audience=target_audience,
                                indexing_method=indexing_method
                            ))
                            st.session_state.last_ingestion_logs = logs
                            st.rerun()
            
            # SECTION B: REMOVAL
            with col_remove:
                st.markdown("#### Purge Assets")
                with st.container(border=True):
                    target_file = st.text_input("Exact Filename", placeholder="e.g., handbook.pdf", key="del_f_target")
                    target_pages = st.text_input("Specific Pages (Optional CSV)", placeholder="e.g., 2, 5, 12", key="del_p_target")
                    st.write("")
                    
                    if st.button("Execute Data Purge", type="secondary", use_container_width=True):
                        if not target_file.strip():
                            st.warning("Target filename is required.")
                        else:
                            parsed_pages = None
                            if target_pages.strip():
                                try:
                                    parsed_pages = [int(p.strip()) for p in target_pages.split(",") if p.strip()]
                                except ValueError:
                                    st.error("Invalid page format.")
                                    st.stop()
                                    
                            st.session_state.last_ingestion_logs = None
                            with st.spinner("Purging records..."):
                                deletion_report = pipeline.delete_document_data(
                                    org_namespace=user_context['org_namespace'],
                                    file_name=target_file.strip(),
                                    specific_pages=parsed_pages
                                )
                                st.session_state.last_deletion_msg = deletion_report
                                st.rerun()

            # --- STATUS DISPLAYS (Moved to bottom of tab for cleaner layout) ---
            if st.session_state.last_ingestion_logs:
                st.write("")
                st.markdown("##### Processing Logs")
                for log in st.session_state.last_ingestion_logs:
                    if "Skipped" in log:
                        st.warning(log)
                    elif "Failed" in log:
                        st.error(log)
                    else:
                        st.success(log)
                if st.button("Clear Logs", key="dismiss_ingest_logs"):
                    st.session_state.last_ingestion_logs = None
                    st.rerun()

            if st.session_state.last_deletion_msg:
                st.write("")
                msg = st.session_state.last_deletion_msg
                if "Successfully" in msg:
                    st.success(msg)
                else:
                    st.error(msg)
                if st.button("Clear Logs", key="dismiss_del_msg"):
                    st.session_state.last_deletion_msg = None
                    st.rerun()

    # =================================================================
    # TAB 3: SYSTEM EVALUATION & BENCHMARKING
    # =================================================================
    with tab_eval:
        st.write("")
        st.markdown("### AI Model Telemetry")
        
        if not is_admin:
            st.error("🔒 Telemetry access restricted to administrative personnel.")
        else:
            with st.container(border=True):
                eval_col1, eval_col2, eval_col3 = st.columns([2, 1, 1])
                with eval_col1:
                    uploaded_eval_file = st.file_uploader("Upload Benchmark Dataset (.json)", type=["json"], key="eval_uploader")
                with eval_col2:
                    eval_search_mode = st.radio("Test Engine", ["Semantic", "Hybrid"], key="eval_mode")
                with eval_col3:
                    st.write("") 
                    st.write("") 
                    submit_eval = st.button("Run Diagnostics", type="primary", use_container_width=True)
            
            if submit_eval:
                if uploaded_eval_file is None:
                    st.warning("Benchmark dataset missing.")
                else:
                    with st.spinner("Executing telemetry suite. This may take a few moments..."):
                        try:
                            # Kept your original evaluation wrapping logic[cite: 1]
                            def benchmark_query_wrapper(org_namespace, user_role, query):
                                return pipeline.query_secure_namespace(
                                    org_namespace=org_namespace, 
                                    user_role=user_role, 
                                    query=query, 
                                    search_mode=eval_search_mode
                                )
                            
                            report_df = eval_pipeline.run_uploaded_evaluation_workflow(
                                org_namespace=user_context['org_namespace'],
                                user_role=user_role,
                                json_bytes=uploaded_eval_file.getvalue(),
                                query_pipeline_func=benchmark_query_wrapper
                            )
                            
                            st.write("")
                            st.markdown("### Telemetry Results")
                            
                            # Transformed metrics into a card layout
                            with st.container(border=True):
                                m1, m2, m3, m4 = st.columns(4)
                                m1.metric("Faithfulness", f"{round(report_df['faithfulness'].mean(), 2)}")
                                m2.metric("Relevancy", f"{round(report_df['answer_relevancy'].mean(), 2)}")
                                m3.metric("Precision", f"{round(report_df['context_precision'].mean(), 2)}")
                                m4.metric("Recall", f"{round(report_df['context_recall'].mean(), 2)}")
                            
                            st.write("")
                            st.markdown("#### Diagnostic Logs")
                            st.dataframe(report_df, use_container_width=True)
                            
                        except Exception as eval_err:
                            st.error(f"Telemetry failure: {str(eval_err)}")