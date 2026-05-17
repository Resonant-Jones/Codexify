# Release Candidate Evidence Index — 2026-05-15

## Scope
<<<<<<< HEAD
This is the front door for the current local-first beta release candidate evidence bundle. It links the proof artifacts that define what is true now and keeps the release claims bounded to the current-state contract.

## Current Release Posture
- Local Docker Compose is the supported install path.
- The supported beta posture is local-only.
- The current release checklist is complete on current evidence as recorded in [`docs/architecture/00-current-state.md`](../architecture/00-current-state.md).

## Evidence Map
- [`docs/architecture/00-current-state.md`](../architecture/00-current-state.md) - authoritative short-horizon release truth layer and current release definition.
- [`docs/architecture/2026-05-05-supported-profile-live-proof.md`](../architecture/2026-05-05-supported-profile-live-proof.md) - live supported-profile proof for the local-only provider/catalog/health posture on the supported Compose path.
- [`docs/architecture/2026-05-08-supported-profile-live-proof.md`](../architecture/2026-05-08-supported-profile-live-proof.md) - fresh current-tip re-run of the supported-profile and catalog/health posture.
- [`docs/architecture/2026-05-05-coding-result-return-path-live-proof.md`](../architecture/2026-05-05-coding-result-return-path-live-proof.md) - live coding-result return-path proof artifact for the source-thread result-return seam.
- [`docs/architecture/2026-05-06-coding-result-return-path-backend-seam-proof.md`](../architecture/2026-05-06-coding-result-return-path-backend-seam-proof.md) - backend seam proof that keeps result persistence and lineage anchored in Guardian.
- [`docs/proofs/2026-05-07-workspace-obsidian-e2e-proof.md`](../proofs/2026-05-07-workspace-obsidian-e2e-proof.md) - workspace-local Obsidian retrieval proof artifact.
- [`docs/proofs/2026-05-07-workspace-obsidian-e2e-supersession.md`](../proofs/2026-05-07-workspace-obsidian-e2e-supersession.md) - supersession notice that explains the current interpretation of the earlier workspace-local proof.
- [`docs/architecture/codexify-platform-readiness-audit.md`](../architecture/codexify-platform-readiness-audit.md) - release audit contract, including JSON-mode audit behavior.
- [`docs/audits/generated/2026-05-15-beta-sentinel.md`](../audits/generated/2026-05-15-beta-sentinel.md) - human-readable beta sentinel artifact for the current release-candidate window.
- [`docs/audits/generated/2026-05-15-beta-sentinel.json`](../audits/generated/2026-05-15-beta-sentinel.json) - machine-readable beta sentinel artifact for downstream automation.
- [`CHANGELOG.beta.md`](../../CHANGELOG.beta.md) - beta evidence ledger for the current sentinel window.

## Claim Matrix
| Claim | Status | Indexed evidence |
| --- | --- | --- |
| Supported install path | Supported | `00-current-state.md`, supported-profile live proofs |
| Supported provider posture | Supported | `00-current-state.md`, supported-profile live proofs |
| Chat completion | Supported | `00-current-state.md`, supported-profile live proofs |
| Upload / embed / readback | Supported | `00-current-state.md`, supported-profile live proofs |
| Coding-result source-thread delivery | Supported on current evidence | `00-current-state.md`, coding-result return-path proofs |
| Durable terminal run-state convergence | Supported on current evidence | `00-current-state.md`, coding-result return-path proof set |
| Workspace-local Obsidian retrieval injection | Supported on current evidence, with supersession notice | workspace Obsidian proof + supersession notice |
| Supported-profile / catalog / health alignment | Supported | supported-profile live proof re-run, current-state contract |
| Internal / quarantined surfaces excluded | Preserved | `00-current-state.md`, config-and-ops truth surfaces |

## Non-Claims
- No cloud-provider beta support is claimed.
- No packaged desktop replacement for local Compose is claimed.
- No command bus, delegation, federation, or graph-write release expansion is claimed.
- No UI dispatch is claimed.
- No lease allocation from UI is claimed.
- No terminal execution from UI is claimed.
- No plugin runtime is claimed.
- No merge automation is claimed.
- No live MiniMax/Codex successful execution from Command Center is claimed.
- The [Command Center worker-control proof](../proofs/2026-05-10-command-center-worker-control-plane-live-proof.md) exists as an adjacent operator-control artifact, but it explicitly remains non-dispatch and excludes the behaviors above.

## Validation and Audit Automation
- Beta sentinel automation runs and generates the indexed markdown and JSON artifacts in [`docs/audits/generated/`](../audits/generated/).
- Platform-readiness audit JSON mode is repaired and documented in [`docs/architecture/codexify-platform-readiness-audit.md`](../architecture/codexify-platform-readiness-audit.md).
- Docs validation remains the required repo check for this index and its linked contract surface.

## Renewal Rule
This index is a point-in-time evidence bundle, not a permanent guarantee. Any future runtime change that affects the supported beta posture, release claims, or release gates requires renewed proof and a refreshed evidence index.
=======

This is the local-first beta release candidate evidence bundle for Codexify. It is a front door for humans and future agents who want to know what is true for this release candidate without widening the runtime promise.

## Current Release Posture

- Supported install path: local Docker Compose.
- Supported beta posture: local-only.
- Release checklist status: complete on current evidence.

## Evidence Map

| Artifact | What it anchors |
| --- | --- |
| [`docs/architecture/00-current-state.md`](/Users/resonant_jones/.codex/worktrees/db59/Codexify/docs/architecture/00-current-state.md) | Canonical short-horizon release truth: supported path, active blockers, and the present release promise. |
| [`docs/audits/generated/2026-05-15-beta-sentinel.md`](/Users/resonant_jones/.codex/worktrees/db59/Codexify/docs/audits/generated/2026-05-15-beta-sentinel.md) | Human-readable beta sentinel snapshot for the current release candidate. |
| [`docs/audits/generated/2026-05-15-beta-sentinel.json`](/Users/resonant_jones/.codex/worktrees/db59/Codexify/docs/audits/generated/2026-05-15-beta-sentinel.json) | Machine-readable beta sentinel snapshot for the same release candidate. |
| [`docs/proofs/2026-05-13-coding-result-return-terminal-state-live-proof.md`](/Users/resonant_jones/.codex/worktrees/db59/Codexify/docs/proofs/2026-05-13-coding-result-return-terminal-state-live-proof.md) | Live proof of Guardian source-thread `coding_result` delivery, idempotent replay, and durable terminal-state convergence. |
| [`docs/proofs/2026-05-13-workspace-local-obsidian-retrieval-live-proof.md`](/Users/resonant_jones/.codex/worktrees/db59/Codexify/docs/proofs/2026-05-13-workspace-local-obsidian-retrieval-live-proof.md) | Historical proof record for workspace-local Obsidian retrieval; includes the initial failure and the post-fix rerun note that reports success. |
| [`docs/proofs/2026-05-15-supported-profile-catalog-health-drift-proof-rerun-after-runtime-wiring.md`](/Users/resonant_jones/.codex/worktrees/db59/Codexify/docs/proofs/2026-05-15-supported-profile-catalog-health-drift-proof-rerun-after-runtime-wiring.md) | Live evidence that the supported-profile, catalog, and health surfaces are aligned on the current local-only beta contract. |
| [`docs/architecture/codexify-platform-readiness-audit.md`](/Users/resonant_jones/.codex/worktrees/db59/Codexify/docs/architecture/codexify-platform-readiness-audit.md) | Contract for the platform-readiness audit itself and its objective-check doctrine. |
| [`CHANGELOG.beta.md`](/Users/resonant_jones/.codex/worktrees/db59/Codexify/CHANGELOG.beta.md) | Evidence-led beta changelog entries that track the release candidate story over time. |

## Claim Matrix

| Claim | Status | Evidence |
| --- | --- | --- |
| Supported install path | Proven | `docs/architecture/00-current-state.md` |
| Supported provider posture | Proven | `docs/architecture/00-current-state.md`, `docs/proofs/2026-05-15-supported-profile-catalog-health-drift-proof-rerun-after-runtime-wiring.md` |
| Chat completion | Proven | `docs/architecture/00-current-state.md` |
| Upload / embed / readback | Proven | `docs/architecture/00-current-state.md` |
| Coding-result source-thread delivery | Proven | `docs/proofs/2026-05-13-coding-result-return-terminal-state-live-proof.md` |
| Durable terminal run-state convergence | Proven | `docs/proofs/2026-05-13-coding-result-return-terminal-state-live-proof.md` |
| Workspace-local Obsidian retrieval injection | Proven after rerun | `docs/architecture/00-current-state.md`, `docs/proofs/2026-05-13-workspace-local-obsidian-retrieval-live-proof.md` |
| Supported-profile / catalog / health alignment | Proven | `docs/proofs/2026-05-15-supported-profile-catalog-health-drift-proof-rerun-after-runtime-wiring.md` |
| Internal/quarantined surfaces excluded | Proven | `docs/architecture/00-current-state.md`, `docs/proofs/2026-05-15-supported-profile-catalog-health-drift-proof-rerun-after-runtime-wiring.md` |

## Non-Claims

- No cloud-provider beta support.
- No packaged desktop replacement for Compose.
- No command bus, delegation, federation, or graph-write release expansion.
- No UI dispatch.
- No lease allocation from UI.
- No terminal execution from UI.
- No plugin runtime.
- No merge automation.
- No live MiniMax/Codex successful execution from Command Center.

## Validation / Audit Automation

- Beta sentinel command: `scripts/release/beta_release_sentinel.py`.
- Platform-readiness audit contract: `scripts/audit_platform_readiness.py` is an objective-check audit, not a subjective score sheet.
- Documentation validation expectation: run `scripts/validate_docs.py` from the repo root after updating the evidence bundle.

## Renewal Rule

This index is a point-in-time evidence bundle, not a forever guarantee. Any future runtime change that affects the supported path, provider posture, retrieval, or operator truth surfaces requires renewed proof before this index should be treated as current.

## Relationship to Current Truth

This index summarizes already-proven release evidence and does not widen the release claim beyond `docs/architecture/00-current-state.md`. It is intentionally bounded to the current local-first beta posture.
>>>>>>> d9c2c1077 (Add release candidate evidence index)
