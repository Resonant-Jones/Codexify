# Release Candidate Evidence Index — 2026-05-15

## Scope

This is the front door for the current local-first beta release candidate evidence bundle. It links the proof artifacts that define what is true now and keeps the release claims bounded to the current-state contract.

## Current Release Posture

- Supported install path: local Docker Compose.
- Supported beta posture: local-only.
- Release checklist status: complete on current evidence.

## Evidence Map

| Artifact | What it anchors |
| --- | --- |
| [`docs/architecture/00-current-state.md`](../architecture/00-current-state.md) | Canonical short-horizon release truth: supported path, active blockers, and the present release promise. |
| [`docs/audits/generated/2026-05-15-beta-sentinel.md`](../audits/generated/2026-05-15-beta-sentinel.md) | Human-readable beta sentinel snapshot for the current release candidate. |
| [`docs/audits/generated/2026-05-15-beta-sentinel.json`](../audits/generated/2026-05-15-beta-sentinel.json) | Machine-readable beta sentinel snapshot for the same release candidate. |
| [`docs/proofs/2026-05-13-coding-result-return-terminal-state-live-proof.md`](../proofs/2026-05-13-coding-result-return-terminal-state-live-proof.md) | Live proof of Guardian source-thread `coding_result` delivery, idempotent replay, and durable terminal-state convergence. |
| [`docs/proofs/2026-05-13-workspace-local-obsidian-retrieval-live-proof.md`](../proofs/2026-05-13-workspace-local-obsidian-retrieval-live-proof.md) | Historical proof record for workspace-local Obsidian retrieval, including the initial failure and the post-fix rerun note that reports success. |
| [`docs/proofs/2026-05-15-supported-profile-catalog-health-drift-proof-rerun-after-runtime-wiring.md`](../proofs/2026-05-15-supported-profile-catalog-health-drift-proof-rerun-after-runtime-wiring.md) | Live evidence that the supported-profile, catalog, and health surfaces are aligned on the current local-only beta contract. |
| [`docs/architecture/codexify-platform-readiness-audit.md`](../architecture/codexify-platform-readiness-audit.md) | Contract for the platform-readiness audit itself and its objective-check doctrine. |
| [`CHANGELOG.beta.md`](../../CHANGELOG.beta.md) | Evidence-led beta changelog entries that track the release candidate story over time. |

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

## Validation and Audit Automation

- Beta sentinel command: `scripts/release/beta_release_sentinel.py`.
- Platform-readiness audit contract: `scripts/audit_platform_readiness.py` is an objective-check audit, not a subjective score sheet.
- Documentation validation expectation: run `scripts/validate_docs.py` from the repo root after updating the evidence bundle.

## Renewal Rule

This index is a point-in-time evidence bundle, not a forever guarantee. Any future runtime change that affects the supported path, provider posture, retrieval, or operator truth surfaces requires renewed proof before this index should be treated as current.

## Relationship to Current Truth

This index summarizes already-proven release evidence and does not widen the release claim beyond `docs/architecture/00-current-state.md`. It is intentionally bounded to the current local-first beta posture.
