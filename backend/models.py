"""
Pydantic models for API request/response schemas.
"""

from pydantic import BaseModel, field_validator
import re


def clean_github_url(url: str) -> str:
    """Normalize a GitHub URL by removing trailing slashes and .git suffix."""
    v = url.strip().rstrip("/")
    if v.endswith(".git"):
        v = v[:-4]
    return v


class CloneRequest(BaseModel):
    """Request to analyze a GitHub repository."""
    repo_url: str

    @field_validator("repo_url")
    @classmethod
    def validate_github_url(cls, v: str) -> str:
        v = clean_github_url(v)
        # Validate it looks like a GitHub URL
        pattern = r"^https?://github\.com/[\w.\-]+/[\w.\-]+$"
        if not re.match(pattern, v):
            raise ValueError(
                "Invalid GitHub URL. Expected format: "
                "https://github.com/owner/repository"
            )
        return v


class ChatMessage(BaseModel):
    """A single message in chat history."""
    role: str  # "user" or "assistant"
    content: str


class ChatRequest(BaseModel):
    """Request to chat about a repository."""
    repo_url: str
    question: str
    chat_history: list[ChatMessage] = []


class ChatResponse(BaseModel):
    """Response from the chat endpoint."""
    answer: str


class SnippetChatRequest(BaseModel):
    """Request to chat about a specific code snippet."""
    repo_url: str
    file_path: str
    snippet: str
    question: str
    chat_history: list[ChatMessage] = []


class SnippetChatResponse(BaseModel):
    """Response from the snippet chat endpoint."""
    answer: str


class FileRequest(BaseModel):
    """Request to explain a specific file."""
    repo_url: str
    file_path: str


class RepoSummary(BaseModel):
    """Structured analysis of a repository."""
    name: str
    description: str
    languages: list[str]
    framework: str | None = None
    folder_structure: str
    entry_point: str | None = None
    config_files: list[str]
    important_files: dict[str, str]  # filename -> content
    ai_summary: str
    file_list: list[str] = []  # flat list of all files for browsing
