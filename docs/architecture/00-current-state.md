## Purpose
This file is Codexify's canonical short-form source of truth for current operational and release state. If it conflicts with older architecture, planning, or roadmap language on short-horizon reality, this file wins.

## Last updated
2026-06-12

## Interpretation rule
This file is authoritative for:
- release readiness
- supported install path
- active blockers
- current priorities
- what is and is not part of the present release promise

## Current phase
Codexify is in local-first beta hardening on `main`. The supported path remains the local Docker Compose stack with local-only provider posture. Recent `main` work expands local-provider setup and operator-facing docs, but it does not widen the release promise.

## What changed recently
- `main` added Whoosh'd profile switching and the first Whoosh'd local model profile.
- `main` documented the Whoosh'd local runtime install path and local inference provider setup.
- `main` added Campaign Runner intention-packet, prompt-artifact, and fixture-materialization scaffolding.
- `main` added TTS console voice profiles and the local Qwen3 TTS adapter.
- The supported local-only posture remains intact on `main`.

## Current supported reality
- Local Docker Compose remains the supported install path.
- The supported posture is local-only: `CODEXIFY_LOCAL_ONLY_MODE=true`, `ALLOW_CLOUD_PROVIDERS=false`, `LLM_PROVIDER=local`.
- Whoosh'd is a supported local runtime preset on Apple Silicon paths.
- `LOCAL_RUNTIME_PRESET` can select between `whooshd-mlx`, `ollama`, `lmstudio`, and `custom-openai-compatible` while staying under `LLM_PROVIDER=local`.
- Live model availability is still proven only by inventory from `/v1/models` or `/api/tags`.
- Health surfaces still report LLM availability and chat queue/worker status.
- Chat completion, upload -> embed -> readback, and workspace-local retrieval remain the supported beta paths.
- Graph writes remain default-off on the supported Compose path.

## Not yet true / do not assume
- Do not assume cloud-provider beta support.
- Do not assume the packaged desktop shell replaces the local Compose supported path.
- Do not assume delegation, federation, or graph write surfaces are part of the present release promise.
- Do not assume docs-only exports, scaffolds, prompt artifacts, or brief-generation output prove runtime support.
- Do not assume Whoosh'd setup equals live provider reachability without endpoint/model inventory proof.
- Do not infer a wider beta claim from the new local preset wiring alone.

## Active blockers
- Queue-coupled chat still depends on Redis plus worker health.
- Canonical and legacy config paths still coexist, so startup and operator state can drift.
- End-to-end Guardian delegation is not yet a release-supported path.
- Federation remains high-blast-radius and trust-policy sensitive.
- Graph-write enablement stays outside the default release promise.

## This week’s priorities
1. Keep supported-profile, health, and catalog surfaces aligned on `main`.
2. Preserve fresh proof for chat, upload, retrieval, and coding-result return paths.
3. Keep delegation, federation, and graph-write work explicitly out of the release promise until proven.
4. Keep the release-truth docs synced with the live `main` posture.
5. Avoid widening supported beta claims until a new merged capability is proven end to end.

## Release definition right now
- [x] Supported-profile flags match the local-only beta contract.
- [x] The current `main` tip includes a supported local runtime preset for Whoosh'd.
- [x] Fresh live evidence exists on the current `main` tip for the supported path.
- [x] Chat completion, upload -> embed -> readback, and workspace-local retrieval are in the supported claim set.
- [ ] Queue, config, delegation, and federation risks must stay explicitly documented and rechecked when the supported path drifts.

## How to read the rest of the KB
- `system-overview.md` explains structure, not release readiness.
- `flows.md` explains runtime behavior.
- `data-and-storage.md` explains persistence/invariants.
- `config-and-ops.md` explains operator/runtime truth.
- `roadmap-signals.md` is planning guidance, not live status.
- `tech-debt-and-risks.md` is a risk register, not the active blocker list unless repeated here.
