# Paul Safe and Sensitive Zones

**For:** Paul's agent - know where to study freely and where to stop
**Last updated:** 2026-06-29

## Safe Study Zones

These areas are lower risk for a first-pass study. Paul can inspect them freely, ask questions, and write reports.

- `docs/collaborators/paul/`
- `docs/collaborators/`
- `docs/architecture/README.md`
- `docs/architecture/00-current-state.md`
- `docs/architecture/system-overview.md`
- `docs/architecture/flows.md`
- `docs/architecture/data-and-storage.md`
- `docs/architecture/modules-and-ownership.md`
- `docs/architecture/config-and-ops.md`

## Sensitive Zones

These areas need a report first and a proposal before any change.

- memory and identity
- provenance and export/restore
- chat runtime semantics
- retrieval
- auth and remote access
- provider routing
- queue and worker semantics
- Continuity
- supported profile activation
- graph / Neo4j mount semantics

## Paul-Specific Rule

If Paul studies one of the sensitive zones above, stop at the report and ask for constraints before producing a proposal or touching implementation.

## What Paul Must Not Assume

- That a doc description means the runtime exists.
- That route presence means supported release support.
- That a metaphor about memory is a runtime contract.
- That a report is the same thing as a task.
