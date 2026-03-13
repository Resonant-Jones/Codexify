Purpose: Define a beta-safe Stage 0 plan for classifying Codexify configuration into deployment config and runtime settings, based only on directly inspected files, without changing current behavior.
Last updated: 2026-03-12
Source anchors:
- `guardian/core/config.py`
- `guardian/config/core.py`
- `guardian/core/dependencies.py`
- `guardian/config_loader.py`
- `guardian/config/settings.py`
- `guardian/config/system_config.py`
- `guardian/cognition/user_settings/store.py`
- `guardian/cognition/system_profiles/resolver.py`
- `frontend/src/lib/runtimeConfig.ts`
- `frontend/src/lib/env.ts`
- `frontend/src/lib/providerPref.ts`
- `frontend/src/imprint/settingsApi.ts`
- `guardian/queue/redis_queue.py`
- `guardian/routes/connectors.py`
- `guardian/workers/chat_worker.py`
- `guardian/workers/voice_worker.py`
- `guardian/voice/config.py`
- `docs/reference/architecture/config-and-ops.md` (supporting reference)
- `docs/CONFIGURATION.md` (supporting reference)

# Config Classification and Consolidation Plan

## Purpose

This document defines a beta-safe Stage 0 planning boundary for Codexify configuration. The immediate goal is to reduce config drift ahead of beta stabilization by:

- identifying the current configuration categories that are visible from directly inspected files
- separating deployment config from runtime settings
- defining a future canonical boundary without changing behavior yet

This is a planning artifact, not a completed audit. It does not change runtime behavior, loader behavior, environment parsing, provider behavior, worker boot behavior, or UI behavior.

## Current Problem Statement

The inspected repo already shows multiple configuration entrypoints and interpretation layers:

- `guardian/core/config.py` defines a large Pydantic `Settings` model for backend settings.
- `guardian/config/core.py` defines a separate `Settings` model with overlapping provider, secret, and runtime fields.
- `guardian/core/dependencies.py` loads dotenv layers, resolves auth and exposure behavior, and reads multiple environment variables directly into module-level constants.
- `guardian/config_loader.py` merges YAML defaults with environment variables into a dict-backed loader.
- `guardian/config/settings.py` exposes a dict-backed runtime singleton for dynamic settings.
- `guardian/config/system_config.py` loads and persists JSON-backed system configuration and initializes directories.

The inspected repo also shows hidden state spread across more than one storage and interpretation surface:

- environment variables and code defaults in backend settings and dependency modules
- browser-local storage in `frontend/src/lib/runtimeConfig.ts` and `frontend/src/lib/providerPref.ts`
- thread- or database-backed runtime behavior in `guardian/cognition/system_profiles/resolver.py`
- API-managed identity settings in `frontend/src/imprint/settingsApi.ts`
- in-memory fallback user settings in `guardian/cognition/user_settings/store.py`
- worker/runtime state such as queue names, concurrency, heartbeat keys, and timeouts in queue and worker modules

That spread creates unclear ownership for user-facing settings. For example, inspected files show provider/model behavior appearing in more than one place:

- environment-derived provider and model defaults in `guardian/core/config.py`, `guardian/config/core.py`, and `guardian/core/dependencies.py`
- browser-stored provider/model preferences in `frontend/src/lib/providerPref.ts`
- thread-scoped profile overrides including `provider_override`, `model_override`, `temperature_override`, and `retrieval_config` in `guardian/cognition/system_profiles/resolver.py`

Operationally, that creates drift risk:

- startup env loading is centralized in `guardian/core/dependencies.py`, but multiple workers and route modules still read env directly
- overlapping config families exist across separate modules with different defaulting behavior
- frontend runtime behavior can be influenced by env, Tauri-provided values, and browser-local overrides

For beta stabilization, Codexify needs an explicit boundary between machine/startup concerns and user-visible runtime behavior, even before any code is changed.

## Classification Framework

### Deployment config

Deployment config is configuration that belongs to the machine, process, secret boundary, or infrastructure topology. It is evaluated as boot-time or infrastructure state, even if the current code reads it in more than one place.

Examples that fit this class include:

- database URLs
- Redis URLs
- provider API keys
- storage paths
- host and port bindings
- worker concurrency
- queue names and heartbeat TTLs
- service URLs used to reach backing systems
- boot-critical feature flags and route exposure flags

Observed repo examples supporting this class include:

- DSNs, provider defaults, base URLs, storage paths, and feature flags in `guardian/core/config.py`
- auth mode, exposure mode, API key handling, and dotenv loading in `guardian/core/dependencies.py`
- YAML/env-backed TTS and plugin config in `guardian/config_loader.py`
- JSON-backed path and operational defaults in `guardian/config/system_config.py`
- Redis queue names and turn-lock TTLs in `guardian/queue/redis_queue.py`
- connector worker enablement and sync interval in `guardian/routes/connectors.py`
- chat and voice worker queue names, concurrency, heartbeat keys, and timeout-related settings in `guardian/workers/chat_worker.py`, `guardian/workers/voice_worker.py`, and `guardian/voice/config.py`

### Runtime settings

Runtime settings are settings that primarily affect user-visible behavior and should eventually be managed separately from environment variables. They may still be env-backed today, but they describe product behavior more than machine wiring.

Examples that fit this class include:

- default provider
- default model
- retrieval mode or retrieval configuration
- temperature and completion defaults
- user-visible toggles
- active backend profile or other UI-facing behavior controls
- identity- or thread-scoped behavioral settings

Observed repo examples supporting this class include:

- thread profile data such as `provider_override`, `model_override`, `temperature_override`, and `retrieval_config` in `guardian/cognition/system_profiles/resolver.py`
- identity settings fields such as `memory_mode`, `diary_requires_unlock`, and `allow_sensitive_modeling` in `guardian/cognition/user_settings/store.py` and `frontend/src/imprint/settingsApi.ts`
- browser-stored provider/model preference selection in `frontend/src/lib/providerPref.ts`
- frontend runtime behavior overrides for backend/share base URLs in `frontend/src/lib/runtimeConfig.ts`

### Decision criteria

Use the following rules when classifying a setting:

1. If the value is required to boot the process, authenticate to infrastructure, bind to a network surface, find a filesystem location, size a worker, or connect to an external service, classify it as deployment config.
2. If the value is secret, environment-specific, or owned by deploy/ops rather than by a user or thread, classify it as deployment config.
3. If changing the value should normally require a restart or redeploy to be applied safely, classify it as deployment config.
4. If the value mainly changes user-visible model choice, retrieval behavior, completion behavior, or interaction behavior, classify it as a runtime setting candidate.
5. If the value should eventually be scoped per installation, user, thread, or profile and managed through API/UI state rather than process env, classify it as a runtime setting candidate.
6. If a setting affects both runtime behavior and machine safety, prefer deployment config until a narrower managed runtime interface exists.

Put differently: env should be reserved for machine and startup concerns; user-facing behavior should move toward managed runtime settings later.

## Inventory Method

This section describes the audit method. It does not claim that the full inventory has already been completed.

### Audit scope

The audit should enumerate configuration reads, declarations, defaults, and persistence surfaces across at least these inspected areas:

- backend settings models and config modules:
  `guardian/core/config.py`, `guardian/config/core.py`, `guardian/config_loader.py`, `guardian/config/settings.py`, `guardian/config/system_config.py`
- env parsing and startup interpretation:
  `guardian/core/dependencies.py`
- frontend runtime and base URL configuration:
  `frontend/src/lib/runtimeConfig.ts`, `frontend/src/lib/env.ts`
- frontend persisted preference state:
  `frontend/src/lib/providerPref.ts`
- runtime settings and user-facing behavior state:
  `guardian/cognition/user_settings/store.py`, `guardian/cognition/system_profiles/resolver.py`, `frontend/src/imprint/settingsApi.ts`
- worker and job configuration:
  `guardian/queue/redis_queue.py`, `guardian/routes/connectors.py`, `guardian/workers/chat_worker.py`, `guardian/workers/voice_worker.py`, `guardian/voice/config.py`
- provider routing/config and feature-flag usage:
  follow provider, model, base URL, timeout, and `*_ENABLED` or `ENABLE_*` setting families from declaration sites to their consumers

### Recommended audit steps

1. Enumerate declared settings surfaces.
   Start with explicit settings declarations, dict defaults, JSON defaults, YAML defaults, and module-level env-backed constants.
2. Enumerate interpretation surfaces.
   Record where dotenv is loaded, where env values are normalized, and where browser or runtime overrides are applied.
3. Enumerate persistence surfaces for user-visible behavior.
   Record values that live in local storage, in-memory state, per-thread metadata, or API-managed settings.
4. Group by setting family.
   Collapse aliases and overlapping reads into one inventory line item so that drift is visible.
5. Classify each item.
   Apply the deployment-vs-runtime decision criteria above.
6. Record unresolved items.
   If the owner, source of truth, or intended scope is unclear, mark the item as unresolved rather than guessing.

### Expected capture fields

Each inventory entry should capture at least:

| Field | Description |
|---|---|
| Setting family | Canonical label for the setting or alias group |
| Current source type | Env, dotenv, YAML, JSON, local storage, in-memory state, DB/thread metadata, or API-managed state |
| Declaration location | Where the setting is defined or defaulted |
| Read locations | Where the setting is consumed |
| Default/fallback behavior | Default value, fallback chain, or override order if visible |
| Secret status | Secret, non-secret, or mixed |
| Restart requirement | Whether current behavior implies restart/redeploy is needed |
| Scope | Machine, installation, user, thread, profile, or unknown |
| Candidate classification | Deployment config or runtime setting |
| Current owner | Ops/deploy, backend, frontend, user, or unknown |
| Target home | Canonical backend deployment loader, runtime settings service, frontend bootstrap, or unknown |
| Notes | Drift risks, aliases, or follow-up required |

## Proposed Canonical Target State

The intended future architecture is:

- one canonical backend deployment config loader
- runtime settings managed separately from env
- env reserved for machine and startup concerns
- user-facing settings moved toward API- and UI-managed storage over time

In that target state:

- deployment config remains responsible for secrets, infrastructure URLs, ports, paths, queue sizing, concurrency, and boot-critical feature exposure
- runtime settings become an explicit product surface for behavior such as default provider/model, profile behavior, retrieval behavior, and other user-visible toggles
- frontend runtime bootstrap is narrowed to connection/bootstrap concerns instead of acting as a long-term home for behavior settings
- thread, profile, and user behavior controls are represented through explicit backend-managed runtime settings rather than implicit env or browser-local drift

This document does not define the implementation details of that target state. It does not choose schemas, migration mechanics, storage engines, or API contracts yet.

## Migration Stages

### Stage 0: inventory and classification

Document the current config surface, define the classification rules, and prepare the audit method.

This task completes Stage 0 only.

### Stage 1: identify canonical backend config module

Choose and document the single backend deployment-config entrypoint that future deployment reads will standardize on. Based on direct inspection, the Pydantic-backed path in `guardian/core/config.py` is the strongest candidate to evaluate, but this task does not finalize that choice.

### Stage 2: route all deployment config reads through one source

Incrementally move deployment-config reads behind the canonical backend loader while preserving behavior and compatibility. The focus is on read consolidation first, not renaming settings families during this stage.

### Stage 3: introduce a runtime settings service for selected user-facing settings

Create a separate backend-managed runtime settings layer for settings that should not remain env-owned, starting with a small set of user-visible behavior controls such as provider/model defaults, profile behavior, retrieval behavior, and related settings.

### Stage 4: expose those runtime settings in UI

Expose the selected runtime settings through explicit UI and API flows after the backend-managed runtime settings boundary exists.

## Out of Scope

This task does not:

- change any env var names
- remove any config modules
- move secrets into the database
- introduce UI settings screens
- alter provider behavior
- change worker boot behavior
- change runtime behavior, loaders, or env parsing
- edit existing docs for cross-linking, terminology cleanup, or index updates

## Deliverable Summary

This Stage 0 note gives Codexify a concrete planning boundary for beta stabilization:

- it defines how deployment config and runtime settings should be distinguished
- it identifies the currently inspected config surfaces that need to be audited
- it provides a repeatable audit method and capture format
- it prepares the next step of choosing one canonical backend deployment-config path without claiming that consolidation has already happened
