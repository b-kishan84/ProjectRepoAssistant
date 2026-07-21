# 🤖 AI GitHub Repository Explainer Chatbot

An AI-powered chatbot that helps developers understand any public (or private) GitHub repository. Paste a repo URL, get an instant project summary, and chat with the codebase using Google Gemini.

## Features (Version 1 — MVP)

- **Accept any GitHub URL** — public or private (with token)
- **Auto-clone & analyze** — detects languages, frameworks, entry points, folder structure
- **AI-generated summary** — beginner-friendly explanation of the project
- **Chat with the repo** — ask natural language questions about the codebase
- **File explorer** — browse and get AI explanations of any file
- **Interactive Code Snippets** — highlight any code in the editor and click "Ask AI" for instant context-aware help
- **Resilient Disk Caching** — saves analysis to disk (`.repo_analysis.json`) to prevent data loss across backend restarts and minimize API calls
## Tech Stack

| Component | Technology |
|-----------|------------|
| Backend | Python, FastAPI |
| Frontend | Streamlit |
| AI Model | Google Gemini (gemini-3.5-flash) |
| Git Operations | GitPython |

## Setup

### 1. Clone this repository

```bash
git clone https://github.com/your-username/GitHubRepoAssistant.git
cd GitHubRepoAssistant
```

### 2. Create a virtual environment

```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure environment variables

```bash
cp .env.example .env
```

Edit `.env` and add your keys:
- `GOOGLE_API_KEY` — Get from [Google AI Studio](https://aistudio.google.com/)
- `GITHUB_TOKEN` (optional) — For private repository access

### 5. Run the application

**Start the backend:**

```bash
uvicorn backend.main:app --reload --port 8000
```

**Start the frontend (in a new terminal):**

```bash
streamlit run frontend/app.py
```

### 6. Open the app

Navigate to `http://localhost:8501` in your browser, paste a GitHub URL, and start chatting!

## Project Structure

```
GitHubRepoAssistant/
├── backend/
│   ├── main.py               # FastAPI app & API endpoints
│   ├── config.py             # Environment & settings
│   ├── models.py             # Pydantic schemas
│   ├── services/
│   │   ├── repo_cloner.py    # Git clone operations
│   │   ├── repo_analyzer.py  # Repo analysis engine
│   │   └── gemini_service.py # Gemini AI integration
│   └── utils/
│       └── file_utils.py     # File helpers
├── frontend/
│   └── app.py                # Streamlit UI
├── requirements.txt
├── .env.example
└── README.md
```

## License

MIT
