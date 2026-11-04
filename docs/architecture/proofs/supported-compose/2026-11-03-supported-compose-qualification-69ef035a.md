# Supported-Compose runtime — qualification at `69ef035a` — 2026-11-03

> **Release posture: HOLD.** This proof qualifies one frozen revision of the
> supported local Docker Compose runtime. It does not lift the release gate,
> does not widen Beta or production support, and does not authorize deployment.

## Result

**Rubric verdict: PASS** for the supported Compose runtime on the frozen
evaluated revision `69ef035a4320724b9a53279d2fabd6bac0c6e98f`, with two
recorded limitations, one explicit scope boundary, one finding outside the
rubric's criteria, and the excluded surfaces named below.

The supported local Compose topology started on the repaired canonical
startup path, applied the source tree's own Alembic head, and satisfied every
required rubric boundary — including the boundary that the September 2026 run
failed: **an explicitly requested unavailable local model was rejected before
provider execution, with no substitute model executed and no assistant message
persisted.**

| Rubric check | Result |
| --- | --- |
| 1. Supported topology and startup | **PASS** |
| 2. Health and inventory | **PASS** |
| 3. Ordinary chat and durable readback | **PASS** |
| 4. Document ingestion and retrieval | **PASS** |
| 5. Explicit model authority | **PASS** |
| 6. Browser projection | **PASS** |
| 7. Restart recovery | **PASS** |

### Recorded limitations

1. **The `rag-trace` operator surface does not surface the document
   attribution that the durable trace record holds.** The per-message
   retrieval provenance exists and is correct; the HTTP operator surface
   returns empty `documents`/`graph` arrays and `retrieval_provenance: null`.
   See [§9](#9-document-retrieval-and-provenance).
2. **`worker-coding` runs a non-source-matched image.** It starts from the
   pre-baked `codexify-worker-coding-runtime:latest`, not from the
   source-matched backend image. It is outside this rubric and outside the
   supported profile. See [§5](#5-supported-topology-and-startup).

### Scope of this PASS

**This PASS applies to the launcher-driven, source-matched startup that this
run exercised** — `scripts/whooshd_docker_smoke_up.sh full --detach --project
codexify_qual_20261103`, which renders `docker-compose.yml` +
`docker-compose.whooshd-smoke.yml` with the supported profile's provider
contract and builds the backend image from the evaluated checkout
(`codexify-backend-runtime:src-69ef035a4320`).

**It does not qualify the stock `:latest` Compose startup at the same
revision.** The plain `docker compose up` path against the pre-baked
`codexify-backend-runtime:latest` image remains unqualified, and the reason
is structural rather than incidental. `backend/migrations` is a symlink to
`../guardian/db/migrations`, and `docker-compose.yml`'s migrator bind-mounts
only `./backend:/app/backend`, so the symlink resolves into the baked image
instead of into the checkout. PR #982 hardened the qualification launcher; it
did not change the stock Compose configuration. The mechanism is set out in
[§5.1](#51-the-launcher-path-versus-the-stock-compose-path).

This boundary is stated up front because the registry projects this receipt's
verdict against a surface whose scope — "the supported local Docker Compose
runtime" — is broader than the single startup path exercised here. Every
rubric criterion was met against the exercised path, so the verdict stands as
PASS; but this receipt must not be read as saying the stock supported install
path is qualified. `docs/architecture/00-current-state.md` remains release
authority and records the stock-path migrator defect as an open blocker.

### Finding outside the rubric's criteria

**The retained `pending` `events_outbox` rows are the implemented behaviour,
not a delivery failure.** No rubric check depends on outbox publication state,
and the live SSE surface served the same events correctly. The open question is
whether the outbox's `status` column has meaningful publication semantics and
whether retention is bounded — not whether the table "drains". See
[§12](#12-event-stream-and-outbox).

### Excluded surfaces

The Private Preview lane, cloud providers, federation, connectors, hosted
sandbox, Atlas, Pi, and the autonomous coding worker are **not** qualified by
this run and remain under their own authority, exactly as the rubric states.

## 1. Frozen revision and execution window

| Field | Value |
| --- | --- |
| Evaluated commit | `69ef035a4320724b9a53279d2fabd6bac0c6e98f` |
| Commit subject | `fix(knowledge-graph): rebind the adr-index node to the revision main holds (#987)` |
| Worktree | `/Volumes/Dev_SSD/Codexify-main/.worktrees/qual-compose-02` (detached HEAD at the frozen SHA) |
| Upstream state | `origin/main` at `69ef035a4`; the worktree was created from `origin/main` at that SHA and never advanced |
| Compose project | `codexify_qual_20261103` |
| Stack creation | 2026-11-03 19:08:46–19:08:47 EST (2026-11-04T00:08:46Z) |
| Application restart | 2026-11-03 ~19:26 EST (`backend`, `worker-chat`, `worker-document-embed` only) |
| Evidence window | 2026-11-03 16:45 – 19:32 EST (2026-11-04T00:32Z) |
| Profile | `v1-local-core-web-mcp` (version 1, surface `local-docker-compose-webui`) |
| Provider / model | `local` / `local-chat` (Gemma 4 12B IT QAT 4-bit) |
| Browser | Google Chrome `156.0.8078.80` (macOS, real browser via the Chrome DevTools Protocol) |
| Host | macOS 27.2 arm64, Docker Desktop 29.9.2, Docker Compose v5.6.1 |

The revision did not move during the run. The working tree was clean at every
check (`git status --porcelain` returned zero entries throughout).

## 2. Capacity preflight

Gate 0 was satisfied before the build, and the measured values are recorded
here because the capacity result of QUAL-CAPACITY-01 was explicitly
time-sensitive.

| Measurement | Value |
| --- | --- |
| Free space at the first Gate 0 check | 7.4 GiB (100% capacity) |
| Free space at the build-start re-check | **26.93 GB** — above the 26.3 GB requirement |
| `Docker.raw` backing file | `/Volumes/Dev_SSD/offload/docker/Docker.raw` (symlinked from Docker Desktop); 128 GiB logical, 55 GiB allocated at the start of the run |
| Build cache at build start | 0 B across 0 records |
| Free space after the image export | 12.9 GB (the 4.65 GB image plus 7.37 GB of build cache landed in `Docker.raw`, which grew 55 GiB → 70 GiB) |
| Free space at the end of the run | 11.2 GB |
| Builder identity | one usable named builder, `desktop-linux` (driver `docker`, BuildKit v0.34.0) |

**The 26.3 GB precondition was met at build start.** The image build was
executed only after that check passed. The capacity consumed afterwards is the
build's own expected cost, inside the 10 GB safety reserve that
QUAL-CAPACITY-01 already folded into the estimate.

### Two build interruptions, both host-resource, both recovered

1. **First build attempt — BuildKit session EOF.** The build died during the
   runtime stage's `apt-get install nodejs npm` step with
   `failed to receive status: rpc error: code = Unavailable desc = error
   reading from server: EOF`. The Docker VM is capped at **7.749 GiB RAM and
   4 CPUs**, and a concurrent executor's containers were being created inside
   that window (`agentdaw-pg-proof` and `agentdaw-proof` at 16:00:54; six
   `codexify_account_observability_norm_*` containers between 15:35 and
   15:37). Docker's containerd restarted at 21:13:45Z, immediately after the
   failure. No source image was produced and **no qualification-owned
   container, volume, or network was left behind** (0/0/0 verified).

2. **Second attempt — `model-prep` exit 1.** The stock `full` topology aborted
   because `model-prep` could not prepare the embedding model: the harness
   correctly detected the model as absent and then failed with
   `[Errno 17] File exists: '/models/bge-large-en-v1.5'`. This was a defect in
   the **qualification environment provisioning**, not in the product: the
   harness provisions the embed model by bind-mounting `./models`, and the
   first provisioning used a **symlink** for `./models/bge-large-en-v1.5`.
   Docker does not resolve a symlinked bind-mount source, so the container
   received a dangling symlink, `Path.exists()` was false, and the download
   path was taken against a read-only mount. The provisioning was corrected
   by materialising the model directory as a real tree (APFS copy-on-write
   clone, `cp -Rc`, which consumed no additional physical space), and the
   third attempt started the full topology cleanly.

   This is recorded because it is a reproducible trap for any future
   qualification of this path: **the `./models` bind source must be a real
   directory tree, not a symlink.**

The third launch was the evaluated run. Its build was fully cached from the
BuildKit cache.

## 3. Isolation verification

### Worktree

| Check | Result |
| --- | --- |
| Frozen worktree at the evaluated SHA | PASS — detached HEAD, `git status --porcelain` empty at every check |
| Untracked files entering the build context | PASS — none. The build context transferred was **140.43 MB**, which proves the 3.7 GB `models/` tree never entered it (`.dockerignore` excludes `/models`, `/.chroma`, `/data`, `/docker`, `/frontend`, `/tests`, `/docs`, `.env*`, `.scratch*`, `.git`, `.venv`) |
| Git-ignored runtime assets | `.venv` (excluded via `.git/info/exclude`), `models/`, `.chroma/`, `data/media`, `data/imports` |
| Runtime assets provisioned | `models/bge-large-en-v1.5` (APFS clone, read-only mount), empty `.chroma/`, empty `data/media`, empty `data/imports` |

### Compose project

| Check | Result |
| --- | --- |
| Project unused before the run | PASS — 0 containers, 0 volumes, 0 networks for `codexify_qual_20261103` |
| Named volumes project-scoped | PASS — every volume carried `com.docker.compose.project=codexify_qual_20261103`; none was shared with the Private Preview |
| Network project-scoped | PASS — `codexify_qual_20261103_default` only |
| Write isolation from the primary checkout | PASS — `./models` is a real directory inside the worktree, so the read-write `./models:/models` mount could not write into the primary checkout's model tree |
| Host ports | `5433` (db), `5173` (frontend), `7474`/`7687` (neo4j) were free. `8888` was already bound by `codexify-devproxy`, so the operator parameter `CODEXIFY_BACKEND_PORT=8890` was used. The Private Preview publishes **no** host ports, so no Preview port was touched. |
| External services | exactly one: the host Whoosh'd at `127.0.0.1:8000`, reached by the containers as `http://host.docker.internal:8000/v1`. The launcher's Step 5 detected it healthy and **left it untouched** ("Whoosh'd is already running; it is left untouched"). It was never restarted or replaced. |
| Provider model inventory | observed at the runtime, not assumed: `GET http://127.0.0.1:8000/v1/models` advertised exactly one model, `local-chat`, `Gemma 4 12B IT QAT 4-bit`, engine `mlx_vlm`, context window 32768 |

### Environment contract

The qualification ran with the supported profile's own provider contract. The
operator's `.env` targets a **different lane** (`CODEXIFY_SUPPORTED_PROFILE=
v1-friends-family-web`, `LLM_PROVIDER=deepseek`, `ALLOW_CLOUD_PROVIDERS=true`,
`CODEXIFY_EGRESS_ALLOWLIST=deepseek`), and the Whoosh'd smoke overlay only
corrects that on the five runtime services. The qualification environment file
was therefore built from the operator's `.env` with every cloud credential
blanked and the `v1-local-core-web-mcp` `provider_contract` applied verbatim.

The environment file lives **outside the repository**
(`.scratch/qual-compose-02/qual.env`) and is referenced by path through
`CODEXIFY_RUNTIME_ENV_FILE` and `COMPOSE_ENV_FILES`, so no untracked file was
placed in the frozen worktree. Blanked credential keys: `OPENAI_API_KEY`,
`GROQ_API_KEY`, `MINIMAX_API_KEY`, `DEEPSEEK_API_KEY`, `ANTHROPIC_API_KEY`,
`GENAI_API_KEY`, `E2B_API_KEY`, `GOOGLE_DRIVE_OAUTH_CLIENT_ID`,
`GOOGLE_DRIVE_OAUTH_CLIENT_SECRET`, `GOOGLE_OAUTH_CLIENT_ID`,
`GOOGLE_OAUTH_CLIENT_SECRET`, `GOOGLE_RELAY_BROKER_URL`,
`GOOGLE_RELAY_AUDIENCE`, `NOTION_API_KEY`, `DISCORD_BOT_TOKEN`, `GITHUB_TOKEN`,
`GUARDIAN_OAUTH_TOKEN_ENCRYPTION_KEY`.

Retained (local by construction): `GUARDIAN_API_KEY`, `GUARDIAN_SESSION_SECRET`,
`POSTGRES_PASSWORD`, `PGPASSWORD`, `NEO4J_PASS`, and the blessed
`LOCAL_API_KEY=local`.

## 4. Compose configuration

```
docker compose -p codexify_qual_20261103 \
  -f docker-compose.yml \
  -f docker-compose.whooshd-smoke.yml \
  config --quiet
```

exit `0`.

Rendered Compose files, in order:

1. `docker-compose.yml`
2. `docker-compose.whooshd-smoke.yml`

Rendered service set (17 services): `backend`, `db`, `e2e`, `frontend`,
`graph-init`, `migrator`, `model-prep`, `neo4j`, `redis`,
`worker-account-import`, `worker-chat`, `worker-chat-embed`, `worker-coding`,
`worker-document-embed`, `worker-voice`, `worker-warmup`.

The launcher's Step 7 asserted the blessed Whoosh'd contract against the
resolved configuration. **All 16 assertions passed:**

```
[PASS] LOCAL_BASE_URL=http://host.docker.internal:8000/v1
[PASS] ALLOW_CLOUD_PROVIDERS=false
[PASS] CODEXIFY_EGRESS_ALLOWLIST empty
[PASS] CODEXIFY_LOCAL_ONLY_MODE=true
[PASS] LLM_PROVIDER=local
[PASS] LOCAL_PROVIDER_VENDOR=whooshd
[PASS] LOCAL_RUNTIME_PRESET=whooshd-mlx
[PASS] LOCAL_COMPAT_FIRST=true
[PASS] LOCAL_PROVIDER_DISPLAY_NAME=Whoosh'd
[PASS] WHOOSHD_HEALTH_BASE_URL=http://host.docker.internal:8000
[PASS] CODEXIFY_SUPPORTED_PROFILE=v1-local-core-web-mcp
[PASS] LOCAL_CHAT_MODEL=local-chat
[PASS] migrator uses codexify-backend-runtime:src-69ef035a4320
[PASS] backend uses codexify-backend-runtime:src-69ef035a4320
[PASS] worker-chat uses codexify-backend-runtime:src-69ef035a4320
```

## 5. Supported topology and startup

### Image identity

| Field | Value |
| --- | --- |
| Image reference | `codexify-backend-runtime:src-69ef035a4320` |
| Image ID / manifest digest | `sha256:0ecc261727e61eeaad44c48d0c434479a92a8fdb378af82c6f4cb22c9dde1f65` |
| Repo digest | `codexify-backend-runtime@sha256:0ecc261727e61eeaad44c48d0c434479a92a8fdb378af82c6f4cb22c9dde1f65` |
| Size | 4,654,664,374 bytes (4.65 GB) |
| Provenance | `built-from-this-checkout` — the launcher reported this provenance label, and the build was executed against the frozen worktree with an empty tracked tree |
| Build context | 140.43 MB |

### Service state at the evaluated run

| Service | State | Image |
| --- | --- | --- |
| `db` | running (healthy) | `postgres:15` |
| `redis` | running (healthy) | `redis:7-alpine` |
| `neo4j` | running (healthy) | `neo4j:5` |
| `backend` | running (healthy) | `codexify-backend-runtime:src-69ef035a4320` |
| `frontend` | running | `node:20-alpine` |
| `worker-chat` | running | `codexify-backend-runtime:src-69ef035a4320` |
| `worker-document-embed` | running | `codexify-backend-runtime:src-69ef035a4320` |
| `worker-chat-embed` | running | `codexify-backend-runtime:src-69ef035a4320` |
| `worker-warmup` | running | `codexify-backend-runtime:src-69ef035a4320` |
| `worker-voice` | running | `codexify-backend-runtime:src-69ef035a4320` |
| `worker-account-import` | running | `codexify-backend-runtime:src-69ef035a4320` |
| `worker-coding` | running (healthy) | `codexify-worker-coding-runtime:latest` ← **not source-matched** |
| `migrator` | exited 0 | `codexify-backend-runtime:src-69ef035a4320` |
| `model-prep` | exited 0 | `codexify-backend-runtime:src-69ef035a4320` |
| `graph-init` | exited 0 | `neo4j:5` |
| `e2e` | exited 0 | `mcr.microsoft.com/playwright:v1.56.1-jammy` |

Every required service for the profile — `frontend`, `backend`, `db`, `redis`,
`worker-chat`, `worker-document-embed`, `migrator` — was present, and the
required ones were healthy.

**Limitation — `worker-coding` runs a non-source-matched image.** It is
started from the pre-baked `codexify-worker-coding-runtime:latest` because the
supported profile does not own that image. It is outside this rubric and
outside the supported profile (the rubric explicitly does not qualify "the
autonomous coding worker"), and it was therefore **not** qualified by this
run. It is recorded so that no reader mistakes the running container for
evidence about the source-matched path.

### 5.1 The launcher path versus the stock Compose path

The rubric anchors its scope to the runtime that
`docs/architecture/00-current-state.md` names as the supported install path.
That document names the local Docker Compose profile `v1-local-core-web-mcp`
with its provider contract — it does not name a startup command — and it
records, at this tip, that the **stock** supported path still fails Gate B.
This subsection records exactly how the path exercised by this run differs from
the stock path, so that this receipt cannot be read as qualifying the stock
path.

| | Launcher path (exercised) | Stock Compose path (not exercised) |
| --- | --- | --- |
| Startup | `scripts/whooshd_docker_smoke_up.sh full --detach --project codexify_qual_20261103` | `docker compose up` over `docker-compose.yml` (+ `docker-compose.whooshd-smoke.yml`) |
| Backend image | `codexify-backend-runtime:src-69ef035a4320`, built from the evaluated checkout | `${CODEXIFY_BACKEND_IMAGE:-codexify-backend-runtime:latest}` — the pre-baked image |
| Migration source | the image's `/app/guardian`, which **is** the evaluated checkout's `guardian/db/migrations` | the bind-mounted `./backend`, whose `migrations` symlink resolves into the baked image's `/app/guardian` |
| Migrator volumes | stock declaration, unchanged: `- ./backend:/app/backend` | stock declaration, unchanged: `- ./backend:/app/backend` |
| Gate B at `69ef035a4` | **PASS** — `alembic_version` = `d91e4fa6702b` by direct readback | **not exercised**; structurally the migrator applies the baked image's head, not the source head |
| `docker-compose.runtime.yml` migrator | not used by this path | declares **no volumes at all** |

The two paths use the **same Compose configuration**. They differ only in
which image that configuration resolves. The mechanism was verified from the
frozen tree, not inferred:

- `backend/migrations` is a symlink in the evaluated revision. Git records it
  with mode `120000` and blob `0fb5f8a0ce92f02bce914dcd96c5f2be43e63a31`,
  whose content is `../guardian/db/migrations`.
- `docker-compose.yml` declares the backend image as
  `${CODEXIFY_BACKEND_IMAGE:-codexify-backend-runtime:latest}`, and its
  `migrator` service declares exactly one volume, `- ./backend:/app/backend`,
  carrying the source's own comment: *"NOTE: no guardian volume mounts —
  virtiofs stat bug on macOS Docker Desktop causes os.path.exists() to fail
  for files with com.apple.provenance xattr. Migration files come from the
  baked image (COPY guardian /app/guardian)."* The bind mount replaces
  `/app/backend` with the checkout's `backend/`, so the `migrations` symlink
  resolves to `/app/guardian/db/migrations` — the **image's** guardian, not
  the checkout's.
- `docker-compose.runtime.yml`'s `migrator` declares no `volumes` key at all.
- The launcher instead sets `IMAGE_TAG="codexify-backend-runtime:src-${SOURCE_SHA:0:12}"`,
  builds it with `docker build --target runtime -f backend/Dockerfile -t
  "$IMAGE_TAG" "$REPO_ROOT"`, compares the built image's migration head with
  the source head, and exports `CODEXIFY_BACKEND_IMAGE`.

Because the launcher's image is built from the evaluated checkout, the baked
`/app/guardian` *is* the frozen source, and the migrator reaches the source
head. That is the whole reason Gate B passes here, and it is a property of
the image the launcher builds — not of the Compose file, which PR #982 did not
touch.

**Consequence for this receipt.** Gate B is proven for the launcher path at
this revision. It is **not** proven for the stock path, and no claim in this
proof extends to it. The stock-path migrator defect remains open in the tree
at this revision and is recorded as an active blocker in
`docs/architecture/00-current-state.md`.

### Provider contract at the container level

Every one of the 16 qualification containers was inspected by reading
`Config.Env` directly.

| Result | Value |
| --- | --- |
| Containers inspected | 16 |
| Containers whose full 11-key provider contract matched exactly | 11 |
| Containers with a **wrong** contract value | **0** |
| Containers with a cloud credential value | **0** |

The five containers that do not carry the full contract (`e2e`, `model-prep`,
`neo4j`, `redis`, `worker-coding`) have the contract keys **absent**, not
wrong: they are the Playwright runner, the model-preparation job, and two
infrastructure services that have no LLM role, plus the out-of-scope coding
worker.

`backend` contract, read from the running container:

```
LLM_PROVIDER                  = 'local'
ALLOW_CLOUD_PROVIDERS         = 'false'
CODEXIFY_LOCAL_ONLY_MODE      = 'true'
CODEXIFY_EGRESS_ALLOWLIST     = ''
LOCAL_RUNTIME_PRESET          = 'whooshd-mlx'
LOCAL_BASE_URL                = 'http://host.docker.internal:8000/v1'
LOCAL_API_KEY                 = 'local'
LOCAL_COMPAT_FIRST            = 'true'
LOCAL_PROVIDER_DISPLAY_NAME   = "Whoosh'd"
LOCAL_PROVIDER_VENDOR         = 'whooshd'
CODEXIFY_SUPPORTED_PROFILE    = 'v1-local-core-web-mcp'
```

Credential-shaped values present in the qualification containers, and their
classification:

| Value | Length | Classification |
| --- | --- | --- |
| `GUARDIAN_API_KEY` / `VITE_GUARDIAN_API_KEY` | 64 | this installation's own Guardian key |
| `GUARDIAN_SESSION_SECRET` | 64 | this installation's own session secret |
| `PGPASSWORD` / `POSTGRES_PASSWORD` | 8 | the local database password |
| `NEO4J_PASS` | 18 | the local graph database password |
| `LOCAL_API_KEY` | 5 | the blessed literal `local` placeholder |
| `OPENAI_API_KEY` in `db`/`graph-init` | 5 | the Compose file's own literal default `local`, not a secret |

No cloud-provider credential value was present in any qualification
application or worker container.

## 6. Migration and database readback

### Source and image parity

| Measurement | Value |
| --- | --- |
| Source Alembic head (from the frozen worktree) | `d91e4fa6702b` — a **single** revision |
| Image Alembic head (launcher Step 4) | `d91e4fa6702b` |
| Parity | **agree** |

### Migrator terminal result

| Measurement | Value |
| --- | --- |
| Migrator container | project `codexify_qual_20261103`, service `migrator` |
| Container ID | `52465069e31c60c4d6c888570f3950c247299972c171daeebf42864a285fff7e` |
| Exit code | **0** |
| Image | `codexify-backend-runtime:src-69ef035a4320` |

### Direct database readback

Read directly from the qualification project's own PostgreSQL 15 container —
not from logs, not from the launcher's exit code:

```sql
SELECT version_num FROM alembic_version;
-- d91e4fa6702b

SELECT count(*) FROM alembic_version;
-- 1

SELECT count(*) FROM information_schema.tables WHERE table_schema='public';
-- 139
```

**Exactly one** row, equal to the source head. The database agrees with the
source tree and with the baked image.

This is the boundary QUAL-COMPOSE-01 failed. The defect it found — the baked
image applying an outdated Alembic revision because `backend/migrations` is a
symlink into `guardian/db/migrations` and the image bind-mounted only
`./backend` — is repaired by the merged launcher work (PR #982,
`00c3a4163`), and the repair is demonstrated here on the frozen revision.

## 7. Health and inventory

| Surface | HTTP | Result |
| --- | --- | --- |
| `/health` | 200 | `status: ok`; `supported_profile` `v1-local-core-web-mcp` version 1, `valid: true`, `mismatches: []` |
| `/health/chat` | 200 | `ok: true`, `status: healthy`, redis `ok`, worker heartbeat `fresh`, queue `progressing`, backend `postgres`, provider `local`, model `local-chat` |
| `/api/health/llm` | 200 | provider `local`, model `local-chat`, `provider_runtime.authorized: true`, `available: true`, `models: [local-chat]` |
| `/health/llm` | 200 | same content |
| `GET http://127.0.0.1:8000/v1/models` | 200 | exactly one advertised model: `local-chat` |

The model inventory was observed at the runtime. It was not assumed from
configuration.

## 8. Ordinary chat and durable state

Thread `1`, created through the ordinary route `POST /api/chat/threads`.

| Field | Value |
| --- | --- |
| `request_id` | `req_59e0a7779a214ada8cbe240eb151f3d6` |
| `acceptance_status` | `accepted`, `acceptance_warnings: []` |
| `task_id` | `2e3dc65e-a15e-47b9-baaf-2091bec65178` |
| `turn_id` | `8bfa05cf-4f77-4281-a0d9-27d238a91636` |
| Terminal outcome | `state: terminal`, `event_type: task.completed`, `reason: durable_completion_recorded`, `completed_message_id: 2` |
| Deadline snapshot | `accepted_at` 2026-11-04T00:12:52.404Z, `work_deadline_at` 00:24:52.404Z, `terminal_deadline_at` 00:25:52.404Z |
| Transcript | `['user', 'assistant']`; user prompt "Reply with exactly: qual-compose-02", assistant reply "qual-compose-02" |
| Account ownership | `chat_messages.user_id = 'local'` for every row — the local single-account mode the supported profile declares |

### Durable completion-attempt binding

Read directly from `chat_completion_attempts`:

| `request_id` | `backend_task_id` | `thread_id` | `turn_id` | `completed_message_id` | `terminal_event_type` |
| --- | --- | --- | --- | --- | --- |
| `req_59e0a7779a214ada8cbe240eb151f3d6` | `2e3dc65e-a15e-47b9-baaf-2091bec65178` | 1 | `8bfa05cf-4f77-4281-a0d9-27d238a91636` | 2 | — |
| `req_7fcdfbf805b14c3db111551b5e0a003a` | `abf38f03-32c0-4a70-b0c2-a3f259cf1200` | 2 | `ef94a650-c3f2-4693-bcee-74657ee94cbd` | *(null)* | `task.failed` |
| `req_f9e9e34281e648b4bb2bb25dc09ec256` | `1c64d958-f0c4-4946-a1d4-6298efd9eea4` | 3 | `5bc050f7-c44a-46ee-9431-f3873bdb7b09` | 5 | — |
| `req_694cae7b4b974d2d88c726d43c03333e` | `c70ec62a-dcc9-41d5-a489-3586235ce3c5` | 4 | `69d44364-2452-4535-afe7-eb29e2bca244` | 7 | — |
| `req_6d9e760162494c908dc36d3b4f21886a` | `9c57c44f-e15d-4212-945d-058490e3ec96` | 4 | `cdef197f-0454-47a9-ba42-496c8b7e0a92` | 8 | — |

Every attempt binds one `request_id` to one `backend_task_id`, one `turn_id`,
and one `completed_message_id`. No attempt shares a `turn_id` with another, and
no attempt shares a `completed_message_id` with another (both checked with
group-by counts: `0` duplicates each).

### Provider corroboration

The provider's own request ledger (`GET http://127.0.0.1:8000/runtime/requests`)
contains the matching entry, correlated by the application's `request_id`:

```
whoosh-a9413439a4c646acbbb2e59e291fa90e
  upstream_request_id = req_59e0a7779a214ada8cbe240eb151f3d6
  model = local-chat
  status = completed
  error_code = null
```

The worker log shows the matching `chat.inference.request.built` event.

## 9. Document retrieval and provenance

Thread `3`, synthetic document `qual-document.txt` (988 bytes), containing a
unique passphrase and four marker sentences.

| Step | Observation |
| --- | --- |
| Upload | `POST /api/media/upload/document` → HTTP 200, `document_id 6e7675ed-98d2-4c9a-b269-c1ec6eb40998`, `project_id 1`, `thread_id 3`, `source_tag: uploaded` |
| Embedding | `embedding_status: ready`, `embedding_error: null`, `embedding_started_at` 00:17:38.744Z → `embedding_completed_at` 00:18:13.701Z (35 s) |
| Retrieval | The completion's assistant reply was **"The passphrase is: ORANGE-TIDE-4471"** — the exact passphrase from the uploaded document, which the model could not have known without retrieving it |
| Task | `task_id 1c64d958-f0c4-4946-a1d4-6298efd9eea4`, terminal `task.completed` |
| Provider | ledger `whoosh-0c1ba24ee18e4a2b959b4fa160edf3a1`, `upstream_request_id req_f9e9e34281e648b4bb2bb25dc09ec256`, `model local-chat`, `status completed` |
| Model selection | `requested_model = attempted_model = resolved_model = final_model = local-chat`, `fallback_reason: null`, `selection_source: default` — no substitution, no fallback |

### Scope isolation

A second thread (`4`) was created and queried
`GET /api/media/documents?thread_id=4` → `document_ids: []`. The uploaded
document was **not** visible to the other thread. The recorded retrieval
posture boundary was `same_user_same_project`, `widen_reason: none`.

### Document and chunk attribution

The durable trace record (`chat_threads.metadata.debug_latest_rag_trace.trace`)
contains:

```json
"retrieval_executed": true,
"retrieval_absence_reason": null,
"retrieval_status": "no_obsidian_results",
"source_hit_counts": {
  "thread_documents": 1, "project_documents": 1,
  "thread_semantic": 0, "project_semantic": 0, "other_semantic": 0,
  "global_documents": 0, "other_documents": 0, "memory": 0,
  "graph": 0, "obsidian_semantic": 0
},
"contributing_items": [
  {"role": "document", "filename": "qual-document.txt", "thread_id": 3,
   "project_id": 1, "chunk_index": 0,
   "document_id": "6e7675ed-98d2-4c9a-b269-c1ec6eb40998",
   "source_type": "uploaded", "retrieval_lane": "thread_docs"},
  {"role": "document", "filename": "qual-document.txt", "thread_id": 3,
   "project_id": 1, "chunk_index": 0,
   "document_id": "6e7675ed-98d2-4c9a-b269-c1ec6eb40998",
   "source_type": "uploaded", "retrieval_lane": "project_docs"}
]
```

The document and the chunk are identified, and the retrieval lanes that
contributed are named. `retrieval_status: no_obsidian_results` accurately
reports that the Obsidian lane was empty; no Obsidian vault is part of the
supported profile.

### Limitation — the `rag-trace` operator surface does not surface the attribution

Read side by side:

| Surface | Observed |
| --- | --- |
| `GET /api/chat/debug/rag-trace/3/latest` | HTTP 200, `trace_available: true`, `documents: []`, `graph: []`, `retrieval_provenance: null` |
| `GET /api/chat/debug/retrieval-posture/3/latest` | HTTP 200, `status: "ok"`, posture populated with `boundary_label: same_user_same_project` |
| Durable trace record in PostgreSQL | `retrieval_executed: true`, `contributing_items` naming the document and chunk |

The per-message retrieval provenance **is** present and correct — in the
durable record. The `rag-trace` HTTP surface returns the trace but does not
expose the document attribution that the same trace holds. Per the rubric and
this task's instruction, this is recorded as a **limitation**: the
operator-facing `rag-trace` surface is not proven to work, and it is explicitly
**not** classified as proof that the operator surfaces work.

A first read of both surfaces returned empty. That was a **timing artifact**,
not a defect: the trace is written asynchronously after the completion, and
both surfaces reported populated content on re-read after the trace landed.
The limitation above is only the residual difference between the API response
and the durable record.

## 10. Explicit model authority

This is the boundary the September 2026 run failed. It was exercised on
thread `2`.

| Requirement | Observation |
| --- | --- |
| An ordinary request first proved the advertised route is selectable | thread `1` executed `local-chat` successfully — §8 |
| The unavailable-model request was accepted and then failed | `POST /api/chat/2/complete {"model": "qual-nonexistent-model-69ef035a"}` → HTTP 200, `acceptance_status: accepted`, `request_id req_7fcdfbf805b14c3db111551b5e0a003a`, `task_id abf38f03-32c0-4a70-b0c2-a3f259cf1200`, `turn_id ef94a650-c3f2-4693-bcee-74657ee94cbd` |
| It failed durably | `state: terminal`, `event_type: task.failed`, `reason: durable_terminal_outcome_recorded`, `completed_message_id: null` |
| The exact requested model identity was preserved | the durable failure payload records `model: "qual-nonexistent-model-69ef035a"`, `requested_model: "qual-nonexistent-model-69ef035a"`, `configured_source: "requested_model"`, `selection_source: "explicit"`, `requested_provider: "local"` |
| No substitute model executed | `advertised_models: ["local-chat"]` — the runtime knew what was advertised and refused the other name. No `local-chat` execution was performed for this request |
| No fallback was attempted | `fallback_reason: null`; the failure kind is `local_model_unavailable` |
| No successful assistant completion was persisted | `GET /api/chat/2/messages` → roles `['user']` only; `chat_messages` contains exactly one row for thread 2, role `user` |
| The durable attempt records the terminal failure kind | `chat_completion_attempts` row for `req_7fcdfbf805b14c3db111551b5e0a003a`: `terminal_event_type = task.failed`, `completed_message_id = null` |

The full failure payload, read from the durable `events_outbox` rows for
`task.failed` and `completion.error`:

```json
{
  "error": "local_model_resolution_error",
  "provider": "local",
  "failure_kind": "local_model_unavailable",
  "message": "Requested model 'qual-nonexistent-model-69ef035a' is not advertised by the local runtime",
  "model": "qual-nonexistent-model-69ef035a",
  "configured_source": "requested_model",
  "requested_model": "qual-nonexistent-model-69ef035a",
  "advertised_models": ["local-chat"],
  "inventory_source": "whooshd:/v1/models",
  "requested_provider": "local",
  "selection_source": "explicit",
  "endpoint_resolution": {
    "state": "available",
    "selected_endpoint": {"base_url": "http://host.docker.internal:8000/v1"},
    "inventory_url": "http://host.docker.internal:8000/v1/models",
    "inventory_source": "whooshd:/v1/models",
    "inventory_models": [{"id": "local-chat",
      "metadata": {"display_name": "Gemma 4 12B IT QAT 4-bit"}}]
  }
}
```

### Provider-side non-execution

The provider's own request ledger was queried directly:

| Ledger check | Result |
| --- | --- |
| Total entries in the ledger | 40 |
| Entries with `request_id = req_7fcdfbf805b14c3db111551b5e0a003a` | **0** |
| Entries anywhere with `model = qual-nonexistent-model-69ef035a` | **0** |

The rejected turn produced **no provider ledger entry at all**. The only
provider contact for that turn was the model inventory read
(`GET /v1/models`), which is how the system learns what is advertised — not an
inference request. The application-side and provider-side evidence agree.

The worker log confirms the same boundary from the other direction: for
thread 1 the worker logged `chat.inference.request.built` and completed; for
thread 2 it logged **no** `chat.inference.request.built` and instead failed the
task with `exception_type=HTTPException failure_class=http`.

## 11. Browser projection

Real browser: **Google Chrome 156.0.8078.80** (macOS), driven through the
Chrome DevTools Protocol. User agent reported by the page:
`Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML,
like Gecko) Chrome/156.0.0.0 Safari/537.36`.

| Requirement | Observation |
| --- | --- |
| Frontend availability | `GET http://127.0.0.1:5173` → HTTP 200; Vite 7.3.1 dev server; the page title is `Codexify` |
| Synthetic account authentication | the app resolved the local account automatically: `cfy.lastProjectId.account.local = "1"`, `cfy.userName` present; the UI reported **System status: Healthy** |
| Provider/model selection in the UI | `localStorage["guardian.provider.v1"] = "local"`, `localStorage["guardian.provider_model.v1"] = {"provider":"local","model":"local-chat"}` |
| Thread creation | the composer created a thread and the UI navigated to `http://localhost:5173/chat/4` |
| Chat submission | prompt "Reply with exactly: browser-gate-f" entered in the composer and submitted through the Send button |
| Event-stream delivery | the browser console logged `[live-events-hub] connected`; the SSE cursor `cfy.events.lastId` advanced 16 → 20 across the session; the stream was confirmed to deliver the same events through the frontend's own Vite proxy at `http://127.0.0.1:5173/api/events` |
| Successful completion rendering | the transcript rendered the user message at 07:23 PM, then the assistant message **"browser-gate-f"** at 07:24 PM attributed to *Guardian*, with the footer `Project · Whoosh'd · Gemma 4 12B IT QAT 4-bit · Fast`; the intermediate state showed `Working…` with a Stop control and then reconciled to a terminal state |
| Failed attempt rendering | navigating to `http://localhost:5173/chat/2` rendered **"1 earlier response task failed."** above the rejected user turn |
| Terminal-state reconciliation | no lingering `Working…` state; the system panel read `Ready` / `Completed` / "The model is loaded and ready for requests." |
| Refresh and re-entry readback | a full page reload of `/chat/4` preserved both the user prompt and the assistant reply, and the event cursor continued from 16 to 20 |
| Console errors | none. The only console `issue` was an accessibility hint that a form field element should have an id or name attribute |

## 12. Event stream and outbox

The live SSE surface delivers the full event history:

```
$ curl -N -H "X-API-Key: …" "http://127.0.0.1:8890/api/events?last_id=0"
retry: 3000

id: 1
event: thread.created
data: {"title": "New Chat", "user_id": "local", "thread_id": 1, "project_id": 1}

id: 2
event: message.created
data: {"role": "user", "content": "Reply with exactly: qual-compose-02", …}

id: 3
event: task.running
data: {"type": "chat_completion", "task_id": "2e3dc65e-…", "turn_id": "8bfa05cf-…", …}

id: 4
event: message.created
data: {"role": "assistant", "content": "qual-compose-02", …}
```

The same stream is reachable through the frontend's Vite proxy
(`http://127.0.0.1:5173/api/events`), which is the path the browser uses.

**Finding — the retained `pending` outbox rows are the implemented
behaviour, not a delivery failure.** All ten rows in `events_outbox` carried
`status = pending` at the end of the run, including the `task.completed` row
for the successful turn. That status is **not** evidence of failed
publication, and this run's evidence does not support a "the outbox did not
drain" conclusion. The following was verified in the evaluated source:

- `stream_events` (`guardian/guardian_api.py`) reads the outbox and keeps the
  rows. Its body carries the explicit marker: *"Keep outbox events intact so
  concurrent clients can resume independently without losing events due to
  destructive cleanup."*
- The read path `PgDB.list_events_after` filters only on `id > last_id` (plus
  tenant). It does **not** filter on `status`, and it does not even select the
  `status` column. Delivery never depends on a published status.
- The `status` column is schema-only at runtime. The table's DDL
  (`ac973209add4`) declares `status VARCHAR(32) NOT NULL DEFAULT 'pending'`
  with an index on `(status, created_at)`, and `guardian/db/models.py` maps it.
  The runtime model the outbox writer and reader actually use
  (`guardian/core/models.py`) does **not** map `status` at all, and nothing in
  the runtime ever transitions it. `pending` is therefore the permanent value
  and carries no publication semantics.

**The narrower open question is retention, not drainage.** The only deletion
API, `delete_events_through`, exists on `PgDB`, on `ChatDB`, and on the event
bus, but it has **no production caller** — its only callers are in
`guardian/tests/test_events_outbox.py`. The SSE path deliberately does not call
it. Two consequences follow, and both are narrower than "drain the outbox":

1. `status` is either vestigial — in which case it should be dropped or given
   meaning — or the publication state it was designed for was never wired up.
   Until that is settled it must not be read as a delivery signal.
2. Retention is currently **unbounded** in practice. The `stream_events`
   docstring still states *"Deletes events up to the last delivered id so the
   outbox does not grow unbounded"*, but no such deletion is implemented; the
   inline comment deliberately supersedes it. That is a
   documentation-versus-code drift, and it is where a bounded retention policy
   belongs.

Deleting or acknowledging these rows to make the table "drain" would break the
concurrent-client resume behaviour the implementation intentionally preserves.
No rubric check depends on outbox publication state, and the browser observed
the correct terminal rendering, so this is recorded as a finding rather than a
failure.

## 13. Restart recovery

Only qualification-owned application services were restarted. The Private
Preview was not touched.

```
docker compose -p codexify_qual_20261103 \
  -f docker-compose.yml -f docker-compose.whooshd-smoke.yml \
  restart backend worker-chat worker-document-embed
```

The restart was surgical: `backend`, `worker-chat`, and `worker-document-embed`
were the only containers whose uptime reset. `db`, `redis`, `neo4j`,
`frontend`, and the other workers kept their original uptimes.

| Requirement | Observation |
| --- | --- |
| Services return healthy | `backend` healthy; `/health/chat` → `ok: true`, `status: healthy`, worker heartbeat `fresh` (0.97 s), queue `progressing`, provider `local`, model `local-chat` |
| Existing thread survives | thread 4 message roles before → `['user','assistant']`, after → `['user','assistant']` |
| Messages survive | the pre-restart user message (id 6) and assistant message (id 7) are intact, with their original timestamps |
| Durable attempts remain consistent | attempt rows before → 4, after → 4, byte-identical across `request_id`, `backend_task_id`, `thread_id`, `turn_id`, `completed_message_id`, `terminal_event_type` |
| No duplicate completion appears | group-by counts: **0** attempts sharing a `turn_id`, **0** attempts sharing a `completed_message_id`. Thread 4 holds two assistant messages, but they are bound to two **distinct** turns (`69d44364…` and `cdef197f…`) — the second is the explicit post-restart re-completion, not a duplicate of the first |
| Ordinary chat works again | `POST /api/chat/4/complete` → HTTP 200, `task_id 9c57c44f-e15d-4212-945d-058490e3ec96`; assistant message id 8 rendered "browser-gate-f" |
| Document provenance remains accessible | thread 3's document `6e7675ed-98d2-4c9a-b269-c1ec6eb40998` still `embedding_status: ready`; `rag-trace` `trace_available: true`; `retrieval-posture` `status: ok` with the `same_user_same_project` boundary |
| Browser projection reconverges | the browser projection was re-read after the restart and continued to render the terminal states |

## 14. Baseline verification surfaces

All commands were executed from the frozen worktree at
`69ef035a4320724b9a53279d2fabd6bac0c6e98f`, using the repository's own
`.venv` (Python 3.12.13, pytest 8.4.2). Selector groups map to the surfaces
this task named.

| Group | Selector | Result |
| --- | --- | --- |
| Queue and worker lifecycle | `tests/workers/test_chat_worker_lifecycle_events.py`, `tests/workers/test_chat_worker_terminal_authority.py`, `tests/workers/test_chat_worker_heartbeat_activity.py`, `tests/queue/test_chat_redis_deadline.py` | **PASS** (86 tests, exit 0) |
| Cancellation and deadline behaviour | `tests/workers/test_chat_worker_queued_cancellation.py`, `tests/tasks/test_chat_completion_deadline.py`, `tests/core/test_chat_nonstream_accepted_deadline.py`, `tests/workers/test_chat_worker_queue_deadline.py` | **PASS** (exit 0) |
| Turn locks | `tests/queue/test_turn_lock.py`, `tests/core/test_turn_lock_recovery.py`, `tests/queue/test_terminal_turn_lock_cleanup.py` | **PASS** (27 passed on the host, plus 15 environment-gated proofs re-run — §14.1) |
| Account authorization | `tests/identity/test_task_event_stream_authorization.py`, `tests/identity/test_account_purpose_strict_migration.py` | **PASS** (62 tests, exit 0) |
| Provider/model authority | `tests/workers/test_chat_worker_explicit_model_authority.py`, `tests/test_local_model_default_authority.py`, `tests/core/test_supported_profile_provider.py` | **PASS** (19 tests, exit 0) |
| Migration contract | `tests/db/test_chat_completion_attempt_migration.py` | **PASS** (8 tests, exit 0) — see §14.1 |
| Retrieval provenance | `tests/core/test_retrieval_document_chunk_provenance.py`, `tests/context/test_retrieval_trace_provenance.py` | **PASS** (7 tests, exit 0) |
| Durable state integrity | `tests/test_chat_worker_turn_integrity.py`, `tests/workers/test_chat_worker_terminal_cleanup.py` | **PASS** (15 tests, exit 0) |
| Supported configuration | `tests/core/test_supported_profile.py`, `tests/ops/test_source_compose_supported_profile_contract.py`, `tests/proofs/test_supported_profile_live_proof_contract.py` | **PASS** (32 tests, exit 0) |

Exact invocation for every group:

```bash
.venv/bin/python -m pytest -q -p no:cacheprovider <selectors…>
```

### 14.1 Two groups were environment-gated; both were then executed

The first pass of two groups reported skips rather than results. Both skip
sets were **environment gates, not product failures**, and both were
subsequently executed rather than reported as passing.

**Migration contract — 8 skipped.** Reason: `TEST_DATABASE_URL required for
disposable Postgres proof`. The fixture creates and drops its own database
(`codexify_attempt_<uuid>`) and needs no product change. It was re-run with a
disposable endpoint inside a throwaway container on the qualification
network, using the source-matched image and the frozen worktree:

```bash
docker run --rm --network codexify_qual_20261103_default \
  --entrypoint python -v <frozen-worktree>:/app -w /app \
  -e TEST_DATABASE_URL="postgresql://codexify:codexify@db:5432/postgres" \
  -e PYTHONPATH=/app \
  codexify-backend-runtime:src-69ef035a4320 \
  -m pytest -q -rs -p no:cacheprovider \
  tests/db/test_chat_completion_attempt_migration.py
# 8 passed, exit 0
```

The fixture creates its own disposable database against the qualification
PostgreSQL and drops it afterwards; the qualification's own database was not
touched.

**Turn locks — 13 skipped.** Reason: `TEST_TERMINAL_LOCK_REDIS_URL required
for native cleanup proof`. The fixture uses Redis **database 15** and unique
key namespaces, so it is isolated from the queue's database 0. Redis publishes
no host port, so the proof was likewise run in a throwaway container on the
qualification network:

```bash
docker run --rm --network codexify_qual_20261103_default \
  --entrypoint python -v <frozen-worktree>:/app -w /app \
  -e TEST_TERMINAL_LOCK_REDIS_URL="redis://redis:6379/15" \
  -e PYTHONPATH=/app \
  codexify-backend-runtime:src-69ef035a4320 \
  -m pytest -q -rs -p no:cacheprovider \
  tests/queue/test_terminal_turn_lock_cleanup.py
# 15 passed, exit 0
```

**After re-running, the Gate H surface has zero skips.** Every selector in the
nine groups executed and passed.

### 14.2 Trio

Trio is **not installed** in this environment
(`ModuleNotFoundError: No module named 'trio'`). No selector in the nine
groups above is Trio-gated — the only skips observed were the two
environment gates in §14.1, and both were executed. Any Trio-only selector
outside these groups therefore remains **INPROVEN**, not PASS, and is not
counted as evidence here.

### 14.3 Other unrelated failures

No other failure was observed. The nine groups passed on the first execution
apart from the two environment gates above.

## 15. Gate matrix

| Gate | Result | Evidence |
| --- | --- | --- |
| Gate 0 — capacity and isolation | **PASS** | §2, §3 |
| Gate A — supported configuration | **PASS** | §4, §5 |
| Gate B — startup and migrations | **PASS** | §6 |
| Gate C — explicit-model authority | **PASS** | §10 |
| Gate D — ordinary chat and persistence | **PASS** | §8 |
| Gate E — document retrieval and provenance | **PASS**, with one recorded limitation | §9 |
| Gate F — browser and event coherence | **PASS** | §11, §12 |
| Gate G — restart recovery | **PASS** | §13 |
| Gate H — baseline contracts | **PASS** (nine groups, zero skips after §14.1) | §14 |

## 16. Explicit remaining failures and limitations

**Failures.** None. No rubric blocking criterion occurred. Specifically:
the supported topology started and every required service was healthy; the
runtime matched the supported profile's provider contract; the explicitly
unavailable model was rejected before provider execution with no substitute
and no persisted assistant message; every accepted completion reached a
terminal outcome; every persisted assistant message has a matching durable
attempt; durable state survived the restart; and the evaluated commit was
identifiable throughout.

**Limitations.**

1. The `rag-trace` HTTP operator surface returns empty `documents`/`graph`
   and `retrieval_provenance: null` while the durable trace record holds the
   document and chunk attribution. §9.
2. `worker-coding` runs a pre-baked, non-source-matched image. It is outside
   this rubric and outside the supported profile, and it was not qualified
   here. §5.
3. The `events_outbox` was never drained; all ten rows remained `pending`
   while the live SSE stream delivered the same events. §12.

**Unproven.**

- Any boundary outside the supported local-only profile — the Private Preview
  lane, cloud providers, federation, connectors, hosted sandbox, Atlas, Pi,
  and the autonomous coding worker remain unqualified by this run.
- The `rag-trace` and `evals` operator surfaces as *operator-facing* views
  are not proven to work, even though the per-message provenance they draw
  from is present and correct.

## 17. Private Preview isolation

The Private Preview lane was snapshotted before the run and re-verified
afterwards. This run issued no command that targeted the preview project: no
stop, no restart, no prune, no modification.

| Resource | Before | After |
| --- | --- | --- |
| Containers | 18 | 18 |
| Volumes (project-labelled) | 8 | 8 |
| Networks | 1 (`codexify_private_preview_default`) | 1 |
| Backend image | `sha256:22d9f5f13e7d9889794efa32385ee9e790eaacaff5edf7ca9e41a41a1e6e5c55` | unchanged |
| Postgres volume | `codexify_private_preview_pg_data` | unchanged |
| `alembic_version` readback | `3a91d7c4e8b2` | unchanged |
| Public tables | 138 | unchanged |
| Long-running container uptime at close | — | 3 hours continuous, never restarted by this run |

The before and after snapshots were compared field by field, including the
container ID of every one of the 18 containers. The comparison reports **no
differences**: same container IDs, same images, same states, same volumes,
same network, same backend image digest, same Alembic head, same table
count.

The thirteen long-running Preview services held a continuous 3-hour uptime
from before the qualification began through to close, including across this
run's application restart. The five one-shot Preview services (`migrator`,
`graph-init`, `model-prep`, `e2e`, `private-preview-auth-posture`) were
re-executed on the host by another actor at `2026-11-04T00:38:28Z` — after
this run's last qualification action (`00:26:46Z`), and by no command in
this run. Those services are `restart: no` one-shot jobs, so a re-execution
reuses the existing container rather than replacing it: the container IDs are
unchanged, and the durable state they own — the database, its Alembic head,
and its table count — is unchanged as well. The preview's migrator finished
exit 0 against the already-current head and applied no new revision.

## 18. Cleanup

Cleanup is project-scoped and ownership-verified. Only objects carrying the
`com.docker.compose.project=codexify_qual_20261103` label were removed.

### 18.1 Ownership verification

Before anything was removed, the complete qualification-owned inventory was
recorded and every object was confirmed to carry the qualification project
label:

| Object class | Count | Ownership evidence |
| --- | --- | --- |
| Containers | 16 | every one labelled `com.docker.compose.project=codexify_qual_20261103` |
| Volumes | 8 | every one named `codexify_qual_20261103_*` and project-labelled |
| Networks | 1 | `codexify_qual_20261103_default`, project-labelled |

No object belonging to `codexify_private_preview`, `codexify-devproxy`, or any
other project's containers, volumes, networks, or images appeared in that
inventory.

### 18.2 Teardown executed

```bash
docker compose -p codexify_qual_20261103 \
  -f docker-compose.yml \
  -f docker-compose.whooshd-smoke.yml \
  down --remove-orphans -v
```

Exit code 0. The same two compose files and the same project name the
repaired launcher used, so the teardown targeted exactly the project this run
created.

### 18.3 Residue after teardown

| Check | Result |
| --- | --- |
| Containers labelled `codexify_qual_20261103` | 0 |
| Volumes labelled `codexify_qual_20261103` | 0 |
| Networks labelled `codexify_qual_20261103` | 0 |
| Containers whose name contains `codexify_qual_20261103` | 0 |
| Volumes whose name contains `codexify_qual_20261103` | 0 |
| Networks whose name contains `codexify_qual_20261103` | 0 |
| Host free space on `/Volumes/Dev_SSD` | 11 GB before -> 13 GB after |
| Private Preview after-snapshot vs before-snapshot | no differences (§17) |
| Host Whoosh'd | healthy, still advertising `local-chat`, not restarted |

### 18.4 Retained residue, stated explicitly

One qualification-owned object was deliberately **not** removed:

| Object | Identity | Size | Why retained |
| --- | --- | --- | --- |
| Image | `codexify-backend-runtime:src-69ef035a4320` | `sha256:0ecc261727e61eeaad44c48d0c434479a92a8fdb378af82c6f4cb22c9dde1f65` - 4,654,664,374 bytes | It is the Gate A evidence artifact whose digest this proof cites. Removing it would destroy both the reproducibility of the run and the recorded image identity. |

The teardown scope authorized for this task was containers, volumes, and
networks; images were not in it. No `docker image prune`,
`docker system prune`, `docker volume prune`, or `docker builder prune` was
run at any point in this task. The retained image can be removed on request
with `docker image rm codexify-backend-runtime:src-69ef035a4320`.

## 19. Reproducing this run

```bash
# frozen worktree
git worktree add --no-checkout --detach \
  /Volumes/Dev_SSD/Codexify-main/.worktrees/qual-compose-02 69ef035a4
cd /Volumes/Dev_SSD/Codexify-main/.worktrees/qual-compose-02
git sparse-checkout init --no-cone
git sparse-checkout set '/*' '!/.claude/**'
git checkout 69ef035a4

# operator environment, cloud credentials blanked and the supported
# profile's provider_contract applied (see §3)
export COMPOSE_ENV_FILES=<qual.env>
export CODEXIFY_RUNTIME_ENV_FILE=<qual.env>
export CODEXIFY_BACKEND_PORT=8890
export DOCKER_CONTEXT=desktop-linux

# the repaired canonical startup path, detached
bash scripts/whooshd_docker_smoke_up.sh full --detach \
  --project codexify_qual_20261103
```

Two provisioning notes for any future run, both learned here:

- the `./models` bind source must be a **real directory tree**, not a
  symlink, or `model-prep` fails with `[Errno 17] File exists`;
- `./.chroma`, `./data/media`, and `./data/imports` must exist as real
  directories so Docker does not create them with root ownership.

## 20. Validation

All commands were run from the frozen worktree at
`69ef035a4320724b9a53279d2fabd6bac0c6e98f`, after the run's cleanup, against the
working tree that produced this proof and the run receipt.

| # | Command | Result | Exit |
| --- | --- | --- | --- |
| 1 | `python scripts/qualification/generate_registry.py` | `Wrote docs/qualification/registry.json (2 qualification surface(s), tip 69ef035a4320724b9a53279d2fabd6bac0c6e98f).` | 0 |
| 2 | `python scripts/qualification/generate_registry.py --check` | `OK: docs/qualification/registry.json matches the projection at tip 69ef035a4320724b9a53279d2fabd6bac0c6e98f.` | 0 |
| 3 | `python scripts/qualification/validate_registry.py` | `Qualification registry validation pass: .../docs/qualification/registry.json (0 issue(s))` | 0 |
| 4 | `python scripts/validate_docs.py` | `Docs validation passed: required architecture docs, README links, and source headings verified.` | 0 |
| 5 | `git diff --check` | clean — no whitespace errors | 0 |
| 6 | `PYTHONDONTWRITEBYTECODE=1 .venv/bin/python scripts/knowledge_graph/validate_and_generate_dlg.py validate` | `result: pass`, `repository_revision: 69ef035a4320724b9a53279d2fabd6bac0c6e98f`, 0 errors, 6 warnings | 0 |
| 7 | `.venv/bin/python -m pytest -q -rs -p no:cacheprovider tests/qualification/` | 38 passed, 0 skipped | 0 |

The six DLG warnings are all `broken_local_markdown_link` against
`docs/architecture/README.md`. They are pre-existing: the same count and the
same code are recorded in the earlier supported-compose proof
(`docs/architecture/proofs/runtime/2026-10-30-supported-compose-qualification-41ff6152.md`,
§"Document validation"), and this run changed no link target. DLG validation
ran against the frozen revision itself, not against a later tip.

### 20.1 The generated registry agrees with the receipt

The registry is generated, never hand-edited. The projection was compared
field by field against the run receipt's `qualification-metadata` block:

| Field | Receipt | Generated registry | Agree |
| --- | --- | --- | --- |
| `qualification_id` | `supported-compose` | `supported-compose` | yes |
| `rubric_version` | 1 | rubric `rubrics/supported-compose.md`, version 1 | yes |
| `verdict` / `status` | `PASS` | `PASS` | yes |
| `commit` / `tested_commit` | `69ef035a4320724b9a53279d2fabd6bac0c6e98f` | `69ef035a4320724b9a53279d2fabd6bac0c6e98f` | yes |
| `date` / `last_qualified_at` | `2026-11-03` | `2026-11-03` | yes |
| `evidence` | the detailed proof | the detailed proof | yes |

The projection also reports `freshness: current`, which is computed rather
than declared: the tested commit is an ancestor of the projected tip and no
path in the rubric's declared surface (`docker-compose*.yml`,
`config/supported_profiles/**`, `guardian/core/**`, `guardian/queue/**`,
`guardian/routes/**`, `guardian/workers/**`, `guardian/db/migrations/**`)
changed between the tested commit and the tip.

One blocker is projected, and it is factual rather than adverse:

> 1 earlier run receipt(s) for this surface were superseded by a later run.

That is the September 2026 run, which this run supersedes. `run_receipts`
for the surface is now 2. `human_testers` remains 0 and
`independent_completions` remains 0, because this run was automated — an
automated run is never counted as an independent human qualification.

**No contradiction was found.** Generation did not contradict the recorded
evidence, so the run proceeded to publication.
