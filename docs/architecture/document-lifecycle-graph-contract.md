# Document Lifecycle Graph Contract

## Purpose and status

This contract defines the accepted Codexify Document Lifecycle Graph (DLG): a repository-native, schema-governed property graph for document identity, authority, lifecycle, freshness, evidence, ownership, relationships, and retrieval policy. It evolves the Axis Node source-map model; it does not create a parallel truth store.

Status: **Accepted, docs/control-plane architecture only.** [ADR-056](./adr/056-document-lifecycle-graph-control-plane.md) was accepted by Resonant Jones on 2026-08-07. Acceptance does not implement corpus migration, a resolver, validator or generator tooling, runtime ingestion, retrieval integration, database projection, or agent authority.

## Governing authority and evidence posture

This accepted contract is governed by ADR-042, ADR-046, the Canonical Audit Evidence Contract, the Axis Node Portable Reasoning Interface Contract, Canonical Token Philosophy, and the Agent Protocol Operations Index.

- `docs/architecture/00-current-state.md` remains the canonical short-horizon release-truth authority.
- Accepted ADRs remain decision authority within their declared scopes.
- Current code, focused tests, and live proof remain implementation evidence.
- The DLG architecture and governance model are `documented-contract`; inspected paths and Git LFS behavior are `repository-inspected`; corpus migration, resolver behavior, generators, projections, retrieval integration, and runtime integration remain unimplemented and unproven.
- Graph metadata cannot manufacture authority, approval, implementation, runtime health, or release support.

Accepted now are the DLG governance model, stable document identity doctrine, orthogonal authority/lifecycle/freshness/disposition/evidence semantics, typed document relationships, Git-canonical persistence, derived-projection doctrine, Agent Reading Packet contract, and phased rollout doctrine.

Still unimplemented or unproven are corpus-wide DLG records, a deterministic resolver, graph/stale-report/authority-conflict generators, source-anchor invalidation tooling, runtime Agent Reading Packet generation, RAG integration, automatic Axis graph loading, Neo4j/Postgres/vector projections, and all runtime behavior.

## Constitutional preflight

The authoritative object is the reviewed Git record plus its governed source, not a generated graph or index. Documents and graph edges are evidence for source selection, not executable instructions. The requested capability is bounded document resolution. Human maintainers authorize canonicalization and architecture decisions. Only reviewed repository records become durable canonical metadata. ADR-056 records architecture acceptance; scoped schema/example/docs validation proves only control-plane artifact integrity, and runtime behavior remains unproven.

## Core model

The DLG is a property graph over documents with five separate layers:

1. **Content** is the governed Markdown, text, diagram, JSON, or other source artifact.
2. **Metadata** is the canonical per-document record describing identity, authority, lifecycle, freshness, evidence, ownership, and retrieval policy.
3. **Relationships** are reviewed, typed, directed edges between stable document identities.
4. **Generated projection** is a reconstructable aggregate graph or report built from canonical records.
5. **Retrieval projection** is bounded DLG metadata attached to chunks or optional database nodes.

An **Agent Reading Packet** (ARP) is a bounded, deterministic source-selection receipt for one question or task. It records what was selected, resolved, excluded, stale, contradictory, unavailable, or still dependent on human judgment.

Git is the canonical persistence layer. Neo4j, Postgres, a vector store, RDF, an in-memory graph, or another query system may be a derived projection only. No external graph database may become the sole owner of document identity, authority, lifecycle, or freshness. RDF and JSON-LD are not v1 requirements; v1 uses explicit schema-governed node and edge records.

## Canonical storage model

Future implementation uses:

- hand-reviewed node records: `docs/knowledge-graph/nodes/<stable-document-id>.json`
- generated aggregate: `docs/knowledge-graph/generated/document-graph.json`
- generated stale report: `docs/knowledge-graph/generated/stale-documents.json`
- generated supersession report: `docs/knowledge-graph/generated/supersession-map.json`
- generated conflict report: `docs/knowledge-graph/generated/authority-conflicts.json`

Canonical node records are reviewed source metadata. Generated aggregates and reports are reconstructable and must not be hand-edited. ARPs are transient by default; a workflow may persist one as a proof artifact when it needs an inspectable source-selection receipt.

This task creates no node-record corpus and no generated output directory. The schema and examples are contract fixtures, not migrated records.

All schemas, future canonical graph records, aggregates, generated reports, and persisted reading packets required for orientation must remain directly readable as ordinary Git text through connector APIs. `.gitattributes` plaintext exceptions apply to `schemas/knowledge/**/*.json` and `docs/knowledge-graph/**/*.json`; the repository-wide JSON LFS rule remains intact. This task does not migrate `docs/axis-node/source-manifest.json` or any existing LFS object.

## Stable document identity

Every governed document receives a repository-unique ID:

```text
codexify:doc:<domain>:<slug>
```

Examples:

- `codexify:doc:architecture:current-state`
- `codexify:doc:architecture:chat-runtime-contract`
- `codexify:doc:adr:056-document-lifecycle-graph`
- `codexify:doc:proof:2026-04-04-clean-start-migration`

Rules:

- A move or rename changes the locator, not the ID.
- Rewriting the same canonical concept preserves the ID.
- A split creates new IDs linked from each new concept with `derived_from`.
- A merge creates a new ID linked to every source with `derived_from` and, when it replaces their authority, `supersedes`.
- Retired or deleted identities remain tombstones so historical edges resolve.
- Paths are repository-relative locators, never identity.
- Aliases may resolve old paths, IDs, titles, or historical names.
- IDs are unique repository-wide and may never be reused.

## Canonical token domains and orthogonal axes

The schema uses bounded enums. It must not add one combined `status` field or a free-form document kind.

### Authority class

`release_authority`, `accepted_adr`, `normative_contract`, `structural_authority`, `operator_authority`, `design_canon`, `supplementary`, `evidence_only`, `working`, `pointer`, `archive`.

Authority is valid only inside `authority_scopes`. It is not a universal scalar score. An authoritative document outside its scope is not authoritative for the question.

### Lifecycle state

`draft`, `proposed`, `active`, `frozen`, `retired`, `tombstoned`.

### Freshness state

`current`, `stale`, `unknown`, `not_applicable`.

### Disposition

`accepted`, `superseded`, `contradicted`, `quarantined`, `unreviewed`.

### Evidence class

`proven-live-runtime`, `proven-test`, `proven-code-path`, `documented-contract`, `working-theory`, `aspirational`, `unknown`.

### Required distinctions

- Stale means governing coverage changed or expired; it does not mean false.
- Superseded means compatible later authority displaced a record; it does not mean contradicted.
- Frozen means immutable history; it does not mean current-head proof.
- Accepted means accepted within a governance scope; it does not mean release-supported.
- Graph metadata cannot grant authority absent from the underlying repository governance.

## Document kinds

The bounded v1 kinds are:

`current_state`, `adr`, `architecture_contract`, `runtime_map`, `design_canon`, `product_spec`, `operator_runbook`, `proof`, `inspection`, `generated_report`, `campaign`, `task`, `compatibility_pointer`, `historical_archive`.

Extensions require schema-version review. There is no free-form kind escape hatch.

## Document node record

Each node requires:

- `schema_version`, `record_type`, `document_id`, `path`, `title`, `kind`, and `summary`
- `aliases`, `authority_class`, and non-empty `authority_scopes`
- `lifecycle_state`, `freshness`, `disposition`, and `evidence_class`
- `owners`, `source_anchors`, `read_when`, and `must_not_prove`
- `retrieval_policy`, `temporal`, `content_hash`, and `relations`
- `governing_adr_posture` to support architecture-contract validation

Owners are public repository roles, teams, or approved handles—not unconsented personal context. Repository-relative paths are mandatory. Node records must contain no secrets, credentials, private host paths, raw environment values, or secret-bearing free-form metadata.

`freshness` records `state`, RFC 3339 `verified_at`, full `verified_commit`, and explicit `triggers`, with optional `window_days` and `reason`.

Each `source_anchors` entry contains a repository-relative path or glob, one type (`document`, `code`, `test`, `config`, `schema`, `proof`), and `invalidates_freshness`.

`retrieval_policy` records `default_policy` (`include`, `conditional`, `exclude`), applicable and excluded intents, priority (`required`, `primary`, `supporting`, `historical`), optional section hints, and optional maximum chunk budget.

`temporal` records `created_at`, `effective_from`, and optional `effective_until`.

`content_hash` is the SHA-256 of the governed source bytes. It protects identity/integrity, not truth.

Governed schema boundaries use `additionalProperties: false`; extensions require an explicit versioned object.

## Typed relation model

Every relation declares its type, target ID, authority scope, canonicality (`canonical` or `advisory`), review state, and a bounded rationale. Canonical edges are hand-reviewed. Inferred edges never enter the accepted canonical graph without review; optional inference projections remain separately labeled and non-authoritative.

| Edge | Allowed source -> target | Symmetric | Cycle policy | Retrieval effect | Disposition effect | Freshness effect | Canonical posture |
|---|---|---|---|---|---|---|---|
| `governed_by` | governed contract/record -> ADR or policy authority | no | forbidden | include governing decision | none | target change may stale source | canonical after review or advisory while proposed |
| `implements` | implementation-facing contract/map -> decision or contract | no | forbidden in the resolution subset | supporting expansion only; never implementation proof | none | implementation-anchor change may stale source | canonical after review or advisory |
| `evidence_for` | proof/inspection -> any governed target | no | forbidden | include only for declared scope/time | none | evidence retains its own coverage state | canonical after review or advisory |
| `derived_from` | new or derived record -> one or more source records | no | forbidden | expose lineage and historical sources | none by itself | source change may stale an active derivative | canonical after review or advisory |
| `generated_from` | generated report -> non-generated input records | no | forbidden | generated source remains conditional | none | input change stales generated output | canonical after review or advisory |
| `supersedes` | newer compatible record -> older record | no | forbidden | prefer newer and exclude older ordinarily | older becomes `superseded` after review | none by itself | canonical after review or advisory while proposed |
| `contradicts` | any record -> conflicting record | yes; store or reconstruct both directions | two-node mirror is allowed; longer authority-resolution cycles are rejected | include both and expose conflict | both may become `contradicted` after review | none; contradiction is not staleness | canonical after review or advisory while unresolved |
| `pointer_to` | compatibility pointer -> exactly one non-pointer canonical target | no | forbidden | replace pointer content with target | none | target move/supersession may stale pointer | canonical after review; advisory pointers do not resolve automatically |
| `depends_on` | dependent record -> required input record | no | allowed only outside resolution-critical subsets and after semantic review | expand required/supporting dependencies | none | target change may stale source | canonical after review or advisory |
| `applies_to` | scoped rule, contract, or evidence -> governed target | no | allowed when it does not create a resolution cycle | narrow eligible scope or expand scoped context | none | target change may stale source when declared | canonical after review or advisory |
| `related_to` | any record -> contextual neighbor | yes | allowed | weak optional expansion only | none | none | advisory only |

Required semantics:

- `supersedes` always points from newer to older.
- `contradicts` preserves both records and must be visible until reviewed.
- A compatibility pointer has exactly one `pointer_to` target.
- `generated_from` never grants generated material source authority.
- `evidence_for` proves only its declared scope and time window.
- `related_to` cannot decide authority or supersession.
- Canonicality indicates review posture; it cannot override the authority of the connected documents.

## Graph invariants

Future semantic validation must enforce:

- document IDs are unique;
- active canonical paths are unique;
- every target resolves, including tombstones;
- self-relations are forbidden;
- `pointer_to`, `supersedes`, and `derived_from` chains are acyclic;
- a compatibility pointer has exactly one `pointer_to` edge and does not duplicate target content;
- proposed or accepted architecture contracts declare their governing ADR posture;
- accepted architecture contracts have a `governed_by` edge to an accepted ADR;
- proof and evidence records are append-only or frozen;
- evidence corrections create replacement records and lineage instead of rewriting accepted history;
- generated reports cannot become canonical authority;
- generated work briefs and session packets are excluded from ordinary retrieval unless their date, branch, worktree, or session is in scope;
- historical proof cannot become current-head proof without explicit current-coverage evidence;
- only one active release-authority document governs a given release scope;
- authority is scope-specific, never a universal score;
- no edge overrides code, tests, live evidence, accepted ADRs, or `00-current-state.md` outside its granted scope.

## Freshness and invalidation

Freshness follows governing inputs, not modification time. A node becomes stale when one or more of these conditions apply:

- a freshness-invalidating source anchor changed after `verified_commit`;
- a governing ADR or canonical dependency changed;
- a relevant schema or supported profile changed;
- proof implementation or declared implementation coverage changed;
- an explicit freshness window expired;
- a generated record no longer matches its inputs.

Tooling may observe and report stale metadata, including the exact changed anchors. It may not rewrite architecture conclusions or silently mark them false. A human review or approved proof workflow restores `current`. `00-current-state.md` may use a short time window because it is intentionally hot. Stable design canon and frozen proof may use `not_applicable` when currentness is not meaningful.

Freshness changes do not automatically change lifecycle or disposition.

## Agent Reading Packet

An ARP is the canonical future output of graph-aware source resolution. It extends the Axis Orientation Receipt and does not replace it. It grants no execution permission, architecture approval, or truth guarantee.

The packet requires:

- `schema_version`, `packet_id`, `created_at`, `repository_revision`, and `graph_revision`
- `question_or_intent`, `authority_profile`, and an explicit `reading_budget`
- ordered `selected_sources`
- `resolved_pointers`, `supersession_chains`, and `excluded_sources`
- `conflicts`, `stale_warnings`, `proof_gaps`, and `unavailable_sources`
- `human_decisions_required`

Every selected source records document ID, path, reason, authority scope/class, freshness, evidence class, retrieval priority, optional sections, and the traversed graph path. Every exclusion records a document ID or unresolved path and a reason.

The packet exposes rather than hides contradictions, stale authority, unavailable canonical sources, historical-only evidence, proof gaps, and unresolved human decisions.

## Bounded resolver sequence

A future resolver must:

1. Classify the question by intent and authority scope.
2. Select the query-specific authority profile.
3. Resolve aliases and compatibility pointers.
4. Resolve supersession before content selection.
5. Select required roots.
6. Traverse only profile-allowed edge types within a bounded hop count.
7. Filter by lifecycle, disposition, freshness, and retrieval policy.
8. Preserve contradictions and competing accepted sources.
9. Order by scoped authority and purpose, not timestamp or vector score alone.
10. Enforce source, hop, section, and chunk budgets.
11. Emit an ARP before large-corpus ingestion.
12. Attach document ID, graph revision, authority class, freshness, disposition, and evidence class to every RAG chunk.
13. Permit bounded relation-aware expansion after initial semantic retrieval.
14. Record why every source was selected or excluded.

Default behavior includes active canonical sources, resolves pointers, excludes replaced content when a current replacement exists, excludes quarantined material unless requested, and excludes generated session reports unless the session is in scope. It retains immutable proof for historical/proof questions. A stale source is allowed with an explicit warning only when no current alternative exists or history is requested. Ten supplementary documents cannot outvote one scoped canonical source through chunk volume.

No LLM-generated authority score is permitted.

## Query-specific authority profiles

These are scoped resolution orders, not a global hierarchy.

### Release and support

1. `docs/architecture/00-current-state.md`
2. Applicable accepted ADRs and normative contracts
3. Supported-profile and operator documentation
4. Current live proof
5. Supplementary context

### Architecture decision

1. Applicable accepted ADRs
2. Normative contracts
3. Current structural maps
4. Implementation evidence
5. Proposals and historical context

### Implementation behavior

1. Current code path
2. Focused tests
3. Live runtime evidence where required
4. Current architecture documentation
5. Historical or planning material

### UI and design

1. Accepted UI/design canon
2. Current component and token implementation
3. Focused UI tests
4. Product specifications
5. Historical design notes

### Historical and provenance

1. Immutable proof or history matching the requested time
2. Supersession and derivation edges
3. Current interpretation documents
4. Related narrative material

## Lifecycle transitions

| Event | Required transition behavior |
|---|---|
| New draft | New ID; `draft`, `unknown`, `unreviewed`; no authority inference. |
| Proposed contract | `proposed`; governing ADR posture declared; human acceptance pending. |
| Accepted contract | `active` + `accepted`; `governed_by` accepted ADR required. |
| Active becomes stale | Only freshness becomes `stale`; lifecycle remains `active`. |
| Reverification | Approved evidence updates verification fields and restores `current`. |
| Supersession | Newer node adds `supersedes`; older record remains with `superseded`. |
| Rename or move | Preserve ID; update path and retain old locator as alias. |
| Split | Create IDs per new concept; each uses `derived_from`; review old disposition. |
| Merge | Create a new ID with all `derived_from` edges and reviewed `supersedes`; keep sources. |
| Proof correction | Freeze the original; create a replacement linked by lineage and supersession/contradiction as appropriate. |
| Generated expiration | Mark stale or regenerate; never hand-edit the output. |
| Quarantine | Set disposition `quarantined`; retain record and exclude by default. |
| Tombstone | Preserve ID, lineage, aliases, and minimum historical metadata; remove active locator authority. |

Automatic tools may propose transitions. They may not accept architecture, select canonical truth, resolve contradictions, approve supersession, or delete history without the proper human gate. Destructive deletion is replaced by retirement or tombstoning except when secrets or legal requirements require a separately governed removal.

## Staged corpus migration

No mass rewrite occurs in the first implementation phase.

### Phase 0: inventory

Enumerate governed document-like files, calculate hashes, detect Git LFS pointers, and report duplicate paths, titles, ADR numbers, and obvious aliases. Make no content changes.

### Phase 1: classify

Create reviewed node records; assign kinds and orthogonal axes; identify owners, authority scopes, and unclassifiable material.

### Phase 2: connect

Add reviewed pointer, governance, derivation, evidence, dependency, contradiction, and supersession edges. Preserve unresolved relationships instead of guessing.

### Phase 3: validate and generate

Validate nodes, build the aggregate, produce stale/collision/authority-conflict/orphan reports, and create ARPs for representative questions.

### Phase 4: human canonicalization

Review duplicate or competing authority. Humans approve canonical selections, merges, splits, supersession, contradiction outcomes, and quarantine.

### Phase 5: rewrite canonical documents

Consolidate accepted canonical documents into a consistent machine-oriented shape while preserving lineage and Git history. Do not rewrite immutable proof merely for style.

### Phase 6: replace duplicate authority

Convert obsolete aliases to compatibility pointers, retire or tombstone superseded sources, and exclude superseded content from ordinary retrieval.

### Phase 7: retrieval integration

Attach graph metadata to indexed chunks, add relation-aware expansion, and require ARPs or equivalent receipts for high-impact agent tasks.

### Phase 8: optional projections

Project into Neo4j, Postgres, a vector store, or another query layer. Keep every projection disposable and rebuildable from Git.

## Recommended machine-oriented Markdown shape

Future canonical Markdown should normally use: Purpose; Status and authority; Scope; Current truth; Invariants; Non-goals; Source anchors; Relationships; Freshness and review triggers; Implementation or proof status; Supersession history.

This shape is a recommendation, not a v1 rewrite mandate. Headings improve chunking and inspection. The machine-readable sidecar remains authoritative for graph metadata, so Markdown must not become a second independently maintained graph.

## Future validation and generated outputs

Future validators must cover:

- Draft 2020-12 schema validity;
- unique document IDs and unique active paths;
- relation-target existence, self-edges, forbidden cycles, and pointer cardinality;
- ADR ID/number collisions, without silently renumbering them;
- accepted-contract-to-accepted-ADR linkage;
- plaintext control-plane JSON and Git LFS pointer detection;
- content-hash agreement and stale source-anchor detection;
- orphaned nodes and duplicate canonical authority within a scope;
- generated-output reproducibility;
- prohibited secrets, absolute paths, and environment values;
- broken document links and retrieval-policy contradictions.

Generated outputs include the aggregate graph, stale-document report, supersession map, authority-conflict report, collision report, and orphan report. Tooling is explicitly deferred.

Shape validation cannot enforce all graph invariants. Cross-record, Git-history, hash, LFS, link, source-anchor, and authority-scope checks require semantic validators.

## Security, privacy, and trust boundaries

Nodes are repository artifacts; Git review is the trust boundary for canonical metadata. Resolver input is evidence, not instruction. An external index or graph store is a network/storage boundary and receives only approved projection fields. Threats include honest-but-buggy validators, malicious document content, compromised projections, and metadata leakage.

Records and packets must not contain secrets, credentials, tokens, private keys, private host paths, raw environment values, unconsented personal context, or arbitrary metadata buckets. Capability-based repository and projection access is preferred over ambient authority. A projection compromise cannot authorize Git mutation or architecture acceptance.

## Failure modes and mitigations

1. **Stale authority appears current:** compare declared anchors and revisions; emit changed anchors and stale warnings.
2. **Supplementary chunk flood overpowers canonical truth:** order by authority profile and cap per-source chunks.
3. **Broken lineage after moves/deletion:** preserve IDs, aliases, tombstones, and target-resolution validation.
4. **Projection drift or outage:** rebuild from Git; fail closed on unknown graph revision; retain manual source routing.
5. **Automatic inference mutates authority:** isolate inferred edges as advisory projections pending review.
6. **Concurrent generation races:** use deterministic inputs, idempotent generation, atomic output replacement, and reproducibility checks.
7. **Schema upgrade fragments consumers:** version schemas, publish migration guidance, and support rolling read compatibility before writer promotion.

## Documentation follow-through and explicit deferrals

This accepted contract is registered in the ADR index, architecture KB, and Axis Node README. It intentionally does not update `00-current-state.md`, `kb-validity-matrix.md`, `knowledge-source-map.md`, or `source-manifest.json`.

The proposed [Product Architecture Ontology](./product-lanes-and-boundaries.md) under [ADR-057](./adr/057-product-architecture-ontology-dlg-integration.md) extends the DLG with stable product-architecture vocabulary, typed relationship predicates, and evidence-backed assertion semantics. The DLG schema now includes an optional `architecture_scope` extension that references ontology and assertion IDs without duplicating ontology definitions. The Agent Reading Packet schema now includes an optional `architecture_context` extension for bounded product-architecture orientation during source resolution. DLG document identities remain the canonical identity domain for ADRs, contracts, proofs, and architecture authority references.

Deferred work includes every existing-document classification or rewrite; the node corpus; deterministic resolver; lifecycle graph, stale-report, authority-conflict, and source-anchor invalidation tooling; validator CLI; CI; graph-database projection; retrieval integration; RAG chunk metadata; runtime ARP generation; automatic Axis graph loading; agent-harness loading; and document moving, archival, or LFS migration.

## Non-goals

No runtime, CLI, Python tooling, CI workflow, database migration, Neo4j write, vector-index change, RAG behavior, automatic document classification, automatic authority decision, source-manifest migration, mass rewrite, duplicate cleanup, release claim, or UI is implemented by this contract.
