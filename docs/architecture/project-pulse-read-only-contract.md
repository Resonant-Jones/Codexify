# Project Pulse Read-Only Contract

## Status

**Docs-only architecture contract.** Defines Project Pulse semantics as a future read-only interpretive surface above the proven Continuity operator substrate. Does not implement runtime behavior, routes, migrations, UI, workers, or any write path. Does not activate supported beta. Does not widen the release promise.

**Created:** 2026-06-26
**Branch:** `main`
**HEAD:** `1832d87647`

## Purpose

Project Pulse is the first interpretive surface above the proven Continuity substrate. Its job is to define how Codexify may eventually answer "where was I?" or "what is the current project reality?" from governed Continuity records — without writing new Continuity state, mutating memory, activating chat-runtime continuity, expanding supported beta behavior, or collapsing operator diagnostics into narrative summaries.

This contract defines what Project Pulse may read, what it may summarize, what it must not infer, what it must not mutate, and how it preserves the boundary between records, interpretation, and runtime behavior. It does not implement any of those capabilities.

## Scope

Project Pulse is defined as a **future read-only brief surface** that synthesizes interpretive output from existing Continuity records only after implementation is separately authorized by a future architecture-impact task.

It may conceptually read from:

- **Record surfaces:** `continuity_reality_states`, `continuity_context_packets`, `continuity_reality_commits`, `continuity_state_packet_links` (Phase A tables, via the persistence adapter)
- **Proof surfaces:** the loop proof chain (`continuity-operator-loop-proof-chain.md`) and explicit proof artifacts, as metadata sources only — not as narrative source truth
- **Diagnostics surfaces:** aggregate counts, gate posture, and hard-false flags from the diagnostics operator route — as verification signals only, not as summarization inputs
- **Release-truth surfaces:** `00-current-state.md` and supported-profile posture — as boundary markers only, not as content sources
- **Governance metadata:** continuity scope, intensity, decay, exclusions, and import treatment from ADR-015 / ADR-016 — as interpretation constraints, not as pulse content

It must not read from graph mounts, browser contexts, provider state, worker state, or live chat runtime unless separately authorized by a future contract.

## Non-Goals

Project Pulse is explicitly **not** any of the following:

- **A write path.** It must not create, update, or delete any continuity record. It must not call `ContinuityWriteActionService`, `create_reality_stamp`, `compile_and_save_reality_state_from_explicit_packets`, `create_reality_commit`, or `link_state_to_packets`.
- **A Reality Stamp writer.** It does not capture or persist context.
- **A Reality State compiler.** It does not invoke `compile_reality_state()` to produce new compiled truth.
- **A continuity mutation surface.** It does not alter scope, intensity, decay, exclusion, or governance settings.
- **Ambient memory.** It does not automatically produce brief output as a side effect of ordinary system behavior.
- **Chat runtime continuity.** It does not feed Pulse output into the context broker, completion assembly, or turn-level inference. It does not alter retrieval behavior.
- **Worker integration.** It does not schedule background work, heartbeat triggers, or periodic brief generation.
- **Command bus integration.** It does not accept tool calls or emit tool results.
- **Provider integration.** It does not call model providers, invoke inference, or route through AI backends.
- **Retrieval/router behavior.** It does not widen retrieval scope or modify retrieval policy.
- **Browser capture.** It does not read browser context, tab state, or DOM.
- **Sync/shared-dyadic runtime.** It does not federate Pulse output or share reality across users.
- **Graph traversal.** It does not query Neo4j, traverse relationships, or expand record graphs.
- **List/search/query continuity.** It does not list, sort, filter, or paginate continuity records beyond exact-ID reads. Future query semantics require a separate contract.
- **Export/restore continuity inclusion.** It does not produce export manifests or handle restore ID remapping.
- **User-facing UI implementation.** This contract defines interpretive semantics — not render surfaces, layout tokens, accessibility requirements, or visual design.
- **Supported beta activation.** It does not expose Pulse output in the supported beta profile `v1-local-core-web-mcp`.
- **A replacement for `00-current-state.md`.** The current-state file remains the short-horizon release-truth authority.
- **A replacement for operator diagnostics.** Diagnostics is aggregate count/gate truth. Pulse is interpretive summary. They are distinct surfaces.
- **Proof that live runtime behavior has been rerun.** This contract defines semantics, not evidence.

## Governing Sources

This contract is governed by and must remain aligned with:

| Source | Role |
|---|---|
| ADR-015 Continuity Engine Working Set and Decay Contract | Continuity doctrine, working-set decay, provenance, imported-history scaffolding |
| ADR-016 Continuity Governance Surface Contract | User-governed control plane: scope, intensity, decay, exclusions, import treatment, inspection, reset |
| ADR-030 Continuity Protocol Suite Runtime Gate | Overall continuity runtime gate and approved implementation order |
| ADR-031 Continuity Phase A Storage Migration Gate | Phase A storage migration boundary |
| `continuity-protocol-suite.md` | Project Pulse vocabulary definition as UI/output surface, not storage |
| `continuity-operator-diagnostics-truth-surface-contract.md` | Diagnostics boundary Pulse must not collapse into narrative |
| `continuity-operator-loop-proof-chain.md` | Proven evidence chain Pulse may cite as metadata |
| `continuity-operator-readback-route-contract.md` | Exact-ID readback contract defining read semantics |
| `continuity-operator-state-commit-link-readback-contract.md` | Staged state/commit/link readback contracts |
| `continuity-write-action-contract.md` | Write action definitions Pulse must never invoke |
| `00-current-state.md` | Short-horizon release-truth authority |

## Definition

Project Pulse is a **read-only interpretive brief contract**. It defines the semantics for answering bounded questions about project state from governed Continuity records, without creating new records or altering runtime behavior.

It may answer questions such as:

- What is the current reported project state, derived from the latest persisted Reality State?
- What continuity records (packets, states, commits, links) support that state?
- What changed recently, if continuity records show a state transition or new commit?
- What evidence is stale (last-updated timestamp is old), missing (no record found), or unavailable (source surface is not readable)?

It must not answer by:

- Guessing when records are absent
- Inventing records to fill gaps
- Mutating continuity state to make it "look cleaner"
- Treating missing evidence as implicit truth (absence of record ≠ absence of fact)
- Converting diagnostics counts into narrative claims
- Pretending compiled state is live runtime truth

## Core Question

> What can be safely summarized from the current governed Continuity records without creating new continuity state?

Every future implementation decision for Project Pulse must return to this question. If an interpretive output requires creating a record, calling a write action, invoking a compiler, or inferring beyond available evidence, it is not a Pulse output — it is a different surface.

## Source Surfaces

Project Pulse distinguishes four categories of source truth. Each category carries different evidentiary weight and must be cited separately in Pulse output.

### 1. Record Surfaces (Primary)

| Surface | What It Provides | Evidentiary Weight |
|---|---|---|
| `continuity_reality_states` | Compiled Reality State for a scope | Direct evidence — the stored truth surface |
| `continuity_context_packets` | Individual context packets with payload, provenance, sensitivity, and retention | Direct evidence — source records for Reality State |
| `continuity_reality_commits` | Durable state-transition records with trigger, kind, and provenance | Direct evidence — change history |
| `continuity_state_packet_links` | Provenance links between states and packets | Direct evidence — provenance relationships |

Access is via the persistence adapter only. Exact-ID reads are the only allowed read pattern under current contracts. Future list/search/query behavior is out of scope unless separately governed.

### 2. Proof Surfaces (Metadata)

| Surface | What It Provides | Evidentiary Weight |
|---|---|---|
| Loop proof chain | Proven evidence rows for operator surface | Metadata — confirms what was proven, not what is true now |
| Live proof artifacts | Route-specific live proof results | Metadata — scoped to tested profile/commands/environment |
| Hardening regression rerun | Regression guardrail pass/fail | Metadata — confirms no surface drift |

Proof surfaces inform Pulse about what has been verified, not about what the continuity records currently contain. They may appear as a "proven" flag or verification timestamp in Pulse output, but they must not substitute for record reads.

### 3. Diagnostics Surfaces (Verification)

| Surface | What It Provides | Evidentiary Weight |
|---|---|---|
| Aggregate counts | Row counts for all four Phase A tables | Verification — confirms how many records exist, not what they mean |
| Gate posture | Feature flag status, profile quarantine status | Verification — confirms which gates are open or closed |
| Hard-false flags | `graph_used`, `runtime_event_published`, `project_pulse_enabled`, `export_restore_enabled` | Verification — confirms what is not yet active |

Diagnostics provide aggregate truth, not narrative truth. A count of 0 packets means "0 packets exist," not "nothing happened." A count of 5 states means "5 states exist," not "the project is in good shape."

### 4. Release-Truth Surfaces (Boundary)

| Surface | What It Provides | Evidentiary Weight |
|---|---|---|
| `00-current-state.md` | Current release readiness, supported path, active blockers | Boundary — defines what can and cannot be claimed |
| Supported profile manifests | Which profiles expose which surfaces | Boundary — defines quarantine/activation state |

Release-truth surfaces constrain what Pulse may claim. If `00-current-state.md` says Continuity is test-only, Pulse must not present continuity as supported beta. If the active profile is `v1-local-core-web-mcp`, Pulse must not surface operator-gated content.

## Read Model

Project Pulse is read-only. The following rules govern all future reads:

| Rule | Behavior |
|---|---|
| Exact-ID reads only | Pulse may read records by explicit ID only. No list, search, filter, sort, or paginate unless separately governed by a future list/search contract. |
| No graph traversal | Pulse must not query Neo4j, traverse relationships, or expand record graphs. `graph_used` must remain `false`. |
| No relationship expansion | Reading a state must not auto-fetch linked packets. Reading a commit must not traverse commit history. Reading a link must not expand to linked records. |
| No background collection | Pulse must not periodically scan tables, pre-compute briefs, or cache interpretations. |
| No passive capture | Pulse must not read records as a side effect of chat turns, worker cycles, or provider calls. |
| No automatic Reality Stamp write | Pulse must not write records to fill gaps in evidence. Missing evidence is surfaced as missing, not patched. |
| Adapter-only access | All reads must go through the persistence adapter. No direct SQLAlchemy queries that bypass soft-delete filters, session management, or contract validation. |
| Soft-delete aware | Default reads must exclude `deleted_at IS NOT NULL` records unless explicitly requested by a future admin/audit contract. |
| No write imports | The read module must not import `ContinuityWriteActionService`, write actions, or compiler persistence functions. An AST/import audit must confirm zero write references. |

## Interpretation Model

Project Pulse interprets records, it does not replay them. The following rules govern interpretation:

### Summarization Rules

| Rule | Behavior |
|---|---|
| Summarize only from available records | Pulse output must be exclusively derived from records that exist and are readable at interpretation time. |
| Distinguish observed record facts from inferred summary | Every claim in Pulse output must be traceable to a source record or a bounded inference with explicit confidence annotation. |
| Cite source categories internally | The output model must declare which claims come from record surfaces, proof surfaces, diagnostics surfaces, or release-truth surfaces. |
| Mark stale evidence explicitly | If a record's `created_at` or `compiled_at` timestamp is older than a configurable freshness threshold, mark it as stale. |
| Mark missing evidence explicitly | If a source surface has no records for a given scope, mark that surface as "no records available." |
| Mark conflicting evidence explicitly | If two records disagree (e.g., two Reality States for the same scope with different summaries), surface the conflict rather than flattening it. |
| Do not convert diagnostics counts into narrative facts | "5 states exist" is a count. "The project has made good progress" is a narrative claim. Pulse must not derive the second from the first. |
| Do not treat missing records as proof of absence | A missing Reality State means "no readable Reality State available," not "nothing changed." A missing Context Packet means "supporting packet unavailable," not "the claim is unsupported." |
| Do not treat route presence as release support | If a route exists in code but is quarantined by profile, Pulse must not present that surface as available. |
| Do not treat docs presence as runtime proof | If a contract defines a surface but no live proof exists, Pulse must not present that surface as verified. |
| Do not treat tests as live Docker Compose proof | Test coverage is not live supported-path proof unless a live proof artifact confirms it. |

### Confidence Boundaries

Every Pulse output must include an explicit confidence boundary:

- **High confidence:** Claim is directly backed by a current (non-stale) record with complete provenance.
- **Medium confidence:** Claim is backed by a record but the record is stale or has incomplete provenance.
- **Low confidence:** Claim is inferred from multiple records, extrapolated from partial data, or relies on diagnostics/proof metadata rather than record truth.
- **No confidence:** Claim is explicitly missing evidence — no record exists for the queried scope.

## Output Model

The following conceptual output shape defines what a future Project Pulse brief may contain. This is a contract candidate only — no Pydantic model, API response shape, or UI component is specified.

### Conceptual Fields

| Field | Purpose | Source Category |
|---|---|---|
| `pulse_id` | Future stable brief identity | Contract-only token; not yet registered |
| `project_scope` | The project, thread, or workspace scope this brief covers | Release-truth / governance |
| `generated_at` | ISO-8601 timestamp of brief generation | System metadata |
| `source_window` | The time range of records consulted (oldest and newest timestamps) | Record surfaces |
| `summary` | Human-readable interpretive summary derived from available records | Record surfaces (interpreted) |
| `current_reality` | The latest Reality State fields relevant to the scope (summary, open loops, rejected paths, next actions) | Record surfaces (direct read) |
| `recent_changes` | Recent Reality Commits or state transitions, if any | Record surfaces (direct read) |
| `supporting_records` | Source record IDs and families referenced in this brief | Record surfaces (provenance) |
| `stale_or_missing_evidence` | Explicit list of scope/surface pairs where records are stale, missing, or unavailable | Record surfaces (gap analysis) |
| `diagnostics_snapshot` | Aggregate counts and gate posture at generation time | Diagnostics surfaces |
| `confidence_boundary` | Per-claim confidence rating with source justification | Interpretation model |
| `non_claims` | Explicit list of what this brief does **not** claim or assert | Interpretation model |

Field names are contract candidates only. If an existing governing token/domain proposal (`continuity-token-domain-proposal.md`) or canonical token registry already defines exact tokens for any of these concepts, future implementation must use the registered tokens.

### What the Output Must Not Include

- Raw packet payloads (payloads belong to exact-ID readback, not Pulse)
- Raw DB IDs as portable identity (local IDs are not export identity)
- Secrets, API keys, or authentication material
- Model inference output (Pulse summarizes records, it does not call a provider)
- Compiler output (Pulse reads stored Reality States, it does not compile new ones)
- Graph IDs, graph traversal results, or Neo4j metadata
- Runtime events or task event identifiers

## Freshness and Staleness

Project Pulse must not present stale evidence as current.

| Rule | Behavior |
|---|---|
| Expose record timestamps | Every record consulted for a Pulse output must have its `created_at`, `compiled_at`, or `committed_at` timestamp available in the output model. |
| Mark stale records as stale | If a record's age exceeds a configurable threshold (not defined by this contract — deferred to future governance/implementation), it must be marked as stale. |
| Do not silently normalize staleness | A stale Reality State must remain visible as stale. Pulse must not "touch up" old records or fill gaps with fresher-looking inferences. |
| Degrade confidence for staleness | Stale records should reduce the confidence boundary for claims derived from them. |
| State freshness explicitly | The `source_window` field must declare the oldest and newest record timestamps. |
| No automatic refresh | Pulse must not trigger a Reality Stamp write, a compiler invocation, or any persistence action to "refresh" stale evidence. |

## Missing Evidence Behavior

Project Pulse must fail-closed when evidence is missing.

| Gap | Interpretation | Output |
|---|---|---|
| No Reality State for scope | "No readable Reality State available for this scope" | Mark as missing in `stale_or_missing_evidence`; set confidence boundary low or none |
| No Context Packets for scope | "No supporting Context Packets available for this scope" | Mark as missing; do not fabricate supporting records |
| No Reality Commits for scope | "No state transition history available for this scope" | Mark as missing; do not infer change from absence |
| No state-packet links for a state | "Provenance links unavailable for this state" | Mark as missing; do not guess source packets |
| Conflicting Reality States | Two states for the same scope with different summaries | Surface as conflict; include both record IDs and timestamps; do not flatten |
| Diagnostics unavailable | "Diagnostics data unavailable" (e.g., route not exposed, flag off) | Mark as unavailable; do not substitute with assumed counts |
| Feature flag off | "Continuity operator routes not active" | Mark in diagnostics snapshot; do not read any records |
| Profile quarantined | "Operator routes quarantined under active profile" | Mark; do not attempt reads |
| Stale + missing combination | Some records present but stale; some surfaces missing entirely | Distinguish the two in output; stale records get stale markers; missing surfaces get missing markers |

## Diagnostics Boundary

Project Pulse must preserve the diagnostics boundary defined in `continuity-operator-diagnostics-truth-surface-contract.md`.

| Rule | Behavior |
|---|---|
| Diagnostics are aggregate/count/gate posture truth | They answer "how many?" and "which gates are open?" — not "what does this mean?" |
| Project Pulse may include a diagnostics snapshot section | This is strictly a pass-through of aggregate diagnostics data at generation time. |
| Project Pulse must not turn aggregate counts into narrative state | "5 packets exist" must not become "the project has 5 active areas of work." |
| Diagnostics do not replace record reads | A count of 0 Reality States is not a substitute for reading a Reality State. Diagnostics is verification, not interpretation. |
| Diagnostics do not prove semantic meaning | A count of 3 commits does not mean "3 meaningful changes occurred." It means "3 commit records exist." |
| Diagnostics do not authorize writes | A count of 0 packets does not authorize Pulse to create one. |
| Hard-false flags remain hard-false | `project_pulse_enabled=false` in diagnostics means Pulse itself is not active. If Pulse output includes a diagnostics snapshot, it must report this flag honestly. |
| `project_pulse_enabled` flag distinction | This flag in diagnostics means "Project Pulse is separately activated and running." Pulse interpreting a diagnostic snapshot must distinguish between "Pulse is reading diagnostics" and "Pulse is itself activated as a runtime surface." |

## Provenance Requirements

Every future Project Pulse output must preserve provenance so a user or operator can trace every claim back to its source.

| Requirement | Behavior |
|---|---|
| Source record IDs | Where available, include the IDs of records consulted. |
| Source record family | Indicate whether a claim derives from a packet, state, commit, or link. |
| Timestamp | Include the record's creation or compilation timestamp. |
| Freshness status | Mark each source record as current, stale, or unavailable. |
| Evidence category | Distinguish: record truth, proof metadata, diagnostics data, release-truth boundary, or interpretive summary. |
| Local DB IDs | Must not be treated as portable export identity unless a future export/restore contract defines ID mapping. |
| Schema version | If available from the record, include the schema version at write time. |

## User Control and Visibility

Project Pulse must remain user-governed, consistent with ADR-015 and ADR-016.

| Requirement | Behavior |
|---|---|
| Inspectable by operator/user | Pulse output must be visible to the user or operator who requested it. |
| Expose what it read | The output model must declare which records were consulted. |
| Expose what it did not read | The output model must declare which source surfaces were not consulted and why (missing, stale, quarantined, flag-off). |
| No hidden evidence smoothing | Missing evidence must not be hidden behind polished summaries. |
| "Why did you say this?" path | A future implementation must support an inspection path that lets the user trace a claim back to its source record IDs. |
| Governance-respecting | Pulse must respect scope, intensity, decay, exclusion, and import-treatment settings from ADR-016. Excluded material must never appear in Pulse output. Imported scaffolds must be tagged as imported |
| Reset-aware | If continuity has been reset or paused (ADR-016), Pulse must reflect that state and not present stale pre-reset records as current unless explicitly requested. |

## Safety Boundaries

Project Pulse must not cross these safety boundaries:

| Boundary | Rule |
|---|---|
| No durable identity inference | Pulse must not derive persona traits, identity claims, or deep-identity assertions from continuity records. |
| No persona ownership of continuity | Persona switching must not silently inherit another persona's Pulse output. Project continuity is not persona identity. |
| No memory mutation | Pulse must not alter memory storage, fact tables, or diary entries. |
| No chat-history-as-identity collapse | Pulse must not treat chat history as an identity claim. |
| No hidden Project Reality writes | Pulse is read-only. It must not create or update Reality States, commits, packets, or links. |
| No automatic decay/intensity changes | Pulse must not alter continuity-governance settings. Observing stale evidence does not authorize changing decay policy. |
| No cross-project leakage | Pulse scoped to one project must not surface records from another project unless scope governance explicitly permits it. |
| No import-status laundering | Imported records must remain tagged as imported. Pulse must not present scaffold continuity as native lived continuity. |

## Release Boundary

Project Pulse is contract-only in this task.

- **It is not supported beta behavior.** The supported beta profile `v1-local-core-web-mcp` must not expose any Pulse route or UI.
- **It does not widen the supported beta promise.** No release claim has changed.
- **It does not activate Continuity outside `test-continuity`.** The operator surface remains test-only and profile-quarantined.
- **It does not override `00-current-state.md`.** The current-state file remains the short-horizon release-truth authority.
- **It does not imply UI, routes, runtime support, or live proof.** This contract defines semantics only. Implementation is a separate future task.

## Future Implementation Constraints

Future implementation of Project Pulse must be separate architecture-impact tasks and must independently decide:

| Decision | Governance |
|---|---|
| Whether Pulse has a backend route | Route creation requires a separate task with profile activation contract, auth boundary, and live proof |
| Whether Pulse has UI | UI requires a separate task with token/layout law compliance, accessibility review, and design spec |
| Whether Pulse uses exact-ID reads only or gets a query surface | Query semantics require a separate list/search contract beyond this document |
| Whether Pulse can read only local continuity records | Cross-instance reads require a federation/sync contract |
| Whether Pulse may appear in diagnostics or a future Project Reality surface | Surface placement requires separate docs without collapsing diagnostics |
| What tokens/registries are required | Token-domain alignment per `continuity-token-domain-proposal.md` and `canonical-token-philosophy.md` |
| What tests prove read-only behavior | Tests require a separate task; no-write tests, AST audits, graph-off baseline |
| What live proof is required before release claim | Live supported-path proof on Docker Compose with real Postgres |

Additionally, future implementation must not:

- Bundle Pulse implementation with any write path, route expansion, profile activation, or UI surface
- Implement Pulse before a separate architecture-impact task explicitly authorizes implementation
- Claim Pulse as supported beta unless a separate release-scope change authorizes it

## Evidence Boundary

The following governing files were present and inspected during this task:

| File | Status |
|---|---|
| `docs/architecture/00-current-state.md` | Present — confirms test-only quarantined Continuity surface |
| `docs/architecture/README.md` | Present — Continuity documentation list |
| `docs/architecture/adr/adr-index.md` | Present — ADR index |
| `docs/architecture/adr/015-continuity-engine-working-set-and-decay-contract.md` | Present — continuity doctrine, decay, provenance |
| `docs/architecture/adr/016-continuity-governance-surface-contract.md` | Present — user-governed control plane |
| `docs/architecture/adr/030-continuity-protocol-suite-runtime-gate.md` | Present — overall continuity runtime gate |
| `docs/architecture/adr/031-continuity-phase-a-storage-migration-gate.md` | Present — Phase A storage migration gate |
| `docs/architecture/continuity-protocol-suite.md` | Present — Project Pulse vocabulary definition |
| `docs/architecture/continuity-token-domain-proposal.md` | Present — candidate token domains |
| `docs/architecture/continuity-storage-schema-proposal.md` | Present — Phase A table definitions |
| `docs/architecture/continuity-write-action-contract.md` | Present — write action definitions (must not be called) |
| `docs/architecture/continuity-operator-readback-route-contract.md` | Present — exact-ID packet readback contract |
| `docs/architecture/continuity-operator-state-commit-link-readback-contract.md` | Present — staged state/commit/link readback contracts |
| `docs/architecture/continuity-operator-diagnostics-truth-surface-contract.md` | Present — diagnostics boundary |
| `docs/architecture/continuity-operator-loop-proof-chain.md` | Present — proven evidence chain |
| `docs/architecture/2026-06-25-continuity-operator-phase-narrative-log.md` | Present — phase narrative log |
| `docs/architecture/2026-06-26-continuity-operator-evidence-reconciliation.md` | Present — evidence re-grounding report |

No files were missing. No evidence was invented.

**Worktree:** `/Users/chriscastillo/.codex/worktrees/aaba/Codexify-main`
**Branch:** `main`
**HEAD:** `1832d87647`

## ADR Impact

- **Classification:** Aligned with existing ADR(s); no new ADR required.
- **Governing ADRs/contracts:**
  - ADR-015 Continuity Engine Working Set and Decay Contract
  - ADR-016 Continuity Governance Surface Contract
  - ADR-030 Continuity Protocol Suite Runtime Gate
  - ADR-031 Continuity Phase A Storage Migration Gate
  - `continuity-protocol-suite.md`
  - `continuity-operator-diagnostics-truth-surface-contract.md`
  - `continuity-operator-loop-proof-chain.md`
  - `00-current-state.md`
- **Reason:** This task defines a read-only interpretive contract above the proven Continuity substrate. It does not change runtime behavior, storage semantics, route semantics, supported-profile posture, release scope, identity boundaries, or provenance guarantees. Project Pulse is already named and scoped in `continuity-protocol-suite.md` and ADR-030's approved implementation order (step 7: "Project Pulse UI spec"). This contract defines the interpretive semantics for that step without implementing any runtime behavior.

## Current-Truth Anchors

### What Is True Now

- The Continuity operator substrate is proven on `main` per the re-grounded reconciliation report (`2026-06-26-continuity-operator-evidence-reconciliation.md`).
- The Continuity operator surface remains test-only, API-key-gated, and profile-quarantined under `test-continuity`.
- `00-current-state.md` remains the release-truth authority.
- Six operator routes exist behind explicit gates.
- Diagnostics returns aggregate counts/gate posture, not narrative summaries.
- Exact-ID readbacks are proven; no list/search semantics exist.
- Project Pulse is not implemented by this task.

### What Is Not Yet True

- Project Pulse is not runtime behavior.
- Project Pulse is not supported beta.
- Project Pulse is not UI.
- Project Pulse is not export/restore inclusion.
- Project Pulse is not list/search continuity.
- Project Pulse is not graph traversal.
- Project Pulse is not chat runtime continuity.
- Project Pulse is not worker/command bus/provider/retrieval/browser/sync integration.

### What This Task May Assume

- Defining the read-only interpretive contract is the next safe architecture step after continuity evidence re-grounding.
- The contract defines semantics for ADR-030's step 7 (Project Pulse UI spec) without implementing it.

## Invariants

The following invariants are mandatory for this contract and all future Project Pulse implementation:

- **No writes.** Pulse must not create, update, or delete any continuity record.
- **No ambient memory.** Pulse must not auto-generate briefs as a side effect of ordinary system behavior.
- **No implicit continuity mutation.** Pulse must not alter scope, intensity, decay, or governance settings.
- **No runtime behavior change.** This contract does not alter any existing route, worker, or service.
- **No route creation.** No Pulse route is defined or implemented by this contract.
- **No schema or migration creation.** No new tables, columns, or indexes are authorized.
- **No supported beta widening.** The supported beta profile remains quarantined.
- **No Project Reality write semantics.** Pulse reads Reality State; it does not create or update it.
- **No diagnostics-to-narrative collapse.** Aggregate counts must not become narrative claims.
- **No graph traversal.** Pulse must not query Neo4j or traverse relationships.
- **No export/restore semantics.** Pulse does not produce export manifests or handle restore remapping.
- **No chat runtime continuity.** Pulse does not feed into the context broker or completion assembly.
- **No hidden identity inference.** Pulse must not derive persona traits or identity claims.
- **No source laundering from stale/missing evidence.** Stale and missing records must remain visible as such.

## Proof Surface

The proof surface for this task is documentation validation only:

- The new contract exists at `docs/architecture/project-pulse-read-only-contract.md`.
- All required headings and boundary definitions are present.
- The `README.md` links the contract correctly in the Continuity reading path.
- No runtime proof is claimed. No tests are added. No live Docker Compose proof is rerun.

## Validation

Run from repo root:

```
test -f docs/architecture/project-pulse-read-only-contract.md
grep -q "# Project Pulse Read-Only Contract" docs/architecture/project-pulse-read-only-contract.md
grep -q "read-only" docs/architecture/project-pulse-read-only-contract.md
grep -q "not supported beta" docs/architecture/project-pulse-read-only-contract.md
grep -q "not Project Reality" docs/architecture/project-pulse-read-only-contract.md
grep -q "not export/restore" docs/architecture/project-pulse-read-only-contract.md
grep -q "not list/search" docs/architecture/project-pulse-read-only-contract.md
grep -q "not graph traversal" docs/architecture/project-pulse-read-only-contract.md
grep -q "not chat runtime continuity" docs/architecture/project-pulse-read-only-contract.md
grep -q "Diagnostics Boundary" docs/architecture/project-pulse-read-only-contract.md
grep -q "Missing Evidence Behavior" docs/architecture/project-pulse-read-only-contract.md
grep -q "Project Pulse Read-Only Contract" docs/architecture/README.md
git diff --check -- docs/architecture/project-pulse-read-only-contract.md docs/architecture/README.md
```

No automated runtime tests apply.
