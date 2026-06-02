# Guardian Work Brief Runbook

Purpose: give a solo builder a daily operating packet that keeps the original Axis instance, Codexify, and Codex task execution aligned without requiring a human team meeting.

## What It Is

`scripts/guardian_work_brief.py` turns repo-local truth into four artifacts:

| Artifact | Use |
|---|---|
| `axis-brief.md` | Manual transfer packet for the original Axis instance in ChatGPT. |
| `codex-next-task.md` | Narrow task prompt for the next Codex implementation or verification slice. |
| `truth-ledger.json` | Machine-readable source ledger for future automation. |
| `decision-log.md` | Daily closeout record: finished, blocked, next priority, Axis KB note. |

The brief is not a replacement for the platform readiness audit. The audit remains an evidence input. The brief is the decision layer that turns evidence into the next move.

## Default Command

```bash
make guardian-brief
```

Equivalent direct command:

```bash
python3 scripts/guardian_work_brief.py
```

Use an explicit date when backfilling or rerunning a day:

```bash
python3 scripts/guardian_work_brief.py --date 2026-05-28
```

## Output Paths

Dated artifacts:

```text
docs/guardian/work-briefs/YYYY-MM-DD/axis-brief.md
docs/guardian/work-briefs/YYYY-MM-DD/codex-next-task.md
docs/guardian/work-briefs/YYYY-MM-DD/truth-ledger.json
docs/guardian/work-briefs/YYYY-MM-DD/decision-log.md
```

Latest pointers:

```text
docs/guardian/work-briefs/latest-axis-brief.md
docs/guardian/work-briefs/latest-codex-next-task.md
docs/guardian/work-briefs/latest-truth-ledger.json
docs/guardian/work-briefs/latest-decision-log.md
```

## Daily Use

1. Run `make guardian-brief`.
2. Read `latest-axis-brief.md`.
3. Transfer the `Reality`, `Drift`, `Risk`, and `Decision` sections into Axis's KB or working thread.
4. Use `latest-codex-next-task.md` as the next Codex prompt when you want implementation help.
5. Fill in the closeout fields at the end of the day:
   - `Finished today`
   - `Blocked`
   - `Next priority`
   - `Axis KB note`

## Guardrails

- Treat `docs/architecture/00-current-state.md` as the release-truth gate.
- Treat generated audits and marketing packets as alignment inputs, not runtime proof.
- Do not create a new daily automation until the existing daily audit and heartbeat paths are accounted for.
- Prefer one decision packet per day over many overlapping generated artifacts.
- If the brief says the branch is behind or the worktree is dirty, classify that before making release claims.

## Why This Exists

This is a monotropic operating aid. It reduces the amount of social and project-management modeling required while building. The goal is not to imitate a team meeting; the goal is to preserve attention for the work by making truth, drift, risk, and next action visible in one place.
