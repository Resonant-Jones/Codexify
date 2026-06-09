# Whoosh'd Model Profiles

## Purpose

Whoosh'd model profiles are data-only local runtime descriptors for MLX-backed
local models.

They give Codexify a bounded place to describe candidate local model runtime
expectations without changing provider routing, provider identity, runtime
health semantics, catalog behavior, or release support.

## Scope

Profiles may describe:

- profile metadata
- runtime start hints
- model family notes
- acceptance checks
- release posture

Profiles are file-backed JSON manifests under
`config/whooshd/model-profiles/` and are validated by
`scripts/validate_whooshd_model_profiles.py`.

## Non-Goals

- No new provider id.
- No runtime routing changes.
- No catalog changes.
- No health semantics changes.
- No release claim expansion.
- No custom proxy restoration.

## Current First Profile

The first profile is `gemma-4-e2b-it-4bit`.

- Model repo: `mlx-community/gemma-4-e2b-it-4bit`
- Runtime hint:
  `mlx_vlm.server --model mlx-community/gemma-4-e2b-it-4bit --port 8000`
- Local OpenAI-compatible base URL hint:
  `http://host.docker.internal:8000/v1`

This profile is candidate metadata only. It is not wired into provider routing
or catalog exposure and is not a supported release model.

## Invariants

- Provider id remains `local`.
- Whoosh'd is display/vendor metadata unless a future ADR changes provider
  routing.
- A model profile is not proof of model quality.
- A model profile is not release support.
- Model-family hidden/thinking channel leakage must be blocked before
  Guardian-facing use.
- Acceptance checks must include no prompt echo, no thought/channel leakage, and
  Guardian completion smoke.

## Follow-Up Path

Later tasks may add live smoke proof, profile selection UI, catalog exposure, or
additional model profiles. Those changes must be separate tasks because each one
changes a different proof surface and may affect provider governance or release
posture.
