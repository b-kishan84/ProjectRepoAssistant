"""
Repository cloning service — handles cloning GitHub repos via GitPython.
"""

import re
import shutil
import logging
from pathlib import Path

from git import Repo, GitCommandError

from backend.config import settings

logger = logging.getLogger(__name__)


def parse_repo_url(repo_url: str) -> tuple[str, str]:
    """
    Extract owner and repo name from a GitHub URL.

    Returns:
        (owner, repo_name)
    """
    # Clean URL
    url = repo_url.strip().rstrip("/")
    if url.endswith(".git"):
        url = url[:-4]

    match = re.match(r"https?://github\.com/([\w.\-]+)/([\w.\-]+)", url)
    if not match:
        raise ValueError(f"Invalid GitHub URL: {repo_url}")

    return match.group(1), match.group(2)


def get_clone_path(repo_url: str) -> Path:
    """Get the local path where the repo would be/is cloned."""
    owner, name = parse_repo_url(repo_url)
    return settings.CLONE_DIR / f"{owner}__{name}"


def build_clone_url(repo_url: str) -> str:
    """
    Build the actual git clone URL.
    If a GITHUB_TOKEN is configured, embed it for private repo access.
    """
    url = repo_url.strip().rstrip("/")
    if not url.endswith(".git"):
        url += ".git"

    if settings.GITHUB_TOKEN:
        # Insert token for authenticated access
        # https://github.com/... -> https://<token>@github.com/...
        url = url.replace("https://github.com/", f"https://{settings.GITHUB_TOKEN}@github.com/")

    return url


def clone_repo(repo_url: str) -> Path:
    """
    Clone a GitHub repository to the local clone directory.

    If the repo is already cloned, removes and re-clones it (MVP — no persistence).

    Args:
        repo_url: The GitHub repository URL.

    Returns:
        Path to the cloned repository directory.

    Raises:
        ValueError: If the URL is invalid.
        GitCommandError: If cloning fails.
    """
    clone_path = get_clone_path(repo_url)
    clone_url = build_clone_url(repo_url)

    # Ensure clone directory exists
    settings.CLONE_DIR.mkdir(parents=True, exist_ok=True)

    # Remove existing clone if present (MVP: fresh clone each time)
    if clone_path.exists():
        logger.info(f"Removing existing clone at {clone_path}")
        shutil.rmtree(clone_path)

    logger.info(f"Cloning {repo_url} -> {clone_path}")

    try:
        Repo.clone_from(
            clone_url,
            str(clone_path),
            depth=1,  # Shallow clone for speed
            no_checkout=False,
        )
        logger.info(f"Successfully cloned {repo_url}")
    except GitCommandError as e:
        logger.error(f"Failed to clone {repo_url}: {e}")
        # Clean up partial clone
        if clone_path.exists():
            shutil.rmtree(clone_path)
        raise

    return clone_path


def cleanup_repo(repo_url: str) -> None:
    """Remove a cloned repository from disk."""
    clone_path = get_clone_path(repo_url)
    if clone_path.exists():
        shutil.rmtree(clone_path)
        logger.info(f"Cleaned up {clone_path}")
