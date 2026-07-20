"""
Gemini AI service — handles all interactions with Google Gemini for
generating summaries and chatting about repositories.
"""

import logging
# pyrefly: ignore [missing-import]
from google import genai

from backend.config import settings

logger = logging.getLogger(__name__)

# Initialize client (lazy — created on first use)
_client: genai.Client | None = None


def _get_client() -> genai.Client:
    """Get or create the Gemini client."""
    global _client
    if _client is None:
        settings.validate()
        _client = genai.Client(api_key=settings.GOOGLE_API_KEY)
        logger.info("Gemini client initialized")
    return _client


# ─── System Prompts ────────────────────────────────────────────────────────────

SUMMARY_SYSTEM_PROMPT = """You are an expert software engineer and technical writer.
Your job is to analyze a GitHub repository and generate a clear, beginner-friendly
project summary.

Given repository metadata and file contents, create a well-structured summary that includes:
1. **What the project does** — a clear, one-paragraph explanation
2. **Main purpose** — why this project exists
3. **Technologies used** — languages, frameworks, libraries
4. **Key features** — what the project offers
5. **Folder structure** — explain the organization
6. **Entry point** — where the application starts
7. **Installation instructions** — how to set it up (based on config files)
8. **How to run** — commands to start the project

Write in a friendly, approachable tone. Use markdown formatting with headers,
bullet points, and code blocks where appropriate. Assume the reader is a developer
who is seeing this project for the first time."""

CHAT_SYSTEM_PROMPT = """You are an expert code mentor helping a developer understand a GitHub repository.
You have access to the repository's metadata, structure, and file contents.

Rules:
- Answer questions accurately based on the provided repository context.
- If you can see the relevant code, explain it clearly.
- If you don't have enough context to answer, say so honestly and suggest which
  file or area the user should look at.
- Use code snippets in your answers when helpful.
- Format your responses with markdown for readability.
- Be concise but thorough.
- When explaining code, mention the file path so the user can find it.
- If asked about something not in the repository context, clearly state that."""

FILE_EXPLAIN_SYSTEM_PROMPT = """You are an expert code reviewer and mentor.
Given a source code file from a GitHub repository, provide a clear explanation that includes:

1. **Purpose** — What this file does in the project
2. **Key components** — Important functions, classes, or variables
3. **Inputs & outputs** — What data flows in and out
4. **Business logic** — The core logic implemented
5. **Dependencies** — What this file imports or depends on
6. **Connections** — How this file relates to other parts of the project

Be concise, clear, and beginner-friendly. Use markdown formatting."""

SNIPPET_CHAT_SYSTEM_PROMPT = """You are a hyper-focused, context-aware AI code assistant.
The user has highlighted a specific block of code inside a file. Your job is to answer
questions **only about that selected snippet**, using the full file as background context.

Capabilities you should demonstrate:
- Explain code line-by-line or at a high level.
- Describe the purpose of any function, variable, class, or condition.
- Explain why specific logic or patterns are used.
- Identify where referenced functions/variables are defined or used elsewhere in the file.
- Find potential bugs, edge cases, or performance issues.
- Suggest refactoring, optimizations, or cleaner alternatives.
- Generate docstrings, comments, or pseudocode for the snippet.

Rules:
- Focus your answer on the SELECTED SNIPPET only. Use the rest of the file for context
  but do not explain the entire file unless asked.
- Use code blocks and markdown formatting for clarity.
- When suggesting changes, show the improved code alongside the original.
- Be concise but thorough. Avoid unnecessary preambles.
- If the snippet is too small or unclear to answer meaningfully, say so."""


# ─── Public Functions ──────────────────────────────────────────────────────────

def generate_summary(repo_analysis: dict) -> str:
    """
    Generate an AI-powered project summary from repository analysis data.

    Args:
        repo_analysis: Dictionary from repo_analyzer.analyze_repo()

    Returns:
        Markdown-formatted project summary string.
    """
    client = _get_client()

    # Build the context prompt with repo information
    context_parts = [
        f"Repository: {repo_analysis['name']}",
        f"Languages: {', '.join(repo_analysis['languages'][:10])}",
    ]

    if repo_analysis.get("framework"):
        context_parts.append(f"Framework: {repo_analysis['framework']}")

    if repo_analysis.get("entry_point"):
        context_parts.append(f"Entry point: {repo_analysis['entry_point']}")

    context_parts.append(f"\nFolder Structure:\n```\n{repo_analysis['folder_structure']}\n```")

    if repo_analysis.get("config_files"):
        context_parts.append(f"\nConfig files: {', '.join(repo_analysis['config_files'][:15])}")

    # Add important file contents
    important_files = repo_analysis.get("important_files", {})
    for filename, content in important_files.items():
        # Truncate very large files
        truncated = content[:5000] if len(content) > 5000 else content
        context_parts.append(f"\n--- {filename} ---\n{truncated}")

    context = "\n".join(context_parts)

    prompt = f"""Analyze this repository and generate a comprehensive project summary.

{context}

Generate a clear, beginner-friendly project summary following the format in your instructions."""

    logger.info(f"Generating summary for {repo_analysis['name']}")

    response = client.models.generate_content(
        model=settings.GEMINI_MODEL,
        contents=prompt,
        config=genai.types.GenerateContentConfig(
            system_instruction=SUMMARY_SYSTEM_PROMPT,
            temperature=0.3,
            max_output_tokens=4096,
        ),
    )

    return response.text


def chat_with_repo(
    question: str,
    repo_analysis: dict,
    chat_history: list[dict] | None = None,
    file_content: str | None = None,
) -> str:
    """
    Answer a user's question about a repository using Gemini.

    Args:
        question: The user's question.
        repo_analysis: Dictionary from repo_analyzer.analyze_repo()
        chat_history: List of {"role": str, "content": str} messages.
        file_content: Optional content of a specific file the user is asking about.

    Returns:
        Gemini's answer as a string.
    """
    client = _get_client()

    # Build context
    context_parts = [
        f"Repository: {repo_analysis['name']}",
        f"Languages: {', '.join(repo_analysis['languages'][:10])}",
    ]

    if repo_analysis.get("framework"):
        context_parts.append(f"Framework: {repo_analysis['framework']}")

    if repo_analysis.get("entry_point"):
        context_parts.append(f"Entry point: {repo_analysis['entry_point']}")

    context_parts.append(f"\nFolder Structure:\n```\n{repo_analysis['folder_structure']}\n```")

    # Add important file contents (summarized to save tokens)
    important_files = repo_analysis.get("important_files", {})
    for filename, content in important_files.items():
        truncated = content[:3000] if len(content) > 3000 else content
        context_parts.append(f"\n--- {filename} ---\n{truncated}")

    # Add specific file content if provided
    if file_content:
        context_parts.append(f"\n--- Requested File Content ---\n{file_content}")

    context = "\n".join(context_parts)

    # Build messages list for multi-turn conversation
    messages_for_prompt = []

    # Add conversation history
    if chat_history:
        for msg in chat_history[-10:]:  # Keep last 10 messages for context
            messages_for_prompt.append(f"{msg['role'].upper()}: {msg['content']}")

    history_text = "\n".join(messages_for_prompt) if messages_for_prompt else ""

    prompt = f"""Repository Context:
{context}

{f"Conversation History:{chr(10)}{history_text}{chr(10)}" if history_text else ""}
User Question: {question}

Provide a helpful, accurate answer based on the repository context above."""

    logger.info(f"Chat question for {repo_analysis['name']}: {question[:80]}...")

    response = client.models.generate_content(
        model=settings.GEMINI_MODEL,
        contents=prompt,
        config=genai.types.GenerateContentConfig(
            system_instruction=CHAT_SYSTEM_PROMPT,
            temperature=0.4,
            max_output_tokens=4096,
        ),
    )

    return response.text


def explain_file(
    file_path: str,
    file_content: str,
    repo_analysis: dict,
) -> str:
    """
    Generate an AI explanation of a specific file.

    Args:
        file_path: Relative path to the file in the repo.
        file_content: The file's content.
        repo_analysis: Dictionary from repo_analyzer.analyze_repo()

    Returns:
        Markdown-formatted explanation of the file.
    """
    client = _get_client()

    prompt = f"""Repository: {repo_analysis['name']}
Languages: {', '.join(repo_analysis['languages'][:5])}
Framework: {repo_analysis.get('framework', 'Unknown')}

File path: {file_path}

File content:
```
{file_content[:8000]}
```

Explain this file following the format in your instructions."""

    logger.info(f"Explaining file: {file_path}")

    response = client.models.generate_content(
        model=settings.GEMINI_MODEL,
        contents=prompt,
        config=genai.types.GenerateContentConfig(
            system_instruction=FILE_EXPLAIN_SYSTEM_PROMPT,
            temperature=0.3,
            max_output_tokens=3000,
        ),
    )

    return response.text


def chat_about_snippet(
    snippet: str,
    file_path: str,
    file_content: str,
    question: str,
    repo_analysis: dict,
    chat_history: list[dict] | None = None,
) -> str:
    """
    Answer a user's question about a specific highlighted code snippet.

    Args:
        snippet: The exact code the user highlighted.
        file_path: Path of the file containing the snippet.
        file_content: Full content of the file for context.
        question: The user's question about the snippet.
        repo_analysis: Dictionary from repo_analyzer.analyze_repo()
        chat_history: Previous messages in this snippet chat.

    Returns:
        Gemini's answer as a string.
    """
    client = _get_client()

    # Build conversation history text
    messages_for_prompt = []
    if chat_history:
        for msg in chat_history[-8:]:  # Keep last 8 messages
            messages_for_prompt.append(f"{msg['role'].upper()}: {msg['content']}")
    history_text = "\n".join(messages_for_prompt) if messages_for_prompt else ""

    prompt = f"""Repository: {repo_analysis['name']}
Languages: {', '.join(repo_analysis['languages'][:5])}
Framework: {repo_analysis.get('framework', 'Unknown')}

File: {file_path}

Full file content (for context):
```
{file_content[:10000]}
```

--- SELECTED SNIPPET (user highlighted this) ---
```
{snippet}
```
--- END SELECTED SNIPPET ---

{f"Conversation History:{chr(10)}{history_text}{chr(10)}" if history_text else ""}
User Question about the selected snippet: {question}

Answer the question focusing specifically on the selected snippet."""

    logger.info(f"Snippet chat for {file_path}: {question[:80]}...")

    response = client.models.generate_content(
        model=settings.GEMINI_MODEL,
        contents=prompt,
        config=genai.types.GenerateContentConfig(
            system_instruction=SNIPPET_CHAT_SYSTEM_PROMPT,
            temperature=0.4,
            max_output_tokens=4096,
        ),
    )

    return response.text
