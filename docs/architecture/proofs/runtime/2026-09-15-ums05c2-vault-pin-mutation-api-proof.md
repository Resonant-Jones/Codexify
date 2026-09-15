# UMS-05C2 Memory Vault Pin/Unpin Mutation API Proof

Date: 2026-09-15

Status: **PASSED — VAULT PIN MUTATION API COMMITTED**

Final verdict:

```text
UMS05C2_VAULT_PIN_MUTATION_API_COMMITTED
UMS-05C3 VAULT HOLD/RELEASE-HOLD MUTATION AUTHORIZED
UMS-05D+ NOT AUTHORIZED
UMS-06+ NOT AUTHORIZED
```

## Opening lineage

- Branch: `main`
- Opening HEAD: `39f07412013578fdfa18571d027083438c3b4367`
  (`Add Memory Vault pin mutation spine`, UMS-05C1)
- C1 ancestor proof: exit 0; no later drift
- Index at open: empty; unrelated dirt preserved

## Route endpoint

```text
PATCH /api/memory-vault/items/canonical/{memory_id}/pin
```

Request body (`VaultPinRequest`):

```text
pinned: bool
expected_updated_at: timezone-aware datetime (required)
reason: str | None
request_ref: str | None
```

Response body (`VaultMutationResponse`):

```text
changed: bool
receipt_id: str | None
previous_updated_at: datetime
resulting_updated_at: datetime
item: VaultItemResponse
```

## Stable account authority

Account resolves only from `RequestUserScope.account_id` (blank → 401). No
legacy `user_id` fallback; caller query parameters have no authority. The
mutation service factory binds the same account and reuses the same
repository database/session authority as the read service.

## Exact service delegation

The route delegates only `MemoryVaultMutationService.set_pinned(...)` with
`memory_id`, `expected_updated_at`, `pinned`, `reason`, `request_ref`. The
route performs no SQL, no CAS comparison, no receipt creation, no no-op
calculation, and no read-before-write.

## Proofs

- Pin and unpin both delegate exact desired boolean state; the C1 service
  owns whether the receipt action becomes `pin` or `unpin`.
- Changed response preserves `changed=true`, receipt id, previous/resulting
  CAS tokens, and canonical `VaultItem` readback.
- No-op response preserves `changed=false`, `receipt_id=null`, unchanged
  timestamp, and canonical readback.
- Stale CAS → HTTP 409 `Memory changed since it was read`; internal exception
  text absent.
- Missing/cross-account → identical HTTP 404 `Memory not available`.
- Integrity failure → HTTP 409 `Memory mutation unavailable`; internals absent.
- Missing/malformed/naive `expected_updated_at` → HTTP 422 before the mutation
  service is invoked.
- No compatibility mutation route exists.

## Control-plane proof

The existing `memory_vault` route label and internal-only supported-profile
posture are reused unchanged. On an admitted profile the PATCH route is
mounted and hidden from public OpenAPI; with the feature flag false it is
absent; on a quarantined profile with the flag true it remains absent. Legacy
`memory` posture is unchanged. Vault methods are exactly GET + PATCH.

## Regression results

| Surface | Result |
| --- | --- |
| C1 mutation (`test_memory_vault_mutation.py`, PostgreSQL 17.6) | 11 passed |
| B1/R1 read projection | 24 passed |
| Route (`test_memory_vault.py`) | 35 passed |
| Activation (`test_memory_vault_activation.py`) | 7 passed |
| UMS-04 export/restore round-trip | 1 passed |
| Alembic heads | one head `7e5a5fccf253` |

## Runtime immutability

```text
guardian/services/memory_vault_mutation.py
  f6a07deabfd76bc623a03c80dfa67ea5460fefebcb3fdbba5ca250a5fb4a390b
tests/services/test_memory_vault_mutation.py
  06894efdad76e72f723906ccc4194e5ecb30e999769e1a0b5ccbf032c47a1ecc
guardian/services/memory_vault_read.py
  7c12d7dc9836465b4bb4b1f393bf066ce5de3b665aab6ed70051f7d247e843b3
```

Unchanged from opening.

## ADR impact

Aligned with ADR-084 and `memory-vault-contract.md`. No new ADR. No
architecture semantic change. Existing C1 mutation authority was exposed
without duplication.

## Limitations

- No hold/release, retire/restore, content, Project, Persona, or Personal
  Facts mutation.
- No frontend mutation controls; no public OpenAPI promotion.
- UMS-05C remains OPEN; UMS-05C3 alone is authorized next; UMS-05D+ and
  UMS-06+ remain unauthorized.
