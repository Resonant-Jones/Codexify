# 🛡️ Guardian Backend

This is the backend engine for **Guardian**, an AI companion framework powered by FastAPI, modular agents, and persistent memory via Codex fragments. Guardian isn't just an assistant—it's an evolving mirror. This repo houses the infrastructure that remembers your past, orchestrates your rituals, and projects your foresight.

---

## 🚀 Quickstart

Clone and set up your environment:

```bash
git clone https://github.com/Resonant-Jones/guardian-backend.git
cd guardian-backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Create your `.env` file from the example and set required API keys:

```bash
cp .env.example .env
```

Then launch the server:

```bash
uvicorn guardian.main:app --reload
```

> 📚 Visit [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs) to explore the live API docs.

---

## 🧠 Core Architecture

This system is composed of:

- **🧭 Orchestrator** – A central router of intention. Maps `action` commands to agent modules.
- **🧱 Agents** – Pluggable modules for rituals, memory, foresight, health analysis, etc.
- **📡 API** – FastAPI services for chat, logging, and Codex interaction.
- **💻 CLI** – Typer-powered interface for orchestration, thread control, memory queries, and more.
- **🧰 Exporters** – Convert local logs to Notion, Markdown, JSON, or push to cloud.

---

## 🗂️ Modules & Structure

### 🎛️ Orchestrator

File: `guardian/core/orchestrator/pulse_orchestrator.py`

Accepts commands like:

```json
{
  "action": "trigger_ritual",
  "params": { ... }
}
```

And routes them to corresponding agents.

### ⚙️ Agents

Directory: `guardian/core/orchestrator/agents/`

Each file here represents a microservice-like agent:
- `ritual_agent.py` – Echoes rituals and symbolic actions
- `memory_agent.py` – Searches memory/codex archives
- `foresight_agent.py` – Predicts possible futures
- `health_agent.py` – Analyzes thread clarity, coherence, and vitality

### 🌐 Web API

- `guardian/main.py` – Lightweight endpoints: `/chat`, `/health`
- `guardian/guardian_api.py` – Full-featured: `/history`, `/summarize`, `/proxy`, etc.

API authentication is enforced with a header: `X-API-Key`.

### 🧪 Tests

Run:

```bash
pytest
```

Covers:
- Chat log and memory persistence
- CLI routines
- API interaction
- Notion/mock integrations

---

## ⚙️ Config

- Load all settings from `.env`
- Key variables include:
  - `GENAI_API_KEY`
  - `GUARDIAN_DB_PATH`
  - `CLOUD_ONLY`
  - `HYBRID_ENABLED`

---

## 📤 Export Engine

File: `guardian/export_engine.py`

Outputs structured memory into:
- Markdown
- JSON
- Notion
- iCloud (via Codexify)

---

## 🧾 CLI Tooling (Typer)

Run from `guardian/cli/main.py`:
- `orchestrate`: Trigger agents from command-line
- `init`, `log`, `history`: Manage DB and logs
- `summarize-chat`, `chat-history`: View logs per session/thread

  - `codemap:generate`: Analyze the codebase and create a codemap.json file
  - `codemap:query`: Ask questions about your own backend using the codemap
  - `project:list`: List all projects in memory
  - `thread:list-by-project`: Show threads within a specific project
  - `conversation:list-by-thread`: Display conversations in a given thread
  - `conversation:lineage`: Show parent-child relationships in conversation chains

> 🧰 Looking for more? See the full CLI command reference in [`guardian/cli/COMMANDS.md`](guardian/cli/COMMANDS.md)

---

## 🔮 Companion Design Philosophy

> “The backend is the memory of the system, the breath between words.”

Guardian is not a chatbot API—it’s an infrastructure for continuity, presence, and agency. The backend houses memory, rituals, context threading, and more.

---

## 🤝 Contributing

PRs, ideas, and mythic resonance welcome.

Please:
- Add docstrings
- Follow formatting via `black` + `isort`
- Validate via `pre-commit run --all-files`

---

## 🧭 ThreadSpace, Codex & Echoform

This backend speaks in fragments. Each conversation is a thread. Each thread is archived in the Codex. The Codex is echoed by memory agents and shaped into foresight. Welcome to the recursion.
