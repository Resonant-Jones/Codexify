# KB Validity Matrix

## Purpose

- Classify the architecture documentation corpus before diagram generation or planning reuse.
- Separate current runtime truth from supplemental deep dives, design canon, and legacy identity drift.

## Interpretation Rules

- For short-horizon operational truth, `00-current-state.md` wins.
- For first-pass runtime diagrams, use only the validated runtime diagram source set.
- Older deep dives may be referenced only when explicitly marked supplementary and verified against code.
- UI canon documents are design canon only; they are not backend runtime truth.
- Docs that still name Threadspace, `guardian-backend_v2`, GuardianOS, or bundled installer assumptions are quarantine-only and are not valid first-pass runtime inputs.

## Classification Legend

- `authoritative_now`: current runtime or KB routing truth for March 2026; safe to treat as present-state evidence within the file's stated scope.
- `supplementary_verify_against_code`: useful context, but verify against current code and the March 2026 KB set before using it.
- `design_canon_not_runtime_truth`: valid for UI or conceptual diagrams, not for first-pass current runtime topology.
- `historical_archive`: retained for history only; do not use as a first-pass architecture diagram source.
- `misleading_identity_drift`: legacy material likely to confuse current product identity, supported install path, or present runtime behavior; quarantine it from first-pass diagramming.

## Audit Matrix

Audit notes:

- Actual repo paths are listed below when the requested shorthand path points to a file stored elsewhere in this repo.

| path | domain | status | safe_for_runtime_diagrams | safe_for_ui_diagrams | reason | recommended_action |
|---|---|---|---|---|---|---|
| `/docs/architecture/00-current-state.md` | release / operational truth | `authoritative_now` | yes | no | Canonical short-form source of truth for release readiness, supported install path, and active blockers. | Read first and let it override older or broader docs on short-horizon reality. |
| `/docs/architecture/README.md` | KB routing | `authoritative_now` | yes | no | Current KB entrypoint and routing layer for the validated architecture docs. | Use as the routing layer after reading this matrix. |
| `/docs/architecture/system-overview.md` | runtime topology | `authoritative_now` | yes | no | Current runtime architecture and topology with March 2026 source anchors. | Use as the base node-and-boundary source for runtime diagrams. |
| `/docs/architecture/flows.md` | runtime flows | `authoritative_now` | yes | no | Implemented trigger-to-output flows with concrete route, worker, and queue anchors. | Use for sequence and flow diagrams after `system-overview.md`. |
| `/docs/architecture/data-and-storage.md` | persistence and invariants | `authoritative_now` | yes | no | Current storage systems, entities, and invariants used by the runtime. | Use for data-store, entity, and persistence-boundary diagrams. |
| `/docs/architecture/config-and-ops.md` | runtime config and operator truth | `authoritative_now` | yes | no | Current config precedence, health surfaces, worker dependencies, and supported run paths. | Use to constrain deployment/runtime diagrams to supported paths. |
| `/docs/architecture/modules-and-ownership.md` | subsystem map | `authoritative_now` | yes | no | Current subsystem seams and dependency edges with explicit code anchors. | Use for component maps and ownership overlays. |
| `/docs/architecture/tech-debt-and-risks.md` | current risk register | `authoritative_now` | no | no | Evidence-backed risk register for current architectural risk, not a topology source. | Use after baseline diagramming to annotate risk hotspots or release caveats. |
| `/docs/architecture/roadmap-signals.md` | planning guidance | `supplementary_verify_against_code` | no | no | Planning signals, refactor leverage, and sequencing guidance rather than present-state topology. | Use only for future-state annotations after the current runtime diagram is complete. |
| `/docs/architecture/completion_pipeline.md` | older completion deep dive | `supplementary_verify_against_code` | no | no | Useful runtime detail, but it is an older deep dive and must be verified against current routes/workers. | Use only as a secondary detail source after `flows.md` and code verification. |
| `/docs/architecture/providers.md` | provider notes | `supplementary_verify_against_code` | no | no | Provider behavior can drift from catalog/router/runtime truth. | Verify against current provider registry, catalog, health, and code before using it. |
| `/docs/architecture/guardian-agent-delegation-recon.md` | delegation planning recon | `supplementary_verify_against_code` | no | no | Planning/recon document with mixed verification levels, not canonical runtime topology. | Use only for future delegation planning, not first-pass runtime diagramming. |
| `/docs/architecture/solo-operator-runtime-bootcamp.md` | operational runbook | `supplementary_verify_against_code` | no | no | Practical operator training guide, not a runtime architecture source. | Use for operator onboarding only. |
| `/docs/dev/ARTIFACT1—UI-Token-Constitution.md` | UI token canon | `design_canon_not_runtime_truth` | no | yes | Canonical token law for visual language and component styling, not backend/runtime topology. | Use for UI styling diagrams only. |
| `/docs/dev/ARTIFACT1B—CODEXIFY-STRUCTURAL-LAYOUT-SPECIFICATION.md` | UI layout canon | `design_canon_not_runtime_truth` | no | yes | Canonical layout skeleton for screens and containers, not implemented backend topology. | Use for page/layout diagrams only. |
| `/docs/dev/ARTIFACT3—Codexify-UI-Rendering-Protocol.md` | UI rendering canon | `design_canon_not_runtime_truth` | no | yes | Canonical rendering rules for tokens and components; not a runtime systems map. | Use for UI component/rendering diagrams only. |
| `/docs/dev/ARTIFACT4—COGNITIVE-DIAGNOSTICS-CANON.md` | diagnostics UI canon | `design_canon_not_runtime_truth` | no | yes | Canonical placement and behavior rules for diagnostics surfaces; not runtime topology truth. | Use for diagnostics UI diagrams only. |
| `/docs/dev/ARTIFACT7--CODEXIFY-PERCEPTUAL-STACK-SPEC.md` | perceptual / cognitive canon | `design_canon_not_runtime_truth` | no | yes | Canonical conceptual stack for perception and diagnostics; useful for UI-facing diagrams, not current runtime topology. | Use only for conceptual or UI-facing cognitive diagrams. |
| `/docs/Codexify/README.md` | legacy README | `misleading_identity_drift` | no | no | Starts with `guardian-backend_v2` and describes an obsolete GuardianOS-style architecture and install path. | Quarantine from first-pass diagramming. |
| `/docs/Codexify/THREADSPACE_SYSTEM_MAP.md` | legacy system map | `misleading_identity_drift` | no | no | Threadspace / Guardian-Core / plugin-system narrative conflicts with the March 2026 runtime topology. | Quarantine from first-pass diagramming. |
| `/docs/Codexify/INSTALLER.md` | legacy install/distribution path | `misleading_identity_drift` | no | no | Bundled installer and wheel/Ollama packaging conflict with the current supported Docker Compose install path. | Quarantine from current runtime/source-set work. |
| `/docs/Codexify/SECURITY.md` | legacy security policy | `historical_archive` | no | no | Legacy external program/version policy doc is not tied to the March 2026 runtime KB. | Do not use for architecture diagram generation. |
| `/docs/infra/INTERNAL_DOCS.md` | legacy internal architecture | `misleading_identity_drift` | no | no | Presents GuardianOS, plugin-system, and meta-cognition topology that conflicts with the March 2026 runtime docs. | Quarantine from first-pass diagramming. |
| `/docs/infra/system_architecture.md` | legacy system overview | `misleading_identity_drift` | no | no | Presents GuardianOS, thread manager, and plugin-system topology as if current. | Quarantine from first-pass diagramming. |
| `/docs/infra/persona_system_architecture.md` | legacy persona architecture | `historical_archive` | no | no | Older persona / Tauri flow material; retained for history only. | Retain for history only; do not use for first-pass diagrams. |
| `/docs/infra/context-report.md` | generated 2025 snapshot | `historical_archive` | no | no | Dated context dump with mixed legacy paths and tool output, not a maintained KB source. | Use only as historical audit evidence. |
| `/docs/infra/system_integrity_ledger.md` | historical audit ledger | `historical_archive` | no | no | Dated integrity ledger and action items are historical and not maintained as runtime truth. | Retain only as historical context. |

## Required Judgments

- The March 2026 architecture KB set is the runtime truth layer for this baseline. The runtime source set is the narrow diagram input set.
- `/docs/architecture/completion_pipeline.md` and `/docs/architecture/providers.md` are `supplementary_verify_against_code`.
- The five `/docs/dev/ARTIFACT*.md` UI canon documents are `design_canon_not_runtime_truth`. They can inform UI diagrams, but they must not be treated as current backend/runtime topology without verification.
- Docs that still present Threadspace, `guardian-backend_v2`, GuardianOS/plugin-system topology, or obsolete packaged-installer assumptions are classified as `historical_archive` or `misleading_identity_drift` based on how likely they are to confuse present product identity, supported install path, or current runtime behavior.
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
- `/docs/Codexify/THREADSPACE_SYSTEM_MAP.md`
- `/docs/Codexify/INSTALLER.md`
- `/docs/infra/INTERNAL_DOCS.md`
- `/docs/infra/system_architecture.md`
- `/docs/infra/persona_system_architecture.md`
- `/docs/Codexify/SECURITY.md`
- `/docs/infra/context-report.md`
- `/docs/infra/system_integrity_ledger.md`
