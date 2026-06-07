# Guardian Work Brief - Truth Ledger - 2026-06-05

## Evidence Gathered
- `make guardian-brief` failed because this checkout has no `guardian-brief` target.
- `git status --short --branch --untracked-files=all` before this packet showed `codex/map-researchcode-functions...origin/codex/map-researchcode-functions [ahead 2]` and no file-level changes.
- `git rev-list --left-right --count HEAD...@{upstream}` returned `2 0`.
- `HEAD` is `e05635e54be3` (`Add Guardian work brief fallback packet`).
- `docs/architecture/00-current-state.md` says current supported release truth is anchored to `main`, local Docker Compose, local-only provider posture, aligned supported-profile/catalog/health, chat completion, upload/embed/readback, coding-result return, and workspace-local Obsidian retrieval proof.
- `docs/architecture/00-current-state.md` explicitly says the Guardian Retrieval Navigation Model, adaptive route hints, reviewable graph evolution proposals, and self-improving memory are not shipped runtime features.
- `docs/architecture/README.md` points readers to `00-current-state.md` first for current-state interpretation and release readiness.
- `docs/architecture/adr/adr-index.md` remains the ADR entrypoint and places ADRs beside, not above, the main architecture corpus.

## Proven
- This branch is ahead of its upstream by two commits and behind by zero commits.
- The worktree was clean before today's packet apart from branch divergence.
- The preferred automation target is absent in this checkout.
- The current-state doc remains the authority for release truth.

## Code-Path Only / Not Re-Proven Today
- No backend runtime path was exercised.
- No queue, worker, provider, Redis, Postgres, frontend, SSE, or health path was tested.
- No supported Docker Compose proof was rerun.
- No generator test was run because the generator is absent on this branch.

## Blockers
- Missing `make guardian-brief` target prevents preferred automated generation in this checkout.
- Side-branch status means `main` release evidence should not be treated as freshly proven on this branch.

## Changed Files From This Run
- `docs/guardian/work-briefs/2026-06-05/axis-brief.md`
- `docs/guardian/work-briefs/2026-06-05/codex-next-task-packet.md`
- `docs/guardian/work-briefs/2026-06-05/truth-ledger.md`
- `docs/guardian/work-briefs/2026-06-05/decision-log.md`
