# Credential history rewrite ref reconciliation

## Purpose

This is a no-mutation reconciliation snapshot for a future credential-history
rewrite. It identifies the current heads-and-tags publication surface without
authorizing any remote action.

## Prior Security Proof State

Credentials were rotated, the public tip was sanitized, a local replace-only
rewrite was proven, and current reachable LFS payloads were archive- and
restore-verified. Remote history has not been rewritten.

## No-Mutation Guarantee

All rewrite work occurred in disposable bare repositories. No working-repository
rewrite, push, force push, remote ref update, branch-protection change, or pull
request mutation occurred.

## Current Remote Baseline

Fresh remote `main`: `179d80207434ecde3c224e8e2425feffda9351ce`.

## PR #581 Disposition

PR #581 is merged. The current repository has no open pull requests.

## LFS Preservation Digest Verification

The operator-owned preservation archive and manifest matched their recorded
SHA-256 digests before this analysis. The archive was not extracted or changed.

## Source Ref Construction

A fresh bare source was fetched with explicit `refs/heads/*` and `refs/tags/*`
refspecs after removing Git's default remote-tracking fetch refspec.

## Excluded GitHub-Managed Ref Namespaces

The source and candidate each contained only `refs/heads/*` and `refs/tags/*`.
No GitHub pull refs, remote-tracking refs, backup refs, or filter-repo temporary
refs were eligible publication targets.

## Rewrite Method

The disconnected candidate used the proven `git filter-repo --replace-text`
method with a private five-rule replacement map.

## Exact Ref-Name Preservation

Source and candidate ref-name sets were identical. No extra candidate heads
were introduced.

## Branch Inventory

The current source contains 361 branches and zero tags. All 361 branch tips
changed under the candidate rewrite; none were unchanged.

## Tag Inventory

There are zero current tags, so no tag recreation decision is presently needed.

## Changed Branches

All 361 source branches require a changed-tip classification under the candidate
rewrite. Publication must fail if any live source SHA differs from the recorded
private map at execution time.

## Unchanged Branches

None.

## Protected Branches

One changed branch is protected. Any future update requires a separately
approved temporary protection procedure.

## Fully Merged Branches

286 changed branches are fully merged into current `main`. They are retirement
candidates only; this report does not approve deletion.

## Branches With Unique History

75 changed branches contain commits unique relative to current `main`. Each
requires an explicit owner or preservation decision before any remote rewrite.

## Open Pull Request Heads

There are zero open-PR head branches in the current GitHub inventory.

## Changed Tags

None.

## Signature Impact

Signature-bearing commit and annotated-tag impact has not been fully audited in
this pass. Any rewritten signed commit or changed signed tag would require
signature recreation as a separate decision.

## Sensitive-Value Scan

The earlier candidate proof established zero historical-value matches. A new
full heads-and-tags exhaustive blob/message/tag scan was not completed in this
reconciliation pass, so that result is not re-asserted as fresh evidence here.

## Git Integrity

The heads-and-tags source passed `git fsck --full --no-reflogs`; the candidate
also passed the same Git object-integrity check.

## LFS Pointer Preservation

The earlier full pointer-preservation proof remains available. A new dual
source/candidate pointer audit was not completed in this pass.

## Publication Ref Policy

Only reconciled `refs/heads/*` and `refs/tags/*` are eligible. GitHub-managed
pull refs must never be force-pushed; absent source refs must never be created;
fully merged branches require separate retirement approval; unique-history
branches require named decisions; protected branches require a protection
procedure; and unchanged refs must not be updated. The expected rewritten
`main` SHA is `2cf4cc6e7d2220ba72bbdef166e2f57ec032ca4c`.

## Required Human Decisions

- Decide preservation, retirement, or force-update handling for each of the 75
  unique-history branches.
- Approve any temporary protection procedure for the protected branch.
- Approve publication sequencing and collaborator re-clone communication.

## Remaining Remote-Rewrite Prerequisites

Complete the exhaustive secret scan, dual LFS pointer audit, signature impact,
and exact changed-branch appendix; then obtain explicit remote-rewrite
authorization. No force update or branch retirement is authorized now.

## Recommendation

The heads-and-tags surface is cleanly constructed and candidate ref names are
exactly preserved, but the remaining audits and exact unique-branch appendix
are incomplete.

## Explicit Non-Actions

No remote ref changed, no pull request was modified, no branch was deleted or
created, and no credential value was printed or committed.

## Exact Changed-Ref Appendix

Deferred pending the required exhaustive audit and owner-decision packet.

Recommendation: HOLD
