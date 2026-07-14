# Structural Signature Impact of the Credential-History Rewrite

## Purpose

This report records a local structural audit of commit and annotated-tag
signature impact from the exact combined credential-history rewrite. It
identifies embedded signature material and its disposition without treating
local signer trust configuration as authoritative and without authorizing
publication.

## Scope

- All commits reachable from current `refs/heads/*` and `refs/tags/*`.
- Embedded commit signature headers, recognized signature formats, and
  `mergetag` headers.
- Annotated-tag message-body signature material.
- Source-to-candidate commit mapping from filter-repo's commit map.
- No LFS analysis, branch-decision analysis, publication planning, signature
  recreation, cryptographic trust decision, or remote mutation.

## No-Mutation Guarantee

The source and candidate were disposable bare repositories with no configured
remotes after source construction. The working repository was not rewritten.
No branch, tag, branch protection rule, pull request, or remote ref was changed.

## Remote Baseline

Fresh remote `main`: `179d80207434ecde3c224e8e2425feffda9351ce`.

The heads-and-tags source was fetched directly from the public remote URL with
explicit branch and tag refspecs. Its `refs/heads/main` matched the fresh remote
`main` SHA.

## Open Pull Request Observation

PR #586 was observed read-only and remained open, non-draft, and mergeable.

| Field | Observed value |
| --- | --- |
| Number | 586 |
| State | OPEN |
| Draft | false |
| Mergeable | MERGEABLE |
| Head ref | `codex/project-pulse-implementation-target-inspection` |
| Head SHA | `92459d33ded3837d6db61ddfc0c951caac7b0ad7` |
| Base ref | `main` |
| Base SHA | `179d80207434ecde3c224e8e2425feffda9351ce` |

PR #586 was not modified.

## Source Construction

The bare source contained only branch and tag refs and had no named remote.

| Metric | Source | Candidate |
| --- | ---: | ---: |
| Branch refs | 362 | 362 |
| Tag refs | 0 | 0 |
| Reachable commits | 8,198 | 8,118 |

## Combined Rewrite Method

The candidate was copied from the source and rewritten by exactly one
`git filter-repo` invocation using `--replace-text` and `--replace-message`
with the same private five-rule value-replacement map. The map was derived from
the known exposure commit, remained mode `600`, and was destroyed with the
disposable workspace. The private map file and historical values were not
printed.

## Ref-Name Preservation

Source and candidate ref-name sets were identical. Both contained 362 branch
refs, zero tag refs, and no unexpected ref namespace.

## Structural Signature Detection Contract

The auditor enumerated commits with `git rev-list --all` and read raw objects
through batched `git cat-file` processes. It classified `gpgsig`,
`gpgsig-sha256`, other signature-shaped multiline headers, and signature block
formats without retaining or printing signature payloads. `mergetag` was
classified separately from a commit's own signature.

Structural presence means signature bytes were embedded in a Git object. It
does not establish cryptographic validity, signer identity, trust, revocation
status, or publication safety.

## Commit Mapping

Every reachable source commit had an explainable filter-repo mapping.

| Mapping measure | Count |
| --- | ---: |
| Reachable source commits | 8,198 |
| Reachable candidate commits | 8,118 |
| Mapping failures | 0 |
| Signed source commits removed by a zero mapping | 0 |
| Unsigned source commits whose SHA changes | 7,314 |

Commit-map completeness: **PASS**.

## Source Commit-Signature Inventory

| Structural measure | Count |
| --- | ---: |
| Source commits with `gpgsig` | 725 |
| Source commits with `gpgsig-sha256` | 0 |
| Other signature-shaped multiline headers | 0 |
| Source commits with any embedded signature | 725 |
| OpenPGP-signed source commits | 690 |
| SSH-signed source commits | 35 |
| X.509-signed source commits | 0 |
| Unknown-format signed source commits | 0 |

## Rewritten Commit-Signature Impact

| Impact measure | Count |
| --- | ---: |
| Signed source commits with unchanged SHA | 0 |
| Signed source commits with changed SHA | 725 |
| Signed source commits removed | 0 |
| Rewritten signed commits retaining signature material | 0 |
| Rewritten signed commits losing signature material | 725 |
| Rewritten signed commits with different signature bytes | 0 |
| Rewritten signed commits with byte-identical signature bytes | 0 |

All 725 signature-bearing source commits map to changed candidate commits whose
raw headers contain no embedded commit-signature material. The original
signatures are therefore not preserved. No retained signature-looking bytes
were interpreted as valid.

## Merge-Tag Findings

Source commits containing `mergetag` headers: **0**. No embedded signed-tag
evidence was found through commit merge-tag headers.

## Annotated Tag-Signature Inventory

The current ref set contains no tags, so no current tag-signature impact exists.

| Tag measure | Count |
| --- | ---: |
| Total tag refs | 0 |
| Lightweight tag refs | 0 |
| Annotated tag objects | 0 |
| Signed annotated tag objects | 0 |
| Unsigned annotated tag objects | 0 |
| Signed OpenPGP tags | 0 |
| Signed SSH tags | 0 |
| Signed X.509 tags | 0 |
| Signed unknown-format tags | 0 |
| Tag refs whose target changes | 0 |
| Signed tag refs whose target changes | 0 |
| Signed tag object IDs that change | 0 |
| Signed candidate tags retaining signature material | 0 |
| Signed candidate tags losing signature material | 0 |
| Tag mapping failures | 0 |

## Local Verification Limitations

Optional local `git log --all --format='%H %G?'` collection exited successfully
for both repositories but reported `N` for all 8,198 source commits and all
8,118 candidate commits. That local result conflicts with the 725 raw source
objects containing `gpgsig` headers and was therefore treated only as evidence
of this environment's verification limitation. No external keyserver, trust
store, signing key import, signer-trust decision, or independent cryptographic
verification was used.

The batched raw-object structural audit is authoritative for this report.

## Git Integrity

- Source: `git fsck --full --no-reflogs` — **PASS**, with no reachable
  Git-object errors.
- Candidate: `git fsck --full --no-reflogs` — **PASS**, with no reachable
  Git-object errors.

## Expected Rewritten Main

The current disposable candidate's expected rewritten `main` SHA is:

`62dd453b5d14bf2dcbb6faa235fd586ecbc41109`

This is a candidate SHA only. Neither the working repository nor any remote ref
was updated to it. It differs from the earlier candidate recorded by the prior
proofs because the fresh heads-only ref surface changed while remote `main`
remained stable; filter-repo's empty-commit pruning can therefore produce a
different current candidate graph. This report records the fresh exact run and
does not reinterpret the earlier proof artifact.

## Required Human Decision

Publication requires an explicit decision to either accept loss of the 725
original commit signatures or recreate approved signed commits through a
separate controlled process. This audit does not make that decision. No signed
tag decision is currently required because the current ref set contains no
tags.

## Result

The structural audit completed, every signature-bearing commit was mapped and
classified, mappings were complete, and both repositories passed Git integrity
checks. Because 725 signed commits are rewritten and lose signature material,
the publication gate requires a human decision.

## Deferred Proof Tasks

- Human acceptance or rejection of commit-signature loss.
- Recreation of approved signed commits or tags.
- Unique-history branch appendix.
- Human branch preservation and retirement decisions.
- Branch-protection procedure.
- Publication command generation.
- Remote history mutation.

## Explicit Non-Actions

- No signature was recreated, resigned, or cryptographically verified.
- No signing key was imported and no Git signing configuration changed.
- No LFS audit or payload download occurred.
- No working-repository history or remote ref changed.
- No pull request, including PR #586, was modified.
- No publication or force-push command was generated.
- No credential value, fingerprint, raw object dump, or complete signature
  block was printed or committed; no replacement expression was committed.

Result: SIGNATURE_DECISION_REQUIRED
