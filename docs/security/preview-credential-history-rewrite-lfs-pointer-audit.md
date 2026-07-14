# Dual LFS Pointer Audit for the History-Rewrite Candidate

## Purpose

This report records a local-only, disposable-mirror proof that the exact
combined blob-and-message rewrite preserves the complete reachable Git LFS
pointer surface without malformed pointers, missing pointer records, changed
object IDs, changed declared sizes, or unrelated path drift. It is evidence for
a separately authorized remote-remediation task, not an authorization to
perform one.

## Scope

- All reachable LFS pointer blobs from `refs/heads/*` and `refs/tags/*` refs in
  both the source and the combined-rewrite candidate.
- Valid LFS pointer parsing: canonical version, SHA-256 OID, declared size, and
  optional `ext-*` extension records.
- Malformed pointer detection and classification.
- Complete normalized surface comparison: pointer blob SHAs, LFS object IDs,
  declared sizes, pointer-to-path associations.
- The targeted example file (`.env.private-preview.example`) LFS status.
- No LFS payload download, extraction, inspection, or modification.
- No signature analysis, branch classification, publication planning, or remote
  mutation.

## No-Mutation Guarantee

All rewrite and audit work occurred in disposable bare repositories with no
configured remotes. No ref was pushed, force-pushed, deleted, retargeted, or
otherwise changed outside those mirrors. The working repository was not
rewritten. No remote ref was changed. The operator-owned LFS preservation
archive was not modified.

## Remote Baseline

Fresh remote `main` SHA: `179d80207434ecde3c224e8e2425feffda9351ce`.

## Open Pull Request Observation

PR #586 is currently open, non-draft, and mergeable:

| Field | Value |
| --- | --- |
| Number | 586 |
| State | OPEN |
| Draft | false |
| Mergeable | MERGEABLE |
| Head ref | `codex/project-pulse-implementation-target-inspection` |
| Head SHA | `92459d33ded3837d6db61ddfc0c951caac7b0ad7` |
| Base ref | `main` |
| Base SHA | `179d80207434ecde3c224e8e2425feffda9351ce` |

PR #586 was observed read-only and was not modified.

## LFS Preservation Digest Verification

The operator-owned LFS preservation archive and manifest were verified before
this analysis:

- Archive (`codexify-lfs-objects-complete.tar`) SHA-256:
  `12bd9abb12bc2e7e5149aa29da212e2c7047013f482a7317b6d95eb4bbee55e7`
  — **MATCHES**
- Payload manifest (`lfs-payload-manifest.json`) SHA-256:
  `3456231c2f062af2aaa7ada84764c77aefb722acd1281e0b3a84d9d15c106511`
  — **MATCHES**

Both digests match the recorded values. The archive was not extracted or
modified.

## Source Construction

A fresh bare source repository was initialized with no remotes and fetched from
the upstream remote URL using only `refs/heads/*` and `refs/tags/*` refspecs.
The source `refs/heads/main` SHA matches the observed remote `main`.

Source contains exactly:

- 362 branch refs under `refs/heads/*`;
- 0 tag refs under `refs/tags/*`.

No other ref namespaces are present. Source Git integrity passed
(`git fsck --full --no-reflogs` with no errors).

## Combined Rewrite Method

One `git filter-repo` invocation using two authorized replacement options from
the same private replacement map derived from the known exposure commit
(`4d783762101f75e1c1230e2b82413a8da2580ef9`:
`.env.private-preview.example`):

- `--replace-text` (blob content replacement);
- `--replace-message` (commit message and tag message replacement).

The candidate was copied from the source and had its remote removed before
rewrite. The candidate had no configured remote. The rewrite completed
successfully.

## Ref-Name Preservation

Source and candidate ref-name sets are identical. All 362 ref names are
preserved. No extra candidate heads were introduced.

## Pointer Parser Contract

An independent Python auditor was created for this analysis. For every reachable
blob in each repository:

1. The blob is checked for the canonical LFS pointer version prefix:
   `version https://git-lfs.github.com/spec/v1`
2. Valid pointers are parsed to require exactly:
   - one canonical version record;
   - one `oid sha256:<64 lowercase hex characters>` record;
   - one non-negative numeric `size` record.
3. Optional `ext-*` extension records are accepted.
4. Malformed pointers are classified by failure category.

Per-object `git cat-file -p` calls are used for reliable content retrieval,
with object enumeration via `git rev-list --all --objects` and classification
via `git cat-file --batch-check`.

## Source Pointer Inventory

| Metric | Value |
| --- | --- |
| Total blobs inspected | 23,042 |
| Valid LFS pointer blobs | 551 |
| Distinct LFS object IDs | 549 |
| Distinct (OID, size) pairs | 549 |
| Total pointer-associated paths | 551 |
| Malformed pointers | 0 |
| Duplicate pointer records | 2 |
| Total declared payload bytes | 374,033,177 |

## Candidate Pointer Inventory

| Metric | Value |
| --- | --- |
| Total blobs inspected | 23,042 |
| Valid LFS pointer blobs | 551 |
| Distinct LFS object IDs | 549 |
| Distinct (OID, size) pairs | 549 |
| Total pointer-associated paths | 551 |
| Malformed pointers | 0 |
| Duplicate pointer records | 2 |
| Total declared payload bytes | 374,033,177 |

## Malformed Pointer Results

- Source malformed pointer count: **0**
- Candidate malformed pointer count: **0**

Both repositories contain zero malformed LFS pointers.

## Object-ID and Size Comparison

| Comparison | Result |
| --- | --- |
| Missing candidate pointer blobs | 0 |
| New candidate pointer blobs | 0 |
| Missing candidate LFS object IDs | 0 |
| New candidate LFS object IDs | 0 |
| Changed declared sizes | 0 |

The LFS object-ID set and declared-size mapping are identical between source
and candidate.

## Path and Pointer-Blob Comparison

| Comparison | Result |
| --- | --- |
| Missing candidate path records | 0 |
| New candidate path records | 0 |
| Changed path-to-pointer associations | 0 |

The complete `(path, pointer blob SHA, LFS object ID, declared size)` record
set is identical between source and candidate.

## Target File Classification

The targeted example file (`.env.private-preview.example`) was inspected in
both source and candidate. Neither begins with the canonical LFS pointer
version line.

- Source target is LFS pointer: `false`
- Candidate target is LFS pointer: `false`

## Git Integrity

- Source: `git fsck --full --no-reflogs` — **PASS** (no errors)
- Candidate: `git fsck --full --no-reflogs` — **PASS** (no errors)

## Expected Rewritten Main

The expected rewritten candidate `main` SHA is:

`9b06f79400c4933b808c98bf84f973923a011a85`

This SHA is the candidate tip only. No working repository or remote ref was
updated to this value.

## Result

| Check | Result |
| --- | --- |
| Source and candidate contain only heads and tags | PASS |
| Source and candidate ref-name sets identical | PASS |
| Exact combined rewrite reproduced (--replace-text + --replace-message) | PASS |
| Source malformed pointers | 0 |
| Candidate malformed pointers | 0 |
| Pointer blob sets identical | PASS |
| LFS object-ID sets identical | PASS |
| Declared-size mappings identical | PASS |
| Pointer path associations identical | PASS |
| Targeted example file is not an LFS pointer | PASS |
| Source Git integrity | PASS |
| Candidate Git integrity | PASS |
| LFS preservation digests valid | PASS |
| No remote mutation | PASS |
| No LFS payloads downloaded | PASS |
| PR #586 untouched | PASS |
| No credential values printed or committed | PASS |

Result: LFS_POINTER_AUDIT_PASSED

## Deferred Proof Tasks

- Structural signature analysis (signed commits and annotated tags).
- Unique-history branch appendix (branches with commits not reachable from
  `main`).
- Human branch-preservation decisions.
- Remote rewrite command generation.
- Branch-protection procedure.
- Signature recreation.
- Force-pushing refs.
- GitHub Support requests.
- Authentication-flow verification.

## Explicit Non-Actions

- No working-repository history was rewritten.
- No remote ref was changed.
- No branch protection was modified.
- No pull request was mutated (PR #586 remains untouched).
- No tag was created, deleted, or modified.
- No credential value was printed or committed.
- No LFS payload was downloaded or inspected.
- No preservation archive was extracted, modified, or altered.
- No tool, dependency, or interpreter was installed or upgraded.
- No authentication-flow test was performed.
- No runtime or configuration edit occurred.
