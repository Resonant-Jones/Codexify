# Canonical Tester backend startup attempt

## Result

**`CANONICAL_BACKEND_STARTUP_PASS`**

One and only one canonical Tester `backend` startup was performed. The backend
remained running and Docker health became `healthy`; the one permitted
non-model `GET /health` returned `status: "ok"`. No repair, retry, worker-chat
start, chat request, provider completion, DeepSeek completion, or Watchdog
operation was performed.

This is live startup/health evidence only. It does not prove worker operation,
chat completion, persistence completion, retrieval quality, or release
readiness.

## Scope, source, and authority

- **Source HEAD before the runtime attempt:**
  `0644077fd3b6916cd41da8b3276a594b580305f7`
  (`Add backend startup failure receipt`).
- **Branch:** `codex/diagnose-tester-fresh-chroma-failure`.
- **Prerequisites in ancestry:** `0644077fd3b6916cd41da8b3276a594b580305f7`
  and `3fe63b4232f12fb305a50ac789311341d6587a9a`.
- **Compose project:** `codexify_tester`.
- **Backend image:** `codexify-backend-runtime:latest`, image ID
  `sha256:af108ff65ba1d1fde1417ac776be41eacd106aaf77d2800b7c6e40d2359b6288`
  (`linux/arm64`).
- **Provider posture, inspected read-only:** `LLM_PROVIDER=local`,
  `LOCAL_CHAT_MODEL=gemma-4-12b-it-qat-4bit`,
  `ALLOW_CLOUD_PROVIDERS=true`, and `CODEXIFY_LOCAL_ONLY_MODE=false`.

`.env.tester` remained ignored and unchanged. The canonical configuration
render completed successfully. It emitted only warnings that optional
`LOCAL_VISION_MODEL` and `LOCAL_GGUF_MODEL` values were unset; no Compose file
or runtime configuration was changed.

## Canonical state before the attempt

The backend container was present but exited from the preceding failure:

| Property | Value |
| --- | --- |
| Container | `codexify_tester-backend-1` (`f77a9d7e0ca2…`) |
| Service / project | `backend` / `codexify_tester` |
| State / prior exit | `exited` / `3` |
| Existing worker-chat container | absent |
| Canonical Chroma host path | `/Users/chriscastillo/.codex/worktrees/5ab6/Codexify-main/.chroma` |
| Canonical Chroma container path | `/app/.chroma` (read-write mount) |

No backend was already healthy, so the authorized attempt was necessary.

The canonical partial Chroma state was not opened through Chroma or altered
manually. Its pre-attempt structural fingerprint was:

| Property | Value |
| --- | --- |
| Files | `1` (`chroma.sqlite3`) |
| Aggregate bytes | `16,384` |
| `chroma.sqlite3` SHA-256 | `163ed995f24a76a53571f16c9f1e835271264a11136a25f5df854316ce14c58f` |
| Deterministic file-manifest SHA-256 | `e3c08c0fc8c57fff5dabefbde312d6d21ffcf526a4f3d54a664b09eb1f14fe71` |

Both preservation generations were confirmed present and read-only before the
start:

- historical incompatible state:
  `/Volumes/Dev_SSD/Codexify-preservation/chroma/20260824T182108Z-9f263fa2fdb9/canonical-chroma`;
- fresh-partial evidence:
  `/Volumes/Dev_SSD/Codexify-preservation/chroma/20260824T185433Z-3fe63b42/fresh-partial-after-failed-init`.

The fresh-partial preservation retained the pre-attempt SQLite SHA-256 above.
Neither preservation was mounted, opened through Chroma, restored, or changed.

## One canonical startup attempt

`CANONICAL_BACKEND_START_ATTEMPTS=1`

The normal Tester Compose operation targeted only the `backend` service and
its declared dependencies:

```text
docker compose -p codexify_tester --env-file .env.tester \
  -f docker-compose.yml -f docker-compose.tester.yml \
  -f docker-compose.whooshd-deepseek.yml up -d backend
```

It started the required database, graph, migrator, and model-preparation
dependencies before the canonical backend. It did not target or start
`worker-chat`, a Watchdog worker, or an alternate diagnostic command.

After the attempt, Docker reported:

| Property | Value |
| --- | --- |
| Backend state | `running` |
| Docker health | `healthy` |
| Exit code | not applicable (backend remained running) |
| Restart count | `0` |
| Startup-failure receipt count | `0` |

Bounded backend-log inspection found no
`CODEXIFY_STARTUP_FAILURE_RECEIPT` prefix and no
`backend_startup_failure` event. Raw log capture was mode-restricted and
removed after the zero-count check.

## Bounded health proof

One canonical, non-model request was sent after Docker health became healthy:

```text
GET http://127.0.0.1:8889/health
```

It succeeded with:

```json
{"status":"ok","supported_profile":{"name":"v1-whooshd-deepseek-web","valid":true,"release_hold":true}}
```

No other HTTP request was sent. In particular, there was no chat completion,
provider/Whoosh'd/DeepSeek invocation, or Watchdog activity. Normal local
startup materialized derived Chroma state, but no user-facing or explicit
model request was initiated in this task.

## Post-attempt derived Chroma state

The startup completed its normal derived-store initialization. This is a
runtime side effect of the one authorized canonical start, not an operator
repair or manual mutation.

| Property | Pre-attempt | Post-attempt |
| --- | ---: | ---: |
| Files | `1` | `5` |
| Aggregate bytes | `16,384` | `42,588,516` |
| SQLite size | `16,384` | `188,416` |
| SQLite SHA-256 | `163ed995f24a…` | `602eca12546c…` |
| Manifest SHA-256 | `e3c08c0fc8c…` | `e777982dc4da…` |

The additional bounded structural files were one generated Chroma index
directory with `data_level0.bin` (`42,360,000` bytes), `length.bin` (`40,000`
bytes), `header.bin` (`100` bytes), and an empty `link_lists.bin`. No document,
embedding, metadata, or user content was read or recorded. Both external
preservations remained read-only and retained their prior state.

## State safety and ADR impact

- No source, test, Compose, dependency, migration, configuration, or
  preservation file changed.
- No manual Postgres reset/write, Redis clear, Chroma reset, deletion,
  restoration, or repair occurred. Normal backend initialization was allowed
  to perform its ordinary runtime work.
- `worker-chat` remained absent; no worker, inference, or Watchdog path was
  started by this task.
- **No ADR impact — live evidence only; ADR-067 and ADR-074 remain preserved.**

## Validation

- prerequisite ancestry and `.env.tester` ignore/posture checks passed;
- canonical Tester Compose configuration rendered successfully (with only the
  optional unset-model warnings above);
- the backend process remained `running` and `healthy` after the one start;
- the single `/health` request succeeded;
- preservation and pre/post Chroma structural fingerprints were checked;
- documentation validation and Git diff checks are recorded at commit
  closeout.

## Deferred next slice

Start and prove the normal Tester chat worker against the healthy backend,
Redis, and reconciled local/Gemma posture without performing model inference.
