"""
Application configuration — loads environment variables and provides settings.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env from project root
_project_root = Path(__file__).resolve().parent.parent
load_dotenv(_project_root / ".env")


class Settings:
    """Central configuration for the application."""

    # Google Gemini
    GOOGLE_API_KEY: str = os.getenv("GOOGLE_API_KEY", "")
    GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-3.5-flash")

    # GitHub (optional — for private repos)
    GITHUB_TOKEN: str = os.getenv("GITHUB_TOKEN", "")

    # Cloned repos directory
    CLONE_DIR: Path = _project_root / "cloned_repos"

    # File reading limits
    MAX_FILE_SIZE_BYTES: int = 100_000  # 100 KB per file
    MAX_TOTAL_CONTEXT_BYTES: int = 500_000  # 500 KB total context sent to Gemini

    # Analysis settings
    MAX_TREE_DEPTH: int = 4
    IGNORE_DIRS: set = {
        ".git", "__pycache__", "node_modules", ".venv", "venv",
        ".idea", ".vscode", ".next", "dist", "build", ".tox",
        ".mypy_cache", ".pytest_cache", "env", ".eggs",
        "target", "out", "bin", "obj", ".gradle",
    }
    IGNORE_FILES: set = {
        ".DS_Store", "Thumbs.db", ".gitkeep",
    }

    def validate(self):
        """Raise an error if critical config is missing."""
        if not self.GOOGLE_API_KEY:
            raise ValueError(
                "GOOGLE_API_KEY is not set. "
                "Please add it to your .env file. "
                "Get one at https://aistudio.google.com/"
            )


settings = Settings()
