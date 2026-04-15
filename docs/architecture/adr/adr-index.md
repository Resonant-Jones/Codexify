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
