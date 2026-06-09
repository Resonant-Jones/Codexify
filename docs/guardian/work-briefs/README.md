# Guardian Work Briefs

Guardian Work Briefs are dated operator reporting packets for orienting Axis and
the next Codex task inside the current Codexify checkout. They summarize repo
state, branch drift, current-state truth boundaries, and the next narrow review
focus without exercising runtime machinery.

## Canonical Files

Each generated packet writes exactly four markdown files under
`docs/guardian/work-briefs/<YYYY-MM-DD>/`:

- `axis-brief.md`
- `codex-next-task-packet.md`
- `truth-ledger.md`
- `decision-log.md`

## Run

```bash
make guardian-brief
```

By default the generator uses the current UTC date. Tests and automation can set
`GUARDIAN_BRIEF_REPO_ROOT` and `GUARDIAN_BRIEF_DATE` to make the run
deterministic.

## What The Generator Records

- Repo root, branch, short HEAD SHA, upstream ref, and ahead/behind counts when
  an upstream exists.
- `git status --short --branch --untracked-files=all` before generated files are
  written.
- Whether expected architecture files are present.
- Current-state release-truth context from
  `docs/architecture/00-current-state.md`.
- The four generated file paths for the dated packet.

## What It Does Not Do

The generator does not run Docker Compose, backend, frontend, workers, Redis,
Postgres, Neo4j, model runtimes, browsers, marketing generation, daily audits,
heartbeat bundles, public exports, campaign generation, branch cleanup, pull,
rebase, merge, push, or release machinery.

Generated work briefs are reporting artifacts. They are not runtime proof, audit
proof, release signoff, or release claims. `docs/architecture/00-current-state.md`
remains the short-horizon release-truth boundary for interpreting every packet.
