# Guardian Composer Coding Loop Live Proof

Proof date: 2026-08-03

Runtime prerequisite window: 2026-08-03 13:01:12-13:01:13 EDT

## Outcome

`next-proof-needed`

The live browser lane did not start because the supported `worker-coding`
container failed two independent adapter-readiness prerequisites before any
Coding Loop request was submitted:

1. Node and the Guardian Pi wrapper were present, but the mounted Pi SDK build
   artifact `codex_runner/vendor/pi-coding-agent/dist/index.js` was absent.
2. The worker's persistent home had no shared Pi auth store, and no API key was
   present for its effective default provider, Anthropic.

The worker container would therefore be unable to execute the configured
`pi_codex_runner` adapter. In accordance with the task failure policy, the
proof stopped at the prerequisite gate instead of creating a source message,
accepting a run that could not execute, or presenting a terminal failure as
end-to-end proof.

This result does not disprove the Composer, queue, worker, persistence, result
return, or durable WebUI readback code path. It means those live surfaces remain
unproven until the adapter package and credential/session prerequisites are
available inside the supported worker container.

## Repository identity

- Branch: `codex/wire-coding-loop-into-composer`
- Full `HEAD`: `97eb3f70fd8295d5071dd7977028da25e7e27b68`
- Base implementation commit: `b70c337b8e1fe02d808451e3bdd56a2531690e5a`
- Implementation ancestry: pass; `git merge-base --is-ancestor` exited `0`
- Worktree before proof: clean
- Execution lane: architecture-impact
- Task kind: proof
- Evidence posture reached: sanitized runtime-prerequisite evidence plus one
  focused automated authorization-boundary test; no live Coding Loop run

## Compose project and service posture

- Compose project: `codexify`
- Compose invocation: default project invocation, no explicit profile
- Compose inputs selected by the default invocation:
  `docker-compose.yml` and `docker-compose.override.yml`
- Exact service name for the coding worker: `worker-coding`
- Required path services named by the Compose graph:
  `db`, `migrator`, `backend`, `redis`, `worker-coding`, and `frontend`
- Exact services started by this proof: none
- One-off container used: `docker compose run --rm --no-deps ... worker-coding`
  for read-only readiness checks only; it did not launch `CodingWorker`
- Existing state observed at the gate:
  - `redis`: already running and healthy; `PING` returned `PONG`
  - `db`: already present but exited
  - `backend`: not running
  - `frontend`: not running
  - `worker-coding`: not running; no worker logs existed
  - coding queue depth: `0`

No Compose startup, migration, backend health, worker readiness, or frontend
health claim is made. The prerequisite gate closed before those steps.

## Sanitized environment prerequisites

No secret value was printed or written into this receipt.

| Prerequisite | Result | Evidence |
| --- | --- | --- |
| Supported local posture | pass | `.env` declares local-only mode, cloud providers disabled, and local LLM provider |
| Guardian API key in worker environment | present | sanitized in-container presence check |
| Node executable | present | sanitized in-container path check |
| Guardian Pi wrapper | present | sanitized in-container file check |
| Vendored Pi SDK build | **missing** | `codex_runner/vendor/pi-coding-agent/dist/index.js` absent in the mounted worker tree |
| Effective Pi provider | `anthropic` | no `PI_PROVIDER` override; wrapper default |
| Effective Pi model | `claude-sonnet-4-20250514` | no `PI_MODEL` override; wrapper default |
| Shared Pi auth store | **missing** | no `~/.pi/agent/auth.json` in the persistent worker home |
| Anthropic API key in worker environment | **missing** | sanitized in-container presence check |
| OpenAI API key in worker environment | missing | sanitized in-container presence check; not the effective provider |
| Google/Gemini API key in worker environment | missing | sanitized in-container presence check; not the effective provider |

There is also an operator-environment warning: the runbook-style
`set -a; source .env; set +a` command fails because the value assigned to
`LOCAL_PROVIDER_DISPLAY_NAME` contains an unescaped apostrophe. The key name
and quoting shape were inspected without printing the value. Docker Compose
can parse the env file independently, as demonstrated by the one-off container,
but the documented shell-loading ritual is not currently reproducible with
this local file.

## Intended bounded request

The request was prepared but not submitted:

```text
Inspect docs/architecture/00-current-state.md and return a concise summary. Do
not modify files.
```

Intended Composer policy:

- explicit mode: `Coding Loop`
- `allow_shell=false`
- `allow_network=false`
- `allow_write=false`
- no allowed paths
- no validation command
- no commit request
- no pull-request request

The current Composer implementation additionally sends `repo_root=null` and
`adapter_kind=pi_codex_runner`.

## Source and execution identities

No request was submitted, so no execution identities were created.

| Identity | Value |
| --- | --- |
| Source thread id | not created |
| Source message id | not created |
| Coding task id | not created |
| Attempt id | not created |
| Accepted run id | not created |
| Deployment id | not created |

This preserves the distinction between source-message identity and execution
attempt identity without inventing placeholder evidence.

## Milestone evidence

| Milestone | Result | Evidence and boundary |
| --- | --- | --- |
| Route acceptance | not run | No browser or HTTP submission occurred because the adapter-readiness gate closed. Acceptance remains unproven. |
| Queue enqueue | not run | The coding queue was observed at depth `0`; no task was created or enqueued. |
| Worker dequeue | not run | `worker-coding` was not running and had no logs. Dequeue/start remains unproven. |
| Adapter execution | blocked before attempt | The worker image has Node and the wrapper, but lacks the mounted Pi SDK build and effective-provider credentials/session. No model call was attempted. |
| Terminal result persistence | not run | No run or coding-result artifact exists from this proof. |
| Result return to source lineage | not run | No source thread/message or result was created. |
| WebUI terminal rendering | not run | The frontend was not started and Playwright was not opened. |
| Durable WebUI readback | not run | No terminal card existed to refresh or reconstruct. |

No milestone has been collapsed into a generic "worked" claim.

## HTTP and projection evidence

No live Coding Loop HTTP request was issued and there are therefore no runtime
HTTP status codes or response bodies to summarize.

The following authenticated projections were not called because no `run_id`
or `thread_id` existed:

- `GET /api/agents/runs/{run_id}`
- `GET /api/agents/runs/{run_id}/coding`
- `GET /api/chat/{thread_id}/coding-runs`

An existing focused automated test did verify the bounded authorization and
path-redaction behavior:

```text
.venv/bin/python -m pytest -q \
  guardian/tests/routes/test_agent_orchestration_events.py::test_coding_run_snapshot_is_scoped_and_path_bounded
```

Result: pass (`1 passed`). The test proves that a coding snapshot visible to
its owning user is absent for another user and that raw workspace prefixes are
not exposed. It is automated-test evidence, not a live cross-user request.

## Health and worker evidence

Exact service-status command used:

```text
docker compose ps --all db redis backend frontend worker-coding
```

Exact health command used:

```text
docker compose exec -T redis redis-cli ping
```

Result: `PONG` for the already-running Redis service. No backend health command
was run because the backend was not started after the prerequisite gate closed.

Exact queue command used:

```text
docker compose exec -T redis redis-cli LLEN codexify:queue:coding-execution
```

Result: `0`.

Exact worker-log command used:

```text
docker compose logs worker-coding --tail=100
```

Result: no output because no `worker-coding` service container was running.

## Browser verification result

Not run. Playwright's required `npx` prerequisite was present, but the WebUI
and worker path were not started after the adapter-readiness gate failed.
No thread was created, no Coding Loop mode was selected, no message was
submitted, and no accepted/active/terminal card was observed.

## Durable refresh/readback result

Not run. There was no terminal run to recover, so browser refresh and same-thread
reopening would not test the requested durable reconstruction seam.

## Warnings

- The default Compose project had pre-existing state: Redis was healthy while
  Postgres was exited. Those services were not started or stopped by this proof.
- The local `.env` file is accepted by Docker Compose but is not shell-sourceable
  through the runbook command because of the apostrophe described above.
- The adapter-readiness check used the currently available
  `codexify-backend-runtime:latest` image plus the Compose-mounted current
  `codex_runner` tree. No image build was attempted after the gate failed.

## Failures

- Required Pi SDK build artifact missing from the worker-mounted adapter tree.
- Shared Pi auth store missing from the persistent worker home.
- No API credential available for the effective Anthropic provider.

These are prerequisite failures. No runtime contradiction was observed because
the coding request was not accepted or executed.

## Exact commands run

Repository identity and scope:

```text
git merge-base --is-ancestor b70c337b8e1fe02d808451e3bdd56a2531690e5a HEAD
git status --short --branch
git branch --show-current
git rev-parse HEAD
git show --stat --oneline --decorate --no-renames \
  b70c337b8e1fe02d808451e3bdd56a2531690e5a
```

Compose discovery and state:

```text
docker compose config --services
docker compose ps --all
docker compose ps --all db redis backend frontend worker-coding
docker compose logs worker-coding --tail=100
docker compose exec -T redis redis-cli ping
docker compose exec -T redis redis-cli LLEN codexify:queue:coding-execution
```

Sanitized adapter prerequisite checks:

```text
docker compose run --rm --no-deps --entrypoint python worker-coding \
  -c '<sanitized executable, file, auth-store, provider, model, and key-presence checks>'
```

Environment-load diagnosis:

```text
set -a
source .env
set +a
awk '<sanitized key and quote-shape inspection>' .env
```

Focused authorization-boundary validation:

```text
.venv/bin/python -m pytest -q \
  guardian/tests/routes/test_agent_orchestration_events.py::test_coding_run_snapshot_is_scoped_and_path_bounded
```

No `docker compose up`, migration, backend health, authenticated readback,
browser, destructive reset, volume deletion, database mutation, repository
mutation, service stop, or service-down command was run.

## ADR impact

Classification: aligned with existing ADRs and contracts.

- ADR-020 Guardian Mediated Coding Agent Execution Contract
- Guardian Build Loop Doctrine
- Runtime Protocol Token Contract
- Existing coding-worker and Guardian result-return contracts

This proof changes no execution authority, queue semantics, cancellation
semantics, result lineage, adapter behavior, or release posture. Guardian
remains the sole execution authority, and acceptance remains distinct from
completion.

## Documentation follow-through

`docs/architecture/00-current-state.md` is unchanged because the outcome is
not `go`. No proof helper was created because existing Compose and test commands
were sufficient to reproduce the prerequisite failure.

## Validation results

| Command | Result | Proof boundary |
| --- | --- | --- |
| `.venv/bin/python -m pytest -q guardian/tests/routes/test_agent_orchestration_events.py::test_coding_run_snapshot_is_scoped_and_path_bounded` | pass (`1 passed`) | automated owner-scope and bounded-path projection behavior only |
| `.venv/bin/python scripts/validate_docs.py` | pass | documentation structure and required architecture links only |
| `git diff --check` | pass | tracked diff whitespace only before staging |
| required-section inspection for `Outcome`, `Route acceptance`, `Worker dequeue`, `Terminal result persistence`, `Durable WebUI readback`, and `What this does not prove` | pass | receipt completeness only |
| sanitized secret and unrestricted-host-path scan | pass | receipt content only |

These checks are not live Composer, queue, worker, adapter, persistence, or
browser proof.

## What this does not prove

This receipt does not prove:

- Guardian Composer route acceptance
- coding queue enqueue
- coding-worker dequeue or active state
- Pi adapter execution or model response
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

Before rerunning this proof:

1. Restore or build the project-approved vendored Pi SDK so
   `codex_runner/vendor/pi-coding-agent/dist/index.js` and its required
   dependencies exist in the tree mounted into `worker-coding`.
2. Authenticate Pi inside the persistent worker home, or supply the matching
   provider API key through the supported secret-handling path. Verify only
   presence/readiness; do not print the credential.
3. Re-run the sanitized one-off worker readiness check.
4. Make the local `.env` shell-sourceable or update the operator ritual so its
   documented environment-loading command succeeds without exposing secrets.
5. Only after those gates pass, start `db`, run `migrator`, start `backend`,
   `redis`, `worker-coding`, and `frontend`, then execute all eight live
   milestones and authenticated projections.

## Axis KB recommendation

Record one operational prerequisite for the Guardian Coding Loop: readiness
requires more than the `worker-coding` service and wrapper file. The
Compose-mounted worker tree must contain the built Pi SDK, and the persistent
worker home or supported secret path must supply credentials for the effective
Pi provider. A readiness check should distinguish `node_present`,
`wrapper_present`, `pi_sdk_present`, and `provider_auth_present` before any run
is accepted as a proof attempt. Also record that the current runbook's
`source .env` ritual can fail on otherwise Compose-valid values containing an
apostrophe.

## Secret-handling statement

No raw API key, session secret, provider token, Pi auth contents, environment
value, cookie, unrestricted host path, private prompt, or model payload is
included in this receipt.
