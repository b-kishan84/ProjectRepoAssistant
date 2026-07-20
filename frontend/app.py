"""
Streamlit frontend for the GitHub Repository Explainer Chatbot.
"""

import streamlit as st
import requests
import time
from code_editor import code_editor

# ─── Configuration ─────────────────────────────────────────────────────────────

API_BASE_URL = "http://localhost:8000"

st.set_page_config(
    page_title="GitHub Repo Assistant",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─── Custom CSS ────────────────────────────────────────────────────────────────

st.markdown("""
<style>
    /* Main container */
    .main .block-container {
        padding-top: 2rem;
        max-width: 1200px;
    }

    /* Header styling */
    .app-header {
        text-align: center;
        padding: 1.5rem 0;
        margin-bottom: 1rem;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        border-radius: 12px;
        color: white;
    }
    .app-header h1 {
        color: white !important;
        font-size: 2rem;
        margin-bottom: 0.3rem;
    }
    .app-header p {
        color: rgba(255, 255, 255, 0.85);
        font-size: 1.05rem;
        margin: 0;
    }

    /* Sidebar styling */
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #1a1a2e 0%, #16213e 100%);
    }
    [data-testid="stSidebar"] .stMarkdown h1,
    [data-testid="stSidebar"] .stMarkdown h2,
    [data-testid="stSidebar"] .stMarkdown h3 {
        color: #e0e0ff !important;
    }
    [data-testid="stSidebar"] .stMarkdown p,
    [data-testid="stSidebar"] .stMarkdown li {
        color: #c0c0e0 !important;
    }

    /* Status badges */
    .status-badge {
        display: inline-block;
        padding: 4px 12px;
        border-radius: 20px;
        font-size: 0.85rem;
        font-weight: 600;
    }
    .status-ready {
        background: #d4edda;
        color: #155724;
    }
    .status-loading {
        background: #fff3cd;
        color: #856404;
    }

    /* File tree styling */
    .file-tree {
        font-family: 'Courier New', monospace;
        font-size: 0.85rem;
        background: #1e1e2e;
        color: #cdd6f4;
        padding: 1rem;
        border-radius: 8px;
        overflow-x: auto;
        line-height: 1.6;
    }

    /* Info cards */
    .info-card {
        background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
        border-radius: 10px;
        padding: 1.2rem;
        margin: 0.5rem 0;
    }

    /* Chat messages */
    [data-testid="stChatMessage"] {
        border-radius: 12px;
        margin-bottom: 0.5rem;
    }

    /* Tabs */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
    }
    .stTabs [data-baseweb="tab"] {
        border-radius: 8px 8px 0 0;
        padding: 8px 20px;
        font-weight: 600;
    }

    /* Buttons */
    .stButton > button {
        border-radius: 8px;
        font-weight: 600;
        transition: all 0.3s ease;
    }
    .stButton > button:hover {
        transform: translateY(-1px);
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
    }
    /* Snippet chat dialog styling */
    [data-testid="stDialog"] [data-testid="stVerticalBlock"] {
        gap: 0.5rem;
    }
    .snippet-box {
        background: #1e1e2e;
        color: #cdd6f4;
        padding: 0.8rem;
        border-radius: 8px;
        font-family: 'Courier New', monospace;
        font-size: 0.82rem;
        overflow-x: auto;
        max-height: 200px;
        overflow-y: auto;
        border-left: 4px solid #667eea;
        margin-bottom: 0.5rem;
    }
    .snippet-label {
        font-size: 0.8rem;
        color: #888;
        margin-bottom: 4px;
    }
</style>
""", unsafe_allow_html=True)


# ─── Session State Initialization ──────────────────────────────────────────────

if "analyzed" not in st.session_state:
    st.session_state.analyzed = False
if "repo_summary" not in st.session_state:
    st.session_state.repo_summary = None
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "repo_url" not in st.session_state:
    st.session_state.repo_url = ""
if "selected_file" not in st.session_state:
    st.session_state.selected_file = None
if "file_explanation" not in st.session_state:
    st.session_state.file_explanation = None
if "snippet_chat_history" not in st.session_state:
    st.session_state.snippet_chat_history = []
if "snippet_chat_file" not in st.session_state:
    st.session_state.snippet_chat_file = None


# ─── Helper Functions ──────────────────────────────────────────────────────────

def check_api_health() -> bool:
    """Check if the backend API is running."""
    try:
        resp = requests.get(f"{API_BASE_URL}/api/health", timeout=3)
        return resp.status_code == 200
    except requests.ConnectionError:
        return False


def analyze_repository(repo_url: str) -> dict | None:
    """Send analyze request to the backend."""
    try:
        resp = requests.post(
            f"{API_BASE_URL}/api/analyze",
            json={"repo_url": repo_url},
            timeout=120,  # Cloning + analysis can take time
        )
        if resp.status_code == 200:
            return resp.json()
        else:
            st.error(f"❌ Error: {resp.json().get('detail', 'Unknown error')}")
            return None
    except requests.ConnectionError:
        st.error("❌ Cannot connect to the backend. Is it running on port 8000?")
        return None
    except requests.Timeout:
        st.error("❌ Request timed out. The repository might be too large.")
        return None


def send_chat_message(repo_url: str, question: str, chat_history: list) -> str | None:
    """Send a chat message to the backend."""
    try:
        resp = requests.post(
            f"{API_BASE_URL}/api/chat",
            json={
                "repo_url": repo_url,
                "question": question,
                "chat_history": chat_history,
            },
            timeout=60,
        )
        if resp.status_code == 200:
            return resp.json().get("answer")
        else:
            return f"❌ Error: {resp.json().get('detail', 'Unknown error')}"
    except requests.ConnectionError:
        return "❌ Cannot connect to the backend."
    except requests.Timeout:
        return "❌ Request timed out."


def get_file_explanation(repo_url: str, file_path: str) -> dict | None:
    """Get file content and AI explanation from the backend."""
    try:
        resp = requests.get(
            f"{API_BASE_URL}/api/files",
            params={"repo_url": repo_url, "file_path": file_path},
            timeout=60,
        )
        if resp.status_code == 200:
            return resp.json()
        else:
            st.error(f"❌ Error: {resp.json().get('detail', 'Unknown error')}")
            return None
    except (requests.ConnectionError, requests.Timeout):
        st.error("❌ Cannot connect to the backend.")
        return None


def send_snippet_chat(
    repo_url: str,
    file_path: str,
    snippet: str,
    question: str,
    chat_history: list,
) -> str | None:
    """Send a snippet chat message to the backend."""
    try:
        resp = requests.post(
            f"{API_BASE_URL}/api/chat-snippet",
            json={
                "repo_url": repo_url,
                "file_path": file_path,
                "snippet": snippet,
                "question": question,
                "chat_history": chat_history,
            },
            timeout=90,
        )
        if resp.status_code == 200:
            return resp.json().get("answer")
        else:
            return f"❌ Error: {resp.json().get('detail', 'Unknown error')}"
    except requests.ConnectionError:
        return "❌ Cannot connect to the backend."
    except requests.Timeout:
        return "❌ Request timed out."


# ─── Snippet Chat Dialog & Helpers ──────────────────────────────────────────

@st.dialog("💬 Ask AI about this code", width="large")
def _open_snippet_chat(snippet: str, file_path: str, file_content: str):
    """Open a modal dialog with a mini chatbot focused on the selected snippet."""

    # Reset chat if the snippet changed
    if "_dialog_snippet" not in st.session_state or st.session_state._dialog_snippet != snippet:
        st.session_state._dialog_snippet = snippet
        st.session_state.snippet_chat_history = []
        st.session_state.qa_pills = None
        st.session_state.last_pill_selection = None

    # Show the selected snippet
    st.markdown('<p class="snippet-label">📌 Selected Code:</p>', unsafe_allow_html=True)
    st.markdown(
        f'<div class="snippet-box"><pre>{snippet}</pre></div>',
        unsafe_allow_html=True,
    )

    def clear_active_qa():
        st.session_state.qa_pills = None
        st.session_state.last_pill_selection = None

    # Native Streamlit Pills for instantaneous active state highlighting
    qa_options = ["🔍 Explain", "🐛 Find Bugs", "✨ Refactor", "📝 Docstring"]
    selection = st.pills("**Quick Actions:**", qa_options, key="qa_pills")
    
    if selection and selection != st.session_state.get("last_pill_selection"):
        st.session_state.last_pill_selection = selection
        if selection == "🔍 Explain":
            _send_and_store(snippet, file_path, "Explain this code in detail, line by line.")
        elif selection == "🐛 Find Bugs":
            _send_and_store(snippet, file_path, "Find any bugs, edge cases, or potential issues in this code.")
        elif selection == "✨ Refactor":
            _send_and_store(snippet, file_path, "Suggest refactoring or optimizations for this code. Show the improved version.")
        elif selection == "📝 Docstring":
            _send_and_store(snippet, file_path, "Generate a proper docstring or comments for this code.")

    st.markdown("---")

    # Define the container for chat history, but we won't draw into it yet!
    chat_container = st.container(height=350)

    # Action buttons row
    bcol1, bcol2 = st.columns([1, 1])
    with bcol1:
        if st.button("🔄 Regenerate Last", key="snippet_regen", use_container_width=True,
                     disabled=len(st.session_state.snippet_chat_history) < 2):
            if len(st.session_state.snippet_chat_history) >= 2:
                st.session_state.snippet_chat_history.pop()  # Remove assistant
                last_user_msg = st.session_state.snippet_chat_history.pop()  # Remove user
                _send_and_store(snippet, file_path, last_user_msg["content"])
    with bcol2:
        if st.button("🗑️ Clear Chat", key="snippet_clear", use_container_width=True,
                     disabled=len(st.session_state.snippet_chat_history) == 0):
            st.session_state.snippet_chat_history = []
            clear_active_qa()

    # Bottom action bar: input
    user_input = st.chat_input(
        "Ask about the selected code...",
        key="snippet_chat_input",
        on_submit=clear_active_qa
    )
    if user_input:
        _send_and_store(snippet, file_path, user_input)

    # Now that ALL logic is processed, render the history into the container
    with chat_container:
        if not st.session_state.snippet_chat_history:
            st.markdown(
                "*Select a quick action above, or type a question below to get started.*"
            )
        for msg in st.session_state.snippet_chat_history:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])


def _send_and_store(snippet: str, file_path: str, question: str):
    """Send a snippet chat question and store both the question and answer in history."""
    st.session_state.snippet_chat_history.append({"role": "user", "content": question})

    answer = send_snippet_chat(
        repo_url=st.session_state.repo_url,
        file_path=file_path,
        snippet=snippet,
        question=question,
        chat_history=st.session_state.snippet_chat_history[:-1],
    )

    if answer:
        st.session_state.snippet_chat_history.append({"role": "assistant", "content": answer})
    else:
        st.session_state.snippet_chat_history.append(
            {"role": "assistant", "content": "❌ Failed to get a response. Please try again."}
        )


# ─── Header ────────────────────────────────────────────────────────────────────

st.markdown("""
<div class="app-header">
    <h1>🤖 GitHub Repo Assistant</h1>
    <p>Paste a GitHub URL → Get an AI-powered explanation → Chat with the codebase</p>
</div>
""", unsafe_allow_html=True)


# ─── Sidebar ───────────────────────────────────────────────────────────────────

with st.sidebar:
    st.markdown("### 🔗 Repository URL")

    repo_url = st.text_input(
        "GitHub URL",
        placeholder="https://github.com/owner/repo",
        label_visibility="collapsed",
        key="url_input",
    )

    col1, col2 = st.columns(2)

    with col1:
        analyze_clicked = st.button("🚀 Analyze", use_container_width=True, type="primary")

    with col2:
        if st.button("🔄 Reset", use_container_width=True):
            st.session_state.analyzed = False
            st.session_state.repo_summary = None
            st.session_state.chat_history = []
            st.session_state.repo_url = ""
            st.session_state.selected_file = None
            st.session_state.file_explanation = None
            st.rerun()

    # API Health Check
    st.markdown("---")
    api_ok = check_api_health()
    if api_ok:
        st.success("✅ Backend connected")
    else:
        st.error("❌ Backend offline — start it with:\n`uvicorn backend.main:app --reload`")

    # Show analyzed repo info
    if st.session_state.analyzed and st.session_state.repo_summary:
        summary = st.session_state.repo_summary
        st.markdown("---")
        st.markdown("### 📊 Repo Info")
        st.markdown(f"**{summary.get('name', 'Unknown')}**")

        if summary.get("languages"):
            langs = ", ".join(summary["languages"][:5])
            st.markdown(f"🔤 {langs}")

        if summary.get("framework"):
            st.markdown(f"🏗️ {summary['framework']}")

        if summary.get("entry_point"):
            st.markdown(f"🚪 Entry: `{summary['entry_point']}`")

        st.markdown(f"📁 {len(summary.get('file_list', []))} files")

    # Example prompts
    st.markdown("---")
    st.markdown("### 💡 Example Questions")
    example_questions = [
        "What does this project do?",
        "Explain the folder structure",
        "How does authentication work?",
        "What's the entry point?",
        "Explain the API routes",
        "Which file should I start reading?",
    ]
    for q in example_questions:
        st.markdown(f"- *{q}*")


# ─── Analyze Logic ─────────────────────────────────────────────────────────────

if analyze_clicked and repo_url:
    st.session_state.repo_url = repo_url
    st.session_state.chat_history = []
    st.session_state.selected_file = None
    st.session_state.file_explanation = None

    with st.spinner("🔄 Cloning and analyzing repository... This may take a minute."):
        result = analyze_repository(repo_url)

    if result:
        st.session_state.repo_summary = result
        st.session_state.analyzed = True
        st.success("✅ Repository analyzed successfully!")
        time.sleep(0.5)
        st.rerun()

elif analyze_clicked and not repo_url:
    st.warning("⚠️ Please enter a GitHub repository URL.")


# ─── Main Content ──────────────────────────────────────────────────────────────

if not st.session_state.analyzed:
    # Welcome screen
    st.markdown("---")

    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown("""
        ### 📋 Analyze
        Paste any public or private GitHub URL.
        The AI clones it and analyzes the entire codebase.
        """)
    with col2:
        st.markdown("""
        ### 🧠 Understand
        Get a beginner-friendly summary with
        technologies, structure, and how to run the project.
        """)
    with col3:
        st.markdown("""
        ### 💬 Chat
        Ask natural language questions about
        any file, folder, function, or workflow.
        """)

    st.markdown("---")
    st.info("👆 Enter a GitHub URL in the sidebar to get started!")

else:
    # Repository is analyzed — show tabs
    summary = st.session_state.repo_summary

    tab_summary, tab_chat, tab_files = st.tabs(["📋 Summary", "💬 Chat", "📁 Files"])

    # ─── Summary Tab ───────────────────────────────────────────────────────

    with tab_summary:
        # AI-generated summary
        st.markdown("### 🧠 AI Project Summary")
        st.markdown(summary.get("ai_summary", "No summary available."))

        st.markdown("---")

        # Quick stats
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Languages", len(summary.get("languages", [])))
        with col2:
            st.metric("Files", len(summary.get("file_list", [])))
        with col3:
            st.metric("Config Files", len(summary.get("config_files", [])))
        with col4:
            framework = summary.get("framework", "—")
            st.metric("Framework", framework if framework else "—")

        st.markdown("---")

        # Folder structure
        st.markdown("### 📂 Folder Structure")
        st.markdown(
            f'<div class="file-tree">{summary.get("folder_structure", "")}</div>',
            unsafe_allow_html=True,
        )

    # ─── Chat Tab ──────────────────────────────────────────────────────────

    with tab_chat:
        st.markdown("### 💬 Chat with the Repository")
        st.markdown(
            f"Ask anything about **{summary.get('name', 'this repo')}**. "
            "The AI has full context of the codebase."
        )

        # Display chat history
        for msg in st.session_state.chat_history:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])

        # Chat input
        if prompt := st.chat_input("Ask about the repository..."):
            # Add user message
            st.session_state.chat_history.append({"role": "user", "content": prompt})
            with st.chat_message("user"):
                st.markdown(prompt)

            # Get AI response
            with st.chat_message("assistant"):
                with st.spinner("Thinking..."):
                    response = send_chat_message(
                        repo_url=st.session_state.repo_url,
                        question=prompt,
                        chat_history=st.session_state.chat_history[:-1],  # Exclude current
                    )
                if response:
                    st.markdown(response)
                    st.session_state.chat_history.append(
                        {"role": "assistant", "content": response}
                    )

    # ─── Files Tab ─────────────────────────────────────────────────────────

    with tab_files:
        st.markdown("### 📁 File Explorer")
        st.markdown("Select a file to see its content and AI explanation.")

        file_list = summary.get("file_list", [])

        if file_list:
            selected = st.selectbox(
                "Choose a file",
                options=file_list,
                index=None,
                placeholder="Select a file to explore...",
                key="file_selector",
            )

            if selected and st.button("🔍 Explain File", type="primary"):
                with st.spinner(f"Analyzing `{selected}`..."):
                    result = get_file_explanation(st.session_state.repo_url, selected)

                if result:
                    st.session_state.selected_file = selected
                    st.session_state.file_explanation = result
                    # Reset snippet chat when switching files
                    st.session_state.snippet_chat_history = []
                    st.session_state.snippet_chat_file = selected

            # Display file explanation
            if st.session_state.file_explanation:
                file_data = st.session_state.file_explanation

                st.markdown(f"#### 📄 `{file_data.get('file_path', '')}`")

                exp_tab, code_tab = st.tabs(["🧠 Explanation", "📝 Source Code"])

                with exp_tab:
                    st.markdown(file_data.get("explanation", "No explanation available."))

                with code_tab:
                    # Detect language for syntax highlighting
                    path = file_data.get("file_path", "")
                    lang_map = {
                        ".py": "python", ".js": "javascript", ".ts": "typescript",
                        ".java": "java", ".go": "golang", ".rs": "rust", ".rb": "ruby",
                        ".php": "php", ".cs": "csharp", ".cpp": "c_cpp", ".c": "c_cpp",
                        ".html": "html", ".css": "css", ".json": "json",
                        ".yaml": "yaml", ".yml": "yaml", ".md": "markdown",
                        ".sh": "sh", ".sql": "sql", ".xml": "xml",
                        ".toml": "toml", ".jsx": "jsx", ".tsx": "tsx",
                    }
                    ext = "." + path.rsplit(".", 1)[-1] if "." in path else ""
                    lang = lang_map.get(ext, "python")

                    st.markdown(
                        "💡 **Highlight any code** in the editor below, "
                        "then click the **💬 Ask AI about selected code** button that appears below."
                    )

                    # Render the interactive code editor
                    # We use response_mode="select" so it automatically sends back the highlighted text.
                    editor_response = code_editor(
                        file_data.get("content", ""),
                        lang=lang,
                        response_mode="select",
                        info={"name": f"File: {path}"},
                        options={
                            "readOnly": True,
                            "showLineNumbers": True,
                            "wrap": True,
                            "fontSize": 14,
                        },
                        key=f"code_editor_{path}",
                    )

                    # Handle selection with a reliable native Streamlit button
                    selected_snippet = editor_response.get("selected", "").strip() if editor_response else ""
                    
                    if selected_snippet:
                        st.markdown(f"**{len(selected_snippet)} characters selected.**")
                        if st.button("💬 Ask AI about selected code", type="primary", use_container_width=True):
                            _open_snippet_chat(
                                selected_snippet,
                                file_data.get("file_path", ""),
                                file_data.get("content", ""),
                            )
        else:
            st.info("No files found in the repository.")



