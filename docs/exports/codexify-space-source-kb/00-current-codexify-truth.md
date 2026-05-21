# Current Codexify Truth

## Current phase

- `Current`: Codexify is in local-first beta hardening on `main`.

## Current supported reality

- `Current`: The supported install and runtime path is local Docker Compose.
- `Current`: The supported provider posture is local-only, with `LLM_PROVIDER=local`, `CODEXIFY_LOCAL_ONLY_MODE=true`, and `ALLOW_CLOUD_PROVIDERS=false`.
- `Current`: Chat completion works on the supported path and persists back into the source thread.
- `Current`: Upload -> embed -> readback works on the supported path.
- `Current`: Workspace-local retrieval is supported on the current tip.
- `Current`: Image-turn containment is proven on the supported profile.
- `Current`: Guardian-returned coding results can land back in the source thread on the supported path.

## What is not yet true

- `Not Current`: Cloud-provider beta support is not a safe public claim.
- `Not Current`: The packaged desktop shell does not replace the supported local Compose path.
- `Not Current`: Command bus, delegation, federation, and graph-write surfaces are not part of the present public release promise by default.
- `Not Current`: Internal/manual local-model draft work is not public release proof.
- `Not Current`: UI dispatch, lease allocation, live agent execution, merge automation, and similar operator-control surfaces are not settled public product claims.

## Active blockers or release risks

- `Current risk`: Chat still depends on Redis and worker health, so acceptance does not guarantee completion.
- `Current risk`: Legacy and canonical config paths still coexist, so operator drift remains possible.
- `Current risk`: Supported-path proof must be refreshed whenever runtime behavior drifts.

## What Codexify.Space may safely say

- `Current`: Codexify is a local-first AI workspace.
- `Current`: It is currently being hardened around a supported local Docker Compose path.
- `Current`: It is designed around user-owned context, inspectable runtime truth, and proof-before-promise discipline.
- `Current`: It supports conversation, document ingestion, retrieval-backed context, and artifact continuity on the supported path.
- `Philosophy`: It treats continuity, ownership, and inspectability as product doctrine rather than marketing garnish.

## What Codexify.Space must not imply

- Do not imply hosted SaaS maturity.
- Do not imply cloud-provider support is part of the current safe default.
- Do not imply desktop packaging is the primary supported runtime.
- Do not imply autonomous agents, federation, graph writes, or delegation are shipped public guarantees.
- Do not imply acceptance equals completion, or that visible events guarantee UI receipt.
- Do not imply memory means hidden profiling or durable trait inference by default.

## Source docs used

- `docs/architecture/00-current-state.md`
- `docs/architecture/system-overview.md`
- `docs/architecture/flows.md`
- `docs/architecture/config-and-ops.md`
- `docs/architecture/tech-debt-and-risks.md`
- `docs/beta/README-FIRST.md`
