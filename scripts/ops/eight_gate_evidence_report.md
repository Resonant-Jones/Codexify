# Eight-gate evidence harness — build report

**Date:** 2026-11-06
**Repository:** Codexify, worktree `feat-auto-20261105-c8c1dc20`
**Evaluated checkout:** `e0022ba8f` (worktree HEAD); `origin/main` tip observed as `fba6e4dac`
**Rubric:** `docs/qualification/rubrics/release-readiness-gates.md` version 3

## Precondition — pause the Private Preview for the duration of the run

**The Private Preview must be stopped before the eight-gate run, and stay stopped until it
finishes.** This is a precondition of running the harness, not a preference.

This host runs Docker Desktop with a **7.7 GiB guest** on a host that was, on 2026-11-07,
down to **~130 MiB of free pages with 16 GiB of compressed memory**. Under that pressure the
host killed Docker Desktop itself and took the Private Preview's thirteen containers with it —
including a concurrently running proof, whose work was lost with the VM.

Two of these gates are the heaviest thing anyone will run here: gate 3 sends a real SIGTERM at a
real worker holding a real claim, and gate 2 needs an attempt older than 780 seconds against a
live stack. Running that beside a live Preview on this host is the exact condition that killed
Docker.

**Two heavy Docker workloads must never run concurrently on this host.** The Preview is the
largest single consumer, so pausing it is also the cheapest way to protect any other run in
flight.

Pause and restore, using the operator's own reconciler (the desired-up marker cannot be removed
in place on this host, so the pause is done by pointing the serving-source pin at a root the
reconciler rejects):

```sh
# pause: stop the project, then point the pin where the reconciler will not act
GOOD=/Volumes/Dev_SSD/Codexify-main/.worktrees/private-preview-serving-20261106
REPO=/Volumes/Dev_SSD/Codexify-main
PIN="$HOME/Library/Application Support/Codexify/private-preview/serving-source"

docker compose --project-directory "$REPO" --env-file "$REPO/.env.private-preview" \
  -p codexify_private_preview \
  -f "$GOOD/docker-compose.yml" \
  -f "$GOOD/docker-compose.private-preview.yml" \
  -f "$GOOD/docker-compose.private-preview-serving.yml" stop
printf '%s\n' "$REPO" > "$PIN"

# restore: point the pin back at the serving worktree and reconcile
printf '%s\n' "$GOOD" > "$PIN"
bash "$HOME/Library/Application Support/Codexify/private-preview/codexify_private_preview_autostart.sh" auto-start
```

Volumes are preserved by the pause; the restore brings the stack back in about a minute.

The **self-check** is safe to run with the Preview up: it launches no containers and no
subprocesses. The **runtime** is not — `eight_gate_runtime.py` drives the real stack through
`docker exec` into the Preview's own `db` and `redis` containers.

## Result

Three new files under `scripts/ops/`. No tracked file was modified; nothing under
`docs/`, `guardian/`, `config/`, or any compose file was touched.

| File | Purpose |
| --- | --- |
| `scripts/ops/eight_gate_evidence.py` | The harness. Eight independent gate functions, the CLI, and the JSON writer. |
| `scripts/ops/eight_gate_runtime.py` | The read-only runtime access layer: PostgreSQL, Redis, HTTP, headless Chromium, env-file parsing, credential redaction. |
| `scripts/ops/eight_gate_evidence_selfcheck.py` | 54 self-checks that verify the harness's own verdict logic without needing a stack. |

The harness runs against a stack that is already up. It never starts, stops, or
recreates a container, and it never writes to PostgreSQL or Redis. The only
writes are its own output JSON and — where a gate's PASS condition requires
driving the running product — ordinary calls to the product's own HTTP API
(a chat completion, an account login, a thread read).

**No gate reached PASS in this session, because no disposable stack was up.**
Only `codexify_private_preview` was running, and the brief forbids touching it.
The harness was validated against live scratch containers and a fake-driver
suite instead; see *Validation* below. The per-gate sections say exactly what
each gate needs from outside this repository.

## What the source actually says

The brief listed the evidence surfaces; each was verified against the source
before use, and two of them turned out to be described imprecisely.

| Claim | Verified |
| --- | --- |
| `codexify:worker:chat:heartbeat` and `codexify:worker:voice:heartbeat` are the only two heartbeat keys | **Confirmed.** `guardian/workers/chat_worker.py:178`, `guardian/voice/runtime.py:9`. No other worker module contains a heartbeat constant. |
| The rubric names four queues | **Confirmed but the set differs.** The rubric names `chat-embed`, `coding-execution`, `document-embed`, `account-import`. A chat completion is actually enqueued on `codexify:queue:chat` (`guardian/core/chat_completion_service.py:248`), which is **not** in the rubric's list. The harness observes the rubric's four *and* `codexify:queue:chat`, because the rubric's PASS condition ("a submitted request observed at a non-zero queue depth") can only be exercised on the queue the request really lands on. |
| Deadline length configurable by environment variable | **Not configurable.** `guardian/tasks/chat_deadline.py:22-23` defines `ACCEPTED_CHAT_TASK_WORK_BUDGET_SECONDS = 720` and `ACCEPTED_CHAT_TASK_TERMINAL_BUDGET_SECONDS = 60` as module constants. There is no `os.getenv` in that module and no deadline/budget variable in `docker-compose.yml` or the supported profile. The total budget is therefore a fixed 780 s. |
| Heartbeat payload timestamp | The chat worker writes `ts` as an **integer epoch** (`guardian/workers/chat_worker.py:686`), not an ISO string. The harness accepts both. |

Two consequences for the gates:

* **Deadline (gate 2)** cannot be driven past its own deadline by configuration.
  It requires an attempt that lives for ~13 minutes, or an existing attempt
  already past its deadline.
* **Graceful-stop (gate 3)** and **lock (gate 4)** both need a coding run that
  holds a claim. `backend/scripts/docker/run_worker_coding.py:100-108` calls
  `evaluate_pi_readiness()` and exits 78 before consuming anything when the Pi
  prerequisites are absent, so a claim only exists on a stack whose Pi runtime
  and credentials are in place.

## Per-gate report

### 1. queue/worker — UNPROVEN without a stack

* **Surface read.** `LLEN` on `codexify:queue:chat-embed`,
  `codexify:queue:coding-execution`, `codexify:queue:document-embed`,
  `codexify:queue:account-import`, and `codexify:queue:chat`; `GET` +
  `TTL` on `codexify:worker:chat:heartbeat` and
  `codexify:worker:voice:heartbeat`; the `chat_completion_attempts` row for
  the submitted request.
* **Observation path.** `gate_queue_worker` submits one chat completion
  through `POST /api/chat/{thread_id}/complete`, then samples the chat queue
  continuously at 100 ms while the attempt settles, re-reads the heartbeat at
  the end so its freshness is judged at the time of the read, and reads the
  durable attempt row back.
* **PASS reachable?** Yes, in principle. All three conditions are observable
  from a live stack: non-zero depth then zero, a fresh chat heartbeat, and a
  terminal attempt row.
* **What it needs.** A running backend that accepts the submission. The
  request path needs an authenticated session or a static key
  (`GUARDIAN_API_KEY`), and the *non-zero depth* observation needs the worker
  to be slow enough that a sample catches the request queued — on a fast local
  model the worker can claim it between two samples, in which case the gate
  honestly reports UNPROVEN rather than claiming a pass it did not see.
* **Liveness coverage limit honoured.** The harness records the voice
  heartbeat as an observation but never asserts liveness for
  document-embed, account-import, or coding-execution; only the chat queue is
  judged for liveness, per the rubric's limit.

### 2. deadline — UNPROVEN without a ~13-minute-old attempt

* **Surface read.** `chat_completion_attempts.deadline_snapshot`,
  `.turn_lock_token`, `.accepted_at`, `.terminal_event_type`,
  `.terminal_outcome`, and the constraint
  `ck_chat_attempt_recovery_snapshot_pair` read from `pg_constraint`.
* **Observation path.** `gate_deadline` reads every attempt row, separates
  (1) accepted attempts carrying a snapshot with a future `terminal_deadline_at`
  plus a turn lock from (2) attempts observed past their own
  `terminal_deadline_at` in a terminal state. Both must hold for PASS.
* **PASS reachable?** Yes, but not by configuration. Because the budgets are
  constants (720 s + 60 s), the second observation requires an attempt that
  has been open for at least ~13 minutes and has since been terminalised —
  typically one the recovery controller reconciled as `CHAT_ACCEPTED_TASK_ORPHANED`
  (`guardian/core/db.py:676-685`, gated by `ck_chat_attempt_orphan_outcome`).
  The harness reads any such attempt the stack already holds; it does not
  fabricate one.
* **What it needs.** Either a stack that has already produced a past-deadline
  terminal attempt, or a request that is left open for ~13 minutes. It does
  **not** need an environment variable — none exists.

### 3. graceful-stop — UNPROVEN without a claimed coding run

* **Surface read.** `agent_runs.status`, `coding_worker_instance_id`,
  `coding_worker_claim_id`, `coding_worker_last_heartbeat_at`; the Redis
  queue depth before and after; and the SIGTERM/SIGINT registration in
  `backend/scripts/docker/run_worker_coding.py`.
* **Observation path.** `gate_graceful_stop` reads the handler source, the
  canonical run rows, and the queue depth on both sides of the observation
  window. PASS requires a run that held a claim to be observed terminal with
  **both** ownership columns NULL and the queue depth unchanged.
* **PASS reachable?** The observation path is complete, but the *event* is not
  reachable from this repository or from an env file. It requires a coding run
  that holds a claim at the moment of the SIGTERM.
* **What it needs.** (a) A coding execution task in
  `codexify:queue:coding-execution`; (b) a coding worker whose Pi runtime is
  available (`node`, the Pi wrapper at `PI_WRAPPER_PATH`, the Pi SDK build,
  and `git` — `guardian/agents/pi_readiness.py:187-229`); (c) a provider
  credential that authorises the coding run to execute; and (d) an operator
  SIGTERM to that worker while it holds the claim. The harness deliberately
  does **not** stop the worker — the stack lifecycle belongs to another
  component — so it can observe the before/after but cannot produce the stop.
* **Note on the schema.** The rubric states the ownership pair "CHECK
  constraint requires to be both NULL or both NOT NULL"
  (`guardian/db/models.py:5817-5822`). I found no code path that NULLs either
  ownership column on terminalisation — `finalize_claimed_run_status` and
  `claim_coding_run_terminal` (`guardian/agents/store.py:1720-1738`) write
  only `status`, `ended_at`, and `error`. So on this revision the PASS
  condition depends on a release path that I could not locate in the source.
  This is stated as an observation, not a claim about the product.

### 4. lock — UNPROVEN without a queued coding run

* **Surface read.** The constraint `uq_agent_runs_coding_worker_claim_id` read
  from `pg_constraint` (with its `contype`, so "is it actually UNIQUE?" is
  answered, not assumed), and `claim_run_for_acceptance` in
  `guardian/agents/store.py:1519-1603`.
* **Observation path.** `gate_lock` first reads the constraint — an absent
  constraint is an immediate FAIL, exactly as the rubric's FAIL clause
  describes. It then finds one queued `agent_runs` row and issues **two
  concurrent** `claim_run_for_acceptance` calls against it through the
  product's own store code, then reads the run's ownership back to confirm
  exactly one holder and that the loser left no partial write.
* **PASS reachable?** The concurrent attempt is genuinely runnable — but it
  needs a queued coding run to claim, and it needs a **host-reachable**
  `DATABASE_URL`, because the two claims must open two independent
  transactions against the live database. When the stack only exposes
  PostgreSQL inside the Compose network, the harness reports the exact
  missing input rather than substituting a weaker observation.
* **What it needs.** (a) A queued coding run with a coding deployment
  (dispatch a coding execution task first); (b) a host-reachable
  `DATABASE_URL`; and (c) the same Pi runtime and provider credential as
  gate 3, if the run is to be produced by the product rather than by an
  operator.

### 5. migration-deployment — the most nearly satisfiable gate

* **Surface read.** `alembic_version` read **directly out of PostgreSQL** —
  row count and value, never a container exit code; the evaluated checkout's
  single Alembic head computed from `guardian/db/migrations` with Alembic's own
  `ScriptDirectory`; the migrator container's own logs; and the three refusal
  cases.
* **Observation path.** `gate_migration_deployment`:
  1. reads `alembic_version` from the database (exactly one row required);
  2. computes the checkout's head — verified here as `a7d4c9e2f1b3` across
     135 revisions;
  3. reads the migrator container's logs for its own
     `Migration source is coherent (N revisions)` line and its
     `Verified alembic_version == <rev>` line;
  4. exercises the three refusal cases by calling the migrator's own
     `compare_migration_sources` and `require_coherent_migration_source`
     against temporary doctored trees — stale image (a revision removed),
     same-head image with different revision content (a revision's bytes
     changed), and same-head source with a different migration environment
     (`env.py` changed). Each case is asserted to raise, and no migration is
     applied anywhere.
* **PASS reachable?** Yes. Against a live scratch PostgreSQL carrying the
  Codexify schema, this harness read `alembic_version = ['a7d4c9e2f1b3']`
  with `row_count = 1`, matching the checkout head, and all **3/3** refusal
  cases failed closed with no migration applied.
* **What it still needs.** The migrator container's own coherence verdict in
  its logs — that requires the migrator to have run against this checkout's
  source in the evaluated project. This is the one gate whose remaining
  requirement is a stack artifact rather than a credential or an export file.

### 6. browser — UNPROVEN without an account session and a populated thread

* **Surface read.** The DOM's own text from a real headless Chromium —
  `[data-testid="chat-message"]` and `[data-testid="chat-message-author"]`
  (`frontend/src/features/chat/ChatView.tsx:1088,1107`) — against the
  durable `chat_messages` / `chat_threads` rows.
* **Observation path.** `gate_browser` opens `/chat/{thread_id}` in Chromium
  with the account session token injected into `sessionStorage` under
  `guardian.auth.token` (the key the frontend itself uses,
  `frontend/src/lib/api.ts:135`), reads the DOM text, compares it against the
  durable rows, then reloads and re-reads to check the projected state
  survives. The browser version, viewport, device pixel ratio, and user agent
  are recorded, as the rubric requires.
* **PASS reachable?** Yes. The DOM read, the durable comparison, and the
  reload check are all implemented and were exercised against a real
  Chromium (141.0.7390.37) in this session; the PASS/FAIL transition was
  verified with a driven DOM.
* **What it needs.** (a) An **authenticated account session** — the rubric
  states plainly that an unauthenticated surface is not evidence for this
  gate, so the harness will not accept a static key here; supply
  `EIGHT_GATE_SESSION_TOKEN` or `EIGHT_GATE_ACCOUNT_<NAME>_SESSION`. (b) A
  reachable frontend (`--frontend-url`, or `CODEXIFY_FRONTEND_PORT` in the
  env file). (c) At least one chat thread with persisted messages.
* **Browser method reuse.** The prior stock-compose proof drove Chromium
  against a running frontend. The repo's own browser tooling is Playwright
  (`frontend/src/playwright.config.ts`, the `e2e` Compose service on
  `mcr.microsoft.com/playwright:v1.56.1-jammy`). The harness uses the local
  Playwright browser cache because it can run without starting a container;
  it drives the same Chromium and the same DOM selectors, and it reads the
  DOM rather than inferring from a screenshot.

### 7. import-recall — UNPROVEN without a real provider export

* **Surface read.** `openai_account_import_jobs` including its durable
  `checkpoint` and `staged_manifest`; the canonical imported `chat_threads`
  (`origin_system IN ('openai','anthropic')`) and their `chat_messages`; the
  Imports Project; and the recall result read back over HTTP.
* **Observation path.** `gate_import_recall` reads the durable job rows and
  their checkpoints, the canonical imported rows, and then issues the recall
  read for the owning account — both the native history search and the
  imported-history inspection route — recording what each returned. Because
  ADR-016 excludes imported records from *native* recall
  (`guardian/core/account_history_recall.py:711`, and
  `guardian/core/message_origin_classification.py:210`), the harness reads
  the imported-history inspection route as the recall surface for an imported
  record and records both.
* **PASS reachable?** Only with a **natural** import. The rubric is explicit
  that the 2026-10-09 synthetic proof cannot satisfy this gate.
* **What it needs.** (a) **A real provider export file** — an actual OpenAI
  or Anthropic account export, produced by the provider, not a synthetic
  fixture. This is the input I could not obtain and would not fabricate.
  Supply it with `--import-export-file`; without it the harness reports the
  natural/synthetic classification as unevidenced, which the rubric makes
  UNPROVEN. (b) The import performed through the product's natural path
  (`POST /api/imports/openai-account` → files → commit) so the account-import
  worker materialises it. (c) The owning account's session.

### 8. scope-isolation — UNPROVEN without two distinct accounts

* **Surface read.** The same read issued under two account identities —
  `GET /api/chat/{thread_id}/messages` and the history-search route — plus
  the canonical `user_id` on the rows.
* **Observation path.** `gate_scope_isolation` resolves two distinct account
  identities (from supplied session tokens, or by logging two accounts in),
  creates one record under the owning account through the product's API, then
  issues the **same** read under both identities against the **same** record
  identifier and compares what each saw.
* **PASS reachable?** Yes, provided two distinct accounts exist on the stack.
* **What it needs.** (a) **Two distinct authenticated accounts**, supplied as
  `EIGHT_GATE_ACCOUNT_<NAME>_SESSION` / `EIGHT_GATE_ACCOUNT_<NAME>_SESSION_TOKEN`
  or as `EIGHT_GATE_ACCOUNT_<NAME>_USERNAME` / `_PASSWORD` (the harness logs
  them in itself); (b) a writable account session to create the record; and
  (c) multi-user account scoping on the stack
  (`guardian/core/thread_access.py:101-108` enforces the owner check only
  when `principal.multi_user_enabled` is true).
* **Note.** The rubric states this gate "does not satisfy the human
  qualification" — agent-created accounts are acceptable here but not for
  `onboarding-and-people`.

## Inputs required from outside this repository

1. **A disposable Compose stack that is already up**, plus its `--env-file`.
   The harness reads the env file by key name: `DATABASE_URL` (or
   `POSTGRES_USER` / `POSTGRES_PASSWORD` / `POSTGRES_DB` and
   `CODEXIFY_POSTGRES_PORT`), `REDIS_URL` (or `CODEXIFY_REDIS_PORT`),
   `GUARDIAN_API_KEY`, `CODEXIFY_BACKEND_PORT`, `CODEXIFY_FRONTEND_PORT`.
2. **An authenticated account session** for the browser gate:
   `EIGHT_GATE_SESSION_TOKEN`.
3. **Two distinct authenticated accounts** for the scope-isolation gate:
   `EIGHT_GATE_ACCOUNT_<NAME>_SESSION` or
   `EIGHT_GATE_ACCOUNT_<NAME>_USERNAME` / `_PASSWORD`.
4. **A real provider export file** (OpenAI or Anthropic account export) for
   the natural-import gate: `--import-export-file`.
5. **A host-reachable `DATABASE_URL`** for the lock gate's concurrent claims.
6. **A Pi runtime, a provider credential, and a queued coding run** for the
   graceful-stop and lock gates, plus an operator SIGTERM to the coding
   worker while it holds the claim.
7. **A migrator that has run against this checkout's source** in the
   evaluated project, for the migration gate's coherence line.
8. **~13 minutes of elapsed time** (or an existing past-deadline attempt) for
   the deadline gate's second observation. No environment variable can
   shorten this — the budgets are constants.

Gates that are blocked on items 4, 6, and 8 are blocked on inputs this
repository cannot produce: a real provider export, a provider credential, and
wall-clock time. I did not simulate any of them.

## Commands

Against a running disposable stack:

```bash
/Volumes/Dev_SSD/Codexify-main/.venv/bin/python \
    scripts/ops/eight_gate_evidence.py \
    --env-file <stack>/.env \
    --compose-project <project> \
    --base-url http://127.0.0.1:8888 \
    --out <results>.json
```

The env file carries the account sessions and the export-file path:

```bash
# .env additions (values are read by name and never printed)
EIGHT_GATE_SESSION_TOKEN=<account session token>
EIGHT_GATE_ACCOUNT_ALPHA_SESSION=<account A session token>
EIGHT_GATE_ACCOUNT_BETA_SESSION=<account B session token>
```

Optional flags:

```bash
--frontend-url http://127.0.0.1:5173      # defaults to CODEXIFY_FRONTEND_PORT
--database-url postgresql://...           # defaults to DATABASE_URL in the env file
--redis-url redis://...                   # defaults to REDIS_URL in the env file
--import-export-file /path/to/export.zip  # the real provider export
--only queue/worker --only deadline       # run a subset of gates
--gate1-settle-seconds 45                 # how long gate 1 watches for the terminal state
```

The harness prints one line per gate and writes the same structure to the JSON:

```
[PASS] queue/worker  -- max_chat_queue_depth=3 final_chat_queue_depth=0 ...
[FAIL] deadline  -- the live revision [...] is not the evaluated checkout's single head ...
[UNPROVEN] import-recall  -- no natural import has been performed on this stack ...
passed 3/8; results written to results.json
```

The JSON carries a top-level `passed` / `total` count, a `verdicts` map, and
one object per gate with `gate`, `verdict`, `surface_read`, `observed`,
`reason`, and `missing_inputs`.

The harness's own self-checks need no stack:

```bash
/Volumes/Dev_SSD/Codexify-main/.venv/bin/python \
    scripts/ops/eight_gate_evidence_selfcheck.py
```

## Validation performed

* **Compilation.** `py_compile` on both harness modules.
* **Self-check suite.** 54/54 checks pass
  (`scripts/ops/eight_gate_evidence_selfcheck.py`). It covers env-file
  parsing, credential redaction (no value appears in `repr`, `str`, or the
  written JSON), the gate set and order, the queue and heartbeat key names,
  and the PASS/FAIL/UNPROVEN transition of every gate under known durable
  observations — including that an absent unique constraint is FAIL, that a
  DOM disagreeing with the durable state is FAIL, that a snapshot alone is
  UNPROVEN, and that a worker stopped while idle is UNPROVEN.
* **Live database reads.** Every SQL statement the harness issues was
  executed against a real PostgreSQL carrying the Codexify schema
  (`chat_completion_attempts`, `agent_runs`, `alembic_version`,
  `chat_messages`, `chat_threads`, `openai_account_import_jobs`), through both
  access paths: a direct psycopg connection and the `docker exec`/`psql`
  fallback. The `pg_constraint` reads return the real definitions —
  `ck_chat_attempt_recovery_snapshot_pair` and
  `UNIQUE (coding_worker_claim_id)`.
* **Live Redis reads.** `LLEN`, `GET`, and `TTL` against a running Redis,
  through both the direct client and the `redis-cli` container fallback.
* **Live browser.** A real headless Chromium (141.0.7390.37) launched and
  driven; the DOM text, author text, version, viewport, device pixel ratio,
  and user agent were all read.
* **Real refusal cases.** All three migrator refusal cases were exercised
  against the migrator's own comparison functions: each raised, and none
  applied a migration.
* **Live checkout head.** The checkout's single head was computed from its
  own migration source with Alembic's `ScriptDirectory`:
  `a7d4c9e2f1b3` across 135 revisions.
* **End-to-end harness run.** The full CLI was run against live scratch
  PostgreSQL and Redis. It produced a valid eight-gate JSON with
  `passed 0/8` and the expected UNPROVEN reasons — the migration gate read
  the live revision `['a7d4c9e2f1b3']` with `row_count = 1` from the live
  database and matched it against the checkout head.
* **Credential hygiene, verified on real output.** The harness was run with a
  distinctive session token and API key in the env file; neither string
  appears anywhere in the written JSON, and no credential-bearing key is
  emitted. Credentials are identified only by a SHA-256 fingerprint prefix.
* **Not validated.** No gate was exercised against the evaluated disposable
  stack, because none was up and the brief forbids starting one. The
  Private Preview project was not touched.

## Unknowns

* Whether a stopped coding worker releases its ownership columns to NULL on
  this revision. I found no code path that does so, but the graceful-stop
  PASS condition depends on it and I could not observe a stop.
* Whether the frontend's `data-testid="chat-message"` elements are the
  projection the rubric means, or whether it means a narrower element. I
  chose the message and author elements because they are the ones whose
  durable counterparts (`chat_messages`) the harness compares against. The
  rubric does not name a selector.
* Whether the natural-import recall surface should be the native history
  search or the imported-history inspection route. ADR-016 excludes imported
  records from native recall, so the harness reads both and records both; the
  rubric says "the recall result that returns it" without naming a route.
* Whether the lock gate's "the refusal recorded" means the store's refusal
  return value, a durable row, or an event. The harness records the store's
  refusal outcome and the post-attempt ownership row, and reports which it
  observed.
* The exact env-file key names the operator will use for the two account
  identities and the export file. The harness supports the names documented
  above; others would need a one-line change to the two name-matching
  helpers.
