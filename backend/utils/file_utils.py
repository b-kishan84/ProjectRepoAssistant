"""
File utility functions — extension mapping, tree generation, binary detection.
"""

from pathlib import Path

from backend.config import settings


# Map file extensions to language names
EXTENSION_LANGUAGE_MAP: dict[str, str] = {
    ".py": "Python",
    ".js": "JavaScript",
    ".ts": "TypeScript",
    ".jsx": "JavaScript (React)",
    ".tsx": "TypeScript (React)",
    ".java": "Java",
    ".kt": "Kotlin",
    ".go": "Go",
    ".rs": "Rust",
    ".rb": "Ruby",
    ".php": "PHP",
    ".cs": "C#",
    ".cpp": "C++",
    ".c": "C",
    ".h": "C/C++ Header",
    ".hpp": "C++ Header",
    ".swift": "Swift",
    ".dart": "Dart",
    ".scala": "Scala",
    ".r": "R",
    ".R": "R",
    ".lua": "Lua",
    ".sh": "Shell",
    ".bash": "Shell",
    ".zsh": "Shell",
    ".ps1": "PowerShell",
    ".html": "HTML",
    ".css": "CSS",
    ".scss": "SCSS",
    ".sass": "Sass",
    ".less": "Less",
    ".sql": "SQL",
    ".yaml": "YAML",
    ".yml": "YAML",
    ".json": "JSON",
    ".xml": "XML",
    ".md": "Markdown",
    ".toml": "TOML",
    ".ini": "INI",
    ".cfg": "Config",
    ".vue": "Vue",
    ".svelte": "Svelte",
    ".ex": "Elixir",
    ".exs": "Elixir",
    ".erl": "Erlang",
    ".zig": "Zig",
    ".nim": "Nim",
    ".pl": "Perl",
    ".pm": "Perl",
    ".m": "Objective-C",
    ".mm": "Objective-C++",
    ".proto": "Protocol Buffers",
    ".tf": "Terraform",
    ".dockerfile": "Dockerfile",
}

# Binary file extensions to skip
BINARY_EXTENSIONS: set[str] = {
    ".png", ".jpg", ".jpeg", ".gif", ".bmp", ".ico", ".svg",
    ".webp", ".mp3", ".mp4", ".avi", ".mov", ".wav",
    ".pdf", ".zip", ".tar", ".gz", ".rar", ".7z",
    ".exe", ".dll", ".so", ".dylib", ".bin",
    ".woff", ".woff2", ".ttf", ".eot", ".otf",
    ".pyc", ".pyo", ".class", ".o", ".obj",
    ".db", ".sqlite", ".sqlite3",
    ".lock",
}


def is_binary_file(file_path: Path) -> bool:
    """Check if a file is likely binary based on extension or content."""
    if file_path.suffix.lower() in BINARY_EXTENSIONS:
        return True
    # Quick content check for files without recognized extensions
    try:
        with open(file_path, "rb") as f:
            chunk = f.read(1024)
            # If there are null bytes, it's likely binary
            return b"\x00" in chunk
    except (OSError, PermissionError):
        return True


def should_ignore(path: Path) -> bool:
    """Check if a path should be ignored during traversal."""
    name = path.name
    if name in settings.IGNORE_DIRS or name in settings.IGNORE_FILES:
        return True
    if name.startswith(".") and name not in {".env.example", ".gitignore", ".dockerignore"}:
        return True
    return False


def get_file_tree(
    root: Path,
    prefix: str = "",
    max_depth: int | None = None,
    current_depth: int = 0,
) -> str:
    """
    Generate a tree-like string representation of a directory structure.

    Example output:
        ├── src/
        │   ├── main.py
        │   └── utils.py
        └── README.md
    """
    if max_depth is None:
        max_depth = settings.MAX_TREE_DEPTH

    if current_depth >= max_depth:
        return ""

    lines: list[str] = []

    try:
        entries = sorted(
            root.iterdir(),
            key=lambda p: (not p.is_dir(), p.name.lower()),
        )
    except PermissionError:
        return ""

    # Filter out ignored entries
    entries = [e for e in entries if not should_ignore(e)]

    for i, entry in enumerate(entries):
        is_last = i == len(entries) - 1
        connector = "└── " if is_last else "├── "
        new_prefix = prefix + ("    " if is_last else "│   ")

        if entry.is_dir():
            lines.append(f"{prefix}{connector}{entry.name}/")
            subtree = get_file_tree(entry, new_prefix, max_depth, current_depth + 1)
            if subtree:
                lines.append(subtree)
        else:
            lines.append(f"{prefix}{connector}{entry.name}")

    return "\n".join(lines)


def get_all_files(root: Path) -> list[str]:
    """Get a flat list of all non-ignored file paths relative to root."""
    files: list[str] = []

    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        # Check if any parent directory should be ignored
        if any(should_ignore(parent) for parent in path.relative_to(root).parents):
            continue
        if should_ignore(path):
            continue
        if is_binary_file(path):
            continue
        files.append(str(path.relative_to(root)))

    return files


def safe_read_file(file_path: Path, max_size: int | None = None) -> str | None:
    """
    Read a file safely, returning None if it's binary, too large, or unreadable.
    """
    if max_size is None:
        max_size = settings.MAX_FILE_SIZE_BYTES

    if not file_path.exists() or not file_path.is_file():
        return None

    if is_binary_file(file_path):
        return None

    try:
        size = file_path.stat().st_size
        if size > max_size:
            return f"[File too large: {size:,} bytes — skipped]"

        return file_path.read_text(encoding="utf-8", errors="replace")
    except (OSError, PermissionError, UnicodeDecodeError):
        return None
