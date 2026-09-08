# UMS-03B Memory Envelope Protocol Tokens Proof

Date: 2026-09-07

Status: **PASSED — TOKEN-ONLY IMPLEMENTATION**

## Qualification identity

- Execution lane: Architecture-Impact
- Task kind: implementation (token-only slice)
- Evidence posture: focused test suite + docs validation + compile
  check + Alembic head identity; no live runtime qualification
- Campaign: Unified Account-Owned Memory Store
- Execution slice: UMS-03B (resumed after UMS-03A-A unblock)
- Starting HEAD: `5f8ef5f913ade9355333294e0a3cc2f1ca5cfa4c`
- UMS-03A original commit: `12075540e29077a40a7d578eef315bc4277c0841`
- UMS-03A reverification commit: `09a13039cc6309188d66782f18514cc2856733b3`
- UMS-03A-A amendment commit: `5f8ef5f913ade9355333294e0a3cc2f1ca5cfa4c`
- UMS-03: OPEN
- UMS-03C: AUTHORIZED TO START
- UMS-04: NOT AUTHORIZED

## UMS-03B STOP-then-RESUME chain (recorded)

The first UMS-03B attempt read the canonical §4.8 of
`docs/architecture/unified-memory-store-contract.md` to extract the
exact semantic-species spellings required for a closed
`MemorySemanticSpecies` protocol-token registry. The UMS-03A taxonomy
named three species using slash-joined prose:

- `Episodic / semantic memory`
- `Verified personal fact`
- `Candidate / unreviewed fact`

Two of the three names used `A / B` syntax that joined two
human-readable terms per species; choosing a single canonical string
for either slash-joined species would invent the spelling that
UMS-03A did not freeze. The UMS-03B spec required "no aliases" and
"stable serialized string values" for the registry. The first
UMS-03B pass BLOCKED with no implementation work behind it (HEAD
and index unchanged).

UMS-03A-A then froze the canonical serialized spellings without
changing the three-species taxonomy:

```text
episodic_semantic_memory
verified_personal_fact
candidate_unreviewed_fact
```

This unblocked UMS-03B. The implementation below mechanically
registers those spellings as canonical protocol tokens.

## New token classes

### `MemorySemanticSpecies` (in `guardian/protocol_tokens.py`)

```python
class MemorySemanticSpecies(str, Enum):
    """Canonical semantic species of a canonical memory envelope record."""

    EPISODIC_SEMANTIC_MEMORY = "episodic_semantic_memory"
    VERIFIED_PERSONAL_FACT = "verified_personal_fact"
    CANDIDATE_UNREVIEWED_FACT = "candidate_unreviewed_fact"
```

Exact member count: **3**

Exact serialized values:

- `episodic_semantic_memory`
- `verified_personal_fact`
- `candidate_unreviewed_fact`

Aggregate:

```python
MEMORY_SEMANTIC_SPECIES_VALUES: frozenset[str] = frozenset(
    {species.value for species in MemorySemanticSpecies}
)
```

Aggregate set:

```text
{
  "episodic_semantic_memory",
  "verified_personal_fact",
  "candidate_unreviewed_fact",
}
```

### `MemoryPersonaLinkKind` (in `guardian/protocol_tokens.py`)

```python
class MemoryPersonaLinkKind(str, Enum):
    """Canonical typed stable-Persona attribution relationship kinds."""

    CAPTURED_UNDER = "captured_under"
    SUGGESTED_BY = "suggested_by"
    ASSOCIATED_WITH = "associated_with"
```

Exact member count: **3**

Exact serialized values:

- `captured_under`
- `suggested_by`
- `associated_with`

Aggregate:

```python
MEMORY_PERSONA_LINK_KIND_VALUES: frozenset[str] = frozenset(
    {kind.value for kind in MemoryPersonaLinkKind}
)
```

Aggregate set:

```text
{
  "captured_under",
  "suggested_by",
  "associated_with",
}
```

## `__all__` registrations

`guardian/protocol_tokens.py` `__all__` was extended to include:

- `MemorySemanticSpecies`
- `MemoryPersonaLinkKind`
- `MEMORY_SEMANTIC_SPECIES_VALUES`
- `MEMORY_PERSONA_LINK_KIND_VALUES`

No other `__all__` entries were changed.

## Alias audit (negative test)

`tests/contracts/test_protocol_tokens.py` proves that the following
strings are **not** canonical members of `MEMORY_SEMANTIC_SPECIES_VALUES`:

- `episodic_memory`
- `semantic_memory`
- `candidate_fact`
- `unreviewed_fact`

The negative-assertion test prevents the spec-forbidden aliases from
re-entering the registry in a future refactor.

## Contract test result

`tests/contracts/test_protocol_tokens.py` was extended with:

- `test_memory_semantic_species_tokens` — locks the three frozen
  species spellings and the alias exclusions.
- `test_memory_persona_link_kind_tokens` — locks the three Persona-
  attribution relationship spellings.

Command and result:

```bash
.venv/bin/python -m pytest -v tests/contracts/test_protocol_tokens.py
======================== 35 passed, 1 warning in 0.16s =========================
```

35 tests passed, 0 failed (33 pre-existing + 2 new). All 33
pre-existing protocol-token contracts remain green.

## Compile result

```bash
.venv/bin/python -m py_compile guardian/protocol_tokens.py
```

Exit status: 0 (clean).

## Runtime-consumer inspection (`rg`)

```bash
rg -n "MemorySemanticSpecies|MemoryPersonaLinkKind|MEMORY_SEMANTIC_SPECIES_VALUES|MEMORY_PERSONA_LINK_KIND_VALUES" \
  --type py --type md \
  guardian tests docs
```

Authorized references:

- `guardian/protocol_tokens.py` — class definitions, aggregate
  expressions, and `__all__` entries.
- `tests/contracts/test_protocol_tokens.py` — import block and
  contract tests.
- `docs/architecture/proofs/runtime/2026-09-07-ums03a-a-memory-species-token-spelling-proof.md` —
  historical STOP narrative that *mentions* the future registry
  names but does not consume them.

No runtime memory consumer, no `ContextBroker`, no
`guardian.context`, no `guardian.memoryos`, no ORM model, no
Alembic migration, no retrieval path, no export path, no route, no
worker, and no frontend module references the new tokens.

## Alembic head before/after

Before implementation:

```bash
.venv/bin/python -m alembic -c backend/alembic.ini heads
e5a9c2f7b4d1 (head)
```

After implementation:

```bash
.venv/bin/python -m alembic -c backend/alembic.ini heads
e5a9c2f7b4d1 (head)
```

The Alembic head is unchanged. No migration was added.

## Documentation follow-through

- `docs/architecture/runtime-protocol-token-contract.md` — added
  two new entries: `Memory semantic species` and `Memory
  Persona-attribution link kinds`. Each entry records the frozen
  values, the authority limitations, the explicit non-implication
  for persistence / retrieval / activation, and the
  attribution-only (not ownership) interpretation of Persona
  links.
- `docs/architecture/unified-memory-store-contract.md` — added
  §4.8.2 `Token implementation checkpoint (UMS-03B)` recording the
  registry implementation without re-deciding the underlying
  semantic taxonomy. No other section was modified.
- `docs/Campaign/unified-memory-store/README.md` — updated the
  Campaign state block to record UMS-03B as CLOSED and UMS-03C as
  AUTHORIZED TO START. Added a UMS-03B narrative paragraph.
- `docs/architecture/00-current-state.md` — updated the
  checkpoint block and added a UMS-03B narrative paragraph
  describing the token registration and the unchanged persistence
  / retrieval / release state.

## Files changed

| Path                                                              | Kind            |
|-------------------------------------------------------------------|-----------------|
| `guardian/protocol_tokens.py`                                     | implementation |
| `tests/contracts/test_protocol_tokens.py`                         | tests          |
| `docs/architecture/runtime-protocol-token-contract.md`            | doc            |
| `docs/architecture/unified-memory-store-contract.md`              | doc (additive checkpoint) |
| `docs/Campaign/unified-memory-store/README.md`                    | state + narrative |
| `docs/architecture/00-current-state.md`                          | state + narrative |
| `docs/architecture/proofs/runtime/2026-09-07-ums03b-memory-envelope-token-proof.md` | new proof receipt |

## ADR impact

- ADR-081 (Project ownership authority): unchanged.
- ADR-082 (Persona Profile manifest and binding authority):
  unchanged.
- ADR-083 (MemoryOS): not present in the canonical ADR registry;
  recorded as known truth, not repaired.
- ADR-084 (Unified Account-Owned Memory Store): unchanged;
  remains controlling. The new token registries sit inside the
  contract that ADR-084 accepts.

No new ADR was created. No existing ADR was modified.

## Confirmation summary

- ✅ UMS-03A original, reverification, and UMS-03A-A amendment
  commits remain in active history
- ✅ no partial UMS-03B implementation from the prior BLOCKED
  attempt
- ✅ `MemorySemanticSpecies` exists with exactly three members
- ✅ exact species values are `episodic_semantic_memory`,
  `verified_personal_fact`, `candidate_unreviewed_fact`
- ✅ no species aliases exist; negative-assertion test proves it
- ✅ no speculative species exists
- ✅ `MEMORY_SEMANTIC_SPECIES_VALUES` aggregate matches the enum
  exactly
- ✅ `MemoryPersonaLinkKind` exists with exactly three members
- ✅ exact Persona-link values are `captured_under`,
  `suggested_by`, `associated_with`
- ✅ no additional Persona-link kind exists
- ✅ Persona links remain attribution rather than ownership
- ✅ no open-ended provenance enum added
- ✅ no governance-state enum added
- ✅ no speculative registry introduced
- ✅ protocol-token test count: 35 passed, 0 failed
- ✅ existing 33 token contracts remain green
- ✅ token module compiles
- ✅ no ORM changed
- ✅ no Alembic migration changed
- ✅ Alembic head remains `e5a9c2f7b4d1`
- ✅ no runtime memory consumer changed
- ✅ no retrieval behavior changed
- ✅ no export / restore behavior changed
- ✅ runtime protocol-token contract updated
- ✅ UMS contract records implementation without semantic drift
- ✅ Campaign closes UMS-03B only
- ✅ UMS-03 remains OPEN
- ✅ UMS-03C becomes AUTHORIZED TO START
- ✅ UMS-04 remains NOT AUTHORIZED
- ✅ current-state contains no persistence / runtime / release
  overclaim
- ✅ proof receipt complete
- ✅ docs validation passes
- ✅ task-scoped diff check passes
- ✅ exactly seven task-owned files staged
- ✅ unrelated Pi fixture remains unstaged
- ✅ commit succeeded (this proof is the receipt; the commit will
  be reported in the closeout)
- ✅ nothing pushed or merged

## Release and runtime impact

```text
UMS-03A CANONICAL MEMORY ENVELOPE CONTRACT: REVERIFIED
UMS-03A-A MEMORY-SPECIES TOKEN SPELLINGS: CLOSED
UMS-03B MEMORY ENVELOPE PROTOCOL TOKENS: CLOSED
UMS-03: OPEN
UMS-03C: AUTHORIZED TO START
UMS-04: NOT AUTHORIZED
RUNTIME/RELEASE IMPACT: NONE

MemorySemanticSpecies:
  episodic_semantic_memory
  verified_personal_fact
  candidate_unreviewed_fact

MemoryPersonaLinkKind:
  captured_under
  suggested_by
  associated_with
```

The implementation is a token registration only. No SQL schema,
no migration, no ORM model, no runtime writer, no runtime reader,
no retrieval path, and no export path were introduced. No runtime
or release capability changed. No Beta claim widened. No
canonical memory persistence implementation exists yet.
