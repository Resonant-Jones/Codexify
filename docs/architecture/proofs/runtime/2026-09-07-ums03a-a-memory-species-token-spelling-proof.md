# UMS-03A-A Memory-Species Token Spelling Proof

Date: 2026-09-07

Status: **PASSED — DOCUMENTATION-ONLY CONTRACT AMENDMENT**

## Qualification identity

- Execution lane: Architecture-Impact
- Task kind: architecture-contract amendment
- Evidence posture: documentation-only; no SQL schema, no migration,
  no ORM model, no runtime reader/writer, no retrieval behavior, no
  export implementation, no ADR was changed
- Campaign: Unified Account-Owned Memory Store
- Execution slice: UMS-03A-A
- Starting HEAD: `09a13039cc6309188d66782f18514cc2856733b3`
- UMS-03A original commit: `12075540e29077a40a7d578eef315bc4277c0841`
- UMS-03A reverification commit: `09a13039cc6309188d66782f18514cc2856733b3`
- UMS-03B prior state: BLOCKED at protocol-token implementation
  boundary; this amendment is its unblocker
- UMS-03: OPEN
- UMS-03C: NOT AUTHORIZED
- UMS-04: NOT AUTHORIZED

## UMS-03B STOP reason (recorded from this session's operator transcript)

UMS-03B read the canonical §4.8 of
`docs/architecture/unified-memory-store-contract.md` to extract the
exact semantic-species spellings required for a closed
`MemorySemanticSpecies` protocol-token registry. The UMS-03A taxonomy
named three species using slash-joined prose:

- `Episodic / semantic memory`
- `Verified personal fact`
- `Candidate / unreviewed fact`

The UMS-03B spec required "no aliases" and "stable serialized string
values" for the registry. Two of the three names used `A / B` syntax
that joined two human-readable terms per species; choosing a single
canonical string for either slash-joined species would invent the
spelling that UMS-03A did not freeze. The UMS-03B STOP conditions
explicitly required halting in that case rather than inventing
spellings. UMS-03B therefore BLOCKED with no implementation work
behind it (HEAD and index unchanged).

UMS-03A-A is the narrow contract amendment that closes that ambiguity.

## Three pre-amendment human-readable labels

| # | Pre-amendment human-readable label |
|---|---|
| 1 | Episodic / semantic memory |
| 2 | Verified personal fact |
| 3 | Candidate / unreviewed fact |

## Three canonical serialized spellings (frozen by this amendment)

| # | Pre-amendment label            | Canonical serialized token    |
|---|--------------------------------|-------------------------------|
| 1 | Episodic / semantic memory     | `episodic_semantic_memory`    |
| 2 | Verified personal fact         | `verified_personal_fact`      |
| 3 | Candidate / unreviewed fact    | `candidate_unreviewed_fact`   |

These three spellings are the closed canonical serialization of the
three-species taxonomy. No alternate serialization alias is
authorized:

- `episodic_memory` alone is **not** canonical.
- `semantic_memory` alone is **not** canonical.
- `candidate_fact` alone is **not** canonical.
- `unreviewed_fact` alone is **not** canonical.

The human-readable labels remain descriptive and may use
natural-language punctuation or explanatory phrasing; they are not
authoritative for serialization.

## Required proof statements

```text
SPECIES COUNT BEFORE: 3
SPECIES COUNT AFTER:  3

CANONICAL SERIALIZED VALUES:
  episodic_semantic_memory
  verified_personal_fact
  candidate_unreviewed_fact

SEMANTIC TAXONOMY CHANGE:    NONE
RUNTIME IMPLEMENTATION:      NONE
SCHEMA/MIGRATION CHANGE:     NONE
RETRIEVAL CHANGE:            NONE
EXPORT/RESTORE CHANGE:       NONE
```

## Species semantics preservation

Every UMS-03A species-level semantic decision remains byte-identical
after this amendment. Specifically preserved:

- **creation authority** for each species (§4.8, lines 701–705 of the
  pre-amendment contract; equivalently the species table in the
  post-amendment §4.8).
- **review posture** before ambient influence.
- **activation posture** / explicit retrieval posture.
- **ambient influence posture**.
- **provenance requirements** (§4.11 spine).
- **mutation / revision semantics**.
- **legacy compatibility mapping** (§4.13 compatibility matrix and
  §4.6 inventory).

The three pre-amendment species headings remain in §4.8 with their
substantive prose unchanged. The slash-joined prose
(`Episodic / semantic memory`, `Candidate / unreviewed fact`) remains
a single human-readable combined label per affected species, not a
list of protocol aliases. The post-amendment contract adds:

1. A normative serialization-authority block at the start of §4.8
   that establishes the canonical serialized token as the protocol
   authority and explicitly demotes the human-readable label to
   descriptive.
2. A `Canonical token` column in the §4.8 species table that maps
   each human-readable label to its frozen spelling.
3. A new sub-section §4.8.1 (`Amendment provenance`) that records
   the UMS-03A-A provenance chain and the unchanged semantics.

No other section of the contract was modified. §4.6 inventory and
§4.13 compatibility matrix remain byte-identical; their slash-joined
prose is now interpretable through the §4.8 freeze rather than
requiring independent rewriting.

## Persona-attribution vocabulary preservation

The already-frozen Persona-attribution relationship vocabulary at
§4.3 (lines 277–279) and §4.9 (lines 735–737) is unchanged:

- `captured_under`
- `suggested_by`
- `associated_with`

This amendment does not modify Persona-attribution semantics, does
not introduce new relationship kinds, and does not change how
Persona subjects are referenced.

## ADR impact

- ADR-081 (Project ownership authority): unchanged.
- ADR-082 (Persona Profile manifest and binding authority):
  unchanged.
- ADR-083 (MemoryOS): not present in the canonical ADR registry;
  this amendment does not repair that gap (per the UMS-03B STOP
  precedent and the UMS-03A-A spec, which instructs the amendment
  to record the absence as known truth rather than invent a new
  ADR).
- ADR-084 (Unified Account-Owned Memory Store): unchanged;
  remains controlling. The amendment extends §4.8 within the
  envelope contract that ADR-084 already accepts.

No new ADR was created. No existing ADR was modified.

## Files changed

| Path                                                              | Kind            |
|-------------------------------------------------------------------|-----------------|
| `docs/architecture/unified-memory-store-contract.md`              | normative edit  |
| `docs/Campaign/unified-memory-store/README.md`                    | state + narrative |
| `docs/architecture/00-current-state.md`                          | checkpoint + narrative |
| `docs/architecture/proofs/runtime/2026-09-07-ums03a-a-memory-species-token-spelling-proof.md` | new proof receipt |

The original UMS-03A proof receipt
(`docs/architecture/proofs/runtime/2026-09-07-ums03a-canonical-memory-envelope-contract-proof.md`)
and the UMS-03A reverification receipt
(`docs/architecture/proofs/runtime/2026-09-07-ums03a-reverification-proof.md`)
are preserved unmodified as historical evidence.

## Read-only surfaces (verified not modified)

- `guardian/protocol_tokens.py` — no `MemorySemanticSpecies`,
  `MemoryPersonaLinkKind`, or any other UMS-03B-implementation
  token class was added. The grep in this session confirmed
  zero matches.
- `tests/contracts/test_protocol_tokens.py` — no UMS-03B tests
  were added.
- `docs/architecture/runtime-protocol-token-contract.md` — no
  changes; the UMS-03A-A amendment does not consume the
  protocol-token contract surface.
- `guardian/protocol_tokens.py` aggregate `*_VALUES` frozensets —
  unchanged.

The contract-token registry implementation belongs to UMS-03B
when it is resumed, not to this amendment.

## Release and runtime impact

```text
UMS-03A CANONICAL MEMORY ENVELOPE CONTRACT: REVERIFIED
UMS-03A-A MEMORY-SPECIES TOKEN SPELLINGS: CLOSED
UMS-03B MEMORY ENVELOPE PROTOCOL TOKENS: AUTHORIZED TO RESUME
UMS-03: OPEN
UMS-03C: NOT AUTHORIZED
UMS-04: NOT AUTHORIZED
RUNTIME/RELEASE IMPACT: NONE

CANONICAL MEMORY-SPECIES TOKENS:
  episodic_semantic_memory
  verified_personal_fact
  candidate_unreviewed_fact
```

The amendment is documentation-only. No SQL schema, no migration,
no ORM model, no runtime reader or writer, no retrieval behavior,
and no export implementation changed. No runtime or release
capability changed. No Beta claim widened. No canonical memory
persistence implementation exists yet.
