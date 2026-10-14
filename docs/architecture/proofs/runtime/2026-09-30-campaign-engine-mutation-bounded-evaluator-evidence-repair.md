# Campaign Engine mutation-bounded Evaluator evidence repair

Date: 2026-09-30

Evidence class: provider-free deterministic implementation proof.
Aligned with ADR-068; no new ADR or release-support claim.

## Canonical operational specimen

`CANONICAL_MILESTONE_A_TASK=docs/Campaign/fixtures/milestone-a-ordinary-single-task.md`

That repository fixture is the authored ordinary single-Task specimen for
Campaign -> live Executor -> boundary validation -> Task validation -> live
Evaluator -> Receipt -> CampaignState. It retains the Makefile-only scope,
later supported recipe, optional profile, Compose environment argument,
one docs-validation attempt, and all operator stop/authority constraints.
Future trials consume this artifact instead of reconstructing chat history.

## Observed blocker

The fresh ordinary-tool-selection Campaign
`campaign-milestone-a-makefile-21c5b1b5f3f1` ran from `0d7ce72c8` with one
DeepSeek Executor invocation, effort `off`, and no required tool. It removed
the stale 13-line recipe, changed only Makefile, passed boundary validation,
and passed its single `make PYTHON=python3 docs` attempt without the duplicate
warning. Evaluator preparation then failed with
`changed_file_snapshot_too_large`: before/after file sizes were 33,917/29,624
bytes and the runtime limited both whole snapshots to 4,096 bytes. That failed
Campaign and uncommitted disposable target remain preserved; neither was
resumed or repaired.

## Implementation

File size is not change size. The Evaluator verifies complete file bytes
locally against Git baseline, Executor snapshot, and Attempt hashes. Its
packet carries changed-file paths, before/after SHA-256 and byte sizes, and
the complete unified diff. The existing 16,384-byte diff bound and 32,768-byte
packet bound remain; oversized actual evidence fails closed without a
partial diff. Missing-final-newline markers are represented explicitly.
Invalid UTF-8, path/hash mismatches, and changed-set inconsistencies fail
before invocation.

The packet projects target snapshots onto changed files. Full repository
hash snapshots remain in the immutable checkpoint, are checked against
actual target readback, and remain covered by checkpoint artifact hashes.
Task validation and Executor identity/Attempt evidence remain linked.

The target fingerprint now also supports a physical Git worktree's `.git`
file. It verifies the resolved Git root and Git HEAD, hashes target bytes,
and preserves symlink and drift rejection. Guardian grants, Evaluator
read-only authority, retry/repair/fallback/rebinding policy, and CE-L3 gates
are unchanged.

## Deterministic proof

Focused tests cover a small change in a file larger than 128 KiB with 250
unchanged files; the complete fake lifecycle reaches final CampaignState
with a bounded packet while its full checkpoint snapshots remain intact.
The exact canonical Makefile fixture, all twelve acceptance criteria, and
its complete stale-block deletion also fit the existing packet bounds.
Oversized changes, snapshot/hash inconsistency, invalid UTF-8, and Git HEAD
drift fail closed. Existing read-only, authorization, identity, validation,
and checkpoint-preservation regressions are retained.

Provider calls during this repair: **0**. CE-L3: **not entered**.
No live ordinary Task success is claimed by these fake-invocation tests.

Validation:

- Focused live Evaluator suite: 32 tests passed.
- Aggregate schema, live Executor, and live Evaluator regressions:
  167 passed in 33.98 seconds.
- Ruff on changed Python surfaces: passed (existing configuration advisory).
- `PYTHON=.venv/bin/python make docs`: passed; the unrelated pending duplicate
  Make target warning remains until a separate successful Task closeout.
- `git diff --check`: passed.

After provider-free validation, the operator has authorized a fresh Campaign
and a new physical disposable worktree using this same canonical fixture.
That run's result must be recorded separately from repair proof and must
return control before any Task commit.
