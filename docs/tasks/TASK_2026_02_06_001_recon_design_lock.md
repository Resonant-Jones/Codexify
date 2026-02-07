# TASK-2026-02-06-001_recon_+_design_lock

## Metadata
- Campaign-ID: CAMPAIGN_2026_02_06_GUARDIAN_PARITY_CONTROL_PLANE
- Task-ID: TASK-2026-02-06-001_recon_+_design_lock
- Task title: Recon + Design Lock
- Task artifact: docs/tasks/TASK_2026_02_06_001_recon_design_lock.md
- Owner: resonant_jones
- Risk: LOW
- Commit mode: one-commit (docs-only)

## Objective
Produce an evidence-based “Design Lock” note that names the **exact integration points** (paths + symbols) for auth, router registration, lifecycle hooks, queue/workers, and test harness patterns — without writing any new subsystems.

## Scope
### In-scope
- Locate and cite (file paths + key functions/classes) for:
  - API key auth dependency entrypoint(s)
  - Router registration patterns (`include_router`, dependencies)
  - Lifespan/startup hooks (where background workers/schedulers would be started)
  - Queue mechanism / outbox pattern (Redis, tasks, workers)
  - Test harness patterns (fixtures, overrides, TestClient)
- Write a short **Design Lock** note into the campaign file (paths + symbols + rationale).
- Update this task artifact with the commands run + findings summary.

### Out-of-scope
- No implementation changes to backend/frontend behavior.
- No refactors.
- No new modules, workers, or routes.
- No dependency changes.

## Allowed files (STRICT)
> Do not modify files outside this list.

- docs/tasks/TASK_2026_02_06_001_recon_design_lock.md
- docs/Campaign/CAMPAIGN_2026_02_06_GUARDIAN_PARITY_CONTROL_PLANE.md

## Dependencies / Prereqs (NO GUESSING)
Run these to confirm you’re in the right repo and the tree is clean:

```bash
cd /Users/resonant_jones/Keep/Resonant_Constructs/Codexify

git rev-parse --show-toplevel
# Expected: /Users/resonant_jones/Keep/Resonant_Constructs/Codexify

git status --porcelain -uall
# Expected: (no output)
```

## Command checklist (copy/paste)
```bash
cd /Users/resonant_jones/Keep/Resonant_Constructs/Codexify

# 0) REQUIRED: clean tree before starting
git status --porcelain -uall

# 1) Auth dependency (API key)
rg -n "require_api_key|X-API-Key|GUARDIAN_API_KEY" guardian/core guardian/routes guardian/guardian_api.py

# 2) Router registration + dependencies (where routers get included)
rg -n "include_router\(|APIRouter\(" guardian/guardian_api.py guardian/routes -S

# 3) Lifespan / startup hooks (where schedulers/workers would start)
rg -n "lifespan|startup|on_event\(\"startup\"\)|@app\.on_event|asynccontextmanager" guardian -S

# 4) Queue / outbox / worker entrypoints
rg -n "redis_queue|enqueue|outbox|worker|document_embed_worker|chat_embedding_worker" guardian docker-compose.yml -S

# 5) Test harness patterns
rg -n "TestClient\(|fixture\(|monkeypatch|dependency_overrides|override" tests guardian/tests -S

# 6) Confirm only allowed files will be edited (should still be clean right now)
git status --porcelain -uall
```

## Expected outputs (success signals)
- The campaign file contains a new **Design Lock** section that:
  - Names the auth dependency function(s) (path + symbol)
  - Names where routers are registered (path + symbol)
  - Names where lifespan/startup wiring exists (path + symbol)
  - Names the queue mechanism and worker entrypoints (path + symbol)
  - Names test harness patterns (fixture file paths)
- This task artifact includes:
  - The commands run
  - A short summary of findings with file references
- `git status --porcelain -uall` shows only:
  - `docs/tasks/TASK_2026_02_06_001_recon_design_lock.md`
  - `docs/Campaign/CAMPAIGN_2026_02_06_GUARDIAN_PARITY_CONTROL_PLANE.md`

## Rollback / cleanup
```bash
cd /Users/resonant_jones/Keep/Resonant_Constructs/Codexify

git restore -- docs/tasks/TASK_2026_02_06_001_recon_design_lock.md \
  docs/Campaign/CAMPAIGN_2026_02_06_GUARDIAN_PARITY_CONTROL_PLANE.md

git status --porcelain -uall
```

## Commit plan (MANUAL)
### Commit (docs-only)
- Commit message (EXACT):
  - `TASK-2026-02-06-001_recon_+_design_lock: design lock notes + references`

```bash
cd /Users/resonant_jones/Keep/Resonant_Constructs/Codexify

git status --porcelain -uall

# stage only the two allowed docs
git add docs/tasks/TASK_2026_02_06_001_recon_design_lock.md \
  docs/Campaign/CAMPAIGN_2026_02_06_GUARDIAN_PARITY_CONTROL_PLANE.md

git status --porcelain -uall

git commit --no-verify -m "TASK-2026-02-06-001_recon_+_design_lock: design lock notes + references"

git log -1 --oneline

git status --porcelain -uall
```

## Mapping
- TASK-2026-02-06-001_recon_+_design_lock -> [<commit>, n/a]

## Notes
- Naming hygiene: this task artifact filename contains `+` and is non-canonical. Do **not** rename during this task; if desired, create a separate docs-only rename task using `git mv`.

## Summary (fill after completion)
- Findings (paths + symbols):
  - Auth dependency: `guardian/core/dependencies.py` -> `verify_api_key()`, `require_api_key()`; startup key guard in `guardian/guardian_api.py`.
  - Router registration: `guardian/guardian_api.py` -> centralized `app.include_router(...)` block for all route modules.
  - Lifespan/startup: `guardian/guardian_api.py` -> `app_lifespan()` manages startup/shutdown, connector worker start/stop, and service binding.
  - Queue/workers: `guardian/core/event_bus.py` (`emit_event`, `subscribe_in_memory`), `guardian/queue/redis_queue.py` (`enqueue`, `dequeue`, `enqueue_chat_embed`), `guardian/tasks/types.py` (`TASK_TYPE_REGISTRY`), `guardian/workers/*` entrypoints + `docker-compose.yml` worker services.
  - Tests: `tests/routes/conftest.py` (`test_client` fixture with `dependency_overrides`), `tests/realtime/conftest.py` (`db_engine`/`db_session` skip-or-run DB fixtures), `guardian/tests/conftest.py` (`_PatchedTestClient` fixture pattern).
- Commands run:
  - `git status --porcelain -uall`
  - `rg -n "require_api_key|X-API-Key|GUARDIAN_API_KEY" guardian/core guardian/routes guardian/guardian_api.py -S`
  - `rg -n "include_router\\(|APIRouter\\(" guardian/guardian_api.py guardian/routes -S`
  - `rg -n "lifespan|startup|on_event\\(\"startup\"\\)|@app\\.on_event|asynccontextmanager" guardian -S`
  - `rg -n "redis_queue|enqueue|outbox|worker|document_embed_worker|chat_embedding_worker" guardian docker-compose.yml -S`
  - `rg -n "TestClient\\(|fixture\\(|monkeypatch|dependency_overrides|override" tests guardian/tests -S`
  - `rg --files guardian | rg '^guardian/(ws|cron|browser|channels)/'`
  - `nl -ba guardian/core/dependencies.py | sed -n '108,230p'`
  - `nl -ba guardian/guardian_api.py | sed -n '150,280p'`
  - `nl -ba guardian/guardian_api.py | sed -n '420,490p'`
  - `nl -ba guardian/core/event_bus.py | sed -n '1,140p'`
  - `nl -ba guardian/queue/redis_queue.py | sed -n '150,250p'`
  - `nl -ba tests/routes/conftest.py | sed -n '150,240p'`
  - `nl -ba tests/realtime/conftest.py | sed -n '1,180p'`
  - `nl -ba guardian/tests/conftest.py | sed -n '1,140p'`
- Final git status: only the two allowed files are modified (campaign + this task artifact).
- Mapping: `TASK-2026-02-06-001_recon_+_design_lock -> [<commit>, n/a]`
