Purpose: define Guardian's future retrieval navigation doctrine as a planning-only layer that learns where relevant meaning tends to live before broader retrieval. This note does not describe current runtime support and does not widen the supported beta promise.
Last updated: 2026-05-21
Source anchors:
- docs/architecture/00-current-state.md
- docs/architecture/router-decision-table.md
- docs/architecture/system-overview.md
- docs/architecture/flows.md
- docs/iddb_policy_v1.md
- docs/architecture/data-and-storage.md
- docs/architecture/self-extending-agent-plugin-system.md
- guardian/context/broker.py
- guardian/core/chat_completion_service.py

# Guardian Retrieval Navigation Model

## Status

- This note is planning-only architecture doctrine.
- It is not a shipped runtime surface.
- It does not enable graph writes, adaptive mutation, runtime route priors, or retrieval-router execution changes.
- No new ADR is required for this docs-only note.
- Governing ADRs in the current index are:
  - Retrieval policy:
    - `ADR-004 Retrieval Policy as Control Plane`
  - Continuity governance:
    - `ADR-015 Continuity Engine Working Set and Decay Contract`
    - `ADR-016 Continuity Governance Surface Contract`
  - Identity boundaries:
    - `ADR-005 Runtime Mode and Account Boundary Invariants`
    - `ADR-005 Imprint UI Deprecation and Identity Ownership`
  - Graph-write boundaries:
    - `ADR-007 Memory Graph Derived Write Hook`
    - `ADR-011 Graph Write Task Seam and Worker Scaffold`
    - `ADR-017 Graph Write Idempotency and Receipt Semantics`
    - `ADR-018 Graph Write Inspection Surface`
    - `ADR-019 Graph Backend Adapter Contract`
    - `ADR-025 Neo4j Graph Backend Adapter Flagged Off By Default`
    - `ADR-026 Graph Write Runtime Flag Boundary on Supported Compose Path`
  - Connector/context command semantics:
    - `ADR-024 Context Command and Active Connector Semantics`
  - Self-extending and retrieval-plugin governance:
    - `ADR-010 Self-Extending Agent Plugin System`
    - `ADR-021 Web Agent Boundary and Retrieval Contract`
- Brief reason:
  - This task does not change accepted runtime architecture.
  - It documents a future retrieval-navigation doctrine that must remain aligned with existing retrieval, continuity, graph-write, connector, identity, and sovereignty boundaries.
  - Any later implementation that changes live retrieval behavior, graph writes, identity modeling, canonical tokens, or proof surfaces must be a separate architecture-impact task and may require an ADR update or a new ADR.

## Purpose

Guardian should learn where relevant context tends to live before it reads deeply, widens broadly, or treats full-vault ingestion as the default answer.

This doctrine favors navigation over indiscriminate ingestion. The goal is to guide retrieval toward likely evidence lanes across threads, projects, documents, artifacts, memories, and proof surfaces while keeping the system bounded, inspectable, provenance-backed, and user-owned.

## Core Thesis

Guardian should learn where meaning lives before it tries to read everything.

## Problem Statement

Full-vault ingestion and flat semantic search are weak defaults for large, evolving workspaces. They spend budget early, blur source priority, and can over-read noisy or weakly relevant material before Guardian has established where the best evidence is likely to live.

For Codexify's local-first runtime, routing should happen before expensive retrieval. Guardian needs a future doctrine for choosing bounded starting points, probing for evidence quality, and expanding only when the first pass is insufficient.

## Relationship to Current Runtime

Current runtime seams already exist:

- `ContextBroker` is the context and retrieval orchestration seam.
- Semantic retrieval, document context, memory retrieval, and optional graph context are existing assembly lanes.
- The retrieval-router doctrine is the correct policy seam that sits before `ContextBroker` assembly.
- The retrieval-router decision table remains doctrine plus scaffold and does not itself claim live behavior changes.
- Chat completion and workspace-local retrieval have proof surfaces, while debug traces remain diagnostic-only unless explicitly documented otherwise.
- Graph writes remain default-off on the supported Compose path.

This note does not change runtime behavior. It documents a future layer that should sit before `ContextBroker` assembly and inform bounded source selection without turning advisory navigation metadata into canonical truth.

## Model Layers

### User Expectation Model

This future layer captures operational preferences and retrieval expectations only:

- prefers thread-first answers
- expects provenance when claims are important
- wants local-only scope unless broadening is explicit
- tolerates shallow probe first, then expansion if needed

It must not become hidden identity inference. It is not a license to derive durable sensitive traits, deep identity labels, or persona-owned identity state.

### Project / World Model

This future layer represents the user's active working world:

- current project boundaries
- thread and artifact adjacency
- document families and proof surfaces
- known local corpora such as workspace, documents, and memories
- explicit continuity or governance settings when applicable

It describes where relevant evidence is likely to be, not who the user is.

### Retrieval Navigation Model

This future layer uses expectation and world cues to propose bounded navigation priors:

- likely starting lanes
- likely bridge surfaces
- likely noisy hubs to avoid
- probe order
- expansion order
- provenance expectations

Its outputs are route hints and relationship traces, not canonical facts and not autonomous execution authority.

## Proposed Non-Runtime Contracts

The following shapes are proposed future contracts only. They are conceptual, not implemented, and not canonical token commitments.

```ts
type RetrievalAttemptRecord = {
  attempt_id: string
  user_id: string
  thread_id: string
  project_id?: string
  source_message_id?: string
  intent_class: string
  source_mode: string
  initial_scope: "conversation" | "local" | "bounded_expansion"
  selected_sources: string[]
  probe_sources: string[]
  expansion_applied: boolean
  outcome: "sufficient" | "insufficient_evidence" | "wrong_scope" | "noisy_result" | "user_corrected"
  provenance_chain_found: boolean
  notes?: string[]
  recorded_at: string
}

type RetrievalRouteHint = {
  hint_id: string
  owner_scope: {
    user_id: string
    project_id?: string
    thread_id?: string
  }
  hint_kind: "start_here" | "prefer_after_probe" | "avoid_as_noisy" | "bridge_candidate"
  target_surface: "thread" | "project_docs" | "thread_docs" | "workspace" | "memory" | "proof_surface" | "graph_enrichment"
  confidence: number
  reason: string
  supporting_attempt_ids: string[]
  advisory_only: true
  expires_at?: string
}

type RelationshipTrace = {
  trace_id: string
  owner_scope: {
    user_id: string
    project_id?: string
  }
  source_surface: string
  target_surface: string
  bridge_type: "same_project" | "same_artifact_family" | "same_proof_lineage" | "same_thread" | "derived_link"
  provenance_refs: string[]
  confidence: number
  review_status: "unreviewed" | "accepted_for_hinting" | "rejected"
  recorded_at: string
}

type GraphEvolutionProposal = {
  proposal_id: string
  owner_scope: {
    user_id: string
    project_id?: string
  }
  basis_attempt_ids: string[]
  proposed_changes: Array<{
    operation: "add_edge" | "reweight_edge" | "deprecate_edge"
    source_ref: string
    target_ref: string
    reason: string
  }>
  provenance_refs: string[]
  review_required: true
  reversible: true
  canonical_applied: false
  created_at: string
}
```

## Retrieval Flow Doctrine

Future retrieval-navigation flow:

1. request
2. intent classification
3. expectation and navigation hints
4. bounded source selection
5. probe
6. expand only if needed
7. retrieve
8. verify evidence
9. record attempt outcome

The navigation layer should bias toward bounded routing, probing, and expansion rather than defaulting to full-vault ingestion.

## Learning Signals

Possible future learning signals include:

- insufficient evidence
- wrong scope
- user correction
- repeated missing bridge
- noisy source or hub
- successful source selection
- provenance chain found

These signals should shape future route hints only within governed boundaries and with inspectable provenance.

## Governance and Identity Boundaries

This doctrine must stay aligned with [IDDB Policy v1](./iddb_policy_v1.md).

- Learning retrieval preferences is allowed only as operational preference modeling.
- Chat history remains diary content by default, not durable identity truth.
- Durable identity modeling remains governed and opt-in where applicable.
- Personas may borrow identity context within governed boundaries, but they do not own identity.
- Route hints are advisory navigation metadata, not canonical truth and not durable trait inference.
- Sensitive trait inference must not be smuggled in through retrieval metadata, route priors, or relationship traces.

## Graph Evolution Boundary

Future graph-evolution work must begin as reviewable proposals, not automatic canonical graph mutation.

If retrieval navigation produces evidence that a relationship should exist, that evidence should first become a bounded, provenance-backed, reversible proposal. It must not directly mutate canonical graph topology.

Graph writes remain default-off unless a separate governed runtime task changes that supported-path boundary.

## Phased Introduction

### Phase 0: docs-only doctrine

Document the doctrine, scope, and governance boundaries without changing runtime behavior.

### Phase 1: retrieval attempt logging

Introduce bounded attempt records so future implementation can measure which starting lanes succeed or fail.

### Phase 2: retrieval route hints

Introduce advisory route hints that can bias bounded source selection without becoming canonical truth.

### Phase 3: relationship traces

Introduce provenance-backed traces that explain why certain surfaces appear adjacent or bridged during retrieval.

### Phase 4: reviewable graph-evolution proposals

Introduce proposal artifacts for candidate graph changes without enabling automatic canonical mutation.

### Phase 5: narrow automated updates only for low-risk, high-confidence cases after explicit governance

Any narrow automation must come after explicit governance, bounded risk classification, reversibility, and supported-path proof.

## Proof Surface

For this task, proof is documentation validation only.

For any future implementation, proof must include:

- runtime tests
- trace evidence
- identity-boundary tests
- supported-path proof

Future proof must distinguish route hints, relationship traces, and graph-evolution proposals from shipped runtime truth until each surface is separately implemented and proven.

## Non-Goals

- No runtime behavior changes
- No full-vault ingestion
- No automatic graph mutation
- No deep identity inference
- No new release promise
- No UI or diagnostics surface in this task

## Open Questions

- Should route hints persist only per user, or also per project and per thread?
- What review UX should govern graph-evolution proposals before any canonical write is even considered?
- How should graph-patch governance classify low-risk versus prohibited proposals?
- What decay or staleness rules should retire route hints and relationship traces when workspace topology changes?
- If hints or traces ever become durable, should they be included in export and restore by default or only by explicit opt-in?
- Which proof surface should own truth for future retrieval-navigation outcomes: worker-visible attempt records, durable trace artifacts, or a dedicated inspection surface?
