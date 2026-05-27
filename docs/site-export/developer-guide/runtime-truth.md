# Runtime Truth

This page summarizes current supported runtime reality.
If it conflicts with broader architecture language, the short-horizon source of truth is `/docs/architecture/00-current-state.md`.

## Supported local Docker Compose path

The supported install and runtime path remains local Docker Compose.
That path includes the FastAPI backend, Postgres as the system of record, Redis-backed queues and task events, worker processes for chat and embeddings, and the current supported-profile wiring for the local beta contract.

## Local-only provider posture

The supported posture is local-only:

- `CODEXIFY_LOCAL_ONLY_MODE=true`
- `ALLOW_CLOUD_PROVIDERS=false`
- `LLM_PROVIDER=local`

Cloud-capable configuration, discovered provider inventory, or partial internal adapter work do not widen the current support promise.

## Current supported capabilities

On the supported local Compose path, the documented supported reality is:

- chat completion works and persists back into the source thread
- upload to embed to readback works
- workspace-local Obsidian retrieval is supported
- image-turn containment remains proven
- coding results return through Guardian into the source thread
- health, supported-profile, and catalog surfaces are aligned on `main`
- health checks report LLM model availability

## Current non-promises

The current release posture does not promise:

- cloud-provider beta support
- packaged desktop as a replacement for the supported Compose path
- command bus, delegation, federation, or graph writes as end-user release surfaces
- Guardian Retrieval Navigation Model, adaptive route hints, reviewable graph evolution proposals, or self-improving memory as shipped runtime features
- local-model draft adapter wiring into Heartbeat, publishing, scheduling, command dispatch, or release approval
- UI dispatch, lease allocation, live agent execution, merge automation, or autonomous coding-worker behavior

## Active blockers

The current blockers are operational and structural rather than a single merged-code defect:

- chat completion remains queue-coupled and depends on Redis plus worker health
- canonical and legacy config paths still coexist, so startup and operator state can drift
- legacy `/tools` behavior still overlaps with the command bus
- sync subscriptions remain process-local rather than durable across restarts
- federation remains high blast radius because of trust-policy and egress sensitivity

## Release posture

Current direction should be read as local-first beta hardening, not a widened launch promise.
Developers should preserve fresh proof for the supported Compose path and avoid promoting internal-only or unproven seams into external claims.
