# UMS-03H — Legacy Memory Compatibility Coverage Proof

- **Slice:** UMS-03H (coverage closure)
- **Date:** 2026-09-08
- **Execution lane:** Architecture-Impact
- **Task kind:** architecture/runtime coverage proof
- **Starting HEAD:** `d12334cfe68b7a6703d8cbd7f72d0dcfc2be4e25` (UMS-03H-R)
- **UMS-03H-R prerequisite SHA:** `d12334cfe68b7a6703d8cbd7f72d0dcfc2be4e25`
- **UMS-03G semantic prerequisite SHA:** `774d71ca0bdf219c714ab2ad2c6f2db837a7081e`
- **Alembic head before / after:** `f6b0d3e8c5a2` / `f6b0d3e8c5a2` (unchanged)
- **Local safety ref preserved:** `recovery/ums03e-conflated-71fd9f4d5`
  → `71fd9f4d5f4f2d05eb97c829a0097039c5fb0cae` (UMS-03E reconciliation
  artifact, untouched)

## Objective

Determine whether every legacy durable memory authority or state
identified by the frozen UMS-03A inventory is covered by the
existing UMS-03E/F/G compatibility adapters, by subordinate
lineage representation, or by explicit contractual exclusion —
with zero unmapped blockers.

## Frozen UMS-03A source inventory (reconstructed from contract + UMS-03A proofs)

The frozen UMS contract §4.6 (lines 590–598) and the §4.13
compatibility-read matrix (lines 899–906) name the following
admitted legacy source/state families:

| § | Source/State | Physical Authority | Owner | Project | Persona | Lifecycle | Provenance | Run-time Consumer | Write Authority |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 4.6.1 / 4.13 | `memory_entries` (any `silo`) | `memory_entries` table, FK `users.id` CASCADE | `user_id` | none | none | `silo ∈ {ephemeral, midterm, longterm}`; `pinned`; mutable `content` | none | `guardian.core.pgdb` CRUD; `guardian.routes.memory`; `guardian.context.broker` semantic lane | `guardian.routes.memory`; external Memoryos |
| 4.6.2 / 4.13 | `personal_facts` (verified + active) | `personal_facts` table, app-level FK | `user_id` | none | none | `status='verified' AND is_active=true` | indirect via `personal_fact_evidence.source_type` | `guardian.routes.personal_facts`; `guardian.context.broker` (verified+active per ADR-013) | `guardian.services.personal_facts` |
| 4.6.2 / 4.13 | `personal_facts` (candidate/disputed/archived/inactive) | `personal_facts` table, app-level FK | `user_id` | none | none | `status ∈ {candidate, disputed, archived}` OR `is_active=false` | `personal_fact_evidence.source_type` distinguishes live-chat vs import vs user_stated | Personal Facts service | `guardian.fact_candidate_pipeline` (live chat); import pipeline; Vault explicit remember |
| 4.6.3 / 4.13 | `personal_fact_evidence` | `personal_fact_evidence` table, FK `personal_facts.id` CASCADE | via fact_id | none | none | append-only via `fact_id` | `source_type ∈ {chatgpt_import, runtime_extraction, user_stated, user_corrected, claude_import}`; nullable FK to `chat_messages`; `evidence_meta` (JSONB); `modality`; `excerpt` | Personal Facts service; broker evidence rendering | Personal Facts service |
| 4.6.4 / 4.13 | `personal_fact_revisions` | `personal_fact_revisions` table, FK `personal_facts.id` CASCADE | via fact_id | none | none | append-only | `actor`; `action`; `field_changed`; `old_value`; `new_value`; `reason`; `created_at` | Personal Facts service | Personal Facts service |
| 4.6.5 / 4.13 | `Memoryos` library state | external library `guardian/memoryos/`, file-backed JSON (NOT Postgres) | embedded account-keyed file paths | none | none | library-internal heat-based retention | library-internal | Memoryos `Retriever`; chat completion prompt assembly | Memoryos `Updater` |

Contract governing sections: `docs/architecture/unified-memory-store-contract.md`
§4.6 lines 590–598; §4.13 lines 899–906; §4.6 notes lines 600–624.

## Current-code re-inventory

`Base.metadata.tables` was re-inventoried on the current
reconciled `main`. The durable memory-like tables are:

```text
memory_entries              (legacy UMS-03E compatibility)
memory_records              (UMS-03D canonical substrate, non-authoritative)
memory_provenance           (UMS-03D canonical substrate, non-authoritative)
memory_persona_links        (UMS-03D canonical substrate, non-authoritative)
personal_facts              (legacy UMS-03F/G compatibility)
personal_fact_evidence      (subordinate provenance to personal_facts)
personal_fact_revisions     (historical lineage of personal_facts)
persona_profile_revisions   (Persona Profile audit lineage per ADR-082)
agent_run_artifacts         (agent run output, not user-knowledge memory)
```

`guardian/memoryos/` persistence was inspected. Short-term,
mid-term, and long-term memory use JSON file persistence under
`self.file_path` (`open(..., "w")` / `json.dump(...)`). No
SQLAlchemy, no Postgres, no `personal_facts` writes. This
matches the contract's note at line 616–620 that Memoryos
"is not currently Postgres-backed, its storage shape is
library-internal, and its reconciliation into the canonical
envelope is explicitly deferred".

The candidate pipeline (`guardian/fact_candidate_pipeline.py`)
line 11: "Candidates are stored as status='candidate' in
`personal_facts`". The OpenAI account import flow uses
`AccountImportJob` status transitions but ultimately routes
facts through the Personal Facts service into `personal_facts`
rows. No fourth durable memory authority exists.

`guardian/context/broker.py` imports `MemoryOSRetriever` from
`guardian.memoryos.retriever` (pre-existing, not part of UMS-03
scope). It does not consume canonical UMS tables
(`memory_records` etc.) and does not consume compatibility
projections.

## Classification of every durable memory-like source

| Source | Bucket | Notes |
| --- | --- | --- |
| `memory_entries` | A. admitted independent legacy memory authority | COVERED by UMS-03E |
| `personal_facts` (verified + active subset) | A. admitted independent legacy memory authority | COVERED by UMS-03F |
| `personal_facts` (candidate/disputed/archived/inactive subset) | A. admitted independent legacy memory authority | COVERED by UMS-03G |
| `personal_fact_evidence` | B. subordinate evidence/provenance | SUBORDINATE_LINEAGE_COVERED (lives inside Personal Fact projections) |
| `personal_fact_revisions` | C. subordinate revision/history | SUBORDINATE_LINEAGE_COVERED (lives inside Personal Fact projections) |
| `Memoryos` library state | n/a (deferred) | EXPLICITLY_EXCLUDED_BY_CONTRACT (§4.13 line 904) |
| `memory_records` | F. canonical UMS persistence introduced by UMS-03D | non-authoritative structural persistence; not a legacy source |
| `memory_provenance` | F. canonical UMS persistence introduced by UMS-03D | non-authoritative structural persistence; not a legacy source |
| `memory_persona_links` | F. canonical UMS persistence introduced by UMS-03D | non-authoritative structural persistence; not a legacy source |
| `persona_profile_revisions` | G. receipt/audit persistence | ADR-082 Persona Profile audit trail; not a UMS-03A legacy source |
| `agent_run_artifacts` | D. derived operational state | agent run output; not user-knowledge memory |

The candidate pipeline routes into `personal_facts` and the
import pipeline routes facts through Personal Facts into
`personal_facts`. They do not introduce additional durable
authorities. They are therefore covered by the same
compatibility predicates as the Personal Fact families.

## Final coverage matrix

| Source/State | Physical Authority | Semantic Species | Projection Function | Evidence/Revision Treatment | Project | Persona | Review/Lifecycle | Canonical Write | Verdict |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `memory_entries` (any `silo`) | `memory_entries` | `episodic_semantic_memory` | `read_memory_entry_projection` | n/a | absent | zero links | ambient-eligible by default; `silo` is retention class only | no | **COVERED** |
| `personal_facts` (verified + active) | `personal_facts` | `verified_personal_fact` | `read_verified_personal_fact_projection` | evidence + revision preserved | absent | zero links | approved, active; `ambient_eligible=True` | no | **COVERED** |
| `personal_facts` (candidate/disputed/archived/inactive) | `personal_facts` | `candidate_unreviewed_fact` | `read_candidate_personal_fact_projection` | evidence + revision preserved | absent | zero links | pending/unapproved; `ambient_eligible=False` | no | **COVERED** |
| `personal_fact_evidence` | `personal_fact_evidence` (FK CASCADE to `personal_facts`) | n/a (provenance) | Lives in `MemoryCompatibilityProjection.evidence` (both Personal Fact adapters) | n/a | n/a | n/a | n/a (lineage only) | no | **SUBORDINATE_LINEAGE_COVERED** |
| `personal_fact_revisions` | `personal_fact_revisions` (FK CASCADE to `personal_facts`) | n/a (lineage) | Lives in `MemoryCompatibilityProjection.revisions` (both Personal Fact adapters) | n/a | n/a | n/a | n/a (lineage only) | no | **SUBORDINATE_LINEAGE_COVERED** |
| `Memoryos` library state | external library file JSON | n/a (deferred) | none | n/a | n/a | n/a | library-internal heat retention | n/a | **EXPLICITLY_EXCLUDED_BY_CONTRACT** |

### Verdict counts

```text
TOTAL ADMITTED SOURCE/STATE ROWS = 6

COVERED                          = 3
SUBORDINATE_LINEAGE_COVERED      = 2
EXPLICITLY_EXCLUDED_BY_CONTRACT  = 1
UNMAPPED_BLOCKER                  = 0
```

## Memory-entries coverage (UMS-03E)

- **Projection function:** `read_memory_entry_projection(session, *, authenticated_account_id, memory_entry_id) -> MemoryCompatibilityProjection | None`
- **Eligibility predicate:** `memory_entries.id == :id AND user_id == :authenticated_account_id`
- **Semantic species:** `episodic_semantic_memory` (canonical `MemorySemanticSpecies` token)
- **Owner derivation:** `user_id` (FK `users.id`, NOT NULL, CASCADE)
- **Project posture:** `None` (frozen contract: "absent today → account scope")
- **Persona posture:** `[]` (frozen contract: "absent today → zero links")
- **Provenance:** `source_system='codexify'`, `source_record_id='memory_entries:<id>'`; primary evidence fields not applicable
- **Review/activation:** `ambient_eligible=True` per the frozen §4.10 line 723 default; `silo` is retention class only
- **Legacy source identity:** `legacy_source_family='memory_entries'`, `legacy_source_record_id='memory_entries:<id>'`
- **No-write behavior:** SQL-event listener asserts no INSERT/UPDATE/DELETE/TRUNCATE/MERGE against `memory_records` / `memory_persona_links` / `memory_provenance` / `personal_facts` / `personal_fact_evidence` / `personal_fact_revisions`
- **Evidence source:** `docs/architecture/proofs/runtime/2026-09-07-ums03e-memory-entry-compatibility-proof.md` + `tests/core/test_memory_compatibility.py` test 1–15

**Verdict: COVERED** (all 15 UMS-03E tests pass on current `main`).

## Verified/current Personal Fact coverage (UMS-03F)

- **Projection function:** `read_verified_personal_fact_projection(session, *, authenticated_account_id, personal_fact_id) -> MemoryCompatibilityProjection | None`
- **Eligibility predicate:** `personal_facts.id == :id AND user_id == :authenticated_account_id AND status='verified' AND is_active IS TRUE`
- **Semantic species:** `verified_personal_fact` (canonical `MemorySemanticSpecies` token)
- **Owner derivation:** `user_id`
- **Project posture:** `None`
- **Persona posture:** `[]`
- **Provenance:** `source_system='codexify'`, `source_record_id='personal_facts:<id>'`; primary evidence `source_type` / `source_message_id` / `evidence_meta` / `modality` / `excerpt` from latest `personal_fact_evidence`
- **Review/activation:** `ambient_eligible=True` per frozen §4.10 line 724; Personal Facts remains lifecycle authority
- **Legacy source identity:** `legacy_source_family='personal_facts'`, `legacy_source_record_id='personal_facts:<id>'`
- **No-write behavior:** same SQL-event proof
- **Evidence source:** `docs/architecture/proofs/runtime/2026-09-07-ums03f-verified-personal-fact-compatibility-proof.md` + tests 16–34

**Verdict: COVERED** (all 19 UMS-03F tests pass on current `main`).

## Candidate/unreviewed Personal Fact coverage (UMS-03G)

- **Projection function:** `read_candidate_personal_fact_projection(session, *, authenticated_account_id, personal_fact_id) -> MemoryCompatibilityProjection | None`
- **Eligibility predicate:** `personal_facts.id == :id AND user_id == :authenticated_account_id AND (status IN ('candidate','disputed','archived') OR is_active IS FALSE)`
- **Semantic species:** `candidate_unreviewed_fact` (canonical `MemorySemanticSpecies` token)
- **Owner derivation:** `user_id`
- **Project posture:** `None`
- **Persona posture:** `[]`
- **Provenance:** `source_system='codexify'`, `source_record_id='personal_facts:<id>'`; primary evidence fields from latest `personal_fact_evidence`
- **Review/activation:** `ambient_eligible=False`; review posture remains pending / unapproved regardless of `is_active`; Personal Facts lifecycle authority preserved
- **Legacy source identity:** `legacy_source_family='personal_facts'`, `legacy_source_record_id='personal_facts:<id>'`
- **No-write behavior:** same SQL-event proof
- **Evidence source:** `docs/architecture/proofs/runtime/2026-09-08-ums03g-candidate-personal-fact-compatibility-proof.md` + tests 35–52

**Verdict: COVERED** (all 18 UMS-03G tests pass on current `main`).

The candidate / disputed / archived / inactive source-state
combinations covered by this projection are precisely the
admitted "candidate / unreviewed" subset of the §4.13 line 901
matrix.

## `personal_fact_evidence` classification

`personal_fact_evidence` is owned through its `fact_id` FK to
`personal_facts` (ON DELETE CASCADE). The UMS-03F and UMS-03G
projections both surface the full evidence list as a typed
`MemoryCompatibilityEvidence` collection on
`MemoryCompatibilityProjection.evidence`. The evidence rows do
not have an independent lifecycle from their parent fact;
they are append-only via `fact_id`; they do not independently
participate in current recall authority; deleting or changing
an evidence row does not constitute independent memory
lifecycle.

**Verdict: SUBORDINATE_LINEAGE_COVERED** — the evidence rows
are surfaced through the Personal Fact compatibility
projections' provenance, not as an independent memory authority.

## `personal_fact_revisions` classification

`personal_fact_revisions` is owned through its `fact_id` FK to
`personal_facts` (ON DELETE CASCADE). The UMS-03F and UMS-03G
projections both surface the full revision list as a typed
`MemoryCompatibilityRevision` collection on
`MemoryCompatibilityProjection.revisions`. Revisions are
append-only; the current authoritative fact row is never
replaced by an old revision; revisions do not carry
activation authority; old revisions cannot approve a fact or
promote it to current truth.

**Verdict: SUBORDINATE_LINEAGE_COVERED** — the revision rows
are surfaced through the Personal Fact compatibility
projections' lineage, not as an independent memory authority.

## Imported-source classification

`guardian/fact_candidate_pipeline.py` line 11:
"Candidates are stored as status='candidate' in
`personal_facts`". The OpenAI account import flow routes facts
through the Personal Facts service into `personal_facts` rows.
No durable import authority exists outside `personal_facts`
and its evidence / revision lineage. Import provenance lives
in `personal_fact_evidence.source_type` and is read through
both Personal Fact compatibility projections.

**Verdict: SUBORDINATE_LINEAGE_COVERED** (via the Personal Fact
projections' evidence provenance and lineage). Import
provenance does not create a fourth semantic species and
does not mint verification or activation authority.

## Disputed Personal Fact state classification

Per the frozen §4.13 line 901 / §4.10 line 725 mapping,
`disputed` status falls under the `candidate_unreviewed_fact`
species. The UMS-03G reader accepts disputed rows; tests
40 (`test_disputed_fact_projects_as_candidate`) and the
projection's `status` field surface the disputed state without
promoting it.

**Verdict: COVERED** (by UMS-03G as part of the natural
complement of the verified + active predicate).

## Archived/retired/inactive Personal Fact state classification

Per the frozen §4.13 line 901 / §4.10 line 725 mapping,
`archived` status and `is_active=false` both fall under the
`candidate_unreviewed_fact` species. The UMS-03G reader
accepts archived rows and inactive rows; tests 41 (archived)
and 36 (inactive) and 39 (verified + inactive) confirm the
behavior.

**Verdict: COVERED** (by UMS-03G as part of the natural
complement of the verified + active predicate).

## Additional MemoryOS durable authority inspection

`guardian/memoryos/` is a JSON-file-backed external library
with short_term / mid_term / long_term persistence. It does
NOT use SQLAlchemy, does NOT write to `personal_facts`, does
NOT write to `memory_entries`, and has no Postgres-canonical
state. The frozen §4.6 inventory entry for Memoryos (line 598)
and the frozen §4.13 line 904 entry both explicitly say
"reconciliation into the canonical envelope is explicitly
deferred" / "not safely mappable".

**Verdict: EXPLICITLY_EXCLUDED_BY_CONTRACT** — per §4.13 line
904. The pre-existing `MemoryOSRetriever` integration in
`guardian/context/broker.py` is a retrieval source for the
context broker, not a UMS-03 compatibility consumer.

## Canonical UMS persistence runtime-consumer inspection

`rg -l 'MemoryRecord\b|MemoryProvenance\b|MemoryPersonaLink\b' guardian/` returned only `guardian/db/models.py` (the
class definitions themselves). No runtime file outside the
class definitions imports the canonical UMS substrate
classes. The canonical UMS tables
(`memory_records`, `memory_provenance`,
`memory_persona_links`) remain structural and
non-authoritative at runtime, exactly as the UMS-03D proof
established.

## Compatibility-projection runtime-consumer inspection

`rg -l 'read_memory_entry_projection|read_verified_personal_fact_projection|read_candidate_personal_fact_projection|MemoryCompatibilityProjection' guardian/` returned only
`guardian/core/memory_compatibility.py` (the implementation
module itself). No runtime consumer exists under
`guardian/context/`, `guardian/memoryos/` orchestration,
`completion/runtime`, `routers`, or `workers`.
`tests/core/test_memory_compatibility.py` is the only test
consumer. Documentation references are not runtime consumers.

The pre-rebaseline state holds exactly: compatibility
projections are definition + test + documentation; they have
no live runtime consumer.

## Semantic species coverage (taxonomy)

All three canonical semantic species have at least one
valid legacy compatibility path:

| Species | Compatibility Path |
| --- | --- |
| `episodic_semantic_memory` | UMS-03E `read_memory_entry_projection` |
| `verified_personal_fact` | UMS-03F `read_verified_personal_fact_projection` |
| `candidate_unreviewed_fact` | UMS-03G `read_candidate_personal_fact_projection` |

## Compatibility test results (current `main`)

```text
tests/core/test_memory_compatibility.py  52 passed in 0.73s
  0 failed
  0 errors
  0 skipped
```

The exact pre-rebaseline count (52) is preserved. No semantic
regression, no skip, no error.

## Adjacent UMS regression results

```text
tests/contracts/test_protocol_tokens.py  35 passed
tests/core/test_persona_subjects.py     11 passed
                                        46 passed in 0.56s
```

Pre-rebaseline count (46) is preserved.

## Alembic topology

```text
f6b0d3e8c5a2 (head)
```

Single head, unchanged. No post-UMS-03D migration was added.

## Closure verdict

```
LEGACY_MEMORY_COMPATIBILITY_INVENTORY_CLOSED
```

**UNMAPPED_BLOCKER = 0.**

Every admitted legacy source/state is exactly one of:

- `COVERED` (3 rows: `memory_entries`, verified + active
  Personal Facts, candidate / disputed / archived / inactive
  Personal Facts)
- `SUBORDINATE_LINEAGE_COVERED` (2 rows:
  `personal_fact_evidence`, `personal_fact_revisions`)
- `EXPLICITLY_EXCLUDED_BY_CONTRACT` (1 row: `Memoryos`
  library state, per §4.13 line 904)

UMS-03I is now authorized to introduce one bounded unified
compatibility read surface that composes the three proven
projections. UMS-03I is **not** authorized to redirect live
ContextBroker / MemoryOS / completion retrieval; that is a
later gate.

## ADR impact

Aligned with ADR-081, ADR-082, and ADR-084. No new ADR. No new
architecture decision. ADR-083 remains unissued/retired per
the canonical registry. No canonical durable `memory_id` was
fabricated for any compatibility-only row.

## Confirmed non-claims

- No production code was changed by UMS-03H.
- No test was changed by UMS-03H.
- No ORM model or migration was changed by UMS-03H.
- No retrieval / router / MemoryOS / ContextBroker consumer
  was added by UMS-03H.
- No canonical runtime writer was added.
- No export / restore behavior was changed.
- No release / Beta claim was widened.
- Nothing was pushed or merged.
- The local safety ref
  `recovery/ums03e-conflated-71fd9f4d5` remains preserved.
- The Pi fixture remains untouched and unstaged.

## Required successful state

```
UMS-03D CANONICAL MEMORY PERSISTENCE: CLOSED
UMS-03E MEMORY-ENTRY COMPATIBILITY PROJECTION: CLOSED
UMS-03F VERIFIED PERSONAL-FACT COMPATIBILITY: CLOSED
UMS-03G CANDIDATE PERSONAL-FACT COMPATIBILITY: CLOSED
UMS-03H-R RECONCILED-MAIN REBASELINE: CLOSED
UMS-03H LEGACY MEMORY COMPATIBILITY COVERAGE: CLOSED
UMS-03: OPEN
UMS-03I UNIFIED COMPATIBILITY READ SURFACE: AUTHORIZED TO START
UMS-04: NOT AUTHORIZED
RUNTIME/RELEASE IMPACT: NONE

COMPATIBILITY INVENTORY:
  every admitted legacy source/state is:
    COVERED
    SUBORDINATE_LINEAGE_COVERED
    or EXPLICITLY_EXCLUDED_BY_CONTRACT

UNMAPPED BLOCKERS:
  0

SEMANTIC SPECIES:
  episodic_semantic_memory: covered
  verified_personal_fact: covered
  candidate_unreviewed_fact: covered

AUTHORITY:
  legacy sources remain authoritative
  compatibility projections remain read-only
  canonical memory tables remain non-authoritative

RETRIEVAL:
  no live compatibility-projection integration yet

NEXT:
  UMS-03I may unify the already-proven compatibility read surface
  UMS-04 remains unauthorized
```
