# Continuity Persistence Adapter Live DB Proof

**Artifact window:** 2026-06-25T19:45:00Z to 2026-06-25T20:00:00Z  
**Branch:** `main`  
**HEAD commit:** `3d5c9d34b`  
**Adapter commit:** `3d5c9d34b` (then narrow repairs applied)  
**Migration revision:** `e8d1f2a3b4c5` (add continuity Phase A tables)  
**Proof classification:** PASS  

## 1. Prior Gap

The persistence adapter was implemented but 13 live DB adapter tests were skipped because `GUARDIAN_DATABASE_URL` was unavailable. This proof closes that gap by running the adapter against the supported local Docker Compose Postgres stack.

## 2. Scope

**Tested:**

- Docker substrate health and clean reset
- Migration to current HEAD (`e8d1f2a3b4c5` confirmed)
- Live DB persistence adapter tests — all 31 ran, none skipped
- Full focused continuity suite — 136 tests, none skipped
- Adapter write/read round-trip for all four Phase A tables
- Validation rejection (invalid records rejected before writes)
- Transaction atomicity (link batch failure rolls back entire batch)
- Uniqueness enforcement (duplicate links rejected)
- Provenance preservation (JSONB fields survive round-trip)
- Graph-off baseline (no Neo4j used)
- No runtime wire paths

**Narrow defects found and repaired:**

| Defect | Root Cause | Repair |
|---|---|---|
| String timestamps rejected by Postgres | ISO-8601 strings passed directly to `TIMESTAMPTZ` columns | Added `_parse_ts()` helper converting ISO strings to `datetime` |
| `created_at=NULL` on link rows | `created_at` column is NOT NULL without `server_default` | Set `created_at=datetime.now(timezone.utc)` in link builder |
| `user_id=NULL` rejected by NOT NULL constraint | `ContinuityScope` without `user_id` produced NULL scope columns | Default `user_id` to `"local"` when not set (seed-default user) |
| `_ensure_uuid` discarded short IDs | String IDs < 32 chars replaced with random UUIDs, breaking readback | Preserve any non-empty value as-is; only generate UUID when empty |
| Test mutated frozen dataclass | `state_a.scope = "project"` on frozen `RealityState` | Constructed `RealityState` directly with correct scope |

**Not tested:**

- Runtime write paths (none exist)
- Compiler persistence wiring (none exists)
- API routes (none exist)
- Workers (none exist)
- Project Pulse UI (none exists)
- Browser capture (none exists)
- Graph writes (none used)
- Sync (none exists)
- Export/restore inclusion (none exists)

## 3. Environment

| Item | Value |
|---|---|
| Artifact date | 2026-06-25 |
| Branch | `main` |
| Adapter HEAD (pre-repair) | `3d5c9d34b` |
| Docker Desktop | 4.79.0 (230596) |
| Postgres | localhost:5433, healthy |
| Redis | Docker Compose, healthy |
| Neo4j | Docker Compose, running (not used) |
| Graph writes | Not used |
| Provider calls | None |
| `GUARDIAN_DATABASE_URL` | `postgresql://codexify:***@localhost:5433/Codexify` |

## 4. Exact Commands

```sh
# Docker substrate health
docker compose down -v                              # clean
docker compose up -d db redis neo4j                 # all healthy
docker compose run --rm migrator                    # ~50 migrations, e8d1f2a3b4c5 at HEAD
docker compose run --rm --entrypoint python migrator \
  -m alembic -c /app/backend/alembic.ini current    # confirmed: e8d1f2a3b4c5

# Live DB persistence tests
GUARDIAN_DATABASE_URL="$PG_URL" \
  .venv/bin/pytest -v tests/continuity/test_persistence_adapter.py

# Full continuity suite
GUARDIAN_DATABASE_URL="$PG_URL" \
  .venv/bin/pytest -v \
    tests/continuity/test_persistence_adapter.py \
    tests/continuity/test_phase_a_storage_schema.py \
    tests/continuity/test_contracts.py \
    tests/continuity/test_compiler.py
```

## 5. Live DB Adapter Test Results

**Command:** `GUARDIAN_DATABASE_URL=... pytest -v test_persistence_adapter.py`

**Result: 31 passed, 0 skipped**

All 13 previously-skipped live DB tests now execute and pass:

| Test | Result |
|---|---|
| `test_save_valid_context_packet` | PASS |
| `test_save_context_packet_preserves_provenance` | PASS |
| `test_save_valid_reality_state` | PASS |
| `test_save_reality_state_preserves_source_packet_ids` | PASS |
| `test_save_reality_state_no_auto_links` | PASS |
| `test_save_valid_reality_commit` | PASS |
| `test_link_state_packets_creates_rows` | PASS |
| `test_link_duplicate_causes_failure` | PASS |
| `test_load_reality_state_roundtrip` | PASS |
| `test_load_reality_state_returns_none_for_missing` | PASS |
| `test_load_latest_reality_state_by_project` | PASS |
| `test_list_reality_commits` | PASS |
| `test_link_atomicity_on_failure` | PASS |

## 6. Full Focused Continuity Suite

**Command:** `GUARDIAN_DATABASE_URL=... pytest -v test_persistence_adapter.py test_phase_a_storage_schema.py test_contracts.py test_compiler.py`

**Result: 136 passed, 0 skipped**

| Suite | Tests | Passed | Skipped |
|---|---|---|---|
| Persistence adapter | 31 | 31 | 0 |
| Storage schema | 18 | 18 | 0 |
| Contracts | 45 | 45 | 0 |
| Compiler | 42 | 42 | 0 |
| **Total** | **136** | **136** | **0** |

## 7. Persistence Behavior Verification

### Write/Read Round-Trip

| Surface | Verified |
|---|---|
| Context packet: payload_json round-trip | PASS — `{"key": "value"}` survives |
| Context packet: provenance_json round-trip | PASS — `source_packet_ids`, `source_message_ids` preserved |
| Context packet: sensitivity, retention, scope IDs, source fields | PASS |
| Reality state: state_json round-trip | PASS — full serialized contract survives |
| Reality state: extracted JSON (artifacts, assumptions) | PASS — `["file-a.py"]`, `["Assumption 1"]` preserved |
| Reality state: source_packet_ids, confidence, provenance | PASS |
| Reality state: no auto-created links | PASS — 0 links after state-only save |
| Reality commit: kind, trigger, prev/new state IDs, provenance, summary | PASS |
| Load by ID: returns correct state | PASS |
| Load latest by scope: returns most recent compiled_at | PASS |
| List commits: returns bounded newest-first commits | PASS |

### Validation Rejection

| Surface | Verified |
|---|---|
| Invalid ContextPacket rejected before write | PASS — validation errors returned, no row created |
| Invalid RealityState rejected before write | PASS |
| Invalid RealityCommit rejected before write | PASS |
| Empty state_id for link rejected | PASS |
| Empty relationship for link rejected | PASS |
| Empty packet_ids for link rejected | PASS |

### Transaction / Uniqueness

| Surface | Verified |
|---|---|
| Link batch atomicity | PASS — duplicate in batch causes entire batch rollback; no partial links |
| Uniqueness constraint enforced | PASS — duplicate `(state_id, packet_id, relationship)` triples rejected |

## 8. Graph-Off and Runtime Gate Verification

- No Neo4j imports or API calls in persistence.py (AST verified)
- No route, worker, provider, Redis, broker, or chat runtime imports in persistence.py
- No compiler auto-persistence — adapter never calls `compile_reality_state()`
- No graph writes — Neo4j running but unused for continuity operations
- No browser capture
- No sync behavior
- No export/restore inclusion

## 9. Runtime Non-Goals

This proof does not and must not be interpreted as:

- Proving any runtime write path exists — the adapter is called only by tests
- Proving compiler output is persisted automatically — the compiler remains pure
- Proving workers emit continuity events — no continuity workers exist
- Proving API routes serve continuity records — no continuity routes exist
- Proving UI renders continuity data — no Project Pulse or continuity UI exists
- Proving graph writes are enabled — graph writes remain default-off
- Proving sync behavior exists — no sync protocol exists
- Proving export/restore includes continuity — no export/restore continuity inclusion exists
- Widen the supported beta release promise — `00-current-state.md` remains unchanged

## 10. ADR Impact

- **Classification:** Aligned with ADR-030 and ADR-031
- This proof confirms the persistence adapter works correctly against the supported Postgres schema. The adapter validates contracts, preserves provenance, enforces atomicity, and rejects invalid input — all without runtime wiring, Neo4j, or provider dependencies.
- The narrow defect repairs (5 items) are bounded to the adapter and test modules only. No runtime surface was touched.

## 11. Outcome

**PASS** — outcome: `go`

All 136 continuity tests pass against live Postgres. Zero skips. The adapter is proven correct against the Phase A schema.

## 12. Follow-Up

**Next task:** Write-on-explicit-action Reality Stamp / Reality Commit MVP contract (step 5 of ADR-030's approved implementation order).

The adapter is proven. The next gated step is defining the minimal write-on-explicit-action contract for manual Reality Commit creation — still no heartbeat, no compiler auto-persistence, no route/worker writes.
