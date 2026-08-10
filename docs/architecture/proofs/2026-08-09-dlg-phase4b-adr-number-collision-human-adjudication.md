# DLG Phase 4B ADR Number-Collision Human Adjudication

## Status

State:

- Accepted human governance record
- Phase 4 adjudication
- non-implementation
- canonicalization execution deferred

This record captures the human maintainer's explicit adjudication of all seven direct
ADR-number collision prefixes identified by the Phase 4A review. It records governance
decisions and later work queues; it does not execute any ADR canonicalization.

## Governing evidence

Reference:

- [ADR-056: Document Lifecycle Graph Control Plane](../adr/056-document-lifecycle-graph-control-plane.md)
- [DLG Phase 4A ADR Number-Collision Canonicalization Review](./2026-08-08-dlg-phase4a-adr-number-collision-canonicalization-review.md)
- [ADR-057: Product Architecture Ontology as a Document Lifecycle Graph Extension](../adr/057-product-architecture-ontology-dlg-integration.md), where its existing citations form part of the reviewed evidence
- Human adjudication recorded 2026-08-09

ADR-056 requires human review for canonicalization, supersession, contradiction
resolution, quarantine, and destructive migration decisions. ADR-057 remains scoped
as existing governance evidence; this record does not alter either ADR.

## Decision doctrine

- ADR number order is not architecture rank.
- Accepted / Proposed governance posture is preserved.
- Renumbering does not change architectural meaning or identity unless a separate human decision explicitly changes it.
- No new ADR number is allocated by this record.
- Independent decisions remain independent; a shared numeric prefix does not establish identity continuity.
- Duplicate-authority cleanup is distinct from renumbering.

## Retained-number ledger

| ADR number | Retained document | Status | Human disposition |
|---|---|---|---|
| ADR-005 | `005-runtime-mode-and-account-boundary-invariants.md` | Accepted | Retains ADR-005. The independent Imprint UI proposal remains Proposed and is queued for later trailing renumbering. |
| ADR-016 | `016-continuity-governance-surface-contract.md` | Accepted | Retains ADR-016. Workspace Retrieval remains Accepted and is queued for later trailing renumbering. |
| ADR-024 | `024-context-command-active-connector-semantics.md` | Accepted | Retains ADR-024. Workspace Obsidian remains Accepted and is queued for later trailing renumbering. |
| ADR-039 | `039-operator-user-access-boundary.md` | Proposed | Retains ADR-039. Capability-Oriented Mesh remains Accepted and is queued for later trailing renumbering. |
| ADR-041 | `041-vaultnode-canonical-machine-and-audit-authority.md` | Accepted | Retains ADR-041. Provider Capability and Pi Loop Manager remain independent Proposed ADRs, each queued for later trailing renumbering. |
| ADR-053 | `053-node-hosted-room-access-boundary.md` | Proposed | Retains ADR-053. The duplicate ThreadSpace/WhisperMesh artifact is excluded from renumbering and queued for separately governed Phase 6 cleanup. |
| ADR-055 | `055-threadspace-whispermesh-managed-service-boundary.md` | Proposed | Retains ADR-055. Orthogonal UI remains Accepted and is queued for later trailing renumbering. |

## Renumber queue

These seven independent documents are approved for later trailing-number allocation.
No replacement number has been selected; every future number is `not assigned`.

| Queue order | Current path | Current number | Status | Approved future action | Semantic posture |
|---:|---|---|---|---|---|
| 1 | `005-imprint-ui-deprecation-and-identity-ownership.md` | ADR-005 | Proposed | Assign a new unused trailing ADR number in a separately authorized move. | Preserve independent Proposed status and architectural meaning. |
| 2 | `016-workspace-retrieval-source-for-local-knowledge.md` | ADR-016 | Accepted | Assign a new unused trailing ADR number in a separately authorized move. | Preserve Accepted status and architectural meaning. |
| 3 | `024-workspace-obsidian-selection-and-injection-contract.md` | ADR-024 | Accepted | Assign a new unused trailing ADR number in a separately authorized move. | Preserve Accepted status and architectural meaning. |
| 4 | `039-capability-oriented-mesh-architecture.md` | ADR-039 | Accepted | Assign a new unused trailing ADR number in a separately authorized move. | Preserve Accepted status and architectural meaning; later numbering is not a downgrade. |
| 5 | `041-provider-capability-model-contract.md` | ADR-041 | Proposed | Assign a new unused trailing ADR number in a separately authorized move. | Preserve independent Proposed status and architectural meaning. |
| 6 | `docs/architecture/adr/proposed/041-pi-loop-manager-campaign-runner-gate-graph.md` | ADR-041 | Proposed | Assign a new unused trailing ADR number in a separately authorized move. | Preserve independent Proposed status, reference surface, and architectural meaning. |
| 7 | `055-orthogonal-ui-material-personalization.md` | ADR-055 | Accepted | Assign a new unused trailing ADR number in a separately authorized move. | Preserve Accepted status and architectural meaning. |

The document `053-threadspace-whispermesh-managed-service-boundary.md` is not part of
this seven-item renumber queue.

## Duplicate-authority cleanup queue

Record exactly:

`053-threadspace-whispermesh-managed-service-boundary.md`

This artifact is not given another ADR number because the human disposition identifies
it as the duplicate of the ThreadSpace/WhisperMesh decision whose intended canonical
number is ADR-055. Its historical relationship to the ADR-055 decision remains
governed evidence. A separately authorized Phase 6 review may choose tombstone,
compatibility-pointer, retirement, or another permitted treatment; this record selects
no Phase 6 mechanism and executes no cleanup.

## Collision decisions

### ADR-005

`005-runtime-mode-and-account-boundary-invariants.md` retains ADR-005. The
independent `005-imprint-ui-deprecation-and-identity-ownership.md` remains a Proposed
ADR and enters the trailing renumber queue. No pointer, supersession, retirement, or
semantic replacement is approved.

### ADR-016

`016-continuity-governance-surface-contract.md` retains ADR-016.
`016-workspace-retrieval-source-for-local-knowledge.md` remains Accepted and enters
the trailing renumber queue. Its architectural meaning and acceptance posture remain
unchanged. No pointer, supersession, retirement, or semantic replacement is approved.

### ADR-024

`024-context-command-active-connector-semantics.md` retains ADR-024.
`024-workspace-obsidian-selection-and-injection-contract.md` remains Accepted and
enters the trailing renumber queue. Its architectural meaning and acceptance posture
remain unchanged. No pointer, supersession, retirement, or semantic replacement is
approved.

### ADR-039

`039-operator-user-access-boundary.md` retains ADR-039.
`039-capability-oriented-mesh-architecture.md` remains Accepted and enters the
trailing renumber queue. Moving Capability-Oriented Mesh to a later ADR number does
not alter or diminish its Accepted status. No pointer, supersession, retirement, or
semantic replacement is approved.

### ADR-041

`041-vaultnode-canonical-machine-and-audit-authority.md` retains ADR-041 and remains
Accepted. `041-provider-capability-model-contract.md` remains an independent Proposed
ADR and enters the trailing renumber queue. The proposed
`docs/architecture/adr/proposed/041-pi-loop-manager-campaign-runner-gate-graph.md`
also remains an independent Proposed ADR, with its independent reference surface
preserved, and enters the trailing renumber queue separately. No identity merge,
pointer, supersession, retirement, or semantic replacement among these three
documents is approved.

### ADR-053

`053-node-hosted-room-access-boundary.md` retains ADR-053. The historical merge
adjudication selecting Node-Hosted Room as ADR-053 is accepted as the canonical number
disposition. `053-threadspace-whispermesh-managed-service-boundary.md` does not
receive another ADR number; its duplicate relationship to the ThreadSpace/WhisperMesh
decision now represented at ADR-055 enters separately governed Phase 6 duplicate-
authority cleanup. No tombstone, pointer, retirement, deletion, or other Phase 6
mechanism is executed or approved by this record.

### ADR-055

`055-threadspace-whispermesh-managed-service-boundary.md` retains ADR-055. The
explicit historical 053 -> 055 governance chain and ADR-057 citation are accepted as
sufficient human basis for the number disposition. `055-orthogonal-ui-material-personalization.md` remains Accepted and enters the trailing renumber queue. Its
architectural meaning and acceptance posture remain unchanged. No pointer,
supersession, retirement, or semantic replacement is approved.

## Explicitly approved future work

Only these classes of later work are approved:

- Allocate unused trailing numbers for the seven renumber-queue members; each future number remains `not assigned` until that task begins.
- Perform one separately authorized canonicalization task per ADR move.
- Update repository-local references affected by each approved move.
- Update ADR index entries when the matching move is executed.
- Regenerate derived DLG findings after relevant canonical changes.
- Separately perform Phase 6 duplicate-authority cleanup for `053-threadspace-whispermesh-managed-service-boundary.md`.

This section authorizes categories of future tasks, not their execution.

## Explicitly not approved

- No numbers selected.
- No batch rename.
- No pointer creation.
- No tombstone creation.
- No retirement.
- No supersession.
- No ADR content rewrite.
- No architecture status changes.
- No DLG identity creation.
- No DLG relation creation.
- No retrieval integration.

## Phase sequencing

- **Phase 4:** Human dispositions are now recorded.
- **Next mechanical work:** One-collision / one-document canonicalization tasks assigning trailing numbers.
- **Phase 5:** Canonical-document rewrites only where separately required and authorized.
- **Phase 6:** Duplicate-authority replacement for the ADR-053 duplicate only through separately authorized cleanup.

The numbering fixes themselves are not architecture downgrades.

## Validation record

Validation performed for this record:

- Canonical base: `2327ed68259f23deb4c60e4d4af3a297fb160107`.
- Direct collision count: 7; retained-number count: 7; renumber-queue count: 7.
- Renumber queue status counts: Accepted 4; Proposed 3.
- Duplicate-authority cleanup queue count: 1.
- Concrete new ADR numbers assigned: 0; ADR files renamed: 0; ADR statuses changed: 0.
- DLG nodes changed: 0; DLG relations changed: 0; pointers created: 0; tombstones created: 0; supersession relations created: 0.
- Protected ADR, index, DLG contract, node, and generated-projection content remains unchanged by this one-file artifact.
- Phase 3A validator: passed; graph remains 9 nodes / 8 relations (`governed_by` 2, `depends_on` 2, `evidence_for` 4), with 7 numeric collisions still reported by design.
- Phase 3B ARP validation: passed, 4/4.
- Documentation validation: passed. The existing duplicate Make-target warning remained; the diagram freshness check also emitted a non-failing warning because the unrelated Git LFS fixture could not be inspected under the current metadata permissions.
- `git diff --check`: passed.
- Exact commit scope: this adjudication record only.
- No automated runtime tests apply.

The seven numeric collisions remain mechanically present by design because this record
does not execute renumbering.

## Phase 4B conclusion

DLG Phase 4B human adjudication is canonical: all seven direct ADR-number collision dispositions are accepted, seven independent ADR documents are queued for later trailing-number reassignment, and the duplicate ADR-053 ThreadSpace/WhisperMesh artifact is deferred to separately governed Phase 6 cleanup.

## Next gate

The repository is ready for separately authorized one-document-at-a-time ADR renumbering tasks; replacement numbers must be allocated from the then-current unused trailing ADR range immediately before each canonical move.
