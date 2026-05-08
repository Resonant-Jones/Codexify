---
tags:
* architecture
* adr
* agents
* guardian
* execution-contract
  aliases:
* ADR-020
* Guardian Mediated Coding Agent Execution Contract
---

# ADR-020: Guardian Mediated Coding Agent Execution Contract

## Status

Accepted

## Date

2026-04-29

## Classification

This ADR is architecture-impacting.

## Governing ADRs

- ADR-003: Message Identity vs Request Identity
- ADR-010: Self-Extending Agent Plugin System
- ADR-012: Post-Completion Eval Spine
- ADR-014: Flow Builder Thread, Draft, and Receipts Contract
- ADR-005: Runtime Mode and Account Boundary Invariants

## Context

Codexify already treats Guardian as the owner of chat threads, message identity,
request identity, assistant persistence, task events, and durable transcript
state. That ownership has to remain intact if a future coding-agent substrate
such as Pi SDK is attached behind Guardian.

The missing seam is a bounded execution contract that lets Guardian package a
coding request, route it to an adapter, and ingest the result before anything is
shown to the user or persisted as a personal record.

Without that seam, a future coding agent could accidentally become the
conversation owner, memory owner, or lineage owner. This ADR prevents that by
fixing the request and result contract around Guardian-issued identity and
Guardian-controlled persistence.

## Decision

Codexify defines a Guardian-mediated coding-agent execution contract.

All user coding-agent requests must pass through Guardian intake first. Guardian
creates a coding-task envelope, attaches policy and scope, and forwards the
request to a coding-agent adapter only after it has established request
identity, thread identity, and permission boundaries.

All coding-agent results must return through Guardian result ingestion first.
Guardian then decides whether the result becomes an assistant-side record,
execution artifact, or other personal record reference.

This ADR defines the contract only. It does not introduce live Pi SDK calls,
runtime dispatch, autonomous execution, route behavior, or persistence schema
changes.

## Request Path

User -> Guardian intake -> Guardian coding task envelope -> coding-agent adapter

## Result Path

coding-agent adapter -> Guardian result ingestion -> assistant message / personal
record

## Required Task Envelope Fields

| Field | Meaning |
| --- | --- |
| `codingTaskId` | Guardian-owned task identity for the coding execution attempt. |
| `threadId` | Source chat thread that anchors the request lineage. |
| `sourceMessageId` | User-authored message that requested the coding action. |
| `requestId` / `attemptId` | Attempt identity for the execution instance. |
| `userId` / actor subject | Guardian-resolved user or acting subject. |
| `projectId` | Optional project scope for the request. |
| `workspace scope` / `repo root` | Optional local workspace or repository boundary. |
| `allowed paths` | Filesystem paths the adapter may touch inside Guardian-issued scope. |
| `instructions` | The bounded coding instructions to execute. |
| `context bundle summary` | A Guardian-owned summary of the context sent to the adapter. |
| `permission policy` | The capability and boundary policy issued by Guardian. |
| `adapter kind` | Which adapter target Guardian selected. |

## Required Result Payload Fields

| Field | Meaning |
| --- | --- |
| `codingTaskId` | Links the result to the Guardian-owned task identity. |
| `requestId` / `attemptId` | Links the result to the specific execution attempt. |
| `status` | The terminal or in-progress coding-task state. |
| `summary` | Human-readable result summary. |
| `files changed` | Files the adapter reports as changed. |
| `artifacts` | Generated artifacts or bounded outputs. |
| `logs summary` | Condensed execution logs or trace notes. |
| `error code/message` | Nullable failure details when the attempt fails. |
| `adapter session reference` | Nullable handle for future adapter session lookup. |

## Contract Rules

### Intake Rule

Guardian must own request intake, identity resolution, and policy attachment
before any adapter sees the task.

### Persistence Rule

Coding-agent results must be captured by Guardian before any user-visible
assistant output or personal-record persistence occurs.

### Transcript Rule

The user-authored message remains the lineage anchor. The coding-agent result is
an attempt-scoped execution record, not a replacement for the original message.

### Replay Rule

Replays must create a new attempt identity linked to the same source message.
The original message identity must remain unchanged.

### Export / Restore Rule

Any future persisted coding-agent result records must preserve thread, message,
attempt, artifact, and provenance lineage. Restore must not silently drop that
lineage.

### Security and Policy Rule

Coding-agent adapters operate only inside Guardian-issued permissions and scoped
filesystem or workspace boundaries. Adapters may not widen scope on their own.

### Pi SDK Interpretation

Pi SDK, if introduced later, is an execution substrate only. It is not the
conversation owner, memory owner, identity owner, or canonical persistence
owner.

## Non-Goals

This ADR does not:

- implement Pi SDK runtime calls
- add a live coding-agent route
- alter the chat completion loop
- alter command bus behavior
- add database migrations
- create autonomous coding-agent execution
- change provider routing
- widen the supported beta promise

## Consequences

### Positive

- Guardian keeps ownership of request identity and lineage
- future adapters can be swapped without rewriting the control plane
- result handling stays bounded before user-visible presentation
- export and restore can preserve a single provenance spine

### Negative

- the system needs another contract surface to maintain
- later runtime work must respect the Guardian envelope instead of inventing a
  direct adapter shortcut

## Open Questions

- exact DB table shape for durable coding-agent runs
- whether result summaries become assistant messages immediately or remain
  inspectable execution artifacts first
- how much raw session transcript or log material is retained
- where Pi SDK sessions are stored or referenced

## Links

- [[ADR Index]]
- [[003-Message-Identity-vs-Request-Identity|ADR-003 Message Identity vs Request Identity]]
- [[010-Self-Extending-Agent-Plugin-System|ADR-010 Self-Extending Agent Plugin System]]
- [[012-Post-Completion-Eval-Spine|ADR-012 Post-Completion Eval Spine]]
- [[014-Flow-Builder-Thread-Draft-and-Receipts-Contract|ADR-014 Flow Builder Thread, Draft, and Receipts Contract]]
- [[005-Runtime-Mode-and-Account-Boundary-Invariants|ADR-005 Runtime Mode and Account Boundary Invariants]]
- [[chat-runtime-contract|Chat Runtime Contract]]
- [[account-export-restore-contract|Account Export + Restore Contract]]
- [[self-extending-agent-plugin-system|Self-Extending Agent Plugin System]]
- [[flows|Critical Flows]]
- [[data-and-storage|Data and Storage]]
- [[modules-and-ownership|Modules and Ownership]]
- [[00-current-state]]
