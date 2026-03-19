# Codexify Runtime Diagrams v1

## Purpose

This document is the first-pass runtime diagram pack derived only from the validated runtime KB source set. It is a baseline runtime view for peer review, not a final presentation artifact.

## Source set used

- `/docs/architecture/00-current-state.md`
- `/docs/architecture/README.md`
- `/docs/architecture/system-overview.md`
- `/docs/architecture/flows.md`
- `/docs/architecture/data-and-storage.md`
- `/docs/architecture/config-and-ops.md`
- `/docs/architecture/modules-and-ownership.md`

## Interpretation constraints

- `00-current-state.md` overrides broader docs on short-horizon release reality.
- These diagrams reflect the current runtime baseline, not aspirational architecture.
- Optional or not-currently-active systems are labeled explicitly.
- Quarantined legacy docs were not used.

## Diagram legend

- `durable`: persisted state or system-of-record surfaces that the validated runtime docs treat as restart-stable.
- `operational / ephemeral`: queues, locks, event transport, or process-local state that keep the runtime moving but are not primary durable truth.
- `optional`: present in current runtime docs but not required for the baseline supported path.
- `feature-flagged`: available only when explicit runtime flags or policy enable it.
- `release-bounded exclusion`: intentionally omitted from v1 because the validated runtime docs do not treat it as part of the present release promise.

## Diagram 1: Runtime Topology Overview (high confidence)

```mermaid
flowchart LR
    user["User"]

    subgraph clients["Client Boundary"]
        browser["Browser"]
        tauri["Tauri desktop shell<br/>(optional client shell)"]
        frontend["React frontend"]
        client_state["Local/session storage"]
    end

    subgraph runtime["Supported local runtime (Docker Compose)"]
        backend["FastAPI backend"]
        event_surface["Event surfaces<br/>/api/events and /api/tasks/*/events"]
        workers["Worker layer<br/>chat, chat-embed, document-embed, warmup, cron"]
        context["Context + retrieval orchestration"]
        ingestion["Media + document ingestion"]
        command["Command bus + legacy tools shim<br/>(beta / internal-only surfaces)"]
    end

    subgraph durable["Durable stores"]
        postgres["Postgres<br/>system of record"]
        vector["Vector store<br/>message and document embeddings"]
        media_store["File/object storage<br/>media and generated artifacts"]
    end

    subgraph operational["Operational transport"]
        redis["Redis<br/>queues, locks, task events, heartbeats"]
    end

    subgraph optional["Optional / feature-flagged"]
        neo4j["Neo4j<br/>optional / feature-flagged graph context<br/>(not part of baseline release path)"]
    end

    subgraph model_boundary["Model execution boundary"]
        provider["Local or cloud model provider<br/>selected by runtime config and policy"]
    end

    user --> browser
    user --> tauri
    browser --> frontend
    tauri --> frontend
    frontend <--> client_state
    frontend --> backend
    frontend --> event_surface
    backend --> event_surface
    postgres --> event_surface
    redis --> event_surface
    event_surface --> frontend
    backend --> context
    backend --> ingestion
    backend --> command
    backend <--> postgres
    backend <--> redis
    workers <--> redis
    workers <--> postgres
    workers --> context
    workers --> vector
    workers --> provider
    context <--> postgres
    context <--> vector
    context -. feature-flagged .-> neo4j
    ingestion --> media_store
    ingestion --> postgres
    ingestion --> redis
```

Supported runtime topology is the local Docker Compose stack. Non-Compose deployment remains unverified in the validated source set.

### Evidence notes

- Primary sources: `/docs/architecture/00-current-state.md`, `/docs/architecture/system-overview.md`, `/docs/architecture/config-and-ops.md`
- Conservative assumptions: worker types are collapsed into one worker layer, event surfaces are grouped into one runtime boundary, and provider execution is shown as one policy-shaped boundary rather than per-provider lanes.
- Explicit exclusions: non-Compose deployment detail, one-shot bootstrap services, federation/sync surfaces, and provider inventory/governance nuance beyond the current execution boundary.

## Diagram 2: Chat Completion Sequence (high confidence)

```mermaid
sequenceDiagram
    participant U as User
    participant FE as React frontend
    participant API as Chat API route
    participant Redis as Redis queue/task transport
    participant Worker as Chat worker
    participant Ctx as Context broker
    participant PG as Postgres
    participant Vec as Vector store
    participant Neo as Neo4j (optional / feature-flagged)
    participant LLM as Model provider
    participant Stream as Task event surface

    U->>FE: Submit message and request completion
    FE->>API: POST /api/chat/{thread_id}/complete
    API->>Redis: Acquire turn lock
    API->>Redis: Enqueue ChatCompletionTask
    API-->>FE: task_id, turn_id, messages_url, trace_url
    FE->>Stream: Subscribe to /api/tasks/{task_id}/events
    Worker->>Redis: Dequeue task and emit task.running
    Worker->>Ctx: Assemble context
    Ctx->>PG: Load messages, project scope, linked docs
    Ctx->>Vec: Run semantic retrieval
    opt graph context enabled
        Ctx->>Neo: Fetch graph snippets
    end
    Ctx-->>Worker: Context bundle
    Worker->>LLM: Completion request
    LLM-->>Worker: Assistant output
    Worker->>PG: Persist assistant message and audit/domain events
    Worker->>Redis: Publish task.completed and release turn lock
    Redis-->>Stream: Task events available
    Stream-->>FE: Task lifecycle updates
    FE->>API: Refresh messages_url
    API-->>FE: Updated thread/messages
```

This sequence keeps the baseline completion loop focused on the current enqueue -> worker -> retrieval -> persist -> task-event path documented in the validated runtime set.

### Evidence notes

- Primary sources: `/docs/architecture/flows.md`, `/docs/architecture/system-overview.md`, `/docs/architecture/00-current-state.md`
- Conservative assumptions: the task-event surface is shown as one actor, context assembly is compressed to its stable data dependencies, and the user-message step is collapsed into the request lane so the completion path stays readable.
- Explicit exclusions: provider catalog nuance, failure/retry branches, memory/sensor/federated context branches, and any future delegation or orchestration lanes.

## Diagram 3: Data and Storage Boundaries (high confidence)

```mermaid
flowchart TB
    subgraph runtime["Runtime surfaces"]
        frontend["React frontend / optional Tauri client shell"]
        backend["FastAPI routes + workers"]
    end

    subgraph durable["Durable / persisted state"]
        postgres["Postgres<br/>threads, messages, projects, memories,<br/>document metadata, audit, command runs,<br/>cron runs, events_outbox"]
        vector["Vector store<br/>semantic corpus for messages and documents"]
        media["File/object storage<br/>uploaded/generated media and artifacts"]
    end

    subgraph operational["Operational / ephemeral transport"]
        redis["Redis<br/>chat/document/cron queues,<br/>turn locks, task events, heartbeats"]
        buses["In-process buses<br/>fallback event fanout and sync subscription"]
    end

    subgraph client_local["Client-local state"]
        browser_state["Local/session storage<br/>auth/session state, runtime overrides,<br/>drafts, UI preferences"]
    end

    subgraph optional["Optional / feature-flagged"]
        neo4j["Neo4j<br/>optional / feature-flagged graph context<br/>(not part of baseline release path)"]
    end

    frontend <--> browser_state
    frontend --> backend
    backend <--> postgres
    backend <--> redis
    backend <--> vector
    backend <--> media
    backend -. process-local only .-> buses
    backend -. optional / feature-flagged .-> neo4j
```

This boundary map emphasizes durable state versus operational transport. Redis is operationally critical but not the system of record; Postgres remains the durable source of truth in the validated runtime set.

### Evidence notes

- Primary sources: `/docs/architecture/data-and-storage.md`, `/docs/architecture/system-overview.md`, `/docs/architecture/00-current-state.md`
- Conservative assumptions: routes and workers share one runtime access node, vector storage is shown as one logical retrieval store, and file/object storage is grouped as one artifact boundary.
- Explicit exclusions: entity-level schema detail, unverified retention/encryption claims, experimental sync durability, and backend-specific vector implementation detail.

## Diagram 4: Subsystem / Ownership Map (moderate confidence)

```mermaid
flowchart LR
    subgraph frontend_boundary["Frontend boundary"]
        shell["Frontend shell + session spine"]
        transport["Frontend transport + auth client"]
    end

    subgraph api_boundary["API / route layer"]
        bootstrap["API bootstrap + auth/exposure boundary"]
        chat["Chat routes + thread lifecycle"]
        media["Media/document routes"]
        command["Command bus + legacy tools shim<br/>(command bus internal-only in supported beta)"]
        cron["Cron routes + scheduled automation"]
    end

    subgraph core_services["Core services"]
        completion["Completion assembly + chat worker"]
        retrieval["Context + retrieval broker"]
        prompt["Prompt + profile system"]
        provider["Provider routing + catalog"]
        embed["Embedding + vector indexing"]
    end

    subgraph platform["Queue / workers / persistence"]
        queue["Queue + task transport"]
        persistence["Persistence + durable events"]
    end

    shell --> transport
    transport --> bootstrap
    bootstrap --> chat
    bootstrap --> media
    bootstrap --> command
    bootstrap --> cron
    chat --> queue
    chat --> persistence
    queue --> completion
    queue --> embed
    completion --> retrieval
    completion --> prompt
    completion --> provider
    retrieval --> persistence
    media --> queue
    media --> persistence
    embed --> persistence
    command --> persistence
    cron --> queue
    cron --> persistence
```

This is a seam map, not a call graph. It groups subsystem boundaries and conservative dependency direction; it does not enumerate every route, file, or runtime edge.

### Evidence notes

- Primary sources: `/docs/architecture/modules-and-ownership.md`, `/docs/architecture/system-overview.md`, `/docs/architecture/README.md`
- Conservative assumptions: subsystem clusters are grouped at seam level rather than file level, queue/workers/persistence are collapsed into one platform lane, and command bus plus legacy tools are shown together because the validated docs describe them as coexisting runtime surfaces.
- Explicit exclusions: experimental federation/sync boundary detail, collaboration/websocket detail, formal team ownership labels, and file-level hotspot rendering.

## Omitted / intentionally excluded areas

- Experimental federation and sync surfaces are not diagrammed in v1 because `00-current-state.md` says federation and sync durability are not part of the present release promise.
- Future federation concepts and other future-feature architecture documents are excluded.
- Legacy Threadspace / GuardianOS / installer-era material is excluded.
- UI canon, token, layout, and rendering diagrams are excluded.
- Roadmap-only material and supplementary deep dives are excluded.
- Speculative provider or future architecture details that exceed the validated runtime source set are excluded.

## Diagram quality notes

This is a first-pass runtime baseline intended to be refined after human review. Adjust edge granularity, labels, and scope only when the change can be justified from the validated runtime source set or freshly re-verified current runtime evidence.

## Reviewer guidance

This pack is intended as a baseline runtime map. Resolve disagreements by checking the validated runtime source set first. If a diagram edge cannot be justified from that source set, remove it or downgrade the diagram's confidence. Future diagram variants should branch from this baseline rather than bypassing it.
