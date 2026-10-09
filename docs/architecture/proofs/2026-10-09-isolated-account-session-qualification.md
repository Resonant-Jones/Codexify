# Isolated two-account session qualification — 2026-10-09

## Result and scope

**PASS: Astra Goal 04's isolated two-account authentication prerequisite.**

At the exact R5 source, two synthetic canonical `User` rows, credentials issued
by the existing account-session signer, and subject bindings registered through
the existing Redis `SessionStore` authorized real HTTP requests to mounted
account-import routes. PostgreSQL readback proved independent job ownership.
All 25 expected HTTP results matched, including cross-account read/stage/commit
denial, ignored identity headers, quarantined authentication endpoints, and
revocation. No authentication dependency was mocked or patched.

This is trusted, explicitly authorized fixture provisioning into a disposable
database. It establishes a reproducible prerequisite for the next R5 proof;
it does not establish a shipped onboarding procedure or general multi-user
Beta support. No conversation import, embedding handoff, retrieval selection,
provider-context inclusion, or assistant answer was exercised. Natural recall
remains **UNPROVEN**. Release **HOLD is unchanged**.

Only this proof artifact changes. Application source, tests, supported-profile
manifest, current-state document, and the earlier R5 receipt remain unchanged.

## Frozen source and orientation

- Mode: **PROOF**, architecture-impact acceptance lane. Read the Axis invocation
  and task-generation protocols, current-state, architecture README/ADR index,
  Account Export + Restore Contract, R5 receipt, and the named authentication,
  account-import, identity and regression surfaces before live qualification.
- Evaluated HEAD: `bfd3da6b3b53a0cc07afca3e9a638b3773d0033a`, exactly the task's
  R5 commit; branch `codex/synthetic-account-import-recall-qualification`.
- Physical checkout:
  `/Volumes/Dev_SSD/offload/codex/worktrees/synthetic-import-recall/Codexify-main`.
  Initial and pre-artifact `git status --short` were empty.
- Source is intentionally frozen, not silently substituted for current main.
  Before this artifact, local main was
  `9405ba325f49f6b8db00901fe05120894f266d92`; cached `origin/main` was
  `d89459b6dbff08e8bdf0f030fc459d4c207fdb95`.
  `git rev-list --left-right --count main...HEAD` returned `1 2`;
  `main...origin/main` returned `5 124`. These are local ref observations;
  this task did not fetch, adopt, or qualify moving mainline code.
- The unrelated active checkout remained at
  `bd4f36346f816d82a9f86eeee2524edadd3465bb`, branch
  `codex/invocation-scoped-execution-binding`, with its pre-existing untracked
  `Codexify.Space/`, `guardian/core/scout_account_transport.py`,
  `guardian/core/scout_handoff.py`, `guardian/core/scout_qualification.py`, and
  `guardian/routes/scout_auth.py` untouched.

## Architecture and authority

Aligned with accepted existing contracts; no new ADR or contract change.

| Anchor | Application to this proof |
| --- | --- |
| [ADR-005](../adr/005-runtime-mode-and-account-boundary-invariants.md) | Preserve single-user runtime posture; fixture principals do not enable a general multi-user deployment. |
| [ADR-069](../adr/069-codexify-beta-runtime-support-boundary.md) | Preserve `v1-local-core-web-mcp` and distinguish bounded proof from runtime/release support. |
| [ADR-081](../adr/081-project-ownership-authority.md) | Canonical server-side ownership, not source metadata or caller claims, controls access; no Project ownership change occurs. |
| [ADR-092](../adr/092-credential-purpose-and-mixed-principal-authentication-boundary.md) | Use canonical `account_session` issuance and verified subject bindings; preserve its explicitly separate local/single-user behavior. |
| [Account Export + Restore Contract](../account-export-restore-contract.md) | PostgreSQL owns durable account-import jobs; authenticated account scope is authority. No archive metadata, import execution, or personal-memory promotion occurs. |

The authoritative objects were `users.id`, Redis's server-registered session
subject, and `openai_account_import_jobs.user_id`. The human task authorized
fixture provisioning; the existing signer/store and real request dependencies
authorized each API operation. HTTP bodies, job IDs, header claims, runtime
identity and this receipt are evidence, not grants of account authority.

`guardian/routes/migration.py` imports `get_account_user_id` and
`require_account_session` as its request-owner and credential dependencies.
With `GUARDIAN_AUTH_MODE=local`, `verify_account_session` delegates to the
unchanged `verify_api_key`, and `get_request_user_id` uses an approved session
store binding before local fallback. The fixture validates signature, exact
purpose and signed/stored subject agreement before presenting credentials.

**Bounded purpose result:** the issued fixture tokens are purpose-bound and
validated by the canonical purpose/subject helpers. This local HTTP lane does
not independently enforce the full remote ADR-092 purpose/mixed-principal
contract. The operator negative below was unregistered; it does not prove
rejection of an operator token incorrectly registered as an account session.
No malformed Redis binding, remote/Preview boundary, guest lane or public
ingress is qualified here. Tightening local behavior would be a separate task.

## Runtime isolation

macOS/arm64, Docker Desktop `desktop-linux`, server 29.8.2. Existing host venv
Python 3.12.13/pytest 8.4.2 was read without dependency installation. A fresh
runtime image was built from frozen source using `backend/Dockerfile` and its
canonical backend requirements (Python 3.11.14). Build and migration exited 0.

- Project: `codexify_account_session_20261009`; only `db`, `redis`, and `backend`
  ran. No import worker or chat worker was started; no owner job was committed.
- Image: `codexify-session-proof:bfd3da6b3`, actual container image
  `sha256:b760ccff6e4f5994a131ba9c375e5dafc41a99e23df0f489a3430e55377622c0`.
- PostgreSQL 15 used new project volume
  `codexify_account_session_20261009_pg_data`, loopback port `57494`, and
  migration head `17b23052da6a`. Before fixtures, `users` contained only
  `local | local | guest`.
- Redis 7 used a fresh container and anonymous volume
  `93700baaa715682e15d77afd094bab4132717882334b97b43cfc12ca729cbbe7`.
  Redis persistence was disabled; sessions never touched another runtime.
- Fresh project volumes `session_vectors`, `session_imports`, and
  `session_media` isolated vector, fixture staging and media storage.
- Frozen `guardian` and `config` binds were read-only. Existing local BGE
  weights were read-only at `/models/bge-large-en-v1.5`. Backend application
  code came from the fresh image. Eight authority/profile files matched
  frozen checkout SHA-256 values inside the running container.
- New task-only session secret, service key and database password were generated
  with Python `secrets`; no shared session/signing/config volume was adopted.
  Credential files were mode 0600 and are excluded from this receipt.
- The final backend set existing `CODEXIFY_IDENTITY_DIR=/app/data/identity`
  explicitly, causing the existing identity generator to avoid legacy tracked
  identity migration and create an independent key in its disposable writable
  layer. That identity is separate from the two database account principals.
  An initial successful probe was repeated after adding this guard; the final
  receipt below is the run with the explicit identity override.
- Live posture: profile `v1-local-core-web-mcp`, `auth=quarantined`, auth mode
  `local`, exposure `local_safe`, multi-user disabled, `DEBUG=false`,
  `LOCAL_DEV=false`, `DEV_MODE=false`. Local-only provider posture, cloud
  credentials empty, graph writes disabled; no Preview flags were enabled.
- API exposed only `127.0.0.1:58894`; probes executed inside the container via
  actual listening HTTP API at `http://127.0.0.1:8888`, without TestClient or
  authentication monkeypatches. Host `/ping` returned 200.
- Resource bounds: database 256 MiB, Redis 64 MiB, backend 1800 MiB/one CPU.
  All three containers were running with `OOMKilled=false` when inspected.
  This API subset does not qualify full profile startup, frontend or workers.

Network: `codexify_account_session_20261009_default`, ID `e3584ff5ede7c6cd99a3dda7bd04199e96ccfc1b0283bbc0f68dc9e6808ed416`.

| Service | Final container ID |
| --- | --- |
| backend | `c44d46af5b027beeed74cfe9617fb22853fddedcb23a612662c462e803729b49` |
| db | `77cc8747e72d87b09794c9b23d4c9be47725ed6f5ac7bccfe4b2129562049e36` |
| redis | `5218cf80379553b7f82e26076a4f5432e834efe46168525c546224f915012292` |

Independent runtime identity: `user_7d0095feac3277b30044359ab817bf812c68a77ff5f7d79aa84a06b2f21bf75e`, created
`2026-10-09T16:48:34.624878Z`, key version 1. Public-key-string
SHA-256: `91332e0ba00443ee746709002af476dd75192190de620a2f6dcc6113c66d1ac8`.
No private identity key was copied into the artifact.

## Canonical fixture and live results

Synthetic accounts A/B were inserted with the existing `User` ORM and
`GuardianDB.get_session`, distinct IDs/usernames, `role=guest`, and canonical
`hash_password(secrets.token_urlsafe(32))`. No password login was used. This is
an explicitly authorized operator fixture step, not an exposed registration
endpoint or an alternate identity model. `UserManager` seeds only `local`;
this task does not pretend it provisions arbitrary accounts.

The existing `issue_session_token` issued A/B credentials with independent
nonces, 900-second TTL and `purpose=ACCOUNT_SESSION_PURPOSE`. The canonical
`SessionStore.store(token, user_id, 900)` registered each matching subject.
Tokens stayed in process memory and the disposable Redis store, never in logs,
command arguments, receipt bodies or repository files.

| Canonical account | Signature | Account purpose | Operator purpose | Signed/store/resolver match | Expiry (Unix UTC) |
| --- | --- | --- | --- | --- | ---: |
| `session-proof-20261009-a` | PASS | true | false | PASS / PASS / PASS | 1791565415 |
| `session-proof-20261009-b` | PASS | true | false | PASS / PASS / PASS | 1791565415 |

The fixture was only `fixture.txt`: ASCII `SYNTHETIC SESSION FIXTURE\n`, 26
bytes. Both jobs declared one file/26 bytes; A staged that file. This is not an
OpenAI export and was never committed for ingestion. No private archive was
accessed. API serialization omits `user_id`; live identity is demonstrated by
HTTP-created job IDs joined to independent PostgreSQL ownership readback.

| Job ID | Canonical `user_id` | Status after probes | Uploaded files/bytes | Imported threads/messages |
| --- | --- | --- | --- | --- |
| `b0e7e003-7fb5-4901-aa11-5fbb82ad6bfc` | `session-proof-20261009-a` | receiving | 1 / 26 | 0 / 0 |
| `ed0f7a78-54ea-4712-be85-6021646e6b89` | `session-proof-20261009-b` | receiving | 0 / 0 | 0 / 0 |

All outcomes below are **PASS**, with expected status equal to observed status.
`J_A`/`J_B` expand to the corresponding job IDs above. Tokens are described by
role only. Positive owner calls used `Authorization: Bearer` with that owner's
canonical credential. A's successful stage and B's zero uploads demonstrate
that the negative stage/commit probes did not mutate another account's job.

| Probe | Actual request | Expected | Observed |
| --- | --- | ---: | ---: |
| `a_create` | `POST /api/imports/openai-account` | 200 | 200 |
| `a_read_own` | `GET /api/imports/openai-account/J_A` | 200 | 200 |
| `b_create` | `POST /api/imports/openai-account` | 200 | 200 |
| `b_read_own` | `GET /api/imports/openai-account/J_B` | 200 | 200 |
| `b_read_a` | `GET /api/imports/openai-account/J_A` | 404 | 404 |
| `b_stage_a` | `POST /api/imports/openai-account/J_A/files` | 404 | 404 |
| `b_commit_a` | `POST /api/imports/openai-account/J_A/commit` | 404 | 404 |
| `a_read_b` | `GET /api/imports/openai-account/J_B` | 404 | 404 |
| `a_claim_b_header` | `GET /api/imports/openai-account/J_A` | 200 | 200 |
| `b_claim_a_header` | `GET /api/imports/openai-account/J_A` | 404 | 404 |
| `missing_credentials` | `GET /api/imports/openai-account/J_A` | 401 | 401 |
| `missing_claim_a` | `GET /api/imports/openai-account/J_A` | 401 | 401 |
| `tampered_account_a` | `GET /api/imports/openai-account/J_A` | 401 | 401 |
| `invalid_claim_a` | `GET /api/imports/openai-account/J_A` | 401 | 401 |
| `signed_unregistered` | `GET /api/imports/openai-account/J_A` | 401 | 401 |
| `operator_without_account_binding` | `GET /api/imports/openai-account/J_A` | 401 | 401 |
| `static_service_key` | `GET /api/imports/openai-account/J_A` | 404 | 404 |
| `service_key_claim_a` | `GET /api/imports/openai-account/J_A` | 404 | 404 |
| `a_stage_own` | `POST /api/imports/openai-account/J_A/files` | 200 | 200 |
| `quarantined_/api/auth/register` | `POST /api/auth/register` | 404 | 404 |
| `quarantined_/auth/register` | `POST /auth/register` | 404 | 404 |
| `quarantined_/api/auth/login` | `POST /api/auth/login` | 404 | 404 |
| `quarantined_/auth/login` | `POST /auth/login` | 404 | 404 |
| `a_revoked_own` | `GET /api/imports/openai-account/J_A` | 401 | 401 |
| `b_revoked_own` | `GET /api/imports/openai-account/J_B` | 401 | 401 |

`a_claim_b_header` used A's bearer plus `X-User-Id: session-proof-20261009-b`;
`b_claim_a_header` used B's bearer plus A's claimed header. Headers did not
change the authenticated owner. Missing/invalid credentials with A's header
also failed. Static service-key-only requests, with and without an A identity
claim, could not read A's resource (404); they did not become A. This preserves
the local service-key/default-local scope behavior, rather than claiming all
service-key-only calls are rejected as 401.

The signed-unregistered account token returned 401. A canonical operator-purpose
credential without an account binding returned 401 and failed the exact
account-purpose helper. Both cases establish this fixture's approved binding
requirement; they do not expand the bounded local-purpose claim above.

Inspectably sanitized cross-account failure excerpt:

```json
{
  "detail": {
    "code": "account_import_not_found",
    "message": "Account import job was not found."
  },
  "request_id": "req_f5c0e377b2e140e2ac57df0ffa3743ff"
}
```

After canonical `store.revoke` for both A and B, `store.verify` returned `None`;
the same bearer credentials read against their own existing jobs returned 401.
Only after those live revocation probes were the fixture jobs/accounts deleted.

## Validation and evidence boundaries

Commands ran from the frozen physical checkout. `PY` below was the existing
`/Volumes/Dev_SSD/Codexify-main/.venv/bin/python`; `P` was
`/private/tmp/codexify-account-session-20261009`. No dependencies were installed
into that shared host environment. Mock embeddings applied only to regression
and migration processes, not to live authentication substitution.

```bash
CODEXIFY_CONFIG_SOURCE=core CODEXIFY_DISABLE_DOTENV=1 \
  CODEXIFY_EMBEDDINGS_BACKEND=mock "$PY" -m pytest -v tests/core/test_auth_boundary.py
CODEXIFY_CONFIG_SOURCE=core CODEXIFY_DISABLE_DOTENV=1 \
  CODEXIFY_EMBEDDINGS_BACKEND=mock "$PY" -m pytest -v tests/core/test_multi_user_auth_mode.py

docker build --target runtime -f backend/Dockerfile -t codexify-session-proof:bfd3da6b3 .
compose_session() {
  docker compose --project-name codexify_account_session_20261009 \
    --env-file "$P/runtime.env" -f docker-compose.yml \
    -f docker-compose.whooshd-smoke.yml -f "$P/override.yml" "$@"
}
compose_session config --format json > "$P/rendered.json"
compose_session up -d --no-deps db redis
docker exec codexify_account_session_20261009-db-1 pg_isready -U codexify -d Codexify
DATABASE_URL=<task-only-postgres-DSN> CODEXIFY_CONFIG_SOURCE=core \
  CODEXIFY_DISABLE_DOTENV=1 CODEXIFY_EMBEDDINGS_BACKEND=mock \
  /Volumes/Dev_SSD/Codexify-main/.venv/bin/alembic -c backend/alembic.ini upgrade head
compose_session up -d --no-deps --no-build backend
# Repeated after the existing identity-directory override was made explicit.
curl --max-time 5 -sS http://127.0.0.1:58894/ping
docker exec -i codexify_account_session_20261009-backend-1 python \
  < "$P/qualify_sessions.py" > "$P/live.log" 2>&1
docker cp codexify_account_session_20261009-backend-1:/app/data/imports/session-qualification/receipt.json \
  "$P/receipt.json"
```

| Stage | Classification | Observed evidence |
| --- | --- | --- |
| Exact source/profile | PASS | R5 SHA frozen; 8 host/container file hashes match; profile file unchanged. |
| Independent services/storage/secret/identity | PASS | New project/network/volumes; fresh secrets; explicit independent identity generator. |
| Canonical account/session fixture | PASS | Distinct User rows; exact-purpose signer, signature and signed/store/resolver consistency checks. |
| Real request identity and durable ownership | PASS | Own create/read 200 joined to canonical job owners. |
| Negative account and header isolation | PASS | Cross-account read/stage/commit 404; missing/invalid 401; identity claims ignored. |
| Auth quarantine | PASS | All four registration/login aliases 404; manifest unchanged. |
| Canonical revocation | PASS | Both Redis bindings absent, subsequent HTTP owner reads 401. |
| `tests/core/test_auth_boundary.py` | PASS | **9 passed in 8.04s**, exit 0. |
| `tests/core/test_multi_user_auth_mode.py` | PASS | **3 passed in 87.22s**, exit 0. |
| Import/embedding/natural recall | NOT EXECUTED | Explicitly outside Goal 04. No R5 PASS is inferred. |
| Cleanup | PASS | Exact fixture records removed; zero session bindings and no project resources remain. |

Live ORM mapper configuration emitted an existing `MemoryRecord.project` /
`MemoryRecord.user` overlapping-relationship SAWarning. Startup also logged
redacted warnings around default-project role and provider-row synchronization.
Neither blocked the measured HTTP/ownership gates; no repair was attempted.
An early `/healthz` returned 200 with false table flags despite successful
migration and subsequent SQL/API reads. It was not used as schema or full
runtime readiness proof. `/ping`, actual API operations and PostgreSQL
readback establish only the measured session/resource slice.

## Cleanup and preservation

The driver revoked only its own issued tokens, deleted exactly its created job
IDs and synthetic account IDs, and removed the corresponding staged directories.
Independent SQL readback before stack removal returned:

```text
id   | username | role
-------+----------+-------
 local | local    | guest
(1 row)

 import_jobs_remaining
-----------------------
                     0
(1 row)

 version_num
--------------
 17b23052da6a
(1 row)
```

A Redis count of `session:*` returned `0` without printing any session keys.
The original `local` user remained. All fixture operations were inside the
new database; no existing user archive, import database or shared volume was
mounted or mutated.

```bash
compose_session down --volumes
# Inspect project labels only; each list was empty.
docker ps -a -q --filter label=com.docker.compose.project=codexify_account_session_20261009
docker network ls -q --filter label=com.docker.compose.project=codexify_account_session_20261009
docker volume ls -q --filter label=com.docker.compose.project=codexify_account_session_20261009
docker image rm codexify-session-proof:bfd3da6b3
```

Task containers, project network, all created named volumes and the inspected
anonymous Redis volume were removed. The unique image tag/image was removed;
no global prune or reset was run. Temporary task secrets, rendered configuration,
identity keys and proof workspace files were removed after this durable receipt
was authored. The runnable driver and sanitized evidence excerpts below preserve
reproducibility; ephemeral credentials and services are not retained for reuse.

## Reproduction without stored credentials

Use the frozen R5 SHA in an isolated checkout; choose fresh project/ports if
these names are in use. Verify the project has no existing resources before
creating it. Copy the YAML and driver below into a temporary directory outside
the repo. Generate fresh secrets into a mode-0600 runtime env file without
printing them. The actual nonsecret env values and generation recipe are:

```python
import os, secrets
from pathlib import Path
p = Path('/private/tmp/codexify-account-session-20261009')
p.mkdir(exist_ok=True)
values = {
    'CODEXIFY_RUNTIME_ENV_FILE': '/private/tmp/codexify-account-session-20261009/runtime.env',
    'CODEXIFY_SUPPORTED_PROFILE': 'v1-local-core-web-mcp',
    'CODEXIFY_CONFIG_SOURCE': 'core',
    'CODEXIFY_DISABLE_DOTENV': '1',
    'GUARDIAN_AUTH_MODE': 'local',
    'GUARDIAN_EXPOSURE_MODE': 'local_safe',
    'CODEXIFY_MULTI_USER_ENABLED': 'false',
    'DEBUG': 'false',
    'LOCAL_DEV': 'false',
    'DEV_MODE': 'false',
    'LOCAL_CHAT_MODEL': 'local-chat',
    'CODEXIFY_EMBEDDINGS_BACKEND': 'local',
    'CODEXIFY_ALLOW_EMBEDDINGS_FALLBACK': '0',
    'CODEXIFY_VECTOR_STORE': 'chroma',
    'CODEXIFY_CHROMA_PATH': '/app/.chroma',
    'CODEXIFY_COLLECTION': 'account_session_proof',
    'LOCAL_EMBEDDINGS_REQUIRED': '1',
    'CODEXIFY_VOICE_ROUTES_ENABLED': 'false',
    'CODEXIFY_VOICE_TURNS_ENABLED': 'false',
    'CODEXIFY_ENABLE_GRAPH_WRITES': 'false',
    'CODEXIFY_GRAPH_BACKEND': 'noop',
    'OMP_NUM_THREADS': '1',
    'MKL_NUM_THREADS': '1',
}
for key in ('GUARDIAN_API_KEY', 'GUARDIAN_SESSION_SECRET', 'POSTGRES_PASSWORD', 'NEO4J_PASS'):
    values[key] = secrets.token_hex(32)
f = p / 'runtime.env'
fd = os.open(f, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
with os.fdopen(fd, 'w') as stream:
    stream.write(''.join(f'{k}={v}\n' for k, v in values.items()))
```

The database DSN above is redacted, not a command to paste with literal
angle-bracket text. Derive it from the generated PostgreSQL password in-process
as `postgresql://codexify:<generated-password>@127.0.0.1:57494/Codexify`, pass it
as `DATABASE_URL` only to the migration process, and do not print it. Wait for
`pg_isready`, run migration, start the backend, wait for `/ping`, then execute
the driver against actual HTTP. Its receipt contains identifiers/results only.
Do not enable auth routes or reconfigure multi-user/Preview to reproduce this.

Exact final temporary `override.yml` (physical paths identify this execution;
adapt only the frozen checkout/model paths for another isolated host):

```yaml
services:
  db:
    ports: !override ["127.0.0.1:57494:5432"]
    mem_limit: 256m
  redis:
    mem_limit: 64m
    command: ["redis-server","--save","","--appendonly","no","--maxmemory","32mb","--maxmemory-policy","noeviction"]
  backend:
    image: codexify-session-proof:bfd3da6b3
    restart: "no"
    cpus: 1
    mem_limit: 1800m
    ports: !override ["127.0.0.1:58894:8888"]
    depends_on: !override {}
    volumes: !override
      - "/Volumes/Dev_SSD/offload/codex/worktrees/synthetic-import-recall/Codexify-main/guardian:/app/codexify:ro"
      - "/Volumes/Dev_SSD/offload/codex/worktrees/synthetic-import-recall/Codexify-main/config:/app/config:ro"
      - "/Volumes/Dev_SSD/Codexify-main/models/bge-large-en-v1.5:/models/bge-large-en-v1.5:ro"
      - "session_vectors:/app/.chroma"
      - "session_imports:/app/data/imports"
      - "session_media:/app/data/media"
    environment:
      CODEXIFY_IDENTITY_DIR: /app/data/identity
      HF_HUB_OFFLINE: "1"
      CODEXIFY_DISABLE_DOTENV: "1"
      GUARDIAN_AUTH_MODE: local
      GUARDIAN_EXPOSURE_MODE: local_safe
      CODEXIFY_MULTI_USER_ENABLED: "false"
      DEBUG: "false"
      LOCAL_DEV: "false"
      DEV_MODE: "false"
      OMP_NUM_THREADS: "1"
      MKL_NUM_THREADS: "1"
volumes:
  session_vectors: {}
  session_imports: {}
  session_media: {}
```

Exact final temporary `qualify_sessions.py` follows. It is a disposable operator
fixture, not a new application harness or API. Run only against a verified
fresh task-owned database/runtime; its cleanup is intentionally fixture scoped.

```python
"""Authorized, disposable canonical User/signer/SessionStore fixture and real HTTP probes."""
import json,secrets,os,time,hashlib,shutil
from datetime import datetime,timezone
from pathlib import Path
import requests
from sqlalchemy import select,delete,func
from guardian.core.db import load_guardian_db_from_env
from guardian.core.passwords import hash_password
from guardian.core.auth import ACCOUNT_SESSION_PURPOSE,OPERATOR_SESSION_PURPOSE,issue_session_token,verify_session_token_for_purpose,verify_session_token,resolve_account_session_subject
from guardian.core.session_store import get_session_store
from guardian.core.dependencies import _auth_mode
from guardian.core.config import get_settings
from guardian.core.supported_profile import get_active_supported_profile
from guardian.db.models import User,OpenAIAccountImportJob
from guardian import identity
p=Path('/app/data/imports/session-qualification');p.mkdir(exist_ok=True)
receipt={'status':'RUNNING','accounts':[],'http':[],'ownership':[],'revocation':[],'cleanup':{}}
store=get_session_store(); db=load_guardian_db_from_env(); assert db is not None
accounts={'a':'session-proof-20261009-a','b':'session-proof-20261009-b'}; tokens={}; extra_tokens=[]; locators=[]; jobs={}
def save(): (p/'receipt.json').write_text(json.dumps(receipt,indent=2))
def probe(label,actor,method,path,expected,credential=None,headers_extra=None,**kwargs):
 headers={}
 if actor in tokens:headers['Authorization']='Bearer '+tokens[actor]
 if credential is not None:headers['Authorization']='Bearer '+credential
 if headers_extra:headers.update(headers_extra)
 x=requests.request(method,'http://127.0.0.1:8888'+path,headers=headers,timeout=15,**kwargs)
 try: body=x.json()
 except Exception: body={'non_json':True}
 receipt['http'].append({'label':label,'actor':actor,'method':method,'path':path,'expected':expected,'observed':x.status_code,'body':body,'authorization_present':'Authorization' in headers,'identity_header_present':'X-User-Id' in headers});save();print(label,x.status_code,flush=True)
 assert x.status_code==expected, f'{label}: expected {expected}, observed {x.status_code}'
 return body
try:
 assert os.environ['CODEXIFY_IDENTITY_DIR']=='/app/data/identity'
 runtime_identity=identity.get_or_create_user()
 receipt['runtime_identity']={'directory':identity.IDENTITY_DIR,'explicit_override':True,'user_id':runtime_identity['user_id'],'created_at':runtime_identity['created_at'],'key_version':runtime_identity['key_version'],'public_key_sha256':hashlib.sha256(runtime_identity['public_key'].encode()).hexdigest()}
 profile=get_active_supported_profile(); settings=get_settings(); receipt['posture']={'profile':profile.name,'auth_route':profile.route_status('auth'),'auth_mode':_auth_mode(),'multi_user_enabled':settings.CODEXIFY_MULTI_USER_ENABLED,'debug':os.getenv('DEBUG'),'local_dev':os.getenv('LOCAL_DEV'),'session_secret_sha256':hashlib.sha256(os.environ['GUARDIAN_SESSION_SECRET'].encode()).hexdigest()}
 assert profile.name=='v1-local-core-web-mcp' and profile.route_status('auth')=='quarantined' and _auth_mode()=='local' and not settings.CODEXIFY_MULTI_USER_ENABLED
 with db.get_session() as s:
  assert not s.scalars(select(User).where(User.id.in_(list(accounts.values())))).all()
  receipt['baseline_users']=[u.id for u in s.scalars(select(User)).all()]
  for ident in accounts.values():s.add(User(id=ident,username=ident,password_hash=hash_password(secrets.token_urlsafe(32)),role='guest',created_at=datetime.now(timezone.utc)))
  s.commit()
 for actor,ident in accounts.items():
  token,expires=issue_session_token(subject=ident,ttl_seconds=900,purpose=ACCOUNT_SESSION_PURPOSE); tokens[actor]=token;store.store(token,ident,900)
  valid,subject=verify_session_token(token)
  checks={'id':ident,'purpose':ACCOUNT_SESSION_PURPOSE,'expires_at':expires,'signature_valid':valid,'purpose_valid':verify_session_token_for_purpose(token,ACCOUNT_SESSION_PURPOSE),'operator_purpose_valid':verify_session_token_for_purpose(token,OPERATOR_SESSION_PURPOSE),'signed_subject_matches':subject==ident,'stored_subject_matches':store.verify(token)==ident,'canonical_resolver_matches':resolve_account_session_subject(token)==ident}
  assert all(checks[k] for k in ['signature_valid','purpose_valid','signed_subject_matches','stored_subject_matches','canonical_resolver_matches']) and not checks['operator_purpose_valid']; receipt['accounts'].append(checks)
 assert accounts['a']!=accounts['b'] and tokens['a']!=tokens['b'];save()
 fixture=b'SYNTHETIC SESSION FIXTURE\n'; declaration={'total_file_count':1,'total_byte_count':len(fixture)}
 for actor in ['a','b']:
  body=probe(actor+'_create',actor,'POST','/api/imports/openai-account',200,json=declaration);jobs[actor]=body['job_id']
  probe(actor+'_read_own',actor,'GET','/api/imports/openai-account/'+jobs[actor],200)
  with db.get_session() as s:
   job=s.get(OpenAIAccountImportJob,jobs[actor]);assert job.user_id==accounts[actor] and job.status=='receiving';receipt['ownership'].append({'job_id':job.id,'user_id':job.user_id,'status':job.status,'uploaded_file_count':job.uploaded_file_count,'uploaded_byte_count':job.uploaded_byte_count});locators.append(job.staging_locator)
  save()
 target='/api/imports/openai-account/'+jobs['a']
 probe('b_read_a','b','GET',target,404)
 probe('b_stage_a','b','POST',target+'/files',404,files=[('files',('fixture.txt',fixture,'text/plain'))],data=[('relative_paths','fixture.txt')])
 probe('b_commit_a','b','POST',target+'/commit',404)
 probe('a_read_b','a','GET','/api/imports/openai-account/'+jobs['b'],404)
 probe('a_claim_b_header','a','GET',target,200,headers_extra={'X-User-Id':accounts['b']})
 probe('b_claim_a_header','b','GET',target,404,headers_extra={'X-User-Id':accounts['a']})
 probe('missing_credentials',None,'GET',target,401)
 probe('missing_claim_a',None,'GET',target,401,headers_extra={'X-User-Id':accounts['a']})
 token=tokens['a'];tampered=token[:-1]+('A' if token[-1]!='A' else 'B')
 probe('tampered_account_a',None,'GET',target,401,credential=tampered)
 probe('invalid_claim_a',None,'GET',target,401,credential='invalid-session',headers_extra={'X-User-Id':accounts['a']})
 unbound,_=issue_session_token(subject=accounts['a'],ttl_seconds=900,purpose=ACCOUNT_SESSION_PURPOSE);extra_tokens.append(unbound)
 probe('signed_unregistered',None,'GET',target,401,credential=unbound)
 operator,_=issue_session_token(subject=accounts['a'],ttl_seconds=900,purpose=OPERATOR_SESSION_PURPOSE);extra_tokens.append(operator)
 assert not verify_session_token_for_purpose(operator,ACCOUNT_SESSION_PURPOSE)
 probe('operator_without_account_binding',None,'GET',target,401,credential=operator)
 probe('static_service_key',None,'GET',target,404,headers_extra={'X-API-Key':os.environ['GUARDIAN_API_KEY']})
 probe('service_key_claim_a',None,'GET',target,404,headers_extra={'X-API-Key':os.environ['GUARDIAN_API_KEY'],'X-User-Id':accounts['a']})
 probe('a_stage_own','a','POST',target+'/files',200,files=[('files',('fixture.txt',fixture,'text/plain'))],data=[('relative_paths','fixture.txt')])
 with db.get_session() as s:
  receipt['durable_jobs']=[{'id':j.id,'user_id':j.user_id,'status':j.status,'uploaded_file_count':j.uploaded_file_count,'uploaded_byte_count':j.uploaded_byte_count,'imported_thread_count':j.imported_thread_count,'imported_message_count':j.imported_message_count} for j in s.scalars(select(OpenAIAccountImportJob).where(OpenAIAccountImportJob.id.in_(list(jobs.values())))).all()]
  assert len(receipt['durable_jobs'])==2 and all(j['status']=='receiving' and not j['imported_message_count'] for j in receipt['durable_jobs'])
  assert s.get(OpenAIAccountImportJob,jobs['a']).uploaded_file_count==1 and s.get(OpenAIAccountImportJob,jobs['b']).uploaded_file_count==0
 for path in ['/api/auth/register','/auth/register','/api/auth/login','/auth/login']:
  probe('quarantined_'+path,None,'POST',path,404,json={'username':'synthetic-quarantine-probe','password':'synthetic-unused-password'})
 for actor in ['a','b']:
  store.revoke(tokens[actor]);assert store.verify(tokens[actor]) is None;receipt['revocation'].append({'account':accounts[actor],'store_binding_absent':True})
  probe(actor+'_revoked_own',actor,'GET','/api/imports/openai-account/'+jobs[actor],401)
 receipt['status']='PASS'
except Exception as exc:
 receipt['status']='FAIL';receipt['failure']={'class':type(exc).__name__,'message':str(exc)}
 print('qualification_boundary',type(exc).__name__,str(exc),flush=True)
finally:
 for token in list(tokens.values())+extra_tokens:store.revoke(token)
 with db.get_session() as s:
  s.execute(delete(OpenAIAccountImportJob).where(OpenAIAccountImportJob.id.in_(list(jobs.values()))));s.execute(delete(User).where(User.id.in_(list(accounts.values()))));s.commit()
  receipt['cleanup']={'synthetic_users_remaining':s.scalar(select(func.count()).select_from(User).where(User.id.in_(list(accounts.values())))),'synthetic_jobs_remaining':s.scalar(select(func.count()).select_from(OpenAIAccountImportJob).where(OpenAIAccountImportJob.id.in_(list(jobs.values())))),'remaining_users':[u.id for u in s.scalars(select(User)).all()]}
 for locator in locators:
  target=Path('/app/data/imports')/locator
  if target.is_dir():shutil.rmtree(target)
 save()
print('qualification',receipt['status'],flush=True)
raise SystemExit(0 if receipt['status']=='PASS' else 1)
```

## Sanitized evidence identifiers

The temporary receipts were inspected before cleanup. Their hashes identify the
measured evidence; standalone files are intentionally not retained. The API,
SQL, posture and credential-free driver excerpts in this document are durable.

| Evidence | SHA-256 |
| --- | --- |
| `qualify_sessions.py` | `ee39733c5e0c709aae71fdc62600b538acbebb8ae345154c0b78c88eb1e7a28f` |
| `receipt.json` | `b35800cd7e004a38619100ca1d01d6dfa028b30ae8e0cb52eec6d9d91972f23e` |
| `source-hashes.json` | `9270285a7beedcaaeb9ef91b0eb9f6c0893a6b42a3c036ad1bab8614c81cb8ce` |
| `runtime-metadata.json` | `b97d46ebefb3833d92c0694c3afdd05627f42421315d3d2d4d501f654c02940d` |
| `cleanup-receipt.json` | `9f6fcbb016db3f3d5f56778e9aae824553c15ccddbaceb6d273cdd3f17be3b74` |
| `auth-boundary-tests.log` | `e8cfed9d3cc774fabfb3903581955c17a9c050549338d8996ebf7ee4c642000d` |
| `multi-user-tests.log` | `2a02b38bf780f07030ba7a87a81657c2b9fe660dd362ae5c1586605f45b16f1c` |

Authority/profile file equality, source and running container:

| File | Matching SHA-256 |
| --- | --- |
| `guardian/core/auth.py` | `6df7eebe2001e1d787fd3a51ba07622c9e51a203568ae4e5ebd6afe48764ff20` |
| `guardian/core/auth_dependencies.py` | `553389a3af018b20cc4f6dc1645ec0568ea01d5161c857a7d58aa65b20f6b639` |
| `guardian/core/dependencies.py` | `a35e5cca4000944789dbb0a8cf511b30be4643979db9aee9081854c2d8784844` |
| `guardian/core/session_store.py` | `bdd93046769ba150933019ae7ea2e66032bcccfe02fa9c27b9764f5aca33fde3` |
| `guardian/core/user_manager.py` | `abb932c753b57b8e16d9c9201f95225800dafa2e6c4ea9390d96318d28d71b56` |
| `guardian/db/models.py` | `0545d32e2b4764e2c57611fd12468e855bb055477823cbff3040316b405f89ac` |
| `guardian/routes/migration.py` | `a5110ee6e2a2eba2e6cf84a186072d6e6e1e31ad3ede81407f75d62f5e649229` |
| `config/supported_profiles/v1-local-core-web-mcp.yaml` | `40a48315e11f190bd0972b874e5c8bd52027022130e53b99fe0a07fee9fb03f8` |

## Remaining work and documentation follow-through

No Goal 04 acceptance prerequisite remains blocked. Sessions were revoked and
resources removed; a subsequent authorized R5 run must recreate this trusted
fixture, not reuse expired credentials. The next task can proceed to synthetic
import, canonical messages/provenance/replay, embedding readiness, executed
retrieval, provider-context inclusion, persisted answer and unrelated-account
exclusion. None of those gates is passed by this session-only qualification.

No application correction, new ADR, KB addition or runbook correction was
necessary. Documentation follow-through is this artifact only. Current-state,
release HOLD, Preview admission and the earlier R5 stopped-run receipt are
preserved. Final checks are `git diff --check`, exact scoped status/diff,
`git diff --cached --check`, and staged name-status; only this file is committed
with `test: qualify isolated account sessions for import proof`. An initial staged `git diff --cached --check` found trailing spaces in the
quoted psql column padding; that excerpt was trimmed, and the staged check
was rerun successfully. No push, merge, deploy or amend is authorized or performed.
