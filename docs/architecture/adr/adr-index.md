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
28. [[030-continuity-protocol-suite-runtime-gate|ADR-030 Continuity Protocol Suite Runtime Gate]] — runtime gate for the Continuity Protocol Suite; requires ADR-gated implementation with token-domain review, storage review, provenance review, identity review, and graph-optionality verification before any runtime behavior lands. Docs-only; does not implement runtime behavior.
29. [[031-continuity-phase-a-storage-migration-gate|ADR-031 Continuity Phase A Storage Migration Gate]] — migration gate for Phase A continuity storage; gates Alembic/SQLAlchemy work behind explicit proof requirements (clean-start, existing-instance upgrade, downgrade, graph-off baseline, token constraint alignment, provenance preservation, and runtime write gate). Accepts four-phase-A-table boundary; defers Phase B normalization. Docs-only; does not implement migrations, models, or runtime writes.
30. [[036-campaign-runner-provider-adapter-contract|ADR-036 Campaign Runner Provider Adapter Contract]] — defines provider-adapter boundaries for Campaign Runner and forbids direct Codex/Claude dependency coupling in this module.
31. [[037-campaign-runner-pi-provider-broker|ADR-037 Campaign Runner Pi Provider Broker]] — defines Pi as the preferred lightweight provider-broker seam for Campaign Runner when available.
32. [[038-Chat-Transport-Visibility-and-Adaptive-Stream-Recovery-Contract|ADR-038 Chat Transport Visibility and Adaptive Stream Recovery Contract]] — docs-only third-plane contract for stalled-stream interpretation, observation-only recovery, and transcript-safe boundaries.
33. [[039-capability-oriented-mesh-architecture|ADR-039 Capability-Oriented Mesh Architecture]] — foundational mesh principle for exposing capabilities rather than machines; separates trust from tailnet/subnet membership, keeps customer access at governed edge boundaries, and treats Tailscale, Headscale, LAN, HTTPS, queues, and future mechanisms as transport implementations beneath capability authorization.

---

## Relationship to the main architecture docs

These ADRs sit beside, not above, the main architecture corpus.

Use the broader corpus for:

* system maps
* runtime contracts
* API-level specifications
* implementation guides
