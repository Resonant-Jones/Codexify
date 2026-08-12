# DLG Phase 3B Calibration Boundary Repair

## Status

- architecture-impacting validation-contract correction
- test/proof only
- no canonical DLG data change
- no generated projection change
- no runtime change

## Problem

Phase 3B previously combined two distinct invariants: historical Phase 3A generated
snapshot immutability and permanent byte immutability of the current canonical
source/node corpus. The second invariant blocked legitimate human-authorized DLG
lifecycle changes, including a changed ADR Index maintained alongside its DLG node.
This is a general lifecycle boundary, not ADR-058-specific behavior.

## Intended boundary

Phase 3B owns:

- pinned generated Phase 3A graph/report inputs;
- fixed graph and repository revisions represented by those inputs;
- fixed nine calibration document identities and eight reviewed relations;
- four representative ARP scenarios; and
- deterministic selection, exclusion, path, proof-gap, and output semantics.

Phase 3B does not own perpetual immutability of current canonical Markdown or current
canonical node JSON, nor current-source content-hash or freshness validation. Phase 3A
remains responsible for current source/node integrity.

## Test correction

Removed/replaced:

- current canonical nine-node blob freeze;
- current governed Markdown blob freeze.

Preserved:

- six historical generated projection blob freeze;
- pinned generator revisions;
- representative ARP semantic assertions and deterministic generation;
- generated output checks; and
- no-network/runtime boundary.

Added an explicit test proving that Phase 3B can reconstruct its calibration corpus and
packets without live node or governed Markdown files.

## Architecture effect

- DLG nodes changed: 0
- DLG relations changed: 0
- governed Markdown sources changed: 0
- generated Phase 3A projections changed: 0
- generated Phase 3B ARPs changed: 0
- generator changed: 0
- Phase 3A validator changed: 0
- runtime changed: 0

## Validation

- Phase 3B suite passed, including the isolated-root calibration boundary test.
- Phase 3B generator validation passed: 4/4.
- Phase 3A suite passed.
- Phase 3A semantic validator passed.
- Full architecture suite passed.
- Documentation validation passed.
- `git diff --check` passed.
- No automated runtime tests apply.

## Conclusion

Phase 3B now freezes the historical generated calibration snapshot and representative ARP semantics without freezing the living canonical DLG node and Markdown corpus.

## Next gate

The human-authorized Imprint UI ADR-005 to ADR-058 canonicalization may be retried with current-source integrity maintained by Phase 3A and historical representative ARP calibration maintained by Phase 3B.
