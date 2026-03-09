# Guardian Agent Delegation Recon

This document answers the planning question: "How should Guardian evolve into a safe semi-autonomous delegation interface for external coding agents, using the current Codexify runtime seams, without pretending that unfinished pieces already exist?"

Evidence labels used here:
- `Verified`: supported by the requested docs inspected for this task.
- `Verified (code anchor)`: supported only by inspected code outside the requested docs; exact repo paths are cited inline.
- `Inference`: higher-level conclusion that combines multiple sources.
- `Unverified`: missing files, absent routes, or runtime wiring not confirmed from inspected sources.

Requested-source gaps found during recon:
- `Unverified:` `dev-mode-extended-spec.md` was not present in this workspace.
- `Unverified:` `Thread-Artifact-Lineage.md` was not present in this workspace, although `README.md` still references it.

## 1. Executive Summary

`Verified:` Codexify already has several seams that matter for a future delegation loop: a queue-coupled chat completion path, a direct tools compatibility layer, a cron scheduler/executor path, Postgres-backed thread/message/project storage, Redis-backed task events, and documented SSE/websocket/event-feed surfaces that sit alongside the core chat loop rather than replacing it. (`docs/architecture/system-overview.md`, `docs/architecture/completion_pipeline.md`, `docs/architecture/modules-and-ownership.md`, `docs/architecture/data-and-storage.md`, `README.md`)

`Verified (code anchor):` The repo also contains adjacent delegation-specific scaffolding: codex lineage enforcement, agent deployment/run persistence, agent event fanout onto task-event streams, CLI adapters for Codex and Claude Code, confidence scoring helpers, and mutating-step worker primitives. (`guardian/routes/codex.py`, `guardian/codex/lineage.py`, `guardian/routes/agent_orchestration.py`, `guardian/agents/store.py`, `guardian/agents/events.py`, `guardian/agents/adapters/codex.py`, `guardian/agents/adapters/claudecode.py`, `guardian/agents/confidence.py`, `guardian/workers/agent_worker.py`)

`Inference:` These seams are sufficient to plan a grounded delegation architecture, but they do not yet prove a complete Guardian-driven runtime loop that plans in-thread, delegates to an external coding agent, handles clarifications, enforces user escalation gates, and returns results as a finished shipped path.

## 2. Current Runtime Reality (Doc-Verified + Code-Verified)

### Chat Completion Loop

- `Verified:` The current documented chat path is `POST /api/chat/{thread_id}/complete` -> Redis enqueue -> worker execution -> context/prompt assembly -> provider call -> assistant-message persistence -> task-event emission. (`docs/architecture/system-overview.md`, `docs/architecture/completion_pipeline.md`, `docs/architecture/flows.md`)
- `Verified:` The completion path is queue-coupled and worker-driven, with per-thread turn gating and Redis task-event transport called out as part of the implemented runtime rather than as speculation. (`docs/architecture/system-overview.md`, `docs/architecture/completion_pipeline.md`, `docs/architecture/data-and-storage.md`)
- `Verified (code anchor):` The route normalizes `turn_id`, resolves depth gating, acquires a Redis turn lock, enqueues `ChatCompletionTask`, and publishes `task.created`. (`guardian/routes/chat.py`)
- `Verified (code anchor):` Completion assembly is centralized in `guardian/core/chat_completion_service.py`, which loads thread state, calls `ContextBroker`, builds the Guardian system prompt, appends thread document context when present, and returns the final provider payload used by the chat worker. (`guardian/core/chat_completion_service.py`, `guardian/workers/chat_worker.py`)

### Tools Path

- `Verified:` The requested runtime docs describe a direct tools execution path that is immediate and process-local, separate from durable cron execution. (`docs/architecture/system-overview.md`, `docs/architecture/modules-and-ownership.md`, `docs/architecture/flows.md`, `docs/architecture/roadmap-signals.md`)
- `Verified:` The current planning docs also explicitly warn that some execution surfaces remain process-local or non-durable. (`docs/architecture/roadmap-signals.md`)
- `Verified (code anchor):` The `/tools` and `/api/tools` routes now act as a compatibility layer over the command-bus manifest/invoke system while still persisting legacy snapshots in the in-memory `JOBS` map for older callers. (`guardian/routes/tools.py`, `guardian/routes/command_bus.py`)
- `Verified (code anchor):` The command bus already models actor identity, delegated identity, idempotency, approval mode, and run-event streaming for command execution. (`guardian/command_bus/contracts.py`, `guardian/routes/command_bus.py`)

### Cron Path

- `Verified:` The requested docs describe a cron path in which job definitions live in Postgres, scheduler ticks create durable `cron_runs`, Redis carries execution payloads, and a cron worker records terminal status. (`docs/architecture/system-overview.md`, `docs/architecture/data-and-storage.md`, `docs/architecture/flows.md`)
- `Verified (code anchor):` `guardian/routes/cron.py` validates schedules and webhook targets, `guardian/cron/scheduler.py` inserts `cron_runs` and enqueues `cron.execute`, and `guardian/workers/cron_worker.py` advances runs from `queued` to `running` to `succeeded` or `failed`. (`guardian/routes/cron.py`, `guardian/cron/scheduler.py`, `guardian/workers/cron_worker.py`)
- `Unverified:` Continuous cron execution as an always-on default Compose runtime was not confirmed from inspected runtime wiring; `docker-compose.yml` showed chat, voice, warmup, and embedding workers, but not dedicated cron scheduler/worker services. (`docker-compose.yml`, `docs/architecture/system-overview.md`)

### Task Events, Event Feeds, SSE, and WebSocket Surfaces

- `Verified:` Codexify exposes multiple transport surfaces: durable outbox SSE at `/api/events`, Redis task-event SSE at `/api/tasks/{task_id}/events`, sync SSE, and websocket RPC. The requested docs present these as separate subsystems rather than a single universal communication mechanism. (`README.md`, `docs/architecture/system-overview.md`, `docs/architecture/modules-and-ownership.md`, `docs/architecture/data-and-storage.md`)
- `Verified (code anchor):` `/api/events` polls the outbox, `/api/tasks/{task_id}/events` streams Redis task events until terminal state, `/api/sync/subscribe` streams the in-process sync bus, and `/api/ws/rpc` provides authenticated RPC with audit logging. (`guardian/guardian_api.py`, `guardian/sync/api.py`, `guardian/routes/websocket.py`)
- `Verified (code anchor):` Agent run events are already fanned out onto the existing task-event stream keyed by `run_id`. (`guardian/agents/events.py`, `guardian/routes/agent_orchestration.py`)
- `Inference:` That event fanout creates a compatibility seam between future delegation runs and the existing `/api/tasks/{task_id}/events` subscriber model, but it does not by itself prove a complete canonical runtime contract.

### Identity, Persona, and IDDB Boundaries Relevant to Delegation

- `Verified:` IDDB policy treats personas as masks that borrow identity rather than owning it, makes deep identity opt-in, and states that durable sensitive-trait inference is not default behavior. (`docs/iddb_policy_v1.md`)
- `Verified:` The requested identity docs also state that diary threads can be excluded from identity modeling and that excluded content should remain in the diary layer rather than becoming durable identity state. (`docs/iddb_policy_v1.md`)
- `Verified (code anchor):` Project-level `identity_depth` is constrained to `light|deep`, thread rows include `is_diary`, `diary_mode`, `exclude_from_identity`, and `modeling_excluded`, and `thread_blocks_identity_modeling()` plus `can_run_deep_identity_modeling()` gate identity behavior in code. (`guardian/db/models.py`, `guardian/cognition/identity_policy.py`, `guardian/core/pgdb.py`, `guardian/routes/chat.py`)
- `Verified (code anchor):` Current routes expose IDDB settings (`memory_mode`, `diary_requires_unlock`, `allow_sensitive_modeling`) and imprint/persona/system-prompt status, but they do not by themselves define a delegated-agent access policy. (`guardian/routes/iddb.py`, `guardian/routes/imprint.py`)

## 3. Assumptions to Reject or Downgrade

- `Inference:` "Codexify uses SSE and queued tasks" is too broad. The completion path is queue-coupled, but the backend also exposes a durable outbox SSE feed, Redis task-event SSE, sync SSE, websocket RPC, direct tool execution, cron job execution, and command-bus invocation as distinct mechanisms. (`docs/architecture/system-overview.md`, `docs/architecture/modules-and-ownership.md`, `README.md`, `guardian/guardian_api.py`, `guardian/routes/websocket.py`, `guardian/sync/api.py`)
- `Unverified:` "Guardian can already delegate to Codex/Claude Code and receive results through the same mechanism" is not an established runtime fact. `Verified (code anchor):` the repo has agent deployment/run routes, CLI adapters, confidence helpers, event publishers, and worker primitives. `Inference:` that is scaffolding, not proof of a finished in-thread delegation loop. (`guardian/routes/agent_orchestration.py`, `guardian/agents/adapters/codex.py`, `guardian/agents/adapters/claudecode.py`, `guardian/agents/events.py`, `guardian/workers/agent_worker.py`, `docs/guardian/agent-orchestration.md`, `docs/guardian/agent-runtime-onboarding.md`, `docker-compose.yml`)
 - `Verified (code anchor):` There is a delegated-agent confidence helper with `0.85`, `0.70`, and `0.55` cutoffs in `guardian/agents/confidence.py`. `Inference:` These values should be treated as implementation-local scaffolding defaults for delegated-agent handling, not as canonical project-wide user-escalation governance, because none of the requested docs establish a repo-wide threshold. (`guardian/agents/confidence.py`)
 - `Verified (code anchor):` Flow routes exist and currently keep flows and run indexes in process memory. `Inference:` That is not durable enough to serve as the canonical delegation backbone; at most it is an experimental orchestration surface unless persistence, approval state, and recovery semantics are added. `Unverified:` canonical production use of flow builder for Guardian delegation. (`guardian/routes/flows.py`)
- `Inference:` Agent-orchestration APIs and CLI adapters should be treated as adjacent seams, not proof of a completed chat-driven delegation system, because current docs describe plans/deployments/runs and event streaming but also explicitly note that real delegated execution may still be scaffolded rather than fully wired. (`docs/guardian/agent-orchestration.md`, `docs/guardian/agent-runtime-onboarding.md`, `guardian/routes/agent_orchestration.py`)
- `Unverified:` Claims that depend on `dev-mode-extended-spec.md` or `Thread-Artifact-Lineage.md` cannot be treated as established in this recon because those requested files were absent from the workspace.

## 4. Candidate Delegation Architecture

`Inference:` The minimal viable delegation network should treat these as distinct nodes and trust boundaries:
- User/UI node: thread view, approvals, continuation summaries, run status.
- Guardian backend node: policy enforcement, context packing, thread mutations, result injection.
- Redis/Postgres coordination node: transient transport in Redis, durable state and lineage in Postgres.
- External coding agent process node: Codex or Claude Code CLI execution in an isolated cwd/worktree.
- Repo filesystem node: mutable workspace or isolated worktree subject to approval and lineage rules.

`Inference:` Threat model for the first safe version should assume an honest-but-buggy external agent, ambiguous user intent, stale context snapshots, and potentially over-scoped local process access. The design should also tolerate queue loss, retries, and partial worker failure without losing authoritative run state.

### Guardian Planning In-Thread

- `Reuse current seams`
- `Verified:` Reuse the existing thread/message/project/persona/imprint/system-prompt context model as the planning surface inside Guardian. (`docs/architecture/completion_pipeline.md`, `docs/iddb_policy_v1.md`)
- `Verified (code anchor):` Reuse `build_guardian_system_prompt()`, thread lookup, depth gating, and project identity-depth checks so delegated planning starts from the same context boundaries as normal chat. (`guardian/core/chat_completion_service.py`, `guardian/routes/chat.py`, `guardian/cognition/system_prompt_builder.py`)
- `New backend work required`
- `Inference:` Add a delegation planner that emits an explicit delegation intent object rather than directly calling an external agent from the chat path.
- `Inference:` Persist a delegation snapshot with source `thread_id`, source `message_id`, source `turn_id`, requested scope, and resolved context pack hash before any handoff.
- `Open design choices`
- `Inference:` Decide whether planning lives in the chat worker path, in a dedicated delegation route, or behind `/api/agents/plans` as the canonical entrypoint.

### Delegation Handoff to the External Coding Agent

- `Reuse current seams`
- `Verified (code anchor):` Reuse Redis-style task/event transport and the existing agent deployment/run store so delegated work has durable run identity and event streams from day one. (`guardian/agents/store.py`, `guardian/agents/events.py`, `guardian/routes/agent_orchestration.py`)
- `Verified (code anchor):` Reuse the existing CLI adapter envelope contract for Codex and Claude Code instead of inventing a new free-form result channel. (`guardian/agents/adapters/base.py`, `guardian/agents/adapters/codex.py`, `guardian/agents/adapters/claudecode.py`)
- `Verified (code anchor):` Reuse deterministic worktree creation and preserved-worktree-on-escalation semantics already assumed by the mutating-step worker primitives. (`guardian/workers/agent_worker.py`)
- `New backend work required`
- `Inference:` Add a durable delegation-request queue/worker that turns a stored delegation snapshot into an external-agent invocation, instead of invoking CLIs inline from a request path.
- `Inference:` Separate read-only delegation from mutating delegation so only the mutating path requires isolated worktree management and validation boundaries.
- `Open design choices`
- `Inference:` Decide whether delegation runs should standardize on `run_id == task_id` or keep a mapping table; current agent events already publish to task-event streams keyed by `run_id`, which makes either approach viable. (`guardian/agents/events.py`)

### Agent-to-Guardian Clarification Loop

- `Reuse current seams`
- `Verified (code anchor):` Reuse existing per-run event streams and thread run listing so clarifications can be persisted as run-level events before they become user-visible thread messages. (`guardian/routes/agent_orchestration.py`, `guardian/agents/events.py`)
- `Verified (code anchor):` Reuse command-bus actor identity and delegated-by fields so clarifying sub-actions can remain attributable to Guardian on behalf of a user. (`guardian/command_bus/contracts.py`)
- `New backend work required`
- `Inference:` Add explicit clarification event types such as `clarification.requested`, `clarification.answered`, and `clarification.timeout`.
- `Inference:` Add a Guardian-side policy that can answer low-risk clarification questions automatically only when the answer is already grounded in the stored thread snapshot and approved context pack.
- `Open design choices`
- `Inference:` Decide whether unresolved clarifications become regular thread messages, a separate approval queue, or both, and keep that decision distinct from broader persona/profile scope expansion.

### Escalation-to-User Gate

- `Reuse current seams`
- `Verified (code anchor):` Reuse existing tool approval and policy concepts rather than relying on prompt-only obedience: tools routes already import approval token handling, policy evaluation, idempotency helpers, and manifest-derived command contracts. (`guardian/routes/tools.py`, `guardian/routes/command_bus.py`)
- `Verified (code anchor):` Reuse the current identity-depth and diary/exclusion gates as the default ceiling for what context can be passed into a delegated run. (`guardian/cognition/identity_policy.py`, `guardian/routes/iddb.py`, `guardian/routes/chat.py`)
- `New backend work required`
- `Inference:` Add a delegation-specific escalation state machine that can block on user approval before filesystem mutation, secret access, deep identity access, or answer-on-behalf behavior.
- `Inference:` Persist escalation records in the same durable run store as attempts, confidence reports, and artifacts so postmortems are reconstructable.
- `Open design choices`
- `Inference:` Decide whether escalation approval should unlock only one action, one run, or an entire deployment trust state.

### Result Return Path

- `Reuse current seams`
- `Verified (code anchor):` Reuse codex lineage enforcement so every durable delegated artifact can point back to a source thread and source message, and so "jump to source" remains possible. (`guardian/routes/codex.py`, `guardian/codex/lineage.py`)
- `Verified (code anchor):` Reuse agent run artifacts/confidence/escalation tables as durable run metadata, with thread-level visibility via `/api/chat/{thread_id}/agent-runs`. (`guardian/agents/store.py`, `guardian/routes/agent_orchestration.py`)
- `New backend work required`
- `Inference:` Add a canonical result-injection step that writes a summarized Guardian continuation back into the originating thread only after provenance, lineage, and approval checks pass.
- `Inference:` Make the result path idempotent so reruns do not create duplicate thread messages or duplicate codex artifacts.
- `Open design choices`
- `Inference:` Decide whether the first durable artifact should be a codex entry, a generated document, an agent-run artifact row, or a combination of those.

### Notification and Continuation Summary Path

- `Reuse current seams`
- `Verified:` Existing runtime already has outbox SSE and task-event SSE surfaces suitable for live progress updates. (`README.md`, `docs/architecture/data-and-storage.md`)
- `Verified (code anchor):` Existing agent events already stream over SSE and can be replayed from durable storage when a DB is configured. (`guardian/agents/events.py`, `guardian/routes/agent_orchestration.py`)
- `New backend work required`
- `Inference:` Add a canonical Guardian-authored continuation summary that explains what was delegated, what completed, what was blocked, and what still needs user action.
- `Inference:` Add notification dedupe and resume semantics so the UI does not treat task events, run events, and outbox events as separate truths.
- `Open design choices`
- `Inference:` Decide whether continuation summaries should arrive through `/api/events`, `/api/tasks/{task_id}/events`, `/api/agents/runs/{run_id}/events`, or one canonical fanout path that mirrors into the others.

## 5. Delegation Loop Contract Proposal

`Inference:` A safe semi-autonomous loop needs explicit contracts instead of implicit prompt conventions. The following pseudostructures stay within current seams while leaving room for later hardening.

### `DelegationRequest`

```text
DelegationRequest {
  request_id: string
  source_thread_id: int
  source_message_id: int
  source_turn_id: string
  project_id: int | null
  requested_by_user_id: string
  guardian_actor_id: string
  active_profile_id: string | null
  active_persona_id: int | null
  imprint_scope: "light" | "deep"
  depth_mode: "shallow" | "normal" | "deep" | "diagnostic"
  delegation_mode: "read_only" | "mutating"
  target_agent: "codex" | "claudecode" | string
  cwd_scope: string
  worktree_mode: "none" | "isolated_worktree"
  allowed_actions: string[]
  denied_actions: string[]
  allowed_context_refs: ContextRef[]
  iddb_scope: {
    allow_light_identity: bool
    allow_deep_identity: bool
    allow_personal_facts: bool
    allow_diary_threads: bool
    allow_sensitive_modeling: bool
  }
  approval_policy: {
    approval_token: string | null
    policy_hash: string
    requires_human_before_mutation: bool
  }
  provenance: {
    context_pack_hash: string
    system_prompt_hash: string
    request_idempotency_key: string
  }
}
```

`Inference:` `allowed_context_refs` should carry references to already-approved thread messages, thread-linked documents, codex entries, and system docs, not an unrestricted read-anything capability.

### `DelegationClarification`

```text
DelegationClarification {
  run_id: string
  step_index: int | null
  question_id: string
  question: string
  reason_code: string
  can_guardian_answer_without_user: bool
  required_scope_change: {
    needs_more_context: bool
    needs_more_permissions: bool
    needs_iddb_confirmation: bool
  }
  status: "pending" | "answered" | "escalated" | "expired"
  answer: string | null
}
```

`Inference:` Guardian should only auto-answer when the clarification is fully resolvable from the stored request snapshot plus allowed context refs. Otherwise it should escalate or request approval.

### `DelegationResultEnvelope`

```text
DelegationResultEnvelope {
  run_id: string
  status: "succeeded" | "failed" | "escalated" | "blocked"
  summary: string
  confidence: {
    score: float
    band: "high" | "medium" | "low"
    rationale: string[]
  }
  artifacts: [{
    artifact_type: string
    artifact_ref: string
    source_thread_id: int
    source_message_id: int
    source_run_id: string
    source_step_index: int | null
    worktree_id: string | null
    lineage_verified: bool
    blocked_reason: string | null
  }]
  provenance: {
    adapter_name: string
    adapter_schema_valid: bool
    execution_started_at: timestamp
    execution_finished_at: timestamp
    request_idempotency_key: string
    context_pack_hash: string
    evidence_refs: string[]
  }
  guardian_continuation: {
    thread_message_ready: bool
    user_escalation_required: bool
    continuation_summary: string
  }
}
```

`Inference:` Every durable artifact should carry `source_thread_id` and `source_message_id`, or the envelope should downgrade to `blocked`/`escalated` rather than creating an orphaned result.

### IDDB Access Policy Inside the Contract

- `Verified:` Personas borrow identity and deep identity is opt-in. (`docs/iddb_policy_v1.md`)
- `Inference:` Default delegation requests should allow light interaction-style context only, deny deep identity by default, and deny diary/excluded threads unless the user explicitly broadens scope for that run.
- `Inference:` `allow_personal_facts` should default to false even when the current deployment stores personal facts, because durable identity facts are qualitatively more sensitive than recent thread context.

## 6. Confidence and Escalation Policy Recommendation

`Verified (code anchor):` The repo already contains delegated-agent confidence bands at `0.85`, `0.70`, and `0.55`. (`guardian/agents/confidence.py`)

`Inference:` Reuse those bands as an initial policy starting point for delegation, but treat them as implementation scaffolding defaults rather than canonical governance until Codexify explicitly ratifies a user-facing escalation policy.

### Recommended Confidence Bands

- `Inference:` `>= 0.85` -> autonomous continuation is allowed only inside pre-approved scope, with bounded cwd/worktree, no sensitive identity access, and no destructive actions.
- `Inference:` `0.70-0.84` -> supervised continuation is allowed, but the run must remain audit-visible and should surface a continuation summary before any answer-on-behalf or artifact publication.
- `Inference:` `0.55-0.69` -> Guardian should escalate before any mutation, answer-on-behalf, or durable artifact publication.
- `Inference:` `< 0.55` -> block autonomous continuation and require explicit user decision.

### Always-Escalate Categories Regardless of Score

- `Inference:` Destructive repo actions: branch deletion, hard resets, history rewrites, bulk file deletion, irreversible migrations.
- `Inference:` Secret or env access: reading `.env`, auth tokens, API keys, private certificates, credential stores.
- `Inference:` Auth or permission changes: changing ACLs, approval policy, user identity mapping, exposure mode, auth mode, or session/JWT handling.
- `Inference:` Network egress beyond explicit allowlist: any outbound call not already approved by current egress/tool policy.
- `Inference:` Actions outside approved cwd/worktree scope.
- `Inference:` Answering on the user's behalf when the request remains materially ambiguous or high-consequence.

### IDDB Access Requiring Explicit User Confirmation

- `Verified:` Deep identity is opt-in, personas borrow identity, and durable sensitive-trait inference is not default. (`docs/iddb_policy_v1.md`)
- `Inference:` Any delegated access to deep identity, diary threads, modeling-excluded threads, personal facts, or any context that could reveal or infer sensitive durable traits should require explicit user confirmation for that run.
- `Inference:` Cross-persona retrieval should require explicit approval when it would reveal diary-layer or deep-identity material that was not already active in the current thread.

### Evidence Guardian Must Gather Before Answering on the User's Behalf

- `Inference:` Confirm the exact originating thread/message/turn and preserve that lineage in the run record.
- `Inference:` Materialize the bounded context pack and record its hash before delegation.
- `Inference:` Confirm the exact repo/worktree scope and whether the request is read-only or mutating.
- `Inference:` Gather concrete execution evidence: adapter envelope, failing tests or passing tests, diff summary, artifact refs, escalation history, and any unresolved clarifications.
- `Inference:` Refuse answer-on-behalf when the result envelope lacks lineage, provenance, or enough evidence to explain what changed and why.

## 7. Risks, Failure Modes, and Safety Constraints

- `Wrong-context retrieval`
- `Verified:` Context assembly can draw from messages, semantic search, memory, graph, sensors, and optional federated context depending on depth. (`docs/architecture/completion_pipeline.md`)
- `Inference:` Delegation must use an explicit bounded context pack with stable references and hashes; do not let the external agent roam across all retrievers implicitly.

- `Stale thread state`
- `Verified (code anchor):` Chat completions already use turn locks and turn IDs to avoid overlapping assistant turns. (`guardian/routes/chat.py`, `guardian/workers/chat_worker.py`)
- `Inference:` Delegation needs its own snapshot/version guard so long-running external work does not write back against a stale thread without detecting drift.

- `Over-delegation`
- `Verified (code anchor):` Agent routes can create deployments and runs, but they do not yet establish a chat-scoped permission contract. (`guardian/routes/agent_orchestration.py`)
- `Inference:` Every delegation request should carry an allowed-action manifest and default to read-only until the user or policy explicitly unlocks mutation.

- `Silent identity leakage`
- `Verified:` IDDB policy makes deep identity opt-in and disallows default durable sensitive-trait inference. (`docs/iddb_policy_v1.md`)
- `Verified (code anchor):` Thread and project identity gates already exist. (`guardian/db/models.py`, `guardian/cognition/identity_policy.py`, `guardian/routes/iddb.py`)
- `Inference:` Default delegation should exclude diary threads, modeling-excluded threads, and personal facts unless the user grants that scope explicitly.

- `Queue/job durability mismatch`
- `Verified:` Redis queue/event data is operationally critical but non-durable by default in Compose. (`docs/architecture/data-and-storage.md`, `docker-compose.yml`)
- `Inference:` Postgres must remain the source of truth for delegation requests, run state, escalations, clarifications, and artifact lineage; Redis should be transport, not sole record.

- `Direct-tools vs durable-jobs mismatch`
- `Verified:` Direct tools are process-local while cron runs are durable. (`docs/architecture/system-overview.md`, `docs/architecture/roadmap-signals.md`)
- `Verified (code anchor):` Legacy tools snapshots still live in `JOBS`, while cron runs and agent runs have durable stores. (`guardian/routes/tools.py`, `guardian/routes/cron.py`, `guardian/agents/store.py`)
- `Inference:` Anything more consequential than immediate local inspection should go through durable delegation runs, not the in-memory tool job lane.

- `Notification ambiguity`
- `Verified:` The runtime already has multiple event surfaces. (`README.md`, `docs/architecture/system-overview.md`)
- `Inference:` Delegation needs one canonical continuation-summary sink and one canonical live-progress stream, even if events are mirrored elsewhere for compatibility.

- `Unverified flow-builder assumptions`
- `Verified (code anchor):` Flow routes exist but are currently backed by process memory. (`guardian/routes/flows.py`)
- `Inference:` Flow builder can be an optional future orchestration surface, but Phase 1 delegation should not depend on it as the primary durability or approval boundary.

## 8. Phased Delivery Plan

### Phase 0: Recon + Contract

- `Scope`
- Planning-only: finalize this recon, the delegation contract, approval semantics, and provenance rules before runtime changes.
- `Likely future files/subsystems`
- `docs/architecture/guardian-agent-delegation-recon.md`, `docs/guardian/agent-orchestration.md`, `docs/guardian/agent-runtime-onboarding.md`
- `Blast radius`
- Low; documentation and contract alignment only.
- `Dependency risks`
- Missing file references in the current docs map, unclear runtime enablement for cron/agent worker, and stale docs that imply more delegation maturity than the code currently proves.
- `Test strategy for later implementation`
- No runtime tests in Phase 0; require contract examples and route/state diagrams to be stable before coding starts.

### Phase 1: Manual Delegation Wrapper

- `Scope`
- Add a manual, supervised delegation wrapper that lets Guardian create a durable delegation request and start a run intentionally, without automatic clarification answering or automatic answer-on-behalf.
- `Likely future files/subsystems`
- `guardian/routes/agent_orchestration.py`, `guardian/agents/store.py`, `guardian/agents/events.py`, `guardian/routes/chat.py`, frontend thread run-status surfaces
- `Blast radius`
- Medium; additive around agent-run state and thread visibility.
- `Dependency risks`
- Current runtime wiring does not prove an always-on agent worker path, and approval semantics are still split across tools/command-bus concepts.
- `Test strategy for later implementation`
- Route tests for request creation and per-thread run listing, store tests for durable run state, SSE tests for run-event streaming, and adapter stub tests using deterministic fake envelopes.

### Phase 2: Clarification Loop + Escalation Gate

- `Scope`
- Add clarification requests, explicit approval gating, confidence-band enforcement, and guarded writeback into the originating thread.
- `Likely future files/subsystems`
- `guardian/workers/agent_worker.py`, `guardian/agents/confidence.py`, `guardian/agents/store.py`, `guardian/routes/tools.py`, `guardian/routes/command_bus.py`, possible new delegation-state models
- `Blast radius`
- Medium-high; this phase crosses execution policy, identity policy, event streaming, and thread mutation rules.
- `Dependency risks`
- Race conditions with thread state, ambiguous approval semantics, and accidental leakage from diary/deep identity contexts.
- `Test strategy for later implementation`
- State-machine unit tests, confidence-policy tests, escalation tests, stale-thread detection tests, and replay/idempotency tests around repeated clarification or retry events.

### Phase 3: Notifications, Artifact Lineage, and Automation Hooks

- `Scope`
- Add canonical continuation summaries, durable artifact publication with lineage, and optional cron/automation hooks for follow-up notifications or deferred continuation.
- `Likely future files/subsystems`
- `guardian/routes/codex.py`, `guardian/codex/lineage.py`, `guardian/guardian_api.py`, `guardian/routes/cron.py`, `guardian/cron/scheduler.py`, UI event consumers
- `Blast radius`
- Medium; mostly result publication, notification, and automation surfaces.
- `Dependency risks`
- Duplicate notifications across event feeds, missing lineage on delegated artifacts, and automation triggering before a run has passed approval and provenance checks.
- `Test strategy for later implementation`
- Lineage enforcement tests, continuation-summary idempotency tests, event-resume tests across SSE surfaces, and integration tests for cron/manual follow-up hooks.

## 9. Open Questions

- `[Must decide before implementation]` Should the canonical durable entity be a `delegation request`, an `agent deployment/run`, or a `task`, and how should those IDs map to each other?
- `[Must decide before implementation]` Should every mutating delegation run execute in an isolated worktree, or only runs above a certain risk threshold?
- `[Must decide before implementation]` What is the minimal allowed-action set for Phase 1, and which actions are explicitly out of scope until later phases?
- `[Must decide before implementation]` What user interaction model should approvals use: one-shot approval, per-run approval, per-deployment unlock, or per-action approval?
- `[Must decide before implementation]` Should delegated clarifications appear as regular thread messages, a separate approval queue, or both?
- `[Must decide before implementation]` Should delegated runs inherit only the active persona/profile already in scope for the thread, or be allowed to request broader project identity context through an explicit approval path?
- `[Can defer until later]` Should successful delegated results become codex entries, generated documents, or agent-run artifacts first?
- `[Can defer until later]` Should continuation summaries be delivered through `/api/events`, `/api/tasks/{task_id}/events`, `/api/agents/runs/{run_id}/events`, or a canonical mirror strategy?
- `[Can defer until later]` Should flow builder eventually orchestrate multi-step delegation, or remain a separate experimental surface?
- `[Needs code verification]` Is there a deployed runtime configuration outside default `docker-compose.yml` that already runs a cron scheduler/worker continuously?
- `[Needs code verification]` Is there a deployed runtime configuration outside default `docker-compose.yml` that already runs an agent worker or equivalent delegated execution service end to end?
- `[Needs code verification]` Which current docs should replace the missing `Thread-Artifact-Lineage.md` and `dev-mode-extended-spec.md` references in the docs map?
