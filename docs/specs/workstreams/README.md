# Codexify Workstreams

Status: Future-facing specification seed

Last updated: 2026-07-27

## Purpose

This directory preserves the emerging Workstream concept for later architecture review without claiming that Workstreams are implemented, accepted architecture, or part of the supported release.

A Workstream is envisioned as a durable coordination and observation layer that binds a continuing objective to its related conversations, context sources, work orders, execution attempts, artifacts, evidence, decisions, collaborators, and unresolved state.

The concept generalizes patterns already present in Campaign Runner, Execution Ledger, Guardian-mediated delegation, evidence packets, chat lineage, retrieval policy, and Continuity direction. It must extend those rails rather than create a parallel control plane or duplicate canonical truth.

## Current truth

What is true now:

- Campaign Runner can turn an operator-authored intention into repository-grounded audits, campaigns, and bounded task artifacts.
- Execution Ledger architecture defines campaigns, coding work orders, execution attempts, review gates, acceptance criteria, evidence, and completion receipts as governed concepts.
- Guardian owns command authority, execution policy, result return, and lineage boundaries.
- Pi invocation envelope, receipt, artifact, harness-result, and validation contracts exist as backend-only contract surfaces.
- A development-tooling Pi-to-DeepSeek delegation skill exists outside the Codexify runtime for bounded read-only analysis under Codex supervision.

What is not yet true:

- No canonical Workstream runtime entity or projection exists.
- No continuous cross-source observer or deterministic Workstream state reducer exists.
- No Workstream retrieval source or attention policy exists.
- No live Guardian-mediated Pi SDK invocation exists.
- No complete supported-path delegation loop from authored Codexify intent through Codex or Pi execution, durable result return, validation, reinjection, and operator-visible proof has been demonstrated.
- No autonomous dispatch, merge automation, or continuous hands-free progression is authorized.

## Working definition

A Workstream is a durable, policy-bounded coordination object that answers:

- What continuing objective are we pursuing?
- Which people, agents, conversations, documents, repositories, tasks, attempts, and evidence belong to it?
- What is currently true, contradicted, stale, blocked, or unresolved?
- What actions are permitted, proposed, executing, or awaiting review?
- Which acceptance criteria have durable proof?

A Workstream does not replace threads, messages, requests, tasks, attempts, campaigns, projects, retrieval policy, the command bus, Continuity, or release-truth documentation.

## Conceptual placement

```text
Workspace / Project
└── Workstream
    ├── Threads and authored messages
    ├── Campaigns and work orders
    ├── Requests, tasks, runs, and attempts
    ├── Documents and external context references
    ├── Decisions and acceptance criteria
    ├── Artifacts, receipts, and evidence
    └── Derived current state and unresolved attention
```

## Architectural relationship

### Campaign Runner

Campaign Runner is a specialized repository-focused planning compiler:

```text
operator intention
→ repository audit
→ evidence-grounded findings
→ campaigns
→ atomic task artifacts
```

A Workstream would remain present across planning, execution, validation, revision, waiting, and completion. Campaign Runner may eventually create or shape Workstreams, but generated planning artifacts must not become execution authority or runtime proof.

### Execution Ledger

Execution Ledger supplies much of the likely implementation spine:

- campaign goals and campaigns as durable planning containers
- coding work orders as atomic implementation units
- execution attempts as distinct from authored work
- review gates and acceptance criteria
- completion receipts and durable attempt evidence

Workstreams should compose or project these existing entities instead of creating duplicate task truth.

### Chat and retrieval

Threads remain canonical conversation containers. A Workstream may relate multiple threads to one continuing objective.

A future Workstream retrieval posture may sit between thread and broader project or workspace retrieval, but widening must remain policy-controlled and evidence-aware. A Workstream must not become an unbounded transcript bucket.

### Continuity

Continuity governs longitudinal relevance across the user's world. A Workstream governs coherent progress toward one bounded continuing objective. Continuity may track which Workstreams matter, while Workstreams expose their present truth, evidence, and unresolved state.

### Delegation

Agents and humans may participate in a Workstream, but execution remains bounded by Guardian policy, command-bus authority, invocation envelopes, provider governance, and explicit review gates.

A Workstream description cannot grant authority by prompt text alone.

## The dreaming-giant model

A mature Workstream is not required to execute continuously. It continuously preserves and re-evaluates coherence as authorized data arrives.

```text
new message
new commit
new document
new task event
human decision
runtime receipt
elapsed time
contradictory evidence
        │
        ▼
 deterministic observation and reduction
        │
        ▼
updated truth, relevance, blockers, and proposed attention
```

Watching, waiting, and consolidation are meaningful states. Visible activity is not required for continuity.

## Candidate capability stages

1. Read-only Workstream projection over existing Campaign Runner and Execution Ledger records.
2. Explicit links to threads, documents, collaborators, artifacts, and evidence.
3. Normalized event intake from Codexify runtime and reviewed external connectors.
4. Deterministic state reduction, contradiction detection, supersession, and temporal decay.
5. Policy-governed attention and wake behavior.
6. Reviewable action proposals.
7. Bounded execution only after the underlying delegation loop is proven end to end.

## Prerequisite proof gate

Workstream execution must not become a priority until Codexify demonstrates at least one complete delegation loop on a declared supported or explicitly experimental path:

1. A user-authored Codexify request is durably persisted with source thread and message lineage.
2. Guardian resolves policy and creates a bounded work order or invocation envelope.
3. The request is accepted without collapsing acceptance into completion.
4. Codex or a Pi-like harness executes through the governed adapter or worker lane.
5. A durable artifact and receipt return with attempt identity and permission posture.
6. Guardian validates the result and preserves requested-versus-granted authority.
7. The result returns through a governed continuation or reinjection path.
8. The operator can inspect terminal status, artifact lineage, validation evidence, and failure classification.
9. The proof demonstrates that no autonomous recursion, command-bus bypass, hidden state mutation, or release-claim widening occurred.

Until this gate passes, Workstreams remain specification and architecture-discovery material only.

## Invariants

- No parallel canonical task or execution truth surface.
- No prompt-only authority or orchestration control plane.
- No acceptance/completion collapse.
- No event-publication/UI-receipt collapse.
- No artifact/proof collapse.
- No autonomous recursive execution by implication.
- No hidden context widening.
- No durable identity inference from work behavior.
- No release-promise widening from specification text.
- No ADR status until a concrete decision changes accepted architecture.

## ADR posture

Classification: No ADR impact yet.

Reason: this directory records a future concept and its prerequisites. It makes no accepted architectural decision, changes no runtime behavior, adds no canonical tokens, and authorizes no implementation.

A future ADR will be required before introducing a canonical Workstream entity, state reducer, retrieval posture, continuous observer, attention policy, or autonomous progression semantics.

## Revisit trigger

Revisit this specification after a single complete Guardian-mediated delegation loop to Codex or Pi has been runtime-proven with durable lineage, receipts, validation, result return, and operator-visible evidence.
