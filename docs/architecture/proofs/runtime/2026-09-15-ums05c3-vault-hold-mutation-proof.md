# UMS-05C3 Memory Vault Hold / Release-Hold Mutation Proof

Date: 2026-09-15

Status: **PASSED — VAULT HOLD MUTATION COMMITTED**

Final verdict:

```text
UMS05C3_VAULT_HOLD_MUTATION_COMMITTED
UMS-05C4 PROJECT-SCOPE MUTATION AUTHORIZED
UMS-05C5+ NOT AUTHORIZED
UMS-05D+ NOT AUTHORIZED
UMS-06+ NOT AUTHORIZED
```

## Opening lineage

- Branch: `main`
- Opening HEAD: `ebbc9375e73bd663821e313ced35f1a1f72bb4a6`
  (`Expose Memory Vault pin mutation API`, UMS-05C2)
- C2 ancestor proof: exit 0; no later drift
- Index at open: empty; unrelated dirt preserved

## Authority reuse

The C1/C2 mutation spine is reused unchanged: constructor-bound
authenticated account, `memory_records.updated_at` record-level CAS,
`memory_provenance` append-only receipt, one PostgreSQL transaction, and
canonical `MemoryVaultReadService` readback. A narrow private extraction
(`_set_boolean_governance_state`) parameterizes only field, desired boolean,
true action, and false action, with the field vocabulary closed to
`pinned` and `held`.

## Hold authority

`memory_records.held` remains the sole current-state hold authority; the
provenance receipt is audit/lineage only. Holding suspends decay only; no
decay/heat/ranking/retrieval/ambient-eligibility work is implemented.

## CAS proof

- Hold T1 → T2 (held false→true); release T2 → T3 (held true→false).
- Fresh no-op unchanged; stale no-op conflicts.
- Hold-generated token invalidates a stale pin intent (conflict, no pin
  mutation, no receipt).
- Pin-generated token invalidates a stale hold intent (conflict, no hold
  mutation, no receipt).

One record-level `updated_at` CAS protects both `pinned` and `held`.

## Receipt proof

- `hold` and `release_hold` actions; `memory-vault-mutation.v1` schema.
- `previous_values` / `new_values` carry only the authoritative held delta.
- Actor account, expected/resulting CAS, reason, request_ref preserved.
- No memory content, heat, or decay values stored.

## Atomicity / independence

Forced receipt flush failure rolls back `held` and `updated_at` with no
receipt. Hold/release preserves `pinned`, `project_id`, Persona links,
content, review/activation, and `extensions`.

## HTTP proof

`PATCH /api/memory-vault/items/canonical/{memory_id}/hold` reuses the
existing mutation service factory, `VaultMutationResponse`, and C2 error
mapping (401 / 422 / 404 `Memory not available` / 409 `Memory changed since
it was read` / 409 `Memory mutation unavailable`). No SQL, CAS, receipt,
no-op, or decay logic in the route.

## Control-plane proof

Five Memory Vault paths are mounted internally and hidden from public
OpenAPI; feature flag false removes them; quarantine outranks the flag;
`guardian_api.py` and supported-profile manifests are unchanged.

## Regression results

| Surface | Result |
| --- | --- |
| Mutation (`test_memory_vault_mutation.py`, PostgreSQL 17.6) | 20 passed |
| Read projection | 24 passed |
| Route (`test_memory_vault.py`) | 43 passed |
| Activation (`test_memory_vault_activation.py`) | 7 passed |
| UMS-04 export/restore round-trip | 1 passed |
| Alembic heads | one head `7e5a5fccf253` |

## Read/control-plane immutability

```text
guardian/services/memory_vault_read.py
  7c12d7dc9836465b4bb4b1f393bf066ce5de3b665aab6ed70051f7d247e843b3
guardian/guardian_api.py
  bbb6fc86c9ea4d3dfbf8bd52f9b02c602efba5db3b46f0719e02adfed648a9a5
```

Unchanged; no supported-profile manifest diff.

## ADR impact

Aligned with ADR-084 and `memory-vault-contract.md`. No new ADR. No
architecture semantic change. Existing record CAS / receipt / readback
authority reused.

## Limitations

- No decay, heat, ranking, retrieval, or ambient-eligibility behavior.
- No Project/Persona/content/review/create mutation yet.
- UMS-05C remains OPEN; UMS-05C4 Project-scope mutation alone is authorized
  next; UMS-05C5+, UMS-05D+, and UMS-06+ remain unauthorized.
