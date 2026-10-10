# Packaged runtime source fidelity and stopped core-readiness qualification

Qualification date: 2026-10-09, America/New_York; closeout audit: 2026-10-10.
Case timestamps after midnight UTC are 2026-10-10. Interaction mode: PROOF.
Overall result: **qualification stopped;
acceptance criteria remain incomplete**.

The source-attested compiled artifact preserves optional-embedding startup in
the two exercised frozen cases. It exposes an independent startup defect:
explicitly required embeddings accept an incomplete local model with no weights.
Both the backend and document worker continue running. The task's stop condition
for another compiled-artifact startup defect therefore applies. No application
startup, embedder, worker, Compose, or native-adapter repair was attempted.

Installed `core_ready=true`, `inference_ready=false`, workspace presentation,
and complete ordinary-state preservation are **not proven**. This record is not a
successful packaged-runtime qualification or a release claim.

## Authority and repository scope

The executed task is “Qualify a source-attested packaged runtime for no-model
core readiness.” The earlier [embedding-startup diagnosis](./2026-10-07-packaged-backend-embedding-startup-diagnosis.md)
is preserved unchanged, including its historical ADR numbering.

- Repository: `/Volumes/Dev_SSD/offload/codex/worktrees/5ab6/Codexify-main`.
- Branch: `codex/campaign-engine-closure`.
- Starting HEAD: `8087b0cb90b929028d58f63e047f90b4d20b281a`; worktree clean.
- Build/verification commit and frozen source:
  `553e0745abb41084b3a77f55fb3a69fe0690cbf5`.
- Authorized source changes: `backend/Dockerfile`,
  `scripts/verification/check_compiled_runtime_image.sh`, and
  `tests/ops/test_compiled_runtime_contract.py`. This is the only new repository
  documentation artifact.

Governing sources are [ADR-101](../adr/101-clone-to-ready-bootstrap-and-readiness.md)
(Proposed), the [readiness contract](../../../contracts/bootstrap/readiness.v1.json),
[ADR-069](../adr/069-codexify-beta-runtime-support-boundary.md),
[ADR-071](../adr/071-connections-control-plane-boundary.md), and the
[desktop qualification procedure](../../desktop-qualification.md).
The [current-state release gate](../00-current-state.md) remains HOLD. No ADR,
readiness semantics, signing configuration, supported path, or release claim
changed. The proposed next repair appears aligned with the existing required
embedding gate; it does not constitute ADR acceptance or repair authorization.

## Source and artifact identity

Task-owned operational evidence is retained at:

```text
/Volumes/Dev_SSD/offload/codex/proofs/packaged-source-fidelity-20261009-553e0745a
```

Receipt filenames below are relative to this directory. They contain selected
nonsecret evidence; qualification credential files are not reproduced here.

| Field | Recorded value |
| --- | --- |
| Frozen source revision / OCI revision label | `553e0745abb41084b3a77f55fb3a69fe0690cbf5` |
| Compiled source archive SHA-256 | `c7de8f2b7573abf2ff7587351814d7a3433a6dd899ab3a41f854d64e2cbc5836` |
| Platform | `linux/arm64` |
| New local image tag | `ghcr.io/resonant-jones/codexify-runtime:proof-553e0745a-20261009` |
| Verified Docker image ID | `sha256:f26bd88140de7b54de5323d6e6450eca6c897f719f9ed768d438032ee3c6b7d3` |
| Frozen `/app/runtime/codexify-runtime` SHA-256 | `9741f8f9882d89ca8766cb0202f065751c30061e32687822db9a0059341e6c01` |
| Packaged source archive SHA-256 | `92864b94dcb1777942f07bdd0523f7bef4214a735c524820322e05fbdb63665d` |
| Installed app executable SHA-256 | `16c8c0e6f89ccfee5cb92b738025b80ab9c102f570096289dd1414f39e577724` |

`git archive` supplied committed runtime inputs to `compiled-context`, including
the Dockerfile, backend, Guardian, config, builtin help, and PyInstaller inputs.
Untracked files, local environment/credential material, and models were excluded.
`build.json` and `context-files.json` record the archive identity and input scope.
The compiled builder now sets `HF_HUB_OFFLINE=1` and `TRANSFORMERS_OFFLINE=1`
during freezing. Container build dependencies were permitted; no model was
acquired. The local-beta tag was not overwritten by the build.

The recorded build command, abbreviated only through the task-directory variable:

```sh
task_proof=/Volumes/Dev_SSD/offload/codex/proofs/packaged-source-fidelity-20261009-553e0745a
docker build --platform linux/arm64 --target compiled-runtime \
  --build-arg CODEXIFY_SOURCE_REVISION=553e0745abb41084b3a77f55fb3a69fe0690cbf5 \
  --progress plain --iidfile "$task_proof/image-id.txt" \
  -t ghcr.io/resonant-jones/codexify-runtime:proof-553e0745a-20261009 \
  -f "$task_proof/compiled-context/backend/Dockerfile" \
  "$task_proof/compiled-context"
```

Build exit: 0; PyInstaller completed (`build.json`, `build.log`).
`image-identity.json` records the OCI revision match and immutable image ID.
Docker also returned a local RepoDigest with the same digest. That is observed
local metadata, not evidence of registry publication. Nothing was pushed.

The enhanced verifier resolves the local image once, validates its immutable ID,
compares the expected full revision before running, and pins all subsequent
inspection to that ID. Its container uses `--rm --pull never --network none
--read-only --entrypoint sh`. Structural checks and executable hashing remain
distinct from behavioral readiness.

```sh
bash scripts/verification/check_compiled_runtime_image.sh \
  ghcr.io/resonant-jones/codexify-runtime:proof-553e0745a-20261009 \
  553e0745abb41084b3a77f55fb3a69fe0690cbf5
```

Exit: 0 (`verifier.json`, `verifier.log`). An independently executed image
inventory found no `/models` and repeated the executable hash
(`model-inventory.json`). An expected revision of forty zeros against the pinned
image ID rejected with exit 1 before container execution
(`provenance-negative.json`). The label is corroborated by the recorded build
context and command; it alone does not prove behavior.

## Actual frozen-runtime cases

These cases used project `codexify-qualification-frozen-553e0745a-20261009`,
fresh task-owned storage, and initially free loopback ports 22820–22825.
`frozen-cases/case.json` records resolved image references, mounts, and commands.
Backend, migrator, chat-worker, and document-worker references all selected the
qualified image. Actual backend/document-worker image IDs were inspected below.
The successful `--rm` migrator's actual image ID was not independently retained;
resolved configuration is not substituted for that missing observation.

The recorded Compose operations used the existing materialized runtime Compose
file, the task's selected environment file, and the explicit frozen-case project:

| Command suffix | Result |
| --- | --- |
| `up -d --pull never --wait --wait-timeout 120 db redis` | Exit 0; healthy task-owned database and Redis |
| `run --rm --no-deps --pull never migrator` | Exit 0 on fresh case storage |
| `up -d --no-deps --pull never backend worker-document-embed` | Exit 0 |

Task-owned `incomplete.yml` and `required.yml` overrides recreated only the case
backend and document worker with `--no-deps --pull never`; repository Compose
files were not edited. Required-case observation was bounded at 120 seconds.
Optional observations included successful startup, a real vector-health probe,
and continued worker availability after an additional idle interval.

The selected embedding controls used the real local backend, never a mock:

```text
LOCAL_EMBED_MODEL=/models/bge-large-en-v1.5
CODEXIFY_EMBEDDINGS_BACKEND=local
CODEXIFY_ALLOW_EMBEDDINGS_FALLBACK=0
HF_HUB_OFFLINE=1
TRANSFORMERS_OFFLINE=1
LOCAL_EMBEDDINGS_REQUIRED=0 for optional cases; 1 for required cases
```

The absent case used a fresh empty model volume, independently inventoried in
`optional-absent-model-inventory.json`. The incomplete case's read-only `/models`
bind contained only `bge-large-en-v1.5/modules.json` with `[]` and
`config_sentence_transformers.json` with `{}`. There were no weights or copied
model assets. No model-prep command was executed.

| Case | Observed frozen behavior | Acceptance result |
| --- | --- | --- |
| Optional, absent | Backend `/ping` HTTP 200; document worker started and stayed running. `/health/vector` HTTP 200 with `status=down`, `ok=false`, and missing local-directory error. | PASS for exercised backend/idle-worker and unavailable-capability surface |
| Optional, incomplete | Backend `/ping` HTTP 200; document worker started and stayed running. Vector health remained `down`, `ok=false`, with `index 0 is out of range`. | PASS for exercised surface |
| Required, absent | Pinned-image backend invocation exited 1, reporting `LOCAL_EMBEDDINGS_REQUIRED=1` and the missing model directory with provisioning guidance. | PASS for backend only; absent-model document-worker case not separately exercised |
| Required, incomplete | Backend became healthy, `/ping` HTTP 200; document worker started. Both remained running throughout the bounded observation despite required embeddings and unusable assets. | **FAIL: required startup did not fail closed** |

The required-absent invocation used `docker run --rm --pull never --network none
--read-only` with the required/offline/no-fallback controls and the immutable
image ID; exact argv, stderr, and exit are retained in `required-absent.json`.
Its suggestion to run model-prep was diagnostic text only, not an executed action.

Each actual container below reported `.Image` equal to the verified image ID:

| Case | Backend container ID | Document-worker container ID |
| --- | --- | --- |
| Optional absent | `7a63b275e4e417bfeb58a27bbea9ebd3bff230d802da71dc73da2b963e6b537b` | `3104d313e953ce0ed11d914b589fcf0a14eb38527dfd62caf17365bafdaaabed` |
| Optional incomplete | `9eb60db8a974dec3b53c01fe60407feceec0f90312c21944fbad3141310cef92` | `6d36f1c1661fe43d2131764c98c661c37a4ffbc79a71e311b4588eccea81bff8` |
| Required incomplete | `64b9717218d41d55310c5e967d03f12eca253c1d6b1cbd7bb118f31680dcc3d8` | `0e9ff688dfc3841469b935cf4f3e388f99b8188788b40d62a6648a76f17e2362` |

Receipts: `optional-absent-complete.json`, `optional-incomplete.json`, and
`required-incomplete.json`, plus case-specific backend/worker logs, under
`frozen-cases/`. The independent `required-incomplete-blocker.json` additionally
captures actual required/offline/no-fallback environment values, read-only mount,
fixture inventory, healthy/running states, image IDs, and `/ping` response.
The behavioral harness exited 1 because its required-startup assertion failed.
This failed validation remains part of the result; passing focused tests do not
override it. No installed readiness boolean was observed in this frozen case.

## Independent startup blocker and code-path explanation

`proven-live-runtime`: the required-incomplete case violates the task's explicit
fail-closed startup criterion. Configuration, mount, image identity, and absence
of weights were independently observed. This is not the previously diagnosed
old-image eager optional startup failure.

`proven-code-path`: `backend/compiled_runtime_entry.py::_run_backend` rejects a
missing required model directory but does not validate existing model contents.
Backend startup reaches `guardian/core/dependencies.py::init_services`, which
uses `VectorStore(initialize_embedder=True)` when embeddings are required.
`guardian/workers/document_embed_worker.py::run_forever` selects the same required
initialization. `guardian/vector/store.py` constructs the embedder, and
`backend/rag/embedder.py::_init_sentence_transformer` accepts a successfully
constructed SentenceTransformer without an additional usability check.
Offline recovery rejects downloads when construction throws; that rejection
does not validate a successfully constructed but unusable model.

`working-theory`: acceptance of the empty-module fixture during construction,
followed by failure during real embedding use, explains the observed startup
success. No additional instrumentation proved every internal step. The runtime
failure criterion is proven independently of this explanation.

## Packaged application and installed attempts

The app was rebuilt from a separate full tracked archive of the same frozen
revision (`packaged-build-inputs.json`). Existing dependency directories were
linked for build use and an existing release dependency cache was cloned. The
application crate was cleaned before `CARGO_NET_OFFLINE=true cargo tauri build
--bundles app`; exit 0 (`packaged-build.json`, `packaged-build.log`). No host
dependency installation or download was performed. Build dependency reuse is
recorded rather than represented as a hermetic dependency rebuild.

The completed app was copied into the task-owned `installed/Codexify.app`.
Proof-only `codesign --force --deep --sign -` and strict deep verification both
exited 0; CodeResources existed. `spctl --assess --type execute --verbose=4`
exited 3 (rejected). Ad hoc structural signing does not establish distribution
trust or notarization (`installed-artifact.json`).

All attempts used the actual packaged native adapter and existing qualification
controls. Namespace receipts record isolated runtime/data paths, derived ports,
WebKit datastore UUID, Compose project, and qualification Keychain service.

| Qualification ID | Ports | WebKit UUID | Result |
| --- | --- | --- | --- |
| `source-553e0745a-20261009` | 31050–31055 | `793f738e-558e-5e0c-9d12-1d9fff02a6f7` | Image selection was applied too late; initial native setup used local-beta. Subsequent restart left mixed artifacts. Excluded from successful source-fidelity proof. |
| `attested-553e0745a-20261009` | 40930–40935 | `1b23e408-8fd3-5369-bb7e-2da400affa61` | Precreating the runtime directory for image selection triggered the existing unmanaged-root guard. No ownership metadata was fabricated to bypass it. |
| `managed-553e0745a-20261009` | 27690–27695 | `149470d0-06ad-5556-886a-cf43fe1c68c0` | Real app materialization preceded selection; bootstrap started but was stopped when the independent required-model defect was established. |

The first attempt's supplied UI command detail shows native setup completed,
WebUI built, DB/Redis became healthy, and the initial backend exited 3 with the
old image. The user's targeted restart command used:

```text
restart db redis backend worker-chat
up -d --no-deps db redis migrator backend worker-chat
```

This is not evidence of an additional dependency-following invocation. The
subsequent migrator exited 1 with
`project_ownership_reconciliation_unresolved`, project 1,
`unresolved_no_referencing_threads`. `installed-migrator.log` preserves this
failure. `installed-container-observation.json` records new-image backend,
migrator, and chat-worker identities while the document worker still referenced
the old local-beta image. The namespace had already been initialized by the old
artifact; its exact data evolution was not established. This contaminated
attempt is not a clean migration test of the new image and was not repaired.

For the managed attempt, the real app wrote its runtime manifest and packaged
marker before its process was paused with SIGSTOP. The project had zero
containers at selection. Only the namespace `.env` was then written through
existing registry/tag controls, with optional/offline/no-fallback embeddings and
deliberately unavailable inference at the derived port 27695. SIGCONT resumed
the unchanged adapter; native setup generated credentials while preserving
selection. No alternate image-selection mechanism or fabricated manifest was
introduced (`managed-namespace.json`).

The last observed managed inventory showed backend `445ca8efb3f0` running with
health starting; chat worker `2f3fc5b83ebe` and document worker `0f0899f1041b`
created with the qualified image reference; WebUI `11c6dd75914d` created;
DB `49f8913240c1` and Redis `c9396005533d` healthy. Full actual runtime image IDs
for this attempt and its removed migrator were not captured before stopping.
These references and partial startup observations do not satisfy the installed
container-identity or readiness criteria.

The task-owned installed app process group 12834 was terminated after its
executable path was checked (`qualification-stop.json`). Qualification containers
and volumes were retained; no cleanup or daemon restart was performed. Native
accessibility and window capture had been unavailable, so there is no workspace
visual proof. Qualification was not resumed to fill that gap after the stop.

## Isolation, preservation, and remaining unknowns

Before launch, `before.json` recorded 1,782 ordinary filesystem entries, 65
existing containers, 136 existing volumes, and nonsecret ordinary Keychain
metadata. Case and installed attempts used separate explicit projects and fresh
namespace paths, selected loopback ports, and task-owned model fixtures. Ordinary
Codexify volumes were not attached by the recorded task operations. The previous
failed qualification namespace was retained.

An initial final snapshot failed when Docker returned HTTP 500 for container/image
inspection and a subsequent server-version read. Automatic approval review then
rejected the elevated filesystem/Keychain metadata comparison because the
workspace was out of credits; that command did not execute. No approval bypass
was attempted.

After approval succeeded for the documentation commit, a separately reviewed,
read-only audit ran on 2026-10-10. All 1,782 baseline filesystem entries matched,
with no file-read errors or unexpected ordinary additions. The 74 additions were
limited to the exact recorded qualification WebKit datastore paths. Ordinary
`guardian_api_key` Keychain metadata matched its baseline hash and exit status;
the audit did not retrieve the password value.

```sh
python3 /Volumes/Dev_SSD/offload/codex/proofs/packaged-source-fidelity-20261009-553e0745a/final_preservation_check.py
```

`after-final-audit.json` and `preservation-final-comparison.json` retain those
observations. The audit exited 2 for partial evidence because Docker again
returned HTTP 500 on `containers/json?all=1`. Baseline container/volume comparison
and final local-beta identity remain unavailable; ordinary filesystem/Keychain
metadata preservation does not substitute for them. Task containers may remain
running. The Docker failure's cause is unknown and was not repaired or conflated
with the embedding startup defect.

Other unproven acceptance surfaces are actual image-ID equality for every
installed runtime role, installed migrations on the valid selected attempt,
all required core services running, native `core_ready=true`,
`inference_ready=false`, real workspace presentation, and truthful unavailable
inference UI. Successful chat, ingestion/retrieval, persistence/relaunch, and
distribution trust remain outside this proof.

## Validation and documentation follow-through

Before freezing the build commit, repository validation passed:

```sh
git diff --check
bash -n scripts/verification/check_compiled_runtime_image.sh
.venv/bin/python scripts/generate-bootstrap-bindings.py --check
.venv/bin/python scripts/validate_docs.py
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest -q -p no:cacheprovider \
  tests/ops/test_compiled_runtime_contract.py \
  tests/ops/test_registry_runtime_compose_contract.py \
  tests/vector/test_vector_store_resolution.py \
  tests/workers/test_document_embed_worker.py \
  tests/backend/rag/test_embedder.py
```

Focused result: 37 passed. Provenance tests exercise the Dockerfile revision
validator and fake-Docker command audit, including invalid/missing/mismatched
revision, immutable-ID pinning, local-only inspection flags, failure propagation,
and structural-only labeling. They do not establish installed behavior.

The matching live verifier passed; its deliberate mismatch rejected as expected.
Both builds passed. Frozen optional cases passed the exercised surface;
required-absent backend rejected as expected; required-incomplete behavioral
validation failed. Structural signing passed and distribution assessment
rejected. Final filesystem/Keychain metadata comparison matched; the Docker
preservation comparison was unavailable (audit exit 2). These outcomes remain
separate.

This documentation artifact is the only documentation follow-through. Current
state, architecture README, ADR index, ADR-101, desktop qualification instructions,
and the historical diagnosis are unchanged. `.venv/bin/python
scripts/validate_docs.py`, `git diff --check`, and the new-file whitespace check
passed for this artifact. No new runtime source was changed after the frozen
build commit. Git and images are not pushed.

## Recommended next independent slice

Validate explicitly required, pre-provisioned local embedding assets before
backend and document-worker startup succeeds. Reject the reproduced empty-module
fixture with an actionable error while preserving optional lazy startup,
offline behavior, and disabled fallback. Directory existence or successful
constructor return must not be treated as proof of a usable embedding capability.

Likely repair surface: `backend/rag/embedder.py` and its focused tests, with
read-only evaluation of the existing validation helper in
`guardian/scripts/ensure_embed_model.py`, required startup entry in
`backend/compiled_runtime_entry.py`, and backend/worker call sites before fixing
the exact allowlist. Required proof afterward includes a newly frozen compiled
artifact, both required absent/incomplete cases for backend and document worker,
and regression of both optional cases. Model acquisition, OOM, migration data,
restart behavior, Compose topology, native workspace probes, and signing remain
separate work. Installed qualification and preservation comparison must later
resume under explicit scope once the startup gate is repaired and Docker access
is available. This recommendation is not implementation authority.
