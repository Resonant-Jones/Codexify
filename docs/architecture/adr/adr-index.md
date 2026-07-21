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
33. [[039-operator-user-access-boundary|ADR-039 Operator / User Access Boundary]] — docs-only proposed boundary separating infrastructure operator authority from product user experience without implementing roles, hosted access, or release-support changes.
34. [[040-network-profile-topology-resolution-contract|ADR-040 Network Profile Topology Resolution Contract]] — docs-only proposed topology profile contract for explicit operator-controlled access profiles without implementing settings, routing, provider, Vite, or hosted-support changes.
35. [[041-vaultnode-canonical-machine-and-audit-authority|ADR-041 VaultNode Canonical Machine and Audit Authority]] — governing decision for VaultNode canonical runtime and audit authority, noncanonical machine evidence, trusted `latest`, evidence promotion rights, and persistent-serving/audit isolation.
36. [[042-canonical-audit-evidence-contract|ADR-042 Canonical Audit Evidence Contract]] — governing decision for canonical audit manifests, orthogonal proof classifications, artifact integrity, freshness, supersession, contradiction, and trusted `latest` eligibility.
37. [[043-contact-and-circle-storage-model|ADR-043 Contact and Circle Storage Model]] — governs future storage posture for Contacts and Circles as account-scoped, exportable, private-by-default relationship state, with sync deferred behind a future ADR.
38. [[044-invite-lifecycle-and-storage-model|ADR-044 Invite Lifecycle and Storage Model]] — governs future invite lifecycle, invite storage posture, token boundary, invite-to-contact mapping, and invite-to-permission bridge for Contacts, Circles, and future Spaces.
39. [[045-space-participant-resolution-model|ADR-045 Space Participant Resolution Model]] — governs future Space participant resolution, roster semantics, participant source mapping, role/capability posture, mixed-trust handling, and bounded presence for Contacts, Circles, accepted Invites, local accounts, remote nodes, and AI-mediated actors.
40. [[046-axis-node-portable-reasoning-interface-contract|ADR-046 Axis Node Portable Reasoning Interface Contract]] — docs/context contract for portable, source-governed Axis reasoning without implementing a runtime agent or widening release support.
41. [[047-codexify-email-routing-identity-mailbox-governance-provider-adapter-contract|ADR-047 Codexify Email User-Owned Routing Identity, Mailbox Governance, and Provider Adapter Contract]] — accepted governing boundary for human-owned routing identities, logical mailboxes, collaborator consent, provider adapters, immutable approval, idempotency, reconciliation, and durable receipts without implementing Email runtime support.
42. [[ADR-048-guardian-three-channel-delegation-topology|ADR-048 Guardian Three-Channel Delegation Topology]] — accepted architecture record establishing Pi, Codex, and Claude as peer execution systems under Guardian without changing current runtime behavior or release claims.

---

## ADR Graph

- [[039-operator-user-access-boundary|ADR-039 Operator / User Access Boundary]]
  - Governs future role language for operator/user topology, self-operator and host-operator access postures, and authority-safe Settings/onboarding work.
  - Current-truth and related anchors: [[../00-current-state|00 Current State]], [[../system-overview|System Overview]], [[../config-and-ops|Config and Ops]], [[../modules-and-ownership|Modules and Ownership]], [[../account-export-restore-contract|Account Export Restore Contract]], [[../persona-studio-spec|Persona Studio Spec]], and [[040-network-profile-topology-resolution-contract|ADR-040 Network Profile Topology Resolution Contract]].
- [[040-network-profile-topology-resolution-contract|ADR-040 Network Profile Topology Resolution Contract]]
  - Governs future explicit Network Profile topology records, active profile resolution, operator-visible switching doctrine, and provider-capability-aware profile health surfaces.
  - Current-truth and related anchors: [[../00-current-state|00 Current State]], [[../config-and-ops|Config and Ops]], [[../system-overview|System Overview]], [[../modules-and-ownership|Modules and Ownership]], [[../runtime-protocol-token-contract|Runtime Protocol Token Contract]], [[../canonical-token-philosophy|Canonical Token Philosophy]], [[../tech-debt-and-risks|Tech Debt and Risks]], and [[039-operator-user-access-boundary|ADR-039 Operator / User Access Boundary]].
- [[041-vaultnode-canonical-machine-and-audit-authority|ADR-041 VaultNode Canonical Machine and Audit Authority]]
  - Governs VaultNode canonical runtime and audit authority, noncanonical machine evidence, trusted `latest`, evidence promotion rights, and separation between persistent serving and clean audit runtimes.
  - Companion contract: [[../vaultnode-canonical-machine-and-audit-authority-contract|VaultNode Canonical Machine and Audit Authority Contract]].
- [[042-canonical-audit-evidence-contract|ADR-042 Canonical Audit Evidence Contract]]
  - Governs canonical audit evidence manifests, independent authority/proof/freshness/disposition/execution axes, artifact integrity, claim lineage, supersession, contradiction, and trusted `latest` eligibility.
  - Governing authority: [[041-vaultnode-canonical-machine-and-audit-authority|ADR-041 VaultNode Canonical Machine and Audit Authority]].
  - Companion contract: [[../canonical-audit-evidence-contract|Canonical Audit Evidence Contract]].
- [[043-contact-and-circle-storage-model|ADR-043 Contact and Circle Storage Model]]
  - Governs future storage posture for Contacts and Circles as account-scoped, exportable, private-by-default relationship state, with sync deferred behind a future ADR.
  - Related anchors: [[../contacts-circles-and-collaboration-identity|Contacts, Circles, and Collaboration Identity Contract]], [[../account-export-restore-contract|Account Export Restore Contract]], [[../data-and-storage|Data and Storage]], and [[../00-current-state|00 Current State]].
- [[044-invite-lifecycle-and-storage-model|ADR-044 Invite Lifecycle and Storage Model]]
  - Governs future invite lifecycle, invite storage posture, token boundary, invite-to-contact mapping, and invite-to-permission bridge for Contacts, Circles, and future Spaces.
  - Related anchors: [[../contacts-circles-and-collaboration-identity|Contacts, Circles, and Collaboration Identity Contract]], [[../adr/043-contact-and-circle-storage-model|ADR-043 Contact and Circle Storage Model]], [[../account-export-restore-contract|Account Export Restore Contract]], [[../data-and-storage|Data and Storage]], and [[../00-current-state|00 Current State]].
- [[045-space-participant-resolution-model|ADR-045 Space Participant Resolution Model]]
  - Governs future Space participant resolution, roster semantics, participant source mapping, role/capability posture, mixed-trust handling, and bounded presence for Contacts, Circles, accepted Invites, local accounts, remote nodes, and AI-mediated actors.
  - Related anchors: [[../contacts-circles-and-collaboration-identity|Contacts, Circles, and Collaboration Identity Contract]], [[../adr/043-contact-and-circle-storage-model|ADR-043 Contact and Circle Storage Model]], [[../adr/044-invite-lifecycle-and-storage-model|ADR-044 Invite Lifecycle and Storage Model]], [[../account-export-restore-contract|Account Export Restore Contract]], [[../data-and-storage|Data and Storage]], and [[../00-current-state|00 Current State]].
- [[046-axis-node-portable-reasoning-interface-contract|ADR-046 Axis Node Portable Reasoning Interface Contract]]
  - Governs the docs-only Axis role/node/instance/harness distinction, source authority, human approval boundary, and future runtime integration gate.
  - Related anchors: [[../00-current-state|00 Current State]], [[../agent-protocol-operations|Agent Protocol Operations Index]], [[../guardian-role-and-delegation-boundary|Guardian Role and Delegation Boundary]], [[020-guardian-mediated-coding-agent-execution-contract|ADR-020 Guardian Mediated Coding Agent Execution Contract]], and [[../pi-invocation-boundary-contract|Pi Invocation Boundary Contract]].
- [[047-codexify-email-routing-identity-mailbox-governance-provider-adapter-contract|ADR-047 Codexify Email User-Owned Routing Identity, Mailbox Governance, and Provider Adapter Contract]]
  - Governs the human-account authority, user-owned routing identity, logical mailbox, collaborator consent, provider adapter, secret custody, untrusted-content, immutable approval, idempotency, reconciliation, and durable receipt boundaries required before Codexify Email implementation.
  - Related anchors: [[../00-current-state|00 Current State]], [[../../Campaign/codexify-email-agent-native-campaign-index|Codexify Email Agent-Native Campaign Index]], [[../inspections/codexify-email-implementation-targets|Codexify Email Implementation-Target Inspection]], [[../account-export-restore-contract|Account Export Restore Contract]], [[001-Queue-Based-Completion-Acceptance-Model|ADR-001 Queue-Based Completion Acceptance Model]], [[003-Message-Identity-vs-Request-Identity|ADR-003 Message Identity vs Request Identity]], and [[004-Retrieval-Policy-as-Control-Plane|ADR-004 Retrieval Policy as Control Plane]].
- [[ADR-048-guardian-three-channel-delegation-topology|ADR-048 Guardian Three-Channel Delegation Topology]]
  - Governs the accepted peer topology for the Pi, Codex, and Claude execution channels under Guardian, including Task Spec boundaries, result normalization, execution-system/model identity separation, migration posture, and current-release truth.
  - Related anchors: [[../00-current-state|00 Current State]], [[../guardian-build-loop-doctrine|Guardian Build Loop Doctrine]], [[../pi-invocation-boundary-contract|Pi Invocation Boundary Contract]], [[../delegation-runtime|Delegation Runtime Contract]], [[../delegation-operator-manual|Delegation Operator Manual]], and [[020-guardian-mediated-coding-agent-execution-contract|ADR-020 Guardian Mediated Coding Agent Execution Contract]].

## Relationship to the main architecture docs

These ADRs sit beside, not above, the main architecture corpus.

Use the broader corpus for:

* system maps
* runtime contracts
* API-level specifications
* implementation guides
