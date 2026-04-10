# Delegation Operator Manual

Purpose: give a solo operator a practical playbook for supervising delegated work in Codexify, with explicit attention to route acceptance, queue or worker execution, task-event visibility, and durable provenance.

Last updated: 2026-04-04

Source anchors:
- docs/architecture/00-current-state.md
- docs/architecture/system-overview.md
- docs/architecture/flows.md
- docs/architecture/data-and-storage.md
- docs/architecture/config-and-ops.md
- docs/architecture/modules-and-ownership.md
- docs/architecture/chat-runtime-contract.md
- docs/architecture/runtime-protocol-token-contract.md
- docs/architecture/account-export-restore-contract.md
- docs/architecture/delegation-runtime.md
- docs/architecture/guardian-agent-delegation-recon.md
- guardian/routes/chat.py
- guardian/routes/agent_orchestration.py
- guardian/routes/codex.py
- guardian/codex/lineage.py
- guardian/agents/store.py
- guardian/agents/events.py
- guardian/workers/agent_worker.py
- guardian/queue/task_events.py

## Read This First

Delegation is not complete when a request is accepted.

A delegation run is only complete when all four of these layers line up:

1. the route accepted the request
2. the worker or external runtime executed the work
3. the task or run events remained visible enough to explain what happened
4. the transcript, artifact, or summary was persisted with source lineage

If one layer is missing, do not call the run done.

## Five-Minute Preflight

| Check | Why it matters | Command or surface |
|---|---|---|
| Current release posture | Confirms delegation is being operated against the supported branch and profile | `docs/architecture/00-current-state.md` and `docs/architecture/config-and-ops.md` |
| Core runtime health | Separates backend health from queue or worker health | `GET /health`, `GET /health/chat`, `GET /api/health/llm` |
| Source lineage | Prevents orphaned summaries and artifacts | `guardian/codex/lineage.py`, `guardian/routes/codex.py` |
| Event visibility | Tells you whether the run is progressing or only accepted | `/api/agents/runs/{run_id}/events` or the compatible task stream |
| Durable persistence | Confirms that run state and provenance landed in Postgres | `guardian/agents/store.py` and the relevant run or artifact tables |

If any preflight check fails, fix the supporting layer before launching more delegation work.

## Supported Operator Model

| Layer | What must be true | If false |
|---|---|---|
| Acceptance | The runtime accepted the delegation request | Treat the run as not started |
| Execution | A worker or external agent actually processed the run | Inspect worker logs and the run store before retrying |
| Visibility | Events were emitted and remain readable | Treat the run as degraded, not failed by default |
| Persistence | The summary or artifact was written with lineage | Do not close the loop until provenance is repaired |

## Operator Questions For Each Major Flow

### 1) Planning the delegation

| Breaks first | Minimal viable network | First check | Recovery path |
|---|---|---|---|
| The source thread, source message, or acting identity is wrong | UI, Guardian, Postgres | Confirm the source thread and message are real and the acting user is allowed to delegate from them | Rebind to a valid source turn or reject the request |

### 2) Launching the run

| Breaks first | Minimal viable network | First check | Recovery path |
|---|---|---|---|
| Queue or lock failure, missing approval state, or stale profile data | Guardian, Redis, Postgres | Confirm the handoff record exists and that queue and lock surfaces are healthy | Retry with backoff, restart the worker if needed, and keep the snapshot durable |

### 3) Watching execution

| Breaks first | Minimal viable network | First check | Recovery path |
|---|---|---|---|
| External agent drift, missing context, or a clarification that cannot be resolved safely | Worker, external runtime, worktree | Inspect run events and worker logs before trusting the output | Escalate, narrow the scope, or rerun from the stored snapshot |

### 4) Returning results

| Breaks first | Minimal viable network | First check | Recovery path |
|---|---|---|---|
| Missing lineage, missing summary injection, or duplicate publication | Postgres, codex lineage, originating thread | Verify `source_thread_id` and `source_message_id` on the durable artifact and confirm that the source thread received a summary | Refuse completion, repair the metadata, or rerun the injection step |

## What Success Means

- `accepted` means the route accepted the request.
- `accepted_degraded` means the route accepted the request but lifecycle visibility is weaker than normal.
- `task.created`, `task.running`, `task.completed`, `task.failed`, and `task.cancelled` are visibility signals, not a substitute for persisted lineage.
- A delegated summary without `source_thread_id` and `source_message_id` is not a safe final result.

If the run produces an artifact but does not return a source-addressable summary, keep the run open and fix the provenance path.

## Recovery Playbooks

### Acceptance succeeded, but events are missing

1. Check queue and worker health.
2. Check the compatible run or task event stream.
3. Check the run store and worker logs together.
4. Treat the run as degraded until you can explain the missing visibility.

### The worker executed, but no summary appeared in the source thread

1. Inspect the result envelope for lineage fields.
2. Verify that the source thread and source message still exist.
3. Confirm that the result injection step was idempotent and not blocked by provenance validation.
4. Do not publish a second summary until you know why the first one failed.

### The artifact exists, but lineage is missing

1. Treat the artifact as blocked, not complete.
2. Repair the metadata or re-run the injection path.
3. If the artifact cannot be repaired, keep it internal only and mark the delegation run as escalated or failed.

### The source message cannot be found

1. Confirm whether the source message was deleted, imported, or never persisted.
2. If the message cannot be proved, reject the delegation result.
3. Rehydrate from export or restore only if provenance can be maintained.

### The worktree or filesystem scope drifted

1. Stop mutating work immediately.
2. Inspect the worktree id, adapter name, and approval scope.
3. Require a fresh approval boundary before resuming.

## Source Map

Current runtime truth:

- [00-current-state.md](./00-current-state.md)
- [system-overview.md](./system-overview.md)
- [flows.md](./flows.md)
- [data-and-storage.md](./data-and-storage.md)
- [config-and-ops.md](./config-and-ops.md)
- [modules-and-ownership.md](./modules-and-ownership.md)

Runtime contract and tokens:

- [chat-runtime-contract.md](./chat-runtime-contract.md)
- [runtime-protocol-token-contract.md](./runtime-protocol-token-contract.md)

Lineage and provenance:

- [account-export-restore-contract.md](./account-export-restore-contract.md)
- `guardian/codex/lineage.py`
- `guardian/routes/codex.py`

Delegation-specific context:

- [delegation-runtime.md](./delegation-runtime.md)
- [guardian-agent-delegation-recon.md](./guardian-agent-delegation-recon.md)
- [docs/guardian/agent-orchestration.md](../guardian/agent-orchestration.md)
- [docs/guardian/agent-runtime-onboarding.md](../guardian/agent-runtime-onboarding.md)

Operator support:

- [SOLO_OPERATOR_AUTOMATION_RUNBOOK.md](../Ops/SOLO_OPERATOR_AUTOMATION_RUNBOOK.md)
- [SOLO_OPERATOR_FAILURE_SIGNATURES.md](../Ops/SOLO_OPERATOR_FAILURE_SIGNATURES.md)

## Legacy Quarantine

Do not treat these as current runtime truth unless they are explicitly revalidated:

- `docs/Codexify/*`
- `docs/infra/*`
- older delegation planning notes that conflict with the current runtime docs

## Maintenance Rule

If you change delegation acceptance, run visibility, task-event semantics, lineage, provenance, or summary injection, update this manual in the same change set.

Run `make docs` after the change and verify that the source map still points at live docs.
