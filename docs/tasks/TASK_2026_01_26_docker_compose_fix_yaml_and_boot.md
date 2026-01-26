
TASK: Fix docker-compose.yml YAML parse + restore migrator + graph-init

Task ID: TASK-2026-01-26-DOCKER-COMPOSE-FIX-YAML-AND-BOOT

Context / Failure

Running docker compose up fails with:
 • failed to parse docker-compose.yml: yaml: unmarshal errors: mapping key "build" already defined ...

The current docker-compose.yml has:
 • graph-init missing a real entrypoint/command body (currently only command: [sh, -c])
 • migrator accidentally contains the graph-init cypher block appended to its command (bad pipe chaining)
 • a duplicate nested migrator: block under the first migrator, causing duplicate keys and invalid YAML.

Goal

Make docker compose config pass, and make docker compose up --build start cleanly so the new DB-backed features (sharing/collab tables + thread_documents) work.

⸻

Constraints
 • Evidence-first edits: only change what is needed to fix YAML + correct service wiring.
 • Don’t remove existing services or re-architect.
 • Preserve environment defaults already being used (POSTGRES_PASSWORD:-codexify, etc.).
 • Keep migrator as a one-shot service (restart: "no") that upgrades Alembic + seeds.

⸻

Required Edits (Canonical Fix)

1) Fix graph-init service

Replace the current graph-init: service with:
 • entrypoint: [ "sh", "-lc" ]
 • command: uses a |- block to run cypher-shell against bolt://neo4j:7687
 • Ensure it depends on neo4j healthy
 • Ensure it is NOT embedded inside any other service’s command.

1) Fix migrator service

Ensure there is exactly one migrator: service definition.

It must:
 • build from backend/Dockerfile (same as backend/worker services)
 • mount volumes so migrations exist inside container:
 • ./guardian:/app/guardian
 • ./backend:/app/backend
 • ./codexify:/app/codexify
 • working_dir: /app
 • entrypoint: [ "sh", "-lc" ]
 • command: runs:
 • sanity check migrations dir exists: /app/guardian/db/migrations
 • alembic --raiseerr -c /app/backend/alembic.ini upgrade head
 • python /app/backend/scripts/seed_defaults.py
 • depends_on: db healthy
 • restart: "no"

1) Delete the duplicate migrator: block

In the current file, there is a second migrator: block nested under the first migrator’s command. Remove it entirely so YAML is valid.

⸻

Validation Steps (Must Run)

Compose validation

docker compose config >/tmp/compose.expanded.yml

✅ Must exit 0 with no YAML errors.

Boot stack

docker compose down -v
docker compose up --build

✅ Must start backend, workers, db, redis, neo4j, frontend.

Confirm DB tables exist (post-migrate)

docker compose exec -T db psql -U codexify -d Codexify -c "\\dt" | grep -E "thread_documents|shared_links|collaboration_"

✅ Must show:
 • collaboration_audit_log
 • collaboration_permissions
 • shared_links
 • thread_documents

Smoke test: upload document works

echo "hello embed world" > /tmp/codexify_smoke_doc.txt
THREAD_ID=1
curl -sS -X POST <http://localhost:8888/api/media/upload/document> \
  -H "X-API-Key: $GUARDIAN_API_KEY" \
  -F "file=@/tmp/codexify_smoke_doc.txt" \
  -F "project_id=1" \
  -F "thread_id=$THREAD_ID" | head -c 2000

✅ Must return JSON with an id and embedding_status.

⸻

Deliverables
 1. A corrected docker-compose.yml that passes docker compose config
 2. A short terminal log snippet in the PR/commit message showing:
 • compose config OK
 • stack boots
 • table grep shows the 4 new tables
 • upload returns success JSON

⸻

Notes / Known Pitfalls
 • The YAML parse error is caused by duplicate mapping keys, not Docker itself.
 • Do not pipe echo "[Migrator] Done." | set -e ... (that’s how graph-init got injected into migrator).
 • Keep graph-init and migrator separate services with separate commands.
 • Prefer grep over rg inside containers (some images don’t have ripgrep installed).
