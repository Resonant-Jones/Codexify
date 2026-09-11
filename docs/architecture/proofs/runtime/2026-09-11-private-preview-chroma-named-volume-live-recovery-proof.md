# Private Preview Chroma Named-Volume Live Recovery Proof

Date: 2026-09-11

Execution lane: architecture-impact

Mode: EXECUTE

Result: PASS

Reason: `private_preview_adr067_named_volume_chroma_live_recovery_qualified`

## Scope and authority

This proof records the bounded ADR-067 recovery sequence from the obsolete
host-bound Private Preview Chroma store to a fresh operator-owned external
Docker volume. PostgreSQL remained canonical application authority. Chroma
remained derived retrieval state.

The authorized runtime surface was the Private Preview backend and only its
required Compose dependencies. No chat worker, embedding worker, optional
ingestion/backfill service, frontend, origin, provider request, chat completion,
historical Chroma restore, manual Chroma migration, or schema surgery was
authorized or performed.

`ADR_IMPACT=ALIGNED_WITH_ADR_067`

## Repository and Docker boundary

- `START_HEAD=e05b5919b7677b45f87ca4c1ca1b2129e73e31e9`
- `ORIGIN_MAIN=cb551de1866715ef421026203ffe2a87cec8aaca`
- `INITIAL_STAGED_PATCH_SHA256=4e96d8c7155e327f03f15d311ddfbf03c32dc2d86129e184b4f7a6bb29b7560e`
- `DOCKER_CONTEXT=desktop-linux`
- `DOCKER_SERVER_VERSION=29.7.2`
- `DOCKER_SERVER_OS_ARCH=linux/arm64`
- `PRIVATE_PREVIEW_COMPOSE_PROJECT=codexify_private_preview`
- `PREEXISTING_NAMED_VOLUME_PRESENT=false`

The selected Docker context contained the previously recovered Private Preview
database as `codexify_private_preview-db-1`, running healthy. The context was not
changed.

Before any storage mutation, every defined Private Preview Chroma consumer was
stopped and the periodic reconciliation LaunchAgent was absent/unloaded with no
reconciliation process running:

- `ACTIVE_CHROMA_WRITER_COUNT=0`
- `PRIVATE_PREVIEW_WRITERS_QUIESCED=true`
- `PRIVATE_PREVIEW_RECONCILIATION_SUSPENDED=true`

## Canonical database and backup preflight

The retained post-migration database backup was inspected but not restored:

- path: `/Volumes/Dev_SSD/Codexify-preservation/live-canonical-alembic-20260911T194943Z/post-migration.dump`
- size: `3361105` bytes
- SHA-256: `bef8bcaa92ec2386efcd2106151ba9793e51d18da09769e22505a2326c09e7f9`
- mode: `0400`

Live PostgreSQL preflight returned:

- `LIVE_ALEMBIC_REVISION=7e5a5fccf253`
- `LIVE_THREAD_COUNT=72`
- `LIVE_MESSAGE_COUNT=805`
- `LIVE_GENERAL_PROJECT_IDS=6,7,8,9,10`
- `LIVE_PROJECT_1_PRESENT=false`
- `LIVE_RETIRED_PROFILE_1_PRESENT=false`
- `LIVE_RETIRED_PROFILE_2_PRESENT=false`
- `LIVE_RETIRED_PROFILE_3_PRESENT=false`
- `PROJECT_1_REPAIRED_THREAD_COUNT=8`
- `PROJECT_1_AFFECTED_MESSAGE_COUNT=20`

## Host-store identity and preservation

The exact obsolete active store was resolved without wildcard discovery:

- `OLD_CHROMA_PATH=/Volumes/Dev_SSD/Codexify-main/.chroma`
- `OLD_CHROMA_PATH_EXISTS=true`
- `OLD_CHROMA_PATH_IS_DIRECTORY=true`
- `OLD_CHROMA_PATH_IS_SYMLINK=false`
- resolved path: `/Volumes/Dev_SSD/Codexify-main/.chroma`
- device: `16777250`
- inode: `6477533`
- `OLD_CHROMA_FILE_COUNT=6`
- `OLD_CHROMA_SIZE_BYTES=75495910`
- `OLD_CHROMA_TREE_SHA256=23d6a47a7fc438f781cc1dedb64b9f63c8a693d0f85be2ed780a620bf335322c`

The tree digest is the SHA-256 of a deterministic manifest containing relative
path, object type, byte size, and per-file SHA-256. The source was rehashed after
copy and before retirement.

The earlier immutable preservation was reverified without opening it through
Chroma:

- `PRIOR_HISTORICAL_PRESERVATION_PATH=/Volumes/Dev_SSD/Codexify-preservation/chroma/persona-20260906T230016Z/canonical-chroma`
- `PRIOR_HISTORICAL_PRESERVATION_SHA256=c12d9eecacf005c983fe1d2e917f7526cd5e8c0372845d3127329930bd69b19c`
- file count: `5`
- size: `458916` bytes
- symlink count: `0`
- writable entry count: `0`
- `PRIOR_HISTORICAL_PRESERVATION_VALID=true`

That historical artifact was not byte-equivalent to the active store, so a new
retirement-time preservation was required and created:

- `RETIREMENT_PRESERVATION_CREATED=true`
- `RETIREMENT_PRESERVATION_PATH=/Volumes/Dev_SSD/Codexify-preservation/chroma/adr067-recovery-20260911T233236Z/retired-host-chroma`
- source manifest: `/Volumes/Dev_SSD/Codexify-preservation/chroma/adr067-recovery-20260911T233236Z/source-manifest.tsv`
- preservation manifest: `/Volumes/Dev_SSD/Codexify-preservation/chroma/adr067-recovery-20260911T233236Z/preservation-manifest.tsv`
- `RETIREMENT_PRESERVATION_FILE_COUNT=6`
- `RETIREMENT_PRESERVATION_SIZE_BYTES=75495910`
- `RETIREMENT_PRESERVATION_TREE_SHA256=23d6a47a7fc438f781cc1dedb64b9f63c8a693d0f85be2ed780a620bf335322c`
- writable entry count after retention hardening: `0`
- `RETIREMENT_PRESERVATION_MATCH=true`

## Effective topology and retirement

Bounded extraction from the fully merged base and Private Preview Compose model
proved six Chroma consumers. Each resolved to:

```text
type=volume
source=private_preview_chroma
target=/app/.chroma
volume.nocopy=true
VECTOR_STORE=chroma
CHROMA_PATH=/app/.chroma
CHROMA_COLLECTION=codexify_vault_supported
```

- `PRIVATE_PREVIEW_CHROMA_CONSUMER_COUNT=6`
- `PRIVATE_PREVIEW_CHROMA_NOCOPY_CONSUMER_COUNT=6`
- `EFFECTIVE_PRIVATE_PREVIEW_HOST_CHROMA_BIND_COUNT=0`

Three stopped application containers retained stale host-bind definitions. They
were removed through the project-scoped Compose lifecycle. No database volume or
unrelated service container was removed.

- stale host-bind containers before cleanup: `3`
- `STALE_HOST_BIND_CONTAINER_COUNT=0`

After the source was rehashed and matched to the retained preservation, exactly
`/Volumes/Dev_SSD/Codexify-main/.chroma` was removed.

- `ACTIVE_HOST_CHROMA_PATH_PRESENT=false`
- `ACTIVE_CHROMA_INDEX_RETIRED=true`
- `HISTORICAL_CHROMA_PRESERVATION_RETAINED=true`

## External named volume

The operator created exactly one volume with:

```text
docker volume create --driver local codexify_private_preview_chroma
```

Immediate inspection returned:

- `VOLUME_NAME=codexify_private_preview_chroma`
- `VOLUME_DRIVER=local`
- `VOLUME_SCOPE=local`
- `VOLUME_DRIVER_OPTS_EMPTY=true`
- `VOLUME_CREATED_AT=2026-09-11T23:39:43Z`
- `VOLUME_DOCKER_CONTEXT=desktop-linux`
- `FRESH_VOLUME_PREINIT_FILE_COUNT=0`
- pre-initialization directory count: `0`
- `PREINIT_VOLUME_ATTACHED_CONTAINER_COUNT=0`

## Supported-runtime initialization

- `BACKEND_SOURCE_HEAD=e05b5919b7677b45f87ca4c1ca1b2129e73e31e9`
- `BACKEND_IMAGE_ID=sha256:b73f779e8e026cf0b17ef8f6aa1262e543579d2e7c092c91e9690a30397e7a7d`
- image tag: `codexify-backend-runtime:latest`
- image platform: `linux/arm64`
- `SUPPORTED_CHROMA_RUNTIME_VERSION=1.0.15`
- `SUPPORTED_CHROMA_RUNTIME_VERSION_MATCH=true`

The package version was read directly from the backend image without network
access. The bounded startup command was:

```text
docker compose --project-directory /Volumes/Dev_SSD/Codexify-main --env-file /Volumes/Dev_SSD/Codexify-main/.env.private-preview -p codexify_private_preview -f /Volumes/Dev_SSD/Codexify-main/docker-compose.yml -f /Volumes/Dev_SSD/Codexify-main/docker-compose.private-preview.yml up -d --no-build backend
```

Only `backend` was explicitly started. Its required one-shot model preparation,
graph initialization, and migrator dependencies completed successfully; no
worker, frontend, origin, ingestion, backfill, provider, or chat-completion
surface was started.

- `STARTUP_MIGRATOR_EXIT=0`
- `STARTUP_MIGRATOR_FINAL_REVISION=7e5a5fccf253`
- `BACKEND_CHROMA_MOUNT_TYPE=volume`
- `BACKEND_CHROMA_MOUNT_NAME=codexify_private_preview_chroma`
- `BACKEND_CHROMA_MOUNT_TARGET=/app/.chroma`
- `BACKEND_HOST_CHROMA_BIND_COUNT=0`

The volume was empty before startup, the stock backend was its sole writer, and
no historical content was copied. Therefore:

- `FRESH_CHROMA_INITIALIZED=true`
- `FRESH_CHROMA_SQLITE_PRESENT=true`
- `FRESH_CHROMA_SQLITE_INTEGRITY=ok`
- SQLite table count: `20`
- `HISTORICAL_CHROMA_BYTES_IMPORTED=false`

The final read-only manifest, collected after the backend was stopped, was:

| Relative path | Type | Bytes | SHA-256 |
| --- | --- | ---: | --- |
| `chroma.sqlite3` | file | 212992 | `c1c44e07db3ee25243c41cd3cb641fd6f5a435fc136394f1c8463d81bd9977d2` |
| `e90076a7-498e-480d-971e-ad4779f25f9a/` | directory | - | - |
| `e90076a7-498e-480d-971e-ad4779f25f9a/data_level0.bin` | file | 42360000 | `2679902f7ee9902bd54e85a1e4b822cccb4a163c0d49ae93b57d42d40edf49d0` |
| `e90076a7-498e-480d-971e-ad4779f25f9a/header.bin` | file | 100 | `f14d42069445548e1fceb9acb767255a21e1e9d11c021b2d5999d5cbf4d2b705` |
| `e90076a7-498e-480d-971e-ad4779f25f9a/length.bin` | file | 40000 | `e7e2dcff542de95352682dc186432e98f0188084896773f1973276b0577d5305` |
| `e90076a7-498e-480d-971e-ad4779f25f9a/link_lists.bin` | file | 0 | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |

Final bounded store totals were five files and `42613092` bytes.

## Panic search, health, and one reopen

Bounded startup and post-restart logs contained no historical or equivalent
fatal Chroma/SQLite startup signature:

- `HISTORICAL_CHROMA_PANIC_COUNT=0`
- `SQLITE_READONLY_DBMOVED_COUNT=0`
- `BACKEND_CHROMA_STARTUP_FATAL_COUNT=0`

The first backend opening reached healthy state. In-container observations were:

- `BACKEND_HEALTH_HTTP_STATUS=200`
- `/health` state: `ok`
- release hold: `true`
- `CHAT_HEALTH_HTTP_STATUS=200`
- `CHAT_HEALTH_STATE=unhealthy (worker_heartbeat_missing)`
- `CHAT_HEALTH_ENDPOINT_OBSERVED=true`
- chat queue depth: `0`
- provider attempted/completed/executed: `false/false/false`

The degraded chat-health result is the expected worker-absent boundary and is
not worker safe-start proof.

The backend was restarted exactly once through the same Compose project. It
reopened the same external volume, reached healthy state again, retained the
same image and mount identity, and reproduced none of the panic signatures.

- `BACKEND_RESTART_EXIT=0`
- `BACKEND_POST_RESTART_HEALTH_HTTP_STATUS=200`
- post-restart `/health` state: `ok`

## Final PostgreSQL and maintenance boundary

After the reopen, live PostgreSQL readback remained:

- `LIVE_ALEMBIC_REVISION=7e5a5fccf253`
- `LIVE_THREAD_COUNT=72`
- `LIVE_MESSAGE_COUNT=805`
- `LIVE_GENERAL_PROJECT_IDS=6,7,8,9,10`
- `LIVE_PROJECT_1_PRESENT=false`
- `LIVE_RETIRED_PROFILE_1_PRESENT=false`
- `LIVE_RETIRED_PROFILE_2_PRESENT=false`
- `LIVE_RETIRED_PROFILE_3_PRESENT=false`
- `PROJECT_1_REPAIRED_THREAD_COUNT=8`
- `PROJECT_1_AFFECTED_MESSAGE_COUNT=20`
- `LIVE_PROJECT_FK_CENSUS_COUNT=17`
- `LIVE_PROJECT_FK_ORPHAN_COUNT=0`

No provider-backed invocation or user-content mutation occurred:

- `PROVIDER_BACKED_INVOCATION_COUNT=0`

The backend was then stopped through the same Compose project and exited zero.
The intentionally recovered external volume remains retained. Only the
database, Redis, and Neo4j services that were already running before this task
remain running.

- `PRIVATE_PREVIEW_APPLICATION_WRITERS_RUNNING=false`
- `PRIVATE_PREVIEW_WRITERS_QUIESCED=true`
- `PRIVATE_PREVIEW_RECONCILIATION_SUSPENDED=true`
- `PRIVATE_PREVIEW_NAMED_VOLUME_CREATED=true`
- `PRIVATE_PREVIEW_CHROMA_TOPOLOGY_IMPLEMENTED=true`
- `PRIVATE_PREVIEW_CHROMA_RUNTIME_QUALIFIED=true`

## Proof boundary

This proof qualifies only the ADR-067 physical storage cutover, fresh supported
Chroma initialization, one backend reopen, bounded backend health observation,
and canonical PostgreSQL preservation. It does not qualify multiprocess access,
queue/worker startup, authenticated application behavior, provider execution,
or release readiness.

- `QUEUE_WORKER_SAFE_START_PROVEN=false`
- `MULTIPROCESS_CHROMA_CONCURRENCY_PROVEN=false`
- `AUTHENTICATED_PERSONA_ROUTE_PROVEN=false`
- `AUTHENTICATED_BROWSER_SAVE_READBACK_PROVEN=false`
- `PERIODIC_RECONCILIATION_RESTORED=false`
- `PROVIDER_BACKED_CHAT_COMPLETION_PROVEN=false`
- `APPLICATION_RUNTIME_RECOVERY_PROVEN=false`
- `PRIVATE_PREVIEW_RELEASE_READY=false`
- `RUNTIME_TOPOLOGY_CHANGED=false`

## Validation

- `.venv/bin/python -m pytest -v tests/ops/test_private_preview_contract.py`: PASS, `16 passed`
- `python3 scripts/validate_docs.py`: PASS
- `.venv/bin/python scripts/validate_docs.py`: PASS
- `python3 scripts/check_diagram_freshness.py`: PASS
- `git diff --check`: PASS
- `git diff --cached --check`: PASS
- `PRIVATE_PREVIEW_CONTRACT_TESTS=PASS`
- `DOCS_VALIDATION=PASS`
- `DIAGRAM_FRESHNESS_REVIEW=PASS`
- `DIFF_CHECK=PASS`
