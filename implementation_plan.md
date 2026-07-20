# AI GitHub Repository Explainer Chatbot — Version 1 (MVP)

Build an AI chatbot where a user pastes a public GitHub repo URL, the backend clones & analyzes it, and Gemini answers natural-language questions about the codebase.

## User Review Required

> [!IMPORTANT]
> **Google Gemini API Key** — You'll need a `GOOGLE_API_KEY` from [Google AI Studio](https://aistudio.google.com/). The app reads it from a `.env` file.

> [!IMPORTANT]
> **SDK Choice** — The old `google-generativeai` package is deprecated. This plan uses the new **`google-genai`** SDK (`from google import genai`).

> [!WARNING]
> **Token Limits** — For Version 1 (no RAG), we concatenate relevant file contents and send them in the prompt. This works well for small–medium repos but will hit token limits on very large repos. Version 2 (RAG) solves this.

## Open Questions

1. **Gemini Model**: Which model do you want to use? I'll default to `gemini-2.0-flash` (fast, cheap, great for code). Alternatives: `gemini-2.5-flash`, `gemini-2.5-pro`.
2. **Auth**: Should the app support private repos via a GitHub personal access token, or public repos only for MVP?
3. **Persistence**: Should analyzed repos persist across sessions, or is a fresh clone per session fine for MVP?

---

## Project Structure

```
GitHubRepoAssistant/
├── prompt.md                  # (existing) Project spec
├── .env                       # API keys (gitignored)
├── .env.example               # Template for .env
├── .gitignore
├── requirements.txt           # Python dependencies
├── README.md                  # Project documentation
│
├── backend/
│   ├── __init__.py
│   ├── main.py                # FastAPI application entry point
│   ├── config.py              # Settings / env loading
│   ├── models.py              # Pydantic request/response schemas
│   │
│   ├── services/
│   │   ├── __init__.py
│   │   ├── repo_cloner.py     # Clone repo via GitPython
│   │   ├── repo_analyzer.py   # Analyze structure, detect languages/frameworks
│   │   └── gemini_service.py  # Gemini API wrapper (chat + summary)
│   │
│   └── utils/
│       ├── __init__.py
│       └── file_utils.py      # File reading, tree generation, extension mapping
│
└── frontend/
    └── app.py                 # Streamlit UI
```

---

## Proposed Changes

### Core Setup

#### [NEW] [.env.example](file:///Users/kishanb/Desktop/projects/GitHubRepoAssistant/.env.example)

Template with `GOOGLE_API_KEY=your_key_here`.

#### [NEW] [.gitignore](file:///Users/kishanb/Desktop/projects/GitHubRepoAssistant/.gitignore)

Ignore `.env`, `__pycache__`, `.venv`, `cloned_repos/`, `*.pyc`.

#### [NEW] [requirements.txt](file:///Users/kishanb/Desktop/projects/GitHubRepoAssistant/requirements.txt)

```
fastapi
uvicorn[standard]
streamlit
google-genai
gitpython
python-dotenv
requests
```

#### [NEW] [README.md](file:///Users/kishanb/Desktop/projects/GitHubRepoAssistant/README.md)

Project overview, setup instructions, how to run backend + frontend.

---

### Backend — Configuration

#### [NEW] [config.py](file:///Users/kishanb/Desktop/projects/GitHubRepoAssistant/backend/config.py)

- Load `.env` via `python-dotenv`
- Expose `GOOGLE_API_KEY`, `GEMINI_MODEL` (default `gemini-2.0-flash`), `CLONE_DIR` (default `./cloned_repos`)
- Validate that required keys exist at startup

---

### Backend — Pydantic Models

#### [NEW] [models.py](file:///Users/kishanb/Desktop/projects/GitHubRepoAssistant/backend/models.py)

| Schema | Fields | Purpose |
|---|---|---|
| `CloneRequest` | `repo_url: str` | Incoming repo URL from user |
| `RepoSummary` | `name, description, languages, framework, folder_structure, entry_point, config_files, important_files, ai_summary` | Structured analysis result |
| `ChatRequest` | `repo_url: str, question: str, chat_history: list` | Chat message from user |
| `ChatResponse` | `answer: str` | Gemini's reply |

---

### Backend — Services

#### [NEW] [repo_cloner.py](file:///Users/kishanb/Desktop/projects/GitHubRepoAssistant/backend/services/repo_cloner.py)

- `clone_repo(repo_url: str) -> Path` — Clones the repo into `CLONE_DIR/<owner>_<repo>`. If already cloned, pulls latest.
- Validates URL format (must be `github.com/...`).
- Uses `git.Repo.clone_from()` with `depth=1` for speed.

#### [NEW] [repo_analyzer.py](file:///Users/kishanb/Desktop/projects/GitHubRepoAssistant/backend/services/repo_analyzer.py)

Core analysis engine. Functions:

| Function | What it does |
|---|---|
| `analyze_repo(repo_path)` | Orchestrator — calls all functions below and returns a `RepoSummary` |
| `detect_languages(repo_path)` | Counts file extensions, returns languages sorted by frequency |
| `detect_framework(repo_path)` | Checks for framework markers (e.g., `manage.py` → Django, `next.config.js` → Next.js, `Cargo.toml` → Rust, etc.) |
| `get_folder_structure(repo_path, max_depth=3)` | Generates a tree string (ignoring `.git`, `node_modules`, `__pycache__`, `.venv`) |
| `find_entry_point(repo_path)` | Heuristic: looks for `main.py`, `app.py`, `index.js`, `server.js`, `Main.java`, etc. |
| `read_important_files(repo_path)` | Reads `README.md`, `requirements.txt`, `package.json`, `pyproject.toml`, `Dockerfile`, `docker-compose.yml`, `Cargo.toml`, `pom.xml`, `.env.example` — returns dict of `{filename: content}` |
| `read_file_content(repo_path, file_path)` | Reads a specific file, with size limit (max 100KB) to avoid blowing up context |

#### [NEW] [gemini_service.py](file:///Users/kishanb/Desktop/projects/GitHubRepoAssistant/backend/services/gemini_service.py)

- Initializes `genai.Client(api_key=...)` on startup.
- `generate_summary(repo_analysis: dict) -> str` — Sends repo metadata + important file contents to Gemini with a system prompt that asks for a beginner-friendly project summary.
- `chat_with_repo(question: str, repo_analysis: dict, chat_history: list, file_content: str | None) -> str` — Sends the user's question along with repo context to Gemini. Includes chat history for multi-turn conversations.
- System prompts instruct Gemini to act as a helpful code mentor.

---

### Backend — Utilities

#### [NEW] [file_utils.py](file:///Users/kishanb/Desktop/projects/GitHubRepoAssistant/backend/utils/file_utils.py)

- `EXTENSION_LANGUAGE_MAP` — Maps `.py` → Python, `.js` → JavaScript, etc.
- `is_binary_file(path)` — Quick check to skip binary files.
- `get_file_tree(path, prefix, max_depth)` — Recursive tree builder.
- `IGNORE_DIRS` — Set of directories to skip during traversal.

---

### Backend — FastAPI Application

#### [NEW] [main.py](file:///Users/kishanb/Desktop/projects/GitHubRepoAssistant/backend/main.py)

Endpoints:

| Method | Path | Description |
|---|---|---|
| `POST` | `/api/analyze` | Accepts `CloneRequest`, clones repo, runs analysis, generates AI summary, returns `RepoSummary` |
| `POST` | `/api/chat` | Accepts `ChatRequest`, retrieves cached analysis, calls Gemini, returns `ChatResponse` |
| `GET` | `/api/files/{repo_name}/{file_path:path}` | Returns content of a specific file |
| `GET` | `/api/health` | Health check |

- Uses an in-memory dict to cache analyzed repos per session.
- CORS middleware enabled for Streamlit connection.

---

### Frontend — Streamlit

#### [NEW] [app.py](file:///Users/kishanb/Desktop/projects/GitHubRepoAssistant/frontend/app.py)

The Streamlit UI with the following flow:

1. **Sidebar** — Input field for GitHub URL + "Analyze" button. Shows analysis status (loading spinner).
2. **Main Area — Summary Tab** — Once analyzed, shows:
   - Project name & description
   - Languages & framework
   - Folder structure (in a code block)
   - Entry point
   - AI-generated summary (rendered as markdown)
3. **Main Area — Chat Tab** — Chat interface using `st.chat_message` / `st.chat_input`:
   - Full conversation history with scroll
   - Sends questions to `/api/chat`
   - Displays Gemini's responses formatted as markdown
4. **Main Area — Files Tab** — Browse the folder structure, click a file to see its AI-explained content.

Session state manages: `repo_url`, `repo_summary`, `chat_history`, `analyzed` (bool).

---

## Verification Plan

### Automated Tests

```bash
# Start the backend
cd /Users/kishanb/Desktop/projects/GitHubRepoAssistant
uvicorn backend.main:app --reload --port 8000

# In another terminal, test the API
curl -X POST http://localhost:8000/api/analyze \
  -H "Content-Type: application/json" \
  -d '{"repo_url": "https://github.com/tiangolo/fastapi"}'

curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"repo_url": "https://github.com/tiangolo/fastapi", "question": "What does this project do?", "chat_history": []}'
```

### Manual Verification

1. Start backend with `uvicorn backend.main:app --reload`
2. Start frontend with `streamlit run frontend/app.py`
3. Paste a GitHub URL (e.g., `https://github.com/pallets/flask`)
4. Verify the summary is generated correctly
5. Ask questions in the chat and verify relevant, accurate answers
6. Try the file explorer and verify file explanations work
7. Test with 2–3 different repos of varying sizes
