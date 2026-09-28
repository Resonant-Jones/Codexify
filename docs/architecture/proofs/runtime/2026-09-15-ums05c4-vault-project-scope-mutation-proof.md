# UMS-05C4 Memory Vault Project-Scope Mutation Proof

Date: 2026-09-15

Status: **PASSED — VAULT PROJECT-SCOPE MUTATION COMMITTED**

Final verdict:

```text
UMS05C4_VAULT_PROJECT_SCOPE_MUTATION_COMMITTED
UMS-05C5 PERSONA ATTRIBUTION MUTATION AUTHORIZED
UMS-05C6+ NOT AUTHORIZED
UMS-05D+ NOT AUTHORIZED
UMS-06+ NOT AUTHORIZED
```

## Opening lineage

- Branch: `main`
- C3 anchor: `d9c2bb07714f2520f28e6a55dfd587bac9818d19`
- Actual starting HEAD: `d9c2bb07714f2520f28e6a55dfd587bac9818d19`
- Ancestry result: `merge-base --is-ancestor` exit 0 (PASS — C3 anchor is HEAD)
- Index at start: empty
- Working-tree dirt at start: prior partial implementation present in the five
  authorized files (see prior partial implementation reconciliation note below).
  No later commits beyond C3 exist on `main`.

### Prior partial implementation reconciliation

The working tree at opening contained a previously authored C4 implementation
in the five authorized files. After inspection against this task spec:

- `guardian/services/memory_vault_mutation.py`: matches spec — adds
  `set_project_scope`, `MemoryVaultProjectNotAvailable`,
  `MemoryVaultProjectAuthorityConflict`, action constants, and bounded private
  helpers (`_load_authorized_memory`, `_require_fresh_token`,
  `_load_current_project`, `_load_available_project`,
  `_require_conflict_free_project`, `_validate_project_id`).
- `guardian/routes/memory_vault.py`: matches spec — adds
  `VaultProjectScopeRequest` and
  `PATCH /api/memory-vault/items/canonical/{memory_id}/project-scope`
  with full error mapping.
- `tests/services/test_memory_vault_mutation.py`: matches spec — all C4
  authority, CAS, conflict, rollback, cross-action, and independence proofs.
- `tests/routes/test_memory_vault.py`: matches spec — adapter and error-mapping
  proofs for the new PATCH.
- `tests/routes/test_memory_vault_activation.py`: matches spec — `VAULT_PATHS`
  now exposes six paths (3 GET + 3 PATCH).

No drift was found between the prior implementation and this spec, and no
edits beyond the spec's authorized file set were required.

## Project authority

- Canonical Project owner field: `projects.user_id`.
- ADR-081 conflict token: `project_ownership_authority_conflict` (re-exported
  as `PROJECT_OWNERSHIP_AUTHORITY_CONFLICT` from
  `guardian/core/project_ownership.py`).
- Legacy description envelope (JSON with sentinel `__codexify_project_owner__`)
  is inspected only to classify the Project; it never grants authority.
- Memory Project/account consistency:
  `memory_records.user_id` is the account owner and
  `memory_records.project_id` references the Project that must be
  canonically owned by the same account; the FK boundary is reused.
- Target Project ownership proof path:
  `projects.user_id == authenticated_account_id`.
- Conflict current/target behavior: `MemoryVaultProjectAuthorityConflict`
  raised from `_require_conflict_free_project` via
  `classify_project_ownership(...).has_authority_conflict`.
- No Project row is mutated, created, archived, restored, or repaired.

## Mutation service

- Public surface added: `MemoryVaultMutationService.set_project_scope`.
- Signature (exact):

  ```python
  set_project_scope(
      *,
      memory_id: str,
      expected_updated_at: datetime,
      project_id: int | None,
      reason: str | None = None,
      request_ref: str | None = None,
  ) -> VaultMutationResult
  ```

- No per-call account override exists; `authenticated_account_id` is
  constructor-bound and immutable.
- Shared CAS / receipt / readback machinery is reused: `_load_authorized_memory`
  + `_require_fresh_token` load and validate the row; a single SQLAlchemy
  `update` with `WHERE memory_id=? AND user_id=? AND updated_at=?` provides
  the record CAS; `_build_receipt` produces the audit row; `_readback` returns
  the canonical `VaultItem` via `MemoryVaultReadService`.
- No arbitrary-field mutation was introduced; the helper vocabulary remains
  closed to `pinned` and `held` booleans plus the named `project_id`
  mutation.

## Scope proof

- Account → Project (`project_id: None → 9000`) returned
  `changed=True`, `receipt_id=<uuid>`, `previous_updated_at=T1`,
  `resulting_updated_at=T2`, `item.project_id=9000`,
  `receipt.extensions.action == "set_project_scope"`,
  `receipt.extensions.previous_values == {"project_id": None}`,
  `receipt.extensions.new_values == {"project_id": 9000}`.
- Project → Project (`9000 → 9001`) returned
  `changed=True`, `resulting_updated_at=T3` (distinct from T2),
  `receipt.extensions.action == "set_project_scope"`,
  `receipt.extensions.previous_values == {"project_id": 9000}`,
  `receipt.extensions.new_values == {"project_id": 9001}`.
- Project → account (`9001 → None`) returned
  `changed=True`, `resulting_updated_at=T4` (distinct from T3),
  `receipt.extensions.action == "clear_project_scope"`,
  `receipt.extensions.previous_values == {"project_id": 9001}`,
  `receipt.extensions.new_values == {"project_id": None}`.
- Composite authority preservation: SQL `JOIN memory_records ON projects`
  confirmed `memory_records.user_id == projects.user_id == ACCOUNT_A` for
  the Project-scoped rows.
- Explicit-null semantics: `project_id=None` is a deliberate clear; it is
  not treated as `no-op` unless the row already had `project_id=None`.
- Missing `project_id` in request body: rejected with 422 at the HTTP layer;
  the service is not invoked.
- Canonical readback: `MemoryVaultReadService.get_item(...)` returns the
  post-mutation `VaultItem`; the service asserts `item.project_id ==
  desired project_id` and `item.updated_at == resulting_updated_at` before
  returning the success result.

## CAS proof

- Scope T1 → T2 succeeds with `resulting_updated_at != T1`.
- Fresh no-op (`expected_updated_at == T1`, `project_id` unchanged) returns
  `changed=False`, `receipt_id=None`, no DB write, no receipt.
- Stale no-op (`expected_updated_at == T1`, `project_id` unchanged) after a
  different mutation has advanced the row to T2 raises
  `MemoryVaultMutationConflict`; no receipt appended.
- Scope T1 → T2 then stale pin with T1 raises
  `MemoryVaultMutationConflict`; `project_id` and `pinned` both unchanged;
  receipt count unchanged.
- Pin T1 → T2 then stale scope with T1 raises
  `MemoryVaultMutationConflict`; `project_id` unchanged; no scope receipt.
- Hold T2 → T3 then stale scope with T2 raises
  `MemoryVaultMutationConflict`; no scope receipt.

One record-level `updated_at` CAS now protects `pinned`, `held`, and
`project_id`.

## Receipt proof

- Schema: `memory-vault-mutation.v1` (unchanged).
- Action labels (frozen for C4): `set_project_scope`,
  `clear_project_scope`.
- `set_project_scope` carries `previous_values={"project_id": <old int|null>}`
  and `new_values={"project_id": <new int>}`.
- `clear_project_scope` carries
  `previous_values={"project_id": <old int>}` and
  `new_values={"project_id": null}`.
- Preserved fields: `receipt_schema`, `mutation_source`,
  `actor_account_id`, `expected_updated_at`, `resulting_updated_at`,
  `reason`, `request_ref`.
- Receipt payload excludes: account-scoped memory text, Project name,
  `owner_user_id`, and Project `description`.
- Receipt is non-authority audit/lineage; canonical Project ownership
  authority remains `projects.user_id` exclusively.

## Atomicity proof

Forced provenance-flush failure during scope mutation:

- `before_flush` listener raises `RuntimeError` when a new `MemoryProvenance`
  is added.
- `set_project_scope` raises `MemoryVaultMutationError` and rolls the
  session back.
- After rollback: `project_id` unchanged, `updated_at` unchanged,
  receipt count unchanged, and `_non_project_fields` snapshot is identical.

## Independence proof

`_non_project_fields` snapshot before/after a successful scope mutation
remains identical for:

- `user_id`
- `semantic_species`
- `text_content`
- `fact_key`, `fact_value`, `fact_confidence`
- `reviewed_at`, `activated_at`
- `pinned`
- `held`
- `extensions`

## HTTP proof

- Path: `PATCH /api/memory-vault/items/canonical/{memory_id}/project-scope`.
- Request body: `VaultProjectScopeRequest` with required nullable
  `project_id: Annotated[int, Field(strict=True, gt=0)] | None`,
  required `expected_updated_at`, optional `reason`, optional `request_ref`.
- Delegation:

  ```python
  service.set_project_scope(
      memory_id=memory_id,
      expected_updated_at=body.expected_updated_at,
      project_id=body.project_id,
      reason=body.reason,
      request_ref=body.request_ref,
  )
  ```

- Error mapping:
  - `MemoryVaultMutationNotAvailable` → 404 `Memory not available`.
  - `MemoryVaultProjectNotAvailable` → 404 `Project not available`.
  - `MemoryVaultProjectAuthorityConflict` → 409 with
    `detail = {"code": "project_ownership_authority_conflict",
    "message": "Project ownership metadata conflicts with canonical
    authority."}`.
  - `MemoryVaultMutationConflict` → 409 `Memory changed since it was read`.
  - `MemoryVaultMutationError` → 409 `Memory mutation unavailable`.
- Missing `project_id` body field: 422; service is not called.
- Invalid non-null `project_id` (non-positive / non-int / boolean):
  422; service is not called.
- Naive `expected_updated_at`: 422 (Pydantic field validator).
- Blank stable account: 401 (route-level dependency injection).
- Caller account override: response carries the constructor-bound account;
  query-string `user_id` / `account_id` do not change the service authority.
- Pin and hold routes remain unchanged.

## Control-plane proof

- Six Memory Vault paths are mounted internally on each admitted web profile:
  - `GET /api/memory-vault/items`
  - `GET /api/memory-vault/items/canonical/{memory_id}`
  - `GET /api/memory-vault/items/compatibility/{source_kind}/{source_id}`
  - `PATCH /api/memory-vault/items/canonical/{memory_id}/pin`
  - `PATCH /api/memory-vault/items/canonical/{memory_id}/hold`
  - `PATCH /api/memory-vault/items/canonical/{memory_id}/project-scope`
- All six remain hidden from public OpenAPI
  (`not (VAULT_PATHS & openapi_paths)`).
- Feature flag `CODEXIFY_ENABLE_MEMORY_VAULT_ROUTES=false` removes all six.
- A quarantined profile (e.g. `v1-user-profile-accent-proof`) keeps the
  router off even with flag true.
- `guardian/guardian_api.py` is unchanged (same opening/closing SHA-256).
- Supported-profile manifests are unchanged.

## Read regression

`tests/services/test_memory_vault_read_projection.py`: 24 passed.

The readback continues representing `project_id` from canonical memory
authority.

## Existing Project authority regression

- `tests/core/test_project_ownership.py`: 8 passed.
- `tests/migration/test_project_ownership_runtime_convergence.py`: 5 passed
  (using TCP `127.0.0.1:55432` TEST_DATABASE_URL to avoid pre-existing
  alembic configparser interpolation handling of the `%2Ftmp` URL-encoded
  socket path; this is an environmental detail, not a spec change).

No C4 mutation can leave `memory_records.user_id != projects.user_id`.

## UMS-04 portability regression

`tests/services/test_account_export_restore_unified_memory_roundtrip.py`: 1
passed.

## Regression results

| Surface | Result |
| --- | --- |
| Mutation (`test_memory_vault_mutation.py`, PostgreSQL 17.6) | 34 passed |
| Read projection | 24 passed |
| Route (`test_memory_vault.py`) | 59 passed |
| Activation (`test_memory_vault_activation.py`) | 7 passed |
| Project ownership core | 8 passed |
| Project ownership migration convergence | 5 passed |
| UMS-04 export/restore round-trip | 1 passed |
| `py_compile` (5 authorized Python files) | PASS |
| Alembic heads | one head `7e5a5fccf253` |
| `pre-commit` on authorized files | PASS (pyupgrade PASS) |
| `docs validate_docs.py` | PASS |
| `git diff --check` | PASS |

## Read/control-plane immutability

```text
guardian/services/memory_vault_read.py
  7c12d7dc9836465b4bb4b1f393bf066ce5de3b665aab6ed70051f7d247e843b3
guardian/guardian_api.py
  bbb6fc86c9ea4d3dfbf8bd52f9b02c602efba5db3b46f0719e02adfed648a9a5
guardian/core/project_ownership.py
  55a89e0805a26f94343c7c89d7828e0c3d4c5edfc7098966a752433d23764f53
```

Unchanged; no supported-profile manifest diff.

## ADR impact

Aligned with ADR-081 (Project Ownership Authority), ADR-084 (Unified
Account-Owned Memory Store), and `memory-vault-contract.md`. No new ADR. No
architecture semantic change. Canonical Project ownership authority and the
qualified Vault mutation spine were reused.

## Limitations

- No decay, heat, ranking, retrieval, or ambient-eligibility behavior.
- No Project / Persona / content / review / create / retire mutation.
- Compatibility projections remain read-only.
- ADR-081 conflicts are not repaired by Vault scope mutation; they fail
  closed.
- Personal Facts specialized authority remains untouched.
- UMS-05C remains OPEN; UMS-05C5 Persona attribution alone is the
  authorized next slice; UMS-05C6+, UMS-05D+, and UMS-06+ remain
  unauthorized.