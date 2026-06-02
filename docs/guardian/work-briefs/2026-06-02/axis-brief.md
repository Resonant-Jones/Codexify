# Guardian Work Brief - 2026-06-02

Purpose: manual transfer packet for Axis and steering packet for the next Codex task.

## Reality
- Branch: `main` at `0e89d0bd5`
- Upstream delta: behind `0`, ahead `0`
- Latest audit: PASS `43`, WARN `11`, FAIL `0`
- Current phase: Codexify is in local-first beta hardening on `main`. The supported path remains the local Docker Compose stack with local-only provider posture. Recent `main` changes improved operator visibility and added a site-ready documentation export bundle, but they do not widen the release promise.

## Supported Truth
- Local Docker Compose remains the supported install path.
- The supported posture is local-only: `CODEXIFY_LOCAL_ONLY_MODE=true`, `ALLOW_CLOUD_PROVIDERS=false`, `LLM_PROVIDER=local`.
- Health checks report LLM model availability.
- Chat completion works on the supported path and persists back into the source thread.
- Upload -> embed -> readback works on the supported path.
- Workspace-local Obsidian retrieval is supported on the current tip.
- Image-turn containment remains proven on the supported profile.
- Coding results return through Guardian into the source thread on the supported path.
- Graph writes remain default-off on the supported Compose path.
- The release-truth override at `docs/architecture/00-current-state.md` is the live interpretation layer for this week.

## Drift
- 27 changed file(s) are present.
- Do not assume cloud-provider beta support.
- 5 recent marketing/history run(s) are draft.

## Risk
- Queue-coupled chat still depends on Redis plus worker health.
- Canonical and legacy config paths still coexist, so startup and operator state can drift.
- Legacy `/tools` behavior still overlaps with the command bus.
- Sync subscriptions are still process-local rather than durable across restarts.
- Federation remains a high-blast-radius area with trust-policy and egress sensitivity.

## Do Not Assume
- Do not assume cloud-provider beta support.
- Do not assume the packaged desktop shell replaces the local Compose supported path.
- Do not assume command bus, delegation, federation, or graph write surfaces are part of the present release promise.
- Do not assume the Guardian Retrieval Navigation Model, adaptive route hints, reviewable graph evolution proposals, or self-improving memory are shipped runtime features.
- Do not assume the site-export bundle changes runtime support or release readiness.
- Do not assume the local-model draft adapter is connected to Heartbeat, publishing, scheduling, command dispatch, or release approval.
- Do not assume UI dispatch, lease allocation, live agent execution, or merge automation are release-proven.
- Do not assume Guardian Build Loop doctrine means autonomous self-modification, auto-merge, push, or release-ready coding-worker behavior.
- Do not assume Build Proposal generation means approval, execution, release
- Do not assume Whooshd catalog metadata widens provider support beyond the local-only contract.
- Do not infer desktop packaging readiness from architecture docs alone.

## Decision
- Focus: Classify local changes before starting a new implementation slice.
- Rationale: A dirty worktree makes it harder to know what Axis should trust.

## Manual Closeout
- Finished today:
- Blocked:
- Next priority: Classify local changes before starting a new implementation slice.
- Axis KB note:
