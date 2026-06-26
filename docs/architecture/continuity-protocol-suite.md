# Continuity Protocol Suite

> Classification: docs-only architecture contract
> Status: proposed
> Implementation status: no runtime behavior exists
> Normative language: "must", "must not", "should", "non-goal", and "failure policy" are intentional contract terms.

Purpose: Define the first architecture contract for the Continuity Protocol Suite discovered in planning conversation. This is a docs-only contract that introduces a new architecture vocabulary and protocol family. It does not implement runtime behavior, does not widen the supported beta release promise, and does not override `00-current-state.md`.

Last updated: 2026-06-25

## Purpose

### The Problem

Users lose work continuity across deep threads, tabs, projects, providers, browser sessions, coding agents, commits, and partial artifacts. Ordinary memory or RAG is not enough because:

- thread-local continuity exists but does not travel across thread switches
- retrieval widening exists but answers "what is relevant?" not "what is currently true?"
- memory recall surfaces stored facts but not live working context
- imported conversation history carries provenance but not the live mental model the user was operating
- no layer exists that answers "what was I doing, what changed, what is unresolved, and what should I act on next?"

### The Product Thesis

Codexify sells continuity, not model access. Models remain replaceable provider lanes. The product spine is the user's ability to resume work across sessions, projects, threads, and external tools without losing the thread of their own thinking. The Continuity Protocol Suite defines the architecture vocabulary for building that native continuity layer above raw storage and below model inference.

## Non-Goals

This contract does not, and must not be interpreted as, any of the following:

- runtime implementation of any protocol described herein
- a DB schema change, migration, or new table
- a queue or worker behavior change
- a provider-routing change
- graph-write enablement or graph-truth promotion
- browser automation, capture, or integration of any kind
- a cloud continuity service
- encryption or split-trust implementation
- a release support claim or beta surface widening
- an ADR replacement for existing continuity ADRs (ADR-015, ADR-016)
- permission to start implementing without a future ADR
- a substitute for `00-current-state.md` as the short-horizon release-truth authority

## Canonical Terms

The following terms are introduced as architecture vocabulary for the Continuity Protocol Suite. These are candidate terms; any term that becomes a repeated contract-bearing value in future runtime implementation must be promoted to a canonical token before use, consistent with `runtime-protocol-token-contract.md` and `canonical-token-philosophy.md`.

| Term | Meaning |
|---|---|
| `Continuity Protocol Suite` | The family of protocols, contracts, and surfaces that define how Codexify preserves, compiles, and surfaces user work continuity across sessions, projects, threads, tools, and external artifacts |
| `Context Packet` | A self-describing envelope that carries structured evidence from any source surface (browser, thread, project, git, artifact, persona, provider, plugin) into the continuity pipeline |
| `Reality Packet` | A Context Packet whose `kind` is `project_reality` and whose payload represents compiled project-level truth |
| `Continuity Compiler` | The future compilation engine that turns raw evidence packets into compact, confidence-annotated working context; it answers "what matters now" rather than "what is stored" |
| `Reality State` | The compiled truth surface for a given scope; it is a derived product of the Continuity Compiler, not raw storage |
| `Project Reality` | Reality State scoped to a single project; includes active branch, accepted decisions, open loops, rejected paths, active artifacts, and next actions |
| `Thread Reality` | Reality State scoped to a single chat thread |
| `Workspace Reality` | Reality State scoped to the user's local workspace (Obsidian notes, local files, workspace corpus) |
| `Node Reality` | Reality State scoped to a local Codexify node in a federated topology |
| `Reality Commit` | A persisted snapshot of Reality State at a point in time, triggered by user action, semantic delta, heartbeat, or artifact change; distinct from a Git commit |
| `Discovery Commit` | A special Reality Commit created when the user's mental model changes — a new abstraction coined, an assumption overturned, architecture direction shifted, or product thesis sharpened |
| `Project Pulse` | A UI/output surface (not storage) that renders brief answers to "where was I?", daily briefs, recent work, active threads, paused threads, open loops, and suggested resume actions |
| `Resume Packet` | A compiled Context Packet optimized for re-entry — contains exactly enough context to resume work without replaying history |
| `Open Loop` | An unresolved question, decision, task, or exploration that the Continuity Compiler has identified as pending |
| `Rejected Path` | A direction explicitly considered and discarded; preserved to prevent the system and user from accidentally reopening settled questions |
| `Graph Mount` | An optional Neo4j or other graph system that enriches continuity with relationship traversal, visualization, offline analysis, and project map generation; must never be a required runtime dependency for baseline continuity |
| `Browser Context Provider` | A future packet-emitting integration that captures browser context (URL, selected text, page summary, tab binding) without implementing full browser automation |
| `Continuity Cache` | Ephemeral compiled packet reuse for performance; distinct from Reality State, pinned model state, and prompt/KV cache |
| `Pinned Model State` | Ephemeral runtime acceleration (prompt cache, KV cache); a provider/runtime optimization, not durable truth |

## Boundary Model

### Where Continuity Sits

Continuity is a distinct layer in Codexify's architecture stack:

```
┌──────────────────────────────────────┐
│            Model Inference           │  ← replaceable provider lanes
├──────────────────────────────────────┤
│          Continuity Compiler         │  ← compiles evidence into working truth
├──────────────────────────────────────┤
│            Context Broker            │  ← assembles raw evidence for inference
├──────────────────────────────────────┤
│           Reality State              │  ← compiled truth surface (this layer)
│   (Project │ Thread │ Workspace │ Node) │
├──────────────────────────────────────┤
│       Context Packets (envelope)      │  ← shared I/O across all surfaces
├──────────────────────────────────────┤
│  Raw Storage   │   Raw Storage       │  ← Postgres, vector, files, optional graph
│  (messages,    │   (docs, artifacts, │
│   memories,    │    media, imports)  │
│   facts)       │                     │
└──────────────────────────────────────┘
```

### Core Relationships

- **Continuity is above raw storage and below inference.** It does not replace Postgres, Redis, or the vector store. It does not replace the model provider.
- **The Context Broker retrieves evidence; the Continuity Compiler compiles working truth.** These are distinct responsibilities. The broker answers "what evidence is available?" — the compiler answers "what should I carry forward?"
- **Reality State is the compiled truth surface, not a mirror of storage.** It is derived from evidence packets, not from direct DB reads.
- **Project Reality is scoped Reality State.** Different scopes (project, thread, workspace, node) share the same compilation contract but apply different scope boundaries.
- **Browser, Git, thread, artifact, persona, provider, and plugin systems emit packets.** They do not own continuity. The Continuity Compiler owns the compilation pipeline.
- **Optional graph systems enrich continuity but do not own it.** Graph Mounts may provide relationship traversal and visualization but must not be required for baseline continuity operation. The no-graph path must remain fully functional.
- **Pinned model state is ephemeral runtime acceleration, not durable truth.** It is a provider-level optimization (prompt cache, KV cache) and must not be confused with compiled continuity or Reality State.

## Protocol Family

Each row defines a protocol, contract, or surface in the Continuity Protocol Suite. All are proposed; none are implemented.

| Protocol / Contract | Purpose | Scope | Input | Output | Implementation Status | Future Proof Surface |
|---|---|---|---|---|---|---|
| Context Packet Protocol | Define the canonical envelope for evidence passing between all continuity surfaces | All packet-emitting surfaces | Raw context from thread, browser, git, artifact, persona, provider, retrieval, discovery, open loops, rejected paths | Structured `ContextPacket` with provenance, sensitivity, retention, and integrity fields | Not implemented; candidate contract only | Packet schema versioning, canonical token registry for `kind` values |
| Continuity Compiler Contract | Define how raw evidence packets become compact working context | The compilation pipeline between Context Broker and Reality State | Context Packets from all sources, current Reality State snapshot | Compiled Reality State delta, confidence annotations, provenance chain | Not implemented; candidate contract only | Compilation freshness policies, decay models, confidence thresholds |
| Reality State Contract | Define the canonical shape of compiled truth | Project, Thread, Workspace, and Node scopes | Compiled evidence from Continuity Compiler | Structured Reality State with open loops, rejected paths, accepted decisions, next actions | Not implemented; candidate contract only | Schema versioning, scope-specific field extensions, expiry/decay semantics |
| Project Reality Contract | Apply Reality State to project scope with project-specific fields | Single project boundary | Project-scoped Reality State + project metadata and evidence | Project-level compiled truth with goal, active branch, recent changes, active/paused threads | Not implemented; candidate contract only | Project-to-project continuity bridging, federated project reality |
| Reality Commit Protocol | Define when and how Reality State snapshots are persisted | Persistence boundary for compiled truth | Current Reality State, trigger type (manual, semantic-delta, heartbeat, artifact-change, git-adjacent, pause, resume) | Durable Reality Commit with provenance, trigger reason, and delta from prior commit | Not implemented; candidate contract only | Git-backed export, diffable storage, project reality folder |
| Discovery Commit Protocol | Define special Reality Commits created when the user's mental model changes | Epistemic boundary for conceptual shifts | Reality State delta representing mental model change | Discovery Commit with before/after conceptual state, new abstraction, overturned assumption | Not implemented; candidate contract only | Discovery timeline, mental-model versioning, concept graph enrichment |
| Project Pulse Surface | Define the UI/output surface for continuity briefs | UI presentation layer, not storage | Current Project Reality, recent Reality Commits, open loops, active/paused threads | Brief rendering: "where was I?", daily brief, recent work, suggested resume actions | Not implemented; candidate contract only | UI token/layout law compliance, accessibility, diagnostics-boundary enforcement |
| Browser Context Provider | Define browser integration as packet emission, not full automation | Browser-to-Codexify bridge | URL, title, selected text, visible DOM digest, page summary, tab binding, user actions | Browser-scoped Context Packets | Not implemented; candidate contract only | User-visible capture controls, scoped capture policies, per-tab/project binding |
| Resume Engine | Define how the system constructs minimal re-entry context | Re-entry optimization layer | Current Reality State, active scope, recent activity, open loops | Resume Packet with exactly enough context to resume work without replaying history | Not implemented; candidate contract only | Resume quality feedback, user-customizable resume depth |
| Open Loop Engine | Define how unresolved questions, decisions, and tasks are tracked and surfaced | Open-loop lifecycle boundary | Reality State, thread analysis, decision tracking | Identified open loops with priority, age, and blocking relationships | Not implemented; candidate contract only | Open-loop decay, auto-resolution heuristics, cross-project open-loop views |
| Optional Graph Mount | Define Neo4j or other graph systems as optional enrichment mounts | Graph enrichment boundary, not core runtime | Compiled continuity artifacts, packet provenance chains | Relationship traversal, visualization, offline analysis, project map generation | Not implemented; candidate contract only | Mount/unmount lifecycle, pluggable graph backends, graph-optional baseline guarantee |
| Node Sync Protocol | Define how Reality State may be synchronized across federated nodes | Federation boundary within continuity layer | Local Node Reality, peer Node Reality | Synchronized or diffed Node Reality state | Not implemented; candidate contract only | Conflict resolution, merge policies, trust-policy integration |
| Continuity Cache | Define ephemeral compiled packet reuse for performance | Runtime performance boundary | Recently compiled Reality State deltas, active Context Packets | Cache-hit compiled context for fast retrieval; never durable truth | Not implemented; candidate contract only | Cache invalidation policies, cache-size governance, TTL contracts |

## Context Packet Protocol

### Purpose

The Context Packet Protocol defines the canonical envelope for evidence passing between all surfaces that participate in continuity. Every source surface — thread, project, browser, git, artifact, persona, provider, plugin — emits packets through this envelope. The Continuity Compiler consumes packets through this envelope.

This protocol is the shared I/O contract. Without it, every source surface would invent its own shape, making compilation, caching, and provenance tracking impossible.

### Proposed Interface

The following TypeScript-like interface is a candidate contract shape. Field names, types, and constraints are proposals only and must be canonicalized before any runtime implementation.

```ts
interface ContextPacket {
  /** Stable unique identifier for this packet */
  packetId: string;

  /** Schema version for forward compatibility */
  schemaVersion: number;

  /** The kind of packet; determines payload shape and compilation treatment */
  kind: ContextPacketKind;

  /** Scope boundary: project_id, thread_id, workspace_id, or node_id */
  scope: PacketScope;

  /** Which surface emitted this packet */
  source: PacketSource;

  /** When the packet was created */
  createdAt: string; // ISO 8601

  /** Human-readable summary for indexing and brief surfaces */
  summary: string;

  /** The evidence payload; shape depends on `kind` */
  payload: Record<string, unknown>;

  /** Source-specific metadata */
  metadata: PacketMetadata;

  /** Traceable source chain: who emitted, from what upstream artifact, with what confidence */
  provenance: PacketProvenance;

  /** Sensitivity classification for retention, caching, and export behavior */
  sensitivity: PacketSensitivity;

  /** Retention policy: how long this packet remains active before decay */
  retention: PacketRetention;

  /** Content hash or integrity marker for the payload */
  integrity: PacketIntegrity;
}
```

### Permitted Initial Kind Candidates

The following `kind` candidates are proposed for the initial protocol family. These are candidate token domains and must be formalized in a canonical token registry before runtime use.

| Kind | Description | Example Sources |
|---|---|---|
| `thread` | A thread-level continuity event | Chat thread activity, thread summary, decision made in thread |
| `project_reality` | A compiled Project Reality change | Reality Commit, project goal shift, active branch change |
| `browser` | Browser context capture | URL visit, selected text, page summary, tab switch |
| `git` | Git activity context | Commit, branch switch, PR merge, staged changes |
| `artifact` | Generated or uploaded artifact change | Document created, image generated, codex entry saved |
| `persona` | Persona configuration change | Profile switch, persona update, permission change |
| `provider` | Provider lane state change | Model switched, provider degraded, runtime warmup completed |
| `retrieval` | Retrieval evidence packet | Local note match, vector hit, memory recall, workspace evidence |
| `discovery` | Mental model shift | New abstraction coined, assumption overturned, thesis sharpened |
| `open_loop` | Unresolved question or task | Pending decision, incomplete exploration, blocked task |
| `rejected_path` | Direction explicitly discarded | Rejected architecture, abandoned refactor, closed exploration |

### Scope Structure

```ts
interface PacketScope {
  scopeType: "project" | "thread" | "workspace" | "node" | "global";
  projectId?: string;
  threadId?: string;
  workspaceId?: string;
  nodeId?: string;
}
```

### Sensitivity and Retention

Packet sensitivity and retention are candidate policy surfaces. Future implementation must define explicit token domains for sensitivity levels and retention policies before they become runtime-active.

- **Sensitivity** governs whether a packet may be cached, exported, or synced across nodes.
- **Retention** governs how long a packet remains in the active continuity working set before it decays into archival storage.
- The default posture must be conservative: packets are scoped by default, not global; retained by recency and relevance, not indefinitely.

## Continuity Compiler Contract

### Purpose

The Continuity Compiler is the future compilation engine that turns raw evidence (Context Packets) into compact, confidence-annotated working context (Reality State). It sits between the Context Broker and Reality State in the architecture stack.

### Inputs

- Current Reality State snapshot for the target scope
- Incoming Context Packets from all relevant sources
- Decay model for aging evidence
- Compilation policy (depth, budget, freshness requirements)
- User-governed continuity settings (scope, intensity, exclusions) per ADR-016

### Outputs

- Reality State delta (what changed)
- Confidence annotations per compiled assertion
- Provenance chain linking assertions back to source packets
- Explicitly surfaced open loops and rejected paths
- Freshness/recency metadata

### Compilation Goals

The compiler must answer the following questions, not merely assemble raw text:

1. **What matters now?** — The highest-value context for the current working session.
2. **What changed recently?** — Meaningful deltas since the last Reality Commit or session.
3. **What was decided?** — Accepted decisions that should not be casually reopened.
4. **What is unresolved?** — Open loops that need attention.
5. **What should not be reopened casually?** — Rejected paths and settled questions.
6. **What artifacts, files, or threads matter?** — The active working set.
7. **What is the next likely action?** — Suggested resume action based on continuity state.

### Failure Modes

- **Insufficient evidence**: The compiler must report low confidence rather than fabricate assertions.
- **Stale evidence**: Evidence beyond the retention window must be decayed, not silently carried forward.
- **Contradictory packets**: The compiler must surface contradictions rather than silently pick one.
- **Empty scope**: A scope with no evidence must produce a valid but minimal Reality State with explicit "no compiled state" markers.

### Confidence Handling

Every compiled assertion must carry a confidence annotation. The compiler must distinguish:

- **high confidence**: Multiple corroborating packets, recent evidence, explicit user statements.
- **medium confidence**: Single packet, inferred from behavior, moderately aged.
- **low confidence**: Stale evidence, weakly inferred, or single uncorroborated source.
- **explicit**: User-authored Reality Commit or direct statement.

### Provenance Requirements

Every assertion in compiled Reality State must be traceable back to one or more source Context Packets. The provenance chain is essential for:

- user inspection ("why does the system think this?")
- decay decisions ("is this still current?")
- contradiction resolution ("which source is newer or more authoritative?")

### Freshness and Recency

The compiler must apply freshness heuristics:

- Packets within the active session window receive higher weight.
- Packets beyond the retention window are decayed.
- Discovery Commits override older evidence for the concepts they revise.
- User-explicit Reality Commits override compilation-derived assertions.

### Difference from Context Broker

| Aspect | Context Broker | Continuity Compiler |
|---|---|---|
| Question answered | "What evidence is available?" | "What is currently true?" |
| Output | Provider-ready message array | Structured Reality State |
| Lifetime | Per turn | Cross-session, cross-thread |
| Stores | Does not store | Produces Reality State for storage |
| Scope | Turn-scoped, retrieval-policy driven | Scope-scoped, continuity-policy driven |

### Difference from Raw Summarization

The Continuity Compiler is not a summarization engine:

- Summarization condenses text; the compiler extracts structured truth.
- Summarization is lossy language compression; the compiler adds structure, confidence, and provenance.
- Summarization answers "what was said?"; the compiler answers "what is the state of things?"

### Difference from Memory Retrieval

Memory retrieval surfaces stored episodic or semantic facts. The Continuity Compiler surfaces the current working state. Memory answers "what did I store?" — the compiler answers "what should I be working on?"

## Reality State Contract

### Purpose

Reality State is the compiled truth surface for a given scope. It is derived, not raw. It is structured, not conversational. It is confidence-annotated, not assumed.

### Required Conceptual Fields

The following fields are proposed for the Reality State contract. They are not a DB schema; they are a conceptual contract that any future implementation must satisfy.

| Field | Type | Description |
|---|---|---|
| `scope` | `ScopeDescriptor` | The scope this Reality State covers (project, thread, workspace, node) |
| `stateId` | `string` | Stable identifier for this compiled state |
| `schemaVersion` | `number` | Schema version for forward compatibility |
| `compiledAt` | `ISO 8601 string` | When this Reality State was compiled |
| `sourcePacketIds` | `string[]` | IDs of Context Packets that informed this compilation |
| `activeBranch` | `string \| null` | The current working branch of reality (conceptual, not necessarily a Git branch) |
| `acceptedDecisions` | `Decision[]` | Decisions that have been made and should not be casually reopened |
| `openLoops` | `OpenLoop[]` | Unresolved questions, tasks, or explorations |
| `rejectedPaths` | `RejectedPath[]` | Directions explicitly considered and discarded |
| `activeArtifacts` | `ArtifactRef[]` | Artifacts, documents, and threads currently in active use |
| `assumptions` | `Assumption[]` | Working assumptions that reality currently depends on |
| `risks` | `Risk[]` | Identified risks relevant to the current state |
| `nextActions` | `NextAction[]` | Suggested next actions based on continuity analysis |
| `confidence` | `ConfidenceAnnotation` | Overall confidence in this compilation |
| `provenance` | `ProvenanceChain` | Traceable chain back to source packets and prior Reality Commits |
| `expiresOrDecaysAt` | `ISO 8601 string \| null` | When this state should be recompiled or considered stale |

### Decision Shape

```ts
interface Decision {
  decisionId: string;
  summary: string;
  rationale: string;
  decidedAt: string;
  sourcePacketIds: string[];
  confidence: "explicit" | "high" | "medium" | "low";
  revisable: boolean; // whether this decision may be reopened
}
```

### Open Loop Shape

```ts
interface OpenLoop {
  loopId: string;
  summary: string;
  category: "question" | "task" | "decision" | "exploration";
  priority: "blocking" | "high" | "medium" | "low";
  createdAt: string;
  lastTouchedAt: string;
  sourcePacketIds: string[];
  blockingLoops: string[]; // IDs of other open loops that block this one
}
```

### Rejected Path Shape

```ts
interface RejectedPath {
  pathId: string;
  summary: string;
  reason: string;
  rejectedAt: string;
  sourcePacketIds: string[];
  shouldNotReopen: boolean; // true when the path was conclusively rejected
}
```

## Project Reality Contract

### Purpose

Project Reality is Reality State scoped to a single project. It extends the base Reality State contract with project-specific fields.

### Required Fields

In addition to all base Reality State fields, Project Reality must include:

- **current project goal**: The stated objective or purpose of the project as understood at compile time.
- **current working branch of reality**: The conceptual branch — what direction the work is heading, independent of Git branch mechanics.
- **latest meaningful changes**: What changed since the last Reality Commit or session.
- **recent commits or artifacts**: References to recent Git commits, document changes, or artifact generations within the project scope.
- **active threads**: Threads currently in active use.
- **paused threads**: Threads that were active but have been set aside.
- **open loops**: Unresolved project-level questions, tasks, or decisions.
- **rejected paths**: Directions explicitly discarded at the project level.
- **next suggested actions**: What the system suggests the user do next in this project.
- **external evidence references**: Links to relevant external artifacts, urls, or files.
- **confidence and missing-evidence notes**: Where the compilation is uncertain and what additional evidence would improve confidence.

### Relationship to Thread Reality

Project Reality may contain or reference Thread Reality states for threads within the project. Thread Reality is scoped to a single thread's compiled state. Project Reality provides the cross-thread synthesis.

### Relationship to Git

Project Reality is not a Git commit, a Git branch, or a Git log. Git activity may produce Context Packets that inform Project Reality, but the compiler owns the truth surface. A future Git-backed export path may store Reality Commits in a project reality folder within a Git repository, but that storage path does not make the Git commit itself the source of Reality State.

## Reality Commit Protocol

### Purpose

The Reality Commit Protocol defines when and how Reality State snapshots are persisted. A Reality Commit is a durable point-in-time record of compiled truth. It is distinct from a Git commit, distinct from a DB row insert, and distinct from a chat message.

### Triggers

Reality Commits may be triggered by:

| Trigger | Description |
|---|---|
| **Manual trigger** | User explicitly creates a Reality Commit |
| **Semantic-delta trigger** | The Continuity Compiler detects a meaningful change in compiled state |
| **Heartbeat trigger** | Periodic compilation produces a checkpoint Reality Commit |
| **Artifact-change trigger** | A document, codex entry, or generated artifact is created or materially changed |
| **Git-commit-adjacent trigger** | A Git commit occurs and the compiler determines the project reality has meaningfully shifted |
| **Pause-thread trigger** | A thread is paused; the compiler captures the "at-pause" state |
| **Resume-thread trigger** | A thread is resumed; the compiler captures the "at-resume" state against the prior pause state |

### Distinctions

| Concept | What It Is | What It Is Not |
|---|---|---|
| **Reality Commit** | A durable snapshot of compiled Reality State at a point in time | A Git commit, a DB row, or a chat message |
| **Git-backed export** | Future optional storage of Reality Commits in a project reality folder within a Git repo | Live runtime truth or the compiler's working memory |
| **Prompt / KV cache** | Ephemeral runtime acceleration for model inference | Durable continuity or compiled truth |
| **Reality State** | The live compiled truth surface at the current moment | Immutable; it changes as new evidence arrives and compilations run |

## Discovery Commit Protocol

### Purpose

A Discovery Commit is a special category of Reality Commit created when the user's mental model undergoes a conceptual shift. These commits are epistemically significant: they mark moments where the user's understanding changed, not just where artifacts changed.

### When Discovery Commits Occur

Discovery Commits are triggered by conceptual shifts, including:

| Trigger | Example |
|---|---|
| **New abstraction coined** | User names a new concept that did not previously exist in the project vocabulary |
| **Assumption overturned** | A working assumption that the project depended on is proven false |
| **Two concepts merged** | Previously separate ideas are recognized as the same thing |
| **Architecture direction changes** | A decision is made that reorients the project's structural direction |
| **New protocol boundary discovered** | A previously invisible seam between subsystems becomes explicit |
| **Product thesis sharpened** | The project's core purpose or bet is refined |

### Relationship to Reality Commits

Every Discovery Commit is a Reality Commit, but not every Reality Commit is a Discovery Commit. A Discovery Commit must carry additional metadata:

- **before/after conceptual state**: What the user believed before and after the discovery.
- **new abstraction description**: The new concept coined, if applicable.
- **overturned assumption reference**: Which prior assumption was invalidated.
- **confidence**: How certain the discovery is (explicit user statement, strong inference, or tentative).
- **impact radius**: Which other Reality State assertions are affected by this mental model change.

Discovery Commits are the highest-signal input to the Continuity Compiler because they represent ground-truth mental model shifts, not ambient evidence accumulation.

## Project Pulse Surface

### Purpose

Project Pulse is a UI/output surface, not a storage layer. It renders brief, actionable answers derived from Project Reality and recent Reality Commits. It must be user-facing, scannable, and constrained by UI token/layout law.

### Required Brief Surfaces

| Surface | Description |
|---|---|
| **"Where was I?" brief** | The primary resume signal: what the user was working on, which project, which thread, what state things were in |
| **Daily brief** | Summary of recent activity across the project since the last session |
| **Recent work** | List of recent commits, artifact changes, and thread activity |
| **Last commits** | Most recent Reality Commits and/or Git commits within the project scope |
| **Open loops** | Unresolved questions, tasks, and decisions that need attention |
| **Active threads** | Threads currently in use, with brief context |
| **Paused threads** | Threads set aside, with at-pause context and suggested resume action |
| **Suggested resume actions** | What the system recommends the user do next, based on continuity analysis |

### UI Governance

Project Pulse must:

- follow UI token/layout law in any future UI implementation.
- not become a diagnostics leak (raw compilation traces, debug output, or system internals must not render in the user-facing Pulse surface).
- present confidence appropriately: low-confidence suggestions must be visually distinct from high-confidence assertions.
- remain dismissible and user-governed, consistent with ADR-016 continuity governance principles.

### Non-Goals for Project Pulse

Project Pulse is not:

- a system diagnostics dashboard
- a raw Reality State debugger
- a replacement for the thread list or project view
- a mandatory always-on surface

## Browser Context Provider

### Purpose

The Browser Context Provider defines the future integration boundary between the user's browser and Codexify's continuity pipeline. It is a packet emission surface, not a full browser automation engine.

### Proposed Packet Types

| Packet Type | Description | What It Carries |
|---|---|---|
| **URL/title packet** | Current page identity | URL, page title, domain, favicon |
| **Selected text packet** | User-explicit text selection | Selected text, surrounding context, selection timestamp |
| **Visible DOM digest packet** | Lightweight page structure | Visible headings, links, and key content regions |
| **Page summary packet** | AI-generated page synopsis | Summary, topics, key entities (future model-dependent) |
| **Tab/project/thread binding packet** | Which Codexify context this tab relates to | Project ID, thread ID, or "uncategorized" |
| **User action packet** | Browser interaction event | Click, form submit, navigation, bookmark |

### Governance Requirements

Any future browser capture implementation must:

- be user-visible: the user must know when browser context is being captured.
- be scoped: capture policy must be configurable per tab, per project, or disabled entirely.
- respect sensitivity: captured content must follow packet sensitivity and retention policies.
- not be automatic: capture must be opt-in or explicitly triggered, not ambient.
- not implement full browser automation: this provider emits packets; it does not drive the browser.

## Optional Graph Mount

### Purpose

The Optional Graph Mount defines how Neo4j or other graph systems may enrich continuity without becoming a required runtime dependency.

### Enrichment Capabilities

When mounted, a graph system may provide:

| Capability | Description |
|---|---|
| **Relationship traversal** | Navigate connections between packets, threads, artifacts, decisions, and concepts |
| **Visualization** | Graph-based visual representations of project reality, decision trees, and concept maps |
| **Offline analysis** | Batch graph queries for pattern discovery, unused-artifact detection, and relationship mining |
| **Project map generation** | Auto-generated graph-based project structure maps from continuity data |

### Required Invariants

- **Graph mounts must not be required for baseline continuity.** The no-graph path (Postgres-only) must remain fully functional for Reality State compilation, storage, and retrieval.
- **Graph mounts are enrichment only.** They add relationship traversal and visualization. They do not own continuity truth.
- **Mount/unmount must be safe.** Adding or removing a graph mount must not corrupt existing Reality State or Continuity Cache.
- **Graph truth must remain derived.** The graph is a secondary index, not a source of truth. Reality State stored in Postgres is canonical.

This invariant is consistent with ADR-019 (Graph Backend Adapter Contract), ADR-025 (Neo4j Flagged Off By Default), and ADR-026 (Graph Write Runtime Flag Boundary).

## Pinned Model State and Continuity Cache

### Layer Separation

Codexify's architecture must preserve four distinct layers. These layers have different lifetimes, ownership, and truth status, and must never be collapsed:

| Layer | What It Is | Lifetime | Owner | Truth Status |
|---|---|---|---|---|
| **Pinned Model State** | Ephemeral runtime acceleration (prompt cache, KV cache) | Per-session, per-model-load | Provider/runtime | Ephemeral; not durable |
| **Prompt / KV Cache** | Provider-level optimization for repeated prompt prefixes | Per-request, cache-eviction-governed | Provider | Ephemeral; not portable |
| **Continuity Cache** | Compiled packet reuse for performance; avoids re-compiling unchanged evidence | Session-scoped or TTL-governed | Continuity Compiler | Ephemeral acceleration; not durable truth |
| **Reality State** | Durable compiled truth surface | Persisted; expires/decays per policy | Codexify (Postgres) | Durable truth; canonical |

### Invariant

Do not collapse pinned model state, prompt cache, continuity cache, and Reality State into a single concept. They serve different purposes, have different failure modes, and must remain independently governable.

## Storage and Future Implementation Notes

The following notes are non-binding future implementation guidance. They are not implemented by this task and must not be interpreted as current runtime truth.

### Postgres-First for Canonical Records

Reality State, Reality Commits, and Discovery Commits should be stored in Postgres as the primary system of record, consistent with `data-and-storage.md`. The canonical Reality State row should be queryable by scope and compilable from stored Context Packets.

### Optional Git-Backed Export

A future implementation may export Reality Commits as structured files (JSON or Markdown with frontmatter) to a local project reality folder, optionally tracked in Git. This export path is a convenience, not the canonical store.

### Optional Vector Indexes for Packet Retrieval

Context Packets may be indexed in the vector store for semantic retrieval, enabling queries like "find Context Packets related to this decision." This index is a secondary acceleration surface, not canonical storage.

### Optional Graph Mount for Relationship Analysis

As described in the Optional Graph Mount section, Neo4j may enrich continuity with relationship traversal. This mount is optional and must not be required for baseline operation.

### Optional Browser Packet Tables

A future implementation may add Postgres tables for browser-sourced Context Packets with appropriate retention policies. These tables would store packet envelopes, not raw page content.

### Optional Sync Protocol

A future sync protocol may synchronize Reality State across federated Codexify nodes. Any such protocol must respect scope boundaries, sensitivity classifications, and user-governed continuity settings.

## Relationship to Existing Contracts

This contract sits within the existing architecture corpus and relates to the following governing documents:

### `00-current-state.md`

This document is a docs-only architecture contract. It does not widen the release promise, does not claim runtime implementation, and does not override `00-current-state.md` as the short-horizon release-truth authority. If any claim in this document appears to conflict with `00-current-state.md`, `00-current-state.md` wins.

### `chat-runtime-contract.md`

The Continuity Protocol Suite defines a layer above turn-level chat completion. It does not change provider runtime states, request lifecycle states, message-versus-attempt identity, or replay semantics defined in the chat runtime contract. Reality State is cross-turn and cross-session; chat runtime state is per-turn and per-attempt.

### `runtime-protocol-token-contract.md`

All packet `kind` values, Reality State field names, trigger type labels, and confidence levels introduced in this contract are candidate token domains. Before any runtime implementation, they must be promoted to canonical tokens in the protocol token registry per `runtime-protocol-token-contract.md`.

### `canonical-token-philosophy.md`

The terms defined in the Canonical Terms section follow the canonical token philosophy: they carry contract meaning, would be dangerous to rename casually, and must graduate from candidate vocabulary to canonical tokens before runtime use.

### `account-export-restore-contract.md`

Reality State and Reality Commits must be exportable and restorable consistent with the account export contract. Export must preserve provenance chains. Restore must not silently drop compiled truth or collapse Reality Commits into raw message history.

### `router-decision-table.md`

The Continuity Compiler is distinct from the retrieval router. The router decides what evidence to retrieve for a chat turn. The compiler decides what to carry forward from that evidence across sessions. The router operates per-turn; the compiler operates across time.

### `self-extending-agent-plugin-system.md`

Future plugin extensions may emit Context Packets (e.g., a retrieval plugin emitting a retrieval-scoped packet). Plugin-emitted packets must follow the Context Packet Protocol envelope and respect sensitivity, retention, and provenance requirements. Plugins must not own continuity truth.

### `codexify_workspace_surface_spec_v_1.md`

Project Pulse is a future UI surface, not part of the current Workspace (Shelf + Scratchpad + Inspector) spec. If future implementation places Project Pulse within the Workspace shell, it must follow Workspace layout token law, card hierarchy, and view-specific behavior rules.

### ADR-015 and ADR-016

ADR-015 (Continuity Engine Working Set and Decay Contract) and ADR-016 (Continuity Governance Surface Contract) define the user-governed continuity layer above thread-first chat. The Continuity Protocol Suite extends that direction with protocol-level vocabulary, packet envelopes, compilation semantics, Reality State structure, and commit protocols. It does not replace ADR-015 or ADR-016; it provides the layer below the governance surface and above raw storage.

## Required ADR Before Runtime Implementation

Runtime implementation of any protocol, contract, or surface defined in this document requires ADR coverage before:

- adding a DB schema for Reality State, Context Packets, Reality Commits, or Discovery Commits
- adding a packet token registry with canonical `kind`, `scope`, `sensitivity`, or `retention` values
- adding workers for the Continuity Compiler, Open Loop Engine, or Resume Engine
- adding browser capture or Browser Context Provider packet emission
- adding Reality Commit persistence with any of the defined triggers
- adding Git-backed reality storage or project reality folder export
- adding sync behavior for Reality State across nodes
- promoting graph mounts from optional to required for any continuity path
- exposing Project Pulse as a UI surface
- changing provider routing, queue semantics, or worker behavior to support continuity compilation

The pre-implementation ADR must:

- identify which specific protocols or surfaces are being implemented
- define the canonical token registries for all contract-bearing values
- establish the Postgres schema contract for durable Reality State storage
- confirm that graph mounts remain optional and the no-graph path remains fully functional
- confirm that provider/model replaceability is preserved
- confirm that project continuity is separated from persona identity and deep identity consent
- define the proof surface for each implemented protocol
- establish the user governance surface consistent with ADR-016

## Acceptance Checklist

Reviewers must confirm all of the following before accepting this contract:

- [ ] This document is docs-only and introduces no runtime behavior.
- [ ] No release promise has been widened beyond `00-current-state.md`.
- [ ] Graph optionality is preserved; no Neo4j dependency has been introduced for baseline continuity.
- [ ] Provider/model replaceability is preserved; continuity does not depend on any specific model or provider.
- [ ] Project continuity is separated from persona identity; Reality State is not identity.
- [ ] All packet `kind`, protocol, and protocol-family terms are candidate tokens, not runtime-active canonical tokens.
- [ ] Runtime implementation is explicitly deferred pending a future ADR.
- [ ] The boundary model clearly separates storage, retrieval, compilation, and inference layers.
- [ ] The distinction between pinned model state, continuity cache, and Reality State is preserved.
- [ ] Browser capture is defined as packet emission, not full automation, and requires future user-visible controls.
- [ ] No claims are made about sync, cloud continuity services, encryption, or split-trust.
- [ ] Relationship to existing ADRs (ADR-015, ADR-016) and architecture contracts is explicitly stated.
- [ ] `00-current-state.md` remains the short-horizon release-truth authority.
