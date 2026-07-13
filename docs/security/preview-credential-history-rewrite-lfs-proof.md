# LFS-safe preview-credential history rewrite proof

## Purpose

This report records a local-only, disposable-mirror proof path for removing the
rotated preview-credential values from reachable Git history without changing
the working repository, `origin`, GitHub, branch protection, tags, or PR #581.
It is evidence for a separately authorized remote-remediation task, not an
authorization to perform one.

## Prior Rehearsal Result

The prior rehearsal established that the historical exposure was reachable from
24 commits and that public-tip containment was complete. Its mandatory
`--sensitive-data-removal` attempt failed during Git LFS metadata handling, so
it correctly ended as `NEXT_PROOF_NEEDED` without a rewritten candidate.

## No-Push Guarantee

Every rewrite attempt used a fresh disposable mirror with all remotes removed.
No ref was pushed, force-pushed, deleted, retargeted, or otherwise changed
outside those mirrors. The working repository was not rewritten.

## Tool and Interpreter Matrix

| Tool | Observed version or state |
| --- | --- |
| Git | 2.50.1 (Apple Git-155) |
| Default Python | 3.14.4 |
| Git LFS | 3.7.1 |
| git-filter-repo | a40bce548d2c |
| git-filter-repo executable | `/opt/homebrew/bin/git-filter-repo` |
| git-filter-repo shebang | `#!/usr/bin/env python3` |
| Python 3.13 | not installed |
| Python 3.12 | 3.12.13 |
| Python 3.11 | 3.11.14 |

## Original Failure Reproduction

The required default-interpreter sensitive-mode command exited nonzero on a
fresh mirror. Its sanitized diagnostic retained the LFS tracker location and
exception class, while omitting private values, temporary paths, and raw stack
trace text.

## Sanitized Failure Classification

Classification: `filter_repo_lfs_metadata_parser`.

The failure contains the installed filter-repo LFS object-tracker parser
markers and a `ValueError`; it does not identify malformed reachable pointer
metadata, missing local LFS payloads, Git object corruption, or a Python-only
compatibility error as the direct cause.

## Git Object Integrity

The source mirror's `git fsck --full --no-reflogs` completed with no output and
no reachable Git object errors. Git object integrity is therefore distinct from
the separate local LFS payload-availability result below.

## LFS Pointer Inventory

The independent reachable-blob audit found 553 pointer blobs representing 551
distinct LFS object IDs. The audit accepts valid Git LFS extension lines in
addition to the required version, SHA-256 OID, and numeric-size records.

## LFS Payload Availability

`git lfs fsck --pointers` succeeded. Full `git lfs fsck` exited nonzero in the
non-smudging clone because payloads were not locally available: `git lfs
ls-files --all --long` reported 4 cached payloads and 547 not cached. No hash
mismatch evidence was found. No LFS payloads were downloaded for this proof.

## Malformed Pointer Findings

The independent pointer parser found zero malformed reachable pointer blobs;
the Git LFS pointer-only check also passed. The original sensitive-mode failure
is therefore not classified as malformed-pointer evidence.

## Python Runtime Comparison

Sensitive-mode attempts failed with the same sanitized LFS object-tracker
parser classification under Python 3.14.4, Python 3.12.13, and Python 3.11.14.
Python 3.13 was unavailable and was not installed. This rules out the tested
interpreter versions as a practical resolution for this installed
git-filter-repo failure.

## Sensitive-Mode Rewrite Results

| Attempt | Result |
| --- | --- |
| Default Python 3.14.4 | failed: `filter_repo_lfs_metadata_parser` |
| Python 3.12.13 | failed: same classification |
| Python 3.11.14 | failed: same classification |

Each attempt was made from a newly copied disposable source mirror with its
remote removed.

## Replace-Only Fallback Result

The fresh `git filter-repo --replace-text` fallback completed successfully. It
is not treated as automatically equivalent to sensitive mode; the independent
absence scan, ref mapping, pointer comparison, and Git integrity checks below
are the basis for accepting it as a local technical proof method.

## Selected Rewrite Method

Selected local proof method: `git filter-repo --replace-text` using the private
five-rule replacement map derived from the known exposure commit.

Sensitive mode remains unsuitable with the installed filter-repo version until
its LFS metadata parser behavior is separately resolved.

## Changed Refs

The source inventory contained 363 heads/tags; the candidate contained 365.
The candidate map records 925 changed refs: 363 heads and 562 pull-request
refs. It records no changed tags. Of the heads/tags inventory, 360 changed and
3 remained unchanged; two additional local candidate heads were present. This
is an observed candidate-ref difference that a remote execution plan must
reconcile explicitly rather than reproduce blindly.

The candidate rewritten `main` is `aceaa7b55aa09c40927f9d61f633d8ca0fb8ccd5`.

## First Changed Commits

Filter-repo produced three first-changed commit pairs:

- `4e453b8d972d4993dfa37caed20a64224ad72204` -> `24a80744ed38188a0c1f1fa12cfc0119e3b5ee5d`
- `6e74d504f24454426b803b19a70a634eefe62f5c` -> `a956be8da2172ebbfca10cb0a6755af774cacf5c`
- `da400f620c7c23b9479b99a6be9bbfd91d11c41d` -> `482de61a7bce48ade4e8f9a645c5a1c4afa14b7f`

## Exhaustive Historical-Value Scan

The rewritten candidate was scanned across all 23,078 reachable blobs, all
reachable commit messages, and annotated tag messages using exact historical
values held only in private scratch data. Results were zero credential or
address matches, zero commit-message matches, and zero tag-message matches.
The candidate `main` example file also passed sanitized checks for all three
placeholder-shaped secret fields and both required generic email addresses.

## LFS Pointer Preservation

The candidate audit found 553 pointer blobs, 551 distinct object IDs, and zero
malformed pointers. Its complete set of `(LFS object ID, declared size)` pairs
was identical to the source set: zero missing pairs and zero new pairs. The
targeted example file was not an LFS pointer.

## Rewritten Repository Integrity

The candidate had no remotes and passed `git fsck --full --no-reflogs` with no
output. The source had 8,248 reachable commits and the candidate had 11,968.
The increase is explained operationally by retaining rewritten branch history
alongside the repository's pull-request refs; it is not Git object corruption
or an LFS payload requirement. A remote run must use the recorded ref map and
explicitly reconcile the two added candidate heads before publication.

## PR #581 Impact

Read-only GitHub inspection found PR #581 open and ready for review, with head
`codex/canonical-evidence-manifest-579` and base `main`. Both the candidate
head ref and its base ancestry change in the rewrite map. The PR must therefore
be merged, closed, rebased, or recreated as part of a separately coordinated
remote rewrite; this task made no PR change.

## Remaining Remote Prerequisites

- Decide and document the disposition of open PR #581.
- Back up or otherwise account for the 547 locally unavailable LFS payloads
  before any destructive remote operation.
- Reconcile the two additional candidate heads and apply the recorded ref map
  deliberately.
- Coordinate branch protection, signatures, tags, collaborators, re-clones,
  cache/CDN handling, and any GitHub Support purge request.
- Obtain a new, explicit authorization for remote history mutation.

## Recommendation

The local technical proof is sufficient to hold the remote action behind the
remaining coordination and preservation gates. This task does not recommend a
remote rewrite, force push, or release action.

## Explicit Non-Actions

No remote mutation, force push, branch-protection change, PR #581 mutation,
tag rewrite, working-repository rewrite, LFS payload download, tool install or
upgrade, authentication-flow test, or runtime/configuration edit occurred.

Recommendation: HOLD
