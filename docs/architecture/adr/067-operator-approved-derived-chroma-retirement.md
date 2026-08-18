# ADR-067 Operator-Approved Derived Chroma Retirement

**Status:** Accepted

## Context

The current Tester Chroma store located at `/Volumes/Dev_SSD/Codexify-main/.chroma` was created by a non‑stock Chroma migration and is incompatible with the canonical runtime `chromadb==1.0.15`. The diagnostic proof `docs/architecture/proofs/2026-08-13-chroma-backend-startup-isolation-proof.md` classifies the failure as a **PERSISTED_STORE_COMPATIBILITY_BOUNDARY** and recommends copy‑first schema reconciliation.

The operator has elected a different resolution: preserve the incompatible store as historical evidence, retire it from the active runtime path, and initialise a fresh supported Chroma index via the canonical runtime.

## Problem Statement

* The active Chroma store cannot be opened by the supported runtime, causing a panic (`range start index 10 out of range for slice of length 9`).
* The store is derived retrieval state – it is not canonical application authority.
* The operator requires an explicit governance decision authorising retirement while preserving the historical bytes.

## Decision

1. **Authority** – Postgres remains the canonical source of truth for application state. The vector store is strictly a retrieval/index artefact.
2. **Derived State Handling** – Derived Chroma indexes are not automatically disposable; retirement must be operator‑approved and documented.
3. **Operator‑Approved Retirement** – The operator may retire an active Chroma index when:
   - The supported runtime cannot consume it.
   - No canonical authority is derived from it.
   - The original bytes are preserved (e.g., copied to a safe archival location).
   - Writer quiescence is proven.
4. **Preserve‑Retire‑Rebuild Semantics** – Three distinct states are defined:
   - `HISTORICAL_CHROMA_PRESERVATION_RETAINED`
   - `ACTIVE_CHROMA_INDEX_RETIRED`
   - `FRESH_CHROMA_INITIALIZED`
   No state implies another.
5. **No Schema Surgery** – The copy‑first schema reconciliation path remains available for forensic recovery but is not required for this retirement.
6. **Fresh Initialise** – A new Chroma store must be created exclusively through the supported Codexify runtime (i.e., by starting the Tester backend with the stock runtime).
7. **Proof Requirements** – The retirement execution must prove:
   - Exact identity of the retired store.
   - Writer quiescence.
   - Preservation of the original bytes.
   - Fresh store initialisation via the canonical runtime.
   - Absence of the Rust panic after retirement.
   - Successful backend health (`/health`, `/health/chat`).
8. **Rollback Boundary** – Restoring the historical store requires a separate, explicitly authorised architecture‑impact task.

## Authority Boundary

- **Postgres** – remains the sole authority for canonical application data.
- **Chroma** – remains a semantic retrieval store; its persisted bytes are never promoted to canonical authority.

## Operator‑Approval Boundary

Retirement may only be performed after explicit operator approval (this ADR) and after the proof steps listed above are satisfied.

## Preservation Requirement

The original `.chroma` directory must be copied to an archival location (e.g., `archive/chroma/<commit‑sha>/`) before any destructive deletion.

## Active‑Retirement Semantics

The active store is removed from the runtime path after preservation; the runtime is then started so it creates a fresh empty store.

## Fresh‑Initialisation Semantics

The fresh store is created by the stock `chromadb==1.0.15` runtime during normal backend start‑up; no manual schema manipulation is performed.

## Provenance Requirement

All records in the fresh store must originate from canonical sources (Postgres) or deterministic supported built‑ins. No records from the retired store may be copied into the fresh store.

## Runtime‑Proof Requirement

The execution must verify backend start‑up without panic, successful health checks, and authenticated Tester viability.

## Rollback/Restoration Boundary

Restoring the historical store is a separate task and requires its own ADR.

## Consequences

- No change to runtime code, tests, Docker compose, or migrations.
- Documentation reflects the new retirement policy.
- Future operators may use this ADR as the governing reference for similar derived‑store retirements.

## Rejected Alternatives

- **Pin/upgrade Chroma** – Rejected because the non‑stock migrations are outside the supported runtime.
- **Mutate old SQLite store** – Not required; operator chose preserve‑retire‑rebuild.
- **Promote records to Postgres** – Forbidden; derived state cannot become canonical authority.
- **Delete without preservation** – Disallowed; derived state must be retained as evidence.
- **Switch vector backend** – Unrelated to the incompatibility; the defect is store‑schema, not backend choice.

## Implementation/Proof Follow‑Through

The execution task will:
1. Verify the active store identity.
2. Ensure writer quiescence.
3. Copy the store to an archival location.
4. Delete the active store.
5. Restart the Tester backend to initialise a fresh store.
6. Run health checks and confirm the panic is gone.

## Current Evidence Anchors

- `docs/architecture/proofs/2026-08-13-chroma-backend-startup-isolation-proof.md`
- `docs/architecture/proofs/2026-08-13-preserved-tester-canonical-startup-auth-proof.md`

---

*This ADR documents the governance decision only. No runtime mutation has been performed by this change.*