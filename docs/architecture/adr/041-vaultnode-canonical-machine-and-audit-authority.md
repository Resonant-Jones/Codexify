---
tags:
* architecture
* adr
* canonical-authority
* audit
* evidence
* vaultnode
  aliases:
* ADR-041
* VaultNode Canonical Machine and Audit Authority
---

# ADR-041: VaultNode Canonical Machine and Audit Authority

## Status

Accepted

## Date

2026-07-10

## Context

Codexify audit artifacts have been generated from multiple machines, worktrees,
commits, configurations, and Compose projects. Those sources are not
necessarily synchronized. Consequently, an artifact named or linked as
`latest` can describe a different repository state or runtime than another
artifact with the same label.

The larger Sol Baseline Recovery and Canonical Evidence Campaign needs an
authority model that separates code authority, runtime authority, evidence
promotion, and human decision-making. The model must remain truthful during
partitions and machine outages. It must also preserve the distinction between
the persistent runtime that serves Codexify and a clean, disposable runtime
used to perform an audit.

This ADR is architecture doctrine only. It does not make existing artifacts
canonical, and it does not imply that the current audit scripts, Work Brief
generator, sentinels, schedules, or `latest` pointers already enforce this
decision.

## Decision

Codexify adopts the following authority model:

- GitHub `main` is the canonical code authority for accepted code,
  documentation, schemas, and contracts.
- VaultNode is the only canonical runtime and audit authority. Canonical
  evidence must identify VaultNode as its producing machine.
- Other machines may develop, test, and produce provisional evidence, but they
  may not advance canonical `latest`.
- Resonant Jones remains the human decision authority for findings, proof
  thresholds, capability posture, campaigns, and implementation priorities.
  Audit automation may recommend and classify; it may not approve work or
  replace the human decision.
- The persistent serving runtime and the disposable clean audit runtime remain
  separate on VaultNode.
- VaultNode unavailability does not trigger silent canonical-authority
  failover.

The companion [VaultNode Canonical Machine and Audit Authority
Contract](../vaultnode-canonical-machine-and-audit-authority-contract.md) is
the operational interpretation of this decision for agents and future
automation.

## Authority hierarchy

Authority is scoped by question rather than collapsed into one undifferentiated
owner:

| Authority | Governing question | Boundary |
|---|---|---|
| Resonant Jones | What findings, thresholds, posture, campaign, or priority should be selected? | Human decision authority; automation cannot approve on this authority's behalf. |
| GitHub `main` | What code, documentation, schema, and contract state is accepted? | Canonical code authority; a local checkout is not accepted source merely because it is newer or cleaner. |
| VaultNode | What runtime and audit execution is canonical? | Sole canonical runtime/audit host; its machine identity must be present in canonical evidence. |
| Accepted VaultNode evidence | What was actually proven for a specific head and configuration? | Evidence authority is bounded to the identified commit, checkout, profile, configuration, proof suite, and timestamps. |
| Other machines | What development or validation was observed elsewhere? | Provisional or historical evidence only; no canonical `latest` promotion right. |

No generated report, documentation checkbox, or summary can elevate itself in
this hierarchy.

## Canonical machine role

VaultNode is the `canonical_evidence_host` for Codexify. It is the designated
machine for canonical runtime execution, canonical audit execution, and
promotion of accepted evidence to canonical `latest` once the future evidence
contract and human review gates are satisfied.

Canonical evidence produced on VaultNode must identify the machine, repository
root, branch, commit and upstream SHAs, worktree, supported profile, effective
configuration, and proof execution details. A file stored on VaultNode is not
canonical solely because of its location; it must satisfy the evidence
eligibility rules and remain tied to a known clean head and audit context.

## Noncanonical machine role

Every other machine is a `provisional_development_host` unless a future ADR
explicitly changes this decision. Such a machine may:

- develop against its own checkout;
- run tests, audits, and exploratory proofs;
- produce artifacts that preserve their own provenance; and
- submit observations for human review.

It may not advance VaultNode's canonical `latest`, overwrite canonical
evidence, or imply that its local `latest` is the Codexify canonical `latest`.
Its evidence remains provisional or historical until it is independently
revalidated and accepted through the canonical VaultNode path.

These role names are contract vocabulary only in this ADR. This task does not
add runtime tokens, registries, environment variables, or machine-discovery
behavior.

## Trusted `latest` semantics

`latest` means the newest accepted VaultNode evidence for an identified clean
commit and canonical audit configuration. It does not mean the artifact with
the newest filesystem or report timestamp.

The following rules are mandatory:

- A new GitHub `main` commit does not inherit the prior commit's proof.
- If canonical evidence does not cover the current `main` head, canonical
  `latest` is visibly stale and must not be presented as current-head proof.
- A failed or blocked audit must not erase the most recent accepted artifact.
- A timestamp, filename, symlink, generated summary, or documentation checkbox
  is insufficient to establish trusted `latest`.
- Generated reports may summarize evidence, but they may not certify their own
  claims or promote themselves.
- A local or provisional `latest` label is scoped to its producing machine and
  must not be confused with canonical `latest`.

The exact representation of stale state, accepted evidence, and promotion
receipts is deferred to the Canonical Audit Evidence Contract task.

## Runtime and audit checkout separation

VaultNode's persistent serving runtime and its clean audit runtime are distinct
operational surfaces:

- The serving runtime owns the continuously available Codexify service and its
  persistent state.
- The audit runtime is a clean, explicitly identified checkout and Compose
  project used to evaluate a selected head and configuration.
- The serving checkout must not be used automatically as the clean audit
  checkout.
- Audit execution must not silently mutate the persistent serving runtime,
  serving checkout, or its state.
- Exact checkout path names, deployment layout, and cleanup mechanics remain
  deferred implementation details.

## Compose identity expectations

When runtime proof is involved, the persistent serving Compose project and the
audit Compose project must have distinct identities. A future implementation
must make the selected project identity observable in evidence and must avoid
ambiguous container, network, volume, or service ownership between the two
surfaces.

This ADR does not select exact Compose project names, service names, volume
names, paths, override files, or deployment commands.

## Evidence promotion rules

Evidence may be considered for canonical promotion only when it is produced by
the canonical machine, tied to the accepted code head and canonical audit
configuration, clean at the relevant worktree boundary, and complete enough to
identify the proof command, result, artifacts, hashes, and claim disposition.
The future contract must also record unresolved claims instead of treating
absence as success.

Promotion is an explicit decision boundary:

1. Select an accepted GitHub `main` commit and supported profile.
2. Execute the clean audit on VaultNode with the persistent serving runtime
   kept separate.
3. Capture the required provenance and artifact integrity fields.
4. Preserve supported, disproved, and unresolved claims separately.
5. Apply the human-selected proof threshold and campaign decision.
6. Promote only accepted evidence to canonical `latest`.

Automation can perform checks and recommend a disposition. It cannot approve a
campaign, widen capability posture, certify a report, or promote evidence
without the authorized decision path defined by future implementation work.

## VaultNode-unavailable behavior

When VaultNode is unavailable:

- canonical `latest` does not advance;
- the last accepted canonical artifact remains preserved and identifiable;
- other machines may continue development, tests, and provisional
  validation;
- provisional artifacts must retain their producing-machine and provenance
  identity; and
- no machine silently assumes canonical runtime or audit authority.

An outage is therefore a stale-canonical-evidence condition, not permission for
implicit failover. Recovery requires a new VaultNode audit or an explicitly
approved change to this authority model.

## Consequences

Positive consequences:

- Canonical evidence has one runtime and audit origin.
- Code-head coverage and evidence freshness become explicit rather than
  inferred from timestamps.
- Persistent serving state is protected from accidental audit contamination.
- Machine partitions produce visible provisional or stale states instead of
  competing canonical realities.
- Human approval remains distinct from automated observation and recommendation.

Costs and tradeoffs:

- VaultNode availability becomes a prerequisite for advancing canonical proof.
- Canonical audits require more provenance and identity capture than a local
  convenience report.
- Other machines may have useful evidence that cannot be promoted directly.
- Separate serving and audit runtimes consume additional operational
  resources and require explicit cleanup and identity management.
- Existing `latest` files and generated reports require future reconciliation;
  this ADR does not retroactively certify them.

## Rejected alternatives

### Newest timestamp wins

Rejected because timestamps do not establish commit identity, clean state,
configuration identity, producing machine, or proof acceptance.

### Any healthy machine may become canonical

Rejected because silent failover would create competing authorities during
partitions and make canonical evidence dependent on unreviewed local state.

### GitHub `main` is also the runtime authority

Rejected because code acceptance and runtime/audit execution are different
truth surfaces. GitHub cannot by itself prove the state of the VaultNode
runtime, Compose project, local provider, or audit environment.

### The persistent serving checkout is the audit checkout

Rejected because a long-lived serving process, dirty state, persistent volumes,
and operator changes can contaminate clean audit claims.

### Generated summaries or checkboxes certify evidence

Rejected because a report must not be the independent authority for the claims
it summarizes. Evidence must be independently identified and reviewable.

## Implementation follow-through

Future implementation work must be separately scoped and must begin with the
companion contract. At minimum it will need to define and prove:

- the Canonical Audit Evidence Contract and precise JSON schema;
- canonical and provisional machine identity capture;
- clean checkout selection and worktree identity;
- effective configuration identity or hash capture;
- persistent-serving versus disposable-audit Compose isolation;
- accepted-head coverage and visible freshness/staleness behavior;
- append-only or otherwise non-destructive preservation of the last accepted
  artifact after failed audits;
- explicit evidence promotion and human decision receipts; and
- migration or reconciliation treatment for existing audit, proof, and Work
  Brief artifacts.

Those tasks may update the beta release sentinel, audit tooling, Guardian Work
Brief generator, schedules, Compose files, or artifact layout only under their
own approved scope. This ADR itself does not implement them.

## Non-goals

This ADR does not implement or claim:

- audit schemas, validators, generators, reducers, or migration tooling;
- schedules, launch agents, service files, CI, GitHub automation, or vendor
  integrations;
- Compose changes, deployment changes, runtime behavior, or service discovery;
- evidence migration, retroactive acceptance, or cleanup of existing artifacts;
- TTS, image generation, provider, or frontend work;
- automatic failover or a new machine-authority registry;
- release approval, campaign approval, capability expansion, or human-decision
  automation.

## Related documents

- [`00-current-state.md`](../00-current-state.md)
- [`adr-index.md`](./adr-index.md)
- [`README.md`](../README.md)
- [`config-and-ops.md`](../config-and-ops.md)
- [`tech-debt-and-risks.md`](../tech-debt-and-risks.md)
- [`VaultNode Canonical Machine and Audit Authority Contract`](../vaultnode-canonical-machine-and-audit-authority-contract.md)
- [`scripts/guardian_work_brief.py`](../../../scripts/guardian_work_brief.py)
- [`scripts/release/beta_release_sentinel.py`](../../../scripts/release/beta_release_sentinel.py)
