# ADR-042: Canonical Audit Evidence Contract

## Status

Accepted.

## Context

ADR-041 assigns GitHub `main` as code authority and VaultNode as the sole
canonical runtime and audit authority. Existing audit reports, proof packets,
sentinel output, and Guardian Work Brief inputs do not share a machine-readable
record with explicit authority, scope, integrity, freshness, or lineage.

## Problem statement

Without one canonical evidence record, a generated report, a filename date, or
a local `latest` file can be mistaken for current accepted proof. This loses
the distinctions between who observed something, what was demonstrated, what
the run did, whether the observation is still current, and whether later
evidence displaced it.

## Decision

Codexify defines one canonical audit evidence manifest as the machine-readable
source for audit and proof observations. Its normative shape is
[`canonical-audit-evidence.schema.json`](../../../schemas/audit/canonical-audit-evidence.schema.json);
the operating rules are in the [companion contract](../canonical-audit-evidence-contract.md).

This ADR defines semantics and schema only. It does not migrate, generate,
validate, publish, or promote evidence at runtime.

## Evidence model

Each immutable manifest identifies its schema version, evidence identity,
producer, repository, runtime, execution, claims, artifacts, and relationships.
Evidence is an observation record, not a release approval or self-certifying
report. Accepted records are never edited in place; corrections are new linked
records.

## Orthogonal status axes

The manifest keeps these independent:

| Axis | Question answered | Values |
|---|---|---|
| Authority status | Who produced it and may it be canonical? | `CANONICAL`, `PROVISIONAL` |
| Machine role | What role did the producer have? | `canonical_evidence_host`, `provisional_development_host` |
| Proof class | What system truth did it demonstrate? | `CURRENT_LIVE_PROOF`, `CURRENT_TEST_PROOF`, `HISTORICAL_LIVE_PROOF`, `IMPLEMENTED_UNPROVEN`, `PARTIAL_VERTICAL_SLICE`, `DOCS_ONLY`, `BLOCKED`, `UNKNOWN` |
| Freshness status | Does it still cover governing commit and configuration? | `CURRENT`, `STALE` |
| Evidence disposition | Does it remain accepted relative to later evidence? | `ACCEPTED`, `SUPERSEDED`, `CONTRADICTED`, `REJECTED` |
| Execution outcome | What happened in this execution? | `PASS`, `FAIL`, `BLOCKED`, `ERROR`, `NOT_APPLICABLE` |

No overloaded `status` field may combine these axes.

## Claim model

Claims are explicit `supported`, `disproved`, or `unresolved` records with a
stable identifier, scoped statement, reason, and evidence references. A claim
cannot cite its own generated summary as its only evidence. Generated Markdown,
dashboards, and checkboxes may project claims but cannot originate or certify
proof.

## Artifact integrity

Canonical artifact identity is a repository-relative path plus lowercase
SHA-256 hash, media type, and role. A machine-local absolute path is diagnostic
metadata at most, never portable artifact or repository identity. Missing or
hash-mismatched canonical artifacts make promotion ineligible.

## Freshness and staleness

Freshness is coverage, not timestamp recency. Evidence is stale whenever its
evaluated commit, supported-profile identity, effective configuration hash,
relevant Compose configuration, migration head, proof implementation, declared
scope source, runtime image/service identity, or an explicit freshness window
no longer matches the governing input.

Historical proof never silently inherits validity after a new commit or
configuration change.

## Supersession and contradiction handling

Supersession preserves the older record and identifies the compatible,
higher-or-equal-authority successor. Timestamp order alone cannot supersede.
Contradictory records remain visible and unresolved until reviewed or resolved
by new qualifying proof. Provisional evidence cannot supersede canonical
evidence.

## Trusted `latest` implications

ADR-041's trusted `latest` is derived only from accepted VaultNode evidence.
The model distinguishes `latest_observation` (newest schema-valid canonical
observation, including failure or blockage) from `latest_proven` (newest
accepted canonical proof for a declared scope). A failed or blocked run remains
visible without erasing the last proven baseline. Neither pointer can be
advanced by a noncanonical machine or filename timestamp.

## Schema/versioning policy

The schema uses Draft 2020-12 and an explicit `schema_version`. Version changes
are reviewable architecture changes. The schema validates shape and vocabulary;
cross-record and environment lookup checks remain semantic validation work.

## Consequences

- Future producers and consumers have one stable handoff record.
- Authority, proof maturity, freshness, disposition, and execution are no
  longer conflated.
- Consumers must preserve failures, blockers, uncertainty, hashes, and
  evidence lineage.
- Migration is required before existing reports or `latest` files can be
  interpreted under this contract.

## Rejected alternatives

- Markdown reports as canonical evidence.
- Filename timestamps as freshness authority.
- Documentation checkboxes as independent proof.
- One overloaded `status` field for authority, proof maturity, freshness,
  disposition, and execution outcome.
- Machine-local absolute paths as portable artifact identity.
- Noncanonical machines promoting trusted `latest`.
- Historical proof silently inheriting validity across new commits or
  configuration changes.
- Generated summaries certifying their own claims.

## Implementation follow-through

Separate tasks must implement VaultNode identity collection, semantic schema
validation, manifest production, artifact hashing, freshness evaluation,
promotion receipts/pointers, and incremental consumer migration for audit
scripts, proof runners, the beta sentinel, Guardian Work Briefs, and
current-state reporting.

## Non-goals

This ADR does not alter audit scripts, Compose projects, schedules, beta
sentinel behavior, Guardian Work Brief generation, runtime proof, findings
tracking, supported-profile gateway behavior, TTS, image generation, provider,
frontend, worker, queue, or persistence behavior. It creates no registry,
pointer implementation, automatic promotion, or release approval.
