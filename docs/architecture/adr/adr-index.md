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
7. [[007-Memory-Graph-Derived-Write-Hook|ADR-007 Memory Graph Derived Write Hook]] — derived graph candidate emission after assistant persistence, kept non-blocking and idempotent.

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
