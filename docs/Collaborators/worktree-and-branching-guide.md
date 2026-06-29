# Worktree and Branching Guide

Use the film/editing-table analogy:

- `main` = the shared reel / current shared truth
- branch = an alternate cut / path of commits
- worktree = a separate editing table / folder checked out to a branch
- commit = a saved strip of film
- merge = bring an alternate cut back into the shared reel
- rebase = move a branch so it starts from a newer point in `main`
- cherry-pick = copy one specific commit without taking the whole branch

## What This Means in Practice

You can keep working in your branch even if `main` moves on.

You can also keep `main` checked out locally in another place if that helps you inspect the shared reel while you edit elsewhere.

The point of a worktree is separation: one folder can stay stable while another folder carries your edits.

## Answers To The Usual Questions

### Do I wait until `main` includes my bit before I keep working?

No. Keep working on your branch or worktree. Pull from `main` when you need fresh shared truth, but do not stop exploring just because `main` moved.

### Do I keep `main` on my computer at the same time as my edit?

Yes, if that helps. A local checkout of `main` is useful for comparison, review, or rebasing. Your actual edits should stay in the branch worktree.

### Do edits sometimes not make the final cut?

Yes. Some edits are exploratory, some are replaced, and some are discarded after review. That is normal. The final reel should contain only what survives validation and review.

## Rules of Thumb

- Pull from `main` freely.
- Explore on branches.
- Do not merge directly to `main` casually.
- Review before shared truth changes.

## Practical Reminder

If you are unsure whether something belongs in the shared reel, treat it as branch-local until review proves otherwise.
