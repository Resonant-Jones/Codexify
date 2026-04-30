---

tags:

* architecture
* adr
* index
  aliases:
* Architecture Decision Record Index
* ADR Index

---

# ADR Index

## Purpose

This note is the entrypoint into Codexify's Architecture Decision Record set.

These ADRs capture the **why** behind architectural decisions that shape:

* runtime behavior
* retrieval policy
* transcript integrity
* control-plane separation
* observability posture

Use this note as the local map for all ADRs.

---

## Reading Order

1. [[001-Queue-Based-Completion-Acceptance-Model|ADR-001 Queue-Based Completion Acceptance Model]]
2. [[002-Dual-State-Machine-Model|ADR-002 Dual State Machine Model]]
3. [[003-Message-Identity-vs-Request-Identity|ADR-003 Message Identity vs Request Identity]]
4. [[004-Retrieval-Policy-as-Control-Plane|ADR-004 Retrieval Policy as Control Plane]]
5. [[005-Imprint-UI-Deprecation-and-Identity-Ownership|ADR-005 Imprint UI Deprecation and Identity Ownership]]
6. [[006-flow-builder-elicitation-lane|ADR-006 Flow Builder Elicitation Lane]] — upstream spec-building lane for turning tacit expertise into validated workflow structure before execution.
7. [[010-Self-Extending-Agent-Plugin-System|ADR-010 Self-Extending Agent Plugin System]] — bounded self-extending architecture for generated capabilities, plugin forge flow, and sovereignty boundaries.
5. [[005-Runtime-Mode-and-Account-Boundary-Invariants|ADR-005 Runtime Mode and Account Boundary Invariants]]
6. [[005-Imprint-UI-Deprecation-and-Identity-Ownership|ADR-005 Imprint UI Deprecation and Identity Ownership]] — retained as the legacy identity-ownership UI boundary note.
7. [[006-flow-builder-elicitation-lane|ADR-006 Flow Builder Elicitation Lane]] — upstream spec-building lane for turning tacit expertise into validated workflow structure before execution.
8. [[007-Memory-Graph-Derived-Write-Hook|ADR-007 Memory Graph Derived Write Hook]] — derived graph candidate emission after assistant persistence, kept non-blocking and idempotent.
9. [[008-Candidate-Trace-Surface|ADR-008 Candidate Trace Surface]] — backend-only candidate-output diagnostic surface, TTL-bound and excluded from export.
10. [[009-Candidate-Trace-Ingest-Worker|ADR-009 Candidate Trace Ingest Worker Scaffold]] — asynchronous candidate-trace ingestion seam, log-only and non-blocking.
11. [[011-Graph-Write-Task-Seam-and-Worker-Scaffold|ADR-011 Graph Write Task Seam and Worker Scaffold]] — queue-backed graph-write handoff and inspection-only worker scaffold for derived graph candidates.
12. [[012-Post-Completion-Eval-Spine|ADR-012 Post-Completion Eval Spine]] — durable post-completion trace snapshot and attempt-scoped quality verdict seam, inspection-only and non-gating.
13. [[013-Verified-Personal-Facts-Context-Injection|ADR-013 Verified Personal Facts Context Injection]] — backend-only verified personal-facts injection seam, bounded and user-scoped.
14. [[014-Flow-Builder-Thread-Draft-and-Receipts-Contract|ADR-014 Flow Builder Thread, Draft, and Receipts Contract]] — canonical contract for Guardian threads, flow drafts, Builder support lanes, and run receipts.
15. [[015-Continuity-Engine-Working-Set-and-Decay-Contract|ADR-015 Continuity Engine Working Set and Decay Contract]] — user-governed continuity layer above thread-first chat, with working-set decay and provenance.
16. [[016-Continuity-Governance-Surface-Contract|ADR-016 Continuity Governance Surface Contract]] — user-governed continuity control plane for scope, decay, import treatment, exclusions, inspection, and reset semantics.
17. [[017-Graph-Write-Idempotency-and-Receipt-Semantics|ADR-017 Graph Write Idempotency and Receipt Semantics]] — deterministic graph-write identity and ephemeral receipt claims for the inspection-only graph lane.
18. [[018-Graph-Write-Inspection-Surface|ADR-018 Graph Write Inspection Surface]] — latest-per-thread graph-lane inspection snapshots for operator/debug visibility without promoting graph truth.
19. [[019-Graph-Backend-Adapter-Contract|ADR-019 Graph Backend Adapter Contract]] — typed graph backend seam with a default no-op implementation mounted after inspection.
20. [[020-Guardian-Mediated-Coding-Agent-Execution-Contract|ADR-020 Guardian Mediated Coding Agent Execution Contract]] — Guardian-owned contract for coding-agent execution attempts, future Pi SDK adapters, and result ingestion before user-visible output.

---

## Relationship to the main architecture docs

These ADRs sit beside, not above, the main architecture corpus.

Use the broader corpus for:

* current runtime topology
* supported-path truth
* flow sequencing
* storage and invariants
* operational risk

Primary companion notes:

* [[00-current-state]]
* [[system-overview|System Overview]]
* [[flows|Critical Flows]]
* [[completion_pipeline|Completion Request Pipeline]]
* [[chat-runtime-contract|Chat Runtime Contract]]
* [[self-extending-agent-plugin-system|Self-Extending Agent Plugin System]]
* [[router-decision-table|Retrieval Router Decision Table]]
* [[architecture-atlas|Architecture Atlas]]
* [[tech-debt-and-risks|Tech Debt and Risks]]

---

## ADR graph

* [[001-Queue-Based-Completion-Acceptance-Model|ADR-001 Queue-Based Completion Acceptance Model]] links to:

  * [[flows|Critical Flows]]
  * [[completion_pipeline|Completion Request Pipeline]]
  * [[00-current-state]]

* [[002-Dual-State-Machine-Model|ADR-002 Dual State Machine Model]] links to:

  * [[chat-runtime-contract|Chat Runtime Contract]]
  * [[00-current-state]]
  * [[tech-debt-and-risks|Tech Debt and Risks]]

* [[003-Message-Identity-vs-Request-Identity|ADR-003 Message Identity vs Request Identity]] links to:

  * [[chat-runtime-contract|Chat Runtime Contract]]
  * [[completion_pipeline|Completion Request Pipeline]]
  * [[flows|Critical Flows]]

* [[004-Retrieval-Policy-as-Control-Plane|ADR-004 Retrieval Policy as Control Plane]] links to:

  * [[router-decision-table|Retrieval Router Decision Table]]
  * [[flows|Critical Flows]]
  * [[system-overview|System Overview]]
  * [[00-current-state]]

* [[005-Runtime-Mode-and-Account-Boundary-Invariants|ADR-005 Runtime Mode and Account Boundary Invariants]] links to:

  * [[identity-and-runtime-mode|Identity and Runtime Mode]]
  * [[account-export-restore-contract|Account Export + Restore Contract]]
  * [[00-current-state]]

* [[005-Imprint-UI-Deprecation-and-Identity-Ownership|ADR-005 Imprint UI Deprecation and Identity Ownership]] links to:

  * [[system-overview|System Overview]]
  * [[modules-and-ownership|Modules and Ownership]]
  * [[00-current-state]]
  * [[chat-runtime-contract|Chat Runtime Contract]]

* [[006-flow-builder-elicitation-lane|ADR-006 Flow Builder Elicitation Lane]] links to:

  * [[system-overview|System Overview]]
  * [[flows|Critical Flows]]
  * [[chat-runtime-contract|Chat Runtime Contract]]
  * [[router-decision-table|Retrieval Router Decision Table]]
  * [[delegation-runtime|Delegation Runtime Contract]]
  * [[00-current-state]]

* [[007-Memory-Graph-Derived-Write-Hook|ADR-007 Memory Graph Derived Write Hook]] links to:

  * [[router-decision-table|Retrieval Router Decision Table]]
  * [[account-export-restore-contract|Account Export + Restore Contract]]
  * [[flows|Critical Flows]]
  * [[data-and-storage|Data and Storage]]
  * [[00-current-state]]

* [[008-Candidate-Trace-Surface|ADR-008 Candidate Trace Surface]] links to:

  * [[chat-runtime-contract|Chat Runtime Contract]]
  * [[account-export-restore-contract|Account Export + Restore Contract]]
  * [[completion_pipeline|Completion Request Pipeline]]
  * [[data-and-storage|Data and Storage]]
  * [[00-current-state]]

* [[009-Candidate-Trace-Ingest-Worker|ADR-009 Candidate Trace Ingest Worker Scaffold]] links to:

  * [[chat-runtime-contract|Chat Runtime Contract]]
  * [[candidate-trace-surface|Candidate Trace Surface]]
  * [[candidate-ingest-pipeline|Candidate Trace Ingestion Pipeline]]
  * [[data-and-storage|Data and Storage]]
  * [[00-current-state]]

* [[011-Graph-Write-Task-Seam-and-Worker-Scaffold|ADR-011 Graph Write Task Seam and Worker Scaffold]] links to:

  * [[chat-runtime-contract|Chat Runtime Contract]]
  * [[account-export-restore-contract|Account Export + Restore Contract]]
  * [[candidate-ingest-pipeline|Candidate Trace Ingestion Pipeline]]
  * [[memory-graph-indexing-plan|Memory Graph Indexing Plan]]
  * [[data-and-storage|Data and Storage]]
  * [[00-current-state]]

* [[010-Self-Extending-Agent-Plugin-System|ADR-010 Self-Extending Agent Plugin System]] links to:

  * [[system-overview|System Overview]]
  * [[modules-and-ownership|Modules and Ownership]]
  * [[account-export-restore-contract|Account Export + Restore Contract]]
  * [[persona-studio|Persona Studio Architecture]]
  * [[chat-runtime-contract|Chat Runtime Contract]]

* [[013-Verified-Personal-Facts-Context-Injection|ADR-013 Verified Personal Facts Context Injection]] links to:

  * [[router-decision-table|Retrieval Router Decision Table]]
  * [[imprint-ui-deprecation-and-identity-ownership|Imprint UI Deprecation and Identity Ownership]]
  * [[chat-runtime-contract|Chat Runtime Contract]]
  * [[data-and-storage|Data and Storage]]
  * [[flows|Critical Flows]]
  * [[00-current-state]]

* [[014-Flow-Builder-Thread-Draft-and-Receipts-Contract|ADR-014 Flow Builder Thread, Draft, and Receipts Contract]] links to:

  * [[006-flow-builder-elicitation-lane|Flow Builder Elicitation Lane]]
  * [[chat-runtime-contract|Chat Runtime Contract]]
  * [[account-export-restore-contract|Account Export + Restore Contract]]
  * [[data-and-storage|Data and Storage]]
  * [[flows|Critical Flows]]
  * [[system-overview|System Overview]]
  * [[00-current-state]]

* [[015-Continuity-Engine-Working-Set-and-Decay-Contract|ADR-015 Continuity Engine Working Set and Decay Contract]] links to:

  * [[router-decision-table|Retrieval Router Decision Table]]
  * [[chat-runtime-contract|Chat Runtime Contract]]
  * [[account-export-restore-contract|Account Export + Restore Contract]]
  * [[system-overview|System Overview]]
  * [[tech-debt-and-risks|Tech Debt and Risks]]
  * [[00-current-state]]

* [[016-Continuity-Governance-Surface-Contract|ADR-016 Continuity Governance Surface Contract]] links to:

  * [[015-Continuity-Engine-Working-Set-and-Decay-Contract|Continuity Engine Working Set and Decay Contract]]
  * [[account-export-restore-contract|Account Export + Restore Contract]]
  * [[persona-studio|Persona Studio Architecture]]
  * [[system-overview|System Overview]]
  * [[data-and-storage|Data and Storage]]
  * [[tech-debt-and-risks|Tech Debt and Risks]]
  * [[00-current-state]]

* [[017-Graph-Write-Idempotency-and-Receipt-Semantics|ADR-017 Graph Write Idempotency and Receipt Semantics]] links to:

  * [[007-Memory-Graph-Derived-Write-Hook|Memory Graph Derived Write Hook]]
  * [[008-Candidate-Trace-Surface|Candidate Trace Surface]]
  * [[009-Candidate-Trace-Ingest-Worker|Candidate Trace Ingest Worker Scaffold]]
  * [[011-Graph-Write-Task-Seam-and-Worker-Scaffold|Graph Write Task Seam and Worker Scaffold]]
  * [[candidate-ingest-pipeline|Candidate Trace Ingestion Pipeline]]
  * [[memory-graph-indexing-plan|Memory Graph Indexing Plan]]
  * [[account-export-restore-contract|Account Export + Restore Contract]]
  * [[data-and-storage|Data and Storage]]
  * [[00-current-state]]

* [[018-Graph-Write-Inspection-Surface|ADR-018 Graph Write Inspection Surface]] links to:

  * [[011-Graph-Write-Task-Seam-and-Worker-Scaffold|Graph Write Task Seam and Worker Scaffold]]
  * [[017-Graph-Write-Idempotency-and-Receipt-Semantics|Graph Write Idempotency and Receipt Semantics]]
  * [[candidate-ingest-pipeline|Candidate Trace Ingestion Pipeline]]
  * [[memory-graph-indexing-plan|Memory Graph Indexing Plan]]
  * [[data-and-storage|Data and Storage]]
  * [[00-current-state]]

* [[019-Graph-Backend-Adapter-Contract|ADR-019 Graph Backend Adapter Contract]] links to:

  * [[011-Graph-Write-Task-Seam-and-Worker-Scaffold|Graph Write Task Seam and Worker Scaffold]]
  * [[017-Graph-Write-Idempotency-and-Receipt-Semantics|Graph Write Idempotency and Receipt Semantics]]
  * [[018-Graph-Write-Inspection-Surface|Graph Write Inspection Surface]]
  * [[candidate-ingest-pipeline|Candidate Trace Ingestion Pipeline]]
  * [[memory-graph-indexing-plan|Memory Graph Indexing Plan]]

* [[020-Guardian-Mediated-Coding-Agent-Execution-Contract|ADR-020 Guardian Mediated Coding Agent Execution Contract]] links to:

  * [[chat-runtime-contract|Chat Runtime Contract]]
  * [[account-export-restore-contract|Account Export + Restore Contract]]
  * [[self-extending-agent-plugin-system|Self-Extending Agent Plugin System]]
  * [[flows|Critical Flows]]
  * [[data-and-storage|Data and Storage]]
  * [[modules-and-ownership|Modules and Ownership]]
  * [[modules-and-ownership|Modules and Ownership]]
  * [[runtime-protocol-token-contract|Runtime Protocol Token Contract]]
  * [[00-current-state]]
---

## Maintenance rule

When a new architectural decision changes:

* acceptance semantics
* runtime state vocabulary
* retrieval doctrine
* message/attempt identity
* control-plane boundaries

…add a new ADR instead of silently editing history.

If a previous ADR becomes obsolete, supersede it with a new ADR and link both notes.
