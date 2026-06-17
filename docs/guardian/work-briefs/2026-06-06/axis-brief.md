# Guardian Work Brief - 2026-06-06

Purpose: manual transfer packet for Axis and steering packet for the next Codex task.

## Reality
- Branch: `main` at `2bcd31c00`
- Upstream delta: behind `0`, ahead `0`
- Latest audit: PASS `43`, WARN `11`, FAIL `0`
- Current phase: Codexify is in local-first beta hardening on `main`. The supported path remains the local Docker Compose stack with local-only provider posture. Recent `main` changes improved operator visibility, added a site-ready documentation export bundle, and added local runtime presets for Whoosh'd/MLX, Ollama, LM Studio, and custom OpenAI-compatible endpoints, but they do not widen the release promise.

## Supported Truth
- Local Docker Compose remains the supported install path.
- The supported posture is local-only: `CODEXIFY_LOCAL_ONLY_MODE=true`, `ALLOW_CLOUD_PROVIDERS=false`, `LLM_PROVIDER=local`.
- The current Apple Silicon default local inference target is Whoosh'd/OpenAI-compatible. The setup wizard defaults to Ollama on non-Mac machines when no preset is selected.
- Live model availability is proven only when `/v1/models` or `/api/tags` advertises the selected local model.
- Health checks report LLM model availability.
- Chat completion works on the supported path and persists back into the source thread.
- Upload -> embed -> readback works on the supported path.
- Workspace-local Obsidian retrieval is supported on the current tip.
- Coding results return through Guardian into the source thread on the supported path.
- Graph writes remain default-off on the supported Compose path.
- Provider timeout and slow-path failures are classified and presented more accurately in the UI.

## Drift
- 77 changed file(s) are present.
- Do not assume cloud-provider beta support.
- 5 recent marketing/history run(s) are draft.

## Risk
- Queue-coupled chat still depends on Redis plus worker health.
- Canonical and legacy config paths still coexist, so startup and operator state can drift.
- Legacy `/tools` behavior still overlaps with the command bus.
- End-to-end Guardian delegation is not yet a release-supported path.
- Federation remains a high-blast-radius area with trust-policy and egress sensitivity.
- Docs-heavy merged work does not remove the need to recheck runtime proof on the supported path.

## Do Not Assume
- Do not assume cloud-provider beta support.
- Do not assume the packaged desktop shell replaces the local Compose supported path.
- Do not assume command bus, delegation, federation, or graph write surfaces are part of the present release promise.
- Do not assume the Guardian delegation loop contract means the end-to-end delegation loop is shipped.
- Do not assume the Guardian Retrieval Navigation Model, adaptive route hints, reviewable graph evolution proposals, or self-improving memory are shipped runtime features.
- Do not assume the local-model draft adapter is connected to Heartbeat, publishing, scheduling, command dispatch, or release approval.
- Do not assume UI dispatch, lease allocation, live agent execution, or merge automation are release-proven.
- Do not assume Guardian Build Loop doctrine means autonomous self-modification, auto-merge, push, or release-ready coding-worker behavior.
- Do not assume Build Proposal generation means approval, execution, release
- Do not assume any local runtime is available without live endpoint/model inventory proof.
- Do not infer desktop packaging readiness from architecture docs alone.
- Do not infer a wider release promise from docs-only exports, scaffolds, or audit artifacts.

## Decision
- Focus: Classify local changes before starting a new implementation slice.
- Rationale: A dirty worktree makes it harder to know what Axis should trust.

## Manual Closeout
- Finished today:
- Blocked:
- Next priority: Classify local changes before starting a new implementation slice.
- Axis KB note:
