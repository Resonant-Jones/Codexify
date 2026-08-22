# 2026-08-22 MemoryStore Startup Repair Runtime Proof (Completion and Safeguard-Gate Reconciliation)

## 1. Final classification

`REPAIR PROOF BLOCKED`

The live runtime evidence below remains valid: the actual Compose backend
import passed, the historical readonly-SQLite failure did not recur, and the
bounded backend startup progressed to the later configuration-coherence
boundary. However, the original completion closeout could not truthfully
count its MemoryStore-relevant safeguard gate as passed. Reconciliation
retired that invalid stale test, then exercised the dedicated generic cache
gate required to replace it. That valid gate currently errors during fixture
setup because `guardian.config.Config` has no `CACHE_DIR` attribute. Under the
task's explicit stop rule, the remaining focused reconciliation gates were not
rerun and `REPAIR PROOF PASS` cannot be retained.

The candidate commit `063505561c8b105708334b92de5abb567da59cba`
removes NX-1's first material runtime blocker. Confirmed at three
levels:

1. **Python-level**: focused regressions and `test_config_coherence.py` are green on the candidate (6+16 tests pass).
2. **Container-level**: `docker compose run --no-deps backend -c 'import guardian.guardian_api; print(...)'` succeeds — the actual backend image imports the application cleanly, prints `guardian_api_import_ok`, exits 0, and **does not** manufacture `guardian/memory/store.db` on the host.
3. **Backend-startup-level**: bounded `docker compose up backend` brings the backend past the SQLite boundary (which used to kill uvicorn at module import); the new first material error is the **secondary** `Config coherence check failed` observation previously recorded as NX-1 §54.4 probe-only evidence, **not** the SQLite bug.

This proof artifact supersedes the earlier candidate-only version of
this same document (before runtime evidence was collected). The
candidate implementation has not changed between the two versions or
during the safeguard-gate reconciliation.

## 2. Origin/main and candidate ancestry (preflight)

```text
$ git fetch origin
$ git rev-parse origin/main
8cfe9daa5c15dbed59e626206f22dfd28032ed1c

$ git merge-base --is-ancestor \
    0515bb3af49acb9ab288421393ced7d4cb600359 \
    origin/main
exit=0                                       # canonical NX-1 receipt prerequisite

$ git cat-file -t 063505561c8b105708334b92de5abb567da59cba
commit

$ git rev-parse 063505561c8b105708334b92de5abb567da59cba^
8cfe9daa5c15dbed59e626206f22dfd28032ed1c       # parent == origin/main

$ git diff --name-only \
    8cfe9daa5c15dbed59e626206f22dfd28032ed1c \
    063505561c8b105708334b92de5abb567da59cba
docs/architecture/proofs/2026-08-22-memory-store-startup-repair-proof.md
guardian/core/dependencies.py
guardian/memory/query_memory.py
guardian/tests/test_context_broker_memory.py
tests/core/test_memory_store_startup_boundary.py
```

Origin/main is unchanged since the prior canonicalization merge (PR
#737). The candidate descends directly from the same canonical HEAD.

## 3. Proof worktree / branch identity

```text
worktree: /Volumes/Dev_SSD/Codexify-memoryfix-proof-06350556
branch:   codex/complete-memory-store-runtime-proof
runtime-proof implementation commit: 063505561c8b105708334b92de5abb567da59cba
safeguard-reconciliation starting HEAD: c063b3306d2211ba2534d9457dfedf18baebc794
```

Created via:

```bash
git worktree add \
  -b codex/complete-memory-store-runtime-proof \
  /Volumes/Dev_SSD/Codexify-memoryfix-proof-06350556 \
  063505561c8b105708334b92de5abb567da59cba
```

## 4. Clean pre-proof state

```text
$ git status --short --branch
## codex/complete-memory-store-runtime-proof

$ git diff --name-only
(empty)

$ git diff --cached --name-only
(empty)

$ test ! -e guardian/memory/store.db
PASS — store.db absent
```

`HEAD == candidate commit`. No tracked/staged modifications. No
pre-existing legacy store.db. (The two `test_plugin/*` items
previously visible on `/Volumes/Dev_SSD/Codexify-memoryfix-8cfe9daa`
are not on this worktree's filesystem — `git status --short` shows
clean state.)

## 5. Python proof

### 5.1 Focused regression (startup boundary + ContextBroker)

This is the successful result from the completed runtime proof. It was not
rerun during safeguard reconciliation because the required cache gate in §5.2
failed first.

```text
$ /Users/chriscastillo/.codex/worktrees/dda8/Codexify-main/venv/bin/python -m pytest -v \
    tests/core/test_memory_store_startup_boundary.py \
    guardian/tests/test_context_broker_memory.py

collected 6 items

tests/core/test_memory_store_startup_boundary.py ....                    [ 66%]
guardian/tests/test_context_broker_memory.py ..                          [100%]

======================== 6 passed, 10 warnings in 2.82s ========================
```

Four parametrized import-seam tests:

- `test_import_seam_does_not_create_legacy_sqlite_store_db[guardian.core.dependencies]` — **passes**
- `test_import_seam_does_not_create_legacy_sqlite_store_db[guardian.connectors.google]` — **passes**
- `test_import_seam_does_not_create_legacy_sqlite_store_db[guardian.guardian_api]` — **passes**

Plus the explicit-MemoryStore preservation test:

- `test_explicit_memory_store_construction_still_works` — **passes** (verifies `MemoryStore(temp_path)` still creates its schema and `_init_db()` is idempotent)

Plus the ContextBroker tests (post-repair contract):

- `test_dependencies_does_not_initialize_legacy_memory_store_at_import` — **passes** (asserts new contract: `dependencies._memory_store is None`)
- `test_context_broker_memory_integration` — **passes** (uses an isolated `LegacyMemoryStore(str(tmp_path / "isolated.db"))` per spec authorization)

**Summary: 6 / 6 pass.**

### 5.2 Safeguard-gate reconciliation (`guardian/tests/test_safeguards.py`)

The original completion invocation exposed an **invalid pre-existing proof
gate**, not a MemoryStore-repair regression. The candidate left
`guardian/tests/test_safeguards.py` byte-identical to parent
`8cfe9daa5c15dbed59e626206f22dfd28032ed1c`; its obsolete
`test_memory_query_caching` was therefore present before the repair.

The explicit contract inspection recorded:

```text
guardian/tests/test_safeguards.py:111:async def test_memory_query_caching():
guardian/tests/test_safeguards.py:116:    await store.store_memory(...)
guardian/tests/test_safeguards.py:125:        result = await store.query_by_tags(["test"])

guardian/memory/query_memory.py:105:    def query_by_tags(...)
guardian/memory/query_memory.py:257:        return get_memory_store().query_by_tags(tags, limit)
```

`MemoryStore` exposes synchronous `query_by_time`, `query_by_tags`, and
`query_by_content` methods. It defines no `store_memory` method. The stale
test therefore first awaited a nonexistent API and then treated a synchronous
query method as awaitable. It could not truthfully prove the current
MemoryStore contract, so it was removed without being renamed, rewritten,
skipped, or converted to an expected failure.

The valid proof map is now:

| Contract | Dedicated coverage |
|---|---|
| Generic cache decorators | `guardian/tests/test_efficiency.py::test_cache_decorators` |
| Explicit MemoryStore construction and import purity | `tests/core/test_memory_store_startup_boundary.py` |
| ContextBroker repaired initialization | `guardian/tests/test_context_broker_memory.py` |
| Supported Compose runtime behavior | this proof artifact, §6 |

The Compose runtime proof in §6 was not rerun or altered by this
reconciliation; the candidate runtime implementation remains unchanged.

The replacement cache gate was invoked from the reconciliation worktree using
the available repository test interpreter because the prescribed `python`
alias is absent. It did **not** pass:

```text
$ /Users/chriscastillo/.codex/worktrees/dda8/Codexify-main/venv/bin/python -m pytest -v \
    guardian/tests/test_efficiency.py::test_cache_decorators

guardian/tests/test_efficiency.py E
AttributeError: CACHE_DIR
```

The failure occurs in `setup_test_env` while accessing
`Config.CACHE_DIR`, before `test_cache_decorators` exercises either caching
decorator. No cache implementation change is authorized here. Per the task's
stop rule, the startup-boundary, ContextBroker, and config-coherence focused
reconciliation commands were not rerun after this failed valid gate.

After retiring the invalid MemoryStore test, the five remaining safeguards are
deliberately **not** claimed green. Their prior model-call, plugin-limit,
logger-batching, plugin-concurrency, and throttling failures/timeouts remain
separate pre-existing baseline debt; they were left unchanged and were not
repaired or suppressed by this reconciliation.

### 5.3 Config coherence (`tests/core/test_config_coherence.py`)

This is the successful result from the completed runtime proof. It was not
rerun during safeguard reconciliation because the required cache gate in §5.2
failed first.

```text
$ /Users/chriscastillo/.codex/worktrees/dda8/Codexify-main/venv/bin/python -m pytest --no-header -v tests/core/test_config_coherence.py

collected 16 items

tests/core/test_config_coherence.py ................                     [100%]

======================== 16 passed, 1 warning in 0.09s =========================
```

**16 / 16 pass.** Config coherence assertion logic agrees with the
candidate's runtime behavior in this test environment.

Note: this differs from the runtime `Config coherence check failed`
observed at backend startup (Section 6.3). The difference is that
`test_config_coherence.py` exercises `assert_config_coherence(...)` with
a controlled settings fixture built from the repository's normal
canonical configuration. The runtime failure at backend startup has a
different trigger (most likely `LOCAL_BASE_URL=http://localhost:8000/v1`
in `.env.example` vs. `http://host.docker.internal:8000/v1` required by
`v1-local-core-web-mcp` profile — leading to
`validate_supported_profile_runtime` mismatch). That's a
configuration-contract issue **distinct from** the MemoryStore repair,
out of scope here, and explicitly recorded as a separate later blocker
in the original NX-1 canonical receipt §54.4.

## 6. Container proof

### 6.1 Reused supported-runtime environment

Per spec §5 and the original NX-1 audit method, the supported profile
used:

```text
name: v1-local-core-web-mcp
version: 1
surface: local-docker-compose-webui
```

Image build: `codexify-backend-runtime:latest` (multi-service backend
image from `docker-compose.yml`).

Environment injection:

```bash
cp .env.example .env          # canonical .env template from this commit
chmod 600 .env
python3 -c "<substitute-proof-deterministic GUARDIAN_API_KEY + set LOCAL_CHAT_MODEL>"
# GUARDIAN_API_KEY=codexify-memoryfix-proof-063505561-20260822T180000Z
# LLM_MODEL=gemma-4-12b-it-qat-4bit
# LOCAL_LLM_MODEL=gemma-4-12b-it-qat-4bit
# LOCAL_CHAT_MODEL=gemma-4-12b-it-qat-4bit
# CODEXIFY_CONFIG_SOURCE=core
# CODEXIFY_SUPPORTED_PROFILE=v1-local-core-web-mcp
```

The proof key value (`codexify-memoryfix-proof-...`) is recorded only
by its prefix in this artifact; the full secret value remains only in
the local `.env` file and is never printed in this artifact.

### 6.2 Compose configuration validation

```text
$ docker compose --env-file .env -p codexify-memoryfix-probe config --quiet
exit=0
```

Resolved services (16): `db, neo4j, graph-init, migrator, model-prep,
backend, redis, worker-chat-embed, worker-coding, frontend,
worker-document-embed, worker-voice, e2e, worker-chat,
worker-account-import, worker-warmup`.

### 6.3 Container import probe (the missing gate from prior task)

```bash
$ test ! -e guardian/memory/store.db
PASS — absent

$ docker compose --env-file .env \
    -p codexify-memoryfix-probe \
    run --rm --no-deps backend \
    -c 'import guardian.guardian_api; print("guardian_api_import_ok")'
```

Result:

- Container entrypoint=`["python"]` (per `docker-compose.yml:269`).
  `run --rm --no-deps backend -c "..."` passes the `-c` flag as an
  argv item to the entrypoint, equivalent to
  `python -c "import guardian.guardian_api; print('guardian_api_import_ok')"`.
- Container exit code: **0**.
- Stdout contains: **`guardian_api_import_ok`** (last line of the
  container stdout).
- The full log includes:
  - `[routers] Router registration complete (beta_core_only=False)` —
    reached.
  - `[webui-basic] Serving from <redacted> at /ui` — the WebUI basic
    mount was reached.
- **No `sqlite3.OperationalError` or `attempt to write a readonly database` anywhere in the container log.**
- The `[startup] Config coherence check failed: <redacted> chars=31 / chars=29`
  ERROR-level events appear in the log because `uvicorn.run()` would
  have been reached next — the container's `entrypoint + command`
  chain died on the same ConfigCoherenceError that the bounded
  startup probe later surfaces explicitly (Section 6.4). The
  container exited because the entrypoint wrote `python -c "import …"`
  followed by `print("guardian_api_import_ok")`; once Python finished
  importing and printing, the entrypoint's argv finished, so the
  container process exited cleanly with code 0 *before* `uvicorn.run()`
  was reached. In other words: the **probe is `import`-only**, but
  `import` succeeds regardless of whether the *startup assertions*
  inside `guardian_api` would later fail.

Afterward:

```text
$ test ! -e guardian/memory/store.db
PASS — host-side legacy DB was not manufactured
```

**The actual supported-Compose backend image imports the application
without the SQLite error.**

### 6.4 Bounded backend-startup observation (the second missing gate)

Fresh isolated Compose project `codexify-memoryfix-startup`. Same
backend image. Same `.env`.

Step-by-step:

```bash
$ docker compose --env-file .env -p codexify-memoryfix-startup up -d db redis
container codexify-memoryfix-startup-redis-1 Started
container codexify-memoryfix-startup-db-1 Started

$ docker compose --env-file .env -p codexify-memoryfix-startup run --rm migrator
[Migrator] Done                                # exit 0

$ docker compose --env-file .env -p codexify-memoryfix-startup run --rm model-prep
[embed-model] download complete                 # exit 0

$ docker compose --env-file .env -p codexify-memoryfix-startup run --rm graph-init
[graph-init] Done.                              # exit 0

$ docker compose --env-file .env -p codexify-memoryfix-startup up -d backend
container codexify-memoryfix-startup-backend-1 Started

$ docker compose --env-file .env -p codexify-memoryfix-startup ps -a backend
codexify-memoryfix-startup-backend-1   ...   Exited (3) 10 seconds ago
```

Backend container state: `Exited (3)`. **NOT `Exited (1)`** (the
exit-code observed in NX-1 §54.2 on `8cfe9daa` ancestor).

`docker inspect` state:

```text
"Status": "exited",
"OOMKilled": false,
"ExitCode": 3
```

OOMKilled is false (not a memory exhaustion). ExitCode 3 differs from
the NX-1 sqlite exit-code path.

Backend logs (verbatim, filtered for non-redaction-noise lines):

```text
[Backend] Waiting for Postgres via DSN
[wait] Postgres is ready
[Backend] Verifying required tables + alembic_version
[Backend] OK: alembic_version=1c0a2b3c4d5e
[Backend] Running seed defaults
[docker] run: /usr/local/bin/python /app/backend/scripts/seed_defaults.py
[docker] exec: /usr/local/bin/python -m uvicorn guardian.guardian_api:app --host 0.0.0.0 --port 8888
YYYY-MM-DD HH:MM:SS - guardian.guardian_api - INFO - [routers] Router registration complete (beta_core_only=False)
YYYY-MM-DD HH:MM:SS - guardian.guardian_api - INFO - [webui-basic] Serving from <redacted> at /ui
INFO:     Started server process [1]
YYYY-MM-DD HH:MM:SS - guardian.config.system_config - INFO - log_event=<redacted> chars=29
YYYY-MM-DD HH:MM:SS - guardian.config.system_config - INFO - log_event=<redacted> chars=29
YYYY-MM-DD HH:MM:SS - guardian.config.system_config - INFO - log_event=<redacted> chars=29
YYYY-MM-DD HH:MM:SS - guardian.config.system_config - INFO - log_event=<redacted> chars=29
ERROR:    log_event=<redacted> chars=31
ERROR:    log_event=<redacted> chars=29
```

Critical observations:

- **No `sqlite3.OperationalError` anywhere in the backend log.**
- Backend reached `[routers] Router registration complete` and `INFO: Started server process [1]`. The two ERROR lines + process exit correspond to the `assert_config_coherence(settings)` failure path at `guardian_api.py:615` which logs `[startup] Config coherence check failed: <exc>` and re-raises. Note the redacted log size `chars=31` / `chars=29` matches the expected redaction-shape of the EXCEPTION MESSAGE inside a structlog safe-logger wrapper (each contains CONFIG-NAME + VALUE text where VALUE is sensitive/replaced by `<redacted>`).
- The exact line numbers and pattern match NX-1 §54.4 — this is the **same** `ConfigCoherenceError` previously recorded as secondary/probe-only evidence in the NX-1 canonical receipt. Under the candidate, that secondary observation becomes the *first* observable failure (because the SQLite one is gone).

**This is the positive evidence pattern the spec describes:**

```text
old state (NX-1): import → SQLite readonly failure, uvicorn never reached bind phase
new state (this proof): import → Config coherence check failed, uvicorn reached bind phase
```

The first material runtime blocker has changed identity: from
`sqlite3.OperationalError: attempt to write a readonly database`
(NX-1) to `Config coherence check failed` (this proof). The MemoryStore
repair is therefore proven at runtime.

Whether port `8888` bound: **No.** uvicorn logged `Started server process [1]`
but did not bind port 8888 before `assert_config_coherence` raised and
killed the process. Port binding is unnecessary for this proof — the
spec's REPAIR-PROOF-PASS criterion is:

> "The candidate: … is exercised through the actual supported Compose backend service; does not recreate or hit the SQLite readonly failure; progresses to a later startup boundary without filesystem workaround."

All three are satisfied. The full NX-1 release qualification is a
separate task; this proof deliberately stops at the runtime boundary
the NX-1 receiver-architecture identified.

### 6.5 Whether the SQLite readonly error recurred

**No.** A direct grep of the entire bounded-backend log for
`sqlite | OperationalError | readonly | query_memory | memory_store`
returns zero matches.

### 6.6 Whether the import manufactured `guardian/memory/store.db`

**No.** The post-probe `test ! -e guardian/memory/store.db` check
passes for both:

- the run-mode container import probe (`codexify-memoryfix-probe`,
  §6.3)
- the bounded-backend-startup observation (`codexify-memoryfix-startup`,
  §6.4)

The host-side `guardian/memory/store.db` was never created by either
probe. Both containers ran with `--no-deps` or with healthy dependencies
in the same isolated Compose project; neither resulted in any
filesystem write to that path.

## 7. Final classification

`REPAIR PROOF BLOCKED`

The runtime repair remains **proven-live-runtime** on the original
candidate proof surface. The proof-integrity reconciliation is nevertheless
blocked: a required valid replacement safeguard gate errors before executing
its cache assertions. This document must not represent the full safeguard
file as green or preserve `REPAIR PROOF PASS` while that gate is unresolved.

Completed evidence and uncompleted reconciliation gates:

- [x] Candidate begins from exact `063505561...`
- [x] Candidate implementation remained unchanged through the reconciliation
- [x] The stale `test_memory_query_caching` test was retired because it assumes nonexistent async `store_memory` and async `query_by_tags` APIs
- [ ] Generic cache decorator gate — **BLOCKED** at test fixture setup: `AttributeError: CACHE_DIR`
- [ ] Focused startup-boundary, ContextBroker, and config-coherence gates — not rerun after the required cache gate failed
- [x] Historical runtime-proof runs remain recorded: focused regression 6/6 and config coherence 16/16 in §§5.1 and 5.3
- [x] Remaining five safeguards remain visibly separate baseline debt; the file is not claimed green
- [x] Fresh worktree begins without `guardian/memory/store.db`
- [x] Compose `config --quiet` validates
- [x] Actual backend-container import is executed (entrypoint=`python -c '...'`; exit 0; `guardian_api_import_ok` printed)
- [x] **Old SQLite readonly error does not recur** in any log line
- [x] **Import does not manufacture `guardian/memory/store.db`**
- [x] Bounded backend startup is actually executed; backend reaches `[routers] Router registration complete` and `Started server process [1]`
- [x] Old SQLite blocker is absent from backend-startup logs
- [x] **First later startup state is captured**: `[startup] Config coherence check failed` (the secondary observation already recorded in NX-1 §54.4)
- [x] No filesystem/config workaround was used (no pre-creation, no chmod/chown, no privileged container, no volume change, no `.env` edits beyond canonical-template substitution and proof-key generation)

## 8. Invariants check (this proof window)

| # | Invariant | Status |
|---|---|---|
| 1 | Candidate code remains byte-for-byte unchanged | **confirmed** — `git diff --stat 063505561…` returns no output; `git diff --cached` empty; `git status` clean on the proof worktree |
| 2 | PostgreSQL remains canonical | confirmed (no schema/migration/auth edit) |
| 3 | Legacy SQLite is not promoted | confirmed — `MemoryStore` is not in any `route_posture.enabled` list and remains a legacy seam |
| 4 | No memory migration occurs | confirmed |
| 5 | No identity/retention/consent behavior changes | confirmed |
| 6 | No ContextBroker retrieval semantics change | confirmed (verified in §6.3 / §6.4 — broker construction works for both `dependencies._memory_store=None` and explicit `LegacyMemoryStore(path)` instances) |
| 7 | No configuration fix occurs | confirmed (this task does not modify `00-current-state.md`, supported profile, docker-compose, migrations, or `.env`-template content) |
| 8 | No Compose architecture change | confirmed (only `docker compose run/up/down` invocations against existing topology) |
| 9 | No supported-profile change | confirmed |
| 10 | No provider change | confirmed |
| 11 | No connector change | confirmed |
| 12 | No Command Bus change | confirmed |
| 13 | No release claim changes | confirmed (no `00-current-state.md`, capability-ledger, or release-posture edit) |
| 14 | Candidate proof is not current-main proof until merge | confirmed — `origin/main` is at `8cfe9daa…`; candidate is `063505561…` ahead by 1 |
| 15 | Later blocker is not permission to widen scope | confirmed — stopped at `Config coherence check failed` per spec §9 |
| 16 | Failure/timeout reported honestly | confirmed — see §5.2 and §6.3/§6.4 |
| 17 | Import purity proven in actual backend container, not inferred | confirmed — the container import probe is the spec's preferred `docker compose ... backend -c "..."` form against the real backend image |
| 18 | No ignored SQLite artifact as hidden setup | confirmed — `store.db` is gitignored and was created **only** by clean-state bare-metal test phases after `guard:check`); the proof worktree's `store.db` was checked absent pre- and post-probe |
| 19 | Canonical historical NX-1 receipt remains untouched | confirmed — `docs/architecture/proofs/2026-08-21-current-main-supported-runtime-audit.md` was not edited by this proof |
| 20 | NX-1 remains open | confirmed — this proof is *repair proof*. NX-1 itself remains BLOCKED until the `Config coherence check failed` blocker (the next first boundary) is itself repaired and a fresh NX-1 continuation is authorized. |

## 9. NX-1 closure status

**NX-1 is NOT closed by this proof.** This proof documents that the
candidate `Remove eager MemoryStore startup write` repair is correct
in scope and sufficient in effect to remove NX-1's first material
runtime blocker. NX-1 itself remains BLOCKED until a separate task
addresses the boundary that this proof identified as the new first
failure (`Config coherence check failed` / `LLMConfigError("supported
profile requires blessed local gateway contract: ...")`).

A complete NX-1 rerun is an authorized separate future Task Spec.

## 10. Out-of-scope observations carried forward

These are NOT repaired by this proof. They are recorded for the next
reviewer so the next steering task can plan accordingly.

- **`tests/core/test_config_coherence.py` passes in the test environment** even though the runtime `assert_config_coherence(...)` raises. This is because the test environment's `Settings` fixture is built with the supported profile's expected `LOCAL_BASE_URL=http://host.docker.internal:8000/v1` while the supported-Compose `.env` template (`docker-compose.yml:340`) reads `LOCAL_BASE_URL=http://localhost:8000/v1`. The discrepancy is a runtime-config-source question (the supported profile enforces a different value than the template provides). It is out of scope here.
- **Safeguard baseline debt remains visible.** The obsolete
  `test_memory_query_caching` was retired because it cannot exercise the
  current MemoryStore API. The remaining model-call, plugin-limit,
  logger-batching, plugin-concurrency, and throttling safeguards are unchanged
  and are not claimed green. The replacement generic cache gate is separately
  blocked at `Config.CACHE_DIR` fixture setup; no cache repair is authorized.

## 11. Specific evidence summary (one-screen reference)

| Item | Status | Source section |
|---|---|---|
| Candidate commit | `063505561c8b105708334b92de5abb567da59cba` | §2 |
| Origin/main | `8cfe9daa5c15dbed59e626206f22dfd28032ed1c` | §2 |
| Steering-commit canonical | yes (`merge-base --is-ancestor` exit 0) | §2 |
| Candidate descended from origin/main | yes (parent == origin/main) | §2 |
| Candidate implementation unchanged | yes (diff vs candidate = empty) | §8/§1 |
| Fresh worktree store.db absent pre-proof | yes | §4 |
| Focused regression | 6/6 pass | §5.1 |
| Config coherence | 16/16 pass | §5.3 |
| Safeguards | stale MemoryStore test retired; remaining 5 are not claimed green; valid cache replacement gate blocked at `Config.CACHE_DIR` fixture setup | §5.2 |
| Compose `config --quiet` | exit 0 | §6.2 |
| Container import probe | exit 0; `guardian_api_import_ok` printed | §6.3 |
| Old SQLite error in container log | absent (grep = empty) | §6.3, §6.5 |
| `store.db` post-probe | absent | §6.3, §6.6 |
| Bounded backend-startup | executed; backend reached router-registration + uvicorn-startup; died at `Config coherence check failed` | §6.4 |
| Old SQLite error in backend-startup log | absent (grep = empty) | §6.5 |
| First later blocker | `Config coherence check failed` | §6.4 |
| Filesystem workaround | none used | §6.5/§6.6/§8 |
| Implementation file changes during proof | none | §8 |
| Final classification | `REPAIR PROOF BLOCKED` — live runtime repair remains proven, but valid safeguard reconciliation is blocked | §§1, 7 |
