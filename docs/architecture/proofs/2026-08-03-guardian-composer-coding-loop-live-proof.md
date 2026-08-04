# Guardian Composer Coding Loop Live Proof

Proof date: 2026-08-03

Runtime window: 2026-08-03 14:56-15:16 EDT

## Outcome

`hold`

Every runtime prerequisite for the Guardian Composer Coding Loop now passes
live: the exact `worker-coding` image builds, the canonical Pi readiness gate
reports `ready` (provider `deepseek`, model `deepseek-v4-flash`, credential
present, adapter initialized), and the full supported Compose path
(`db`, `redis`, `migrator`, `model-prep`, `backend`, `worker-coding`,
`frontend`) runs healthy. The live browser lane was then attempted with the
exact harmless read-only request.

The browser submission stopped before any HTTP request reached the backend.
The Composer's durable-source-thread creation crashed with a client-side
`ReferenceError: CANONICAL_SINGLE_USER_ID is not defined` in
`frontend/src/features/chat/GuardianChat.tsx` (line 3163, local auth mode).
The Coding Loop dispatch therefore never persisted the source message, never
called `POST /api/agents/coding/execute`, and the coding queue never received a
task. The worker's readiness and the backend's health are proven; route
acceptance, queue enqueue, worker dequeue, adapter execution, provider
response, result persistence, result return, terminal rendering, and durable
readback all remain unproven because the browser lane is blocked by a real
implementation defect.

Per the task failure policy, this proof stops at the defect and documents the
smallest follow-up implementation task. No production code was modified.

This result supersedes the earlier `next-proof-needed` record in this file:
the previously missing Pi SDK build, worker auth store, and provider
credential prerequisites are now present and live-proven. The remaining
blocker is a frontend defect, not an environment or credential gap.

## Repository identity

- Branch: `codex/wire-coding-loop-into-composer`
- Full `HEAD`: `72ed4fe49aa8695b05719d0c266b89d7de824889`
- Implementation commits on the branch:
  - `b70c337b8e1fe02d808451e3bdd56a2531690e5a` Wire Coding Loop into Guardian Composer
  - `97eb3f70fd8295d5071dd7977028da25e7e27b68` Merge origin/main into Coding Loop branch
  - `c038725e872e0c2d7813f532e697e0e9aeb636d8` Prove Guardian Composer Coding Loop
  - `72ed4fe49aa8695b05719d0c266b89d7de824889` Make Coding Worker Pi-ready
- Implementation ancestry: pass; both `git merge-base --is-ancestor` gates exited `0`
- Worktree before proof: clean
- Execution lane: architecture-impact
- Task kind: proof
- Evidence posture reached: runtime prerequisites test-proven **and** live
  readiness-proven; live browser submission attempted and blocked by a
  frontend implementation defect

## Compose project and service posture

- Compose project: `codexify`
- Compose invocation: default project invocation, no explicit profile
- Compose inputs selected by the default invocation:
  `docker-compose.yml` and `docker-compose.override.yml`
- Exact service name for the coding worker: `worker-coding`
- Required path services named by the Compose graph:
  `db`, `migrator`, `model-prep`, `graph-init`, `backend`, `redis`,
  `worker-coding`, `frontend`
- Exact services started by this proof:
  `db` (already healthy), `redis` (already healthy), `migrator` (already
  completed, exit 0), `model-prep` (already completed, exit 0), `backend`,
  `worker-coding`, `frontend`
- `graph-init` was not run: its `neo4j` dependency is pre-existing
  `unhealthy` on this machine because the pre-existing `neo4j_data` volume was
  initialized with an older `NEO4J_PASS` (direct cypher-shell probe:
  "incorrect authentication details"). The graph lane is noop on the supported
  path (`CODEXIFY_ENABLE_GRAPH_WRITES=false`, `CODEXIFY_GRAPH_BACKEND=noop`)
  and the Coding Loop never touches Neo4j, so the proof proceeded without
  deleting the volume or running `graph-init`.
- Because `graph-init` was not run, `backend`, `worker-coding`, and
  `frontend` were started with `docker compose up -d --no-deps` after their
  real prerequisites were verified manually (db healthy, redis healthy,
  migrator/model-prep completed, backend healthy before worker and frontend
  start). This is the only deviation from plain `docker compose up`; it is
  documented here rather than hidden.

## Sanitized environment prerequisites

No secret value was printed, echoed, or written into this receipt.

| Prerequisite | Result | Evidence |
| --- | --- | --- |
| Supported local posture | pass | `.env` declares local-only mode, cloud providers disabled, local LLM provider |
| Exact worker image build | pass | `docker compose build worker-coding` succeeded against HEAD |
| Node executable in worker image | pass | readiness `node_executable: available` |
| Guardian Pi wrapper | pass | readiness `guardian_pi_wrapper: available` |
| Pi SDK runtime (`pi-sdk` image stage) | pass | readiness `pi_sdk_runtime: available` |
| Worker home `/home/codexify` | pass | readiness `worker_home: available` |
| Pi auth material in worker home | pass | readiness `pi_auth_material: available` |
| Auth-file permissions | pass | readiness `pi_auth_permissions: restricted` (mode `0600`) |
| Effective provider | pass | `deepseek` (operator `PI_PROVIDER`, matching host Pi auth store and ADR-052's approved DeepSeek lane) |
| Effective model | pass | `deepseek-v4-flash` (operator `PI_MODEL`) |
| Provider credential | pass | readiness `provider_credential: available` |
| Non-executing adapter initialization | pass | readiness `adapter_initialization: available` |
| Credential validity | unproven | readiness contract states presence-only; a live provider call never occurred because the browser lane was blocked before dispatch |
| Container egress to provider | pass | sanitized in-container probe reached `https://api.deepseek.com` (HTTP 401 without credential, i.e. endpoint reachable) |

## Authentication method used

The operator's canonical host Pi auth store (`~/.pi/agent/auth.json`,
containing a `deepseek` credential) was copied into the persistent named
volume `codexify_pi_auth` at its canonical path
`/home/codexify/.pi/agent/auth.json` with mode `0600`, using a one-off
container. No credential value was printed, and the credential lives only in
the named volume and the operator home — never in the image, the repository,
or this receipt. This is the runbook's canonical auth-file location populated
from the operator's existing Pi login rather than an interactive `/login`.

## Effective provider and model

- Provider: `deepseek` (Pi provider id; credential type `api` key in the
  mounted auth store)
- Model: `deepseek-v4-flash` (the ADR-052-approved DeepSeek V4 Flash lane)
- Selected by the operator's `PI_PROVIDER` / `PI_MODEL` environment, which
  Docker Compose interpolates into `worker-coding`; the wrapper default
  (`anthropic` / `claude-sonnet-4-20250514`) was not used.

## Intended bounded request

The request was submitted from the browser exactly as follows:

```text
Read docs/architecture/00-current-state.md and return a concise five-bullet summary. Do not modify files, run network requests, commit changes, or create a pull request.
```

Request permission policy (sent by the Composer in `GuardianChat.tsx`
`handleCodingLoopDispatch`):

- explicit mode: `Coding Loop`
- `allow_shell=false`
- `allow_network=false`
- `allow_write=false`
- `allowed_paths=[]`
- `max_runtime_seconds=300`
- `adapter_kind=pi_codex_runner`
- `repo_root=null`

## Source and execution identities

No request reached the backend, so no execution identities were created.

| Identity | Value |
| --- | --- |
| Source thread id | not created |
| Source message id | not created |
| Coding task id | not created |
| Attempt id | not created |
| Accepted run id | not created |
| Deployment id | not created |

The Composer's thread-creation call crashed before `POST /api/chat/threads`,
so no source message was persisted. This preserves the distinction between
source-message identity and execution-attempt identity without inventing
placeholder evidence.

## Milestone evidence

| Milestone | Result | Evidence and boundary |
| --- | --- | --- |
| 1. Readiness gate | **proven** | Readiness `ready` (human and JSON), exit `0`; same gate passed inside the live `worker-coding` startup path; Compose healthcheck green; worker process alive after the gate |
| 2. Route acceptance | blocked before attempt | Browser submission aborted client-side before any HTTP request; backend logs show no `POST /api/chat/threads` and no `POST /api/agents/coding/execute` in the window |
| 3. Queue enqueue | not run | Queue `codexify:queue:coding-execution` observed at depth `0` before and after the browser attempt |
| 4. Worker dequeue | not run | `worker-coding` healthy and idle; no task was dequeued |
| 5. Adapter execution | not run | No `pi_codex_runner` invocation occurred |
| 6. Provider response | not run | No DeepSeek request was made; credential validity remains unproven |
| 7. Terminal result persistence | not run | No run or coding-result artifact exists from this proof |
| 8. Result return to source lineage | not run | No source thread/message or result was created |
| 9. WebUI terminal rendering | not run | No run card was created in the DOM |
| 10. Durable WebUI readback | not run | No terminal card existed to refresh or reconstruct |

No milestone has been collapsed into a generic "worked" claim.

## HTTP and projection evidence

No live Coding Loop HTTP request was issued by the browser. The authenticated
read `GET /api/chat/threads` was called from the browser proof harness for
thread identification and returned HTTP 200 with the pre-existing thread
list; no new thread appeared because creation crashed client-side.

The following authenticated projections were not called because no `run_id`
or `thread_id` existed:

- `GET /api/agents/runs/{run_id}`
- `GET /api/agents/runs/{run_id}/coding`
- `GET /api/chat/{thread_id}/coding-runs`

The focused automated authorization-boundary test passed:

```text
.venv/bin/python -m pytest -q \
  guardian/tests/routes/test_agent_orchestration_events.py::test_coding_run_snapshot_is_scoped_and_path_bounded
```

Result: pass (`1 passed`). This proves coding-snapshot owner-scoping and
bounded-path projection behavior at the automated-test level only.

## Health and worker evidence

Exact service-status command used:

```text
docker compose ps --all db redis migrator model-prep backend worker-coding frontend
```

Observed posture:

- `db`: Up, healthy
- `redis`: Up, healthy (pre-existing)
- `migrator`: Exited (0)
- `model-prep`: Exited (0)
- `backend`: Up, healthy (restarted once, see Warnings)
- `worker-coding`: Up, healthy; readiness `ready`; consumer launched; process
  alive after the startup gate; `restart` count 0
- `frontend`: Up; Vite dev server answered HTTP 200 on port 5173

Exact readiness commands used:

```text
docker compose build worker-coding
docker compose run --rm --no-deps --entrypoint python worker-coding \
  /app/backend/scripts/docker/check_worker_coding_readiness.py --format human
docker compose run --rm --no-deps --entrypoint python worker-coding \
  /app/backend/scripts/docker/check_worker_coding_readiness.py --format json
```

Readiness output (human):

```text
Pi coding-worker readiness: ready
Effective provider: deepseek
Effective model: deepseek-v4-flash
Credential validity: unproven (presence only)
- node_executable: available
- guardian_pi_wrapper: available
- pi_sdk_runtime: available
- worker_home: available
- pi_auth_material: available
- pi_auth_permissions: restricted
- effective_provider: configured
- adapter_initialization: available
- provider_credential: available
```

Readiness JSON summary: `status=ready`, `can_consume_tasks=true`,
`reasons=[]`, `warnings=[]`, `schema_version=1`.

Exact queue command used:

```text
docker compose exec -T redis redis-cli LLEN codexify:queue:coding-execution
```

Result: `0` before and after the browser attempt.

Worker logs (sanitized, startup tail): readiness lines identical to the
standalone check above, then

```text
[wait] TCP ready: 127.0.0.1:11434
[worker-coding] Launching coding worker with localhost Ollama bridge 127.0.0.1:11434 -> host.docker.internal:11434
```

No dequeue, adapter, provider, or result-return log lines exist because no
task was enqueued.

## Browser verification result

Blocked by a real implementation defect. Detailed observed sequence:

1. `http://localhost:5173/` loaded; top navigation rendered
   (`data-testid="app-shell-top-nav-rail"`).
2. Guardian view opened (`/chat`); composer rendered
   (`data-testid="composer-textarea"`).
3. No active thread was present; the Composer was expected to auto-create the
   durable source thread (the canonical path in `flows.md` flow 1A step 1).
4. Coding Loop mode engaged
   (`data-testid="composer-coding-loop-toggle"`; send control changed to
   "Dispatch Coding Loop").
5. The exact harmless request was entered and submitted.
6. Browser console immediately reported:

```text
[guardian] thread creation failed ReferenceError: CANONICAL_SINGLE_USER_ID is not defined
    at http://localhost:5173/features/chat/GuardianChat.tsx:2502:68
```

7. No `data-testid="coding-loop-run-card"` and no
   `data-testid="coding-loop-dispatch-failure"` card rendered, because the
   crash happened inside thread creation before dispatch.
8. Backend logs show no `POST /api/chat/threads` and no
   `POST /api/agents/coding/execute` in the window; the queue remained at `0`.

The failure is deterministic: the object-spread expression at
`GuardianChat.tsx:3163` (`...(runtimeConfig.authMode === "remote" ? {} :
{ user_id: CANONICAL_SINGLE_USER_ID })`) evaluates the undefined identifier
in local auth mode and throws before `api.post` is called.

Root cause: mainline commit `62db7502d25842601177c464b4657b2103262c4f`
("Fix remote-auth thread ownership payload", 2026-07-09) deleted the
module-level definition `const CANONICAL_SINGLE_USER_ID = "local";`
(previously line 165) but left the usage at what is now line 3163. The
identifier has no definition, import, or global declaration anywhere in the
repository. Vite's dev server does not typecheck, so the error surfaces only
at runtime. This defect is present on `origin/main` and was merged into this
branch by `97eb3f70f`.

## Durable refresh/readback result

Not run. There was no terminal run to recover, so browser refresh and
same-thread reopening would not test the requested durable reconstruction
seam.

## Warnings

- The `backend` container was OOM-killed once (exit 137, `OOMKilled=true`)
  while the `frontend` service performed its first `pnpm install` on a
  Docker Desktop VM with ~3.8 GiB memory. The backend was restarted with the
  same `--no-deps` invocation and became healthy; this is an environmental
  resource-pressure event, not a code failure. Evidence commands used
  `docker compose up -d --no-deps backend` after the restart.
- `neo4j` is pre-existing `unhealthy` (stored-password mismatch on the
  pre-existing `neo4j_data` volume). `graph-init` was not run and the graph
  lane is noop on the supported path; `backend` was started with
  `--no-deps` accordingly. No volume was deleted.
- The operator shell exports `PI_PROVIDER=deepseek` / `PI_MODEL=deepseek-v4-flash`;
  these values are documented here because they are provider/model names, not
  secrets.
- Credential validity remains unproven: readiness proves only that Pi
  resolved a stored `deepseek` credential. No live provider call occurred.
- The dispatch shape `repo_root=null` means the worker's Git-backed mutation
  scope guard is not verified for this browser lane (the guard emits explicit
  unverified evidence when no cwd/repo root is supplied); read-only posture
  rests on `allow_write=false` plus the request text, not on a proven
  repository boundary.
- The runbook's `set -a; source .env` ritual still fails on the apostrophe in
  `LOCAL_PROVIDER_DISPLAY_NAME`; `docker compose config --quiet` is the
  documented replacement and passes.
- The frontend bundle logs benign 404s for missing dev assets and a React
  setState-in-render warning; neither was observed to affect the proof.

## Failures

1. **Real implementation defect (blocker):** `ReferenceError:
   CANONICAL_SINGLE_USER_ID is not defined` at
   `frontend/src/features/chat/GuardianChat.tsx:3163`, triggered whenever the
   Composer must create a durable source thread in local auth mode. This
   blocks the Guardian Composer Coding Loop browser submission lane and also
   regular composer sends from a no-thread state. Introduced by mainline
   commit `62db7502d`; present on `origin/main`; merged into this branch.
2. Environmental, non-blocking: backend OOM-kill during frontend install
   (recovered), pre-existing `neo4j` unhealthy (graph lane noop, not used).

No runtime contradiction was observed in the backend, worker, queue, or
database because no coding request was accepted or executed.

## Smallest follow-up implementation task

Title: Repair Composer thread creation so the Coding Loop browser lane can
dispatch (restore the canonical single-user id constant).

Scope:

1. In `frontend/src/features/chat/GuardianChat.tsx`, restore a defined
   canonical single-user id for the local-auth thread-creation payload at
   line 3163. The minimal fix is re-adding the module-level constant
   `const CANONICAL_SINGLE_USER_ID = "local";` (the definition deleted by
   `62db7502d`); alternatively reuse the existing
   `COMMAND_BUS_ACTOR_ID = "local"` constant in the same file, or import a
   shared constants module — whichever the operator prefers, with no behavior
   change for remote auth mode.
2. Add a regression test covering Composer thread creation in local auth mode
   (extend `frontend/src/features/chat/__tests__/GuardianChat.test.tsx`).
3. Run frontend typecheck and the focused Vitest suite; confirm no other
   orphaned `CANONICAL_SINGLE_USER_ID` references exist.
4. Re-run this live proof from the browser: all ten milestones, from the
   exact harmless request through durable refresh readback, on the supported
   local Compose path.

This is the only change required to unblock the browser lane; the worker,
queue, persistence, and result-return rails were not implicated by any
observed failure.

## Exact commands run

Repository identity and scope:

```text
git merge-base --is-ancestor b70c337b8e1fe02d808451e3bdd56a2531690e5a HEAD
git merge-base --is-ancestor 72ed4fe49aa8695b05719d0c266b89d7de824889 HEAD
git status --short --branch
git rev-parse HEAD
```

Compose validation and build:

```text
docker compose config --quiet
docker compose build worker-coding
```

Auth provisioning (no secret values printed):

```text
docker run --rm \
  -v codexify_codexify_pi_auth:/mnt/pi \
  -v "$HOME/.pi/agent:/host-pi-agent:ro" \
  --entrypoint sh codexify-worker-coding-runtime:latest \
  -c 'mkdir -p /mnt/pi/agent && cp /host-pi-agent/auth.json /mnt/pi/agent/auth.json && chmod 600 /mnt/pi/agent/auth.json'
```

Readiness:

```text
docker compose run --rm --no-deps --entrypoint python worker-coding \
  /app/backend/scripts/docker/check_worker_coding_readiness.py --format human
docker compose run --rm --no-deps --entrypoint python worker-coding \
  /app/backend/scripts/docker/check_worker_coding_readiness.py --format json
```

Service startup (with documented `--no-deps` for the three services whose
Compose dependency chain includes the unrun `graph-init`):

```text
docker compose up -d --no-deps backend
docker compose up -d --no-deps worker-coding
docker compose up -d --no-deps frontend
docker compose ps --all db redis migrator model-prep backend worker-coding frontend
```

Health and queue probes:

```text
docker inspect --format '{{.State.Health.Status}}' codexify-backend-1
docker inspect --format '{{.State.Health.Status}}' codexify-worker-coding-1
docker compose logs backend --tail=15
docker compose logs worker-coding --tail=40
docker exec codexify-redis-1 redis-cli LLEN codexify:queue:coding-execution
curl -sS -o /dev/null -w "%{http_code}" http://localhost:8888/ping
curl -sS -o /dev/null -w "%{http_code}" http://localhost:5173/
```

Browser proof (host Playwright library, no repo files touched):

```text
cd /tmp/coding-loop-proof && npm i playwright@1.56.1 --no-audit --no-fund
CODEXIFY_GUARDIAN_KEY="$(grep '^GUARDIAN_API_KEY=' <repo>/.env | cut -d= -f2-)" \
  node proof.mjs
node debug2.mjs   # DOM + console-error capture after submit
```

Focused authorization-boundary validation:

```text
.venv/bin/python -m pytest -q \
  guardian/tests/routes/test_agent_orchestration_events.py::test_coding_run_snapshot_is_scoped_and_path_bounded
```

Docs validation and diff hygiene:

```text
.venv/bin/python scripts/validate_docs.py
git diff --check
```

No production runtime file was modified, no database mutation was made, no
volume was deleted, no repository file outside this proof document was
changed, and no credential value was printed.

## ADR impact

Classification: aligned with existing ADRs and contracts; no contract change.

- ADR-020 Guardian Mediated Coding Agent Execution Contract
- Guardian Build Loop Doctrine
- Runtime Protocol Token Contract
- Config and Ops contract
- Existing coding-worker and result-return contracts

This proof changes no execution authority, queue semantics, cancellation
semantics, result lineage, adapter behavior, or release posture. Guardian
remains the sole execution authority, and acceptance remains distinct from
completion. The defect found is a frontend runtime bug, not an authority or
contract violation.

## Documentation follow-through

`docs/architecture/00-current-state.md` is unchanged because the outcome is
not `go`. No proof helper was committed; the browser harness lives under
`/tmp/coding-loop-proof` as disposable operator tooling.

## Validation results

| Command | Result | Proof boundary |
| --- | --- | --- |
| `git merge-base --is-ancestor b70c337b8... HEAD` | pass | implementation ancestry only |
| `git merge-base --is-ancestor 72ed4fe49... HEAD` | pass | implementation ancestry only |
| `docker compose config --quiet` | pass | Compose file validity only |
| `docker compose build worker-coding` | pass | exact image build on HEAD |
| in-container readiness, human and JSON | pass (`ready`, exit 0) | prerequisite presence + non-executing adapter probe; not credential validity |
| `docker compose ps` health checks (`db`, `redis`, `backend`, `worker-coding`, `frontend`) | pass | live service health only |
| `.venv/bin/python -m pytest -q guardian/tests/routes/test_agent_orchestration_events.py::test_coding_run_snapshot_is_scoped_and_path_bounded` | pass (`1 passed`) | automated owner-scope and bounded-path projection behavior only |
| `.venv/bin/python scripts/validate_docs.py` | pass | documentation structure and required architecture links only |
| `git diff --check` | pass | tracked diff whitespace only before staging |
| sanitized secret and unrestricted-host-path scan of this receipt | pass | receipt content only |

These checks are not live Composer, queue, worker, adapter, persistence, or
browser proof.

## What this does not prove

This receipt does not prove:

- Guardian Composer route acceptance from the browser
- coding queue enqueue
- coding-worker dequeue or active task processing
- Pi adapter execution or a DeepSeek model response
- credential validity or provider reachability under a live call
- terminal coding-result persistence
- result return into the source thread
- terminal Composer card rendering
- durable reconstruction after browser refresh
- live cross-user readback rejection
- cancellation or retry
- repository mutation enforcement by the adapter
- concurrent or multi-agent execution
- Symphony scheduling
- release readiness or a widened supported beta surface

## Next proof prerequisites

1. Apply the smallest follow-up implementation task above (restore the
   canonical single-user id constant in `GuardianChat.tsx` and add a
   regression test).
2. Re-run this proof unchanged: build `worker-coding`, confirm readiness
   `ready`, start the supported services, submit the exact harmless request
   from the browser, and verify all ten milestones plus durable refresh
   readback.
3. Optionally record a live DeepSeek response to upgrade credential validity
   from "presence-only" to "validated".

## Axis KB recommendation

Record two operational facts for the Guardian Coding Loop:

1. The Pi-ready worker lane is now live-proven at the prerequisite level:
   image build, canonical readiness (`ready`), provider `deepseek` /
   `deepseek-v4-flash`, credential presence, and the healthy startup gate.
   The remaining blocker is a frontend ReferenceError, not the worker.
2. Mainline commit `62db7502d` ("Fix remote-auth thread ownership payload")
   left an orphaned `CANONICAL_SINGLE_USER_ID` reference in
   `frontend/src/features/chat/GuardianChat.tsx` (line 3163). Vite dev does
   not typecheck, so the Composer's thread-creation crash is runtime-only and
   breaks both Coding Loop dispatch and ordinary composer sends from a
   no-thread state in local auth mode. Any future "composer sends work" claim
   must include a browser-level thread-creation check.

## Secret-handling statement

No raw API key, session secret, provider token, Pi auth contents, environment
value, cookie, unrestricted host path, private prompt, or model payload is
included in this receipt. Provider and model names are documented because
they are not secrets.
