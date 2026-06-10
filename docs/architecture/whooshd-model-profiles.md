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

## Current Profiles

The current profiles are:

- Profile id: `gemma-4-e4b-it-4bit`
- Model repo: `mlx-community/gemma-4-e4b-it-4bit`
- Runtime hint: `mlx_vlm.server --model mlx-community/gemma-4-e4b-it-4bit --port 8000`
- Local OpenAI-compatible base URL hint: `http://host.docker.internal:8000/v1`
- Weight storage root: `/Volumes/Dev_SSD/whooshd/model-weights`

- Profile id: `gemma-4-12b-it-optiq-4bit`
- Model repo: `mlx-community/gemma-4-12B-it-OptiQ-4bit`
- Runtime hint: `mlx_vlm.server --model mlx-community/gemma-4-12B-it-OptiQ-4bit --port 8000`
- Local OpenAI-compatible base URL hint: `http://host.docker.internal:8000/v1`
- Weight storage root: `/Volumes/Dev_SSD/whooshd/model-weights`

- Profile id: `gemma-4-12b-it-qat-4bit`
- Model repo: `mlx-community/gemma-4-12B-it-qat-4bit`
- Runtime hint: `mlx_vlm.server --model mlx-community/gemma-4-12B-it-qat-4bit --port 8000`
- Local OpenAI-compatible base URL hint: `http://host.docker.internal:8000/v1`
- Weight storage root: `/Volumes/Dev_SSD/whooshd/model-weights`

## Invariants

- Provider id remains `local`.
- Whoosh'd is display/vendor metadata unless a future ADR changes provider
  routing.
- A model profile is not proof of model quality.
- A model profile is not release support.
- Offline use requires local cached model artifacts before network loss; the
  profile does not download or prove those artifacts.
- `runtime.offline_probe_command` is an operator hint for local cached-model
  checks, not routing logic, and it can still be overridden by explicit routing
  or task metadata.
- `mlx-vlm` here is a preferred multimodal local runtime hint, not a provider
  replacement and not a routing change by itself.
- Model-family hidden/thinking channel leakage must be blocked before
  Guardian-facing use.
- Acceptance checks must include no prompt echo, no thought/channel leakage, and
  Guardian completion smoke.

## Follow-Up Path

Later tasks may add live smoke proof, profile selection UI, catalog exposure, or
additional model profiles. Those changes must be separate tasks because each one
changes a different proof surface and may affect provider governance or release
posture.
