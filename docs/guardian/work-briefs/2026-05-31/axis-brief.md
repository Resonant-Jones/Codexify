# Guardian Work Brief - 2026-05-31

Purpose: manual transfer packet for Axis and steering packet for the next Codex task.

## Reality
- Branch: `main` at `07d7c7a00`
- Upstream delta: behind `46`, ahead `0`
- Latest audit: PASS `43`, WARN `11`, FAIL `0`
- Current phase: Codexify is in local-first beta hardening on `main`. The supported path remains the local Docker Compose stack with local-only provider posture. This audit window did not surface a new merged runtime capability on `main`; the visible movement remains in release-truth maintenance and docs-level consolidation.

## Supported Truth
- Local Docker Compose remains the supported install path.
- The supported posture is local-only: `CODEXIFY_LOCAL_ONLY_MODE=true`, `ALLOW_CLOUD_PROVIDERS=false`, `LLM_PROVIDER=local`.
- Supported-profile, health, and catalog surfaces are aligned on `main`.
- Chat completion works on the supported path and persists back into the source thread.
- Upload -> embed -> readback works on the supported path.
- Workspace-local Obsidian retrieval is supported on the current tip.
- Image-turn containment remains proven on the supported profile.
- Coding results return through Guardian into the source thread on the supported path.
- Graph writes remain default-off on the supported Compose path.
- The release-truth override at `docs/architecture/00-current-state.md` is the live interpretation layer for this week.

## Drift
- Branch is behind upstream by 46 commit(s).
- 11 changed file(s) are present.
- Do not assume cloud-provider beta support.
- 5 recent marketing/history run(s) are draft.

## Risk
- No single merged-code blocker is proven on `main`.
- Chat completion is queue-coupled and still depends on Redis plus worker health.
- Canonical and legacy config paths still coexist, so startup and operator state can drift.
- Legacy `/tools` behavior still overlaps with the command bus.
- Sync subscriptions are still process-local rather than durable across restarts.
- Federation remains a high-blast-radius area with trust-policy and egress sensitivity.

## Do Not Assume
- Do not assume cloud-provider beta support.
- Do not assume the packaged desktop shell replaces the local Compose supported path.
- Do not assume command bus, delegation, federation, or graph write surfaces are part of the present release promise.
- Do not assume the Guardian Retrieval Navigation Model, adaptive route hints, reviewable graph evolution proposals, or self-improving memory are shipped runtime features. The new retrieval navigation note is planning doctrine only, does not expand the supported release surface, and does not change the current graph-writes-default-off boundary.
- Do not assume the local-model draft adapter is connected to Heartbeat, publishing, scheduling, command dispatch, or release approval.
- Do not assume UI dispatch, lease allocation, live agent execution, or merge automation are release-proven.
- Do not assume Guardian Build Loop doctrine means autonomous self-modification, auto-merge, push, or release-ready coding-worker behavior.
- Do not infer desktop packaging readiness from architecture docs alone.

## Decision
- Focus: Synchronize the working branch before making release claims.
- Rationale: The branch is behind upstream, so proof gathered here may be stale.

## Manual Closeout
- Finished today:
- Blocked:
- Next priority: Synchronize the working branch before making release claims.
- Axis KB note:
