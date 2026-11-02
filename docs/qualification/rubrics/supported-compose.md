# Supported Compose Runtime Qualification Rubric

## Qualification ID

`supported-compose`

## Version

`1`

## Qualification metadata

```yaml qualification-metadata
qualification_id: supported-compose
version: 1
title: Supported Compose Runtime
scope: The supported local Docker Compose runtime, exercised end to end on one frozen evaluated tip
surface_paths:
  - docker-compose*.yml
  - config/supported_profiles/**
  - guardian/core/**
  - guardian/queue/**
  - guardian/routes/**
  - guardian/workers/**
  - guardian/db/migrations/**
```

## Purpose

Determine whether the **supported** local Docker Compose runtime is
qualified on a specific, frozen, evaluated revision.

This rubric covers the runtime that `docs/architecture/00-current-state.md`
names as the supported install path: the local Docker Compose profile
`v1-local-core-web-mcp` with `LLM_PROVIDER=local`,
`CODEXIFY_LOCAL_ONLY_MODE=true`, and `ALLOW_CLOUD_PROVIDERS=false`.

This rubric does **not** qualify:

- the Private Preview lane;
- public ingress or any hosted deployment;
- cloud providers;
- federation, connectors, hosted sandbox, Atlas, or Pi;
- the autonomous coding worker;
- any surface outside the supported profile.

Those lanes have their own authority. A PASS here does not widen them.

## Qualification identity

Every run of this rubric must record:

- the exact evaluated commit SHA;
- the branch and upstream state at evaluation;
- the supported profile name and its resolved provider contract;
- the logical provider and model actually exercised;
- the Compose files rendered, in order;
- the live Alembic revision;
- the durable artifact receipts collected.

A run that cannot name its evaluated commit is not a qualification run. It
is an observation.

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
- The live Alembic revision is recorded.

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

## Freshness

This surface is commit-bound. A run's evidence becomes stale when
meaningful changes touch the supported runtime — the Compose files, the
supported profile manifest, the core, queue, routes, workers, or migrations
that constitute the supported path.

The registry computes this from repository history rather than by hand. See
`scripts/qualification/lib/freshness.py`.

## Evidence

Cite the detailed proof artifacts under
`docs/architecture/proofs/supported-compose/`. The receipt links to the
exact proof rather than duplicating it.

## Relationship to release authority

`docs/architecture/00-current-state.md` remains release authority. A PASS
here qualifies the supported runtime for the tested revision and profile.
It does not by itself lift the release gate, and nothing in this directory
independently widens Beta or production support.
