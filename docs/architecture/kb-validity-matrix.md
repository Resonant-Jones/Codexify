# KB Validity Matrix

## Purpose

- This file classifies the Codexify documentation corpus before architecture diagram generation.
- It separates current runtime truth from design canon, roadmap/speculation, and legacy identity drift.

## Interpretation Rules

- For short-horizon operational truth, `00-current-state.md` wins.
- For current runtime topology, prefer the architecture KB set updated in March 2026.
- Older deep dives may be referenced only when explicitly marked supplementary.
- Legacy Threadspace / `guardian-backend_v2` documents are not valid runtime diagram inputs.

## Classification Legend

- `authoritative_now`: current runtime or KB routing truth for March 2026; safe to treat as present-state evidence within the file's stated scope.
- `supplementary_verify_against_code`: useful context, but verify against current code and the March 2026 KB set before using it.
- `design_canon_not_runtime_truth`: valid for UI or conceptual diagrams, not for first-pass current runtime topology.
- `historical_archive`: retained for history only; do not use as a first-pass architecture diagram source.
- `misleading_identity_drift`: legacy material likely to confuse current product identity, supported install path, or present runtime behavior; quarantine it from first-pass diagramming.

## Audit Matrix

Audit notes:

- Actual repo paths are listed below when the requested shorthand path points to a file stored elsewhere in this repo.
- Not present at audit time: `/docs/architecture/RELEASE.md`, `/Thread-Artifact-Lineage.md`.

| path | domain | status | safe_for_runtime_diagrams | safe_for_ui_diagrams | reason | recommended_action |
|---|---|---|---|---|---|---|
| `/docs/architecture/00-current-state.md` | release / operational truth | `authoritative_now` | yes | no | Explicitly declares itself the canonical short-form source of truth for release readiness, supported install path, and active blockers. | Read first and let it override older or broader docs on short-horizon reality. |
| `/docs/architecture/README.md` | KB routing | `authoritative_now` | yes | no | Current KB entrypoint updated in March 2026 and aligned to the current architecture set. | Use as the routing layer after reading this matrix. |
| `/docs/architecture/system-overview.md` | runtime topology | `authoritative_now` | yes | no | Explicitly frames itself as current runtime architecture and topology, with March 2026 source anchors. | Use as the base node-and-boundary source for runtime diagrams. |
| `/docs/architecture/flows.md` | runtime flows | `authoritative_now` | yes | no | Documents implemented trigger-to-output flows with concrete route, worker, and queue anchors. | Use for sequence and flow diagrams after `system-overview.md`. |
| `/docs/architecture/data-and-storage.md` | persistence and invariants | `authoritative_now` | yes | no | Maps current storage systems, entities, and invariants used by the runtime. | Use for data-store, entity, and persistence-boundary diagrams. |
| `/docs/architecture/config-and-ops.md` | runtime config and operator truth | `authoritative_now` | yes | no | Updated March 2026 and scoped to current config precedence, health surfaces, worker dependencies, and supported run paths. | Use to constrain deployment/runtime diagrams to supported paths. |
| `/docs/architecture/modules-and-ownership.md` | subsystem map | `authoritative_now` | yes | no | Describes current subsystem seams and dependency edges with explicit code anchors. | Use for component maps and ownership overlays. |
| `/docs/architecture/roadmap-signals.md` | planning guidance | `supplementary_verify_against_code` | no | no | The file explicitly surfaces planning signals, refactor leverage, and sequencing suggestions rather than present-state topology. | Use only for future-state annotations after the current runtime diagram is complete. |
| `/docs/architecture/tech-debt-and-risks.md` | current risk register | `authoritative_now` | no | no | March 2026 evidence-backed risk register is current, but it is not a topology source. | Use after baseline diagramming to annotate risk hotspots or release caveats. |
| `/docs/architecture/completion_pipeline.md` | older completion deep dive | `supplementary_verify_against_code` | no | no | Useful runtime detail, but it is an older deep dive and the KB entrypoint already warns to verify it against current routes/workers. | Use only as a secondary detail source after `flows.md` and code verification. |
| `/docs/architecture/providers.md` | provider notes | `supplementary_verify_against_code` | no | no | Provider behavior can drift from catalog/router/runtime truth; this file is narrower than the March 2026 operator docs. | Verify against current provider registry, catalog, health, and code before using it. |
| `/docs/architecture/guardian-agent-delegation-recon.md` | delegation planning recon | `supplementary_verify_against_code` | no | no | Explicit planning/recon document mixing `Verified`, `Inference`, and missing-doc notes rather than canonical runtime topology. | Use only for future delegation planning, not first-pass runtime diagramming. |
| `/docs/architecture/solo-operator-runtime-bootcamp.md` | operational runbook | `supplementary_verify_against_code` | no | no | Practical operator training guide, not a runtime architecture source. | Use for operator onboarding only. |
| `/docs/dev/ARTIFACT1—UI-Token-Constitution.md` | UI token canon | `design_canon_not_runtime_truth` | no | yes | Canonical token law for visual language and component styling, not backend/runtime topology. | Use for UI styling diagrams only. |
| `/docs/dev/ARTIFACT1B—CODEXIFY-STRUCTURAL-LAYOUT-SPECIFICATION.md` | UI layout canon | `design_canon_not_runtime_truth` | no | yes | Canonical layout skeleton for screens and containers, not implemented backend topology. | Use for page/layout diagrams only. |
| `/docs/dev/ARTIFACT3—Codexify-UI-Rendering-Protocol.md` | UI rendering canon | `design_canon_not_runtime_truth` | no | yes | Canonical rendering rules for tokens and components; not a runtime systems map. | Use for UI component/rendering diagrams only. |
| `/docs/dev/ARTIFACT4—COGNITIVE-DIAGNOSTICS-CANON.md` | diagnostics UI canon | `design_canon_not_runtime_truth` | no | yes | Canonical placement and behavior rules for diagnostics surfaces; not runtime topology truth. | Use for diagnostics UI diagrams only. |
| `/docs/dev/ARTIFACT7--CODEXIFY-PERCEPTUAL-STACK-SPEC.md` | perceptual/cognitive canon | `design_canon_not_runtime_truth` | no | yes | Canonical conceptual stack for perception and diagnostics; useful for conceptual or UI-adjacent diagrams, not current runtime topology. | Use only for conceptual or UI-facing cognitive diagrams. |
| `/docs/Codexify/Codexify-System-Specification.md` | extracted system spec | `design_canon_not_runtime_truth` | no | no | 2025 extracted spec mixes implemented and aspirational capabilities, providers, and modules. | Use only for explicitly labeled conceptual or future-state diagrams, never as runtime truth. |
| `/docs/Future-Features/federation_manifest.md` | federation concept | `design_canon_not_runtime_truth` | no | no | Future-facing node architecture and sync design, not part of the current release promise. | Use only for conceptual federation diagrams after the current runtime baseline is drawn. |
| `/docs/Future-Features/Event_Graph.md` | event-graph concept | `design_canon_not_runtime_truth` | no | no | Conceptual spec for a future event graph and agent playbook system. | Use only for future-state conceptual diagrams. |
| `/docs/Future-Features/federated_diff_sync.md` | distributed sync concept | `design_canon_not_runtime_truth` | no | no | Future-facing CRDT-inspired diff sync design, not current implemented topology. | Use only for future sync design work. |
| `/docs/infra/persona_system_architecture.md` | legacy persona architecture | `historical_archive` | no | no | Mermaid architecture references older Rust/Tauri persona flows and does not define the March 2026 runtime. | Retain for history only; do not use for first-pass diagrams. |
| `/docs/infra/system_architecture.md` | legacy system overview | `misleading_identity_drift` | no | no | Presents GuardianOS, thread manager, plugin system, and agent topology as if current; conflicts with the March 2026 KB. | Quarantine from diagram generation. |
| `/docs/infra/context-report.md` | generated 2025 snapshot | `historical_archive` | no | no | Dated context dump with mixed legacy paths and tool output, not a maintained KB source. | Use only as historical audit evidence. |
| `/docs/infra/sync-contract.md` | extracted sync contract | `design_canon_not_runtime_truth` | no | no | Minimal contract note is insufficient to stand in for the current runtime sync implementation. | Use only when drafting future sync protocol docs. |
| `/docs/guardian/iddb_policy_v1.md` | identity data policy | `design_canon_not_runtime_truth` | no | no | Policy/design contract for identity handling, not a description of current runtime topology. | Use only for conceptual identity/privacy diagrams or policy discussions. |
| `/docs/infra/system_integrity_ledger.md` | historical audit ledger | `historical_archive` | no | no | Dated integrity ledger and action items are historical and not maintained as runtime truth. | Retain only as historical context. |
| `/SECURITY.md` | current security posture overview | `supplementary_verify_against_code` | no | no | Useful current security narrative, but it includes planned enhancements and is not a topology source. | Use only for security overlays after code and KB verification. |
| `/docs/Codexify/SECURITY.md` | legacy security policy | `historical_archive` | no | no | External program/version policy doc is not tied to the March 2026 runtime KB. | Do not use for architecture diagram generation. |
| `/docs/Codexify/INSTALLER.md` | legacy install/distribution path | `misleading_identity_drift` | no | no | Describes bundled installer and wheel/Ollama packaging that conflicts with the current supported Docker Compose install path. | Quarantine from current runtime/source-set work. |
| `/docs/infra/INTERNAL_DOCS.md` | legacy internal architecture | `misleading_identity_drift` | no | no | Presents GuardianOS, plugin-system, and meta-cognition topology that conflicts with the March 2026 runtime docs. | Quarantine from first-pass diagramming. |
| `/README.md` | repo entrypoint | `supplementary_verify_against_code` | no | no | Useful current onboarding overview, but the March 2026 architecture KB is the more precise diagram source set. | Use for repo orientation only; defer diagram work to the KB matrix and runtime source set. |
| `/docs/Codexify/README.md` | legacy README | `misleading_identity_drift` | no | no | Starts with `guardian-backend_v2` and describes an obsolete GuardianOS-style architecture and install path. | Quarantine from first-pass diagramming. |

## Required Judgments

- The March 2026 architecture KB set is treated as `authoritative_now`, except where the file explicitly frames itself as planning-only. In this audit, that exception is `/docs/architecture/roadmap-signals.md`.
- `/docs/architecture/completion_pipeline.md` and `/docs/architecture/providers.md` are `supplementary_verify_against_code`.
- The UI token, layout, rendering, diagnostics, and perceptual canons under `/docs/dev/ARTIFACT*.md` are `design_canon_not_runtime_truth`. They can inform UI diagrams, but they must not be treated as current backend/runtime topology without verification.
- Docs that still present `Threadspace`, `guardian-backend_v2`, GuardianOS/plugin-system topology, or obsolete packaged-installer assumptions are classified as `historical_archive` or `misleading_identity_drift` based on how likely they are to confuse present product identity, supported install path, or current runtime behavior.
- `misleading_identity_drift` is used when a file could actively confuse current product identity, supported install path, or present runtime behavior. `historical_archive` is used when a file is primarily dated context rather than an active identity hazard.

## Diagram Source Sets

### Runtime Diagram Source Set v1

- `/docs/architecture/00-current-state.md`
- `/docs/architecture/README.md`
- `/docs/architecture/system-overview.md`
- `/docs/architecture/flows.md`
- `/docs/architecture/data-and-storage.md`
- `/docs/architecture/config-and-ops.md`
- `/docs/architecture/modules-and-ownership.md`

### UI Diagram Source Set v1

- `/docs/dev/ARTIFACT1—UI-Token-Constitution.md`
- `/docs/dev/ARTIFACT1B—CODEXIFY-STRUCTURAL-LAYOUT-SPECIFICATION.md`
- `/docs/dev/ARTIFACT3—Codexify-UI-Rendering-Protocol.md`
- `/docs/dev/ARTIFACT4—COGNITIVE-DIAGNOSTICS-CANON.md`
- `/docs/dev/ARTIFACT7--CODEXIFY-PERCEPTUAL-STACK-SPEC.md`

### Quarantined From First-Pass Diagramming

- `/docs/Codexify/README.md`
- `/docs/Codexify/INSTALLER.md`
- `/docs/infra/INTERNAL_DOCS.md`
- `/docs/infra/system_architecture.md`
- `/docs/infra/persona_system_architecture.md`
- `/docs/Codexify/SECURITY.md`
- `/docs/infra/context-report.md`
- `/docs/infra/system_integrity_ledger.md`
