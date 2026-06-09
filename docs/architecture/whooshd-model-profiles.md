Purpose: Define the bounded Whoosh'd local model profile registry without changing provider routing, catalog behavior, runtime selection, health semantics, or release posture.
Last updated: 2026-06-08
Source anchors:
- config/whooshd/model-profiles/
- scripts/validate_whooshd_model_profiles.py
- docs/architecture/00-current-state.md
- docs/architecture/config-and-ops.md
- docs/architecture/chat-runtime-contract.md
- docs/architecture/runtime-protocol-token-contract.md

# Whoosh'd Model Profiles

## Purpose

Whoosh'd model profiles are data-only local runtime descriptors for MLX-backed local models.

The registry gives future local model work a small file-backed place to record model identity, runtime hints, transcript safety defaults, acceptance checks, and release posture before any runtime routing or catalog exposure is changed.

## Scope

Profiles may describe:

- profile metadata
- runtime start hints
- model family notes
- Guardian defaults
- acceptance checks
- release posture

Profiles may also note where a future live proof should store model weights. For this first profile, the operator requirement is to keep downloaded weights off the repo and under `/Volumes/Dev_SSD/` during a separate runtime-proof task. This metadata task does not download or verify those weights.

## Non-Goals

- No new provider id.
- No runtime routing changes.
- No catalog changes.
- No health semantics changes.
- No release claim expansion.
- No custom proxy restoration.

## Current First Profile

- Profile id: `gemma-4-e2b-it-4bit`
- Model repo: `mlx-community/gemma-4-e2b-it-4bit`
- Runtime hint: `mlx_vlm.server --model mlx-community/gemma-4-e2b-it-4bit --port 8000`
- Local OpenAI-compatible base URL hint: `http://host.docker.internal:8000/v1`

## Invariants

- Provider id remains `local`.
- Whoosh'd is display/vendor metadata unless a future ADR changes provider routing.
- A model profile is not proof of model quality.
- A model profile is not release support.
- Model-family hidden/thinking channel leakage must be blocked before Guardian-facing use.
- Acceptance checks must include no prompt echo, no thought/channel leakage, and Guardian completion smoke.
- Profile metadata must not be treated as health, catalog, supported-profile, queue/worker, or Guardian completion evidence.

## Follow-Up Path

Later tasks may add live smoke proof, profile selection UI, catalog exposure, or additional model profiles, but those must be separate tasks.

The next live-proof task should verify the selected MLX runtime, keep model weights under `/Volumes/Dev_SSD/`, compare health/catalog/supported-profile posture, confirm queue and worker health, and prove one Guardian chat completion persists back into the source thread without prompt echo or hidden-channel leakage.

## ADR Impact

Classification: Aligned with existing ADRs and contracts; no new ADR required.

Governing anchors:

- `docs/architecture/00-current-state.md`
- `docs/architecture/config-and-ops.md`
- `docs/architecture/chat-runtime-contract.md`
- `docs/architecture/runtime-protocol-token-contract.md`
- provider governance and supported-profile doctrine

Reason: this creates a bounded data-only registry for local model profiles. It preserves provider id `local`, keeps Whoosh'd as display/vendor metadata, and does not alter runtime semantics, provider routing, catalog exposure, or release support.
