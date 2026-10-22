# Guardian Delegation Loop Contract

Purpose: define v1 as a hybrid bridge: `Guardian-owned chat intake -> task normalization -> durable intent artifact -> existing coding-run backbone -> Guardian thread continuation -> Command Center transcript mirror`.

Last updated: 2026-09-24

Source anchors:
- docs/architecture/00-current-state.md
- docs/architecture/README.md
- docs/architecture/adr/adr-index.md
- docs/architecture/runtime-protocol-token-contract.md
- docs/architecture/chat-runtime-contract.md
- docs/architecture/agent-tool-loop-contract.md
- docs/architecture/pi-invocation-boundary-contract.md
- docs/architecture/self-extending-agent-plugin-system.md
- docs/architecture/account-export-restore-contract.md
- docs/architecture/delegation-runtime.md
- docs/architecture/adr/020-guardian-mediated-coding-agent-execution-contract.md
- docs/architecture/adr/022-guardian-intent-spine-and-cross-surface-control-plane.md
- docs/architecture/adr/ADR-048-guardian-three-channel-delegation-topology.md
- docs/iddb_policy_v1.md

## Classification

- Classification: Aligned with existing ADR(s)
- Governing ADRs/contracts:
  - ADR-010 Self-Extending Agent Plugin System
  - ADR-020 Guardian Mediated Coding Agent Execution Contract
  - ADR-022 Guardian Intent Spine and Cross-Surface Control Plane
  - Agent Tool Loop Contract
  - Pi Invocation Boundary Contract
  - Chat Runtime Contract
  - Runtime Protocol Token Contract
  - Account Export + Restore Contract
  - IDDB Policy v1
  - Delegation Runtime Contract
- Reason:
  - This task creates a contract document for the Guardian Delegation Loop v1 hybrid bridge. It binds existing runtime, delegation, approval, lineage, and coding-agent concepts without widening the supported release promise or changing runtime behavior.

## Scope

- v1 is scoped to Guardian-to-coding-agent delegation only.
- The execution backbone is the existing coding-run/AgentRun path.
- The source thread remains user truth.
- Command Center transcript is inspection truth, not a second conversational thread.
- Broad "answer as me" authority is out of scope.
- Intent-spine unification is deferred.

Boundary posture for this contract:

- Nodes in scope: Guardian-owned chat intake, durable intent artifact storage, existing coding-run/AgentRun backbone, source-thread continuation path, and Command Center transcript mirror.
- Trust boundary: Guardian remains the owner of intake, approval, lineage, and posting; the coding-run backbone is execution substrate only; the Command Center transcript is a mirror only.
- Threat posture: design first for honest-but-buggy execution, delayed visibility, superseded runs, and context leakage risk; block broader authority and personal-context spillover by default.

## Delegated Task read projection

A Delegated Task is a product/read-model projection over Guardian delegation lineage. Chat is the only implemented source surface in this slice; the projection itself must not redefine delegation as a chat-thread subtype. `GuardianDelegationIntent.intent_id` remains its identity and durable delegation authority. `GET /api/guardian/delegations?thread_id=<id>` lists the existing intents for one canonical source Chat Thread, using separate intent, run, approval, and visibility axes. The existing per-intent transcript endpoint remains read-only execution inspection truth.

Delegated Tasks are subordinate execution lineage, not conversational transcript authority. One Chat Thread may spawn many Delegated Tasks, and a Delegated Task may carry one or more execution attempts/runs under the existing execution records. Questions and clarifications return through Guardian to the originating Chat Thread; results are delivered back through Guardian. Direct human conversation inside a Delegated Task is not part of this slice.

Workspace inspection is the intended future presentation direction, but is not implemented here. Work Threads, sidebar task rows, and persistent reattachable stdout/stderr/PTY sessions remain deferred. This read projection does not change supported release posture.

## Current-Truth Anchors

What is true now:

- Codexify is local-first beta hardening on the supported Docker Compose path.
- Chat completion works on the supported path and persists into the source thread.
- Coding results return through Guardian into the source thread on the supported path.
- Existing runtime docs distinguish acceptance, execution, task-event visibility, and completion.
- Existing bounded tool/coding-agent contracts avoid claims of recursive autonomous execution.
- The Guardian delegation path can mint an execution binding from trusted account context, resolve an enforceable permission posture, persist both against the deployment, and enqueue exactly one coding-execution task. This is **code-path presence with contract tests, not live-runtime proof**: it has not been driven from a chat turn and has not been qualified on the supported Compose path.

What is not yet true:

- The Guardian Delegation Loop v1 is **not** implemented end to end. The delegation *authorization* and *dispatch* path now exists in code — a Guardian-owned execution binding, an enforceable permission posture, and a durable dispatch that enqueues one coding-execution task with a binding byte-identical to the persisted one — but it is **not yet driven from a chat turn**, and it is **not yet proven on the supported Compose path**.
- Guardian delegation is therefore still **non-executable from a user's conversation**. Nothing in this slice makes a chat turn produce a delegated task.
- The delegation route remains **flagged off by default** and quarantined by the supported profile, and no supported-profile or release-surface change has been made or authorized.
- The dispatch recovery contract is **quarantine-and-escalate**: automated re-dispatch is refused because no fencing token exists in this runtime.
- Broad "answer as me" authority does not exist.
- No new public release surface is implied by this contract.
- Intent-spine unification does not exist.
- No Command Center mirror implementation is claimed unless separately proven by current code and runtime docs.
- The current release gate is unchanged: the latest complete supported-Compose qualification remains `HOLD`, and autonomous coding-worker work is not promoted to default Beta support.

What this contract may assume:

- The contract may define the desired v1 semantics for future implementation.
- The contract may describe later phases as non-goals or deferred work.
- The contract may cross-link to existing architecture and ADR docs.

## Locked v1 Decisions

- Execution backbone: hybrid bridge
- Conversation model: non-blocking chat
- Approval model: scoped auto-approve
- Canonical contract artifact: this architecture contract document, not a new ADR
- Canonical future intake surface: Guardian-owned route
- Operator mirror: Command Center transcript surface, not second thread
- Phase 2 future scope: safe happy path only, with no human-approval or cancellation endpoints yet

## Entities

### `GuardianDelegationIntent`

Guardian-owned durable intent artifact for one delegated coding request. It binds `thread_id`, `source_message_id`, normalized work intent, work scope, `context_basis`, approval posture, lineage, and any later run linkage without claiming dispatch or completion by itself.

### `GuardianTaskPlan`

Task-normalized plan derived from `GuardianDelegationIntent`. It captures bounded work goals, repo/worktree scope, execution constraints, success criteria, and escalation points for the existing coding-run/AgentRun backbone.

### `GuardianApprovalDecision`

Guardian-owned decision record for whether a `GuardianDelegationIntent` or `GuardianTaskPlan` may dispatch. It keeps `approval_state`, `approval_source`, scope rationale, and blocking reason separate from acceptance, execution, and visibility.

### `GuardianThreadInterruption`

Source-thread continuation artifact used to request clarification, surface approval needs, post result delivery, or explain degraded visibility. It is a mirror into the user truth thread, not the canonical run transcript.

### `GuardianRunTranscriptEvent`

Durable, ordered event record sourced from agent-run or coding-run events. It exists for inspection, operator visibility, and Command Center mirroring, and must not replace source-thread conversational truth.

### `ContextBasisEntry`

Explicit provenance record for one included context source. A `context_basis` collection explains why each source was included, what fields were used, how confidently it was selected, and whether policy allowed its use.

## Status Axes

These axes are separate truths. This contract does not claim that every value below is already emitted end-to-end in the live runtime, and it does not authorize collapsing them into one field.

- `acceptance_status`: reuse existing protocol tokens `accepted`, `accepted_degraded`
- `approval_state`: `pending`, `approved`, `blocked`
- `approval_source`: `none`, `auto`, `human`
- `intent_status`: `draft`, `planning`, `awaiting_clarification`, `awaiting_approval`, `accepted`, `superseded`, `cancelled`, `failed`
- `run_status`: `not_enqueued`, `queued`, `running`, `completed`, `failed`, `cancelled`
- `visibility_status`: `not_posted`, `interrupt_posted`, `result_posted`, `stale_suppressed`, `delivery_degraded`

### Axis Ownership of Facts

Which axis owns which fact. Writing a fact onto the wrong axis is a category error, and the axes are not interchangeable.

- **`acceptance_status` is admission-scoped.** It records whether the request was admitted and whether the `task.created` start event was visible. `accepted` means admitted with a visible start event; `accepted_degraded` means admitted with degraded start-event visibility (publish failed, or the published event carried no event id). It is derived from the publish outcome in `guardian/core/chat_completion_service.py` and logged beside `task_created_visibility_scope` in `guardian/routes/chat.py`. **It never carries an execution fact.**
- **`intent_status` owns the execution outcome.** A dispatch failure sets `intent_status` to `failed`. It does not alter `acceptance_status`: the request was admitted, and admitting it did not fail.
- **`run_status` is a projection, not a stored field.** `GuardianDelegationIntent` has no `run_status` column. `_resolve_row_run_status` derives it from the linked `AgentRun`, returning `not_enqueued` when no run is linked. Adding a stored `run_status` would require a schema migration and is not authorized here.
- **`visibility_status` owns what the user actually saw.** A dispatch failure leaves it `not_posted`, because the user was never shown a start event.

Consequently, a Guardian dispatch failure must not be recorded as `accepted_degraded`: that token would assert an acceptance-and-visibility state that did not occur. No new protocol token is added for this; the existing axes already carry every fact.

### Dispatch authorization

Dispatching a delegated coding task requires two Guardian-owned authorizations, both resolved from trusted account, project, and workspace context — never from the request.

- **The execution binding** (`guardian/core/guardian_execution_binding.py`) names the provider, model, harness, credential reference, owner scope, and lineage for one attempt. It is secret-free, attempt-scoped, and immutable once established. The provider and credential come from the account's own registered credentials; the model is pinned from the runtime's configuration for that provider. A caller proposal may narrow a grant, never widen one. The binding is persisted into the deployment spec **before** the task is queued, because the credential-lease authority re-reads it from the spec and the coding worker requires the task payload binding to equal the persisted one byte-for-byte.
- **The permission posture** (`guardian/core/guardian_permission_posture.py`) states which surfaces actually enforce the grant and which do not. Per ADR-077 rule 6, denied filesystem mutation is enforced below the model/tool layer; per rule 7, tool allowlists and prompt instructions are defense in depth, not filesystem, network, or process isolation. The git mutation guard **detects** an out-of-scope mutation and fails the attempt — it does not prevent the write. `allow_network` is a request, not an egress guarantee, because no sandbox provider is wired into the coding worker. The posture is therefore advisory for network egress and process isolation, and says so rather than claiming enforcement it cannot evidence.
- **The reasoning effort** is part of the execution binding, not a separate configuration surface. Guardian resolves the effective effort from the provider and model the binding pins, before anything is dispatched, and records it in the binding. The binding schema version is the discriminator: a version 2 binding *governs* the effort and therefore carries it, while a version 1 binding predates the contract and governs nothing, so the harness keeps its own default exactly as before. A version 1 binding is never reinterpreted as if it had governed one. The coding worker forwards the persisted value verbatim to the adapter and selects no level of its own — from the model identity, from ambient process configuration, or from a caller-supplied task field. Because the queued task's binding must equal the persisted one byte-for-byte, a tampered effort is a binding mismatch and is refused before any provider execution. An effort the harness does not accept, or one the lane has not validated, fails closed at resolution time; it is never clamped or downgraded to a level Guardian did not select. The lanes that have been validated are a bounded list in `guardian/agents/coding_agent_contracts.py`, not a model-capability registry: a lane that is not listed there has no validated compatibility rule and is left ungoverned.

### Dispatch recovery

The queue is `LPUSH` + destructive `BRPOP`/`RPOP` with no ack, no pending list, and no requeue. Four layers must therefore be kept distinct, because a guarantee on one says nothing about another:

| Layer | Guarantee | Mechanism |
|---|---|---|
| Task delivery | **At-most-once, and lossy** | `guardian/queue/redis_queue.py` |
| Attempt execution | **Unguaranteed** | a dequeued task may still be executing |
| Execution effects | **Not idempotent** | the adapter runs a subprocess with write access and may commit |
| Result delivery | **Idempotent** per (intent, run) | `build_guardian_delegation_result_delivery_key` |

**No exactly-once execution claim is made.** A missing heartbeat is *uncertain*, not lost: the worker may be between phases, blocked on a subprocess, or in a long validation loop. Recovery is therefore **quarantine-and-escalate**. Automated re-dispatch is refused while no fencing token exists, because without fencing a superseded attempt's writes cannot be rejected, and isolation alone bounds cross-contamination but not duplicate logical effects. A recovery attempt must mint a new attempt id, a new binding, and a freshly issued credential lease. This mirrors the existing chat recovery idiom, which also refuses to execute during recovery.

Dispatch state lives in `guardian/core/guardian_dispatch.py` and is durable and queryable: `prepared`, `dispatched`, `executing`, `completed`, `failed`, `uncertain`, `quarantined`, `cancelled`. Recovery reads that state; it never infers from absence.

## Coding Delegation Context Policy

Guardian-to-coding-agent delegation is work-scoped by default.

Authoritative default context hierarchy, highest precedence first:

1. `source_message_id` and the selected user turn
2. Codexify Project Knowledge Base
3. Project-scoped architecture docs, ADRs, task files, protocols, and linked artifacts
4. GitHub repository context when configured and task-relevant, including relevant files, issues, PRs, commits, and discussions
5. Current thread context only when needed to resolve immediate task framing
6. Explicitly work-scoped engineering preferences and protocols

Excluded by default:

- broad chat history
- general personal facts
- identity-derived facts
- emotional venting
- client, boss, or relationship commentary
- unrelated prior conversations

Required rules:

- Guardian coding delegation may use only explicit task input, project-scoped knowledge, linked artifacts, configured repository context, and explicitly work-scoped preferences/protocols.
- Personal facts and broad chat history are excluded by default.
- Stored preferences or protocols may be included only if explicitly marked work-scoped, relevant to the task, policy-allowed, and recorded in `context_basis`.
- Raw personal facts may never be injected directly into coding prompts, agent commentary, code comments, commit messages, PR text, or result summaries.
- No coding task prompt, code comment, commit message, PR text, agent commentary, or result summary may include excluded personal or conversational context.

## `ContextBasisEntry`

`ContextBasisEntry` is the minimum provenance unit for any context included in a Guardian-to-coding-agent delegation payload.

Required fields:

| Field | Meaning |
| --- | --- |
| `source_type` | The canonical source category for the included context. |
| `source_id` | Stable reference for the included source object, document, thread turn, repo object, or policy artifact. |
| `included_fields` | The specific fields, excerpts, or structured attributes that were included from the source. |
| `reason` | Why the source was included for this delegated task. |
| `confidence` | The confidence Guardian has that the source is relevant and correctly scoped for the delegated task. |
| `policy_allowed` | Boolean or equivalent explicit indicator that policy allowed inclusion of this source. |

Recommended `source_type` values for coding v1:

- `selected_turn`
- `project_kb`
- `architecture_doc`
- `adr`
- `task_file`
- `protocol_doc`
- `linked_document`
- `linked_image`
- `github_file`
- `github_issue`
- `github_pr`
- `github_commit`
- `github_discussion`
- `thread_frame`
- `work_scoped_preference`

## Invariants

- Guardian may not infer durable user identity traits or durable intent from the delegated task.
- Guardian coding delegation may use only explicit task input, project-scoped knowledge, linked artifacts, configured repository context, and explicitly work-scoped preferences/protocols.
- Personal facts and broad chat history are excluded by default.
- A delegated result may not post back to the thread without `thread_id`, `source_message_id`, and lineage.
- A superseded run may complete, but its result must be suppressed from the source thread.
- Durable run transcript is sourced from agent-run events.
- Thread interruptions and global notifications are mirrors.
- Acceptance, approval, execution, and visibility must not be collapsed into one state.
- The reasoning effort is Guardian's to select and the binding's to carry. A worker task may not choose or widen its own invocation options, and an effort the Guardian did not authorize must not reach the harness.

## Deferred Phases / Non-Goals

- No runtime implementation in this slice.
- No route implementation in this slice.
- No database migration in this slice.
- No second thread.
- No broad auto-approve.
- No intent-spine unification.
- No current-state/release-truth widening.

## Proof Surface for Future Phases

- Safe happy path proves selected turn -> work-scoped `context_basis` -> `GuardianDelegationIntent` -> scoped auto-approval -> AgentRun dispatch -> linked `run_id`.
- Thread closure proves exactly one terminal result delivery.
- Supersession proves stale completion suppression.
- Command Center proves transcript mirror from durable run events.
- Approval lifecycle proves approve/cancel behavior only after happy path is proven.
