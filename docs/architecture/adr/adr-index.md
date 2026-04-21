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
6. [[005-Flow-Builder-Elicitation-Lane|ADR-006 Flow Builder Elicitation Lane]] — upstream spec-building lane for turning tacit expertise into validated workflow structure before execution.
7. [[010-Self-Extending-Agent-Plugin-System|ADR-010 Self-Extending Agent Plugin System]] — bounded self-extending architecture for generated capabilities, plugin forge flow, and sovereignty boundaries.
5. [[005-Runtime-Mode-and-Account-Boundary-Invariants|ADR-005 Runtime Mode and Account Boundary Invariants]]
6. [[005-Imprint-UI-Deprecation-and-Identity-Ownership|ADR-005 Imprint UI Deprecation and Identity Ownership]] — retained as the legacy identity-ownership UI boundary note.
7. [[005-Flow-Builder-Elicitation-Lane|ADR-006 Flow Builder Elicitation Lane]] — upstream spec-building lane for turning tacit expertise into validated workflow structure before execution.
8. [[007-Memory-Graph-Derived-Write-Hook|ADR-007 Memory Graph Derived Write Hook]] — derived graph candidate emission after assistant persistence, kept non-blocking and idempotent.
9. [[008-Candidate-Trace-Surface|ADR-008 Candidate Trace Surface]] — backend-only candidate-output diagnostic surface, TTL-bound and excluded from export.
10. [[009-Candidate-Trace-Ingest-Worker|ADR-009 Candidate Trace Ingest Worker Scaffold]] — asynchronous candidate-trace ingestion seam, log-only and non-blocking.

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

* [[005-Flow-Builder-Elicitation-Lane|ADR-006 Flow Builder Elicitation Lane]] links to:

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

* [[010-Self-Extending-Agent-Plugin-System|ADR-010 Self-Extending Agent Plugin System]] links to:

  * [[system-overview|System Overview]]
  * [[modules-and-ownership|Modules and Ownership]]
  * [[account-export-restore-contract|Account Export + Restore Contract]]
  * [[persona-studio|Persona Studio Architecture]]
  * [[chat-runtime-contract|Chat Runtime Contract]]
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
