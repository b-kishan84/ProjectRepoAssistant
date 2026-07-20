"""
Repository analysis service — detects languages, frameworks, entry points,
reads important files, and builds the folder structure.
"""

import logging
from collections import Counter
from pathlib import Path

from backend.config import settings
from backend.utils.file_utils import (
    EXTENSION_LANGUAGE_MAP,
    get_file_tree,
    get_all_files,
    safe_read_file,
    should_ignore,
    is_binary_file,
)

logger = logging.getLogger(__name__)


# Files that are important for understanding a project
IMPORTANT_FILES: list[str] = [
    "README.md",
    "readme.md",
    "README.rst",
    "requirements.txt",
    "package.json",
    "pyproject.toml",
    "setup.py",
    "setup.cfg",
    "Cargo.toml",
    "pom.xml",
    "build.gradle",
    "go.mod",
    "Gemfile",
    "composer.json",
    "Dockerfile",
    "docker-compose.yml",
    "docker-compose.yaml",
    ".env.example",
    "Makefile",
    "Procfile",
    "app.yaml",
    "netlify.toml",
    "vercel.json",
]

# Framework detection rules: (marker_file, framework_name)
FRAMEWORK_MARKERS: list[tuple[str, str]] = [
    # Python
    ("manage.py", "Django"),
    ("django", "Django"),  # directory
    ("flask", "Flask"),
    ("app/__init__.py", "Flask"),
    ("fastapi", "FastAPI"),
    ("streamlit", "Streamlit"),
    ("celery.py", "Celery"),
    # JavaScript / TypeScript
    ("next.config.js", "Next.js"),
    ("next.config.mjs", "Next.js"),
    ("next.config.ts", "Next.js"),
    ("nuxt.config.js", "Nuxt.js"),
    ("nuxt.config.ts", "Nuxt.js"),
    ("angular.json", "Angular"),
    ("vue.config.js", "Vue.js"),
    ("svelte.config.js", "SvelteKit"),
    ("gatsby-config.js", "Gatsby"),
    ("remix.config.js", "Remix"),
    ("astro.config.mjs", "Astro"),
    ("vite.config.js", "Vite"),
    ("vite.config.ts", "Vite"),
    ("webpack.config.js", "Webpack"),
    ("tailwind.config.js", "Tailwind CSS"),
    ("tailwind.config.ts", "Tailwind CSS"),
    # Ruby
    ("Gemfile", "Ruby on Rails"),
    ("config/routes.rb", "Ruby on Rails"),
    # Rust
    ("Cargo.toml", "Rust/Cargo"),
    # Go
    ("go.mod", "Go Modules"),
    # Java
    ("pom.xml", "Maven"),
    ("build.gradle", "Gradle"),
    # Mobile
    ("pubspec.yaml", "Flutter"),
    ("Podfile", "iOS (CocoaPods)"),
    # Other
    ("terraform", "Terraform"),
    (".github/workflows", "GitHub Actions"),
]

# Common entry point filenames
ENTRY_POINT_CANDIDATES: list[str] = [
    # Python
    "main.py", "app.py", "run.py", "server.py", "manage.py",
    "wsgi.py", "asgi.py",
    # JavaScript/TypeScript
    "index.js", "index.ts", "app.js", "app.ts",
    "server.js", "server.ts", "main.js", "main.ts",
    # Go
    "main.go", "cmd/main.go",
    # Rust
    "src/main.rs", "src/lib.rs",
    # Java
    "src/main/java/Main.java",
    # Ruby
    "config.ru", "app.rb",
    # C/C++
    "main.c", "main.cpp",
]


def detect_languages(repo_path: Path) -> list[str]:
    """
    Detect programming languages used in the repository by analyzing file extensions.

    Returns:
        List of language names sorted by frequency (most common first).
    """
    extension_counts: Counter[str] = Counter()

    for file_path in repo_path.rglob("*"):
        if not file_path.is_file():
            continue
        # Skip ignored directories
        try:
            rel = file_path.relative_to(repo_path)
        except ValueError:
            continue
        if any(part in settings.IGNORE_DIRS for part in rel.parts):
            continue

        ext = file_path.suffix.lower()
        if ext in EXTENSION_LANGUAGE_MAP:
            language = EXTENSION_LANGUAGE_MAP[ext]
            extension_counts[language] += 1

    # Return languages sorted by count, excluding markup/config if there's actual code
    code_languages = []
    config_languages = []
    config_set = {"JSON", "YAML", "TOML", "INI", "Config", "Markdown", "XML"}

    for lang, _count in extension_counts.most_common():
        if lang in config_set:
            config_languages.append(lang)
        else:
            code_languages.append(lang)

    # Return code languages first, then config
    return code_languages + config_languages


def detect_framework(repo_path: Path) -> str | None:
    """
    Detect the primary framework by checking for known marker files.

    Returns:
        Framework name or None if not detected.
    """
    detected: list[str] = []

    for marker, framework in FRAMEWORK_MARKERS:
        marker_path = repo_path / marker
        if marker_path.exists():
            if framework not in detected:
                detected.append(framework)

    # Also check package.json for framework dependencies
    pkg_json_path = repo_path / "package.json"
    if pkg_json_path.exists():
        try:
            import json
            content = pkg_json_path.read_text(encoding="utf-8", errors="replace")
            pkg = json.loads(content)
            deps = {}
            deps.update(pkg.get("dependencies", {}))
            deps.update(pkg.get("devDependencies", {}))

            framework_deps = {
                "react": "React",
                "next": "Next.js",
                "vue": "Vue.js",
                "nuxt": "Nuxt.js",
                "@angular/core": "Angular",
                "svelte": "Svelte",
                "express": "Express.js",
                "fastify": "Fastify",
                "nestjs": "NestJS",
                "@nestjs/core": "NestJS",
                "electron": "Electron",
            }
            for dep, fw_name in framework_deps.items():
                if dep in deps and fw_name not in detected:
                    detected.append(fw_name)
        except (json.JSONDecodeError, OSError):
            pass

    if not detected:
        return None

    return ", ".join(detected[:3])  # Return top 3 at most


def find_entry_point(repo_path: Path) -> str | None:
    """
    Find the likely entry point of the project.

    Returns:
        Relative path to the entry point, or None.
    """
    for candidate in ENTRY_POINT_CANDIDATES:
        entry = repo_path / candidate
        if entry.exists():
            return candidate

    # Fallback: check src/ directory for common entry points
    src_dir = repo_path / "src"
    if src_dir.is_dir():
        for candidate in ENTRY_POINT_CANDIDATES:
            name = Path(candidate).name
            entry = src_dir / name
            if entry.exists():
                return f"src/{name}"

    return None


def read_important_files(repo_path: Path) -> dict[str, str]:
    """
    Read the content of important/notable files in the repository.

    Returns:
        Dict mapping filename to its content.
    """
    result: dict[str, str] = {}

    for filename in IMPORTANT_FILES:
        file_path = repo_path / filename
        content = safe_read_file(file_path)
        if content is not None:
            result[filename] = content

    return result


def get_config_files(repo_path: Path) -> list[str]:
    """Get a list of configuration files present in the repo."""
    config_patterns = [
        "*.toml", "*.yaml", "*.yml", "*.json", "*.cfg", "*.ini",
        "*.conf", "*.config", "*.xml",
        "Dockerfile*", "docker-compose*", "Makefile", "Procfile",
        ".env*", ".eslintrc*", ".prettierrc*", "tsconfig*",
        "jest.config*", "babel.config*", "webpack.config*",
    ]
    config_files: list[str] = []

    for pattern in config_patterns:
        for match in repo_path.glob(pattern):
            if match.is_file() and not should_ignore(match):
                rel = str(match.relative_to(repo_path))
                if rel not in config_files:
                    config_files.append(rel)

    return sorted(config_files)


def analyze_repo(repo_path: Path) -> dict:
    """
    Run full analysis on a cloned repository.

    Returns:
        Dictionary with all analysis results ready to be passed to Gemini.
    """
    repo_name = repo_path.name.replace("__", "/")

    logger.info(f"Analyzing repository: {repo_name}")

    languages = detect_languages(repo_path)
    framework = detect_framework(repo_path)
    folder_structure = get_file_tree(repo_path)
    entry_point = find_entry_point(repo_path)
    important_files = read_important_files(repo_path)
    config_files = get_config_files(repo_path)
    file_list = get_all_files(repo_path)

    # Extract description from README if available
    description = ""
    for readme_key in ["README.md", "readme.md", "README.rst"]:
        if readme_key in important_files:
            readme_content = important_files[readme_key]
            # Take first non-empty, non-heading paragraph
            lines = readme_content.split("\n")
            for line in lines:
                stripped = line.strip()
                if stripped and not stripped.startswith("#") and not stripped.startswith("="):
                    description = stripped[:200]
                    break
            break

    analysis = {
        "name": repo_name,
        "description": description,
        "languages": languages,
        "framework": framework,
        "folder_structure": folder_structure,
        "entry_point": entry_point,
        "important_files": important_files,
        "config_files": config_files,
        "file_list": file_list,
    }

    logger.info(
        f"Analysis complete: {len(languages)} languages, "
        f"framework={framework}, {len(important_files)} important files, "
        f"{len(file_list)} total files"
    )

    return analysis
