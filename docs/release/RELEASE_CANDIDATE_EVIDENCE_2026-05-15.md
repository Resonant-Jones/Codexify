# Release Candidate Evidence Index - 2026-05-15

## Scope

This is the front door for the current local-first beta release candidate evidence bundle. It points at the proof artifacts that define what is true now and keeps the release claims bounded to the current-state contract.

## Current Release Posture

- Supported install path: local Docker Compose.
- Supported beta posture: local-only.
- Release checklist status: complete on current evidence.

## Evidence Map

| Artifact | What it anchors |
| --- | --- |
| [`docs/architecture/00-current-state.md`](../architecture/00-current-state.md) | Canonical short-horizon release truth: supported path, active blockers, and the present release promise. |
| [`docs/architecture/2026-05-05-supported-profile-live-proof.md`](../architecture/2026-05-05-supported-profile-live-proof.md) | Initial supported-profile proof for the local-only provider/catalog/health posture on the supported Compose path. |
| [`docs/architecture/2026-05-08-supported-profile-live-proof.md`](../architecture/2026-05-08-supported-profile-live-proof.md) | Fresh current-tip rerun of supported-profile and catalog/health posture. |
| [`docs/proofs/2026-05-15-supported-profile-catalog-health-drift-proof-rerun-after-runtime-wiring.md`](../proofs/2026-05-15-supported-profile-catalog-health-drift-proof-rerun-after-runtime-wiring.md) | Latest drift-proof rerun showing supported-profile, catalog, and health alignment for the current local-only contract. |
| [`docs/architecture/2026-05-05-coding-result-return-path-live-proof.md`](../architecture/2026-05-05-coding-result-return-path-live-proof.md) | Initial live coding-result return-path artifact for source-thread result-return behavior. |
| [`docs/architecture/2026-05-06-coding-result-return-path-backend-seam-proof.md`](../architecture/2026-05-06-coding-result-return-path-backend-seam-proof.md) | Backend seam proof that keeps result persistence and lineage anchored in Guardian. |
| [`docs/proofs/2026-05-13-coding-result-return-terminal-state-live-proof.md`](../proofs/2026-05-13-coding-result-return-terminal-state-live-proof.md) | Latest live proof of source-thread `coding_result` delivery, idempotent replay, and durable terminal-state convergence. |
| [`docs/proofs/2026-05-13-workspace-local-obsidian-retrieval-live-proof.md`](../proofs/2026-05-13-workspace-local-obsidian-retrieval-live-proof.md) | Workspace-local Obsidian retrieval live proof with rerun evidence. |
| [`docs/proofs/2026-05-07-workspace-obsidian-e2e-proof.md`](../proofs/2026-05-07-workspace-obsidian-e2e-proof.md) | Historical workspace-local Obsidian retrieval proof artifact. |
| [`docs/proofs/2026-05-07-workspace-obsidian-e2e-supersession.md`](../proofs/2026-05-07-workspace-obsidian-e2e-supersession.md) | Supersession note for interpretation of the earlier workspace-local proof. |
| [`docs/architecture/codexify-platform-readiness-audit.md`](../architecture/codexify-platform-readiness-audit.md) | Release audit contract and objective-check doctrine. |
| [`docs/audits/generated/2026-05-15-beta-sentinel.md`](../audits/generated/2026-05-15-beta-sentinel.md) | Human-readable beta sentinel snapshot for this release-candidate window. |
| [`docs/audits/generated/2026-05-15-beta-sentinel.json`](../audits/generated/2026-05-15-beta-sentinel.json) | Machine-readable beta sentinel snapshot for downstream automation. |
| [`CHANGELOG.beta.md`](../../CHANGELOG.beta.md) | Beta evidence ledger for the current sentinel window. |

## Claim Matrix

| Claim | Status | Evidence |
| --- | --- | --- |
| Supported install path | Supported on current evidence | `docs/architecture/00-current-state.md`, supported-profile proof set |
| Supported provider posture | Supported on current evidence | `docs/architecture/00-current-state.md`, supported-profile proof set |
| Chat completion | Supported on current evidence | `docs/architecture/00-current-state.md` |
| Upload / embed / readback | Supported on current evidence | `docs/architecture/00-current-state.md` |
| Coding-result source-thread delivery | Supported on current evidence | coding-result proof set |
| Durable terminal run-state convergence | Supported on current evidence | coding-result proof set |
| Workspace-local Obsidian retrieval injection | Supported on current evidence, with supersession context | workspace proof set + supersession notice |
| Supported-profile / catalog / health alignment | Supported on current evidence | supported-profile proof reruns |
| Internal/quarantined surfaces excluded | Preserved on current evidence | `docs/architecture/00-current-state.md`, supported-profile proof reruns |

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
- The [Command Center worker-control proof](../proofs/2026-05-10-command-center-worker-control-plane-live-proof.md) exists as an adjacent operator-control artifact, but it remains non-dispatch and excludes the behaviors above.

## Validation and Audit Automation

- Beta sentinel automation runs and generates the indexed markdown and JSON artifacts in [`docs/audits/generated/`](../audits/generated/).
- Platform-readiness audit JSON mode and audit contract are documented in [`docs/architecture/codexify-platform-readiness-audit.md`](../architecture/codexify-platform-readiness-audit.md).
- Documentation validation expectation: run `scripts/validate_docs.py` from the repo root after updating the evidence bundle.

## Renewal Rule

This index is a point-in-time evidence bundle, not a permanent guarantee. Any future runtime change that affects the supported beta posture, release claims, or release gates requires renewed proof and a refreshed evidence index.

## Relationship to Current Truth

This index summarizes already-proven release evidence and does not widen the release claim beyond `docs/architecture/00-current-state.md`. It is intentionally bounded to the current local-first beta posture.
