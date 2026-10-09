# Natural OpenAI account import-to-recall proof R5 — 2026-10-09

## Result and first boundary

**Overall: BLOCKED at supported authenticated-account setup, before live import.**

The fresh, task-owned PostgreSQL/Redis runtime, backend, account-import worker,
chat-embedding worker, and chat worker started. The backend and embedding/chat
workers loaded the real local BGE model. The selected local provider was
reachable through a transparent task-owned capture sidecar. However, every
registration/login alias returned HTTP 404 under the prescribed
`v1-local-core-web-mcp` profile. That profile quarantines `auth`; the existing
operator provisioning commands require different Preview/tester postures.

No supported provisioning and session-issuance procedure for two independent
accounts was established within this task's authorized posture. Qualification
stopped at that prerequisite. No application correction, profile amendment,
manually seeded account/session workaround, or `X-User-Id` simulation was used.
This is **not** an observed importer, embedding, retrieval, or provider-answer
failure. Natural recall and negative account isolation remain unproven.

Release **HOLD remains unchanged**. No Preview admission, runtime-support,
VaultNode qualification, or release-readiness claim follows from this receipt.

## Frozen source and workspace

- Evaluated HEAD: `4eb460449096fefc5098ff700ef75034efeac521`, containing the prior
  synthetic qualification. Branch:
  `codex/synthetic-account-import-recall-qualification`.
- Physical checkout:
  `/Volumes/Dev_SSD/offload/codex/worktrees/synthetic-import-recall/Codexify-main`.
  Initial and pre-artifact `git status --short` were empty. The alleged additional
  seven-line edit was absent: the prior qualification artifact had no working
  diff. No prior proof or test was edited.
- Parent/source local main:
  `82971cc92383bc39db1aa5a1506ddc183572f74e`, with October 9 current-state.
  This was not the old VaultNode review source `228f34ce6`.
- At orientation, local main was six commits ahead/nine behind cached remote
  main `5c6e2ca76bb9680457594bb5092868338ee5f75a`. During R5, external work advanced
  local main to `9405ba325f49f6b8db00901fe05120894f266d92` and origin/main to
  `4939e2881c884073f5b820f281d9e322558349f1`. Final `main...origin/main` was
  `5 21`; `main...HEAD` was `1 1`. `82971cc92383…` remained an ancestor of main.
  `git ls-remote origin refs/heads/main` confirmed `4939e2881c88…`. R5 did not
  fetch, adopt, or qualify those moving revisions.
- The unrelated active checkout stayed at
  `bd4f36346f816d82a9f86eeee2524edadd3465bb`, branch
  `codex/invocation-scoped-execution-binding`. Its existing untracked
  `Codexify.Space/` and four Scout Python files remained untouched.

## Runtime isolation and environment

Local macOS/arm64; Docker Desktop `desktop-linux`, server 29.8.2. Regression
execution used the existing `/Volumes/Dev_SSD/Codexify-main/.venv/bin/python`
(Python 3.12.13), without installing dependencies into that environment. The
fresh backend image used the repository Dockerfile's Python 3.11.14 runtime and
canonical backend requirements.

- Compose project: `codexify_natural_recall_r5_20261009`.
- Configuration: frozen checkout `docker-compose.yml`,
  `docker-compose.whooshd-smoke.yml`, and temporary R5 override only.
- Image built from this checkout: `codexify-r5:4eb460449096`, inspected and used
  by all task application/capture containers as
  `sha256:c83f7d70153b00b242be46b63b3a7083fe85d15ca27cdae4d7bb163eac4db147`.
  Build exited 0. Unpacking took 337.1 seconds; export took 438.2 seconds.
  Intermittent Docker API timeouts during build were not classified as an
  application failure; startup subsequently completed.
- Actual project network: `codexify_natural_recall_r5_20261009_default`,
  ID `72822e3449d0017acaa92ca130646f5e3cfe9a9a9254c0355b977d214f14dc7c`.
- New PostgreSQL volume: project-prefixed `pg_data`; database was migrated to
  `17b23052da6a`. Loopback port `127.0.0.1:57493`.
- Redis was a new container/network member, with its new anonymous `/data`
  volume `15c495268b842679c167685fd09a3a203aff91ba802b1b3b25e50ac538df40d3`.
  Persistence was disabled. Queues were confined to this Redis instance.
- New project-prefixed `r5_vectors`, `r5_imports`, and `r5_media` volumes.
  Backend/chat/chat-embedding services shared the task vector volume at
  `/app/.chroma`; account staging used `/app/data/imports`. Rendered settings
  selected Chroma collection `synthetic_recall_r5`.
- Application code came from the fresh image, with the same frozen `guardian`
  mounted read-only as `/app/codexify` and frozen `config` read-only. Existing
  BGE weights at `/Volumes/Dev_SSD/Codexify-main/models/bge-large-en-v1.5` were
  mounted read-only. No Preview/candidate data, queue, vector, media, session,
  credentials, or CLI-home volume was adopted.
- Rendered application settings used `LLM_PROVIDER=local`,
  `ALLOW_CLOUD_PROVIDERS=false`, `CODEXIFY_LOCAL_ONLY_MODE=true`, empty cloud
  credentials, embedding backend `local`, and fallback disabled. Embedding
  worker logs confirmed `backend=sentence_transformer` and
  `/models/bge-large-en-v1.5`; mock embeddings were used only by regression tests.
- Application ports exposed only `127.0.0.1:58893`. Dependencies were started
  explicitly with `--no-deps`; pre-existing weights replaced model provisioning
  and graph writes remained disabled. Frontend/document-worker/full-profile
  readiness was not qualified by this API-oriented subset.
- Limits: PostgreSQL 256 MiB, Redis/capture 64 MiB each, backend/chat/embed 1800
  MiB each, account-import 256 MiB. All started application workers were running
  with `OOMKilled=false`. Limited VM memory was observed, not used to manufacture
  a resource blocker.

The capture sidecar resolved `whooshd-upstream` to the Docker host gateway
`192.168.65.254` and forwarded requests/responses without changing their bodies.
Only this project's DNS alias for `host.docker.internal` pointed to it
(`172.21.0.5`); the supported `LOCAL_BASE_URL` remained
`http://host.docker.internal:8000/v1`. An upstream `/health` and a backend-issued
`/v1/models` probe returned 200. Host model discovery advertised `local-chat`,
Gemma 4 12B IT QAT 4-bit, `mlx_vlm`; advertisement is not generation proof.

## Synthetic fixture prepared, not imported live

Temporary root: `/private/tmp/codexify-natural-recall-r5/fixture`.

| Relative path | Bytes | Purpose |
| --- | ---: | --- |
| `Workspaces/Synthetic Helix/conversations__r5.part-0001/file_0000000000000001.dat` | 843 | Readable JSON shard; conversation `r5-helix-workspace`, source messages `m1`, `m2`, ordered parent chain; workspace provenance `external-r5-workspace` and intentionally untrusted export owner |
| `Unassigned/conversations__r5.part-0002/file_0000000000000001.dat` | 694 | Independent readable shard; conversation `r5-garden-unassigned`, distinct conversation/message pairs |
| `user.json` | 70 | Synthetic export account metadata, never intended as Guardian authority |

SHA-256 respectively:

```text
36fbde789d67c5dbdd72404d0345e3280d23f293248fac9db9649ef7cf8a3dff
9bc16a8959183929c7d947acad1312998b4b3859b4d407ae3e9f5753d2118bc5
06c5ac250c25a5917490fda06d0ef583d9aa2d0c11e20f5504311c27d3f908c1
```

Only imported synthetic assistant evidence would have supplied
`HELIX-624913`. Planned separate-chat question:
“What calibration code did I record for the Helix navigation beacon?”
The expected answer was absent from that prompt. Planned posture `workspace`
uses the existing same-user boundary in `retrieval_router_policy.py`; no policy
was changed. Neither the question nor a completion was submitted.

Accounts `synthetic-r5-a` and `synthetic-r5-b` were planned. Registration of A
failed before either account existed. Replay, attachment/orphan cases and
interrupted recovery were rerun in the existing regression owner, not claimed
as new live R5 evidence. An intentional B source-ID collision was deferred at
the authentication boundary; the globally keyed source-message unique index
remains an unqualified compatibility risk recorded in the preceding proof.

## Exact execution commands and receipts

Commands ran from the physical frozen checkout. `P` below expands to
`/private/tmp/codexify-natural-recall-r5`; `PY` expands to the existing venv
Python above. Random task-only secrets were generated into mode-0600 files;
their values and credential-bearing rendered configuration are excluded here.

```bash
docker build --target runtime -f backend/Dockerfile -t codexify-r5:4eb460449096 .

compose_r5() {
  docker compose --env-file "$P/runtime.env" \
    -p codexify_natural_recall_r5_20261009 \
    -f docker-compose.yml -f docker-compose.whooshd-smoke.yml \
    -f "$P/override.yml" "$@"
}
compose_r5 config --format json

compose_r5 up -d --no-deps db redis
DATABASE_URL=<task-only-postgres-DSN> CODEXIFY_CONFIG_SOURCE=core \
  CODEXIFY_DISABLE_DOTENV=1 CODEXIFY_EMBEDDINGS_BACKEND=mock \
  /Volumes/Dev_SSD/Codexify-main/.venv/bin/alembic \
  -c backend/alembic.ini upgrade head
compose_r5 up -d --no-deps --no-build provider-capture backend
curl --max-time 5 -sS http://127.0.0.1:58893/ping
compose_r5 up -d --no-deps --no-build \
  worker-chat worker-chat-embed worker-account-import
"$PY" "$P/api_import.py"
```

The generated API driver uses `requests`, performs ordinary registration/login,
then would call account-import create/multipart-files/commit/status. It exited 1
at its first registration, before executing any import operation. Expected
registration: 200 and canonical user ID. Observed:

```text
POST /api/auth/register -> 404 {"detail":"Not Found"}
POST /auth/register     -> 404 {"detail":"Not Found"}
POST /api/auth/login    -> 404 {"detail":"Not Found"}
POST /auth/login        -> 404 {"detail":"Not Found"}
```

Read-only contract reconciliation:

- `guardian/guardian_api.py` registers both auth routers under label `auth`.
- `config/supported_profiles/v1-local-core-web-mcp.yaml` does not enable that
  label; `SupportedProfileManifest.route_status()` defaults absent labels to
  `quarantined`.
- `supported_profile_contract_mismatches()` rejects remote auth with an
  unavailable auth route. Merely setting `GUARDIAN_AUTH_MODE=remote` would not
  preserve this profile's contract.
- `guardian.cli.private_preview_provision` requires private-preview exposure
  and an approved allowlist. `guardian.cli.tester_account_provision` requires
  remote auth, `local_safe`, and `v1-friends-family-web`. Neither was invoked.
- Session verification code exists, but this receipt does not establish an
  approved principal/session bootstrap outside those guarded procedures. It
  does not assert that every possible session fixture is technically impossible.

Stop readback in the task database:

```text
users=1                    # startup local account
synthetic_r5_users=0
r5_source_messages=0
openai_account_import_jobs=0
personal_facts=0
alembic_version=17b23052da6a
account-import queue=0; chat-import-embed queue=0; chat queue=0
```

Provider capture contained three GET requests (`/api/tags`, two `/v1/models`),
all 200, and **zero completion POSTs**. There is no import-job ID, recall-thread
ID, chat-task/attempt ID, executed provider-context receipt, or persisted
assistant-answer ID to attribute to R5.

Temporary evidence identifiers: `auth-boundary.json`, `api-receipts.json`,
`api-import.log`, `fixture-inventory.json`, `actual-mounts.txt`, `runtime.log`,
`readback-stop.txt`, `provider-wire.jsonl`, and `cleanup.log`, beneath `P`.
The committed excerpts above preserve the material result if temporary files
expire. The capture/script/config files are inspection aids, not a new committed
test harness or substitutes for successful executed-path evidence.

## Regression validation

Each command used the frozen checkout and environment
`CODEXIFY_CONFIG_SOURCE=core CODEXIFY_DISABLE_DOTENV=1
CODEXIFY_EMBEDDINGS_BACKEND=mock TEST_DATABASE_URL=<migrated-task-only-DSN>`.

| Exact command (with `$PY` expanded as above) | Final observed result |
| --- | --- |
| `$PY -m pytest -v tests/rag/test_openai_export_account_import.py` | 37 passed, 1 warning, 5.15 s |
| `$PY -m pytest -v tests/services/test_account_import_embedding_handoff.py` | 3 passed, 0.90 s |
| `$PY -m pytest -v tests/workers/test_account_import_worker.py` | 13 passed, 1.32 s |
| `$PY -m pytest -v tests/migration/test_openai_export_conversation_import.py` | 30 passed, 2 warnings, 55.89 s; all three PostgreSQL tests executed |

**83 passed; no final skips or failures.** This does not reuse the preceding
97-test total: the extra 14 adapter tests were not requested/rerun in R5.

Initial setup error retained: migration was started before PostgreSQL accepted
connections and failed with connection refused. The prematurely run integration
suite produced **29 passed, 1 failed, 1 warning in 26.02 s**; the failure was
`test_postgres_synthetic_modern_account_import_recovery_and_lineage`, reporting
missing expected database tables. After confirmed database readiness, migration
exited 0 and the entire integration suite passed as shown. No source repair or
concealed skip was used. Warnings concerned existing relationship/deprecation
behavior; no unrelated change was made.

## Gate matrix

| Gate | Classification | Exact evidence or missing prerequisite |
| --- | --- | --- |
| Frozen source includes prior qualification; clean workspace | PASS | HEAD, parent, clean status and empty prior-proof diff |
| Independent runtime storage/network/queues and service startup | PASS, bounded subset | Rendered configuration, actual mounts/image IDs, running workers, `/ping` 200, migrated task database |
| Real local embedding model loads | PASS, startup only | Backend/chat/embed logs show local SentenceTransformer/BGE; no imported message embedding receipt |
| Local inference provider discovery/transport | PASS, discovery only | Actual upstream health/models 200; generation unexecuted |
| Two supported authenticated principals | BLOCKED | Auth aliases 404; no supported setup/issuer procedure established within prescribed profile |
| Synthetic live API/worker import and lineage | BLOCKED | No authenticated account, job or live imported messages |
| Imported pending → ready embedding and backend/worker vector parity | BLOCKED | No live imported message/handoff; startup model loading is insufficient |
| Separate-chat searchability and broker selection | BLOCKED | No authorized live corpus or recall turn |
| Executed provider-context inclusion | BLOCKED | Zero completion POSTs; GET/model health and debug traces cannot substitute |
| Relevant answer, PostgreSQL persistence and API readback | BLOCKED | No completion or assistant row |
| B negative retrieval/provider-input control and source-ID collision | BLOCKED | No second authenticated principal; neither control attempted |
| Overall natural import-to-recall | BLOCKED | Required positive and negative executed-path gates remain unproven |

## Cleanup, ADRs, documentation and follow-up

Exact project cleanup used the same inspected Compose arguments with
`down --volumes`. This removed only the newly created R5 containers, network,
named volumes and anonymous Redis volume. Post-cleanup project-label container,
volume and network inventories were empty. The task image tag/digest was
removed with `docker image rm codexify-r5:4eb460449096`; no Docker-wide prune,
shared-volume reset, shared-service restart, or Whoosh'd configuration change
was performed. Task secret files and credential-bearing rendered configuration
were deleted; sanitized excerpts/scripts/fixtures remain temporary evidence.

Governing anchors were read: current-state, architecture README/index/flows,
Axis task protocol, Account Export + Restore Contract, import diagnostics and
runbook, R4, and preceding synthetic qualification. Accepted ADR-081 preserves
`projects.user_id` as project authority and independent thread ownership;
ADR-005 governs account/mode boundaries; ADR-004 governs retrieval policy;
ADR-013 separates verified facts from imported history; ADR-069 preserves
support posture separately from evidence maturity. ADR-041/042 prevent local
proof from being promoted into unverified canonical-machine/release evidence.

**ADR impact: aligned, proof-only; no new ADR or contract changes.** PostgreSQL
stayed canonical; import metadata never selected an account; no private archive,
permanent personal fact, manual vector seed, cloud substitution, or release
claim was introduced. Message ownership, lineage, replay and recovery remain
covered by the passing regression assertions, not by new live R5 receipts.

Documentation changed only this artifact. Auth-profile compatibility is
documented here; no runbook, profile, `00-current-state.md`, test or application
source was changed. `git diff --check` and staged diff/path checks are the
documentation closeout validations; automated document-only runtime tests do
not apply beyond the explicitly requested regression runs above.

Smallest prerequisite for a fresh successor: establish and explicitly authorize
a reproducible canonical principal-provisioning/session-issuance procedure for
this exact local profile, or amend the task's profile boundary through the
governing process. Do not silently invoke a guarded Preview/tester provisioner
under false posture or promote fabricated sessions into supported-auth proof.
Then rerun one uninterrupted fresh synthetic API import → actual embedding
worker → vector parity → separate governed chat → captured actual local
provider input → persisted/readable answer → authenticated B negative control
and intentional source-ID collision. Any ownership defect or required code
correction requires its own authorized follow-up. A real archive remains
deferred: use a complete, unmodified export folder through the documented
account-import procedure only after the required qualification/authority gates.
