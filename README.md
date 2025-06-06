# guardian-backend

FastAPI backend for Companion memory, Codex fragments, and real-time chat orchestration.

This is the server-side infrastructure for the Guardian system. It handles memory persistence, Codex fragment delivery, user authentication, and API routing for AI Companion interactions within ThreadSpace.

> “The backend is the memory of the system, the breath between words.”

---

## 🚀 Quickstart

**1. Clone & enter the repo**
```bash
git clone <your-repo-url>
cd guardian-backend
```

**2. Create and activate a virtual environment**
```bash
python -m venv .venv
source .venv/bin/activate
```

**3. Install dependencies**
```bash
pip install -r requirements.txt
```

**4. Set up environment variables**
Copy `.env.example` to `.env` and fill in your secrets (e.g., `GENAI_API_KEY`).

**5. Launch the server**
```bash
uvicorn guardian.main:app --reload
```
Visit [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs) for interactive API docs.

---

## 🛠️ Core Features

- **Memory Persistence:** Store and retrieve conversation fragments by user/session/tag.
- **Codex Fragments:** Structured knowledge, rituals, and lore delivery endpoints.
- **Real-time Chat Orchestration:** Passes prompts to language models (Gemini, OpenAI, etc).
- **CLI Tools:** Typer-powered command-line interface for direct DB and memory operations.
- **Authentication:** API key-based (configurable via env).

---

## 💡 Example API Usage

**Check health**
```bash
curl http://127.0.0.1:8000/health
```

**Chat with Companion**
```bash
curl -X POST http://127.0.0.1:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Tell me a myth about memory."}'
```

**(More endpoints: /history, /summarize, etc. Document as you add them)**

---

## 🧪 Running Tests

```bash
pytest
```

---

## ⚙️ Configuration

- All secrets and config loaded from `.env`.
- Required: `GENAI_API_KEY`, etc.

---

## 🤝 Contributing

PRs and mythic collaborations welcome. Please run tests and add docstrings.
