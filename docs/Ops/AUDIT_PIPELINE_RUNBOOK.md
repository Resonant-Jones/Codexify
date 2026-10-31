# Audit Pipeline Runbook

Purpose: describe the scheduled audits that maintain Codexify's release truth,
where they run, and how their output reaches `origin/main` — so that anyone
reading a generated audit can know exactly which revision it describes.

## The Problem This Solves

Until 2026-10-30 every scheduled audit ran in the **shared primary checkout**
(`/Volumes/Dev_SSD/Codexify-main`). That produced three defects:

1. **The audits raced each other.** The weekly release audit, the guardian
   work brief, and the (since-retired) daily audit all fired at **05:00** in
   the same working tree, and all wrote into `docs/architecture/`.
2. **The weekly audit mutated a checkout that had a concurrent executor in it.**
   Its own run record for 2026-10-30 reads: *"the active checkout began on
   `feat/saved-widget-promotion-20261029` … was temporarily switched to `main`
   for the scoped edit, then restored to the feature branch."*
3. **Its output never reached the thing that reads it.** The audit committed to
   the **local** `main` branch, which was never pushed, while the dev-log
   publisher read `00-current-state.md` from the **fetched `origin/main` tip**.
   The published truth document was therefore always at least one audit cycle
   stale, and the audit's own commits were stranded on a local branch.

Concretely, on 2026-10-30 the local `main` was **20 commits behind
`origin/main`** and did not contain PR #956. The weekly audit described that
stale tree as current state.

## The Current Arrangement

| Job | Runs at | Runs in | Publishes |
|---|---|---|---|
| Weekly mainline release audit | daily 05:00 | audit checkout | `00-current-state.md` + architecture README → `origin/main` |
| Guardian work brief | daily 05:00 | audit checkout | local reporting artifacts only (gitignored) |
| Daily dev-log publisher | daily 22:00 ET | fetches `origin/main` | dated dev log → `origin/main` |
| Daily audit (morning/evening) | **retired** | — | — |

### The audit checkout

```
/Volumes/Dev_SSD/Codexify-audit-pinned
```

A dedicated worktree, used by nothing else. It is **detached** at the fetched
`origin/main` tip and is never switched to a local branch, so "the tree that
was audited" and "the revision the result is published onto" are the same git
object.

Every run begins with:

```bash
/Users/chriscastillo/.minimax/agents/mavis/devlog/prepare_audit_checkout.sh
```

which fetches `origin/main`, hard-resets the checkout to that tip, and refuses
to continue if any tracked file is still modified. It prints
`AUDIT_CHECKOUT_READY <sha>`; that sha is the audited revision.

### Publication

The weekly audit does **not** commit to `main` and does **not** push. It
publishes through one guarded path:

```bash
/Users/chriscastillo/.minimax/agents/mavis/devlog/publish_current_state.sh \
  --source-dir /Volumes/Dev_SSD/Codexify-audit-pinned
```

The publisher is the same mechanism the dev-log publisher uses
(`lib/publish_origin_main.sh`), so every automated write to `origin/main`
obeys the same guarantees:

- It never switches, resets, or mutates any existing checkout's working tree.
- It publishes from a **fresh isolated temporary worktree** created on the
  freshly fetched `origin/main` tip — never from a stale local branch.
- The commit parent **must** be that fetched tip, and the commit tree must
  change **only** the requested paths.
- It re-checks for `origin/main` drift immediately before pushing, and refuses
  to push if `main` moved during the run.
- It pushes normally (never force), then verifies the remote SHA and the
  published paths.
- Every failure stops with a single `RESULT:` line and a `BLOCKER:` line. It
  never falls back to another publication path.

### The guards specific to the current-state document

`publish_current_state.sh` refuses to publish rather than degrade the truth
document when:

- `00-current-state.md` does not carry its eleven required sections **in
  order**;
- the architecture README no longer references `00-current-state.md`;
- the document exceeds its line budget;
- the `Last updated` date would go **backwards** relative to what is already
  published;
- `origin/main` moved since the revision the document was authored against
  (exit code 22) — the audit must re-run against the new tip rather than
  publish a description of a revision that is no longer current.

It is idempotent: if both documents are byte-identical to the tip it reports
`RESULT: NOOP` and publishes nothing.

## The Retired Daily Audit

`scripts/daily_audit.py` and the `daily-audit` automation are retired
(paused 2026-08-12; last output 2026-08-09). `docs/audits/daily/morning/` and
`docs/audits/daily/evening/` are historical artifacts, not live reports.

The generator resolved its output directory from the checkout it ran in, so
each run wrote into whichever checkout or worktree hosted the script. The
reports were not comparable across runs. Copies of those paths found in other
worktrees are inherited files with identical timestamps, not independent runs.

`scripts/daily_audit.py` remains in the tree for historical reference. Nothing
scheduled invokes it.

## Worktree Sprawl — Known Hazard

The repository has **234 worktrees** across `/Volumes/Dev_SSD/Codexify-main/.worktrees`,
`~/.codex/worktrees`, and `/Volumes/Dev_SSD/offload/codex/worktrees`. This is
not cosmetic: it filled the volume to 100% (2.0 GiB free as of 2026-10-30),
and during the audit-pipeline investigation a `cd` into the primary checkout
failed outright because a concurrent executor was mid-mutation.

Any change to this pipeline must verify that the audit checkout is a *dedicated*
path and not one of the shared ones.

## When the Audit Cannot Publish

An audit that cannot publish is reporting a real condition, not a bug in the
publisher. The usual causes are:

- `origin/main` moved during the audit (exit 22) — the next run re-audits the
  new tip. This is the expected outcome on a busy day.
- The eleven-section contract was broken by the edit — the audit must repair
  the document, not relax the guard.
- The push was rejected — report it. The repository's `main` is governed by the
  `Main Lock` ruleset, which requires a pull request; the publisher's
  credential is an authorised bypass actor for the daily artifacts only. A
  rejection means that authorisation no longer covers this path, and the
  output should be delivered by a PR instead.
