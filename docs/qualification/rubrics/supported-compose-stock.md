# Stock Compose Runtime Qualification Rubric

## Qualification ID

`supported-compose-stock`

## Version

`1`

Derived from `supported-compose` rubric version 2. The seven required checks
and blocking criteria below are unchanged. Startup identity, freshness coverage,
and evidence custody identify the separate stock Compose execution path.

## Qualification metadata

```yaml qualification-metadata
qualification_id: supported-compose-stock
version: 1
title: Stock Compose Runtime
scope: The supported local-first Beta profile v1-local-core-web-mcp, exercised end to end on one frozen revision through stock Docker Compose startup, without the source-matched launcher
surface_paths:
  - .dockerignore
  - docker-compose*.yml
  - config/**
  - backend/**
  - guardian/**
  - frontend/**
  - plugins/**
  - codex_runner/**
  - package.json
  - pnpm-lock.yaml
  - pnpm-workspace.yaml
```

## Purpose and startup boundary

Qualify the stock `docker compose up` startup of `docker-compose.yml` for the
supported `v1-local-core-web-mcp` profile: local inference, cloud providers
disabled, local-only policy, and an empty egress allowlist. Required services
and provider invariants remain those of the accepted profile and ADR-069.

The source-matched launcher is a distinct startup and is not invoked by a run
of this rubric. Its receipts and registry verdict cannot substitute for stock
execution evidence. The existing `supported-compose` rubric is unchanged.

A disposable isolation overlay may select a verified immutable image, allocate
unique resources and host ports, provide synthetic credentials, and apply the
existing supported profile's provider values. It must not replace the stock
migrator's command, mounts, source guard, or dependency/startup semantics.
Image and effective mounted application source compatibility must be verified
before startup. Shared production tags and Preview resources are not test
inputs. The image may be reused after content verification; a rebuild is not
a prerequisite in its own right.

This rubric does not qualify Private Preview, public ingress, hosted deployment,
cloud providers, federation, connectors, hosted sandbox, Atlas, Pi, autonomous
coding workers, onboarding-and-people, or any surface outside the supported
profile. A PASS does not widen those lanes or promote release status.

## Required run identity and evidence

Every run records its full frozen source SHA, clean isolated worktree, local
lineage and upstream observations, selected image identity and content parity,
Compose files in order, resolved provider contract and runtime inventory,
project-owned storage, exact stock startup commands, direct database revision
readback, and dated proof references. The frozen SHA remains unchanged.

Each of the seven checks requires evidence from this integrated run. The proof
must include provider-side non-execution evidence for unavailable-model
rejection, a real-browser event/UI/reload observation, and state survival plus
a new ordinary completion after restarting only qualification-owned services.
Mocks, a migrator-only receipt, or a launcher-driven run cannot replace those
observations. Record errors, unproven criteria, Preview before/after observations,
and positively identified resource cleanup without inventing causality.

## Required checks

Each check is recorded as **PASS**, **FAIL**, **UNPROVEN**, or **N/A** with
a reason.

### 1. Supported topology and startup

- `docker compose config --quiet` succeeds for the rendered Compose set.
- Every required service for the profile is present and healthy:
  `frontend`, `backend`, `db`, `redis`, `worker-chat`,
  `worker-document-embed`, `migrator`.
- The resolved environment matches the profile's provider contract exactly:
  local-only, no cloud credentials, empty egress allowlist.
- The live Alembic revision is recorded, and it is read **directly out of
  PostgreSQL** rather than from a container exit code.
- The live Alembic revision equals the evaluated checkout's single Alembic
  head, with exactly one row. The checkout resolves to exactly one head, and
  the image's baked migration source is proven to describe the evaluated
  checkout by the migrator's own coherence proof over `versions/*.py` and
  `env.py`, and that proof passed rather than failing closed.

  A stale image must fail closed here. A run in which the migrator refuses to
  migrate is a **FAIL**, not an UNPROVEN: the migration-source contract is
  observable, and the refusal is the designed behaviour.

### 2. Health and inventory

- `/health`, `/health/chat`, and `/api/health/llm` respond.
- Model inventory is observed at the runtime, not assumed from configuration.

### 3. Ordinary chat and durable readback

- A thread is created through the ordinary route.
- A user message is authored and accepted.
- Completion is enqueued and a terminal outcome is observed.
- The assistant message is persisted and readable afterward.
- The durable attempt record agrees with the transcript and the events.

### 4. Document ingestion and retrieval

- A document is uploaded and reaches an embedding state.
- A retrieval probe returns documents.
- Provenance identifies the retrieved document and chunk.

### 5. Explicit model authority

- A completion that explicitly requests an **unavailable** model fails
  **before provider execution**.
- No substitute model executes.
- No assistant message is persisted for the failed attempt.
- The durable attempt records the terminal failure kind.

This is the check most likely to fail. It is also the check that most
directly protects the user: an explicit model request that silently
resolves to a different model is a false success.

### 6. Browser projection

- A real browser renders the thread.
- The terminal state converges in the UI.
- Reload preserves the projected state.

### 7. Restart recovery

- The supported services are restarted.
- Ordinary chat works after the restart.
- Durable state survives the restart.

## Blocking criteria

This rubric cannot receive PASS if any of the following occur:

- the supported topology does not start, or a required service is unhealthy;
- the migrator fails closed, or the live `alembic_version` does not equal the
  evaluated checkout's single Alembic head;
- the runtime does not match the supported profile's provider contract;
- an explicit unavailable model is executed, substituted, or reported as
  successful;
- a completion is accepted but no terminal outcome is ever observed;
- an assistant message is persisted without a matching durable attempt;
- durable state is lost across a restart;
- the evaluated commit cannot be identified.

A run that satisfies every required check but leaves the browser,
restart-recovery, or provenance boundaries unexercised is **HOLD**, not
PASS. Unproven boundaries are not silent passes.

## Verdict interpretation

Overall PASS requires every required blocking criterion to pass. Directly
contradictory runtime behavior is FAIL; incomplete required evidence or a
preflight prerequisite that prevents safe execution is HOLD. N/A requires a
specific justification and cannot hide a required unexercised boundary.

Known limitations outside these required criteria must remain visible without
being silently repaired or automatically invalidating a scoped PASS. Required
criteria that fail remain blocking, regardless of unrelated passing checks.

## Freshness

Evidence is commit-bound. The registry computes freshness from the declared
surface paths: stock Compose and supported configuration, backend/migrator,
Guardian runtime and persistence, frontend and locked dependencies, plugins,
and execution adapters. Documentation-only receipt maintenance does not imply
new runtime proof. Image identity and external provider observations remain
explicit run evidence, not facts inferred from source paths.

## Evidence and release authority

Run receipts belong in `docs/qualification/runs/` and cite detailed proofs under
`docs/architecture/proofs/supported-compose/`. Registry output is generated by
the canonical generator and never hand-maintained. Historical receipts are
immutable. `00-current-state.md` retains release authority. Release remains
HOLD unless a separate authorized release decision changes it.
