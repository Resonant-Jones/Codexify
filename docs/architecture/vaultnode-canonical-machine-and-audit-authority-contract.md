# VaultNode Canonical Machine and Audit Authority Contract

## Purpose

Translate [ADR-041](./adr/041-vaultnode-canonical-machine-and-audit-authority.md)
into precise operational rules for agents, operators, audit tooling, and future
automation. The contract makes authority, provenance, freshness, and promotion
boundaries explicit without claiming that the enforcing runtime exists today.

## Scope

This contract covers Codexify code-head authority, runtime and audit machine
roles, canonical and provisional evidence, trusted `latest`, checkout and
Compose identity, and evidence promotion. It applies to audit automation,
proof generation, Guardian Work Brief generation, beta sentinel behavior,
VaultNode schedules, and multi-machine audit behavior once those surfaces are
implemented against this contract.

This is a documentation contract. It does not add runtime tokens, a registry,
JSON validation, schedules, Compose configuration, service files, or evidence
migration.

## Canonical terminology

| Term | Contract meaning |
|---|---|
| `canonical_evidence_host` | VaultNode, the sole machine authorized to produce and advance canonical runtime/audit evidence. |
| `provisional_development_host` | Any other machine that may develop, test, and produce provenance-preserving provisional evidence but may not advance canonical `latest`. |
| Code authority | GitHub `main` as the accepted source for code, documentation, schemas, and contracts. |
| Runtime/audit authority | VaultNode as the only canonical execution origin for runtime and audit proof. |
| Accepted evidence | Evidence that satisfies eligibility, covers an identified accepted head/configuration, and passes the applicable human-selected threshold. |
| Canonical `latest` | The newest accepted VaultNode evidence for an identified clean commit and canonical audit configuration, not the newest timestamp. |
| Provisional evidence | Evidence from a noncanonical host or otherwise unaccepted run; useful for development and review, but not canonical proof. |
| Historical evidence | Prior evidence retained for context that is not asserted to cover the current `main` head. |
| Stale `latest` | Canonical `latest` that does not cover the current accepted `main` head or cannot be shown to match the required configuration. |
| Promotion | An explicit, reviewable act that makes eligible VaultNode evidence the canonical `latest`; generation alone is not promotion. |

These role names are vocabulary for contracts and future automation. They are
not new runtime protocol tokens or registry entries in this task.

## Authority table

| Surface | Authority | What it may decide | What it may not decide |
|---|---|---|---|
| Accepted source state | GitHub `main` | Accepted code, docs, schemas, and contracts | Whether a runtime proof exists for that source state |
| Canonical execution | VaultNode | Origin of canonical runtime and audit observations | Human campaign approval or capability posture |
| Evidence disposition | Resonant Jones, using the defined proof threshold | Findings, thresholds, capability posture, campaign, and priorities | Nothing is delegated to automation merely because it generated a report |
| Automation | The future approved audit/promotion path | Checks, captures, compares, and recommends | Self-certification, approval, silent failover, or unsupported claim promotion |
| Other machines | Local operator/developer | Development and provisional validation | Canonical `latest` advancement or canonical authority failover |

## Machine-role contract

### `canonical_evidence_host`

The `canonical_evidence_host` role is assigned to VaultNode. A canonical run
must prove that the producing machine is VaultNode and must capture enough
identity to distinguish the host from its checkout, worktree, Compose project,
and configuration.

VaultNode must remain available for the persistent Codexify serving runtime,
but persistent availability does not make every serving-runtime observation a
clean audit result. Audit runs still require the separate checkout and runtime
boundaries below.

### `provisional_development_host`

The `provisional_development_host` role applies to all other machines unless a
future architecture decision changes the authority model. It can generate
useful results, but every result must be labeled with its own machine and
provenance. It may not write, replace, relabel, or promote canonical `latest`.

## Canonical evidence eligibility

Evidence is eligible for canonical consideration only if it is produced on
VaultNode and identifies the accepted source and execution context. At
minimum, an evidence record must capture:

- machine identity;
- machine role;
- repository root;
- branch;
- commit SHA;
- upstream SHA;
- dirty state;
- worktree identity;
- supported profile;
- effective configuration identity or hash;
- Compose project identity when runtime proof is involved;
- command or proof suite;
- start timestamp;
- completion timestamp;
- result;
- artifact paths;
- artifact hashes; and
- supported, disproved, and unresolved claims.

Eligibility also requires that the record can be associated with a clean,
identified checkout and that the referenced artifacts remain available for
review. A green command exit or generated report is not sufficient by itself.

The precise JSON schema, field types, enumerations, validation rules, and
promotion receipt shape are deferred to the Canonical Audit Evidence Contract
task.

## Provisional evidence rules

Evidence from a `provisional_development_host` may be:

- used to find defects or prioritize a proof;
- attached to a review or campaign packet as provisional input;
- compared with canonical evidence; and
- retained as historical context with its provenance intact.

It may not:

- advance canonical `latest`;
- overwrite or delete the last accepted canonical artifact;
- be described as VaultNode proof;
- be used to claim current-head coverage without VaultNode revalidation; or
- silently change the canonical capability or release posture.

## Trusted `latest` contract

Consumers must interpret canonical `latest` as a pointer to the newest
accepted VaultNode evidence for an identified clean commit and canonical audit
configuration. Consumers must not infer trust from a filename, mtime, report
date, directory location, or generated summary.

The contract requires:

1. Commit coverage is explicit. A new `main` SHA has no inherited proof.
2. Configuration coverage is explicit. A changed supported profile or effective
   configuration invalidates unqualified freshness.
3. Current-head freshness is visible. If coverage is absent, `latest` is stale.
4. Failure is non-destructive. A failed or blocked audit preserves the last
   accepted artifact and records the new failure separately.
5. Authority is explicit. Only accepted VaultNode evidence may advance the
   canonical pointer.
6. Summaries are derived. Documentation checkboxes and generated reports may
   explain evidence but cannot independently certify or promote it.

Local `latest` files may exist for convenience. They are machine-scoped and
must be labeled or interpreted as provisional unless they satisfy the
canonical promotion path.

## Required identity fields

The required identity fields are intentionally listed as contract concepts,
not as an implemented schema:

| Field | Why it is required |
|---|---|
| Machine identity and role | Distinguishes VaultNode authority from provisional hosts. |
| Repository root | Prevents similarly named checkouts from being conflated. |
| Branch, commit SHA, upstream SHA | Establishes accepted-head and upstream coverage. |
| Dirty state and worktree identity | Prevents a dirty or ambiguous checkout from being treated as clean proof. |
| Supported profile | Establishes which supported posture was evaluated. |
| Effective configuration identity/hash | Detects configuration drift not visible in the branch or SHA. |
| Compose project identity | Separates persistent serving and audit runtime proof. |
| Command/proof suite | Identifies what was actually executed. |
| Start/completion timestamps | Establishes execution interval and supports freshness review. |
| Result | Separates accepted, failed, blocked, and other future dispositions. |
| Artifact paths and hashes | Makes outputs reviewable and detects replacement or mutation. |
| Supported/disproved/unresolved claims | Preserves uncertainty and prevents absence from becoming an implicit pass. |

## Freshness and staleness

Freshness is a relation, not a timestamp. An evidence artifact is current-head
fresh only when its recorded commit SHA matches the accepted GitHub `main`
head under the required canonical profile and configuration, and when its
result remains accepted for the applicable proof threshold.

`latest` must be visibly stale when:

- the accepted `main` SHA is newer than the evidence SHA;
- the upstream SHA or branch relationship is unknown or mismatched;
- the worktree was dirty or cannot be shown to be the intended clean worktree;
- the supported profile or effective configuration changed;
- the evidence result is failed, blocked, or unresolved for the required gate;
- VaultNode has not been reachable for a required revalidation; or
- the artifact or its hash cannot be independently read back.

Staleness does not erase evidence. It changes how the evidence may be used.

## Supersession and contradiction handling

Evidence records are superseded by a newer accepted canonical record covering
the same decision scope. Supersession must preserve the older record for audit
history and must identify the newer record or reason for supersession.

Contradictory evidence must not be merged into a synthetic pass. When two
records disagree:

- preserve both records and their provenance;
- identify the differing commit, configuration, machine, runtime, command, or
  claim;
- classify the disagreement as unresolved until reviewed;
- do not advance canonical `latest` from the contradiction; and
- require a new or explicitly reviewed VaultNode proof to resolve it.

An audit failure does not supersede by deletion. It is a new observation that
may leave the prior accepted `latest` in place while making current coverage
stale or blocked.

## Runtime/audit topology

The minimum conceptual topology is:

```text
GitHub main  --->  clean audit checkout on VaultNode  --->  disposable audit runtime
      \                                      \
       \                                      +--> evidence artifacts and hashes
        +--> persistent serving checkout on VaultNode ---> persistent serving runtime
```

The serving and audit paths have separate responsibilities:

- The persistent serving runtime remains continuously available and owns its
  serving state.
- The audit checkout is selected from an accepted head and is not implicitly
  the serving checkout.
- The audit Compose project has an identity distinct from the persistent
  serving project.
- Runtime proof must record the audit Compose project identity.
- Audit cleanup, volume policy, exact paths, and deployment commands are
  deferred implementation details.

## Promotion workflow

The future promotion workflow must be explicit and reviewable:

1. Resolve the accepted GitHub `main` head and supported profile.
2. Confirm VaultNode identity and the availability of the canonical audit lane.
3. Materialize or select the clean audit checkout without using the serving
   checkout automatically.
4. Run the named proof suite in the distinct audit runtime.
5. Capture all required identity, configuration, timing, result, claim, and
   artifact-integrity fields.
6. Compare the result with the current canonical `latest` and preserve any
   contradiction or failure.
7. Apply the human-selected proof threshold and decision.
8. Promote only accepted evidence to canonical `latest`; otherwise leave the
   previous accepted artifact intact and expose stale/blocked status.

No step may treat report generation, pointer replacement, or a successful
subprocess exit as approval by itself.

## Failure behavior

| Failure | Required behavior |
|---|---|
| VaultNode unavailable | Do not advance canonical `latest`; preserve the last accepted artifact; allow only provisional work elsewhere. |
| GitHub `main` moved | Treat prior evidence as non-current for the new SHA until exact-head proof exists. |
| Dirty or ambiguous audit checkout | Evidence is ineligible for canonical promotion; do not guess. |
| Configuration/profile mismatch | Mark coverage stale or invalid for the requested scope; do not inherit prior proof. |
| Audit fails or blocks | Preserve the last accepted artifact and record the new result separately. |
| Artifact missing or hash mismatch | Treat evidence as unresolved/ineligible until readback is repaired. |
| Contradictory machine results | Preserve both; classify unresolved; require reviewed VaultNode proof. |
| Serving/audit identity collision | Stop or fail closed; do not claim clean audit proof. |

## Agent behavior

Agents working on audit, proof, reports, or Work Briefs must:

- read `00-current-state.md`, ADR-041, and this contract before changing an
  authority-sensitive surface;
- distinguish GitHub `main` code authority from VaultNode runtime/audit
  authority;
- record the actual machine, checkout, head, dirty state, profile,
  configuration, Compose identity, commands, timestamps, results, artifacts,
  and unresolved claims when producing future evidence;
- treat non-VaultNode evidence as provisional or historical;
- keep failed or blocked results visible without deleting the last accepted
  artifact;
- mark `latest` stale when current-head coverage is absent;
- refuse silent canonical failover when VaultNode is unavailable; and
- never claim that a documentation checkbox, generated summary, route
  presence, or successful enqueue is independent proof of the underlying
  runtime claim.

Agents must stop at the documentation/contract boundary when a requested
follow-up requires schema, runtime, schedule, Compose, service, CI, or
automation changes outside the task scope.

## Security and secret-handling boundary

Evidence must identify configuration and runtime posture without exposing
secrets. Future implementations must prefer stable configuration identities or
redacted hashes over raw environment values, API keys, session secrets,
credentials, tokens, private prompt content, or sensitive user data.

Machine identity and artifact provenance are audit metadata, not permission to
read arbitrary host state. Capability-based access, least privilege, explicit
mounts, and separate service credentials remain required implementation
concerns. Audit artifacts must not become a covert secret-export channel.

## Deferred implementation work

The following work is intentionally deferred:

- precise Canonical Audit Evidence JSON schema and validator;
- machine-role and identity capture implementation;
- clean audit checkout materialization and lifecycle;
- configuration identity/hash computation and redaction policy;
- separate persistent-serving and audit Compose projects;
- canonical `latest` pointer, freshness, staleness, and non-destructive
  promotion behavior;
- promotion receipts and human decision capture;
- Guardian Work Brief and beta sentinel integration;
- VaultNode schedules and service management;
- reconciliation or migration of existing audit/proof artifacts; and
- tests or runtime proofs for the above implementation.

## Non-goals

This contract does not:

- implement an evidence schema, generator, validator, reducer, or registry;
- change existing audit scripts, Work Brief behavior, beta sentinel behavior,
  schedules, or `latest` files;
- modify Docker Compose, services, launch agents, CI, GitHub automation, or
  deployment paths;
- certify or migrate existing artifacts;
- grant non-VaultNode machines canonical authority;
- introduce automatic failover;
- approve campaigns, findings, capabilities, or releases; or
- widen Codexify's current supported runtime claim.
