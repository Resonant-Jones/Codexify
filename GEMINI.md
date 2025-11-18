# Codexify Project Overview

This document provides a comprehensive overview of the Codexify project, intended as a guide for AI agents and developers.

## 1. Project Overview

Codexify is a local-first, AI-powered conversation and knowledge management platform. It combines retrieval-augmented generation (RAG), semantic memory, and multi-provider LLM orchestration into a unified system. It's designed for developers, researchers, and organizations who need intelligent conversation management with enterprise-grade data sovereignty.

### 1.1. Key Technologies

- **Backend:** Python, FastAPI, SQLAlchemy, Alembic, PostgreSQL, Neo4j, ChromaDB, LangChain
- **Frontend:** React, TypeScript, Vite, Tailwind CSS, Tauri (for desktop)
- **AI/ML:** Groq, OpenAI, Anthropic, Google Gemini, Sentence Transformers, FAISS, Torch
- **Dev Tools:** Docker, pnpm, Ruff, Black, MyPy, pytest, pre-commit

### 1.2. Architecture

Codexify follows a multi-tier architecture with a clear separation of concerns and event-driven communication. The main components are:

- **Frontend:** A React and TypeScript-based user interface.
- **API Gateway:** A FastAPI server that acts as the entry point for the backend.
- **Core Services:** A set of services for AI routing, memory management, chat orchestration, RAG, connectors, and plugins.
- **Storage Layer:** A hybrid database strategy using PostgreSQL for structured data, Neo4j for knowledge graphs, and ChromaDB for vectors.
- **External Services:** LLM providers and integrations with third-party services like GitHub, Google Drive, and Notion.

## 2. Building and Running

### 2.1. Prerequisites

- Docker (20.10+) and Docker Compose (v2.0+)
- Node.js (20+) with pnpm (9+)
- Python (3.10, 3.11, or 3.12)
- Make (optional, for convenience commands)

### 2.2. Getting Started

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/Resonant-Jones/Codexify.git
    cd Codexify
    ```

2.  **Set up the environment:**
    ```bash
    cp .env.example .env
    nano .env
    ```
    *Edit `.env` with your API keys (at minimum, set `GROQ_API_KEY` or `OPENAI_API_KEY`).*

3.  **Start the stack:**
    - **Using Docker Compose (recommended):**
      ```bash
      docker-compose up -d
      ```
    - **Using Make:**
      ```bash
      make dev
      ```

4.  **Verify the installation:**
    ```bash
    curl http://localhost:8888/healthz
    open http://localhost:5173
    open http://localhost:8888/docs
    ```

5.  **Run migrations:**
    Migrations run automatically via the `migrator` service in Docker Compose. To run manually:
    ```bash
    docker-compose exec backend alembic upgrade head
    ```

## 3. Development Conventions

### 3.1. Backend

- **Code Style:** The project uses `black` for code formatting, `isort` for import sorting, and `ruff` for linting.
- **Type Checking:** `mypy` is used for static type checking.
- **Testing:** The project uses `pytest` for testing.
- **Dependencies:** Backend dependencies are managed with `pip` and are listed in `backend/requirements.txt`.

### 3.2. Frontend

- **Package Manager:** The project uses `pnpm` for managing frontend dependencies.
- **Code Style:** The project uses `eslint` for linting and `prettier` for code formatting.
- **Testing:** The project uses `vitest` for unit testing and `cypress` for end-to-end testing.
- **Dependencies:** Frontend dependencies are managed in `frontend/package.json`.

### 3.3. Commits

The project follows the [Conventional Commits](https://www.conventionalcommits.org/) specification.
