Guardian (Dev) — Auth, Envs, Endpoints, and Rituals

0) TL;DR (happy path)

# Backend (one terminal)

uvicorn guardian.guardian_api:app --reload --log-level info

# Dev API key (from env files)

KEY="$(bash scripts/dev-key.sh)"

# Health + threads should work

curl -s <http://127.0.0.1:8000/healthz> | jq
curl -s -H "X-API-Key: $KEY" <http://127.0.0.1:8000/threads> | jq

Front-end .env.local:

VITE_GUARDIAN_API_BASE=<http://127.0.0.1:8000>
VITE_GUARDIAN_API_KEY=<same dev key as backend>

App bootstrap:

import { configureGC } from '@/dcw-services/gc';
configureGC({
  base: import.meta.env.VITE_GUARDIAN_API_BASE,
  token: import.meta.env.VITE_GUARDIAN_API_KEY,
});

⸻

1) Environment files (local dev vs prod)
 • Local dev (private, untracked):
 • .env.local — overrides anything else for this machine (backend + optional Vite vars). Do not commit.
 • .env.backend.development — optional backend-only dev overrides.
 • Shared templates (safe to commit):
 • .env.template, .env.example, server/.env.example — no real keys.
 • Production:
 • .env.production (or deploy-specific secret store). Never commit real keys.

Backend load order (last one wins):

.env  →  .env.backend.development  →  .env.local

You’ll see something like this on startup:

[env] dotenv loaded (in order): .env -> .env.backend.development -> .env.local
[auth] Using GUARDIAN_API_KEY=e96d…11f6

⸻

2) Secrets: where to put keys
 • Backend dev key: set GUARDIAN_API_KEY in .env.local (or .env.backend.development).
 • Frontend: only for local dev, you can mirror the key as VITE_GUARDIAN_API_KEY in .env.local so the browser can call the dev API.
 • For production, do not expose secrets in Vite env; frontends can’t keep secrets. Use a server/proxy to attach headers.

Generate a strong dev key (example):

python - <<'PY'
import secrets, hashlib
key = secrets.token_hex(32)
print(hashlib.sha256(key.encode()).hexdigest())
PY

Copy it into:

# .env.local (backend)

GUARDIAN_API_KEY=<sha256-like string>

# .env.local (frontend – dev only)

VITE_GUARDIAN_API_KEY=<same value>
VITE_GUARDIAN_API_BASE=<http://127.0.0.1:8000>

⸻

3) DBs: keeping dev and prod separate
 • Backend reads GUARDIAN_DB_PATH. If unset, it defaults (e.g., guardian/guardian.db).
 • For dev isolation, set:

# .env.backend.development or .env.local

GUARDIAN_DB_PATH=guardian/guardian.dev.db

 • Check what’s active:

curl -s <http://127.0.0.1:8000/healthz> | jq

# {

# "db_path": ".../guardian/guardian.dev.db"

# "projects_table_exists": true

# "threads_table_exists": true

# }

Wipe dev DB (careful!):

rm -f guardian/guardian.dev.db

# restart uvicorn so tables are re-created

⸻

4) Scripts you should keep

scripts/dev-key.sh

# !/usr/bin/env bash
set -euo pipefail
grep -h -E '^GUARDIAN_API_KEY=' .env.local .env.backend.development .env 2>/dev/null \
  | tail -n1 \
  | cut -d= -f2- \
  | tr -d '\r'

Make it executable:

chmod +x scripts/dev-key.sh

Usage:

KEY="$(scripts/dev-key.sh)"
printf 'Using key: %s…%s\n' "${KEY:0:4}" "${KEY: -4}"

⸻

5) Endpoints (current)
 • GET /ping → {"status":"Guardian awake!"} (no auth)
 • GET /healthz → DB path + table existence (no auth)
 • Auth required via header X-API-Key: <GUARDIAN_API_KEY>
 • Threads:
 • GET /threads
 • POST /threads body: {"summary"|"title": string, "project_id": string|null, ...}
 • DELETE /thread/{id}
 • Also: GET /history/v2?session_id=s1&user_id=default (empty list until you wire chat history)
 • Projects:
 • POST /projects body: {"name": string, "description": string?}
 • GET /projects
 • DELETE /projects/{id}

⸻

6) Curl rituals (dev)

# Key

KEY="$(scripts/dev-key.sh)"

# Health (no auth)

curl -s <http://127.0.0.1:8000/healthz> | jq

# Threads

curl -s -H "X-API-Key: $KEY" http://127.0.0.1:8000/threads | jq
curl -s -X POST http://127.0.0.1:8000/threads \
  -H 'content-type: application/json' -H "X-API-Key: $KEY" \
  -d '{"summary":"Hello MVP","project_id":"p1"}' | jq
curl -s -X DELETE -H "X-API-Key: $KEY" <http://127.0.0.1:8000/thread/1> | jq

# Projects

PID=$(curl -s -X POST http://127.0.0.1:8000/projects \
  -H 'content-type: application/json' -H "X-API-Key: $KEY" \
  -d '{"name":"Alpha","description":"First project"}' | jq -r .project_id)
curl -s -H "X-API-Key: $KEY" http://127.0.0.1:8000/projects | jq
curl -s -X DELETE -H "X-API-Key: $KEY" <http://127.0.0.1:8000/projects/$PID> | jq

⸻

7) Frontend wiring (Vite)

.env.local:

VITE_GUARDIAN_API_BASE=<http://127.0.0.1:8000>
VITE_GUARDIAN_API_KEY=<dev key – same as backend, dev only>

Bootstrap (already in place):

import { configureGC } from '@/dcw-services/gc';
configureGC({
  base: import.meta.env.VITE_GUARDIAN_API_BASE,
  token: import.meta.env.VITE_GUARDIAN_API_KEY,
});

If the UI shows a white screen, open the browser console (DevTools → Console) and look for:
 • missing exports/imports (e.g. request not exported)
 • 404 for /src/dcw-services/gc.ts (wrong path/alias)
 • TypeError: Importing a module script failed (bad module URL)
Fix imports and restart Vite after changing envs.

⸻

8) Troubleshooting (the greatest hits)
 • 401 Unauthorized
 • Your header is empty or wrong. Print it:
bash scripts/dev-key.sh | awk '{print substr($0,1,4) "…" substr($0,length($0)-3)}'
 • Backend startup log should show the key it loaded:
"[auth] Using GUARDIAN_API_KEY=…"
 • 500 on /threads
 • Was previously caused by code calling an internal DB method; fixed in API. If seen again, check /healthz for table presence and watch uvicorn stack traces.
 • 422 on /chat
 • Body schema mismatch. Send at least:

{"prompt":"ping from curl","model":"<your model id>"}

 • Also ensure provider config + keys are set (Groq/OpenAI/etc.) in backend env (do not put those in Vite env).

 • 404 on /projects
 • Route not loaded or server running an older file. Restart uvicorn. Confirm routes:

python - <<'PY'
import guardian.guardian_api as g
print([ (r.path, sorted(getattr(r,'methods',[])))
        for r in g.app.routes if r.path.startswith('/projects') ])
PY

 • Method Not Allowed (405) with /threads
 • Use the correct variant: we accept POST /threads (no trailing slash). Follow redirects carefully when in doubt.
 • Vite white screen
 • Usually an import/export mismatch. Read the console errors; fix exports in the referenced module (e.g., ensure export { request } exists if imported, or remove stale imports).

⸻

9) Production notes
 • Use a separate GUARDIAN_DB_PATH (e.g., guardian/guardian.prod.db) and separate secrets store (host env / secret manager).
 • Don’t ship real keys in the frontend. For prod, have the frontend call your backend without embedding secrets; the backend attaches X-API-Key.
 • Pre-deploy checklist:
 • /healthz OK on the prod host.
 • GET /threads returns 401 without header, 200 with header.
 • POST /projects returns 201 and a numeric project_id.
 • DELETE /projects/{id} returns 200 with {"deleted":true}.

⸻

10) Appendix: verify what the server loaded

# If you log this in startup

# [env] dotenv loaded (in order):

# [auth] Using GUARDIAN_API_KEY=e96d…11f6

# Or introspect routes quickly

python - <<'PY'
import guardian.guardian_api as g
print("Routes:", sorted((r.path, sorted(getattr(r,'methods',[]))) for r in g.app.routes))
PY