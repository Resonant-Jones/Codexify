# Guardian Delegation Loop Contract

Purpose: define v1 as a hybrid bridge: `Guardian-owned chat intake -> task normalization -> durable intent artifact -> existing coding-run backbone -> Guardian thread continuation -> Command Center transcript mirror`.

Last updated: 2026-05-25

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

## Current-Truth Anchors

What is true now:

- Codexify is local-first beta hardening on the supported Docker Compose path.
- Chat completion works on the supported path and persists into the source thread.
- Coding results return through Guardian into the source thread on the supported path.
- Existing runtime docs distinguish acceptance, execution, task-event visibility, and completion.
- Existing bounded tool/coding-agent contracts avoid claims of recursive autonomous execution.

What is not yet true:

- The Guardian Delegation Loop v1 is not implemented.
- Broad "answer as me" authority does not exist.
- No new public release surface is implied by this contract.
- Intent-spine unification does not exist.
- No Command Center mirror implementation is claimed unless separately proven by current code and runtime docs.

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
