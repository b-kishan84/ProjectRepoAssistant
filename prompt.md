# AI GitHub Repository Explainer Chatbot

## Project Overview

Build an AI-powered chatbot that helps developers understand any public GitHub repository.

The user provides a GitHub repository URL, and the chatbot analyzes the repository, explains the project, and answers questions about the codebase in natural language.

The project should be built in **two phases**:

* **Version 1 (MVP):** Repository analysis without RAG.
* **Version 2:** Add Retrieval-Augmented Generation (RAG) using a vector database for scalable and accurate repository search.

---

# Version 1 (MVP)

## Goal

Build a working chatbot that can analyze small to medium-sized repositories and answer questions by reading repository files directly.

### Features

### 1. Accept a GitHub Repository URL

The user enters a public GitHub repository URL.

Example:

```
https://github.com/username/project
```

---

### 2. Clone the Repository

Clone the repository locally using GitPython.

Store it inside a temporary folder.

---

### 3. Analyze the Repository

Automatically detect:

* Programming language(s)
* Framework (if possible)
* Folder structure
* Entry point
* Configuration files

Read important files including:

* README.md
* requirements.txt
* package.json
* pyproject.toml
* Dockerfile
* docker-compose.yml
* Cargo.toml
* pom.xml
* .env.example

---

### 4. Generate a Project Summary

Generate a beginner-friendly explanation that includes:

* What the project does
* Main purpose
* Technologies used
* Key features
* Folder structure
* Entry point
* Installation instructions
* How to run the project

---

### 5. Explain Files

When the user selects or asks about a file, explain:

* What the file does
* Important functions/classes
* Inputs and outputs
* Business logic
* How it interacts with other files

Example:

User:

```
Explain src/auth/login.py
```

Assistant:

* Handles user authentication
* Validates credentials
* Creates JWT tokens
* Returns login response
* Used by the authentication API

---

### 6. Explain Folders

Example:

```
Explain the controllers folder
```

The chatbot should explain:

* Purpose of the folder
* What files belong there
* Relationship with the rest of the project

---

### 7. Chat with the Repository

The chatbot should answer questions like:

* What does this project do?
* Explain the authentication flow.
* Where is the database connection?
* Which file starts the application?
* Explain the API routes.
* Which files should I modify to add a feature?
* Explain this function.
* Summarize the README.
* Explain the folder structure.

For Version 1, the chatbot can directly read the required files when answering questions. A vector database is **not required**.

---

### Expected Version 1 Workflow

```
User
    │
    ▼
Enter GitHub URL
    │
    ▼
Clone Repository
    │
    ▼
Read Important Files
    │
    ▼
Analyze Folder Structure
    │
    ▼
Generate Summary
    │
    ▼
Chatbot Answers Questions
```

---

# Version 2 (Advanced)

## Goal

Improve the chatbot so it can efficiently understand **large repositories** using Retrieval-Augmented Generation (RAG).

Instead of reading files every time, create a searchable knowledge base.

---

### Additional Features

### 1. Chunk the Repository

Split source code into logical chunks.

Examples:

* One class
* One function
* README sections
* Configuration files

---

### 2. Generate Embeddings

Convert every chunk into embeddings using Sentence Transformers.

---

### 3. Store Embeddings

Store embeddings inside ChromaDB.

Each record should contain:

* File name
* Chunk
* Path
* Embedding

---

### 4. Semantic Search

When the user asks a question:

Example:

```
How does authentication work?
```

The chatbot should:

* Convert the question into an embedding.
* Search ChromaDB.
* Retrieve only the most relevant code chunks.
* Send those chunks to Gemini.

This improves speed, reduces token usage, and enables support for very large repositories.

---

### 5. Smarter Answers

The chatbot should now be able to:

* Trace execution across multiple files
* Explain relationships between modules
* Follow imports
* Explain call chains
* Identify where variables are used
* Compare files

---

### 6. Advanced Repository Intelligence

Support questions like:

* Show the authentication flow.
* Explain how requests reach the database.
* Where is JWT generated?
* Which files depend on this class?
* Find duplicate logic.
* Suggest refactoring opportunities.
* Find unused files.
* Explain the overall architecture.

---

### 7. Nice-to-Have Features

* Mermaid architecture diagrams
* Dependency graph
* Call graph
* README improvement suggestions
* Auto-generated documentation
* Complexity analysis
* TODO/FIXME detection
* Code quality suggestions
* Onboarding guide for new developers

---

### Expected Version 2 Workflow

```
User
    │
    ▼
Enter GitHub URL
    │
    ▼
Clone Repository
    │
    ▼
Parse Files
    │
    ▼
Split into Chunks
    │
    ▼
Generate Embeddings
    │
    ▼
Store in ChromaDB
    │
    ▼
User Asks Question
    │
    ▼
Semantic Search
    │
    ▼
Retrieve Relevant Chunks
    │
    ▼
Gemini Generates Answer
```

---

# Suggested Tech Stack

### Backend

* Python
* FastAPI

### Frontend

* Streamlit

### AI Model

* Google Gemini

### Git Operations

* GitPython

### Parsing

* pathlib
* os

### Embeddings (Version 2)

* Sentence Transformers

### Vector Database (Version 2)

* ChromaDB

### Optional

* tree-sitter (better code parsing)

---

# Final Goal

The finished application should act as an **AI mentor for any GitHub repository**.

A developer should be able to paste a repository URL and immediately:

* Understand what the project does.
* Learn how the codebase is organized.
* Explore any file or folder.
* Ask natural language questions about the code.
* Understand complex workflows without manually reading hundreds of files.
* Scale to large repositories using RAG in Version 2.
