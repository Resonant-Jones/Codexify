# Packaged backend embedding startup diagnosis — 2026-10-07

## Determination

**Selected classification: READINESS_SEMANTICS.** The observed packaged backend makes optional embedding availability a prerequisite for application lifespan completion and therefore for `core_ready`. This contradicts the branch-local Clone-to-Ready contract. The current branch already defers embedding construction at the blocking startup seam; the frozen registry runtime used by the packaged adapter demonstrably executes different behavior. The bounded next outcome is runtime artifact/source fidelity, not another embedding initialization repair or model download.

The model path is correctly selected for a separately provisioned embedding capability. No inspected contract requires weights to be baked into the runtime image. Missing weights establish unavailable embedding capability, not an image-content contract violation. This distinction is why the task's narrowly defined `IMAGE_FIDELITY` classification is not selected despite the proven executable-behavior mismatch.

## Scope, provenance, and authority

- Lane: architecture-impact; interaction mode: REPORT / PROOF; runtime/source investigation read-only.
- Requested checkout: `/Users/chriscastillo/.codex/worktrees/5ab6/Codexify-main`; verified physical checkout: `/Volumes/Dev_SSD/offload/codex/worktrees/5ab6/Codexify-main`.
- Starting branch: `codex/campaign-engine-closure`.
- Starting HEAD: `bbf38778b36ddf8d0f0ae0e7a4aae7ae806a8ecf`.
- Starting worktree: clean; branch already one local commit ahead of its remote-tracking ref. No fetch or push was performed.
- Only authorized change: this proof artifact. No runtime source, configuration, Compose file, model, signing, readiness contract, or release claim was changed.
- Governing sources: [readiness.v1.json](../../../contracts/bootstrap/readiness.v1.json), [ADR-099](../adr/099-clone-to-ready-bootstrap-and-readiness.md), [desktop qualification](../../desktop-qualification.md), and [current release truth](../00-current-state.md). ADR-099 remains **Proposed**; overall release posture remains **HOLD**.
- Current image/container metadata and retained backend logs are direct observations. Source traces and focused tests are code-path/test evidence. Prior qualification receipts are historical evidence, not a new installed-app qualification.

The authoritative configuration belongs to the local operator and task-scoped adapter contract. Docker transports configuration and executes the selected artifact; its tag does not establish source revision. PostgreSQL remains owned durable state. Model/cache volumes hold capability assets, not authorization or core-readiness authority. This diagnosis concerns buggy components and artifact/configuration disagreement across host, container, and asset-acquisition boundaries; it creates no new permissions or network capability.

The supplied task's image-mismatch stop condition is reached at the repair boundary: the selected frozen runtime does not implement current branch startup semantics, and replacing it requires separately authorized image build/selection and possibly publication. Investigation stopped at an evidence-backed report; no such operation was attempted. No unresolved human architecture choice is required to describe the contradiction: source and the Proposed ADR agree at the blocking seam.

## Files inspected

Required reads included `docs/architecture/00-current-state.md`, `docs/architecture/adr/adr-index.md`, `docs/architecture/README.md`, `docs/architecture/agent-protocol-operations.md`, `docs/architecture/adr/099-clone-to-ready-bootstrap-and-readiness.md`, `docs/desktop-qualification.md`, `contracts/bootstrap/readiness.v1.json`, `docker-compose.runtime.yml`, and `docker-compose.yml`.

The direct implementation/proof trace inspected:

- `guardian/core/dependencies.py`, `guardian/guardian_api.py`, `guardian/core/config.py`, `guardian/vector/store.py`, `guardian/utils/embed_paths.py`, `backend/rag/embedder.py`, and `guardian/workers/document_embed_worker.py`.
- `guardian/ops/setup_wizard.py`, `scripts/setup`, `.env.example`, `src-tauri/src/commands.rs`, and `src-tauri/src/qualification.rs`.
- `backend/compiled_runtime_entry.py`, `backend/compiled_backend_entry.py`, `backend/scripts/docker/run_backend.py`, `guardian/scripts/ensure_embed_model.py`, and `backend/Dockerfile`.
- `scripts/verification/check_compiled_runtime_image.sh`, `tests/ops/test_compiled_runtime_contract.py`, `tests/ops/test_registry_runtime_compose_contract.py`, `tests/core/test_embedder_preflight_dependencies.py`, `tests/vector/test_vector_store_resolution.py`, `tests/workers/test_document_embed_worker.py`, `tests/backend/rag/test_embedder.py`, `tests/conftest.py`, and `scripts/validate_docs.py`.
- Axis Node README, invocation protocol, contract, source manifest, source map, character directive, constitutional heuristic, and the task-authoring Ops anchors. The source manifest reports schema `1.0.0`. No nested `AGENTS.md` applies to the changed proof path.

Host evidence was read only from the named qualification namespace and the preceding proof directory `/Volumes/Dev_SSD/offload/codex/proofs/desktop-materialization-20261007`. Relevant evidence files were `closeout.txt`, `final-container-states.json`, and the existing artifact/build receipts. The qualification `.env` was searched only for allowlisted nonsecret embedding/image variables; its contents were not dumped.

## Configuration ownership and resolution

| Layer | Evidence and effect |
| --- | --- |
| Template/default origin | `.env.example:75` documents `LOCAL_EMBED_MODEL=/models/bge-large-en-v1.5`. `guardian/scripts/ensure_embed_model.py` independently defines that same default and `DEFAULT_EMBED_MODEL_ID=BAAI/bge-large-en-v1.5`. The compiled dispatcher also uses the path as its preflight fallback. |
| Effective source-clone assignment | `docker-compose.yml` explicitly assigns the literal path in backend/model-prep environments. A literal service environment value takes precedence over an `env_file` value; it is not `${LOCAL_EMBED_MODEL}` interpolation. |
| Effective packaged assignment | `docker-compose.runtime.yml` likewise explicitly assigns `LOCAL_EMBED_MODEL: "/models/bge-large-en-v1.5"` to backend and model-prep. The packaged adapter selects this topology; Compose transports this adapter-owned path policy to the process. |
| Generated packaged `.env` | `materialize_packaged_setup_env` (`src-tauri/src/commands.rs:1769`) backfills provider policy, credentials, image registry/tag, and URLs. Its defaults do not assign `LOCAL_EMBED_MODEL` or `LOCAL_EMBEDDINGS_REQUIRED`. The inspected qualification file contains `CODEXIFY_IMAGE_REGISTRY=ghcr.io/resonant-jones` and `CODEXIFY_IMAGE_TAG=local-beta`; no embedding-model, embedding-required, or offline override was found in that file. |
| Qualification override | `Qualification::setup_values`, `environment`, and `initial_inference` scope identity, paths, ports, URLs, and inference isolation. They do not override the embedding path. `spawn_compose_command` clears ambient application environment, supplies the isolated `.env`, and keeps bounded Docker/OS necessities. |
| Runtime consumer | `guardian.utils.embed_paths.get_local_embed_model` reads `os.getenv("LOCAL_EMBED_MODEL")`; strict mode requires an absolute existing directory. `require_local_embed_model` supplies the value to `LocalSemanticEmbedder._init_sentence_transformer` through `_get_local_embed_model(strict=True)`. Actual model construction then validates loadability, not merely directory existence. |

`guardian/core/config.py` retains deprecated `LOCAL_EMBEDDING_MODEL`; it is not the authority selecting this failing path. `CODEXIFY_CONFIG_SOURCE=core` selects configuration-coherence behavior but does not replace the direct embedding environment accessor. Dotenv uses `override=False`; the container's explicit environment wins.

The final failed-container values were independently read with an allowlist:

```text
LOCAL_EMBED_MODEL=/models/bge-large-en-v1.5
LOCAL_EMBEDDINGS_REQUIRED=0
CODEXIFY_EMBEDDINGS_BACKEND=local
CODEXIFY_ALLOW_EMBEDDINGS_FALLBACK=0
CODEXIFY_CONFIG_SOURCE=core
HF_HOME=/root/.cache/huggingface
HF_HUB_OFFLINE=0
TRANSFORMERS_OFFLINE=1
SENTENCE_TRANSFORMERS_HOME=/models
```

Thus there was no explicit request to require startup embedding validation, no mock fallback permission, and no wrong-path override. The offline guard in current source rejects recovery before invoking download when either offline flag is true. The retained frozen-runtime log instead records a recovery attempt with `TRANSFORMERS_OFFLINE=1`; this is additional behavioral disagreement, not evidence of a successful download.

## Exact image and model-path evidence

The locally available tag, inspected digest reference, and failed backend container's `.Image` all identify:

```text
ghcr.io/resonant-jones/codexify-runtime:local-beta
ghcr.io/resonant-jones/codexify-runtime@sha256:12b3990f5f7971df289e082d027f51b5345f6d9edbfd1a762dc0125651494b4d
image ID: sha256:12b3990f5f7971df289e082d027f51b5345f6d9edbfd1a762dc0125651494b4d
created: 2026-04-30T16:56:14.886734049Z
```

The image has `/app/runtime/codexify-runtime` (91,712,760 bytes), its `_internal` directory, migrations, config, and help assets. It has no `/app/guardian` or `/app/backend` source directory. Source files materialized beside the packaged app do not replace frozen executable code: the runtime Compose backend has no source bind mount.

Two ephemeral inspections used the exact digest, `--pull never`, `--rm`, `--network none`, `--read-only`, a shell entrypoint, and no attached volumes. They reported:

```text
/models: absent
/models/bge-large-en-v1.5: absent
compiled-dispatcher-present
guardian-source-directory-absent
backend-source-directory-absent
```

Image metadata declares no Docker `VOLUME`. Labels expose base-image metadata but no application source revision or promise of preloaded BGE weights. The current `backend/Dockerfile` compiled-runtime target copies the frozen distribution, config, help, and migrations; it neither downloads nor copies model weights. The compiled-image verification script checks artifact structure, not a preloaded embedding model. The source revision/build process that produced this particular image remains unknown; its creation timestamp alone is not source provenance.

The failed backend `a2f8e321aeb2` mounts:

```text
codexify-qualification-installed-bbf38778b-20261007_codexify_models -> /models
codexify-qualification-installed-bbf38778b-20261007_hf_cache -> /root/.cache/huggingface
```

Model-prep `f577d4f6c930` mounts those exact same qualification volumes. Other backend mounts are qualification-scoped CLI home, Chroma, and media volumes. The model volume controls the runtime path and would shadow any image content there; in this image there is no model directory to shadow or initialize by volume copy-up. No ordinary Codexify volume was attached to an inspection container.

A read-only `docker cp ...:/models/bge-large-en-v1.5/. - | tar -tvf -` stream inspected the retained stopped qualification container's mounted path without extracting or modifying it. This is its post-failure inventory, not a snapshot before the first backend launch:

| Completed model-directory file | Bytes |
| --- | ---: |
| `.gitattributes` | 1,519 |
| `1_Pooling/config.json` | 191 |
| `README.md` | 94,607 |
| `config.json` | 779 |
| `config_sentence_transformers.json` | 124 |
| `modules.json` | 349 |
| `sentence_bert_config.json` | 52 |
| `special_tokens_map.json` | 125 |
| `tokenizer.json` | 711,396 |
| `tokenizer_config.json` | 366 |
| `vocab.txt` | 231,508 |

The inventory also contains an empty `onnx` directory and Hugging Face download metadata/locks under `.cache/huggingface/download`, plus three `.incomplete` blobs of 1,340,698,349, 1,336,854,281, and 1,073,741,824 bytes. There is **no completed `model.safetensors` or `pytorch_model.bin`**, no completed `onnx/model.onnx`, and no `.codexify_model_ok` sentinel. Partial blobs are not usable weights.

`ensure_embed_model._model_status` requires SentenceTransformer configuration markers plus `model.safetensors` or `pytorch_model.bin` at the root or in `0_Transformer`. The retained directory meets the configuration-marker criterion and fails the weight criterion. The backend log independently reports no supported completed model-weight file. Therefore neither the bare image nor the observed mounted directory contains a complete model at the selected path. No model loader or provisioning script was executed by this diagnosis.

## Blocking backend startup chain

The failed backend's live metadata records `Path=/app/runtime/codexify-runtime`, `Args=["backend"]`, `ExitCode=3`, and `OOMKilled=false`. The current dispatcher/entrypoint sources explain process routing; the retained traceback provides the exact frozen-runtime blocking frames:

```text
/app/runtime/codexify-runtime backend
  -> compiled runtime backend role / backend entrypoint
  -> import guardian.guardian_api:app; uvicorn.run(app)
  -> FastAPI / Starlette application lifespan startup
  -> guardian/guardian_api.py:586 app_lifespan
  -> guardian/core/dependencies.py:775 init_services
  -> guardian/vector/store.py:98 VectorStore.__init__
  -> backend/rag/embedder.py:701 Embedder.__init__
  -> backend/rag/embedder.py:271 LocalSemanticEmbedder.__init__
  -> backend/rag/embedder.py:294 _init_embedding_model
  -> backend/rag/embedder.py:320 _init_sentence_transformer
  -> _get_local_embed_model -> require_local_embed_model
  -> SentenceTransformer(..., local_files_only=True)
  -> missing model weights / load exception
  -> _recover_local_model_once:392 raises RuntimeError
  -> unhandled lifespan failure; Application startup failed. Exiting.
  -> observed process exit 3; no core API readiness
```

Frozen-trace line numbers above belong to the image and must not be interpreted as current checkout line numbers. Dispatcher function routing is corroborated by `backend/compiled_runtime_entry.py:118-143`, `_run_backend:16-36`, and `backend/compiled_backend_entry.py:29-35`; a frozen source-revision attestation was not found.

The retained log shows an initial failure at `2026-10-07T15:37:08Z`: the model path was not an existing directory. A later startup at `15:37:30Z` found the partial directory but failed because weights were absent:

```text
LOCAL_EMBED_MODEL '/models/bge-large-en-v1.5' could not be loaded
from local cache. Auto-download was attempted and failed:
Error no file named pytorch_model.bin, model.safetensors, tf_model.h5,
model.ckpt.index or flax_model.msgpack found in directory
/models/bge-large-en-v1.5.
```

This is **application-lifespan dependency initialization -> vector-store construction -> embedder construction**, not the primary import-time failure, worker startup, or a health-handler invocation. The image logs successful module load and then “Waiting for application startup” before failure. Uvicorn does not complete startup to serve the required `/ping` and core health surfaces. Core readiness is blocked indirectly because the backend never becomes available, not because the readiness adapter explicitly probes embedding health.

## Model-prep and Compose dependency intent

Both Compose files formally declare backend dependencies on healthy DB, successfully completed migrator, model-prep, and graph-init. Chat/document workers also declare model-prep completion. Thus an ordinary dependency-following Compose `up` can introduce model-prep even when only backend/chat services are named. This is an executable graph, not proof that model preparation belongs to core bootstrap.

Model-prep owns embedding asset preparation: `backend.compiled_runtime_entry._run_model_prep` dispatches to `guardian.scripts.ensure_embed_model.main`; source Compose runs that script directly. It prepares `BAAI/bge-large-en-v1.5` into `/models/bge-large-en-v1.5`, uses the shared model lock/cache, validates configuration and completed weights, and supports a revision override. It does not prepare the local chat inference model. Under ADR-099 it is deferred embedding/document/retrieval capability preparation, not a prerequisite for opening the core workspace or establishing chat-provider health.

The canonical adapters deliberately bypass optional dependencies:

```text
scripts/setup:
  up -d --wait ... db redis
  run --rm --no-deps migrator
  up -d --no-deps backend worker-chat worker-document-embed frontend

commands.rs core_bootstrap_compose_stages(packaged=true):
  build webui
  up -d --wait --wait-timeout 180 db redis
  run --rm --no-deps migrator
  up -d --no-deps backend worker-chat worker-document-embed webui
```

The preceding proof's `closeout.txt:103-118` records an additional command `up -d db redis migrator backend worker-chat`, without `--no-deps`. That command's dependency expansion explains the appearance of model-prep/Neo4j/graph-init. The receipt explicitly says no Restart Services control was activated by the preceding agent and the invocation cause was not established. The current desktop log records materialization, not a causal command receipt. **Who or what invoked that additional command, and why, remain unknown.** It must not be attributed to the canonical staged startup based on service presence alone.

Model-prep's live metadata records start `15:37:24.089212001Z`, finish `15:39:14.024231678Z`, exit 137, `OOMKilled=true`. Its log records model-lock acquisition and a first BGE download attempt. The backend's first failure predates model-prep's start, and its later missing-weight failure predates the OOM finish. The OOM is not the cause of the original lifespan coupling and is not required to explain it. Allocation cause, resource repair, and invocation behavior were not investigated further.

The qualification runtime Compose file is byte-identical to the branch copy; both SHA-256 values are `02011472307f0970fe204cb4b8e07f81b64358ad194098abd833c17dadac5ca9`. There is no evidence of a qualification-specific embedding-path or dependency override.

## Readiness contract and adapter comparison

`readiness.v1.json` defines core readiness as healthy required application services, migrations, and workspace presentation. It permits onboarding access and does not prove inference or full supported-runtime qualification. ADR-099 explicitly states that both adapters defer model preparation and that optional embedding assets no longer gate backend/document-worker startup unless `LOCAL_EMBEDDINGS_REQUIRED` explicitly requests startup validation.

| Capability | Required for `core_ready`? | Evidence/qualification boundary |
| --- | --- | --- |
| Backend API/core health | Yes | Available API and observed core startup/health are required. |
| PostgreSQL, migrations, Redis, required workers | Yes | Adapters stage DB/Redis and migration; core inventory and queue/chat infrastructure are checked. Running the document worker does not prove successful ingestion. |
| Workspace presentation | Yes | Contract requires it. Source setup probes frontend HTTP; native packaged snapshot currently treats `workspace_ready` as true for packaged mode. Installed workspace entry still needs actual observation and was not reached. This neighboring implementation difference is deferred. |
| Configured chat-provider/model inference | No | Separate `inference_ready`; unavailable inference leaves core onboarding possible and chat unavailable. |
| Embedding model availability | No by default | Explicit `LOCAL_EMBEDDINGS_REQUIRED=1` is the source startup opt-in exception; observed packaged value was 0. |
| Successful document ingestion/embedding | No | Requires actual capability assets/task completion; not established by idle-worker existence. |
| Successful semantic retrieval | No | Requires real embedding/vector capability and its own proof. |

Current source at the blocking seam is already aligned:

- `guardian/guardian_api.py` calls `dependencies.init_database` and `init_services` inside `_app_lifespan_body` (`615-618`).
- `guardian/core/dependencies.py:1275-1286` resolves `LOCAL_EMBEDDINGS_REQUIRED` and calls `VectorStore(initialize_embedder=required)`; absent/0 means false.
- `guardian/vector/store.py:68-88` resolves vector runtime metadata and leaves `_embedder=None` when initialization is deferred. First `embedder` access acquires the lock and constructs the actual capability; constructor default remains eager for explicit consumers.
- `guardian/workers/document_embed_worker.py:215-218` uses the same opt-in rule while waiting for tasks.
- `backend/rag/embedder.py:378-385` rejects offline recovery before the download call. A missing/invalid path or missing weights still fails real capability use; optionality does not supply fake vectors or report ingestion/retrieval success.
- Lifespan's later `seed_global_system_docs(get_vector_store())` may attempt capability work, but is inside a caught, logged soft-failure block (`guardian_api.py:620-634`). This report does not claim that all embedding-related work is absent during startup; the point is that optional model failure does not escape that block to gate core startup.

Canonical source Compose binds the checkout's Guardian/backend sources and uses `run_backend.py -> uvicorn guardian.guardian_api:app`. Packaged Compose executes the registry image's frozen dispatcher with no source bind mounts. Therefore source-clone and packaged adapters **agree in intended staging/readiness semantics but currently diverge at runtime implementation** for unavailable embeddings: current source defers the blocking construction, whereas the inspected packaged image eagerly constructs it despite `LOCAL_EMBEDDINGS_REQUIRED=0`.

This is code-path plus narrow-test evidence for source behavior, not a fresh absent-model source-clone live installation. Prior ADR source-install observations are historical. A full current source lifespan experiment was neither manufactured against ordinary data nor claimed from mocked tests.

## Classification alternatives

| Candidate | Supporting observation | Contradicting/limiting evidence | Decision |
| --- | --- | --- | --- |
| IMAGE_FIDELITY | Image contains no model; executable behavior differs from branch source. | This task permits this classification only when a model-preload contract is violated. No such contract was found; Compose gives model-prep/volume ownership and the build recipe contains no weights. Source-revision provenance is unknown. | Not selected. Behavior fidelity is the repair mechanism, not proof of required preloaded weights. |
| CONFIGURATION | Effective path points to unavailable/incomplete capability assets. | Path matches template, preparation script, mounted target, and both adapters. Required flag is 0. Qualification adds no embedding override. A temporarily unavailable optional capability does not itself make the path wrong. | Not selected. |
| READINESS_SEMANTICS | Live lifespan trace gates backend on embedding; final flag is 0; contract explicitly defers this capability; source has a lazy constructor at the same seam. | Full supported Beta still includes documents/retrieval/local inference, and generic Compose declares model-prep dependencies. Those are broader support/capability obligations, not the intermediate core-onboarding contract; canonical staged bootstrap bypasses them. | Selected. |
| COMBINED | Frozen implementation mismatch and partial asset directory coexist. | No independent wrong configuration or model-preload obligation was proved. Model-prep OOM is separate and occurred after original backend failure. | Not selected; multiple symptoms do not establish multiple contract faults. |

The violated contract is the branch-local optional-model/core-readiness separation in Proposed ADR-099 and `contracts/bootstrap/readiness.v1.json`, not an accepted promise that the packaged image contains BGE weights. The live failure does not amend the supported Beta boundary or qualify packaged desktop.

## Validation and remaining limits

Three existing hermetic tests passed (exit 0):

```sh
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest -q -p no:cacheprovider \
  tests/vector/test_vector_store_resolution.py::test_core_store_defers_model_initialization_until_capability_use \
  tests/workers/test_document_embed_worker.py::test_idle_worker_defers_optional_model_until_a_task \
  tests/backend/rag/test_embedder.py::test_offline_model_recovery_never_downloads
```

These prove deferred construction, idle-worker optionality, and offline download rejection in branch source using stubs/in-memory fixtures. They do not prove packaged backend health or a complete source setup. No runtime source test suite is required for this documentation-only change.

Documentation validation: `git diff --check` passed; `PYTHONDONTWRITEBYTECODE=1 .venv/bin/python scripts/validate_docs.py` passed (exit 0); all four proof-local Markdown links resolve. The final untracked-file diff and staged whitespace check are reviewed before commit. The repository validator checks its established architecture corpus, not every newly created proof file; proof-local links were checked separately.

Remaining unknowns: exact source revision/build provenance of the frozen image; why the dependency-following command was invoked; the historical cause of image/tag drift; and model-prep allocation failure. Partial asset inventory is post-failure state. No new workspace-entry, inference/chat, conversation persistence/relaunch, ordinary-runtime comparison, full platform, or release qualification is asserted.

Documentation follow-through is this artifact only. Architecture README, ADR index, ADR-099, current-state, and desktop qualification documentation are deliberately unchanged. No memory/KB writes were performed; a future artifact-provenance record would be useful after the separately authorized repair is proved.

## Bounds of the one recommended implementation outcome

The eventual repair appears **aligned with existing Proposed ADR-099**, `readiness.v1.json`, ADR-069's intermediate-onboarding/support distinction, and ADR-071's configuration/authorization/health separation. It does not appear to require an ADR amendment. This diagnosis neither accepts nor amends any ADR.

The follow-up should build/qualify a compiled runtime from an explicitly recorded current branch revision and make packaged image selection resolve that qualified artifact rather than relying on the present unqualified `local-beta` tag. It should carry existing lazy backend/document-worker startup and offline recovery into the actual executable; no new lazy-loading refactor is justified by this evidence.

Exact likely file surfaces, if durable selection/provenance changes are needed: `docker-compose.runtime.yml`, `src-tauri/src/commands.rs` (image defaults/selection), `scripts/verification/check_compiled_runtime_image.sh` (behavior/provenance qualification), `tests/ops/test_registry_runtime_compose_contract.py`, and `tests/ops/test_compiled_runtime_contract.py`. `backend/Dockerfile` and `packaging/pyinstaller/codexify_runtime.spec` are existing build inputs to verify; change them only if the new artifact fails to include the already-present implementation. A separate task must explicitly authorize its final allowlist and any image publication. This list is a recommendation, not edit authority.

Intended tests: retain the three existing focused tests; cover packaged image selection/provenance and real frozen optional/required embedding behavior with absent and incomplete local assets; verify `LOCAL_EMBEDDINGS_REQUIRED=1` remains fail-closed and offline recovery makes no network request. Static file-presence tests alone are insufficient.

Live proof afterward: in the approved isolated qualification namespace, select and record the new exact digest/source revision, retain staged `--no-deps` bootstrap, and observe backend health, idle core workers, actual `core_ready`, and workspace entry with embedding/inference unavailable and no model-prep acquisition. Preserve configuration and owned volumes; record ordinary-state isolation again. Missing embedding must still fail real document/retrieval capability use without fake success. Successful core proof would not establish inference/chat or persistence/relaunch.

Explicitly deferred: model downloads/copying/provisioning, model-prep OOM, the additional dependency-following invocation cause/restart behavior, generic Compose dependency edits, packaged workspace-probe changes, provider/inference configuration, document/retrieval success, conversation persistence/relaunch, signing/notarization, desktop qualification isolation changes, ADR promotion/amendment, and all release/support claims.

Recommended next slice:
Qualify and select a source-attested compiled packaged runtime that preserves the existing optional-embedding startup contract, then prove isolated no-model core readiness without model preparation.
