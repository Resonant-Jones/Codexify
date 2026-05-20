# 00 Current Codexify Truth

## Current phase

`Current`: Codexify is in local-first beta hardening. The authoritative short-horizon truth source is `docs/architecture/00-current-state.md` from the infrastructure repo.

## Current supported reality

`Current`:
- The supported install/runtime path is the local Docker Compose stack.
- The supported posture is local-only provider operation, not cloud-first beta support.
- Chat completion is supported on that path.
- Upload -> embed -> readback is supported on that path.
- Workspace-local retrieval is supported on the current tip.
- Image-turn containment is proven on the supported profile.
- Guardian-returned coding results can land back in the source thread on the supported path.

## What is not yet true

`Current`:
- Desktop packaging does not replace the supported local Compose path.
- Cloud-provider beta support must not be assumed.
- Command bus, delegation, federation, graph writes, scheduling, publishing, lease allocation, merge automation, and live agent dispatch are not safe public release promises.
- Presence of a route, catalog entry, feature flag, or ADR is not proof of supported release behavior.

## Active blockers or release risks

`Current`:
- No currently proven supported-path blocker is recorded on `main`.
- Redis and worker health remain release risks for chat completion.
- Config drift between supported and legacy paths remains an operator risk.
- Runtime proof must be refreshed when the supported path changes.

## What Codexify.Space may safely say

`Current`:
- Codexify is a local-first AI workspace.
- The current supported path is local Docker Compose.
- The system is built around inspectable runtime surfaces rather than hidden magic.
- Current beta claims should stay narrow and proof-driven.
- User-owned continuity, retrieval, and identity boundaries are central product doctrines.

## What Codexify.Space must not imply

`Current`:
- That Codexify beta is cloud-hosted by default
- That packaged desktop is the primary supported runtime today
- That any internal operator or experimental surface is publicly supported
- That request acceptance equals completion
- That task-event publication guarantees UI receipt
- That memory or identity modeling happens without consent

## Source docs used

- `docs/architecture/00-current-state.md`
- `docs/architecture/README.md`
- `docs/architecture/system-overview.md`
- `docs/architecture/flows.md`
- `docs/architecture/config-and-ops.md`
- `docs/architecture/tech-debt-and-risks.md`
- `docs/release/audits/beta-smoke-test.md`
- `docs/release/open-source-tiering/public-readiness-checklist.md`
- `docs/Marketing/README.md`
