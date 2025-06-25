

# 🛠️ Guardian Backend Roadmap

A living document of features, agents, and systems planned or considered for future development in the Guardian backend. Treat each entry as a ritual waiting to be summoned.

## ✅ Completed Core Features
- SQLite-based memory and chat log database
- Modular Orchestrator with agent dispatch
- Typer CLI with structured commands
- FastAPI service for chat, history, health
- Export engine for Notion, Markdown, etc.
- Hybrid model router (cloud/local)
- Codex integration and template loading
- Logger with structured output

## 🧩 Potential Features to Add

### Agents
- [ ] `dream_agent`: handle dream logging and interpretation
- [ ] `emotion_agent`: analyze affective tones in chat history
- [ ] `context_agent`: infer user intent from long-term logs
- [ ] `schedule_agent`: calendar/Gmail integration upgrades

### CLI Tools
- [ ] `guardian log` with filtering/search flags
- [ ] `guardian export notion --live-sync`
- [ ] `guardian foresight` interactive terminal planner

### API Endpoints
- [ ] `/rituals/list` - discoverable rituals
- [ ] `/codex/lookup` - remote Codex fragment fetch
- [ ] `/metrics/ping` - performance + health monitoring

### Memory Layer
- [ ] Thread-based memory pruning or compression
- [ ] Semantic search integration (e.g., ChromaDB, LanceDB)

### Developer Features
- [ ] CLI test harness for agents
- [ ] Replay log mode for debugging agent flows
- [ ] Auto-documentation of API via OpenAPI annotations

## ✨ Notes
This file is meant to evolve. Add stub files for new agents as placeholders if you want to define rituals before writing their code.
