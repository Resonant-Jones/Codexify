# Project Pulse Exact-ID Read Proof Fixture Contract

## Title

Project Pulse exact-ID read proof fixture contract.

## Purpose

Define a static proof fixture shape for a future exact-ID Project Pulse read without implementing Project Pulse, adding routes, adding adapter methods, adding tests, or changing runtime behavior.

## Status

docs/proof-only contract; static fixture only; no runtime loader implemented; no route, service, adapter method, schema, migration, UI, CLI, worker, command bus, provider call, retrieval change, graph traversal, browser capture, export/restore behavior, test, database seed, or write path added; does not widen supported beta.

## Source contracts read

- `docs/architecture/00-current-state.md`
- `docs/architecture/adr/adr-index.md`
- `docs/architecture/README.md`
- `docs/architecture/project-pulse-read-only-contract.md`
- `docs/architecture/project-pulse-contract-follow-through.md`
- `docs/architecture/project-pulse-implementation-target-inspection.md`
- `docs/architecture/continuity-persistence-adapter-contract.md`
- `docs/architecture/continuity-operator-readback-route-contract.md`
- `docs/architecture/continuity-operator-state-commit-link-readback-contract.md`
- `docs/architecture/continuity-operator-diagnostics-truth-surface-contract.md`
- `docs/architecture/continuity-write-action-contract.md`
- `docs/architecture/continuity-operator-loop-proof-chain.md`
- `docs/architecture/agent-protocol-operations.md`

## Why this fixture exists

The Project Pulse implementation target inspection (`project-pulse-implementation-target-inspection.md`) found identifiable Continuity target seams but also a concrete adapter/route boundary mismatch. The current operator routes provide useful exact-ID behavior evidence, but they bypass the persistence adapter. The adapter lacks complete exact-ID packet/commit/link read methods. Before any service, route, or schema work proceeds, a static proof fixture provides source material for the expected proof shape — establishing what an exact-ID read result must look like without implementing any runtime behavior.

## Current blocker from target inspection

- Project Pulse has no runtime implementation target yet.
- Current Continuity operator routes provide useful exact-ID behavior evidence.
- Current Continuity operator routes bypass the persistence adapter.
- The adapter does not yet provide complete exact-ID packet, commit, and link read methods.
- Therefore, the next safe step is a static proof fixture contract before service or route implementation.

## Fixture scope

This fixture defines exactly two static cases:
- one authorized exact-ID read where a record is found
- one exact-ID read where evidence is missing (record not found)

The fixture models the expected proof shape: source categories, provenance fields, freshness indicators, confidence ratings, diagnostics snapshot posture, boundary flags, authority locks, and forbidden interpretations. It does not model runtime loading, database seeding, API behavior, or any live system interaction.

## Fixture file

`docs/architecture/fixtures/project-pulse-exact-id-read-proof.v1.json`

## Fixture shape

The fixture is a single JSON document at schema version `project-pulse-exact-id-read-proof.v1`. Top-level fields:

| Field | Purpose |
|---|---|
| `schema_version` | Identifies the fixture schema version |
| `fixture_kind` | Identifies the fixture as a static Project Pulse exact-ID read proof fixture |
| `status` | Always `docs_proof_only` |
| `generated_by` | Always `manual_static_fixture` |
| `runtime_claim` | Always `none` |
| `release_claim` | Always `none` |
| `source_contracts` | List of governing contract paths |
| `cases` | Array of exactly two case objects |
| `authority_locks` | Ten boolean locks, all set to `false` |
| `forbidden_interpretations` | Array of explicit interpretation guard strings |

## Required fixture cases

### Case 1: Found exact-ID read (`found_exact_id_read`)

Models a successful exact-ID read against a reality state record via the adapter's `load_reality_state` method. The record is found, the payload is populated with example fields, confidence is `high`, freshness is current, and all boundary flags remain closed. Required sub-fields:

- `case_id`, `case_kind`, `requested_surface`, `requested_id`, `read_posture`, `source_category`, `record_family`
- `record_found` must be `true`
- `record_payload` must be a non-null object with example reality state fields
- `provenance` must declare `adapter_method`, `read_mode`, `source_category`, and `soft_delete_filtered`
- `freshness` must include `record_age_seconds`, `stale`, and `stale_threshold_not_set`
- `confidence` must be `high`
- `diagnostics_snapshot` must include `project_pulse_enabled: false`, `graph_used: false`, `runtime_event_published: false`, `export_restore_enabled: false`, aggregate counts, operator profile posture, and `supported_beta_quarantined: true`
- `boundaries` must include all seven boundary flags set to `true`

### Case 2: Missing exact-ID read (`missing_exact_id_read`)

Models a failed exact-ID read where no record exists for the requested ID. `record_found` is `false`, `record_payload` is `null`, `missing_reason` is populated, confidence is `none`, and freshness indicators are `null`. All other required fields match the found case structure with appropriate absent-record semantics.

## Authorized source categories

- `record_surface` — continuity records via adapter reads
- Future proof, diagnostics, release-truth, and governance categories per the read-only contract are acknowledged but are not separately modeled in this fixture

## Forbidden source categories

This fixture must not model reads from:
- graph mounts
- browser contexts
- provider state
- worker state
- live chat runtime
- export/restore manifests

## Exact-ID read boundary

The fixture models exact-ID reads only. It does not define or imply:
- list behavior
- search behavior
- query semantics
- pagination
- relationship expansion
- graph traversal
- background collection
- periodic scanning

## Missing-evidence boundary

The missing case models `record_found: false` with `record_payload: null`. The fixture does not fabricate records, infer state from absence, substitute diagnostics counts for record truth, or trigger writes to fill gaps.

## Diagnostics boundary

The diagnostics snapshot is a pass-through of aggregate posture at generation time. It is not narrative project truth. `project_pulse_enabled` remains `false` in both cases.

## Adapter boundary

Both cases reference `adapter_method: load_reality_state` in provenance. The fixture does not model direct SQLAlchemy access, bypass the adapter, or invoke write methods. The adapter gap (incomplete exact-ID packet/commit/link coverage) is not resolved by this fixture.

## Non-goals

This fixture does not:
- implement Project Pulse runtime behavior
- add adapter methods
- modify Continuity routes
- add routes, services, schemas, migrations, UI, CLI, workers, command bus integration, provider/model calls, retrieval/router behavior, graph traversal, browser capture, or export/restore behavior
- add tests, runtime fixture loading, database seed behavior, or cron behavior
- create Project Pulse records or mutate Continuity records
- import or invoke Continuity write actions
- infer release support or widen supported beta

## Recommended next slice

`Define Project Pulse output artifact schema`

**Reason:** After the static exact-ID read proof fixture exists, the next safe architecture step is to define the future Pulse output artifact shape without adding runtime behavior. Adapter repair and service skeleton work must remain deferred until the output contract is clear.

## ADR impact

**Classification:** Aligned with existing ADRs and architecture contracts.

**Governing ADRs/contracts:**
- ADR-015 Continuity Engine Working Set and Decay Contract
- ADR-016 Continuity Governance Surface Contract
- ADR-030 Continuity Protocol Suite Runtime Gate
- ADR-031 Continuity Phase A Storage Migration Gate
- `docs/architecture/project-pulse-read-only-contract.md`
- `docs/architecture/project-pulse-contract-follow-through.md`
- `docs/architecture/project-pulse-implementation-target-inspection.md`
- `docs/architecture/continuity-persistence-adapter-contract.md`
- `docs/architecture/continuity-operator-readback-route-contract.md`
- `docs/architecture/continuity-operator-state-commit-link-readback-contract.md`
- `docs/architecture/continuity-operator-diagnostics-truth-surface-contract.md`
- `docs/architecture/continuity-write-action-contract.md`
- `docs/architecture/00-current-state.md`

**Reason:** This task defines a static proof fixture and contract for future exact-ID read proof work. It does not implement runtime behavior, add adapter methods, add routes, add tests, add storage, mutate records, or widen supported beta.

## Release-truth boundary

`docs/architecture/00-current-state.md` remains authoritative for release truth. Project Pulse is currently docs-only, not supported beta behavior, not chat-runtime continuity, not a write path, and must not mutate Continuity records. This fixture is static source material only — not runtime proof, not a release claim, and not an implementation authorization.

## Validation results

Validation commands and results are recorded in the task closeout. No automated runtime tests apply.
