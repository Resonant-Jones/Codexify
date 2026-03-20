Codexify: Artifact Event Capture, Thread Modes, and Task Graph

Status: Draft v0.1
Audience: Engineering, product, and system design contributors
Scope: Repo-ready architecture + product specification

⸻

1. Purpose

Codexify should automatically persist generated work artifacts and execution context so that tasks, notes, documents, and thread lineage become:
 • recoverable
 • reorderable
 • traceable
 • branch-aware where applicable
 • usable without manual filing at creation time

This feature addresses task loss, context fragmentation, and artifact scattering during active development.

⸻

1. Problem Statement

Work artifacts are already being generated conversationally:
 • “turn this into a task”
 • “turn this into a note”
 • “turn this into a document”

However, these artifacts are not consistently persisted or structured as first-class system objects.

Consequences:
 • ideas are lost or buried in threads
 • execution context and branch context drift apart
 • follow-up work must be rediscovered manually
 • lineage between artifacts is weak or implicit

⸻

1. Design Goals
 • Zero-friction capture at point-of-thought
 • Automatic persistence of generated artifacts
 • Clear separation between capture and promotion
 • Append-only event history as source of truth
 • Task queue derived from artifact graph
 • Minimal disruption to existing core loop

⸻

1. Non-Goals (V1)
 • Full project management system
 • Sprint planning or calendars
 • Multi-user collaboration features
 • Heavy UI systems (kanban boards, etc.)
 • Mandatory forms at capture time

⸻

1. Core Concepts

5.1 Thread Modes

Execution Thread
A thread capable of producing operational artifacts.

Properties:
 • may generate tasks
 • may bind to branch/worktree
 • records execution context
 • allows planning and design discussion

Non-Execution Thread
A thread for ideation and reference.

Properties:
 • may generate notes/documents
 • does not bind to execution context
 • does not trigger execution flows

Key distinction: permission and consequence, not topic.

⸻

5.2 Artifact Types

First-class artifact categories:
 • Task
 • Note
 • Document

Future extensions may include prompts, summaries, and derived assets.

⸻

1. Capture Model

6.1 Automatic Capture Triggers

Artifacts are auto-created when:
 • user invokes: “turn this into a task”
 • user invokes: “turn this into a note”
 • user invokes: “turn this into a document”
 • structured artifact blocks are generated
 • execution threads change branch binding

6.2 Capture Philosophy
 • Capture should be automatic
 • Metadata should be inferred
 • User action should be minimal

Text storage cost is negligible compared to the cost of losing context.

⸻

6.3 Auto-Save vs Promotion

Auto-Save:
 • artifact is persisted

Promotion:
 • artifact becomes operational (task queue, priority, dependency)

These must remain separate.

⸻

1. Event Graph Model

The system is built on an append-only event log with graph relationships.

7.1 Node Types
 • thread
 • message_span
 • artifact
 • task
 • note
 • document
 • branch
 • worktree
 • commit

7.2 Edge Types
 • CREATED_IN
 • DERIVED_FROM
 • BOUND_TO_BRANCH
 • PROMOTED_TO_TASK
 • RELATED_TO
 • DEPENDS_ON
 • COMPLETED_BY
 • ARCHIVED_AS

⸻

1. Task Queue (Derived View)

Tasks are not the source of truth.

They are derived from artifact records.

8.1 Separation of Concerns
 • Event time = historical truth
 • Priority order = execution intent

8.2 Supported Operations
 • reorder
 • status transitions
 • filtering
 • dependency relationships (future)

⸻

1. Data Model

9.1 Thread Context

type ThreadContext = {
  threadId: string
  mode: "execution" | "note" | "reference"
  executionEnabled: boolean
  boundBranch?: string
  boundWorktree?: string
  activeTaskId?: string | null
  createdAt: string
  updatedAt: string
}

9.2 Artifact Record

type ArtifactRecord = {
  id: string
  type: "task" | "note" | "document"
  title: string
  body: string

  threadId?: string
  sourceMessageId?: string

  branch?: string | null
  worktree?: string | null

  status?: "inbox" | "shaped" | "ready" | "doing" | "done" | "dropped"
  priority?: number | null

  createdAt: string
  updatedAt: string
  archivedAt?: string | null
}

9.3 Event Record

type ArtifactEvent = {
  id: string
  eventType: string
  actor: "user" | "assistant" | "system"
  threadId?: string
  artifactId?: string
  payload: Record<string, unknown>
  createdAt: string
}

⸻

1. Metadata Inference

Automatically infer:
 • timestamp
 • thread id
 • thread mode
 • artifact type
 • title

Optional enrichment:
 • branch/worktree
 • related artifacts
 • inferred tags

⸻

1. UI Surfaces (V1)

11.1 Thread Mode Indicator

Displays execution capability.

11.2 Artifact Inbox
 • recent tasks
 • notes
 • documents
 • quick actions (delete, archive, promote)

11.3 Task Queue
 • reorderable
 • status tracking
 • linked to source artifacts

11.4 Artifact Detail View
 • source thread
 • source message
 • branch linkage
 • related artifacts

⸻

1. Backend Surface (Illustrative)
 • POST /api/artifacts
 • GET /api/artifacts
 • GET /api/artifacts/{id}
 • POST /api/artifacts/{id}/promote
 • POST /api/tasks/reorder
 • POST /api/threads/{id}/mode
 • POST /api/threads/{id}/bind-branch
 • GET /api/events

⸻

1. Storage Strategy

Recommended:
 • Artifact table (primary records)
 • Event log (append-only)
 • Derived task queue

Initial implementation should use existing Postgres infrastructure.

⸻

1. Architectural Guardrails
 • Do not tightly couple to completion pipeline
 • Avoid synchronous heavy processing at capture time
 • Keep event history immutable
 • Keep priority mutable
 • Avoid frontend state fragmentation

⸻

1. Phased Rollout

V1
 • thread modes
 • auto-save artifacts
 • artifact inbox
 • basic task queue
 • lineage linking

V2
 • dependencies
 • commit linkage
 • clustering

V3
 • graph visualization
 • task recommendations
 • deduplication

⸻

1. Open Questions
 • Branch binding: manual vs inferred?
 • Auto-save scope: all generated blocks or explicit only?
 • Single table vs polymorphic storage?
 • Task ordering model?
 • Service boundary for capture logic?

⸻

1. Summary

Codexify should automatically persist generated work artifacts as graph-linked events, enabling:
 • durable lineage
 • recoverable context
 • reorderable execution
 • minimal capture friction

This system transforms conversational output into structured, operational memory without interrupting developer flow.
