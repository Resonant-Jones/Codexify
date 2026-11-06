# Stock Compose runtime qualification — 456da46b8 — 2026-11-05

- Rubric: ../rubrics/supported-compose-stock.md
- Rubric version: 1
- Verdict: FAIL
- Date: 2026-11-05 (America/New_York)
- Tester: automated architecture-impact qualification agent
- Evaluated source: 456da46b8a0549ea1d2bd440971f7477efa1669b
- Runtime profile: v1-local-core-web-mcp
- Startup: stock Docker Compose, without the source-matched launcher
- Provider/model inventory: local / local-chat (Whoosh'd)

## Qualification metadata

```yaml qualification-metadata
qualification_id: supported-compose-stock
rubric_version: 1
verdict: FAIL
commit: 456da46b8a0549ea1d2bd440971f7477efa1669b
date: 2026-11-05
tester_alias: stock-compose-runtime-qualification
tester_kind: automated
assistance_level_peak: 0
evidence:
  - docs/architecture/proofs/supported-compose/2026-11-05-supported-compose-stock-456da46b8.md
```

## Scope and result

This is one integrated stock-startup execution of the supported
`v1-local-core-web-mcp` profile at the named local revision, in a disposable
Compose project with its own network, volumes and container names. The
source-matched launcher was not invoked, no `src-<sha12>` image was resolved,
and no shared production tag was replaced or re-pointed. The Private Preview
lane was verified unmodified before and after.

The source-head migration contract **passed**: the migrator's own coherence
proof passed at 135 revisions, the migrator exited 0, and the live
`alembic_version`, read directly out of PostgreSQL rather than from a
container exit code, was the evaluated checkout's single Alembic head
`a7d4c9e2f1b3` with exactly one row.

Ordinary chat completed and was durably read back; an explicitly requested
unavailable model failed closed before provider execution and persisted no
assistant message; and durable state survived a backend restart.

**Document ingestion and retrieval failed.** The shared Chroma collection
`codexify_vault_supported` was created with dimension **384**, while the
configured local embedder (`bge-large-en-v1.5`) produces **1024**. Every
document embedding therefore failed closed with *"Collection expecting
embedding with dimension of 384, got 1024"*, and the document was terminally
marked failed with that reason. The collection dimension is fixed by whichever
writer touches it first, and no dimension is pinned at creation. The live
Private Preview lane's collection is 1024, so the mismatch is specific to a
fresh stock-path volume.

Browser projection was not exercised in a real browser and is UNPROVEN; under
this rubric an unexercised browser boundary prevents a PASS independently.

This execution is **FAIL**, not PASS. It never silently becomes PASS, it
qualifies no release status, and **release remains HOLD**.

**Freshness note.** This receipt is bound to the evaluated commit
`456da46b8a0549ea1d2bd440971f7477efa1669b`, which remains an ancestor of the
branch tip. After the run, `main` advanced with a merge that changed
`guardian/routes/music_projects.py`, which is inside this surface's declared
`surface_paths`. The registry therefore projects `supported-compose-stock` as
`FAIL` at `freshness: stale` against the branch tip, with the blocker *"The
tested commit no longer describes the current tip: 1 path(s) in this
qualification surface changed since the run."* That staleness is the designed
behaviour of a commit-bound surface whose code moved after the run, and it is
reported rather than suppressed. A re-run at the merged tip is required for a
`current` verdict; it would be expected to reach the same verdict, because the
check-4 dimension defect is inherited and unchanged by that merge.

## Check matrix

| Check | Result | Assistance | Evidence | Notes |
| --- | --- | ---: | --- | --- |
| 1. Supported topology and startup | PASS | 0 | proof §5 | All seven required services healthy/running; `docker compose config --quiet` succeeded. |
| 1. Migrations applied at the source head | PASS | 0 | proof §5 | Migrator exit 0; coherence proof passed at 135 revisions; live `alembic_version` = `a7d4c9e2f1b3`, exactly one row, read directly from PostgreSQL. |
| 2. Health and inventory | PASS | 0 | proof §6 | `/ping`, `/health` (`release_hold: false`, profile `valid: true`, no mismatches), `/health/llm` (local provider authorized and available, `local-chat`). |
| 3. Ordinary chat and durable readback | PASS | 0 | proof §7 | Assistant message `STOCK-QUAL-PASS` persisted with a native origin assertion; attempt linked by `completed_message_id`; terminal outcome observed (`task.completed`). The first attempt failed closed on a local-model cold start and was retried after the model loaded. |
| 4. Document ingestion and retrieval | **FAIL** | 0 | proof §8 | Collection dimension 384 vs embedder 1024; every embedding failed closed; document terminally failed with the reason recorded. |
| 5. Explicit model authority | PASS | 0 | proof §9 | Failed before provider execution; no substitute executed; no assistant message persisted; durable attempt recorded `task.failed`. |
| 6. Browser projection | UNPROVEN | 0 | proof §10 | Frontend served HTTP 200 and the thread projection was correct, but **no real-browser observation was performed**. |
| 7. Restart recovery | PASS | 0 | proof §11 | Backend restarted and returned healthy; all three messages including the assistant reply survived. |

## Blocking criteria encountered

- **the migrator fails closed, or the live `alembic_version` does not equal the
  evaluated checkout's single Alembic head** — not triggered; the migrator
  succeeded and the live head matched.
- **the supported topology does not start, or a required service is unhealthy**
  — not triggered at observation time.
- The check-4 dimension mismatch is a required check failing outright, which
  prevents PASS on its own.

## Evidence and release boundary

- [Detailed runtime proof](../../architecture/proofs/supported-compose/2026-11-05-supported-compose-stock-456da46b8.md)
- The image was assembled from a base built by the same repository
  `backend/Dockerfile` under BuildKit from `97778bedf`, plus this revision's
  `guardian/` and `backend/` trees overlaid verbatim. The image's baked
  migration source (`versions/*.py` and `env.py`) and its `run_migrator.py`
  were verified byte-identical to the evaluated checkout by SHA-256 **inside
  the image**, before any startup was judged. The proof does not claim the
  image is byte-identical to a from-scratch build of the repository Dockerfile
  on this date.
- Registry output is generated by `scripts/qualification/generate_registry.py`
  and validated by `scripts/qualification/validate_registry.py`.
- This receipt qualifies only the `supported-compose-stock` surface. It never
  qualifies `supported-compose` (the source-matched path) or
  `onboarding-and-people`. A receipt for one surface never qualifies another.
- **Release remains HOLD.**
