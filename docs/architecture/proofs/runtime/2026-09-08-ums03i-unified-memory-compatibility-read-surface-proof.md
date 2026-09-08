# UMS-03I — Unified Memory Compatibility Read Surface Proof

- **Slice:** UMS-03I (final UMS-03 compatibility-read slice)
- **Date:** 2026-09-08
- **Execution lane:** Architecture-Impact
- **Task kind:** runtime compatibility interface + campaign closure qualification
- **Starting HEAD:** `557edc128db4e8e1c41b021f7afe59b7a3b7f34b` (UMS-03H)
- **UMS-03H prerequisite SHA:** `557edc128db4e8e1c41b021f7afe59b7a3b7f34b`
- **Alembic head before / after:** `f6b0d3e8c5a2` / `f6b0d3e8c5a2` (unchanged)
- **Local safety ref preserved:** `recovery/ums03e-conflated-71fd9f4d5`
  → `71fd9f4d5f4f2d05eb97c829a0097039c5fb0cae` (untouched)

## Objective

Add exactly one public, account-authorized compatibility read
surface that dispatches an explicit legacy source reference into
the already-proven compatibility projections. Compose the
existing UMS-03E/F/G adapters without changing their authority
semantics. No search heuristics. No persistence. No retrieval
integration.

## Design rule

```text
explicit legacy source reference
        │
        ▼
unified compatibility dispatcher
        │
        ├── memory_entry
        │     └── read_memory_entry_projection(...)
        │
        └── personal_fact
              ├── authoritative verified/current state
              │     └── read_verified_personal_fact_projection(...)
              │
              └── authoritative candidate/unreviewed-compatible state
                    └── read_candidate_personal_fact_projection(...)
```

Source-family identity is **explicit**. The caller passes a
`MemoryCompatibilitySourceRef`. The dispatcher does not guess
the kind from identifier shape and does not search across
legacy tables.

## Implementation

Extended: `guardian/core/memory_compatibility.py`

### New types (implementation-scoped, no new protocol tokens)

```python
class MemoryCompatibilitySourceKind(str, Enum):
    MEMORY_ENTRY = MEMORY_ENTRY_LEGACY_SOURCE_FAMILY    # "memory_entries"
    PERSONAL_FACT = PERSONAL_FACT_LEGACY_SOURCE_FAMILY  # "personal_facts"

@dataclass(frozen=True)
class MemoryCompatibilitySourceRef:
    source_kind: MemoryCompatibilitySourceKind
    source_id: int
```

The string values are the same family identifiers already
exposed on `MemoryCompatibilityProjection.legacy_source_family`
by the underlying adapters. The `Enum` and `dataclass` exist
inside the compatibility module to give the dispatcher a
type-checked surface. They are **not** a new
cross-runtime protocol-token domain. Adding them required no
change to `guardian/protocol_tokens.py`.

### New public reader

```python
def read_memory_compatibility_projection(
    session: Session,
    *,
    authenticated_account_id: str,
    source: MemoryCompatibilitySourceRef,
) -> MemoryCompatibilityProjection | None
```

### Dispatch logic

- `MemoryCompatibilitySourceKind.MEMORY_ENTRY` →
  `read_memory_entry_projection(session, authenticated_account_id=..., memory_entry_id=...)`
- `MemoryCompatibilitySourceKind.PERSONAL_FACT` → small
  internal helper that reads just the lifecycle authority
  columns and routes to the matching proven adapter:
  - `status == 'verified' AND is_active IS TRUE` →
    `read_verified_personal_fact_projection(...)`
  - anything else →
    `read_candidate_personal_fact_projection(...)`
- Any other kind → `MemoryCompatibilityReadError`

The internal helper is a tiny `SELECT id, user_id, status,
is_active FROM personal_facts WHERE id=? AND user_id=?` that
mirrors the proven adapter predicate. It exists to avoid
duplicating the lifecycle classification. The selected
adapter then performs its own authoritative read.

The caller cannot supply:

- owner
- semantic species
- Project scope
- Persona attribution
- review state
- activation state
- provenance authority

The caller cannot select which Personal Fact adapter is
invoked — that decision derives from the source row's
persisted `status` and `is_active` columns.

### Excluded source families

The following are NOT in `SUPPORTED_COMPATIBILITY_SOURCE_KINDS`:

- `personal_fact_evidence` — subordinate provenance, not root
- `personal_fact_revisions` — historical lineage, not root
- `Memoryos` library state — `EXPLICITLY_EXCLUDED_BY_CONTRACT` per
  §4.13 line 904
- `chat_messages`, `documents`, `memory_records`,
  `memory_provenance`, `memory_persona_links` — canonical
  UMS substrate, evidence-only, or not admitted

Any attempt to dispatch them via the unified surface fails
closed with `MemoryCompatibilityReadError`.

### Preservation of the three proven direct adapters

`read_memory_entry_projection`,
`read_verified_personal_fact_projection`, and
`read_candidate_personal_fact_projection` remain callable
independently. The unified surface is additive composition,
not a replacement. The UMS-03E/F/G external semantics are
unchanged. All 52 pre-UMS-03I tests still pass.

## Tests added (UMS-03I cases)

Test numbers continue the UMS-03E/F/G sequence (53–70).

| # | Test |
| --- | --- |
| 53 | Memory entry: unified output equals direct adapter output |
| 54 | Verified Personal Fact: unified output equals direct adapter output |
| 55 | Candidate Personal Fact: unified output equals direct adapter output |
| 56 | Disputed Personal Fact: unified dispatches to candidate adapter |
| 57 | Archived Personal Fact: unified dispatches to candidate adapter |
| 58 | Inactive verified Personal Fact: unified dispatches to candidate adapter |
| 59 | Cross-account memory entry: returns None |
| 60 | Cross-account Personal Fact: returns None |
| 61 | Missing memory entry: returns None |
| 62 | Missing Personal Fact: returns None |
| 63 | Empty account id: fails closed |
| 64 | Unsupported source kind (`personal_fact_evidence`): fails closed |
| 65 | Unsupported source kind (`chat_message`): fails closed |
| 66 | Unsupported source kind (`memoryos`): fails closed |
| 67 | No canonical write or legacy mutation across unified dispatch |
| 68 | No fabricated canonical `memory_id` (memory_entry + personal_fact) |
| 69 | Unified dispatcher has no species / status / is_active argument |
| 70 | Memory entry source identity is preserved exactly |

## Compatibility test results

```text
tests/core/test_memory_compatibility.py  70 passed in 0.76s
  0 failed
  0 errors
  0 skipped
```

- 52 UMS-03E/F/G tests preserved exactly
- 18 new UMS-03I tests pass

## Adjacent UMS regression results

```text
tests/contracts/test_protocol_tokens.py  35 passed
tests/core/test_persona_subjects.py     11 passed
                                        46 passed in 0.47s
```

Pre-UMS-03I count (46) is preserved.

## Alembic topology

```text
f6b0d3e8c5a2 (head)
```

Single head, unchanged. No new migration was added. No ORM
model was modified.

## Runtime-consumer surface

`rg -l 'read_memory_compatibility_projection|MemoryCompatibilitySourceRef|MemoryCompatibilitySourceKind' guardian/ tests/ docs/` returned references only in:

- `guardian/core/memory_compatibility.py` (implementation)
- `tests/core/test_memory_compatibility.py` (focused tests)

No consumer exists under `guardian/context/`,
`guardian/memoryos/`, `guardian/core/chat_completion_service.py`,
`guardian/workers/`, or `guardian/routes/`. The unified surface
has no live runtime consumer — UMS-03I is purely a
composition seam.

## Canonical UMS persistence consumers

`rg -l 'MemoryRecord\b|MemoryProvenance\b|MemoryPersonaLink\b' guardian/` returned only `guardian/db/models.py` (the
class definitions). The canonical UMS tables remain
structural and non-authoritative at runtime, exactly as the
UMS-03D proof established and UMS-03H-R revalidated.

## ADR impact

Aligned with ADR-081, ADR-082, and ADR-084. No new ADR. No
new architecture decision. The unified surface composes
existing compatibility semantics; it does not invent
authority or routing.

## UMS-03 closure verdict

`UMS03_CANONICAL_STORAGE_AND_COMPATIBILITY_READS_CLOSED`

All conditions from requirement #23 are satisfied:

```text
✓ canonical persistence exists and is qualified
✓ legacy compatibility inventory is complete
✓ three proven direct adapters remain valid
✓ one deterministic unified compatibility read surface exists
✓ unified output equals direct-adapter output (structural equality)
✓ no source-family ambiguity (explicit MemoryCompatibilitySourceKind)
✓ no canonical writes occur (SQL-event listener assertion)
✓ no authority cutover occurs
✓ no live retrieval integration occurs
```

UMS-04 EXPORT / RESTORE BEFORE INGESTION is now authorized
to start. UMS-05+ remain unauthorized.

## Confirmed non-claims

- No canonical `memory_id` was fabricated for any
  compatibility-only projection.
- No canonical persistence row was created.
- No legacy row was mutated.
- No read repair was performed.
- No caching side effect was introduced.
- No ContextBroker / MemoryOS / completion cutover occurred.
- No new HTTP route, no API endpoint, no frontend change.
- No ORM change.
- No Alembic migration.
- No export/restore behavior change.
- No retrieval/router behavior change.
- No canonical writer was added.
- No live runtime consumer of the unified surface exists.
- The three proven direct adapters remain independently
  callable and externally unchanged.
- The `personal_fact_evidence` / `personal_fact_revisions` /
  `Memoryos` / `chat_message` / canonical-memory source
  families are NOT in the supported dispatch set.
- The local safety ref
  `recovery/ums03e-conflated-71fd9f4d5` is preserved.
- The Pi fixture is untouched.
- Nothing was pushed or merged.

## Required successful state

```
UMS-03D CANONICAL MEMORY PERSISTENCE: CLOSED
UMS-03E MEMORY-ENTRY COMPATIBILITY PROJECTION: CLOSED
UMS-03F VERIFIED PERSONAL-FACT COMPATIBILITY: CLOSED
UMS-03G CANDIDATE PERSONAL-FACT COMPATIBILITY: CLOSED
UMS-03H-R RECONCILED-MAIN REBASELINE: CLOSED
UMS-03H LEGACY MEMORY COMPATIBILITY COVERAGE: CLOSED
UMS-03I UNIFIED COMPATIBILITY READ SURFACE: CLOSED

UMS-03 CANONICAL MEMORY STORAGE + COMPATIBILITY READS: CLOSED

UMS-04 EXPORT / RESTORE BEFORE INGESTION: AUTHORIZED TO START
UMS-05+: NOT AUTHORIZED
RUNTIME/RELEASE IMPACT: INTERNAL COMPATIBILITY READ ONLY

UNIFIED COMPATIBILITY SURFACE:
  source family is explicit
  source identity is explicit
  memory_entries delegates to its proven adapter
  personal_facts delegates according to persisted lifecycle authority
  direct and unified projections are structurally equivalent

AUTHORITY:
  legacy persistence remains authoritative
  compatibility projections remain read-only
  canonical UMS tables remain non-authoritative

RETRIEVAL:
  no ContextBroker / MemoryOS / completion cutover

NEXT:
  UMS-04 proves export and restore before broader canonical-memory ingestion
```
