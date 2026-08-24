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
