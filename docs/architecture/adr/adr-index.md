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
15. [[027-flow-builder-typed-surface-and-run-receipt-contract|ADR-027 Flow Builder Typed Surface and Run Receipt Contract]] — typed vocabulary, validation issue taxonomy, semantic step contract, test/activation distinction, and complete RunReceipt field contract for future implementation planning.
16. [[015-Continuity-Engine-Working-Set-and-Decay-Contract|ADR-015 Continuity Engine Working Set and Decay Contract]] — user-governed continuity layer above thread-first chat, with working-set decay and provenance.
16. [[016-Continuity-Governance-Surface-Contract|ADR-016 Continuity Governance Surface Contract]] — user-governed continuity control plane for scope, decay, import treatment, exclusions, inspection, and reset semantics.
17. [[017-Graph-Write-Idempotency-and-Receipt-Semantics|ADR-017 Graph Write Idempotency and Receipt Semantics]] — deterministic graph-write identity and ephemeral receipt claims for the inspection-only graph lane.
18. [[023-Workspace-E2E-Proof-Harness-Contract|ADR-023 Workspace E2E Proof Harness Contract]] — canonical live-proof harness for the `retrievalSource="workspace"` seam on the supported local Compose path; release-evidence tool only.
19. [[025-neo4j-graph-backend-adapter-flagged-off-by-default|ADR-025 Neo4j Graph Backend Adapter Flagged Off By Default]] — first real graph persistence adapter behind explicit default-off backend selection.
18. [[018-Graph-Write-Inspection-Surface|ADR-018 Graph Write Inspection Surface]] — latest-per-thread graph-lane inspection snapshots for operator/debug visibility without promoting graph truth.
19. [[019-Graph-Backend-Adapter-Contract|ADR-019 Graph Backend Adapter Contract]] — typed graph backend seam with a default no-op implementation mounted after inspection.
20. [[020-Guardian-Mediated-Coding-Agent-Execution-Contract|ADR-020 Guardian Mediated Coding Agent Execution Contract]] — Guardian-owned contract for coding-agent execution attempts, future Pi SDK adapters, and result ingestion before user-visible output.
21. [[021-Web-Agent-Boundary-and-Retrieval-Contract|ADR-021 Web Agent Boundary and Retrieval Contract]] — governed external retrieval and interaction boundary with separate search, read, extract, browser, and service-connector modes.
22. [[022-Guardian-Intent-Spine-and-Cross-Surface-Control-Plane|ADR-022 Guardian Intent Spine and Cross-Surface Control Plane]] — canonical cross-surface intent control plane for chat, voice, automations, CLI, and future plugin surfaces.
23. [[023-workspace-e2e-proof-harness-contract|ADR-023 Workspace E2E Proof Harness Contract]] — canonical live proof harness for the supported local Compose path that validates workspace-scoped Obsidian-backed note retrieval end to end.
24. [[024-Context-Command-and-Active-Connector-Semantics|ADR-024 Context Command and Active Connector Semantics]] — governing ADR for Context Commands, active connector semantics, slash-command connector invocation, and connector/tool boundary doctrine.
24. [[025-workspace-obsidian-selection-and-injection-contract|ADR-024 Workspace Obsidian Selection and Injection Contract]] — canonical contract for truthfully distinguishing workspace-local searchability, broker selection, completion-context injection, and assistant reflection for Obsidian-backed notes.
25. [[026-graph-write-runtime-flag-boundary-on-supported-compose-path|ADR-026 Graph Write Runtime Flag Boundary on Supported Compose Path]] — repairs the default-off graph-write runtime boundary on the supported Docker Compose path so documented contract matches enforced behavior.
26. [[028-execution-ledger-campaign-runner-contract|ADR-028 Execution Ledger Campaign Runner Contract]] — defines Execution Ledger as a governed Campaign Runner extension over goals, campaigns, work orders, attempts, and Guardian-owned lineage/evidence seams.
27. [[029-codex-entry-command-first-draft-flow|ADR-029 Codex Entry Command-First Draft Flow]] — chat-native `/codex_entry` slash command that generates transient draft cards from prior context with Save/Download/Dismiss actions, reusing the existing codex save seam and enforcing default retrieval exclusion.

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


* [[027-flow-builder-typed-surface-and-run-receipt-contract|ADR-027 Flow Builder Typed Surface and Run Receipt Contract]] links to:


  * [[006-flow-builder-elicitation-lane|Flow Builder Elicitation Lane]]
  * [[014-Flow-Builder-Thread-Draft-and-Receipts-Contract|Flow Builder Thread, Draft, and Receipts Contract]]
  * [[flow-builder-surface-research-application|Flow Builder Surface Research Application]]
  * [[runtime-protocol-token-contract|Runtime Protocol Token Contract]]
  * [[canonical-token-philosophy|Canonical Token Philosophy]]
  * [[agent-tool-loop-contract|Agent Tool Loop Contract]]
  * [[self-extending-agent-plugin-system|Self-Extending Agent Plugin System]]
  * [[account-export-restore-contract|Account Export + Restore Contract]]
  * [[flows|Critical Flows]]
  * [[data-and-storage|Data and Storage]]
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

* [[023-Workspace-E2E-Proof-Harness-Contract|ADR-023 Workspace E2E Proof Harness Contract]] links to:

  * [[016-workspace-retrieval-source-for-local-knowledge|ADR-016 Workspace Retrieval Source for Local Knowledge]]
  * [[001-Queue-Based-Completion-Acceptance-Model|ADR-001 Queue-Based Completion Acceptance Model]]
  * [[flows|Critical Flows]]
  * [[config-and-ops|Config and Ops]]
  * [[00-current-state]]
  * [[scripts/proofs/README.md Proof Harness README]]

* [[025-neo4j-graph-backend-adapter-flagged-off-by-default|ADR-025 Neo4j Graph Backend Adapter Flagged Off By Default]] links to:

  * [[007-Memory-Graph-Derived-Write-Hook|Memory Graph Derived Write Hook]]
  * [[011-Graph-Write-Task-Seam-and-Worker-Scaffold|Graph Write Task Seam and Worker Scaffold]]
  * [[017-Graph-Write-Idempotency-and-Receipt-Semantics|Graph Write Idempotency and Receipt Semantics]]
  * [[candidate-ingest-pipeline|Candidate Trace Ingestion Pipeline]]
  * [[memory-graph-indexing-plan|Memory Graph Indexing Plan]]
  * [[config-and-ops|Config and Ops]]
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

* [[021-Web-Agent-Boundary-and-Retrieval-Contract|ADR-021 Web Agent Boundary and Retrieval Contract]] links to:

  * [[web-agent-spec|Web Agent Spec v1]]
  * [[router-decision-table|Retrieval Router Decision Table]]
  * [[config-and-ops|Config and Ops]]
  * [[runtime-protocol-token-contract|Runtime Protocol Token Contract]]
  * [[canonical-token-philosophy|Canonical Token Philosophy]]
  * [[account-export-restore-contract|Account Export + Restore Contract]]
  * [[self-extending-agent-plugin-system|Self-Extending Agent Plugin System]]

* [[022-Guardian-Intent-Spine-and-Cross-Surface-Control-Plane|ADR-022 Guardian Intent Spine and Cross-Surface Control Plane]] links to:

  * [[003-Message-Identity-vs-Request-Identity|Message Identity vs Request Identity]]
  * [[010-Self-Extending-Agent-Plugin-System|Self-Extending Agent Plugin System]]
  * [[014-Flow-Builder-Thread-Draft-and-Receipts-Contract|Flow Builder Thread, Draft, and Receipts Contract]]
  * [[020-Guardian-Mediated-Coding-Agent-Execution-Contract|Guardian Mediated Coding Agent Execution Contract]]
  * [[021-Web-Agent-Boundary-and-Retrieval-Contract|Web Agent Boundary and Retrieval Contract]]
  * [[00-current-state]]
  * [[system-overview|System Overview]]
  * [[flows|Critical Flows]]
  * [[command-bus-auth-cli-automations|Command Bus, Auth, Tool Calls, and Automations]]
  * [[delegation-runtime|Delegation Runtime Contract]]
  * [[persona-studio|Persona Studio Architecture]]

* [[024-Context-Command-and-Active-Connector-Semantics|ADR-024 Context Command and Active Connector Semantics]] links to:

  * [[022-Guardian-Intent-Spine-and-Cross-Surface-Control-Plane|Guardian Intent Spine and Cross-Surface Control Plane]]
  * [[021-Web-Agent-Boundary-and-Retrieval-Contract|Web Agent Boundary and Retrieval Contract]]
  * [[010-Self-Extending-Agent-Plugin-System|Self-Extending Agent Plugin System]]
  * [[runtime-protocol-token-contract|Runtime Protocol Token Contract]]
  * [[chat-runtime-contract|Chat Runtime Contract]]
  * [[router-decision-table|Retrieval Router Decision Table]]
  * [[flows|Critical Flows]]
  * [[config-and-ops|Config and Ops]]

* [[026-graph-write-runtime-flag-boundary-on-supported-compose-path|ADR-026 Graph Write Runtime Flag Boundary on Supported Compose Path]] links to:

  * [[019-Graph-Backend-Adapter-Contract|Graph Backend Adapter Contract]]
  * [[011-Graph-Write-Task-Seam-and-Worker-Scaffold|Graph Write Task Seam and Worker Scaffold]]
  * [[017-Graph-Write-Idempotency-and-Receipt-Semantics|Graph Write Idempotency and Receipt Semantics]]
  * [[018-Graph-Write-Inspection-Surface|Graph Write Inspection Surface]]
  * [[candidate-ingest-pipeline|Candidate Trace Ingestion Pipeline]]
  * [[memory-graph-indexing-plan|Memory Graph Indexing Plan]]
  * [[data-and-storage|Data and Storage]]
  * [[config-and-ops|Config and Ops]]
  * [[00-current-state]]

* [[028-execution-ledger-campaign-runner-contract|ADR-028 Execution Ledger Campaign Runner Contract]] links to:

  * [[001-Queue-Based-Completion-Acceptance-Model|ADR-001 Queue-Based Completion Acceptance Model]]
  * [[002-Dual-State-Machine-Model|ADR-002 Dual State Machine Model]]
  * [[006-flow-builder-elicitation-lane|ADR-006 Flow Builder Elicitation Lane]]
  * [[014-Flow-Builder-Thread-Draft-and-Receipts-Contract|ADR-014 Flow Builder Thread, Draft, and Receipts Contract]]
  * [[020-Guardian-Mediated-Coding-Agent-Execution-Contract|ADR-020 Guardian Mediated Coding Agent Execution Contract]]
  * [[022-Guardian-Intent-Spine-and-Cross-Surface-Control-Plane|ADR-022 Guardian Intent Spine and Cross-Surface Control Plane]]
  * [[024-Context-Command-and-Active-Connector-Semantics|ADR-024 Context Command and Active Connector Semantics]]
  * [[027-flow-builder-typed-surface-and-run-receipt-contract|ADR-027 Flow Builder Typed Surface and Run Receipt Contract]]
  * [[execution-ledger-phase-1-repo-aware-recon|Execution Ledger Phase 1 Repo-Aware Recon]]
  * [[runtime-protocol-token-contract|Runtime Protocol Token Contract]]
  * [[chat-runtime-contract|Chat Runtime Contract]]
  * [[account-export-restore-contract|Account Export + Restore Contract]]
  * [[self-extending-agent-plugin-system|Self-Extending Agent Plugin System]]
  * [[flows|Critical Flows]]
  * [[data-and-storage|Data and Storage]]
  * [[00-current-state]]

* [[029-codex-entry-command-first-draft-flow|ADR-029 Codex Entry Command-First Draft Flow]] links to:

  * [[001-Queue-Based-Completion-Acceptance-Model|ADR-001 Queue-Based Completion Acceptance Model]]
  * [[022-Guardian-Intent-Spine-and-Cross-Surface-Control-Plane|ADR-022 Guardian Intent Spine and Cross-Surface Control Plane]]
  * [[account-export-restore-contract|Account Export + Restore Contract]]
  * [[chat-runtime-contract|Chat Runtime Contract]]
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
