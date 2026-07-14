# Exhaustive History Secret Scan With Message Replacement

## Purpose

This report records a local-only, disposable-mirror proof that combined
`--replace-text` and `--replace-message` replacement removes all historical
rotated credential values from reachable blob contents, commit messages, and
annotated tag messages in a disposable candidate mirror. It is evidence for a
separately authorized remote-remediation task, not an authorization to perform
one.

## Scope

- Reachable blob contents from all `refs/heads/*` and `refs/tags/*` refs.
- Reachable commit messages from all heads and tags.
- Reachable annotated tag messages from all heads and tags.
- No LFS pointer analysis, signature analysis, branch classification,
  publication planning, or remote mutation.

## No-Mutation Guarantee

All rewrite and scan work occurred in disposable bare repositories with no
configured remotes. No ref was pushed, force-pushed, deleted, retargeted, or
otherwise changed outside those mirrors. The working repository was not
rewritten. No remote ref was changed.

## Remote Baseline

Fresh remote `main` SHA: `179d80207434ecde3c224e8e2425feffda9351ce`.

## Deterministic Source Construction

A fresh bare source repository was initialized with no remotes and fetched from
the upstream remote URL using only `refs/heads/*` and `refs/tags/*` refspecs.
The source `refs/heads/main` SHA matches the observed remote `main`.

## Exact Ref Namespace

The source contains exactly:

- 362 branch refs under `refs/heads/*`;
- 0 tag refs under `refs/tags/*`.

No other ref namespaces (pull refs, remote-tracking refs, backup refs, or
filter-repo temporary refs) are present.

Source ref-name set and candidate ref-name set are identical.

## Combined Rewrite Method

One `git filter-repo` invocation using two authorized replacement options from
the same private replacement map:

- `--replace-text` (blob content replacement);
- `--replace-message` (commit message and tag message replacement).

The private replacement map was derived from the known exposure commit
(commit `4d783762101f75e1c1230e2b82413a8da2580ef9`:
`.env.private-preview.example`).

The candidate was copied from the source and had its remote removed before
rewrite. The candidate had no configured remote.

## Source Exposure Reproduction

The fresh source was scanned across all 23,042 reachable blobs, 8,198
reachable commits, and 0 annotated tags using exact historical-value matching.

### Source historical match counts by category

| Category | Count |
| --- | --- |
| Credential-value blob matches | 7 |
| Address-value blob matches | 7 |
| Commit-message matches | 2 |
| Tag-message matches | 0 |
| Distinct matching blobs | 14 |
| Distinct matching commits | 2 |
| Distinct matching tags | 0 |

## Candidate Blob Scan

The disposable candidate was scanned across all reachable blobs for the same
historical credential and address values.

### Candidate blob match counts

| Category | Count |
| --- | --- |
| Credential-value blob matches | 0 |
| Address-value blob matches | 0 |
| Distinct matching blobs | 0 |

## Candidate Commit-Message Scan

The candidate was scanned across all reachable commit messages.

### Candidate commit-message match counts

| Category | Count |
| --- | --- |
| Commit-message matches | 0 |
| Distinct matching commits | 0 |

## Candidate Annotated-Tag Scan

The candidate was scanned across all reachable annotated tag messages.

### Candidate annotated-tag match counts

| Category | Count |
| --- | --- |
| Tag-message matches | 0 |
| Distinct matching tags | 0 |

## Ref-Name Preservation

Source ref-name set and candidate ref-name set are identical. All 362 ref
names are preserved. No extra candidate heads were introduced.

## Commit and Object Counts

| Metric | Source | Candidate |
| --- | --- | --- |
| Reachable commits | 8,198 | 8,118 |
| Branch count | 362 | 362 |
| Tag count | 0 | 0 |

The commit count reduction from 8,198 to 8,118 is operationally explained by
filter-repo collapsing commits whose content became identical after replacement;
it is not object corruption.

## Git Integrity

- Source: `git fsck --full --no-reflogs` completed with no reachable
  Git-object errors.
- Candidate: `git fsck --full --no-reflogs` completed with no reachable
  Git-object errors.

## Expected Rewritten Main

The expected rewritten candidate `main` SHA is:

`9b06f79400c4933b808c98bf84f973923a011a85`

This SHA is the candidate tip only. No working repository or remote ref was
updated to this value.

## Deferred Proof Tasks

- Dual LFS pointer comparison (source vs candidate).
- Structural signature analysis.
- Unique-history branch appendix (branches with commits not reachable from
  `main`).
- Human branch-preservation decisions.
- Remote rewrite command generation.
- Remote history mutation.

## Explicit Non-Actions

- No working-repository history was rewritten.
- No remote ref was changed.
- No branch protection was modified.
- No pull request was mutated.
- No tag was created, deleted, or modified.
- No credential value was printed or committed.
- No LFS payload was downloaded.
- No tool, dependency, or interpreter was installed or upgraded.
- No authentication-flow test was performed.
- No runtime or configuration edit occurred.

## Verification Summary

| Check | Result |
| --- | --- |
| Source exposure reproduced | PASS |
| Source has heads/tags only | PASS |
| Candidate has heads/tags only | PASS |
| Source and candidate ref names identical | PASS |
| Single filter-repo invocation with `--replace-text` and `--replace-message` | PASS |
| Candidate blob matches zero | PASS |
| Candidate commit-message matches zero | PASS |
| Candidate tag-message matches zero | PASS |
| Source Git integrity | PASS |
| Candidate Git integrity | PASS |
| No remote mutation | PASS |
| No credential values printed or committed | PASS |

Result: SECRET_SCAN_PASSED
