# LFS payload preservation for history remediation

## Purpose

This report records a read-only attempt to preserve and independently verify
every LFS payload referenced by the current remote repository before any future
credential-history rewrite. It neither authorizes nor performs a history
rewrite.

## Prior Proof State

The previous no-push proof established an LFS-safe local `--replace-text`
rewrite candidate: historical values were absent from the candidate, Git object
integrity passed, and its pointer `(object ID, declared size)` set matched the
source. That proof remained `HOLD` because most payloads had not been preserved
locally.

## No-Mutation Guarantee

This task used a fresh no-smudge clone in operator-owned Codexify
history-remediation storage. It fetched data from `origin` but did not push,
force-push, rewrite Git history, alter remote refs, change LFS pointer files,
or modify PR #581.

## Remote Baseline

Remote `main` resolved to `d1436c38cbec7759e45ebae76d87f060bcb1342e`.
The fresh clone's `origin/main` resolved to the same commit and passed `git
fsck --full --no-reflogs` with no output.

## Tool Versions

| Tool | Observed version |
| --- | --- |
| Git | 2.50.1 (Apple Git-155) |
| Git LFS | 3.7.1 |
| Python | 3.14.4 |
| tar | bsdtar 3.5.3 |
| SHA-256 | Python `hashlib.sha256` |

## Reachable LFS Pointer Inventory

The current remote-reachable inventory contains 551 pointer blobs representing
549 distinct LFS object IDs, with zero malformed pointers. This differs from
the preceding proof's 553 pointer blobs and 551 object IDs because the remote
ref baseline changed; this report uses the fresh inventory rather than assuming
the prior count.

## Declared Payload Size

The 549 distinct current objects declare a total of 374,033,177 bytes.

## Disk Capacity Preflight

The required capacity was 11,111,451,417 bytes, using
`max(total * 2.25, total + 10 GiB)`. Available capacity was 71,789,084,672
bytes, so the download was authorized to proceed.

## LFS Fetch Result

`git lfs fetch --all origin` exited 0. That status was not treated as proof of
completeness; every object was subsequently located, sized, and hashed against
the canonical reachable-pointer inventory.

## Independent Payload Verification

The independent verifier found 520 present payloads and 29 missing payloads.
All 520 present payloads matched their declared size and SHA-256 object ID.
There were zero size mismatches, zero SHA-256 mismatches, and zero duplicate
storage paths. Verified bytes totalled 147,390,671.

Because the required all-object condition failed, no preservation archive was
created and this task cannot close the payload-preservation prerequisite.

## Git LFS Cross-Check

`git lfs fsck --pointers` exited 0. `git lfs fsck --objects` also exited 0.
Those commands are supporting evidence only: they did not detect the 29 objects
missing from the all-reachable inventory. The independent verifier is the
authoritative completeness check for this task.

## Preservation Archive

No archive was created. Archive creation is prohibited until every referenced
payload is present and cryptographically verified.

## Archive Digest

Not available: no archive, archive metadata, or archive digest was created.

## Restore Verification

Not run: restore verification requires a complete preservation archive.

## Secret-Metadata Scan

Exact historical-value scanning passed for the retained pointer inventory,
payload manifest, and sanitized report data. A credential-assignment pattern
scan also passed. Payload contents were not scanned; object-hash verification
is the relevant preservation proof for payload binaries.

## PR #581 Observation

PR #581 remains open, non-draft, and mergeable. Its head is
`codex/canonical-evidence-manifest-579` at
`5e6a01b1b33170a851322f47a22987ff65e1da0c`; its base is `main` at
`d1436c38cbec7759e45ebae76d87f060bcb1342e`. It has two commits and five
files. PR disposition remains a separate prerequisite for remote rewriting.

## Remaining History-Rewrite Prerequisites

- Retrieve and independently verify the 29 missing current-reachable payloads.
- Create and restore-verify a complete external preservation archive.
- Dispose of or coordinate PR #581.
- Reconcile candidate refs, including pull-request-ref publication decisions.
- Coordinate branch protection, signatures, collaborator re-clones, caches,
  notification, and any GitHub Support purge request.
- Obtain explicit authorization for a separate remote-rewrite operation.

## Recommendation

The preservation archive gate is incomplete. A zero exit from `git lfs fetch
--all` did not establish all-reachable payload availability, so remote history
rewriting remains unauthorized.

## Explicit Non-Actions

No archive, archive digest, restore check, remote mutation, history rewrite,
force push, branch-protection change, PR #581 change, runtime change, or
credential value disclosure occurred. The retained partial external run is not
a complete preservation archive.

Recommendation: HOLD
