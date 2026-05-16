# Release Candidate Evidence Index — 2026-05-15

## Scope
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
