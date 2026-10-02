# UMS-05B Memory Vault Read Surface Activation Proof

Date: 2026-09-14

Status: **PASSED — MEMORY VAULT BACKEND READ SURFACE CLOSED**

Final verdict:

```text
UMS05B_MEMORY_VAULT_BACKEND_READ_SURFACE_CLOSED
UMS-05C VAULT DIRECT HUMAN MUTATION SERVICE AUTHORIZED
UMS-05D+ NOT AUTHORIZED
UMS-06+ NOT AUTHORIZED
```

## Identity / starting anchor

- Branch: `main`
- Opening HEAD: `652902755b6d2ae47d00b0b10ac40c339f3ff5d0`
  (`Fix Memory Vault offset pagination`, UMS-05B2-R1)
- Index at open: empty
- Unrelated dirt preserved: Pi fixture, Scout iOS tree, `.DS_Store` debris

## Implementation commits composing the read chain

| Slice | Commit | Subject |
| --- | --- | --- |
| UMS-05B1 | `adc98bd6c6406a9cb8bee90de174efe143404da3` | Add Memory Vault read projection |
| UMS-05B2 | `d9a1a6f346933b50f0b7f1c59fab4875bb1a9b56` | Add Memory Vault read API |
| UMS-05B2-R1 | `652902755b6d2ae47d00b0b10ac40c339f3ff5d0` | Fix Memory Vault offset pagination |

## Route-control topology

Registration in `guardian/guardian_api.py`:

```text
label         = memory_vault
flag_name     = CODEXIFY_ENABLE_MEMORY_VAULT_ROUTES
include_fn    = app.include_router(memory_vault.router)
default_enabled = True
core_surface  = False
```

Gate order (existing `_include_router`): supported-profile quarantine check →
Beta-core-only check → feature-flag check → mount → enabled-label record →
internal-only hidden-path record. Feature flag cannot override a quarantined
profile.

## Profile posture matrix

| Profile | `memory_vault` posture |
| --- | --- |
| `v1-local-core-web-mcp` | internal_only |
| `v1-friends-family-web` | internal_only |
| `v1-whooshd-deepseek-web` | internal_only |
| `test-continuity` | quarantined |
| `v1-user-profile-accent-proof` | quarantined |

`memory_vault` is not `enabled` and is not added to any criticality tier in
any profile.

## Feature-flag behavior

- Admitted profile + flag unset → mounted internally (default enabled).
- Admitted profile + `CODEXIFY_ENABLE_MEMORY_VAULT_ROUTES=false` → absent.
- Non-admitted profile + `CODEXIFY_ENABLE_MEMORY_VAULT_ROUTES=true` → absent
  (quarantine outranks the flag).

## Runtime mount proof

On `v1-local-core-web-mcp` with the flag unset, the reloaded application
contains exactly:

```text
/api/memory-vault/items
/api/memory-vault/items/canonical/{memory_id}
/api/memory-vault/items/compatibility/{source_kind}/{source_id}
```

and `memory_vault` is present in `app.state.supported_profile_enabled_labels`.

## OpenAPI-hidden proof

The same three paths are absent from `app.openapi()["paths"]` and present in
`app.state.supported_profile_hidden_paths`. Mounted internally, not publicly
advertised.

## Legacy `memory` independence

`route_status("memory")` remains `quarantined` on every supported profile; the
new `memory_vault` label does not alias, replace, or promote the legacy
`memory` family.

## GET-only proof

Against the globally mounted route set, all three Memory Vault routes expose
exactly `GET`. No `POST` / `PUT` / `PATCH` / `DELETE`.

## Regression results

| Surface | Result |
| --- | --- |
| B1/R1 service (`test_memory_vault_read_projection.py`, PostgreSQL 17.6) | 24 passed |
| B2 route (`test_memory_vault.py`) | 25 passed |
| Activation (`test_memory_vault_activation.py`) | 7 passed |
| Supported-profile (`test_supported_profile.py`) | 24 passed |
| Supported-profile quarantine (`test_supported_profile_quarantine.py`) | passed |
| Alembic heads | one head `7e5a5fccf253` |

## Runtime immutability hashes

Read implementation bytes unchanged from opening:

```text
guardian/services/memory_vault_read.py
  7c12d7dc9836465b4bb4b1f393bf066ce5de3b665aab6ed70051f7d247e843b3
guardian/routes/memory_vault.py
  77178d735d5dc465f9d43b31eaee967356d16996ad6c9d47942e449874d71180
```

## ADR impact

Aligned with ADR-084 and `memory-vault-contract.md`. No new ADR. No UMS memory
semantic change. Supported-profile/operator truth changed only as recorded.

## Limitations / release boundary

- No Memory Vault frontend exists yet.
- No Memory Vault mutation exists yet.
- No public route promotion occurred; the route is internal-only and hidden
  from public OpenAPI.
- No migration, no service mutation, no B2 route mutation.
- UMS-06+ remain unauthorized.
- This proof composes B1 (persistence/read semantics) + B2 (HTTP adaptation) +
  B3 (registration/profile authority). It is not a broader live deployment
  proof and does not widen release support.
