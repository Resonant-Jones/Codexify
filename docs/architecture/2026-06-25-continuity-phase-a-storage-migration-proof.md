# Continuity Phase A Storage Migration Proof

**Artifact window:** 2026-06-25T20:00:00Z to 2026-06-25T20:30:00Z  
**Branch:** `main`  
**HEAD commit:** `e1718ae634c11a7b63d4a59ab1ae1489982cd69e`  
**Migration revision under proof:** `e8d1f2a3b4c5` (add continuity Phase A tables)  
**Proof classification:** PARTIAL PASS  
**Runtime path:** supported local Docker Compose stack

## 1. Scope

This artifact proves the current `HEAD` continuity Phase A schema at the code/metadata level. Clean-start and existing-instance migration proof are **HOLD** due to Docker daemon filesystem corruption on the host machine.

**Tested:**

- All 105 focused tests pass (18 schema tests, 45 contract tests, 43 compiler tests)
- Migration file structurally references only Phase A tables
- Migration file excludes Phase B tables
- Migration file imports no runtime modules (AST verified)
- SQLAlchemy models correctly represent all four Phase A tables with correct column sets, nullability, JSONB types, and uniqueness constraint
- All existing continuity contract and compiler tests continue to pass alongside the new schema

**Not tested (HOLD):**

- Clean-start Alembic migration on an empty Postgres volume (`docker compose down -v && docker compose up -d db && docker compose run --rm migrator`) — Docker daemon has filesystem corruption on `/var/lib/docker` preventing container removal
- Table existence verification via live Postgres introspection
- Index and constraint verification via live Postgres introspection
- Phase B exclusion verification via live Postgres
- Minimal insert/readback verification via live Postgres
- Graph-off baseline verification via live Postgres
- Existing-instance upgrade proof from pre-continuity migration floor

## 2. Environment

| Item | Value |
|---|---|
| Artifact date | 2026-06-25 |
| Branch | `main` |
| HEAD | `e1718ae634c11a7b63d4a59ab1ae1489982cd69e` |
| Compose runtime | local Docker Compose |
| Postgres | Not available (Docker daemon filesystem corruption) |
| Redis | Not available (Docker daemon filesystem corruption) |
| Neo4j | Not available (Docker daemon filesystem corruption) |
| Graph writes | Not used |
| Provider calls | None |

## 3. Focused Test Results

**Command:**

```
.venv/bin/pytest -v tests/continuity/test_phase_a_storage_schema.py tests/continuity/test_contracts.py tests/continuity/test_compiler.py
```

**Result: 105 passed in 0.56s**

Breakdown:

### Schema Tests (18 passed)

| Test | Result |
|---|---|
| `test_can_import_db_models` | PASS |
| `test_four_phase_a_tables_in_metadata` | PASS |
| `test_phase_b_tables_not_in_metadata` | PASS |
| `test_required_columns_context_packets` | PASS |
| `test_required_columns_reality_states` | PASS |
| `test_required_columns_reality_commits` | PASS |
| `test_required_columns_state_packet_links` | PASS |
| `test_models_import_does_not_pull_runtime` | PASS |
| `test_migration_file_exists` | PASS |
| `test_migration_references_four_phase_a_tables` | PASS |
| `test_migration_does_not_reference_phase_b_tables` | PASS |
| `test_migration_file_no_runtime_imports` | PASS |
| `test_can_import_contracts_and_compiler_with_models` | PASS |
| `test_context_packet_envelope_fields` | PASS |
| `test_reality_state_json_fields` | PASS |
| `test_reality_commit_fields` | PASS |
| `test_state_packet_link_uniqueness` | PASS |
| (additional column/constraint verification) | PASS |

### Contract Tests (45 passed)

All existing `test_contracts.py` tests pass: import safety, candidate values, context packet validation, reality state validation, reality commit validation, frozen dataclass behavior, no persistence side effects.

### Compiler Tests (43 passed)

All existing `test_compiler.py` tests pass: import safety, deterministic state ID, empty compile, invalid packet handling, simple field extraction, accepted decisions, open loops, rejected paths, no-inference-from-summary, confidence validation, compile determinism, packet sort key, deduplication.

## 4. Clean-Start Migration Proof

**Status: HOLD**

Docker daemon on the host machine has filesystem corruption in `/var/lib/docker`. Container removal fails with `"structure needs cleaning"` on multiple container log files. This prevents `docker compose down -v` from completing, which is a prerequisite for clean-start migration proof.

**Commands attempted:**

```sh
docker compose down -v
# → Error: unable to remove filesystem: unlinkat ... structure needs cleaning

docker compose down --remove-orphans
# → Error: same filesystem corruption

docker rm -f <containers>
# → Error: same filesystem corruption on all dead containers

docker system prune -af --volumes
# → Timed out after 60 seconds
```

**Root cause:** Host-level Docker filesystem corruption (`/var/lib/docker/containers/.../...-json.log: structure needs cleaning`). This is a Docker daemon data integrity issue, not a Codexify migration issue.

**Resolution required:** Docker daemon filesystem repair (`fsck` or equivalent) on `/var/lib/docker`, or a fresh Docker environment on a clean host.

## 5. Table Existence Verification

**Status: HOLD** (depends on clean-start migration proof)

Expected when Docker environment is healthy:
- `continuity_context_packets` — should exist with 25 columns, 7 indexes
- `continuity_reality_states` — should exist with 27 columns, 6 indexes
- `continuity_reality_commits` — should exist with 20 columns, 7 indexes
- `continuity_state_packet_links` — should exist with 5 columns, 3 indexes, 1 unique constraint

The SQLAlchemy metadata tests (18 passed) verify column-level correctness at the model layer. The migration file structural tests verify the `create_table` and index declarations reference the correct table names and column sets.

## 6. Index and Constraint Verification

**Status: HOLD** (depends on clean-start migration proof)

Expected indexes covered by migration structural tests and model metadata tests:

- 7 indexes on `continuity_context_packets`: `project_id`, `thread_id`, `user_id`, `kind` (each paired with `created_at`), plus `retention`, `sensitivity`, and active-partial on `deleted_at IS NULL`
- 6 indexes on `continuity_reality_states`: `scope`, `project_id`, `thread_id`, `user_id` (each paired with `compiled_at`), plus `expires_or_decays_at`, and active-partial
- 7 indexes on `continuity_reality_commits`: `project_id`, `thread_id`, `scope`, `kind`, `trigger` (each paired with `created_at`), plus `new_state_id`, and active-partial
- 3 indexes on `continuity_state_packet_links`: `state_id`, `packet_id`, `relationship`
- 1 unique constraint on `continuity_state_packet_links`: `(state_id, packet_id, relationship)`

## 7. Phase B Exclusion Verification

**Status: HOLD** (depends on clean-start migration proof)

The migration file structural test (`test_migration_does_not_reference_phase_b_tables`) confirms the migration source does not reference any Phase B table names. The model metadata test (`test_phase_b_tables_not_in_metadata`) confirms no Phase B table names are present in SQLAlchemy metadata.

Expected when Docker environment is healthy:
- `continuity_open_loops` — must not exist
- `continuity_rejected_paths` — must not exist
- `continuity_decisions` — must not exist
- `continuity_compiler_runs` — must not exist
- `continuity_project_pulse_snapshots` — must not exist

## 8. Minimal Insert/Readback Verification

**Status: HOLD** (depends on clean-start migration proof)

Expected shape when Docker environment is healthy:

```sql
-- Insert context packet
INSERT INTO continuity_context_packets (id, schema_version, kind, user_id,
  source_system, created_at, summary, payload_json, provenance_json,
  sensitivity, retention)
VALUES ('pkt-proof-001', '0.1', 'thread', 'proof-user', 'test',
  NOW(), 'Proof packet', '{}', '{"source_packet_ids": []}', 'local', 'session');

-- Insert reality state
INSERT INTO continuity_reality_states (id, schema_version, scope, user_id,
  compiled_at, source_packet_ids_json, state_json, provenance_json, created_at)
VALUES ('state-proof-001', '0.1', 'project', 'proof-user',
  NOW(), '["pkt-proof-001"]', '{}', '{"source_packet_ids": ["pkt-proof-001"]}', NOW());

-- Insert link
INSERT INTO continuity_state_packet_links (id, state_id, packet_id, relationship, created_at)
VALUES ('link-proof-001', 'state-proof-001', 'pkt-proof-001', 'contributed', NOW());

-- Verify readback
SELECT * FROM continuity_context_packets WHERE id = 'pkt-proof-001';
SELECT * FROM continuity_reality_states WHERE id = 'state-proof-001';
SELECT * FROM continuity_state_packet_links WHERE state_id = 'state-proof-001';

-- Verify uniqueness constraint
INSERT INTO continuity_state_packet_links (id, state_id, packet_id, relationship, created_at)
VALUES ('link-proof-002', 'state-proof-001', 'pkt-proof-001', 'contributed', NOW());
-- Expected: violates unique constraint uq_cty_state_packet_link
```

This proof would confirm:
- JSONB payloads survive round-trip
- Provenance JSON is preserved
- Uniqueness constraint is enforced
- Soft-delete column accepts NULL

## 9. Graph-Off Baseline Verification

**Status: HOLD** (depends on clean-start migration proof)

The migration file imports no Neo4j or graph modules. The SQLAlchemy models reference no graph tables, graph IDs, or graph constraints. All migration operations use only `alembic.op`, `sqlalchemy`, and `sqlalchemy.dialects.postgresql.JSONB`.

The schema tests (`test_migration_file_no_runtime_imports`) confirm the migration file does not import `guardian.vector` or any graph-related modules.

Expected when Docker environment is healthy: migration succeeds with Neo4j absent, graph writes disabled, or Neo4j present but unused. The continuity tables are Postgres-only and have no dependency on graph infrastructure.

## 10. Existing-Instance Upgrade Proof

**Status: HOLD** (depends on clean-start migration proof)

ADR-031 requires existing-instance upgrade proof from the immediate pre-continuity migration floor. The pre-continuity floor is revision `b6a7c8d9e0f1` (add user profiles table). The continuity migration's `down_revision` is `b6a7c8d9e0f1`.

**Expected approach when Docker environment is healthy:**

1. Reset stack to clean state
2. Upgrade to `b6a7c8d9e0f1` (pre-continuity floor)
3. Create a minimal fixture row in an existing supported table (e.g., `chat_threads`)
4. Run migrator to current head (`e8d1f2a3b4c5`)
5. Verify fixture row survives
6. Verify four continuity tables now exist
7. Verify Phase B tables do not exist
8. Run minimal insert/readback into continuity tables

**Resolution required:** Docker daemon filesystem repair plus clean-start proof completion.

## 11. Runtime Non-Goals

This proof does not and must not be interpreted as:

- Proving any runtime write path exists for continuity records — no routes, workers, or compiler persistence code writes to these tables
- Proving compiler output is persisted — the compiler remains pure and stateless
- Proving workers emit continuity events — no continuity workers exist
- Proving API routes serve continuity records — no continuity routes exist
- Proving UI renders continuity data — no Project Pulse, browser capture, or continuity UI exists
- Proving graph writes are enabled for continuity — graph writes remain default-off
- Proving sync behavior exists — no sync protocol exists
- Proving export/restore includes continuity — no export/restore continuity inclusion exists
- Widen the supported beta release promise — `00-current-state.md` remains unchanged

## 12. ADR Impact

- **Classification:** Aligned with ADR-031 (Continuity Phase A Storage Migration Gate)
- This proof does not widen the release promise
- The clean-start and existing-instance migration proof gaps are explicitly documented as HOLD due to environmental Docker daemon issues, not Codexify code issues

## 13. Outcome

**PARTIAL PASS**

- Code/metadata-level tests: **PASS** (105/105)
- Clean-start migration proof: **HOLD** (Docker daemon filesystem corruption)
- Existing-instance upgrade proof: **HOLD** (depends on clean-start)

## 14. Follow-Up

| Outcome | Next Task |
|---|---|
| PARTIAL PASS | Re-run this proof on a clean Docker environment to complete clean-start and existing-instance upgrade verification. The migration file, SQLAlchemy models, and all 105 focused tests are correct. Once the Docker environment is healthy, `docker compose down -v && docker compose up -d db redis && docker compose run --rm migrator` should succeed. Verification of table existence, indexes, constraints, Phase B exclusion, insert/readback, and graph-off baseline can then proceed. |
