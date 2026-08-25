# GitHub Watchdog worker runtime qualification — BLOCKED

## Receipt

- **Observed at:** `2026-08-24T14:00:53Z`
- **Branch / source commit:** `codex/define-github-watchdog-control-plane` / `c0cef2be3c6c9c72883e490274d7d78cb6c73a51`
- **Prerequisite ancestry:** `c0cef2be3c6c9c72883e490274d7d78cb6c73a51` and `79a5df7bd11f0430a3da95805616d120cce334d3` both exist and are ancestors of the source commit.
- **Compose project:** `codexify-watchdog-proof-20260824` (isolated from an unrelated stack that already owned host port `5433`; its proof database was published only on `127.0.0.1:55433`).
- **Migration head:** repository and running proof database both report `6e9f0a1b2c3`.
- **Worker:** `worker-watchdog-review`, container `e44503b4a7673aacf9b4416e40fc168e7db7b909656bda4f9f6ab94034ead621`, running from the rebuilt local runtime image.
- **Queue:** `github_watchdog_review`.
- **Result:** **BLOCKED**.

## Runtime observations

The actual opt-in Compose worker reached its normal queue-consumption loop. Its
bounded logs included `[watchdog-review-worker] started`; Postgres and Redis
were healthy, and the worker was running after the current Alembic migration
completed.

The runtime database initially stopped at `1c0a2b3c4d5e` because the Watchdog
migrator used an older baked image and had no Compose build declaration. This
was a direct Watchdog Compose defect, not a schema shortcut: adding
`build: *backend_runtime_build` to `migrator`, rebuilding the local runtime
image, and rerunning the normal migration service advanced the same isolated
database legitimately to `6e9f0a1b2c3`. No table was created manually, no
migration was stamped, and no volume was reset.

## First unrepaired blocker

The worker's effective Watchdog policy binding is unconfigured:

| Field | Effective value |
| --- | --- |
| Watchdog provider | unset |
| Watchdog model | unset |
| Watchdog inference mode | unset |
| Ambient provider | `local` |
| Ambient local model | `mlx-community/Llama-3.2-3B-Instruct-4bit` |
| Local-only / cloud allowed | `true` / `false` |

The ambient local chat model is deliberately not substituted for the required
immutable Watchdog provider/model policy. `config-and-ops.md` already defines
this fail-closed posture: empty Watchdog provider or model configuration must
produce `blocked_policy` and must not inherit the ambient chat provider.
Changing those operator settings solely to manufacture a PASS is outside this
qualification's authority.

Consequently, the proof stopped before creating a qualification receipt,
attempt, snapshot, dispatch, Redis envelope, or result. There is no selected
Watchdog model, no valid immutable policy snapshot, and therefore no legitimate
call to `GitHubWatchdogReviewDispatchService`. This preserves the one-model,
no-substitution, no-fallback, and no-escalation invariants.

## Identity and transition evidence

No qualification lineage was created because the authoritative model selection
precondition was absent:

| Item | Value |
| --- | --- |
| Receipt ID | not created |
| Review attempt ID | not created |
| Snapshot ID / SHA-256 | not created |
| Dispatch ID / queue task ID | not created |
| Result ID | not created |
| Provider / model / mode | not selected |
| Prompt / raw-output digest / bytes | not created |
| Structured assessment / usage | not created |

Observed service transition only: `migrator completed` →
`worker-watchdog-review started and entered normal queue loop`. No Redis
Watchdog envelope was enqueued, so no dispatch or model-execution transition is
claimed. The worker was not used to read or write GitHub, invoke Command Bus,
start a Build Loop or coding worker, or publish a review.

## Validation

Passed before the blocker:

```text
git cat-file -e c0cef2be3c6c9c72883e490274d7d78cb6c73a51^{commit}
git merge-base --is-ancestor c0cef2be3c6c9c72883e490274d7d78cb6c73a51 HEAD
git cat-file -e 79a5df7bd11f0430a3da95805616d120cce334d3^{commit}
git merge-base --is-ancestor 79a5df7bd11f0430a3da95805616d120cce334d3 HEAD
docker compose config >/dev/null
docker compose --profile watchdog config >/dev/null
.venv/bin/python -m alembic -c backend/alembic.ini heads
docker compose -p codexify-watchdog-proof-20260824 -f docker-compose.yml -f /private/tmp/codexify-watchdog-runtime-proof-ports.yml --profile watchdog up -d worker-watchdog-review
docker compose -p codexify-watchdog-proof-20260824 -f docker-compose.yml -f /private/tmp/codexify-watchdog-runtime-proof-ports.yml --profile watchdog ps -a
docker compose -p codexify-watchdog-proof-20260824 -f docker-compose.yml -f /private/tmp/codexify-watchdog-runtime-proof-ports.yml logs --no-color --tail=40 worker-watchdog-review
docker compose -p codexify-watchdog-proof-20260824 -f docker-compose.yml -f /private/tmp/codexify-watchdog-runtime-proof-ports.yml exec -T db psql -U codexify -d Codexify -Atc "SELECT version_num FROM alembic_version"
.venv/bin/python -m pytest -q tests/watchdog/test_review_attempt_policy.py tests/watchdog/test_review_dispatch.py tests/watchdog/test_review_worker.py
python3 scripts/validate_docs.py
git diff --check
```

The isolated project's normal migrator completed successfully at the required
head, and the worker startup log was observed. Focused Watchdog regression,
Compose static, documentation, and diff validation results are recorded with
this qualification commit.

## Documentation and next action

`docs/architecture/00-current-state.md` and
`docs/architecture/github-watchdog-control-plane.md` are intentionally
unchanged: this is not a live queue-to-model proof and does not alter Beta or
support posture. `docs/architecture/config-and-ops.md` already records the
missing explicit provider/model prerequisite, so it needs no duplicate change.

The smallest next slice is operator configuration of one authorized Watchdog
provider, exact model identity, and optional inference mode in the runtime
environment, followed by a fresh synthetic captured-snapshot qualification.
That follow-up must use a new attempt and must not reuse this blocked receipt.

## Second qualification — BLOCKED: explicitly selected model unavailable

### Receipt

- **Observed at:** `2026-08-24T15:12:47Z`
- **Branch / source commit:** `codex/define-github-watchdog-control-plane` / `52c07cec672bdd87b409d6cf8b9481e2bb231924`
- **Compose project:** `codexify-watchdog-proof-20260824`
- **Migration head:** `6e9f0a1b2c3`
- **Worker:** `worker-watchdog-review`, container `a814c360d7f7dd52be6c1879cda9aa2d151c05270ca7a3607bdf8b99666d7eb0`, running.
- **Queue:** `github_watchdog_review`.
- **Result:** **BLOCKED** — explicitly configured Watchdog model is unavailable.

### Explicit policy binding and separation proof

The existing canonical settings were bound through a non-secret isolated
Compose override; no tracked environment file or application default was
changed:

| Canonical setting | Bound value |
| --- | --- |
| `CODEXIFY_GITHUB_WATCHDOG_AUTOMATED_REVIEW_PROVIDER` | `local` |
| `CODEXIFY_GITHUB_WATCHDOG_AUTOMATED_REVIEW_MODEL` | `mlx-community/Llama-3.2-3B-Instruct-4bit` |
| `CODEXIFY_GITHUB_WATCHDOG_AUTOMATED_REVIEW_INFERENCE_MODE` | `default` |
| `CODEXIFY_GITHUB_WATCHDOG_AUTOMATED_REVIEW_ESCALATION_MODE` | `disabled` |

The worker process read those Watchdog-specific values while the ambient
`LLM_PROVIDER=local` and `LOCAL_CHAT_MODEL=mlx-community/Llama-3.2-3B-Instruct-4bit`
remained unchanged. The binding therefore did not inherit or derive Watchdog
authority from ambient chat configuration. Local-only remained `true` and cloud
providers remained disabled.

### First blocker and safe stop

The canonical local inventory query reached a live Whoosh'd `/v1/models`
endpoint (`inventory_state=available`, `inventory_source=whooshd:/v1/models`),
but the exact bound model was not advertised (`target_available=false`). This
is a provider-runtime inventory blocker, outside the Watchdog policy,
dispatch, worker, or queue implementation seams. No substitute model was
selected.

The proof stopped before creating a receipt, policy-resolved attempt, captured
snapshot, dispatch, Redis envelope, result, prompt, raw output, or model
request. The existing worker reached its normal queue loop after the binding,
but it did not dequeue a qualification item. Therefore no policy fingerprint,
attempt/result state transition, token usage, cost, or model-correlation value
exists to report, and no GitHub I/O, Command Bus, Build Loop, mutation,
fallback, escalation, or retry occurred.

### Validation

```text
git merge-base --is-ancestor 52c07cec672bdd87b409d6cf8b9481e2bb231924 HEAD
git merge-base --is-ancestor c0cef2be3c6c9c72883e490274d7d78cb6c73a51 HEAD
git merge-base --is-ancestor 79a5df7bd11f0430a3da95805616d120cce334d3 HEAD
.venv/bin/python -m alembic -c backend/alembic.ini heads
docker compose -p codexify-watchdog-proof-20260824 -f docker-compose.yml -f /private/tmp/codexify-watchdog-runtime-proof-ports.yml --profile watchdog config >/dev/null
docker compose -p codexify-watchdog-proof-20260824 -f docker-compose.yml -f /private/tmp/codexify-watchdog-runtime-proof-ports.yml --profile watchdog up -d --no-deps --force-recreate worker-watchdog-review
docker compose -p codexify-watchdog-proof-20260824 -f docker-compose.yml -f /private/tmp/codexify-watchdog-runtime-proof-ports.yml exec -T worker-watchdog-review python -c "import json; from guardian.core.config import get_settings; s=get_settings(); print(json.dumps({'ambient_provider': s.LLM_PROVIDER, 'ambient_model': s.LOCAL_CHAT_MODEL, 'watchdog_provider': s.CODEXIFY_GITHUB_WATCHDOG_AUTOMATED_REVIEW_PROVIDER, 'watchdog_model': s.CODEXIFY_GITHUB_WATCHDOG_AUTOMATED_REVIEW_MODEL, 'watchdog_inference_mode': s.CODEXIFY_GITHUB_WATCHDOG_AUTOMATED_REVIEW_INFERENCE_MODE, 'local_only': s.CODEXIFY_LOCAL_ONLY_MODE, 'cloud_allowed': s.ALLOW_CLOUD_PROVIDERS}, sort_keys=True))"
docker compose -p codexify-watchdog-proof-20260824 -f docker-compose.yml -f /private/tmp/codexify-watchdog-runtime-proof-ports.yml exec -T worker-watchdog-review python -c "import json; from guardian.core.ai_router import discover_local_model_inventory; from guardian.core.config import get_settings; names, resolution = discover_local_model_inventory(get_settings(), timeout_seconds=5); target='mlx-community/Llama-3.2-3B-Instruct-4bit'; print(json.dumps({'target_available': target in names, 'inventory_state': resolution.get('state'), 'inventory_endpoint': resolution.get('inventory_endpoint'), 'inventory_source': resolution.get('inventory_source')}, sort_keys=True))"
docker compose -p codexify-watchdog-proof-20260824 -f docker-compose.yml -f /private/tmp/codexify-watchdog-runtime-proof-ports.yml logs --no-color --tail=30 worker-watchdog-review
```

`docs/architecture/github-watchdog-control-plane.md` and
`docs/architecture/00-current-state.md` remain unchanged because no live
queue-to-model result was proven. The first BLOCKED observation above remains
unchanged and the configured-policy observation does not alter Beta or support
posture.

## Third qualification — BLOCKED: canonical Watchdog qualification model is not advertised by current Whoosh'd inventory

### Receipt

- **Observed at:** `2026-08-24T15:39:21Z`
- **Branch / source commit:** `codex/define-github-watchdog-control-plane` / `9cf9795a63c8c8d4abfecc200ac24988a2b65113`
- **Prerequisite ancestry:** `9cf9795a63c8c8d4abfecc200ac24988a2b65113`, `52c07cec672bdd87b409d6cf8b9481e2bb231924`, and `c0cef2be3c6c9c72883e490274d7d78cb6c73a51` are all ancestors of the source commit.
- **Compose project:** `codexify-watchdog-proof-20260824`.
- **Required canonical Watchdog model:** `qwen3.8-27b-4bit`.
- **Result:** **BLOCKED** — canonical Watchdog qualification model is not advertised by current Whoosh'd inventory.

### Live inventory gate

The live canonical local inventory query completed through the worker's
configured Whoosh'd endpoint:

| Field | Observed value |
| --- | --- |
| Inventory state | `available` |
| Inventory source | `whooshd:/v1/models` |
| Inventory URL | `http://host.docker.internal:8000/v1/models` |
| Advertised model IDs | `gemma-4-12b-it-qat-4bit` |
| `qwen3.8-27b-4bit` advertised | `false` |

The exact canonical Qwen ID is absent. Per the inventory fail-closed rule, no
alternate model was selected and the existing Llama proof override was not
changed. No Whoosh'd model was installed, downloaded, loaded, restarted, or
reconfigured.

### Safe stop

The qualification stopped at live inventory membership, before binding an
explicit Qwen Watchdog policy. Ambient `LLM_PROVIDER` and `LOCAL_CHAT_MODEL`
were not changed and did not provide Watchdog authority. No receipt,
policy-resolved attempt, immutable snapshot, dispatch, Redis envelope, worker
dequeue, provider invocation, prompt, raw output, or result lineage was
created. Therefore no fallback, escalation, retry, GitHub I/O, Command Bus,
Build Loop, mutation, or publication occurred.

The repository migration declaration remains at `6e9f0a1b2c3 (head)`.
The isolated proof database was observed stopped during this preflight, but it
was not restarted or otherwise repaired because the independent model-inventory
gate had already failed.

### Validation

```text
git status --short --branch
git rev-parse HEAD
git merge-base --is-ancestor 9cf9795a63c8c8d4abfecc200ac24988a2b65113 HEAD
git merge-base --is-ancestor 52c07cec672bdd87b409d6cf8b9481e2bb231924 HEAD
git merge-base --is-ancestor c0cef2be3c6c9c72883e490274d7d78cb6c73a51 HEAD
.venv/bin/python -m alembic -c backend/alembic.ini heads
docker compose -p codexify-watchdog-proof-20260824 -f docker-compose.yml -f /private/tmp/codexify-watchdog-runtime-proof-ports.yml --profile watchdog ps -a
docker compose -p codexify-watchdog-proof-20260824 -f docker-compose.yml -f /private/tmp/codexify-watchdog-runtime-proof-ports.yml --profile watchdog exec -T worker-watchdog-review python -c "... discover_local_model_inventory(get_settings(), timeout_seconds=5) ..."
```

The inventory command returned `target_available=false` for the only accepted
qualification ID. The proof did not continue to Compose restart, policy
binding, capture, dispatch, or execution validation. As with the prior two
BLOCKED observations, `docs/architecture/github-watchdog-control-plane.md` and
`docs/architecture/00-current-state.md` remain unchanged: no queue-to-model
path is live-proven and the Watchdog Beta/support posture is unchanged.
