# Configuration Authority Path Census

> **Status:** non-normative inspection artifact. This document records a bounded
> repository audit; it does not establish a new configuration contract, change
> precedence, or make a runtime/release claim.

## Purpose and scope

This census examines backend configuration resolution paths at the `main`
snapshot inspected for this task (`064bb9c53f59ebe5b3f6a110e9c96374514a6cf1`,
before this documentation commit). Its purpose is to answer a narrower question
than a general redundancy review: which materially distinct code paths can
resolve the same configuration responsibility, and whether their authority
relationship is explicit.

The bounded scope includes the primary settings modules, canonical ASGI startup,
maintained API/worker/CLI consumers, and direct environment resolution for
provider/model posture, auth, database, vector, graph, egress, queue, voice/TTS,
storage, command-loopback, and connection/OAuth configuration. Frontend
configuration, a general code-duplication inventory, and runtime execution were
out of scope.

"Pathway" below means a distinct resolver, loader, or adapter boundary with its
own input/default/coercion behavior. It does not mean every individual
`os.getenv` expression, every field in a settings model, or duplicate lines of
code.

## Evidence posture

This is repository/code-path evidence. It establishes definitions, imports,
static callers, default/precedence rules, and the canonical checked-in ASGI
entrypoint (`guardian/server/run.py` → `guardian.guardian_api:app`). It does
not prove that an optional route, worker, CLI, deployment profile, environment
file, or provider path executed in a running deployment.

The inspection used bounded searches for settings constructors, imports,
`os.getenv`/`os.environ`, and the relevant consumer call paths. No environment
file or secret value was read. Where a definition has no statically found
runtime caller, this report says **“No runtime caller found in the bounded
repository scan.”** That is not a claim that the definition is dead or cannot
be selected manually or externally.

The focused coherence suite named by the task is an additional, limited proof
surface. It exercises the tested core/legacy comparison behavior; it cannot
prove that no other resolver exists or that a production process followed a
particular load order.

## Governing architecture and ADRs

- [`README.md`](README.md) and the [canonical ADR index](adr/adr-index.md) were
  used as architecture/ADR navigation anchors; they do not override current
  state or a governing ADR.
- [`00-current-state.md`](00-current-state.md) remains the current release-truth
  authority. Its local-first Beta/private-preview posture is not expanded by
  this audit.
- [`config-and-ops.md`](config-and-ops.md) defines the current documented
  configuration expectations. It explicitly says configuration is not yet
  single-source and directs operators to check both settings modules.
- [`tech-debt-and-risks.md`](tech-debt-and-risks.md) records the split between
  `guardian/core/config.py` and `guardian/config/core.py` as a high-severity
  configuration risk. The risk statement is a reason to inspect, not proof of
  a runtime defect.
- [`modules-and-ownership.md`](modules-and-ownership.md) is relevant because it
  recognizes supporting and compatibility layers as legitimate architecture;
  parallel-looking code is therefore not presumed harmful.
- [ADR-074](adr/074-tester-provider-model-configuration-authority.md) governs
  the tested Tester provider/model relationship: supported profile controls
  allowed/default posture, operator environment controls concrete
  `LOCAL_CHAT_MODEL`, and Compose transports rather than independently selects
  that model.
- [ADR-026](adr/026-graph-write-runtime-flag-boundary-on-supported-compose-path.md)
  governs the default-off graph-write gate and its fail-closed factory.
- [ADR-067](adr/067-operator-approved-derived-chroma-retirement.md) is the
  directly relevant derived-vector-state governance context; it does not turn
  this static census into private-preview runtime proof.

No ADR is changed, superseded, or proposed by this artifact.

## The two known settings surfaces

| Surface | Inputs, defaults, and initialization | Validation / precedence | Static consumer evidence | Relationship to the other surface |
|---|---|---|---|---|
| `guardian/core/config.py` — `Settings`, module-global `settings`, `get_settings()`, `validate_llm_config()`, `assert_config_coherence()` | Pydantic `BaseSettings`; `.env`; `extra="ignore"`. `LLM_PROVIDER` defaults to `local`; configuration source defaults to `strict`. A module-global `settings = Settings()` is constructed at import, and `get_settings()` returns that same object. It also contains typed graph and vector fields. | Validates provider/configuration conditions, normalizes several legacy model aliases, and provides strict/core/legacy coherence modes. `resolve_vector_store_runtime()` intentionally checks current raw vector variables before the settings object. | Canonical ASGI module imports the core surface; its lifespan calls `get_settings()` and `assert_config_coherence()`. Core provider routing, catalog, health, workers, and supported-profile validation also import/use it. | It does not wrap `guardian.config.core`. It lazily imports the legacy getter only for coherence comparison. |
| `guardian/config/core.py` — `Settings`/`Config`, `get_settings()`, legacy provider helpers | Independent Pydantic `BaseSettings`; `.env`; `extra="allow"`. It has legacy defaults such as `AI_BACKEND="groq"`, legacy provider/model/host fields, and independent database/auth fields. `get_settings()` constructs a fresh `Settings()` on each call (with test/CI fallback behavior). | Performs its own production-only provider-key validation, database URL normalization, and model/backend selection helpers. | `guardian/config/__init__.py` exports this getter as `guardian.config.get_settings`. `guardian/core/dependencies.py` imports that package getter; active auth and database helpers call it. Legacy CLI/plugin/thread helpers also reference `Config`. | It neither imports nor delegates to `guardian.core.config`. It independently reproduces overlapping fields and defaults. |

The two classes are therefore not a wrapper/delegate pair. They independently
materialize overlapping environment/configuration responsibilities. The actual
maintained call sites below determine where that structural split rises to a
live competing-authority concern.

### Startup-order observation

`config-and-ops.md` documents the intended sequence as dotenv chain, then core
settings materialization. Static Python import order shows a narrower
documentation/code discrepancy: `guardian/guardian_api.py` imports
`guardian.core.dependencies` and `guardian.core.config` before it executes
`dependencies._load_env_chain()`; the core module constructs its singleton at
import. The legacy getter, by contrast, constructs a fresh object when called.

This establishes a possible same-process observation difference when values are
introduced only by the later explicit dotenv chain. It does **not** prove that
such a value exists, that an environment file is present, or that a running
process has observed divergent values. The existing startup-configuration
qualification similarly records test-process settings drift as a bounded test
finding, not live runtime proof.

## Configuration pathway map

```text
process environment / permitted dotenv files
    |
    +-- guardian.core.dependencies._load_env_chain() ------> primary ASGI dotenv source
    |                                                        (called after module imports)
    |
    +-- guardian.core.config.Settings singleton -----------> core routing, catalog,
    |                                                        supported-profile checks
    |
    +-- guardian.config.core.Settings (fresh per call) ----> dependencies auth/db
    |
    +-- explicit raw resolvers ----------------------------> ASGI bootstrap/auth,
    |                                                        DB helpers, scoped subsystems
    |
    +-- specialized owners --------------------------------> profile, vector, egress,
                                                             graph, queue, voice/TTS,
                                                             storage, OAuth, command bus
```

The diagram is an input-flow map, not a precedence specification. In particular,
the supported profile, operator environment, Compose transport, and runtime
inventory retain the distinct roles assigned by ADR-074.

## Responsibility-by-responsibility census

The following table is the counted pathway inventory. Mechanically repetitive
direct reads are grouped by the resolver that owns their common responsibility.
Every entry uses one of the task-required classifications.

| ID | Responsibility | Resolution path and input behavior | Consumer/reachability evidence | Classification | Competing authority? |
|---|---|---|---|---|---|
| C1 | General current core configuration and provider posture | `guardian.core.config.Settings` / global `settings` / `get_settings()`; Pydantic `.env` plus process environment, `LLM_PROVIDER=local`, singleton at module import. | `guardian.guardian_api` startup; core router/catalog/health and supported-profile validation use the core surface. | **Canonical authority** | Structural overlap with A1; live conflict is only proven for the responsibilities called out below. |
| C2 | Primary ASGI dotenv sourcing | `guardian.core.dependencies._load_env_chain()` loads `.env`, `.env.backend.{GUARDIAN_ENV}`, then `.env.local` with `override=False`. | Explicitly called by `guardian.guardian_api` during canonical app module initialization. | **Canonical authority** | No separate loader is proven to own primary ASGI dotenv precedence; see the import-order observation. |
| C3 | Supported provider posture and allowed profile contract | `guardian.core.supported_profile`: profile name/directory, YAML manifest, provider contract, and explicit `LOCAL_CHAT_MODEL` operator-selection exception. | `guardian.guardian_api` refreshes/validates it in lifespan; provider/catalog/health code consumes its posture. | **Canonical authority** | No. ADR-074 assigns this scope; it is not a general provider client selector. |
| C4 | Active vector-store runtime selection | `guardian.core.config.resolve_vector_store_runtime()` resolves backend/path/collection from raw vector variables first, then core settings, with centralized normalization. | `guardian.vector.store.VectorStore` calls it and passes the result to its embedder; chat completion builds `VectorStore`. | **Canonical authority** | A scoped health/embedder fallback exists (Q1), but it is not proven to control the active store on the normal `VectorStore` path. |
| C5 | Outbound egress policy | `guardian.core.egress.assert_egress_allowed()` uses supplied core settings when supplied, otherwise raw environment fallback in the same policy gateway. | Core router/provider registry pass settings; dependencies, cron, image generation, and several adapters invoke the same gateway without settings. | **Canonical authority** | Two input-acquisition modes, but one policy function and no independent second policy resolver were found. |
| C6 | Graph-write backend selection | `guardian.memory_graph.graph_backend_factory.get_graph_backend_adapter()` directly parses the two graph-write flags, fails closed to noop, and caches by selected backend. | `guardian.workers.graph_write_worker._invoke_graph_backend_adapter()` calls it. ADR-026 names this worker entrypoint. | **Canonical authority** | Core typed graph fields describe the same flags, but no live second selection caller was found for the compatibility factory (U4). |
| K1 | Legacy model-name input aliases inside core settings | `guardian.core.config.Settings.model_post_init()` maps the documented legacy model aliases only when canonical targets are unset and normalizes DeepSeek defaults. | Runs when C1 is constructed. | **Compatibility path** | No independent resolver: it translates legacy input into C1 fields. |
| K2 | Core/legacy transition check | `guardian.core.config.assert_config_coherence()` lazily obtains legacy settings and compares selected overlapping values; `CODEXIFY_CONFIG_SOURCE` selects strict/core/legacy behavior. | Called in canonical ASGI lifespan; covered by `tests/core/test_config_coherence.py`. | **Compatibility path** | It observes both surfaces rather than making either delegate to the other. It does not consolidate their authority. |
| K3 | Deprecated voice URL/provider names | `guardian.voice.config` accepts old voice/STT/TTS environment names and warns once while mapping them to the current voice runtime fields. | `guardian.guardian_api` validates voice config at startup; voice routes/services call the same getter. | **Compatibility path** | No: the aliases are resolved within the voice owner and are explicitly warning-backed. |
| S1 | System directories and process-local system defaults | `guardian.config.system_config.SystemConfig` reads `config.json` plus its own directory/thread/plugin defaults; `ensure_system_dirs()` is explicit. | `guardian.guardian_api` calls `ensure_system_dirs()` in lifespan. | **Specialized owner** | No. It owns system path/bootstrap configuration, not provider, auth, or database endpoint selection. |
| S2 | Plugin CLI YAML/environment configuration | `guardian.config_loader.ConfigLoader` merges an optional YAML config and selected environment values for the plugin CLI. | `guardian.chat.cli.plugin_cli` constructs it. | **Specialized owner** | No. It is a CLI-local configuration object rather than the API/worker settings authority. |
| S4 | Redis queue transport | `guardian.queue.redis_queue._redis_url()` and queue helpers resolve `REDIS_URL`, parse it, and construct queue clients. | Queue/worker, lock, and health consumers use the queue module. | **Specialized owner** | No. Core settings does not provide a competing Redis transport resolver. |
| S5 | Command-bus loopback URL | `guardian.command_bus.loopback_http_adapter.resolve_loopback_base()` requires a command-loopback base, with a constrained non-Docker fallback. | Command execution uses it to build loopback requests. | **Specialized owner** | No. This is a command transport endpoint, not the API's general configuration authority. |
| S6 | Media/storage provider configuration | `guardian.core.storage` resolves storage type, local base/path/URL prefix, and provider-specific S3/GCS configuration. | Media/storage consumers import the storage factory and providers. | **Specialized owner** | No current core-settings counterpart was found for this storage-specific responsibility. |
| S7 | Connection/OAuth application setup | Google Drive OAuth and MiniMax OAuth modules resolve their own client registration, endpoints, allowlists, PKCE/state secret, and timeout values. | Connection routes import these server-owned modules. Their code keeps OAuth credentials/control data server-side. | **Specialized owner** | No. These are per-connector node/application configuration responsibilities, not provider-routing authority. |
| S8 | Media-signing secret selection | `guardian.core.media_signing._media_signing_secret()` uses media secret, then session secret, then API key. | Media URL signing and verification call it. | **Specialized owner** | No. The fallback shares secret material but owns a media-signing purpose, not HTTP-auth configuration. |
| S10 | CLI embedding setup | `guardian.runtime.embed.embedder` resolves vector/embed configuration for the memory embedding CLI. | `guardian.cli.memory.embed` imports it; focused worker tests also import it. | **Specialized owner** | No active API-store authority is proven from this CLI path. |
| A1 | Legacy settings object for overlapping auth/database fields | `guardian.config.core.Settings` independently parses `.env`/environment and creates a fresh object each `get_settings()` call; it has independent legacy defaults and validation. | `guardian.core.dependencies` imports `guardian.config.get_settings`; `verify_api_key`, `require_service_api_key`, and `init_database` call it on active API paths. | **Alternate live authority** | **Yes:** it independently resolves shared auth/database values rather than delegating to C1. |
| A2 | API bootstrap and request-auth key resolution | `guardian.guardian_api` reads `GUARDIAN_API_KEY` directly at import/startup; `guardian.core.auth` reads it directly; `guardian.core.dependencies` reads raw key(s) after attempting A1. | Canonical ASGI startup performs the hard key check; routes use dependencies/auth helpers; chat's local repository-search helper uses the same legacy/raw order. | **Alternate live authority** | **Yes:** raw resolution and A1 separately resolve HTTP-auth key material with different construction/timing behavior. |
| A3 | Application database endpoint and adapter selection | `dependencies.init_database()` gets A1's `GUARDIAN_DATABASE_URL` then raw `DATABASE_URL`; `guardian.core.__init__` chooses an adapter from raw `DATABASE_URL` then `GUARDIAN_DATABASE_URL`; `guardian.core.db.load_guardian_db_from_env()` uses the reverse raw order. | Canonical ASGI calls `init_database`; routes/services call `load_guardian_db_from_env`. | **Alternate live authority** | **Yes:** maintained API and core-adapter branches independently resolve the same database endpoint with non-identical precedence behavior. |
| A4 | Migration and worker-local database bootstrap defaults | `guardian.config.db_defaults.DEFAULT_PG_DSN` resolves `DATABASE_URL`, `GUARDIAN_DATABASE_URL`, `GUARDIAN_DB_URL`, then a Compose default at import; migration/worker helpers layer local behavior around it. | Cron, embedding, account-import, voice worker, media and seed paths import/use it. | **Alternate live authority** | **Yes:** it independently resolves the same database endpoint, adds an alias/default absent from A3, and has maintained worker/migration consumers. |
| A5 | Voice runtime TTS-provider resolver | `guardian.voice.config.get_voice_runtime_config()` resolves `CODEXIFY_TTS_PROVIDER`, otherwise `CODEXIFY_TTS_BACKEND`, plus voice-specific defaults and aliases. | Canonical ASGI validates voice configuration; mounted voice routes/services use this getter. | **Alternate live authority** | **Yes:** it independently resolves the TTS provider/backend responsibility alongside A6, with different input precedence. |
| A6 | Local TTS adapter resolver | `guardian.tts.config.get_local_tts_config()` loads `.env.local` then `.env` for missing process values and resolves `CODEXIFY_TTS_BACKEND`, then `CODEXIFY_TTS_PROVIDER`, with local model/path/output defaults. | Canonical ASGI mounts `/tts`; its routes and TTS renderer/backends call this getter. | **Alternate live authority** | **Yes:** it resolves the same TTS provider/backend inputs as A5 in the opposite order and has a separate dotenv-loading path. |
| A7 | Legacy revisionless system-profile provider/model defaults | `guardian.cognition.system_profiles.resolver._default_profile_catalog()` directly reads local-model aliases and `LLM_PROVIDER`/`CHAT_PROVIDER`, then profile resolution runs before global core-settings fallback in completion assembly. | `guardian.core.chat_completion_service.build_messages_for_llm()` calls `resolve_thread_system_profile()` for completion work. | **Alternate live authority** | **Yes:** the legacy revisionless profile branch independently chooses a provider/model override. Persona revision selection is a separate durable path, not evidence that this fallback executed. |
| U1 | Alternate historical ASGI app | `guardian.server.app` has its own lifespan/coherence/database setup. | `guardian.server.run.py` names `guardian.guardian_api:app` as canonical; bounded imports for `guardian.server.app` were tests. **No runtime caller found in the bounded repository scan.** | **Apparently unreferenced** | Not counted as a proven live competitor. It may still be manually selected or externally referenced. |
| U2 | Mutable dict-backed runtime settings | `guardian.config.settings.RuntimeConfig` / its singleton has no environment resolution and is separate from both Pydantic settings objects. | **No runtime caller found in the bounded repository scan.** | **Apparently unreferenced** | Not counted. |
| U3 | Flow-tuner `BaseSettings` | `guardian.modules.flow_tuner.FlowConfig` independently reads `FLOW_`-prefixed `.env` values. | Only its in-file example and focused test were found. **No runtime caller found in the bounded repository scan.** | **Apparently unreferenced** | Not counted. |
| U4 | Legacy graph compatibility factory | `guardian.memory_graph.graph_backend_factory.get_graph_backend()` combines raw values, C1 settings values, and Neo4j aliases. | The maintained graph worker calls C6 instead. **No runtime caller found in the bounded repository scan.** | **Apparently unreferenced** | Not counted; this prevents calling C6/C1 a proven live selection conflict. |
| Q1 | Direct `backend.rag.embedder` fallback configuration | `Embedder` can resolve vector backend/path/collection directly when callers omit explicit arguments. Normal `guardian.vector.store.VectorStore` callers pass C4's resolved values; `health_vector` has a scoped raw backend fallback for a diagnostic probe. | Static calls establish normal explicit passing and a diagnostic caller, but this scan did not establish a maintained production execution that relies on the embedder's own unparameterized fallback. | **Uncertain** | Not counted as a proven active-store competing authority. |
| Q2 | Legacy provider-adapter/MemoryOS environment paths | `guardian.providers` adapters/registry and local MemoryOS helpers retain direct provider key/model/default reads; some legacy/CLI/optional orchestration imports exist. | The canonical chat path uses `guardian.core.provider_registry` and `guardian.core.ai_router`; the bounded scan could not establish whether every optional legacy/MemoryOS path is reachable in an active deployment. | **Uncertain** | Not counted. The presence of direct reads alone is insufficient to label an alternate live authority. |

## Direct environment access findings

The direct-access scan found many environment reads beyond the two Pydantic
models. They fall into the following evidence-backed groups rather than a raw
grep dump:

1. **Core mechanisms:** C2, C4, and C5 are intentional resolver boundaries.
   They use raw values either to implement documented dotenv/operator precedence
   or to preserve a single policy/resolver boundary.
2. **Live alternate resolution:** A1–A7 have direct/raw or independently
   constructed lookup for an overlapping responsibility. Their exact order is
   documented in the census and is not unified by delegation.
3. **Scoped subsystem ownership:** C3, C6, S1–S2, S4–S8, S10, and K3 parse environment
   values for a specific supported profile, graph/queue/voice/TTS/storage/OAuth/
   command/migration/CLI responsibility. Their direct reads do not by themselves
   establish that they bypass C1.
4. **Historical/optional ambiguity:** Q1–Q2 are retained as uncertain because
   their static existence and partial import evidence do not establish a
   maintained runtime path relying on their local defaults.

Notable direct-read details:

- The primary startup and auth code reads `GUARDIAN_API_KEY` directly even
  though both settings models expose an auth-key field. Dependencies first uses
  the legacy object and then raw fallback; core auth has another raw key path.
- Database reads vary by branch: raw `DATABASE_URL` first in the core package
  selector; legacy `GUARDIAN_DATABASE_URL` first in API initialization; and a
  worker/migration import-time default additionally accepts `GUARDIAN_DB_URL`
  and a Compose fallback.
- The graph worker factory intentionally reads the gate directly and fails
  closed. The core typed fields do not by themselves prove a second worker
  selection path.
- Voice and TTS maintain separate resolvers. Both are mounted API surfaces,
  they consult the same provider/backend aliases in opposite order, and the
  local TTS resolver additionally has its own missing-only dotenv loader. This
  is therefore counted as a live TTS-provider authority seam (A5/A6), while
  voice's deprecated-name mapping remains K3.
- Connector/OAuth modules are server-owned credential/configuration owners; no
  browser credential authority was inferred from their direct reads.

## Competing-authority findings

Four responsibilities have repository evidence of more than one independently
resolving **live** authority. That count is deliberately narrower than the
number of overlapping fields or raw reads.

| Responsibility | Independently resolving live paths | Same input? | Differing defaults / coercion / lifetime observation | Explicit authority relationship? | Assessment |
|---|---|---|---|---|---|
| HTTP API key / accepted key set | A1 legacy settings, A2 direct ASGI/auth/dependencies raw reads | Largely yes (`GUARDIAN_API_KEY`, with legacy multi-key support). | A1 is constructed fresh per call; direct reads observe current process environment; startup hard-check and request verification have separate logic. | Partial: dependencies documents a fallback order, but neither path delegates to C1. | Proven alternate live authority. The source does not prove inconsistent values in a running process. |
| Database endpoint / adapter choice | A1 API initialization, A3 core adapter/DB helper, A4 worker/migration default | Partially: `DATABASE_URL` and `GUARDIAN_DATABASE_URL` overlap; A4 also accepts `GUARDIAN_DB_URL` and a Compose default. | Yes: precedence differs by resolver, A4 is import-time, and core adapter choice can differ from API initializer order. | No single shared resolver/delegation was found. | Proven alternate live authority and the strongest operator-legibility seam after the settings split. |
| TTS provider/backend selection | A5 voice runtime resolver and A6 local TTS adapter resolver | Yes: both consult `CODEXIFY_TTS_PROVIDER` and `CODEXIFY_TTS_BACKEND`. | Yes: their alias ordering is opposite, A6 loads local dotenv files, and each carries a different scoped default/configuration object. | No shared resolver or governing precedence relationship was found. | Proven alternate live authority for two mounted TTS/voice surfaces. It does not imply a release claim for either surface. |
| Legacy revisionless system-profile provider/model default | A7 profile catalog and C1 global core settings/provider routing | Partially: A7 reads `LLM_PROVIDER`/`CHAT_PROVIDER` plus local model aliases; C1 uses its typed fields. | Yes: A7 defaults cloud profile selection differently and converts `local` to `openai` in that legacy profile branch. | The profile resolver is explicitly called before global fallback, but no governing document in the inspected set defines this legacy fallback's relationship to ADR-074's authority model. | Proven alternate live authority in the revisionless profile branch; no production execution of that branch is claimed. |

The broad `guardian.core.config` / `guardian.config.core` structural split is
real. The bounded evidence does **not** prove that every overlapping field is a
simultaneously competing live authority. In particular, C6/U4 and C4/Q1 were
kept out of the proven count because maintained live competing selection was not
established.

### Highest-risk finding

The highest-risk static finding is the combined core/legacy settings and
startup-order seam:

- core settings are a singleton created during import;
- canonical ASGI's explicit dotenv chain executes after its imports; and
- legacy settings are independently constructed on each call and are used by
  active auth/database helpers.

This can create a configuration-observation mismatch and operator confusion,
especially around auth/database values introduced only by the explicit dotenv
chain. It remains a **static risk**, not a demonstrated production defect.

## Classification summary

The counts are pathway groups, not code-line counts. They correspond exactly to
the IDs in the census table.

| Classification | Pathways | Count |
|---|---|---:|
| **Canonical authority** | C1–C6 | 6 |
| **Compatibility path** | K1–K3 | 3 |
| **Specialized owner** | S1–S2, S4–S8, S10 | 8 |
| **Alternate live authority** | A1–A7 | 7 |
| **Apparently unreferenced** | U1–U4 | 4 |
| **Uncertain** | Q1–Q2 | 2 |
| **Total** | C1–Q2 | **30** |

**Proven configuration responsibilities with more than one independently
resolving live authority: 4.**

## Uncertain and unproven findings

- No live execution, deployment environment, Compose rendering, provider call,
  worker process, or production inventory was inspected. This document cannot
  prove which optional paths execute in a real stack.
- The source-level import order creates an observation risk but does not prove
  an environment-file value or a startup defect.
- Q1 and Q2 deliberately remain uncertain. They should not be called obsolete,
  harmful, or live competitors from this evidence alone.
- U1–U4 are conservatively described as apparently unreferenced. A manual
  server command, plugin load, external import, or deployment entrypoint could
  still select them.
- The coherence suite validates only the assertions encoded in that test file;
  it neither exhausts the database/auth/profile branches nor proves a full
  deployment precedence matrix.

## Candidate follow-up slices (not performed)

1. **Core/legacy settings and startup-load contract — highest priority.**
   Define and test a single explicit process-lifetime observation contract for
   core singleton construction, dotenv loading, and the remaining legacy
   consumers. This is the highest conflicting-authority and operator-legibility
   risk; it would require a separate Architecture-Impact Task Spec because it
   could change accepted precedence or startup semantics.
2. **Database endpoint resolver contract.**
   Inventory the intended API/core/worker/migration scopes and decide whether
   their different aliases, precedence, and import-time default are intentional.
   Preserve migration/worker requirements before considering a shared resolver.
3. **Revisionless system-profile provider/model fallback.**
   Specify its relationship to ADR-074 and current supported profiles, including
   whether its raw `LLM_PROVIDER`/`CHAT_PROVIDER` fallback is still intended.
   This must distinguish legacy profile behavior from durable Persona revision
   selection and from runtime availability truth.

These are ranked by authority-conflict risk, runtime-correctness risk,
operator-legibility risk, and potential simplification value. They are not
cleanup instructions and do not authorize implementation work.

## Explicit non-claims and invariant check

- This audit does not prove harmful duplication, a configuration defect, or a
  production outage.
- It does not claim any apparently unreferenced or uncertain path is dead.
- It does not claim a provider is available, a worker ran, a database connected,
  graph writes occurred, or a release posture changed.
- It does not make runtime inventory, health, or Compose transport a new
  configuration authority; ADR-074's division of profile/operator/Compose/
  availability truth remains intact.
- No runtime behavior, precedence, variable name, import, compatibility layer,
  module, source implementation file, architecture authority, ADR, or
  current-state/release claim was changed.
- This document is evidence and reconnaissance only. Any correction of a
  documented/code discrepancy or change to an accepted configuration invariant
  requires a separate Architecture-Impact Task Spec.

## Documentation follow-through

This file is the only documentation follow-through for the audit. The current
state, release documentation, governing ADRs, and configuration contracts were
intentionally left unchanged.
