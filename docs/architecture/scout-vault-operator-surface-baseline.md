# Scout/Vault Operator Surface Baseline

## 1. Purpose

This note captures the current six-tab Scout/Vault operator navigation topology as a **complete-for-now baseline**. It exists so that future work does not treat the Activity tab as unfinished merely because additional observability surfaces are conceptually possible. Each tab has a distinct operator question it answers. Together they form a coherent navigation surface. This baseline defines what is true today, what is intentionally not yet true, and which future Activity surfaces are explicitly deferred.

## 2. Scope

This document covers operator-facing navigation semantics only. It does not define new runtime behavior, new backend routes, new frontend components, new streaming architecture, new task event semantics, or new release claims.

It covers these six tabs:

- Guardian Chat
- Inspector
- Server Status
- Activity
- Artifacts
- Settings

## 3. Current six-tab baseline

Each tab answers a distinct operator question. The mapping is:

- Guardian Chat -> "What did Guardian say?"
- Inspector -> "What evidence supports that?"
- Server Status -> "Is Vault healthy?"
- Activity -> "What happened across all threads?"
- Artifacts -> "What outputs do I own?"
- Settings -> "How do I connect?"

The six tabs form a complete navigation loop: talk to Guardian, inspect evidence, verify health, review history, manage outputs, and configure connections.

### Guardian Chat

**"What did Guardian say?"**

The primary conversation surface. The operator sends messages, Guardian responds. This is the active interaction lane — the operator's real-time dialogue with the system. It is the entry point for chat, tool requests, and delegation.

### Inspector

**"What evidence supports that?"**

The provenance surface. When Guardian makes a claim, cites a source, or references prior work, the Inspector shows the supporting evidence. It answers the operator's audit question: where did this come from?

### Server Status

**"Is Vault healthy?"**

The runtime health surface. Shows live backend connectivity, queue depth, worker status, model availability, and configuration posture. The operator checks this tab when something seems slow, broken, or misconfigured.

### Activity

**"What happened across all threads?"**

The cross-thread recent task receipt timeline. It aggregates task receipts from existing thread and per-thread receipt surfaces into a unified chronological view. It is intentionally an N+1 aggregation in the view layer — it does not require a new backend aggregation route, a streaming pipeline, or new task event semantics. It degrades gracefully when threads or receipts are empty. This is acceptable for the current single-user Vault/operator case.

The Activity tab currently answers *receipt-level* questions: what tasks ran, on which threads, and what their outcomes were. It does not answer live-execution questions, streaming observation questions, or notification questions. Those are deferred.

### Artifacts

**"What outputs do I own?"**

The durable-output surface. Shows user-owned artifacts generated during conversations: code snippets, generated documents, exported files, saved results. The operator browses, inspects, and retrieves outputs from prior interactions.

### Settings

**"How do I connect?"**

The connection and configuration surface. Manages Vault endpoint profiles, authentication, runtime preferences, and connectivity state. This is the operator's entry point for configuring how Scout reaches and authenticates with a Vault instance.

## 4. Activity tab current behavior

The Activity tab presents a cross-thread recent task receipt timeline. It answers the question "what happened across all threads?" at receipt granularity.

Key characteristics:

- It uses existing thread and per-thread receipt surfaces. No new backend aggregation route is required.
- It is intentionally an N+1 aggregation in the view layer. The frontend enumerates threads and collects their receipts into a unified timeline.
- It does not pretend to be a streaming aggregation pipeline. It is a polling/refresh-driven view of persisted receipt data.
- It does not require a new backend route. The data it needs already exists on existing endpoints.
- It degrades gracefully when threads or receipts are empty. An empty timeline is valid and intentional, not a failure state.
- This is acceptable for the current single-user Vault/operator case. Multi-user, high-throughput, or real-time scenarios would need a different architecture, but those are not the current supported posture.

## 5. Explicit non-goals

This baseline does **not** implement or require:

- Active Tasks dashboard
- SSE Observations dashboard
- Completion Requests dashboard
- Notifications surface
- New backend aggregation route
- New streaming architecture
- New task event semantics
- New queue or worker semantics
- New release promise

These are all plausible future observability surfaces. They are intentionally excluded from the current baseline to prevent scope creep and to avoid implying that the Activity tab is incomplete.

## 6. Deferred Activity surfaces

The following Activity-adjacent observability surfaces are explicitly deferred. Each requires either a new backend route, a streaming architecture, or validated operator demand before implementation.

| Deferred surface | What it would answer | Why it is deferred | Likely prerequisite |
|---|---|---|---|
| **Active Tasks** | "What is running right now?" | Requires live task-state visibility beyond persisted receipts; needs queue inspection, worker heartbeat aggregation, or a new task-status endpoint. | Real-time task-status endpoint or queue-inspection route. |
| **SSE Observations** | "What is Guardian doing in real time?" | Requires a streaming event pipeline distinct from current polling/refresh receipts; SSE or WebSocket transport not yet operator-facing. | Streaming event transport to the frontend with durable subscription semantics. |
| **Completion Requests** | "What LLM requests are in flight?" | Requires exposing internal completion-request state; the current architecture treats completion as an implementation detail of the chat loop, not an operator-visible surface. | Completion-pipeline observability endpoint with bounded lifetime and no queue semantics leak. |
| **Notifications** | "What should I pay attention to right now?" | Requires a notification model (priority, read/unread, dismiss, per-tab badge counts) distinct from receipt history; no notification system exists today. | Operator notification model with routing rules and frontend badge/delivery surface. |

Each deferred surface is a legitimate observability concept. None is required for the current baseline to be complete. All are deferred until operator demand, validated architecture, or explicit Campaign work moves them forward.

## 7. Current-truth anchors

### What is true now

- The six-tab navigation topology has distinct operator semantics.
- Guardian Chat is the primary conversation surface.
- Inspector shows evidence and provenance for Guardian claims.
- Server Status shows runtime health, connectivity, and configuration posture.
- Activity answers cross-thread receipt history using existing thread/per-thread receipt surfaces.
- Artifacts shows user-owned durable outputs.
- Settings manages Vault endpoint profiles and connectivity configuration.
- The Activity tab is an N+1 view-layer aggregation, not a streaming pipeline.
- Docs-only baselines do not prove runtime support.
- Local-first beta hardening and current release posture remain governed by `docs/architecture/00-current-state.md`.

### What is not yet true

- No Active Tasks dashboard exists.
- No SSE Observations dashboard exists.
- No Completion Requests dashboard exists.
- No Notifications surface exists.
- No new backend aggregation route exists for Activity.
- No streaming architecture exists for operator-facing observability.
- No release promise expansion accompanies this baseline.

### What future work may assume

- The six-tab topology is the navigation baseline and new tabs should be proposed as additions, not replacements.
- Activity means cross-thread receipt history. It does not mean live task execution proof.
- Deferred Activity surfaces need explicit architecture work before implementation.
- This baseline does not constrain what Guardian Chat, Inspector, Artifacts, or Settings tabs may become.

## 8. ADR impact

- **Classification**: No ADR impact for this docs-only baseline.
- **Reason**: This note documents current operator navigation semantics and defers future observability surfaces without changing runtime contracts. It does not alter acceptance semantics, retrieval doctrine, message/attempt identity, control-plane boundaries, task event semantics, or any ADR-governed runtime contract.
- **Future ADR warning**: Future work may require ADR alignment or a new ADR if it changes task event semantics, streaming aggregation, queue/worker acceptance semantics, operator truth surfaces, or release claims.

## 9. Invariants

1. Route acceptance is not completion.
2. Task-event publication is not UI receipt.
3. Activity receipt aggregation is not live task execution proof.
4. Current Activity does not imply Active Tasks, Notifications, SSE Observations, or Completion Requests dashboards are shipped.
5. Operator-facing labels must not imply stronger runtime truth than the backend proves.
6. This note must not widen the current beta release promise.

## 10. Documentation follow-through

- A narrow link is added to `docs/architecture/README.md` in the doc map section, near the existing Scout-related contracts.
- `docs/architecture/00-current-state.md` is not updated.
- Runtime diagrams are not updated.
- UI diagrams are not updated.

## 11. Suggested next task

Return to Personal Facts UI guardrails by surfacing persisted `guardrail_metadata` in the candidate review UI. Do not expand Activity until operator demand proves the need.
