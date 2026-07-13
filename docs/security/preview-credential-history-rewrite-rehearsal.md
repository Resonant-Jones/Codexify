# Preview Credential History Rewrite Rehearsal

## Purpose

Record a no-push, local rehearsal of a possible Git-history remediation for
the published preview-credential exposure. This is a coordination and proof
artifact, not authorization to rewrite any remote ref.

## Incident Boundary

The known exposure is reachable from published commit
`4d783762101f75e1c1230e2b82413a8da2580ef9`. It includes three Guardian
credential classes and personal preview-address values in the tracked preview
example. Values are intentionally omitted from this report.

## Current Containment State

Active private credentials were rotated, affected tester backend and worker
containers were recreated, and the tester runtime recovered. PR #580
sanitized the public tip; its merge commit is
`d1436c38cbec7759e45ebae76d87f060bcb1342e`. The current tracked example
uses placeholders and generic addresses. Historical objects remain reachable
until a separately approved remote remediation occurs.

## No-Push Rehearsal Guarantee

All rewrite operations were confined to a temporary mirror clone with its
`origin` remote removed before the rewrite command was invoked. This task did
not push, force-push, delete refs, alter branch protection, modify pull
requests, or change the working repository's history.

## Tools and Versions

- Git: `2.50.1 (Apple Git-155)`
- Python: `3.14.4`
- GitHub CLI: `2.87.3`
- git-filter-repo: `a40bce548d2c`
- GitHub CLI authentication: available for inventory reads.
- git-filter-repo options: `--replace-text` and `--sensitive-data-removal`
  were available.

## Baseline Main and Known Exposure Commit

- `origin/main` at rehearsal start:
  `d1436c38cbec7759e45ebae76d87f060bcb1342e`
- Known exposure commit: `4d783762101f75e1c1230e2b82413a8da2580ef9`
- Public-tip containment merge is an ancestor of the baseline main tip.
- The exposure commit is also an ancestor of the baseline main tip.

## Remote Ref Inventory

The remote inventory contained 362 branch refs and no tag refs. The default
branch-protection endpoint was unavailable or reported no protection to this
inventory credential; a future execution must confirm the actual protection
posture directly with repository administrators.

## Open Pull Request Impact

One open pull request existed during inventory:

- #581, draft, head `codex/canonical-evidence-manifest-579`, base `main`.

Its eventual ancestry and GitHub diff behavior cannot be classified until a
successful rewritten-ref map exists. It needs an explicit disposition before
any remote execution.

## Branch and Tag Impact

The candidate ref set is high-impact because 362 branch refs were present.
No tag refs were present in the inventory, so no annotated-tag replacement was
identified from this run. Exact changed and unchanged ref lists are unavailable
because the required local rewrite did not complete.

## Fork and Clone Risk

The GitHub inventory returned zero forks at rehearsal time. Existing clones,
cached GitHub objects, pull-request references, mirrors, and any forks created
after inventory can still retain the exposed objects. A remote rewrite would
require mandatory re-clone instructions and stale-clone push prevention.

## Local Rewrite Method

A private replacement map was derived inside a mode-600 temporary directory
from the historical tracked file. The candidate used:

```text
git filter-repo --sensitive-data-removal --replace-text <private-map> --force
```

The command was executed only in the disconnected mirror. It failed while
parsing LFS metadata before producing a usable rewritten-ref map.

## Changed Refs

Not available. `git filter-repo` did not complete, so no trustworthy
`changed-refs` artifact was produced.

## First Changed Commits

Not available from filter-repo because the rewrite did not complete. The known
published exposure commit remains the manually confirmed incident anchor, but
it is not a substitute for filter-repo's first-changed-commit evidence.

## Commit and Object Counts

- Reachable commits before rewrite: 8,246.
- Commits containing one or more targeted historical values before rewrite: 24.
- Known exposure commit reproduced in the affected set: yes.
- Reachable commits after rewrite: not proven.
- Post-rewrite targeted-value match count: not proven.

## Signature Impact

The pre-rewrite signature-status scan covered 8,246 reachable commits, but
local signature verification was not usable: Git reported unavailable GPG or
SSH allowed-signers verification configuration. No signed-commit count,
signature-bearing descendant count, or tag-signature impact is proven.

Any remote rewrite must decide explicitly whether to preserve, recreate, or
retire signatures after obtaining a verifier-capable audit environment.

## LFS Impact

LFS evidence is incomplete. The source-mirror LFS integrity check failed, and
the mandatory sensitive-data-removal rehearsal then failed while parsing LFS
metadata. No conclusion is available about orphaned LFS objects or required
remote LFS cleanup.

## Sensitive-Value Verification

Exposure reproduction passed: 24 reachable commits matched one or more
private replacement targets, including the known exposure commit. Post-rewrite
absence verification is unavailable because the rewrite did not complete.

No historical values, replacement-map contents, browser tokens, API tokens,
or private environment contents are recorded here.

## Repository Integrity Verification

Not proven for a rewritten candidate because no successful rewritten candidate
was produced. The temporary rewrite mirror remained disconnected throughout.

## Rollback Requirements for a Future Execution

Before any remote rewrite, create an access-controlled encrypted rollback
bundle from a fresh mirror, record the expected rewritten-ref map, and define
an owner, timeout, and abort condition for restoration. The rollback bundle
must remain outside the repository and must not be created opportunistically
during a live rewrite window.

## GitHub Support Follow-Through

Prepare a separate GitHub Support request for server-side cached-object and
secret-scanning guidance after a successful local rehearsal. The request must
avoid including secret values and must not be submitted until a human has
approved the remote execution plan.

## Collaborator Re-Clone Requirements

All collaborators must stop pushing from stale clones before a rewrite. After
execution, they must re-clone or perform the approved hard reset procedure,
verify the rewritten default tip, and avoid reintroducing old objects through
force pushes or branch restoration.

## Remote Execution Prerequisites

| Prerequisite | Status | Notes |
| --- | --- | --- |
| Repository write freeze window | not ready | Requires owner-scheduled window. |
| Collaborator notification | not ready | Requires explicit distribution and acknowledgement. |
| Clean fresh mirror clone | not ready | Must be recreated after the LFS/parser issue is resolved. |
| Access-controlled rollback bundle | not ready | Must be prepared and tested under a separate approval. |
| Branch-protection adjustment plan | not ready | Protection posture was not proven by inventory. |
| Exact expected rewritten ref list | not ready | Rewrite did not produce a ref map. |
| Open pull-request disposition plan | not ready | Draft PR #581 needs an owner decision. |
| Signed-commit and signed-tag decision | not ready | Signature verification was unavailable. |
| Fork/recontamination warning | ready | Zero forks were inventoried; clone/cache risk remains. |
| Mandatory re-clone instructions | not ready | Must be approved and distributed before execution. |
| Stale-clone push prevention | not ready | Requires freeze and branch-protection coordination. |
| GitHub Support request preparation | not ready | Depends on a successful rewrite map and human approval. |
| Post-rewrite secret scan | not ready | Requires a successful candidate rewrite. |
| Post-rewrite public-tip verification | ready | Current public tip was independently sanitized by PR #580. |
| Incident record and audit trail | ready | This rehearsal records the current blocker and boundary. |
| Rotation proof retained outside Git history | ready | Rotation was completed during containment. |
| Explicit final human authorization | not ready | Required for any remote ref mutation. |

## Recommendation

Do not attempt remote remediation until the filter-repo/LFS parser failure is
reproduced and resolved in a clean audit environment, signature and protection
posture are classified, and an exact rewritten-ref map plus rollback plan
exist. A future approval must be task-specific; successful local proof would
not itself authorize a force push.

## Explicit Non-Actions

- No remote refs were changed.
- No force push, mirror push, branch deletion, pull-request modification, or
  branch-protection change occurred.
- No local working-repository history was rewritten.
- No runtime, environment, frontend, backend, Compose, Tailscale, or
  dependency file was modified.
- No authentication or tester workflow verification was resumed.
- No temporary mirror, replacement map, fingerprint data, raw inventory, or
  bundle is retained as a repository artifact.

Recommendation: NEXT_PROOF_NEEDED
