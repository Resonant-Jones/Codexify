# Agent Orchestration & Run Events (SSE) — Codexify

**Last verified (observed runtime):** 2026-02-18  
**Audience:** Codexify contributors/operators running the Docker stack locally.

This document explains **how agent orchestration works end-to-end**, how to **configure** it, and how to **debug** the common migration + event-stream failure modes you just hit.

> Current scope note: the API **creates plans, deployments, and runs**, and emits **run state/events**. A “real” delegated execution loop (worker consuming a run and performing mutating steps) may be **scaffolded but not fully wired** depending on your branch/config.

---

## Architecture at a glance

### Entities

- **Plan**: a proposed spec derived from a prompt (and optionally user-proposed steps).
- **Deployment**: a persisted “runnable” spec bound to a `flow_id` and `thread_id`, with a `trust_state`.
- **Run**: an execution instance of a deployment (tracks status, runtime target, timestamps).
- **Run Events**: append-only events associated with a run, streamed over SSE and (typically) persisted for replay.

### Request flow

1. Client creates a **plan** (`/api/agents/plans`).
2. Client creates a **deployment** (`/api/agents/deployments`).
3. Client starts a **run** (`/api/agents/deployments/{deployment_id}/runs`).
4. Client streams **run events** (`/api/agents/runs/{run_id}/events`).
5. Client can **cancel** a run (`/api/agents/runs/{run_id}/cancel`).
6. Client can list runs for a chat thread (`/api/chat/{thread_id}/agent-runs`).

---

## Database + migrations

Agent orchestration requires the latest DB schema. The authoritative schema version for this feature is the Alembic revision:

- **`9f3d2b1a7c4e`** — `add_agent_orchestration_tables`

### Verify the migration is applied

```bash
docker compose exec db sh -lc 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "select version_num from alembic_version;"'
```

Expected:

- `version_num` should be `9f3d2b1a7c4e` (or a newer head, if you’ve added more migrations).

### Canonical migration path (recommended)

Use the repo’s migrator container. This avoids local env drift and ensures `DATABASE_URL` is present inside the container.

```bash
docker compose up -d db
docker compose run --rm migrator
```

### If you see “Can't locate revision identified by …”

Example failure:

- `Can't locate revision identified by '384dde1f793c'`

This means **your DB is stamped with a revision your current code checkout does not contain** (branch mismatch or a pruned migration).

Fix options:

1) **Nuke local DB volume** (dev only) and rerun migrator:

```bash
docker compose down -v
docker compose up -d db
docker compose run --rm migrator
```

2) Or check out the code revision that includes that Alembic revision (not recommended unless you must preserve data).

### Why local `alembic upgrade head` failed for you

You saw:

- `RuntimeError: sqlalchemy.url not configured. Set DATABASE_URL environment variable or update alembic.ini`

Local Alembic requires `DATABASE_URL` in your shell:

```bash
export DATABASE_URL="postgresql://codexify:<password>@localhost:5433/Codexify"
alembic -c backend/alembic.ini upgrade head
```

…but the **migrator container** is still the preferred path.

---

## Services + runtime configuration

### Docker Compose services you care about

- `db` — Postgres (mapped to host `5433`)
- `redis` — queue/event infra (if used by your run/event bus)
- `backend` — API server (host `8888`)
- `worker-*` — background workers (chat/embedding/etc)
- `frontend` — Vite (host `5173`)
- `migrator` — runs Alembic migrations + seed

### Required environment variables (backend)

| Variable | Purpose | Where |
|---|---|---|
| `GUARDIAN_API_KEY` | API auth key for `X-API-Key` header | compose / env |
| `DATABASE_URL` | Postgres DSN | compose |
| `CORS_ALLOWED_ORIGINS` (or equivalent) | allow frontend origin | compose/config |

Your backend logs confirmed:

- it loads `GUARDIAN_API_KEY=...`
- it uses PostgreSQL via `DATABASE_URL`
- it allows origin `http://localhost:5173`

---

## API contract

### Authentication

All endpoints below require:

- Header: `X-API-Key: <your dev key>`

Example:

```bash
export API_KEY="your-key"
export BASE="http://localhost:8888"
```

---

## 1) Create plan

**POST** `/api/agents/plans`

```bash
curl -s -H "X-API-Key: $API_KEY" -H "Content-Type: application/json" \
  -d '{"prompt":"test plan","thread_id":77,"proposed_steps":[]}' \
  "$BASE/api/agents/plans"
```

Example response (observed):

```json
{
  "ok": true,
  "plan_id": "plan_...",
  "spec_hash": "...",
  "spec": { "prompt": "test plan", "thread_id": 77, "steps": [] }
}
```

---

## 2) Create deployment

**POST** `/api/agents/deployments`

```bash
curl -s -H "X-API-Key: $API_KEY" -H "Content-Type: application/json" \
  -d '{"flow_id":"flow-test","thread_id":77,"spec":{"steps":[]},"trust_state":"supervised"}' \
  "$BASE/api/agents/deployments"
```

Example response (observed):

```json
{
  "ok": true,
  "deployment": {
    "deployment_id": "dep_...",
    "flow_id": "flow-test",
    "thread_id": 77,
    "spec_json": {"steps":[]},
    "trust_state": "supervised",
    "status": "active"
  }
}
```

---

## 3) Start run

**POST** `/api/agents/deployments/{deployment_id}/runs`

```bash
curl -s -H "X-API-Key: $API_KEY" -H "Content-Type: application/json" \
  -d '{"runtime_target":"container","supervised":true}' \
  "$BASE/api/agents/deployments/dep_a193ce01ccd247e5/runs"
```

Example response (observed):

```json
{
  "ok": true,
  "run": {
    "run_id": "run_...",
    "deployment_id": "dep_...",
    "thread_id": 77,
    "status": "running",
    "runtime_target": "container",
    "rollback_mode": "auto",
    "created_at": "2026-02-18T19:53:57.627359+00:00",
    "started_at": "2026-02-18T19:53:57.627359+00:00"
  }
}
```

**Important:** do not literally use `<deployment_id>` in the URL. If you do, you’ll get:

```json
{"detail":"deployment_not_found", ...}
```

---

## 4) List runs for a chat thread

**GET** `/api/chat/{thread_id}/agent-runs`

```bash
curl -s -H "X-API-Key: $API_KEY" "$BASE/api/chat/77/agent-runs"
```

Observed response (after starting one run):

```json
{"ok":true,"thread_id":77,"runs":[{"run_id":"run_...","status":"running", ...}]}
```

---

## 5) Stream run events (SSE)

**GET** `/api/agents/runs/{run_id}/events`

This returns **Server-Sent Events** with fields:

- `id:` monotonically increasing identifier (often timestamp-based)
- `event:` event type name
- `data:` JSON payload
- `: ping` keepalive comment lines

Example:

```bash
curl -N -H "X-API-Key: $API_KEY" \
  "$BASE/api/agents/runs/run_338c4bdd9ca94f3c/events"
```

Observed output:

```text
retry: 3000

id: 1771444437629-0
event: created
data: {"deployment_id": "dep_...", "run_id": "run_..."}

id: 1771444437629-1
event: started
data: {"deployment_id": "dep_...", "run_id": "run_..."}

: ping
: ping
...
```

### Are these events “live”?

Yes, you’re connected to the live backend process. However, what you see on connect can be a mix of:

- **Replay**: historical run events persisted earlier (sent immediately on connect)
- **Tail**: new events appended while the stream is open
- **Keepalive**: `: ping` lines to prevent idle timeouts

With the current scaffolding, it’s expected to see only `created` and `started` unless the worker/runner emits additional step/log events.

---

## 6) Cancel a run

**POST** `/api/agents/runs/{run_id}/cancel`

```bash
curl -s -X POST -H "X-API-Key: $API_KEY" \
  "$BASE/api/agents/runs/run_338c4bdd9ca94f3c/cancel"
```

Expected behavior:

- Run status transitions away from `running`
- An event may be appended/emitted (depending on implementation)

If you have the SSE stream open in another terminal, you should see the cancel-related event if it’s wired.

---

## Event semantics (current observed set)

From your live run stream, the backend currently emits at least:

- `created`
- `started`

Additional events you typically want in a full orchestration loop (may or may not already exist in your code):

- `step_started`
- `step_progress`
- `step_completed`
- `log`
- `terminal_output`
- `cancel_requested`
- `canceled`
- `completed`
- `failed`

> Recommendation: Treat the **event names as contract** once you publish this feature. If you change them, version the API or provide compatibility mapping.

---

## Trust + supervision model

You’re passing:

- `trust_state: "supervised"` on deployments
- `supervised: true` on run-start

Interpretation (intended contract):

- **supervised** implies the worker/runner should respect commit boundaries, require approvals for mutating actions, and/or emit audit artifacts.

Even if execution isn’t fully wired yet, this is where you hang:
- approval gates
- command allowlists
- “commit boundary” enforcement
- rollback / worktree isolation

---

## Troubleshooting

### A) Backend warns: “Expected database tables missing … Apply latest Alembic migrations.”

Example:

- `Expected database tables missing: ['project_document_links']`

This means the backend’s startup schema check expects tables that are absent in the DB it is actually connected to.

**Checklist**

1) Confirm DB revision:

```bash
docker compose exec db sh -lc 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "select version_num from alembic_version;"'
```

2) Confirm backend is pointing to the same DB:

- Check `DATABASE_URL` in backend logs (should reference `db:5432/Codexify` in compose)
- Ensure you didn’t also have a local Postgres running and point backend at `localhost`

3) If you recently swapped branches or migrations:
- `docker compose down -v`
- rerun migrator

---

### B) `deployment_not_found`

Cause: you hit:

- `/deployments/<deployment_id>/runs` literally

Fix: substitute the real deployment id returned from create deployment.

---

### C) `psql: executable file not found` inside backend container

The backend image likely doesn’t ship `psql`. Query via the `db` service container instead:

```bash
docker compose exec db sh -lc 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "\dt"'
```

---

### D) Port conflicts (e.g., `5173` already in use)

Error:

- `bind: address already in use`

Fix:

- stop whatever owns that port, or
- remap the compose port for frontend, or
- run Vite on a different port.

---

## Recommended “operator” workflow

### Fresh bring-up (safe dev default)

```bash
docker compose down -v
docker compose up -d db
docker compose run --rm migrator
docker compose up -d redis backend
```

Then (optional):

```bash
docker compose up -d frontend
```

### Smoke test the full orchestration surface

```bash
export API_KEY="..."
export BASE="http://localhost:8888"

# plan
curl -s -H "X-API-Key: $API_KEY" -H "Content-Type: application/json" \
  -d '{"prompt":"test plan","thread_id":77,"proposed_steps":[]}' \
  "$BASE/api/agents/plans"

# deployment
DEP=$(curl -s -H "X-API-Key: $API_KEY" -H "Content-Type: application/json" \
  -d '{"flow_id":"flow-test","thread_id":77,"spec":{"steps":[]},"trust_state":"supervised"}' \
  "$BASE/api/agents/deployments" | python -c 'import sys,json; print(json.load(sys.stdin)["deployment"]["deployment_id"])')

# run
RUN=$(curl -s -H "X-API-Key: $API_KEY" -H "Content-Type: application/json" \
  -d '{"runtime_target":"container","supervised":true}' \
  "$BASE/api/agents/deployments/$DEP/runs" | python -c 'import sys,json; print(json.load(sys.stdin)["run"]["run_id"])')

# stream
curl -N -H "X-API-Key: $API_KEY" "$BASE/api/agents/runs/$RUN/events"
```

---

## Where to extend next (wiring “real execution”)

To make runs do more than `created/started`, the system needs:

1. A worker that **consumes runs** (from DB queue or Redis stream)
2. A runner that creates:
   - an isolated worktree / sandbox
   - deterministic state files / audit artifacts
3. Event emission for step lifecycle + logs

If you already have deterministic primitives in `guardian/workers/agent_worker.py`, the next doc to add is:

- **Execution Wiring:** “How a run transitions from `running` to `completed/failed/canceled`”  
- **Artifacts:** “Where audit receipts live and how they map to run IDs”  
- **Security model:** “What supervised mode blocks and how approvals are recorded”

---

## Appendix: Quick DB introspection commands

Count tables:

```bash
docker compose exec db sh -lc 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "select count(*) as tables from information_schema.tables where table_schema='\''public'\'';"'
```

List orchestration tables (guessing naming; adjust if needed):

```bash
docker compose exec db sh -lc 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "\dt *agent* \dt *deployment* \dt *run*";'
```

---

## Change log

- 2026-02-18: Initial doc written from live local run + migration recovery session.  
  Observed SSE events: `created`, `started`. Alembic head verified: `9f3d2b1a7c4e`.
