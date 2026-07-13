# Canonical Audit Evidence Contract

## Purpose

Define the record future Codexify audit producers and consumers use to exchange
provenance-preserving audit and proof observations under ADR-041 and ADR-042.

## Scope

This contract defines semantics and the JSON manifest shape. It does not change
existing scripts, artifact layouts, `latest` files, schedules, Compose
projects, runtime behavior, or release posture.

## Governing authority

GitHub `main` is canonical code authority. VaultNode is the canonical runtime
and audit authority. Resonant Jones retains human decision authority. ADR-041
governs machine authority; ADR-042 governs the evidence record.

## Canonical terminology

`canonical_evidence_host` means VaultNode. `provisional_development_host`
means another evidence-producing machine. A manifest is a machine-readable
observation record; a report is a derived presentation. Promotion is an
explicit future decision, not report generation or a successful subprocess.

## Evidence-record identity

Every manifest contains `schema_version`, immutable unique `evidence_id`, the
five status fields, RFC 3339 UTC `created_at`, and the `machine`, `repository`,
`runtime`, `execution`, `claims`, `artifacts`, and `relationships` objects.
Commit IDs are lowercase full 40-character Git hashes; artifact hashes are
lowercase SHA-256. Canonical paths are repository-relative. Corrections create
new linked evidence rather than rewriting accepted history.

## Orthogonal status axes

`authority_status` says whether the producer may be canonical.
`proof_class` says what level of truth is demonstrated. `freshness_status` says
whether governing commit and configuration coverage remains valid.
`disposition` says whether the record remains accepted relative to later
evidence. `execution_outcome` says what happened during this run. These must
not be collapsed into one status.

## Required machine identity

`machine` requires `machine_id`, `machine_role`, `hostname`, and
`authority_basis`. Canonical evidence uses normalized `machine_id: vaultnode`
and `machine_role: canonical_evidence_host`; hostname alone is insufficient.
Any other machine records `authority_status: PROVISIONAL`. Credentials,
tokens, secrets, and secret-bearing host metadata are forbidden.

## Required repository identity

`repository` requires portable `repository_root_identity`, `branch`,
`commit_sha`, `upstream_sha`, `dirty`, and `worktree_identity`. Canonical
evidence requires clean `main` and commit/upstream equality for the accepted
head being evaluated. Absolute working paths are optional diagnostics only and
never canonical identity.

## Required runtime identity

`runtime` requires `supported_profile`, `effective_config_hash`,
`compose_project`, `compose_files`, `migration_head`, and `service_identities`.
They may be null only for genuinely non-runtime proof. A
`CURRENT_LIVE_PROOF` cannot claim runtime proof without runtime identity.
Persistent serving and disposable audit runtime identity must remain distinct.
Use sanitized identifiers and hashes, never raw environment dumps or secrets.

## Execution record

`execution` requires ordered `commands`, `suite_id`, start/completion times,
`exit_code`, and `summary`. Failure or blockage can be canonical evidence about
failure. Missing prerequisites are `BLOCKED`; unrun tests are not failures.
Narrative Markdown alone cannot determine an outcome.

## Claim records

`claims.supported`, `.disproved`, and `.unresolved` contain stable claim IDs,
statements, scopes, evidence references, and reasons. References must lead to
command results, artifact records, test reports, persisted runtime receipts, or
other accepted evidence—not only to the summary asserting the claim. Inference
without support remains unresolved.

## Artifact records

Each artifact supplies an ID, repository-relative path, SHA-256, media type,
and role. Canonical artifact hashes are mandatory. Generated Markdown may be an
artifact but is not automatically a proof artifact. Sanitize secret-bearing
logs before any public manifest records or hashes them.

## Integrity and hashing

Artifact readback and hash match are promotion prerequisites. Hashes protect
artifact identity, not claim truth by themselves. Integrity failure makes a
record ineligible for promotion until repaired or superseded by valid evidence.

## Freshness evaluation

Freshness compares declared coverage with governing inputs; it is never
inferred from filename or modification time. A record becomes stale after a
change to evaluated commit, supported profile, effective configuration hash,
relevant Compose configuration, migration head, proof implementation, declared
scope source, runtime image/service identity, or explicit freshness window.

## Staleness triggers

Stale means former coverage no longer matches. It is distinct from
`CONTRADICTED` (disagreeing evidence), a failed or blocked execution outcome,
and `SUPERSEDED` (a compatible later accepted record).

## Supersession

Supersession preserves history through `relationships.supersedes`. It requires
compatible scope and equal or higher authority; timestamp order is insufficient.
Provisional evidence cannot supersede canonical evidence.

## Contradiction handling

Keep conflicting records and their provenance visible in
`relationships.contradicts`; do not synthesize a pass. A reviewed decision or
new qualifying VaultNode proof resolves the conflict while preserving lineage.

## Trusted `latest` eligibility

Only accepted, schema-valid canonical VaultNode evidence meeting declared
semantic promotion checks is eligible. The pointer implementation and pointer
schema are deferred. Provisional evidence and filename timestamps cannot select
or advance it.

## Latest observation versus latest proven baseline

`latest_observation` is the newest schema-valid canonical VaultNode observation,
including `FAIL`, `BLOCKED`, or `ERROR`. `latest_proven` is the newest accepted
canonical proof satisfying its declared claim scope. A failed or blocked latest
observation cannot erase the prior latest proven baseline.

## Provisional evidence behavior

Provisional evidence may guide investigation and remain historical context. It
cannot claim VaultNode proof, current-head coverage without revalidation, or
promotion rights.

## Failed and blocked run behavior

Record failed and blocked attempts as observations with their actual execution
outcome and unresolved claims. Preserve the prior accepted baseline and expose
any current-coverage gap; never relabel a missing prerequisite as PASS or FAIL.

## Schema versioning

Use the repository-local Draft 2020-12 schema and explicit `schema_version`.
Additive and breaking changes require review, migration guidance, and consumer
compatibility planning. Shape validation is not semantic validation.

## Secret-handling boundary

Manifests must not contain credentials, API keys, tokens, private keys, raw
environment values, or secret-bearing logs. Use redacted, portable identity and
cryptographic hashes. Evidence metadata grants no authority to inspect arbitrary
host state.

## Agent obligations

Agents must preserve axis separation, provenance, uncertainty, artifact
integrity, and historical records; label non-VaultNode evidence provisional;
avoid self-certifying reports; and stop when implementation work exceeds the
approved scope.

## Consumer obligations

Consumers must read manifest semantics before derived summaries, preserve
failure/blockage and lineage, surface stale coverage, distinguish latest
observation from latest proven baseline, and never promote evidence merely from
timestamp, location, or generated prose.

## Implementation status

A bounded repository-local identity collector now observes normalized machine
facts and Git repository identity for a later manifest producer. It accepts
the existing `machine_role` vocabulary, keeps explicit authority inputs
separate from observed hostname facts, emits portable repository/worktree
identities, and reports bounded repository eligibility reason codes. It is
observation tooling only: a successful run is not VaultNode proof, canonical
authority, evidence storage, or promotion approval.

A bounded repository-local runtime identity collector now loads the accepted
supported profile through `guardian/core/supported_profile.py`, hashes selected
Compose definitions and the exact profile bytes, resolves the static migration
head, and emits the canonical runtime identity fields for a later manifest
producer. Its `effective_config_hash` is SHA-256 over a deterministic JSON
projection containing only: profile name/version/surface/path/hash and required
and optional services; ordered selected Compose file paths/hashes/declared
names/services; explicit audit and optional serving project identifiers;
normalized service sets; and the migration head. It excludes environment
values, interpolation output, credentials, database URLs, arbitrary absolute
paths, and container inspection. It is static observation tooling only: it
does not establish that Docker or any service is running or healthy.

A repository-local validator now validates one manifest against the existing
Draft 2020-12 schema, applies bounded single-manifest authority and repository
consistency checks, verifies repository-relative artifact hashes, and reports
canonical eligibility. It remains local tooling only: it does not accept or
promote evidence, execute proof, store evidence, compare records, migrate
producers or consumers, or implement trusted `latest`.

A bounded repository-local manifest producer now composes the machine/Git and
static runtime collector outputs with explicit operator metadata, hashes
explicit repository-relative artifact descriptors, derives `authority_status`
from collector eligibility, computes `evidence-sha256-<digest>` from a stable
manifest projection, and validates the resulting manifest through the existing
validator. It preserves ordered commands and selected Compose files while
normalizing unordered claims, relationships, and artifact descriptors. It
rejects caller-supplied evidence IDs, secret-bearing metadata, unsafe artifact
paths, inconsistent execution outcomes, unresolved claim references, and
unsupported live-proof requests. The CLI is stdout-first; an optional output
path is repository-local, atomic, and non-overwriting unless `--replace` is
explicit. The producer never executes commands, inspects Docker or services,
persists evidence, mutates Git, or promotes authority.

## Deferred implementation work

Live service and Compose runtime inspection, runtime health, artifact collection
from proof runs, complete canonical manifest production beyond this bounded
validated assembly, freshness evaluation, evidence storage, cross-record
resolution, pointer storage, promotion receipts, trusted pointers, consumer
migration, and live VaultNode proof remain separately scoped work.
`CURRENT_LIVE_PROOF` is rejected by this producer; other supported proof classes
may carry nullable runtime fields when static runtime identity is not requested.
A requested static runtime identity must be complete, but it is still not live
proof.

## Non-goals

This contract does not implement producer or consumer migration, a registry,
pointer, schedule, audit run, proof run, live Compose inspection, release
approval, or feature expansion.
