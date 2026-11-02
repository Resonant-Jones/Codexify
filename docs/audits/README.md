# Audits Directory

## Daily audits (morning / evening) — RETIRED

`docs/audits/daily/morning/` and `docs/audits/daily/evening/` are **historical
artifacts, not live reports**.

The daily audit pipeline (`scripts/daily_audit.py`, automation `daily-audit`)
was paused on 2026-08-12. Its last output is dated **2026-08-09**. Nothing in
those two directories describes the current state of the repository, and no
scheduled job writes to them.

It was retired because the generator resolved its output directory from the
checkout it ran in (`REPO_ROOT = Path(__file__).resolve().parents[1]`), so each
run wrote into whichever checkout or worktree happened to host the script. The
resulting reports were not comparable across runs and could not be aggregated.
The files that exist in other worktrees under the same paths are copies
inherited when those worktrees were created, not independent runs — they carry
identical timestamps.

The live release-truth artifact is `docs/architecture/00-current-state.md`,
published by the weekly mainline release audit. See
[`docs/Ops/AUDIT_PIPELINE_RUNBOOK.md`](../Ops/AUDIT_PIPELINE_RUNBOOK.md) for
the current pipeline, its isolation guarantees, and its publication path.

## Guardian Work Brief

The daily audit artifacts are evidence inputs for the original Axis instance in
ChatGPT and for manual KB transfer. They should not be treated as the whole
operating layer by themselves.

Use `scripts/guardian_work_brief.py` or `make guardian-brief` to generate the
decision packet that sits above the audits:

- `docs/guardian/work-briefs/latest-axis-brief.md`
- `docs/guardian/work-briefs/latest-codex-next-task.md`
- `docs/guardian/work-briefs/latest-truth-ledger.json`
- `docs/guardian/work-briefs/latest-decision-log.md`

The brief turns audit evidence, current-state truth, repo status, and draft
publication state into a compact `Reality / Drift / Risk / Decision / Task`
packet. See `docs/Ops/GUARDIAN_WORK_BRIEF_RUNBOOK.md` for the operating flow.

## Beta Release Sentinel

`scripts/release/beta_release_sentinel.py` generates repo-local, evidence-led beta readiness artifacts.

What it does:
- Collects branch, HEAD, and worktree status.
- Reads the current release-definition checklist from `docs/architecture/00-current-state.md`.
- Tries to run `scripts/audit_platform_readiness.py` and records summary or failure warning.
- Writes deterministic dated artifacts:
  - `docs/audits/generated/YYYY-MM-DD-beta-sentinel.md`
  - `docs/audits/generated/YYYY-MM-DD-beta-sentinel.json`
- Appends an evidence-led dated entry to `CHANGELOG.beta.md`.

What it does not prove:
- It is not release approval by itself.
- It does not widen supported beta scope.
- It does not make cloud-provider support claims.
- It does not claim packaged desktop replaces local Compose.
- It does not claim command bus, delegation, federation, graph writes, or worker-control dispatch are public beta promise.

Related index:
- [`Release Candidate Evidence Index — 2026-05-15`](../release/RELEASE_CANDIDATE_EVIDENCE_2026-05-15.md)

Manual run:

```bash
python scripts/release/beta_release_sentinel.py \
  --date 2026-05-13 \
  --output-dir docs/audits/generated \
  --changelog CHANGELOG.beta.md
```

Publication boundary:
- Sentinel output is intentionally repo-local and file-output only in this phase.
- Website, email, and Substack publication automation is deferred until the artifact contract stabilizes.
