# LFS payload recovery and preservation closure

## Purpose

This report closes the current-reachable LFS preservation gate through a fresh
inventory, independent payload verification, external archive creation, and
restore verification. It does not authorize any remote history rewrite.

## Prior Preservation State

The preceding preservation report recorded 549 distinct reachable objects, 551
pointer blobs, and a 29-payload availability gap after `git lfs fetch --all`.
Its independent verifier accepted 520 payloads and found no size or SHA-256
mismatches among those present. No archive was created at that time.

## No-Mutation Guarantee

This task used read-only remote metadata and LFS operations plus operator-owned
Codexify history-remediation storage. It did not push, force-push, rewrite
history, alter remote refs, edit LFS pointers, or modify PR #581.

## Remote Baseline

Remote `main` remained
`d1436c38cbec7759e45ebae76d87f060bcb1342e`. PR #581 remained an independent
open dependency throughout this work.

## Missing Object Inventory

The initial retained evidence recorded 29 missing objects. A fresh current
inventory again contained 549 distinct objects and 551 pointer blobs, with zero
malformed pointers and 374,033,177 declared payload bytes. Reverification of
that complete current set found 549 present and zero missing objects.

The retained earlier run had preserved the aggregate missing count but not a
durable per-object missing-ID list. Consequently, the former 29-object set
cannot be attributed retrospectively to a specific object-level recovery
source. No current-reachable object was silently excluded from the archive.

## Exact Ref Reachability Method

The current inventory enumerated all `refs/remotes/origin/*` refs and tags,
then inspected reachable pointer blobs for canonical version, SHA-256 object
ID, and declared size records. This produced the authoritative current scope.
Because the current missing set is empty, there are zero missing-object path or
ref mappings to classify.

## Targeted GitHub LFS Recovery

The installed Git LFS fetch help did not expose object-ID-directed fetch
support, so no object-specific remote command was attempted. Targeted remote
recovery count: 0.

## Authorized Local Cache Sources

Only the approved categories were inspected for LFS object-store shapes: the
current repository common directory, `/Volumes/Dev_SSD`, and operator-owned
history-remediation storage. Four stores were discovered privately. No payload
contents were inspected during discovery.

## Local Cache Recovery

No payload was copied from a local cache because the refreshed preservation
source clone already contained every current-reachable object. Local-cache
recovery count: 0.

## Independent Verification

The authoritative verifier found 549 expected and 549 present objects, zero
missing objects, zero size mismatches, zero SHA-256 mismatches, and
374,033,177 verified bytes. Every accepted payload's SHA-256 matched its LFS
object ID.

## Remaining Missing Objects

None in the current reachable inventory.

## Reachability Classification

Current missing-object classification counts are all zero: `main_reachable`,
`open_pr_reachable`, `active_branch_reachable`, `stale_branch_only`,
`tag_reachable`, `multi_ref`, and `reachability_unknown`.

## Affected Ref Classes

No current ref reaches an unavailable payload. The former aggregate
29-object gap has no recoverable per-object ref map in the retained previous
metadata; this provenance limitation is recorded rather than inferred.

## Complete Archive Status

Complete archive created in operator-owned Codexify history-remediation
storage, run ID `20260713T204719Z`:
`codexify-lfs-objects-complete.tar`.

## Archive Digests

- Archive size: 377,916,928 bytes
- Archive SHA-256: `12bd9abb12bc2e7e5149aa29da212e2c7047013f482a7317b6d95eb4bbee55e7`
- Payload manifest SHA-256: `3456231c2f062af2aaa7ada84764c77aefb722acd1281e0b3a84d9d15c106511`
- Pointer inventory SHA-256: `afae5e4bbfe753b782a53264a844f93b2f1160c15c3a9a046d93340b66a170f3`
- Archive metadata SHA-256: `e52be6a961392f637d63fb8a4bf7d7036fd5b27c0d90fcff55eb5851308108ac`

## Restore Verification

The archive was extracted into a fresh private directory and independently
verified. It restored 549 expected objects with zero missing objects, zero
extra objects, zero size mismatches, and zero SHA-256 mismatches. Manifest,
pointer-inventory, and metadata digests all matched. The transient extraction
directory was removed; the verified archive and private records remain.

## Metadata Secret Scan

Exact historical-value scanning passed for the private worklist, inventory,
manifest, archive metadata, digest record, and sanitized report data. The
credential-assignment pattern scan also passed. Binary payload contents were
not scanned because cryptographic object identity is the preservation contract.

## PR #581 Observation

PR #581 is open, non-draft, and mergeable. Its head remains
`codex/canonical-evidence-manifest-579` at
`5e6a01b1b33170a851322f47a22987ff65e1da0c`; its base is `main` at
`d1436c38cbec7759e45ebae76d87f060bcb1342e`. It remains untouched and must be
disposed of or coordinated in a separate remote-rewrite task.

## Remaining Remote-Rewrite Prerequisites

- Decide the disposition of PR #581.
- Reconcile the prior rewrite candidate's changed refs and pull-request refs.
- Coordinate branch protection, signatures, collaborator re-clones, caches,
  notification, and any GitHub Support purge request.
- Obtain explicit authorization for a separate remote history rewrite.

## Recommendation

The current reachable LFS payload set is preserved, cryptographically verified,
archived outside the repository, and restore-verified. This closes the payload
preservation gate only; it does not authorize remote history mutation.

## Explicit Non-Actions

No remote rewrite, push, force push, branch deletion, branch retirement, PR
#581 change, runtime/configuration change, or credential disclosure occurred.

Recommendation: LFS_PRESERVATION_READY
