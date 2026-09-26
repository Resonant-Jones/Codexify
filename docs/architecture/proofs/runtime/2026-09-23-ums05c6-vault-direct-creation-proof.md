# UMS-05C6 Memory Vault Direct Creation Proof

Date: 2026-09-23

Status: **PASSED — VAULT DIRECT CREATION COMMITTED (branch-qualified)**

Final verdict:

```text
UMS05C6_DIRECT_USER_AUTHORED_VAULT_CREATION_COMMITTED
UMS-05C7 REMAINING MUTATION AUTHORITY REVALIDATION AUTHORIZED
UMS-05C8+ NOT AUTHORIZED
UMS-05D+ NOT AUTHORIZED
UMS-06+ NOT AUTHORIZED
```

## Branch / lineage

- Branch: `feature/ums-continued`
- C5 anchor: `48fc058546389efe7feece88111bdc2ec6d403ba` (Add Memory Vault
  Persona attribution mutation)
- Starting HEAD: `48fc058546389efe7feece88111bdc2ec6d403ba` (= C5 anchor
  itself)
- `git merge-base --is-ancestor 48fc058... HEAD` exit `0`
- C6 implementation performed exclusively on the UMS development branch;
  no mainline merge, rebase, fetch, pull, or push occurred.
- Index at start: empty.

## Creation authority

- New dedicated service at
  `guardian/services/memory_vault_creation.py`.
- Constructor signature:

  ```python
  MemoryVaultCreationService(
      session,
      *,
      authenticated_account_id,
  )
  ```

  No per-call owner / account / memory-ID override. Blank/empty
  account raises `MemoryVaultCreationAccountNotAvailable`.

- `create_memory` signature:

  ```python
  def create_memory(
      *,
      content: str,
      request_ref: str | None = None,
  ) -> VaultCreationResult
  ```

- The service is intentionally distinct from
  `MemoryVaultMutationService` (different operation category: identity
  authoring, not state transition).

## Canonical initial state

Persisted on every successful `create_memory`:

| Field | Value |
| --- | --- |
| `memory_id` | server-generated UUID (PK) |
| `user_id` | constructor-bound account |
| `project_id` | NULL (account-scoped only) |
| `semantic_species` | `episodic_semantic_memory` (fixed) |
| `text_content` | exact authored text (whitespace preserved) |
| `fact_key`, `fact_value`, `fact_confidence` | NULL |
| `reviewed_at` | database-authored `now()` |
| `activated_at` | database-authored `now()` (same txn expression) |
| `pinned`, `held` | `false` |
| `extensions` | NULL |

Canonical readback rendered:

- `review_posture = "approved"`
- `lifecycle_posture = "active"`
- `item.identity.kind = "canonical"`
- `item.content == exact submitted content`
- `item.account_owner == authenticated account`
- `item.persona_links == []`

Caller cannot choose species, account, Project, Persona, pin, hold,
review, activation, or memory ID. No parallel canonical `review_state` /
`lifecycle_state` / `ambient_eligible` field is introduced.

## Provenance / receipt

Exactly one `memory_provenance` row is created per call.

- `source_system = "codexify"`
- `source_subject_kind = "vault"`
- `source_record_id = created canonical memory_id`
- `is_imported = false`
- `extensions.action = "create_memory"`
- `extensions.receipt_schema = "memory-vault-mutation.v1"`
- `extensions.mutation_source = "vault"`
- `extensions.actor_account_id = authenticated account`
- `extensions.previous_values = {"exists": false}`
- `extensions.new_values = {"exists": true, "semantic_species":
  "episodic_semantic_memory", "project_id": null, "review_posture":
  "approved", "lifecycle_posture": "active", "pinned": false, "held":
  false}`
- `extensions.reason = null`
- `extensions.request_ref = caller supplied or null`
- `extensions.resulting_created_at / resulting_updated_at` are recorded

Receipt payload never contains the authored content. Provenance
carries `source_record_id = created canonical memory_id` as a typed
opaque reference, not as content copy. No Person display, profile, or
prompt data is stored.

## Atomicity proof

Forced `before_flush` failure on receipt-insertion during a creation
mutates the session into integrity-error; service rolls back via
`session.rollback()` and raises `MemoryVaultCreationIntegrityError`.
After rollback: zero `memory_records` rows, zero `memory_provenance`
rows. No orphan canonical state.

## Readback proof

Return value `VaultCreationResult.item` is produced by
`MemoryVaultReadService.get_item(identity=...)` for the same account.
The creation service contains no duplicated read-projection logic. The
service asserts presence of the readback before returning; if `get_item`
returns `None` it raises `MemoryVaultCreationIntegrityError`.

## HTTP proof

- Endpoint: `POST /api/memory-vault/items` (status `201`).
- Reuses the existing `/api/memory-vault/items` GET route; no new path.
- Request model: `VaultCreateMemoryRequest(content: str, request_ref:
  str | None = None)`. Required fields are `content`; optional is
  `request_ref`. No other fields accepted.
- Response model: `VaultCreationResponse(receipt_id: str, item:
  VaultItemResponse)` — reuses `VaultItemResponse`.
- Service dependency factory: `get_memory_vault_creation_service`,
  shares the same DB session authority as the read and mutation
  services.
- The route delegates exactly `creation_service.create_memory(content=,
  request_ref=)`. No SQL, no Project lookup, no Persona lookup, no
  CAS, no receipt construction, no retrieval, no read-before-write.
- Failure posture:
  - 401 blank account
  - 422 missing/invalid content (Pydantic)
  - 422 whitespace-only content (service-layer mapped)
  - 409 integrity failure (`MemoryVaultCreationIntegrityError`)
- The old GET and PATCH mutation routes (pin, hold, project-scope,
  persona-attribution) remain qualified and unchanged.

## Control-plane proof

- The Memory Vault router now exposes (per admitted web profile):
  - `GET  /api/memory-vault/items`
  - `POST /api/memory-vault/items`
  - `GET  /api/memory-vault/items/canonical/{memory_id}`
  - `GET  /api/memory-vault/items/compatibility/{source_kind}/{source_id}`
  - `PATCH /api/memory-vault/items/canonical/{memory_id}/pin`
  - `PATCH /api/memory-vault/items/canonical/{memory_id}/hold`
  - `PATCH /api/memory-vault/items/canonical/{memory_id}/project-scope`
  - `PATCH /api/memory-vault/items/canonical/{memory_id}/persona-attribution`
- 7 unique path templates (per spec: C6 adds POST to the existing
  `/items` rather than creating an eighth path).
- All remain hidden from public OpenAPI:
  `assert not (VAULT_PATHS & openapi_paths)`.
- Feature flag `CODEXIFY_ENABLE_MEMORY_VAULT_ROUTES=false` removes
  every path including the new POST.
- Quarantined profile (e.g. `v1-user-profile-accent-proof`) + flag true
  keeps the router off entirely.
- `guardian/guardian_api.py` is unchanged (SHA verified).
- `config/supported_profiles/*` shows no diff.
- Legacy `memory` route posture remains `quarantined` everywhere.

## PostgreSQL proof

- Server: Homebrew PostgreSQL 17.6 on `127.0.0.1:5432` (sandbox cannot
  bind fresh `initdb` on `/tmp` because `shmget` is blocked there; see
  C5 proof).
- Role: `codexify_test_runner` (LOGIN, CREATEDB, NOSUPERUSER).
- Isolation mechanism (Case A from C5): tests directly mutate
  uniquely-named disposable child databases
  (`ums05c6_<random>`) that the fixture creates via
  `psycopg.connect(admin_url, autocommit=True)` and drops after
  qualification. The admin `postgres` database has zero tables
  (`\dt` → "Did not find any relations").
- The homebrew port-5432 server also holds unrelated long-lived
  databases (`Codexify`, `threadspace_db`, etc.); none are created,
  read, or mutated by C6 qualification.

## Regression results

| Surface | Result |
| --- | --- |
| `test_memory_vault_creation.py` (focused C6) | 15 passed |
| `test_memory_vault_mutation.py` (C1–C5) | 52 passed |
| `test_memory_vault.py` (route surface) | 89 passed |
| `test_memory_vault_activation.py` | 7 passed |
| `test_memory_vault_read_projection.py` | 24 passed |
| `test_account_export_restore_unified_memory_roundtrip.py` | 1 passed |
| `test_persona_subject_identity_migration.py` | 4 passed |
| `test_protocol_tokens.py` | 36 passed |
| `py_compile` (5 authorized Python files) | PASS |
| Alembic heads | one head `7e5a5fccf253` |
| `pre-commit` (executable hooks after `gitleaks` skip) | PASS |
| `validate_docs.py` | PASS |
| `git diff --check` | PASS |

## Runtime / control-plane immutability

```text
guardian/services/memory_vault_mutation.py   unchanged
guardian/services/memory_vault_read.py      unchanged
guardian/protocol_tokens.py                  unchanged
guardian/guardian_api.py                     unchanged
config/supported_profiles/*                  unchanged
account export/restore implementation        unchanged
```

## ADR impact

Aligned with ADR-084, `unified-memory-store-contract.md`, and
`memory-vault-contract.md`. No new ADR. No architecture semantic change.
Existing canonical UMS persistence, provenance, read authority, and
mutation spine were reused.

## Limitations

- No Project, Persona, pin, hold, review-state, lifecycle-state,
  ambient-eligibility, or memory-ID caller authority.
- No Personal Facts creation; no model calls; no summarization, no
  classification, no rewriting.
- No conversational "remember" command yet.
- No idempotency claim from `request_ref` — creation may repeat and
  produces distinct canonical IDs each time.
- Branch-local qualification only. Not deployed, not exposed via
  Preview, not merged into the current `main`. C6 is reachable
  exclusively through internal-only routes on
  `feature/ums-continued`.
- UMS-05C remains OPEN. UMS-05C7 remaining mutation authority
  revalidation is the sole next authorized slice; UMS-05C8+,
  UMS-05D+, and UMS-06+ remain unauthorized.
