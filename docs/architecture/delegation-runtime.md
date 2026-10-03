# Delegation Runtime Contract

Purpose: define the current delegation runtime seam and the minimum safe contract for turning a source thread into a delegated run, without pretending the full loop is already shipped.

Last updated: 2026-09-30

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
- docs/architecture/guardian-agent-delegation-recon.md
- guardian/routes/chat.py
- guardian/routes/agent_orchestration.py
- guardian/routes/codex.py
- guardian/codex/lineage.py
- guardian/agents/store.py
- guardian/agents/events.py
- guardian/command_bus/contracts.py
- guardian/workers/agent_worker.py
- guardian/queue/task_events.py

## Status Legend

- `covered`: current docs or code anchors already describe the surface.
- `thin`: the surface exists, but the contract is still narrow or partially inferred.
- `stale`: the source is present, but its language is older than the current runtime posture.
- `missing`: the surface is discussed, but the repo does not yet prove a full contract.

## What This Document Says

Delegation is not a binary "sent" or "completed" story.

For this runtime, delegation must be treated as:

1. route acceptance
2. queue or worker execution
3. task-event visibility
4. transcript, artifact, and summary persistence

If any one of those layers is missing, the operator should treat the run as degraded, partial, or incomplete rather than successful by default.

## Gap Matrix

| Topic | Current source | Status | Why it matters |
|---|---|---|---|
| Source thread and message capture | `flows.md`, `data-and-storage.md`, `account-export-restore-contract.md`, `guardian/codex/lineage.py` | covered | Delegation needs a durable source pointer before any handoff. |
| Queue acceptance and task-event visibility | `flows.md`, `data-and-storage.md`, `runtime-protocol-token-contract.md`, `guardian/routes/chat.py` | covered | Acceptance is real, but visibility can still degrade. |
| Run persistence and durable metadata | `docs/guardian/agent-orchestration.md`, `guardian/agents/store.py`, `guardian/agents/events.py` | thin | The storage seam exists, but the end-to-end delegation contract is still being tightened. |
| Clarification and escalation policy | `docs/guardian/agent-runtime-onboarding.md`, `guardian-agent-delegation-recon.md` | thin | The runtime needs a precise answer for when Guardian can answer, defer, or escalate. |
| Worktree isolation and mutating steps | `docs/guardian/agent-runtime-onboarding.md`, `guardian/workers/agent_worker.py` | thin | Mutating work needs a bounded filesystem boundary. |
| Completed packet/job result injection back into the originating thread | `guardian/workers/delegation_worker.py`, `guardian/agents/store.py` | bounded implementation and live proof | A completed normalized result returns once with validated source scope; failed/cancelled result UX remains outside this slice. |
| Lineage and provenance on durable artifacts | `account-export-restore-contract.md`, `routes/codex.py`, `guardian/codex/lineage.py` | covered | Delegated artifacts must remain source-addressable. |
| Runtime state vocabulary | `chat-runtime-contract.md`, `runtime-protocol-token-contract.md` | covered | Delegation must not invent new states ad hoc. |
| Support posture and release gating | `00-current-state.md`, `config-and-ops.md` | covered | Operators need the current supported path before treating delegation as trustworthy. |

## Current Runtime Reality

### Verified surfaces

- `docs/architecture/system-overview.md` and `docs/architecture/flows.md` already establish the current queue-backed, worker-driven runtime pattern.
- `docs/architecture/data-and-storage.md` already establishes Postgres as the source of truth for durable state, Redis as transport and visibility infrastructure, and the filesystem as a mutable workspace boundary.
- `docs/architecture/chat-runtime-contract.md` already defines the runtime vocabulary for provider state and request state.
- `docs/architecture/runtime-protocol-token-contract.md` already defines canonical runtime tokens for acceptance, task events, and machine-readable errors.
- `docs/architecture/account-export-restore-contract.md` already requires provenance and lineage to survive export and restore cycles.

### Bounded Codex App Server interface (branch-local)

- This branch adds an explicit `execution_interface=app_server` choice inside the existing `codex` execution channel. Omitting the choice continues to resolve `CodexExecutor` and `codex exec`.
- The App Server adapter starts one local process over stdio, performs the v2 initialization handshake, starts one native thread and one turn, consumes the matching terminal notification, then closes stdin and waits for process exit. It does not resume or reuse native sessions.
- The first adapter slice sets the native thread sandbox to `read-only`. It does not map broader Guardian permission profiles or expose write access.
- Native Codex thread, session, and turn IDs are stored as subordinate metadata. The Guardian result retains the Codexify request, delegation, task, thread, source-message, project, and executor identities.
- Provider evidence comes from the App Server thread response. A model is marked observed only when a per-turn reroute notification supplies it; otherwise a thread model is configured-only. The protocol exchange does not establish the funding or entitlement route, which remains unknown.
- Deterministic protocol tests pass, and a worker test proves that an explicit App Server result follows the existing Guardian terminal-summary path while retaining Codexify lineage.
- **Live proof, 2026-09-29:** one run through `DelegationService` and `delegation_worker` used `codex-cli 0.153.3`. The App Server completed initialization, thread start, and turn start, then returned a terminal failure: configured model `gpt-6-luna` is unsupported with the authenticated ChatGPT account. Guardian recorded a failed summary with the original Codexify source IDs; provider `openai` was observed, per-turn model identity was unavailable, and funding remained unknown. The App Server exited cleanly. The disposable fixture hash and Git status were unchanged. The run used an in-memory delegation service and captured task-event publisher, so it did not prove Postgres or Redis readback.
- **Durable live proof, 2026-09-29:** a separate isolated run used an account-listed `gpt-6-astra` configuration and completed one read-only App Server v2 turn through real Postgres, Redis enqueue/event transport, and `delegation_worker.run_once`. Fresh-process Postgres readback recovered the completed job, normalized exact-token summary, Codexify source lineage, and subordinate native thread/turn IDs; Redis held a terminal `delegation.completed` event. The App Server exited cleanly and the fixture remained byte-for-byte unchanged. The App Server reported provider `openai` and configured model `gpt-6-astra`, but did not expose actual per-turn model or funding identity. The source Codexify Thread received **no durable result message**, which was classified **NEXT_PROOF_NEEDED** at that time and is superseded by the bounded September 30 return proof below. See the [historical proof receipt](./2026-09-29-codex-app-server-durable-round-trip-proof.md).
- Native session reuse, Auto routing, and public support remain unproven. OpenAI currently labels the App Server command experimental and says it is unsupported for production workloads ([App Server documentation](https://developers.openai.com/codex/app-server/)). The implementation follows the documented [v2 thread-start](https://github.com/openai/codex/blob/main/codex-rs/app-server-protocol/schema/typescript/v2/ThreadStartParams.ts), [v2 turn-start](https://github.com/openai/codex/blob/main/codex-rs/app-server-protocol/schema/typescript/v2/TurnStartParams.ts), and [sandbox mode](https://github.com/openai/codex/blob/main/codex-rs/app-server-protocol/schema/typescript/v2/SandboxMode.ts) shapes.

### Completed packet/job result return (branch-local)

The September 29 [historical proof](./2026-09-29-codex-app-server-durable-round-trip-proof.md) established a missing source-thread result message. The September 30 [source-thread return proof](./2026-09-30-codex-app-server-source-thread-return-proof.md) closes that bounded blocker: one fresh read-only App Server v2 turn through Postgres, Redis, and the real delegation worker produced one durable assistant `coding_result` containing the exact token. Independent readback and delivery-only replay recovered the same message ID; thread counts were `1 -> 2 -> 2`. This is `PROVEN_LIVE_RUNTIME` for `codex-cli 0.153.3`, the isolated tested configuration, and completed results only. Provider `openai` was observed; configured model `gpt-6-astra`, actual per-turn model unknown, funding unknown. Native-session reuse, Auto routing, and public support remain unproven.

The worker first normalizes and durably persists the terminal job/summary, then calls `DelegationService.deliver_completed_result(delegation_id)`, then publishes `delegation.completed` with delivery metadata. `AgentStore` validates persisted packet/job/summary lineage against the source thread/message, project, and compatible account ownership. Missing, ambiguous, or contradictory lineage fails closed; progress and running results do not post transcript messages.

The key is `delegation:<delegation_id>:thread_result`. The existing job row is locked through message lookup/insertion and delivery-receipt persistence; the assistant `coding_result` and summary metadata commit together. A shared Guardian insertion/lookup primitive and the existing bounded/sanitized renderer are reused with the legacy intent lane. No legacy run/intent records, schema change, or second message store are involved. Identity metadata is explicitly whitelisted; raw protocol output, prompts, environment data, and worker paths are excluded.

Execution completion and transcript delivery remain distinct facts. `summary.metadata` carries `delivery_ok`, `delivery_status`, `delivery_reason`, `delivery_key`, `result_message_id`, and `visibility_status`. A failed delivery preserves the completed job and normalized evidence; `deliver_completed_result` retries only delivery. A replayed completed worker task retries delivery without resolving or calling an executor. Existing failed/cancelled/stale legacy behavior is unchanged. Job and terminal-summary persistence retain their existing transaction boundaries; delivery requires both records and does not reconstruct a missing accepted summary from external output. The September 29 receipt and release claims are unchanged.

### General inferred delegation posture

- `Inference:` Delegation should inherit the same split between acceptance, execution, and visibility that the chat runtime already uses.
- `Inference:` Delegated runs should be durable in Postgres and observable in event streams, but not reduced to event streams alone.
- `Inference:` Result injection should be idempotent and should refuse to publish an orphaned summary.
- `Inference:` A delegated artifact without `source_thread_id` and `source_message_id` should be treated as blocked or escalated, not silently accepted.

### Unverified delegation posture

- `Unverified:` A fully shipped end-to-end delegation loop is not proven by the current docs alone.
- `Unverified:` The exact canonical mapping between a delegated run, a task id, and a codex artifact id is not yet settled.
- `Unverified:` Automatic answer-on-behalf behavior is not a safe default until a tighter escalation policy exists.

## Nodes and Trust Boundaries

| Node | Responsibility | Trust boundary | What breaks first |
|---|---|---|---|
| UI or chat shell | Captures the user intent, shows status, and surfaces summaries | Browser or desktop client to backend auth boundary | Wrong source thread, stale context, or missing approval context |
| Guardian backend | Enforces policy, snapshots context, launches or records runs, and injects results | Backend process to worker/runtime boundary | Bad lineage, bad scope, or policy drift |
| Postgres | Durable truth for requests, runs, artifacts, lineage, and provenance | Backend to database boundary | Lost run history, duplicate publication, or orphaned artifacts |
| Redis | Transport for task events, queueing, locks, and liveness signals | Backend to queue boundary | Acceptance without visibility, stale locks, or stuck runs |
| External agent runtime | Performs the delegated work | Guardian to external process boundary | Prompt drift, partial execution, or missing artifacts |
| Repo filesystem or worktree | Mutable workspace for code or content changes | Runtime to filesystem boundary | Accidental mutation outside the approved scope |
| Optional provider runtime | Supplies model or tool execution if the agent needs it | Backend to provider egress boundary | Slow or failed execution, but not the authoritative record |

Minimal viable delegation network:

- Guardian backend
- Postgres
- Redis
- one worker or orchestration process
- an isolated filesystem/worktree when mutation is allowed
- the source thread and message rows that prove lineage

If any of those pieces is missing, delegation should degrade to a manual or blocked posture instead of pretending the run is complete.

## State Ownership

| State | Source of truth | Consistency target | Conflict policy | Identity binding |
|---|---|---|---|---|
| Delegation request | Postgres | Strong for writes, eventual for visibility | One canonical request per source turn; idempotent reruns only | `source_thread_id`, `source_message_id`, `source_turn_id`, requesting user id |
| Delegation run | Postgres plus event stream | Strong run row, eventual task/run stream | Single active run per request unless a rerun is explicitly created | `run_id`, `request_id`, adapter name, runtime target |
| Clarification state | Postgres | Strong for the stored answer, eventual for the UI | Auto-answer only when the stored snapshot resolves the question | `run_id`, clarification id, answer provenance |
| Artifacts | Postgres and lineage layer | Strong on write, eventual on display | Dedupe by lineage key; do not create duplicate summaries | `artifact_ref`, `source_thread_id`, `source_message_id` |
| Task events | Redis streams or compatible transport | Eventual and transient | Append only; never use as the sole truth surface | `task_id` or `run_id` |
| Workspace changes | Filesystem or worktree | Local and mutable | Isolate mutating work; require explicit approval for risky steps | `worktree_id`, adapter name, commit or diff hash |

Consistency target:

- strong for durable metadata writes
- eventual for event delivery and UI surfacing
- fail closed when lineage or provenance is ambiguous

Conflict policy:

- prefer a single active delegated run per source turn
- prefer idempotent replays over silent duplicate publication
- prefer human review over automatic merge when the change is mutating or ambiguous
- do not auto-merge or auto-overwrite user-authored thread content without an explicit contract

## Delegation Lifecycle

### 1) Plan

| Breaks first | Minimal viable network | First check | Recovery path |
|---|---|---|---|
| Missing source thread, missing source message, or identity mismatch | UI, Guardian, Postgres | Confirm `source_thread_id` and `source_message_id` resolve to live rows owned by the acting user or approved scope | Reject the request or rebind the snapshot; do not infer lineage |

### 2) Handoff

| Breaks first | Minimal viable network | First check | Recovery path |
|---|---|---|---|
| Queue unavailable, lock failure, or missing approval state | Guardian, Redis, Postgres | Confirm the handoff record exists and the queue or lock layer is healthy | Retry with backoff, restart the queue worker if needed, and preserve the snapshot |

### 3) Execute and Clarify

| Breaks first | Minimal viable network | First check | Recovery path |
|---|---|---|---|
| External agent drift, missing context, or an unresolved clarification | Worker, external agent runtime, worktree | Inspect run events and worker logs before trusting the agent result | Escalate, narrow scope, or rerun from the stored snapshot |

### 4) Return and Persist

| Breaks first | Minimal viable network | First check | Recovery path |
|---|---|---|---|
| Missing lineage, missing summary injection, or duplicate artifact publication | Postgres, codex lineage, originating thread | Verify that the result envelope carries `source_thread_id` and `source_message_id` and that the thread received a continuation summary | Refuse completion, keep the run open, repair the metadata, or rerun the result path |

## Lineage and Provenance Rules

Required fields for delegated summaries or artifacts:

| Field | Purpose |
|---|---|
| `source_thread_id` | Identifies the originating conversation or thread. |
| `source_message_id` | Identifies the source message that authorized or seeded the run. |
| `source_turn_id` | Identifies the logical turn or request boundary. |
| `artifact_ref` | Points to the durable artifact, if one was created. |
| `lineage_verified` | Indicates that the source chain was checked before publication. |
| `provenance` | Carries the adapter, runtime, and publication context. |

Rules:

- Every durable delegated artifact should carry `source_thread_id` and `source_message_id`.
- If the lineage is missing or cannot be proved, the result should downgrade to blocked or escalated instead of publishing an orphaned summary.
- The result summary must state what was delegated, what changed, what failed, and what still needs user action.
- Provenance must survive export and restore cycles; normalization must not erase the fact that the result came from a delegated source.
- "Jump to source" behavior should remain possible from any durable artifact.

## Failure Modes

| Failure mode | Symptom | Mitigation |
|---|---|---|
| Accepted but invisible | Route returns accepted, but task or run events do not appear | Treat as degraded visibility; inspect Redis, worker health, and the run store together |
| Event stream without persistence | The agent or worker logs show progress, but no durable run or artifact row exists | Repair the persistence path before trusting the result |
| Artifact without lineage | A summary or artifact exists but cannot point back to the source thread or message | Block publication or repair metadata; never silently publish an orphan |
| Duplicate rerun | The same delegated work is published twice | Use idempotency keys and lineage checks before injection |
| Scope drift | The external agent works outside the approved scope | Keep mutating worktree access isolated and require explicit escalation before widening scope |

## Open Decisions

- Should the canonical durable entity be a delegation request, an agent deployment or run, or a task?
- Should mutating delegation always use an isolated worktree, or only above a risk threshold?
- Should delegation runs standardize on `run_id == task_id`, or should they keep a mapping table?
- Should the canonical result be a codex entry, a generated document, an agent-run artifact, or a combination?
- Should clarification replies become normal thread messages, approval records, or both?

## Source Map

Current runtime truth:

- [00-current-state.md](./00-current-state.md)
- [system-overview.md](./system-overview.md)
- [flows.md](./flows.md)
- [data-and-storage.md](./data-and-storage.md)
- [config-and-ops.md](./config-and-ops.md)
- [modules-and-ownership.md](./modules-and-ownership.md)

Runtime vocabulary and contracts:

- [chat-runtime-contract.md](./chat-runtime-contract.md)
- [runtime-protocol-token-contract.md](./runtime-protocol-token-contract.md)

Lineage and provenance:

- [account-export-restore-contract.md](./account-export-restore-contract.md)
- `guardian/codex/lineage.py`
- `guardian/routes/codex.py`

Delegation planning context:

- [guardian-delegation-loop-contract.md](./guardian-delegation-loop-contract.md): Phase 1 docs-only contract for the future hybrid bridge from Guardian intake through durable intent, the existing coding-run/AgentRun backbone, source-thread continuation, and Command Center transcript mirroring. It does not prove current implementation.
- [guardian-agent-delegation-recon.md](./guardian-agent-delegation-recon.md)
- [docs/guardian/agent-orchestration.md](../guardian/agent-orchestration.md)
- [docs/guardian/agent-runtime-onboarding.md](../guardian/agent-runtime-onboarding.md)

Operational support:

- [SOLO_OPERATOR_AUTOMATION_RUNBOOK.md](../Ops/SOLO_OPERATOR_AUTOMATION_RUNBOOK.md)
- [SOLO_OPERATOR_FAILURE_SIGNATURES.md](../Ops/SOLO_OPERATOR_FAILURE_SIGNATURES.md)

## Legacy Quarantine

Treat these as historical or planning context unless they are explicitly revalidated against current code:

- `docs/Codexify/*`
- `docs/infra/*`
- `docs/guardian/agent-orchestration.md` when it conflicts with current runtime truth

## Maintenance Rule

If a change touches delegation planning, runtime tokens, queue visibility, lineage, provenance, or result injection, update this document in the same change set.

Run `make docs` after the edit and keep the source map aligned with the runtime contract.
