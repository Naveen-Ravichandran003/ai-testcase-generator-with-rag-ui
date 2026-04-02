import streamlit as st
import requests
import time
from datetime import datetime
import csv
import io
import re
import pandas as pd
import os
from fpdf import FPDF

# --- Page Config ---
st.set_page_config(
    page_title="AI Test Case Generator | RAG + Langflow",
    page_icon="🧪",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- Custom CSS ---
st.markdown("""
<style>
    /* Import Google Font */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

    /* Global styles */
    .stApp {
        font-family: 'Inter', sans-serif;
    }

    /* Hero banner */
    .hero-banner {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 2rem 2.5rem;
        border-radius: 16px;
        margin-bottom: 2rem;
        color: white;
        box-shadow: 0 8px 32px rgba(102, 126, 234, 0.3);
        position: relative;
        overflow: hidden;
    }
    .hero-banner::before {
        content: '';
        position: absolute;
        top: -50%;
        right: -20%;
        width: 300px;
        height: 300px;
        background: rgba(255,255,255,0.05);
        border-radius: 50%;
    }
    .hero-banner h1 {
        font-size: 2rem;
        font-weight: 700;
        margin: 0 0 0.5rem 0;
        color: white;
    }
    .hero-banner p {
        font-size: 1.05rem;
        opacity: 0.9;
        margin: 0;
        font-weight: 300;
    }

    /* Stat cards */
    .stat-card {
        background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
        padding: 1.2rem 1.5rem;
        border-radius: 12px;
        text-align: center;
        border: 1px solid rgba(255,255,255,0.2);
        box-shadow: 0 4px 15px rgba(0,0,0,0.05);
        transition: transform 0.3s ease, box-shadow 0.3s ease;
    }
    .stat-card:hover {
        transform: translateY(-3px);
        box-shadow: 0 8px 25px rgba(0,0,0,0.1);
    }
    .stat-card h3 {
        font-size: 2rem;
        font-weight: 700;
        color: #667eea;
        margin: 0;
    }
    .stat-card p {
        font-size: 0.85rem;
        color: #555;
        margin: 0.3rem 0 0 0;
        font-weight: 500;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }

    /* Sidebar styles */
    section[data-testid="stSidebar"] {
        background: linear-gradient(180deg, #1a1a2e 0%, #16213e 100%);
    }
    section[data-testid="stSidebar"] .stMarkdown h1,
    section[data-testid="stSidebar"] .stMarkdown h2,
    section[data-testid="stSidebar"] .stMarkdown h3,
    section[data-testid="stSidebar"] .stMarkdown p,
    section[data-testid="stSidebar"] .stMarkdown li,
    section[data-testid="stSidebar"] label,
    section[data-testid="stSidebar"] label p {
        color: #e0e0e0 !important;
    }

    /* Connection status badges */
    .conn-status {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        padding: 6px 14px;
        border-radius: 20px;
        font-size: 0.8rem;
        font-weight: 600;
        letter-spacing: 0.3px;
    }
    .conn-ok {
        background: rgba(56, 239, 125, 0.15);
        color: #38ef7d;
        border: 1px solid rgba(56, 239, 125, 0.3);
    }
    .conn-err {
        background: rgba(255, 87, 87, 0.15);
        color: #ff5757;
        border: 1px solid rgba(255, 87, 87, 0.3);
    }
    .conn-pending {
        background: rgba(255, 193, 7, 0.15);
        color: #ffc107;
        border: 1px solid rgba(255, 193, 7, 0.3);
    }

    /* Success box */
    .success-box {
        background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%);
        padding: 1.2rem 1.5rem;
        border-radius: 12px;
        color: white;
        font-weight: 600;
        font-size: 1.05rem;
        margin: 1rem 0;
        box-shadow: 0 4px 15px rgba(17, 153, 142, 0.3);
    }

    /* Error box */
    .error-box {
        background: linear-gradient(135deg, #eb3349 0%, #f45c43 100%);
        padding: 1.2rem 1.5rem;
        border-radius: 12px;
        color: white;
        font-weight: 600;
        font-size: 1rem;
        margin: 1rem 0;
        box-shadow: 0 4px 15px rgba(235, 51, 73, 0.3);
    }

    /* Button styling */
    .stButton > button {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%) !important;
        color: white !important;
        border: none !important;
        padding: 0.75rem 2.5rem !important;
        border-radius: 10px !important;
        font-weight: 600 !important;
        font-size: 1rem !important;
        letter-spacing: 0.5px;
        box-shadow: 0 4px 15px rgba(102, 126, 234, 0.4) !important;
        transition: all 0.3s ease !important;
    }
    .stButton > button:hover {
        transform: translateY(-2px) !important;
        box-shadow: 0 6px 20px rgba(102, 126, 234, 0.6) !important;
    }

    /* Download button */
    .stDownloadButton > button {
        background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%) !important;
        color: white !important;
        border: none !important;
        border-radius: 10px !important;
        font-weight: 600 !important;
        box-shadow: 0 4px 15px rgba(17, 153, 142, 0.3) !important;
    }

    /* Text area */
    .stTextArea textarea {
        border-radius: 12px !important;
        border: 2px solid #e0e0e0 !important;
        font-family: 'Inter', sans-serif !important;
        font-size: 0.95rem !important;
        transition: border-color 0.3s ease !important;
    }
    .stTextArea textarea:focus {
        border-color: #667eea !important;
        box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.15) !important;
    }

    /* Code block */
    .stCode {
        border-radius: 12px !important;
        border: 1px solid #e0e0e0 !important;
    }

    /* Progress text */
    .progress-text {
        color: #667eea;
        font-weight: 600;
        font-size: 0.95rem;
    }

    /* Batch progress card */
    .batch-card {
        background: linear-gradient(135deg, #232526 0%, #414345 100%);
        padding: 0.8rem 1.2rem;
        border-radius: 10px;
        color: #e0e0e0;
        font-size: 0.85rem;
        margin: 0.3rem 0;
        border-left: 4px solid #667eea;
    }
    .batch-card strong {
        color: #667eea;
    }

    /* Footer */
    .footer {
        text-align: center;
        
        padding: 2rem 0 1rem 0;
        color: #999;
        font-size: 0.8rem;
        border-top: 1px solid #eee;
        margin-top: 3rem;
    }

    /* Section headers */
    .section-header {
        background: linear-gradient(90deg, #667eea 0%, transparent 100%);
        padding: 2px 0;
        border-radius: 4px;
        margin: 1.5rem 0 1rem 0;
    }
</style>
""", unsafe_allow_html=True)


# =============================================
# LOAD DEFAULTS FROM BACKEND (from .env file)
# =============================================
@st.cache_data(ttl=300)
def load_backend_config():
    """Load default config from the FastAPI backend (which reads .env)."""
    try:
        resp = requests.get("http://localhost:8000/config", timeout=5)
        return resp.json()
    except Exception:
        return {
            "langflow_url": "http://localhost:7860",
            "flow_id": "",
            "api_key": "",
            "batch_size": 20,
        }


config = load_backend_config()

# Initialize session state from .env defaults (only once)
if "cfg_initialized" not in st.session_state:
    st.session_state.cfg_langflow_url = config.get("langflow_url", "http://localhost:7860")
    st.session_state.cfg_flow_id = config.get("flow_id", "")
    st.session_state.cfg_api_key = config.get("api_key", "")
    st.session_state.cfg_batch_size = config.get("batch_size", 20)
    st.session_state.cfg_initialized = True
    st.session_state.connection_status = "pending"


# =============================================
# SIDEBAR — Langflow Configuration (fully editable)
# =============================================
with st.sidebar:
    st.markdown("## 🔗 Langflow Connection")
    st.markdown(
        '<span style="color:#9ca3af;font-size:0.78rem;">'
        'All settings configurable — nothing is hardcoded</span>',
        unsafe_allow_html=True,
    )
    st.markdown("")

    langflow_url = st.text_input(
        "🌐 Langflow Base URL",
        value=st.session_state.cfg_langflow_url,
        help="The URL where your Langflow instance is running",
    )
    flow_id = st.text_input(
        "🆔 Flow ID (UUID)",
        value=st.session_state.cfg_flow_id,
        help="Open Langflow → click your flow → copy the UUID from the URL bar",
        placeholder="xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
    )
    api_key = st.text_input(
        "🔑 API Key",
        value=st.session_state.cfg_api_key,
        type="password",
        help="Your Langflow API key (optional if auth is disabled)",
    )

    # Update session state when user edits
    st.session_state.cfg_langflow_url = langflow_url
    st.session_state.cfg_flow_id = flow_id
    st.session_state.cfg_api_key = api_key

    # Connection test
    if st.button("🔌 Test Connection", use_container_width=True):
        if not flow_id.strip():
            st.error("⚠️ Enter a Flow ID first!")
        else:
            with st.spinner("Testing connection..."):
                try:
                    resp = requests.post(
                        "http://localhost:8000/test-connection",
                        json={
                            "langflow_url": langflow_url,
                            "flow_id": flow_id,
                            "api_key": api_key,
                        },
                        timeout=60,
                    )
                    result = resp.json()
                    if result["status"] == "connected":
                        st.session_state.connection_status = "connected"
                        st.session_state.flow_name = result.get("flow_name", "")
                        st.success(result["message"])
                    else:
                        st.session_state.connection_status = "error"
                        st.error(result["message"])
                except requests.exceptions.ConnectionError:
                    st.session_state.connection_status = "error"
                    st.error("❌ Cannot reach backend. Run: `uvicorn main:app --reload`")
                except Exception as e:
                    st.session_state.connection_status = "error"
                    st.error(f"❌ Error: {str(e)}")

    # Connection status badge
    status = st.session_state.get("connection_status", "pending")
    if status == "connected":
        flow_name = st.session_state.get("flow_name", "")
        st.markdown(
            f'<span class="conn-status conn-ok">🟢 Connected: {flow_name}</span>',
            unsafe_allow_html=True,
        )
    elif status == "error":
        st.markdown(
            '<span class="conn-status conn-err">🔴 Not Connected</span>',
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            '<span class="conn-status conn-pending">🟡 Not Tested</span>',
            unsafe_allow_html=True,
        )

    st.markdown("---")

    # --- Generation Settings ---
    st.markdown("## 📊 Generation Settings")

    test_count = st.number_input(
        "🔢 Number of Test Cases",
        min_value=10,
        max_value=1000,
        value=500,
        step=50,
        help="Total test cases to generate (in batches)",
    )

    batch_size = int(st.number_input(
        "📦 Batch Size",
        min_value=5,
        max_value=50,
        value=st.session_state.cfg_batch_size,
        step=5,
        help="Test cases per Langflow API call (lower = more reliable)",
    ))
    st.session_state.cfg_batch_size = batch_size

    batches_needed = (int(test_count) + batch_size - 1) // batch_size
    # Each batch: ~30–60s LLM + 2s inter-batch cooldown
    est_min = (batches_needed * 32) // 60
    est_max = (batches_needed * 62) // 60

    st.markdown(f"""
    **📈 Estimated:**
    - Batches: **{batches_needed}**
    - Time: **{est_min}–{est_max} min**
    - Dedup: **✅ Enabled**
    """)

    st.markdown("---")

    # --- Categories ---
    st.markdown("### 📋 Test Categories")
    categories = [
        "🟢 Happy Path", "🔴 Negative", "📐 Boundary",
        "🔒 Security", "⚡ Performance", "♿ Accessibility",
        "🔗 API/Integration", "🗄️ Data Validation",
        "⚠️ Error Handling", "🌐 Cross-Browser",
        "🔄 Session Mgmt", "🌍 i18n/L10n",
        "👥 Concurrency", "📱 Mobile", "🔙 Regression"
    ]
    st.markdown("\n".join([f"- {cat}" for cat in categories]))


# =============================================
# MAIN CONTENT
# =============================================

# --- Hero Banner ---
st.markdown("""
<div class="hero-banner">
    <h1>🧪 AI Test Case Generator</h1>
    <p>Powered by RAG + Langflow — Generate comprehensive, unique test cases from JIRA tickets or feature descriptions</p>
</div>
""", unsafe_allow_html=True)


# --- Stat Cards ---
col1, col2, col3, col4 = st.columns(4)
with col1:
    st.markdown(f"""
    <div class="stat-card">
        <h3>{test_count}</h3>
        <p>Test Cases</p>
    </div>
    """, unsafe_allow_html=True)
with col2:
    st.markdown(f"""
    <div class="stat-card">
        <h3>{batches_needed}</h3>
        <p>Batches</p>
    </div>
    """, unsafe_allow_html=True)
with col3:
    st.markdown(f"""
    <div class="stat-card">
        <h3>15</h3>
        <p>Categories</p>
    </div>
    """, unsafe_allow_html=True)
with col4:
    st.markdown(f"""
    <div class="stat-card">
        <h3>3</h3>
        <p>Dedup Layers</p>
    </div>
    """, unsafe_allow_html=True)

st.markdown("")


# --- Input Section ---
st.markdown("### 📝 Feature / Jira Input")
user_input = st.text_area(
    "Describe the feature or paste a Jira ticket description",
    height=180,
    placeholder="Enter the Jira User Story, Acceptance Criteria, or Technical Feature Requirements here to auto-generate comprehensive test cases...",
    label_visibility="collapsed",
)

# --- Generate & Clear Buttons ---
col_btn1, col_btn2, col_spacer = st.columns([1, 1, 2])
with col_btn1:
    generate_clicked = st.button("🚀 Generate Test Cases", use_container_width=True)
with col_btn2:
    clear_clicked = st.button("🗑️ Clear Results", use_container_width=True)

if clear_clicked:
    if "result_data" in st.session_state:
        del st.session_state.result_data
    st.rerun()


# =============================================
# TEST CASE PARSER
# =============================================
def parse_test_cases(raw_text: str) -> list[dict]:
    """Parse raw LLM output into structured test case dicts."""
    # Remove batch headers
    clean = re.sub(r'--- Batch \d+:.*?---\n?', '', raw_text, flags=re.IGNORECASE)
    clean = re.sub(r'Here are the.*?:\n?', '', clean, flags=re.IGNORECASE)

    # Split on test case boundaries
    blocks = re.split(
        r'\n(?=(?:\*\*)?Test Case \d+[:\s]|(?:ID|Test Case ID)[:\s]*TC)',
        clean,
    )

    results = []
    for block in blocks:
        block = block.strip()
        if not block or len(block) < 20:
            continue

        tc_id = re.search(r'(?:ID|Test Case ID)[:\s]*(TC-?\d+)', block, re.IGNORECASE)
        if not tc_id:
            tc_id = re.search(r'(TC-?\d{3})', block)
        title = re.search(r'Title[:\s]*\*{0,2}[:\s]*(.+)', block, re.IGNORECASE)
        desc = re.search(r'Description[:\s]*(.+)', block, re.IGNORECASE)
        prec = re.search(r'Preconditions?[:\s]*(.+)', block, re.IGNORECASE)
        expected = re.search(r'Expected Result[:\s]*(.+)', block, re.IGNORECASE)
        priority = re.search(r'Priority[:\s]*(.+)', block, re.IGNORECASE)
        test_type = re.search(r'Test Type[:\s]*(.+)', block, re.IGNORECASE)
        steps = re.search(
            r'Steps[:\s]*(.*?)(?=Expected Result|Priority|Test Type|$)',
            block, re.IGNORECASE | re.DOTALL,
        )

        if tc_id or title:
            results.append({
                "ID": tc_id.group(1).strip() if tc_id else "",
                "Title": title.group(1).strip().strip('*') if title else "",
                "Description": desc.group(1).strip() if desc else "",
                "Preconditions": prec.group(1).strip() if prec else "",
                "Steps": steps.group(1).strip() if steps else "",
                "Expected Result": expected.group(1).strip() if expected else "",
                "Priority": priority.group(1).strip() if priority else "",
                "Test Type": test_type.group(1).strip() if test_type else "",
            })

    return results


# =============================================
# GENERATION LOGIC
# =============================================
if generate_clicked:
    if not user_input.strip():
        st.warning("⚠️ Please enter a feature description or JIRA ticket details.")
    elif not flow_id.strip():
        st.markdown(
            '<div class="error-box">❌ Flow ID is required! Enter your Langflow Flow ID in the sidebar → 🆔 Flow ID field</div>',
            unsafe_allow_html=True,
        )
    else:
        progress_bar = st.progress(0)
        status_text = st.empty()
        start_time = time.time()

        try:
            status_text.markdown(
                f'<p class="progress-text">🔄 Sending to Langflow — generating {test_count} '
                f'test cases in {batches_needed} batches...</p>',
                unsafe_allow_html=True,
            )

            response = requests.post(
                "http://localhost:8000/generate",
                json={
                    "input": user_input,
                    "count": test_count,
                    "langflow_url": langflow_url,
                    "flow_id": flow_id,
                    "api_key": api_key,
                    "batch_size": batch_size,
                },
                timeout=7200,  # 2 hours allowance for massive 500 level generated content
            )

            data = response.json()
            data["elapsed"] = time.time() - start_time
            st.session_state.result_data = data

            progress_bar.progress(100)
            status_text.empty()
            
        except requests.exceptions.Timeout:
            progress_bar.empty()
            status_text.empty()
            st.error("⏰ The AI generation has exceeded 2 hours. Please check your Langflow backend limits.")
        except requests.exceptions.ConnectionError:
            progress_bar.empty()
            status_text.empty()
            st.error(
                "🔌 Cannot connect to backend. Make sure to run:\n\n"
                "```\nuvicorn main:app --reload\n```"
            )
        except Exception as e:
            progress_bar.empty()
            status_text.empty()
            st.error(f"❌ Error: {str(e)}")

# =============================================
# DISPLAY RESULTS
# =============================================
if "result_data" in st.session_state:
    data = st.session_state.result_data

    # Check for errors
    if data.get("error"):
        # Pre-flight / fatal errors — render as formatted error box
        raw_msg = data.get("message", "Unknown error")
        # Convert bullet characters and newlines to HTML for the error box
        html_msg = raw_msg.replace("\n", "<br>").replace("•", "&bull;")
        st.markdown(
            f'<div class="error-box">{html_msg}</div>',
            unsafe_allow_html=True,
        )
        if data.get("response"):
            st.markdown("### ⚠️ Partial Results (before error)")
            st.code(data["response"], language="text")
    else:
        # --- Success / Partial-success Banner ---
        batch_count = data.get("batches", "?")
        total_gen = data.get("total_generated", "?")
        titles_tracked = data.get("unique_titles_tracked", "?")
        elapsed = data.get("elapsed", 0)

        if total_gen and total_gen != "?" and total_gen > 0:
            st.markdown(f"""
            <div class="success-box">
                ✅ Generated <b>{total_gen}</b> test cases in <b>{batch_count}</b> batches! &nbsp;|&nbsp;
                ⏱️ {elapsed:.1f}s &nbsp;|&nbsp;
                📋 {titles_tracked} unique titles tracked
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown("""
            <div class="error-box">
                ⚠️ No test cases were generated — all batches failed.
                Check the batch details and Langflow logs below.
            </div>
            """, unsafe_allow_html=True)

        # Display warnings / circuit-breaker / rate-limit messages
        if "warnings" in data:
            warnings = data.get("warnings", [])
            # Check if this is a Groq rate limit abort
            rate_limit_msgs = [w for w in warnings if "RATE LIMIT" in w]
            other_msgs = [w for w in warnings if "RATE LIMIT" not in w]

            if rate_limit_msgs:
                # Parse wait time from the message for display
                import re as _re
                wait_match = _re.search(r'Retry after (\d+)m ([0-9.]+)s', rate_limit_msgs[0])
                wait_str = f"{wait_match.group(1)}m {float(wait_match.group(2)):.0f}s" if wait_match else "~40 min"
                st.markdown(f"""
                <div style="background:linear-gradient(135deg,#f7971e,#ffd200);padding:1.2rem 1.5rem;
                border-radius:12px;color:#1a1a1a;font-weight:600;margin:1rem 0;
                box-shadow:0 4px 15px rgba(247,151,30,0.35);">
                    ⏳ <b>Groq Daily Token Limit Reached</b><br>
                    <span style="font-weight:400;font-size:0.95rem;">
                    Your Groq free-tier quota (100,000 tokens/day) is exhausted.<br>
                    ✅ <b>{total_gen} test cases were saved</b> from completed batches.<br>
                    🕐 <b>Try again in {wait_str}</b> — the quota resets on a rolling 24-hour window.<br>
                    💡 Tip: Download your results now, then generate the remaining batches later.
                    </span>
                </div>
                """, unsafe_allow_html=True)

            if other_msgs:
                st.warning(data.get("message", ""))
                with st.expander("🔍 Show batch error details", expanded=True):
                    for w in other_msgs:
                        st.write(f"- {w}")

        # --- Batch Details ---
        batch_details = data.get("batch_details", [])
        if batch_details:
            # Count by status for summary
            n_ok = sum(1 for b in batch_details if b.get("status") == "success")
            n_warn = sum(1 for b in batch_details if b.get("status") == "warning")
            n_err = sum(1 for b in batch_details if b.get("status") == "error")
            n_skip = sum(1 for b in batch_details if b.get("status") == "skipped")
            summary = f"✅ {n_ok} ok  ⚠️ {n_warn} partial  ❌ {n_err} failed  ⏭️ {n_skip} skipped"

            with st.expander(f"📦 Batch Details ({len(batch_details)} batches) — {summary}", expanded=(n_err + n_skip) > 0):
                for bd in batch_details:
                    status = bd.get("status", "success")
                    if status == "error":
                        border = "#ff5757"   # red
                    elif status == "skipped":
                        border = "#9ca3af"   # grey
                    elif status == "warning":
                        border = "#ffc107"   # amber
                    else:
                        border = "#38ef7d"   # green

                    st.markdown(
                        f'<div class="batch-card" style="border-left-color:{border}">'
                        f'<strong>Batch {bd["batch"]}</strong> — {bd["category"]} '
                        f'| Generated: {bd["generated"]} | Range: {bd["range"]} '
                        f'| <span style="color:{border}">{status.upper()}</span>'
                        f'</div>',
                        unsafe_allow_html=True,
                    )

        # --- Results in Tabs ---
        tab1, tab2, tab3 = st.tabs(["📊 Table View", "📄 Raw Output", "📥 Download"])

        parsed_csv = parse_test_cases(data["response"])
        # Cache parsed result so re-renders (sidebar interactions) don't re-parse
        if "parsed_csv_cache" not in st.session_state or st.session_state.get("parsed_response_hash") != hash(data["response"]):
            st.session_state.parsed_csv_cache = parsed_csv
            st.session_state.parsed_response_hash = hash(data["response"])
        else:
            parsed_csv = st.session_state.parsed_csv_cache
        df = pd.DataFrame(parsed_csv) if parsed_csv else None

        with tab1:
            if df is not None and not df.empty:
                st.markdown(f"**Parsed {len(df)} test cases into structured format:**")

                # Filter controls
                filter_col1, filter_col2 = st.columns(2)
                with filter_col1:
                    priorities = ["All"] + sorted(df["Priority"].unique().tolist())
                    sel_priority = st.selectbox("🎯 Filter by Priority", priorities)
                with filter_col2:
                    types = ["All"] + sorted(df["Test Type"].unique().tolist())
                    sel_type = st.selectbox("📂 Filter by Test Type", types)

                filtered = df.copy()
                if sel_priority != "All":
                    filtered = filtered[filtered["Priority"] == sel_priority]
                if sel_type != "All":
                    filtered = filtered[filtered["Test Type"] == sel_type]

                st.dataframe(
                    filtered,
                    use_container_width=True,
                    height=500,
                    column_config={
                        "ID": st.column_config.TextColumn("TC ID", width="small"),
                        "Title": st.column_config.TextColumn("Title", width="medium"),
                        "Description": st.column_config.TextColumn("Description", width="medium"),
                        "Steps": st.column_config.TextColumn("Steps", width="large"),
                        "Priority": st.column_config.TextColumn("Priority", width="small"),
                        "Test Type": st.column_config.TextColumn("Type", width="small"),
                    },
                )

                # Stats row
                stat_c1, stat_c2, stat_c3 = st.columns(3)
                with stat_c1:
                    st.metric("Total Parsed", len(df))
                with stat_c2:
                    st.metric("High Priority", len(df[df["Priority"].str.contains("High", case=False, na=False)]))
                with stat_c3:
                    st.metric("Unique Types", df["Test Type"].nunique())
            else:
                st.warning("⚠️ Could not parse test cases into table. Check the Raw Output tab.")

        with tab2:
            st.code(data["response"], language="text")

        with tab3:
            st.markdown("### Export Options")
            dl_col1, dl_col2, dl_col3, dl_col4 = st.columns(4)
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            tc_count = total_gen if total_gen != "?" else test_count

            # TXT download
            with dl_col1:
                st.download_button(
                    label="📄 Download TXT",
                    data=data["response"],
                    file_name=f"test_cases_{tc_count}_{ts}.txt",
                    mime="text/plain",
                    use_container_width=True,
                )

            if df is not None and not df.empty:
                # CSV download
                with dl_col2:
                    output = io.StringIO()
                    writer = csv.DictWriter(
                        output,
                        fieldnames=["ID", "Title", "Description", "Preconditions", "Steps", "Expected Result", "Priority", "Test Type"],
                    )
                    writer.writeheader()
                    writer.writerows(parsed_csv)
                    csv_data = output.getvalue().encode("utf-8")

                    st.download_button(
                        label="📊 Download CSV",
                        data=csv_data,
                        file_name=f"test_cases_{tc_count}_{ts}.csv",
                        mime="text/csv",
                        use_container_width=True,
                    )
                    
                # MD download
                with dl_col3:
                    md_data = df.to_markdown(index=False)
                    st.download_button(
                        label="📝 Download Markdown",
                        data=md_data.encode("utf-8"),
                        file_name=f"test_cases_{tc_count}_{ts}.md",
                        mime="text/markdown",
                        use_container_width=True,
                    )
                    
                # PDF Download (Simplified structure)
                with dl_col4:
                    pdf = FPDF()
                    pdf.set_margins(10, 10, 10)
                    pdf.set_auto_page_break(auto=True, margin=15)
                    pdf.add_page()

                    # A4 usable width = 210 - 10 (left) - 10 (right) = 190mm
                    PAGE_W = 190

                    def sanitize(txt):
                        """Encode to latin-1 safely for FPDF core fonts."""
                        return str(txt).encode("latin-1", "replace").decode("latin-1")

                    pdf.set_font("Helvetica", style="B", size=16)
                    pdf.set_x(10)
                    pdf.cell(PAGE_W, 10, txt="AI Generated Test Cases", ln=1, align="C")
                    pdf.ln(8)

                    for row in parsed_csv:
                        pdf.set_x(10)
                        pdf.set_font("Helvetica", style="B", size=11)
                        pdf.multi_cell(PAGE_W, 8, txt=sanitize(f"[{row.get('ID', '')}] {row.get('Title', '')}"))

                        pdf.set_x(10)
                        pdf.set_font("Helvetica", size=10)
                        pdf.multi_cell(PAGE_W, 6, txt=sanitize(f"Description: {row.get('Description', '')}"))

                        pdf.set_x(10)
                        pdf.multi_cell(PAGE_W, 6, txt=sanitize(f"Preconditions: {row.get('Preconditions', '')}"))

                        pdf.set_x(10)
                        pdf.multi_cell(PAGE_W, 6, txt=sanitize(f"Steps: {row.get('Steps', '')}"))

                        pdf.set_x(10)
                        pdf.multi_cell(PAGE_W, 6, txt=sanitize(f"Expected Result: {row.get('Expected Result', '')}"))

                        pdf.set_x(10)
                        pdf.multi_cell(PAGE_W, 6, txt=sanitize(f"Priority: {row.get('Priority', '')} | Type: {row.get('Test Type', '')}"))

                        pdf.ln(4)
                    
                    pdf_bytes = bytes(pdf.output())
                    
                    st.download_button(
                        label="📕 Download PDF",
                        data=pdf_bytes,
                        file_name=f"test_cases_{tc_count}_{ts}.pdf",
                        mime="application/pdf",
                        use_container_width=True,
                    )
            else:
                st.info("CSV/MD/PDF unavailable — could not parse structured data.")

        st.markdown("---")
        st.info(
            "💡 **Tip:** Open the CSV in Excel or Google Sheets, use Markdown for documentation, or PDF for sharing."
        )


# --- Footer ---
st.markdown("""
<div class="footer">
    Built with ❤️ using Streamlit + FastAPI + Langflow &nbsp;|&nbsp;
    AI Test Case Generator v3.0 &nbsp;|&nbsp;
    🔗 All Langflow settings configurable from sidebar
</div>
""", unsafe_allow_html=True)