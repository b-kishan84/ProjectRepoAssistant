"""
FastAPI application — main entry point for the GitHub Repo Assistant API.
"""

import logging
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from backend.models import (
    CloneRequest, ChatRequest, ChatResponse, RepoSummary,
    SnippetChatRequest, SnippetChatResponse, clean_github_url,
)
from backend.services.repo_cloner import clone_repo, get_clone_path, parse_repo_url
from backend.services.repo_analyzer import analyze_repo
from backend.services.gemini_service import (
    generate_summary, chat_with_repo, explain_file, chat_about_snippet,
)
from backend.utils.file_utils import safe_read_file

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# ─── FastAPI App ───────────────────────────────────────────────────────────────

app = FastAPI(
    title="GitHub Repo Assistant API",
    description="AI-powered chatbot that explains GitHub repositories",
    version="1.0.0",
)

# CORS — allow Streamlit to connect
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory cache for analyzed repos (MVP — no persistence)
_repo_cache: dict[str, dict] = {}


# ─── Endpoints ─────────────────────────────────────────────────────────────────

@app.get("/api/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "GitHub Repo Assistant API"}


@app.post("/api/analyze", response_model=RepoSummary)
async def analyze_repository(request: CloneRequest):
    """
    Clone and analyze a GitHub repository.

    1. Clones the repo (shallow, depth=1)
    2. Analyzes structure, languages, frameworks
    3. Generates an AI summary via Gemini
    4. Returns the full analysis

    The analysis is cached in memory for subsequent chat requests.
    """
    repo_url = request.repo_url
    logger.info(f"Analyze request for: {repo_url}")

    try:
        # Step 1: Clone
        clone_path = clone_repo(repo_url)

        # Step 2: Analyze
        analysis = analyze_repo(clone_path)

        # Step 3: Generate AI summary
        ai_summary = generate_summary(analysis)
        analysis["ai_summary"] = ai_summary

        # Cache the analysis for chat
        _repo_cache[repo_url] = analysis

        # Build response
        return RepoSummary(
            name=analysis["name"],
            description=analysis["description"],
            languages=analysis["languages"],
            framework=analysis.get("framework"),
            folder_structure=analysis["folder_structure"],
            entry_point=analysis.get("entry_point"),
            config_files=analysis["config_files"],
            important_files=analysis["important_files"],
            ai_summary=ai_summary,
            file_list=analysis.get("file_list", []),
        )

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error analyzing repo: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to analyze repository: {str(e)}",
        )


@app.post("/api/chat", response_model=ChatResponse)
async def chat_about_repo(request: ChatRequest):
    """
    Chat with the AI about a previously analyzed repository.

    Sends the user's question + repo context to Gemini and returns the answer.
    """
    repo_url = clean_github_url(request.repo_url)
    logger.info(f"Chat request for {repo_url}: {request.question[:80]}...")

    # Check if repo has been analyzed
    analysis = _repo_cache.get(repo_url)
    if not analysis:
        raise HTTPException(
            status_code=404,
            detail="Repository not analyzed yet. Please analyze it first via /api/analyze.",
        )

    try:
        # Check if the question references a specific file
        file_content = None
        question_lower = request.question.lower()

        # Try to detect file references in the question
        file_list = analysis.get("file_list", [])
        for file_path in file_list:
            if file_path.lower() in question_lower or Path(file_path).name.lower() in question_lower:
                clone_path = get_clone_path(repo_url)
                full_path = clone_path / file_path
                file_content = safe_read_file(full_path)
                if file_content:
                    logger.info(f"Found referenced file: {file_path}")
                break

        # Build chat history for context
        history = [
            {"role": msg.role, "content": msg.content}
            for msg in request.chat_history
        ]

        # Get answer from Gemini
        answer = chat_with_repo(
            question=request.question,
            repo_analysis=analysis,
            chat_history=history,
            file_content=file_content,
        )

        return ChatResponse(answer=answer)

    except Exception as e:
        logger.error(f"Error in chat: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate response: {str(e)}",
        )


@app.get("/api/files")
async def get_file_content(repo_url: str, file_path: str):
    """
    Get the content and AI explanation of a specific file.

    Query params:
        repo_url: The GitHub repository URL
        file_path: Relative path to the file within the repo
    """
    repo_url = clean_github_url(repo_url)
    analysis = _repo_cache.get(repo_url)
    if not analysis:
        raise HTTPException(
            status_code=404,
            detail="Repository not analyzed yet.",
        )

    clone_path = get_clone_path(repo_url)
    full_path = clone_path / file_path

    # Security: ensure the path doesn't escape the clone directory
    try:
        full_path.resolve().relative_to(clone_path.resolve())
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid file path.")

    content = safe_read_file(full_path)
    if content is None:
        raise HTTPException(status_code=404, detail="File not found or is binary.")

    try:
        explanation = explain_file(file_path, content, analysis)
    except Exception as e:
        logger.error(f"Error explaining file: {e}", exc_info=True)
        explanation = "Could not generate explanation for this file."

    return {
        "file_path": file_path,
        "content": content,
        "explanation": explanation,
    }


@app.get("/api/file-tree")
async def get_file_tree(repo_url: str):
    """Get the file list for a previously analyzed repo."""
    repo_url = clean_github_url(repo_url)
    analysis = _repo_cache.get(repo_url)
    if not analysis:
        raise HTTPException(status_code=404, detail="Repository not analyzed yet.")

    return {
        "folder_structure": analysis["folder_structure"],
        "file_list": analysis.get("file_list", []),
    }


@app.post("/api/chat-snippet", response_model=SnippetChatResponse)
async def chat_about_code_snippet(request: SnippetChatRequest):
    """
    Chat about a specific highlighted code snippet within a file.

    The AI focuses on the selected snippet while using the full file as context.
    """
    repo_url = clean_github_url(request.repo_url)
    logger.info(f"Snippet chat for {request.file_path}: {request.question[:80]}...")

    # Check if repo has been analyzed
    analysis = _repo_cache.get(repo_url)
    if not analysis:
        raise HTTPException(
            status_code=404,
            detail="Repository not analyzed yet. Please analyze it first.",
        )

    # Read the full file content for context
    clone_path = get_clone_path(repo_url)
    full_path = clone_path / request.file_path

    # Security: ensure path doesn't escape clone directory
    try:
        full_path.resolve().relative_to(clone_path.resolve())
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid file path.")

    file_content = safe_read_file(full_path)
    if file_content is None:
        raise HTTPException(status_code=404, detail="File not found or is binary.")

    try:
        history = [
            {"role": msg.role, "content": msg.content}
            for msg in request.chat_history
        ]

        answer = chat_about_snippet(
            snippet=request.snippet,
            file_path=request.file_path,
            file_content=file_content,
            question=request.question,
            repo_analysis=analysis,
            chat_history=history,
        )

        return SnippetChatResponse(answer=answer)

    except Exception as e:
        logger.error(f"Error in snippet chat: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate response: {str(e)}",
        )
