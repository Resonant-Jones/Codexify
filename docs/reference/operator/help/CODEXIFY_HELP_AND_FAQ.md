# Codexify — Help, Setup, and FAQ

Welcome to Codexify.

This guide is the canonical onboarding and troubleshooting reference.

If you're new, start here.

---

# 🟢 Quick Start (Docker)

## Requirements

- Docker
- Docker Compose
- Git

## Install

```bash
git clone https://github.com/<your-org>/codexify.git
cd codexify
docker compose up --build
```

On the first boot, Codexify may spend a few minutes downloading the default local embedding model into `./models` before the backend and workers come fully online.

Once services are running:
- Frontend: http://localhost:5173
- Backend API: http://localhost:8888

---

## 🔧 First-Run Checklist

- Confirm containers are healthy: `docker compose ps`
- Confirm backend health: `GET /health`
- Confirm DB initialized
- Confirm Redis running
- Confirm vector store initialized (if enabled)
- Check for `SECURITY-REWRITE-NOTICE.md`; if present, apply those reset/re-clone instructions before first run.

If the UI loads but chat does not respond:
- Check backend logs: `docker compose logs backend`
- Check worker logs: `docker compose logs worker-chat`

---

## 📦 Updating Codexify

```bash
git pull
docker compose down
docker compose up --build
```

If the project publishes a security history rewrite notice, do not use `git pull` on an old clone. Follow `SECURITY-REWRITE-NOTICE.md` and re-clone/reset exactly as instructed.

---

## 🧠 Common Questions

**Q: Chat isn’t responding.**
- Check Redis is running.
- Check worker-chat container is active.
- Check provider configuration (`LLM_PROVIDER` and keys).
- Inspect backend logs.

---

**Q: I see `queue_unavailable`.**

Redis is not reachable.

Verify:
- `REDIS_URL`
- Redis container status

---

**Q: Documents uploaded but not searchable.**

Check:
- `worker-document-embed` container
- `uploaded_documents.embedding_status`
- Vector store health endpoint `/health/vector`

---

**Q: How do I configure providers?**

Environment variables (see `.env`):
- `LLM_PROVIDER`
- `OPENAI_API_KEY`
- `GROQ_API_KEY`
- `MINIMAX_API_KEY`
- `ALLOW_CLOUD_PROVIDERS`
- `CODEXIFY_LOCAL_ONLY_MODE`

Restart backend after changes.

---

**Q: Where do I report bugs?**

Open a GitHub issue with:
- OS
- Docker version
- Steps to reproduce
- Logs (redact secrets)

---

## 🛠 Troubleshooting Commands

```bash
docker compose ps
docker compose logs backend
docker compose logs worker-chat
docker compose logs worker-document-embed
```

---

## 🧭 Support Channels

- GitHub Issues (official bug tracking)
- Codexify Discord (#setup-help, #bugs-and-issues)

---

## 📌 Design Principles

Codexify is:
- Local-first
- Sovereignty-respecting
- Postgres-backed
- Redis-queued
- Worker-driven
- Explicitly configurable

It is designed for builders.

---

End of document.
