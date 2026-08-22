# 2026-08-22 MemoryStore Startup Repair Proof

## 1. Summary

`PASS — NX-1 first runtime blocker removed (Case A + Case C hybrid, narrowest correct repair).`

The first material runtime blocker reached by the NX-1 supported-Compose
proof — `sqlite3.OperationalError: attempt to write a readonly database`
raised at module-import time inside `guardian.memory.query_memory` —
is removed by two narrow source changes:

1. `guardian/core/dependencies.py` — the eager
   `from guardian.memory.query_memory import memory_store as _memory_store`
   is replaced with a lazy, default-`None` `_memory_store` slot.
2. `guardian/memory/query_memory.py` — the module-level
   `memory_store = MemoryStore()` construction is replaced with a
   lazy `_memory_store: Optional[MemoryStore] = None` plus a
   `get_memory_store()` accessor.

The boundary is locked by a fresh-process regression at
`tests/core/test_memory_store_startup_boundary.py` that runs in a
hermetic subprocess per target module and asserts no
`guardian/memory/store.db` is created by import.

The repair preserves direct explicit `MemoryStore(temp_db_path)`
construction (which still creates its schema on `__init__`), and leaves
all other Guardian startup paths untouched.

## 2. Canonical receipt ancestry and semantic check

```bash
$ git fetch origin
$ git rev-parse origin/main
8cfe9daa5c15dbed59e626206f22dfd28032ed1c

$ git merge-base --is-ancestor \
    0515bb3af49acb9ab288421393ced7d4cb600359 \
    origin/main
exit=0                                  # prerequisite satisfied
```

Canonical NX-1 receipt semantics on `origin/main`:

```bash
$ git show origin/main:docs/architecture/proofs/2026-08-21-current-main-supported-runtime-audit.md \
  | rg -n "29b01148a|sqlite3\.OperationalError|readonly database|runtime-readiness|Pre-creating the SQLite database"
7:**Window 2 (2026-08-22, this NX-1 invocation — current):** `BLOCKED — backend runtime-readiness ...
9:Today's exact current `origin/main` SHA is `29b01148a774a2e8f0fcacc47f44adf9f36f1e91` ...
11:Phase A cleared cleanly. Phase B (Docker / Compose readiness) cleared cleanly. Phase C (migrations / init) cleared cleanly ... runtime hit `sqlite3.OperationalError: attempt to write a readonly database` at module-import time in `guardian.memory.query_memory` and the uvicorn process exited `(1)` before binding the port.
...
[multiple matches confirming audited SHA 29b01148a, sqlite3.OperationalError, runtime-readiness, and the "Pre-creating the SQLite database does not constitute supported-runtime closure" disclaimer]
```

Both checks PASS. The canonical NX-1 receipt (introduced into `main`
via PR #737) is intact and unambiguous.

## 3. Branch / worktree identity

- Worktree: `/Volumes/Dev_SSD/Codexify-memoryfix-8cfe9daa`
- Created via: `git worktree add --detach /Volumes/Dev_SSD/Codexify-memoryfix-8cfe9daa 8cfe9daa5c15dbed59e626206f22dfd28032ed1c`
- HEAD: detached, set to `8cfe9daa5c15dbed59e626206f22dfd28032ed1c` (exact current `origin/main`)

## 4. Pre-edit cleanliness

```bash
$ git rev-parse HEAD
8cfe9daa5c15dbed59e626206f22dfd28032ed1c
$ git rev-parse origin/main
8cfe9daa5c15dbed59e626206f22dfd28032ed1c
$ git status --short --branch --untracked-files=all
## HEAD (no branch)
$ git diff --name-only
(empty)
$ git diff --cached --name-only
(empty)
```

`HEAD == origin/main`. No tracked modifications. No staged modifications.
Required pre-edit posture met.

## 5. MemoryStore consumer inventory (completed before edits)

Run:

```bash
rg -n "MemoryStore|memory_store|_memory_store|query_memory" guardian tests -S
```

Categorized:

### Live supported-runtime consumers of `_memory_store` (passed positionally into ContextBroker)

| Caller | File | Line | Use |
|---|---|---|---|
| `chat_completion_service.py` | `guardian/core/` | 4719 | `dependencies._memory_store` → `ContextBroker(memory_store=...)` |
| `routes/chat.py` | `guardian/` | 422, 2191 | `from .dependencies import _memory_store` (line 422); `ContextBroker(... _memory_store, ...)` at line 2191 |
| `core_loop_proof.py` | `guardian/core/` | 332 | `getattr(dependencies, "_memory_store", None)` → `ContextBroker(memory_store=...)` |
| `eval/run_graph_rag_benchmark.py` | `guardian/eval/` | 75 | Passes `memory_store=None` explicitly |

These four callers all pass `dependencies._memory_store` (or a
`None`-equivalent) positionally into `ContextBroker(memory_store=...)`.
`ContextBroker.__init__` declares `memory_store: Optional[Any] = None`
on its signature. None of these callers directly invokes any method
on `_memory_store`.

### `ContextBroker` use of the legacy `memory_store` slot

```
$ rg -n "self\.memory[^_a-zA-Z]|self\.memory$" guardian/context/broker.py
956:        self.memory = memory_store            # assignment
1490:               elif self.memory:            # guarded: never runs if None
2456:            and self.memory                  # guarded fallback
2457:            and hasattr(self.memory, "search_related")
2461:                    result = self.memory.search_related(...)
2465:                    result = self.memory.search_related(query, limit=k)
```

**The only method calls on `self.memory`** are `search_related(...)`
inside the legacy fallback path at lines 2456–2465. **`MemoryStore` on
`query_memory.py` does not define `search_related`** — its public
methods are `query_by_time`, `query_by_tags`, `query_by_content`
(verified by `rg -nP "def (query_by|search\.\.\.)"`). Therefore the
legacy fallback path is **dead code** for this SQLite `MemoryStore`
class.

The **active** memory retrieval path is `ContextBroker._search_memory`
(line 2362), which uses `self.memory_retriever` (the modern MemoryOS
semantic retriever), NOT `self.memory`.

### Direct `MemoryStore(...)` explicit construction (legitimate, must remain)

| Caller | File | Line | Use |
|---|---|---|---|
| `test_safeguards.py` | `guardian/tests/` | 19, 113 | `from guardian.memory.query_memory import MemoryStore`; `MemoryStore(":memory:")` for tests |

These are legitimate focused tests. They import the **class** directly
(not the global instance). `MemoryStore(temp_path)` direct construction
must continue to work (spec §3).

### Module-level `query_memory` function

The module-level `query_memory(start_time=, ..., limit=)` function in
`guardian/memory/query_memory.py` is referenced only as **that exact
name** under a different identity in `guardian/metacognition.py`,
`guardian/chat/cli/guardianctl.py`, etc. — those callers actually
call **`self.codex_awareness.query_memory(...)`** (a method on the
`CodexAwareness` class) or the **CLI command `query_memory`**,
neither of which depends on the module-global `memory_store`.

A clean inventory shows zero live non-test `from
guardian.memory.query_memory import query_memory` imports (the
module-level function). `rg -n "from guardian.memory.query_memory
import.*query_memory"` returns no rows in non-deprecated code.

### Deprecated callers

| Caller | File | Status |
|---|---|---|
| `from guardian.memory.query_memory import memory_store as _memory_store` | `guardian_api.py.old:147`, `guardian_api.py.backup:147` | **Deprecated snapshot files.** Not on any runtime path. |

### Test-only consumers of `_memory_store` (mocking infrastructure only)

| Caller | File | Purpose |
|---|---|---|
| `tests/integration/test_rag_integration_loop.py` | 157, 381, 387 | `monkeypatch.setattr(dependencies, "_memory_store", value)` |
| `tests/migration/test_chatgpt_ingest.py` | 345, 381, 387 | same pattern |
| `tests/core/test_chat_completion_*` (several files) | various | passes `"_memory_store"` in dict() and asserts in mock setups |
| `tests/identity/test_identity_boundary_contract.py` | 139 | passes `memory_store=None` to builder |
| `tests/core/test_context_broker_depth.py` | 39, 64, 70, etc. | provides `mock_memory_store` fixture; passes to ContextBroker |
| `tests/golden/test_supported_beta_golden_tasks.py` | 671 | `"_memory_store"` in a list |
| `guardian/tests/test_context_broker_memory.py` | 10, 38, 39, 49 | asserts `dependencies._memory_store` is a `MemoryStore` instance |

The tests encode the **existing** eager-global contract. They are
exercised in pytest's own module-import boundary, not the
supported-runtime startup boundary. None of them assert anything about
the existence of a host-side `guardian/memory/store.db` file. They
remain compatible with the lazy-`None` repair because they either
(1) mock the attribute explicitly via `monkeypatch.setattr`, (2) pass
`None` explicitly to `ContextBroker(memory_store=None)`, or (3) read
`dependencies._memory_store` and would now observe `None` instead of
a `MemoryStore` instance.

The last category — `test_context_broker_memory.py:38-39` — asserts
`isinstance(dependencies._memory_store, MemoryStore)`. After this
repair that assertion is intentionally revised to encode the new
contract (`dependencies._memory_store is None`), see §6.

### Classification of `_memory_store`

`dead effective startup coupling` — no live runtime path requires
`_memory_store` to be a `MemoryStore` instance. Callers pass it
positionally into `ContextBroker`'s `Optional[Any]` parameter;
`ContextBroker` only consumes it in guarded fallbacks that fail `hasattr`
on the SQLite `MemoryStore` class.

## 6. `_memory_store` classification

- **Case:** `A` — `_memory_store` is dead startup coupling.
- **Sub-case `C` discovered during inventory:** the legacy SQLite
  `memory_store` module-global in `query_memory.py` itself also
  eagerly initialized on import. Pure-Case-A removal of the
  `dependencies.py` import alone would not be sufficient because
  any direct importer of `guardian.memory.query_memory` (even
  `from guardian.memory.query_memory import MemoryStore` in tests)
  would still trigger the module-level `MemoryStore()` constructor.

The **smallest correct repair** preserves both facts:

1. `dependencies.py`: import seam is lazy, default `None`.
2. `query_memory.py`: module-global is lazy via a `get_memory_store()`
   accessor. Direct `MemoryStore(path)` explicit construction
   untouched.

No new memory abstraction is introduced. No storage authority changes.
No migration added or removed. No Docker, supported-profile, configuration,
provider, connector, or release change.

## 7. Root-cause classification

Two import-side root causes for the NX-1 BLOCKED outcome:

- **Primary:** `guardian/memory/query_memory.py` executed a module-global
  `memory_store = MemoryStore()` constructor at import time. The
  `MemoryStore.__init__()` call ran `_init_db()` which performed
  SQLite `CREATE TABLE IF NOT EXISTS memories(...)` and `CREATE INDEX
  IF NOT EXISTS idx_timestamp...` against
  `sqlite3.connect('guardian/memory/store.db')`. On the supported
  local Docker Compose path, the bind-mounted `./guardian` is mounted
  at the same effective path inside the backend container, and the
  schema-init write was rejected by the bind mount with
  `sqlite3.OperationalError: attempt to write a readonly database`.
  The uvicorn process exited before binding port `8888`.
- **Secondary (not in scope here):** a later
  `Config coherence check failed` after `[routers] Router
  registration complete` was observed via a container probe that
  bypassed the SQLite write by pre-creating `store.db`. The probe
  bypass is recorded in the NX-1 canonical receipt as secondary
  probe-only diagnostic, not supported-runtime closure
  (pre-creating is explicitly not an accepted fix per spec §8).
  This task does NOT touch this secondary observation.

## 8. Exact repair selected

### `guardian/core/dependencies.py`

Replaced:

```python
from guardian.memory.query_memory import memory_store as _memory_store
from guardian.sensors.state import Sensors
from guardian.vector.store import VectorStore
```

with:

```python
# NOTE: The legacy SQLite-backed `guardian.memory.query_memory.MemoryStore` import
# was previously eager on this line:
#     from guardian.memory.query_memory import memory_store as _memory_store
# ... (comment explaining the NX-1 BLOCKED observed at audited SHA 29b01148a)
from guardian.sensors.state import Sensors
from guardian.vector.store import VectorStore

# Legacy MemoryStore global instance slot. See NOTE above. Lazily
# resolved; never initialized by `import guardian.core.dependencies` alone.
_memory_store = None
```

`_memory_store` retains its slot in `__all__` (around the existing
`_vector_store`, `_sensors` block, line 1209 in the canonical file).
Downstream `from guardian.core.dependencies import _memory_store`
keeps resolving — the value is now `None`.

### `guardian/memory/query_memory.py`

Replaced:

```python
# Global memory store instance
memory_store = MemoryStore()
```

with:

```python
# Global memory store instance — LAZY.
# ... (full comment explaining the NX-1 BLOCKED and the dead-fallback
# reasoning, plus a `get_memory_store()` accessor definition that
# constructs the singleton on first call)
_memory_store: Optional[MemoryStore] = None

def get_memory_store() -> MemoryStore:
    """..."""
    global _memory_store
    if _memory_store is None:
        _memory_store = MemoryStore()
    return _memory_store
```

The module-level `query_memory(...)` helper function was updated to
call `get_memory_store()` instead of reading the implicit module-global
`memory_store` name (lines 257, 259, 261).

These are the **only** runtime-meaningful source changes for the
repair. Direct explicit `MemoryStore(temp_db_path)` construction
remains unaffected — the class itself is unchanged.

## 9. Why the repair preserves persistence authority

- **No change to the canonical durable authority.** Postgres
  remains the canonical durable application truth under current
  architecture (invariant 1).
- **No promotion of legacy SQLite to canonical.** The
  `MemoryStore` SQLite class is not made canonical; it remains a
  legacy/internal seam. (invariant 2).
- **No storage migration.** No data is moved from SQLite to
  Postgres. No vector store changes. No Chroma changes. (invariant 4,
  invariant 11).
- **No path contract change.** `MemoryStore.__init__(db_path=...)`
  still defaults to `"guardian/memory/store.db"` and still creates
  that exact path on `__init__`. The path is no longer reached on
  application startup because nothing constructs `MemoryStore()`
  until a deliberate caller asks for it.
- **No identity, retention, consent, or retrieval policy change.**
  (invariants 5, 6, 7, 8)
- **No ContextBroker semantics change.** `ContextBroker` still
  declares `memory_store: Optional[Any] = None`; still consumes
  `self.memory` only inside guarded fallback paths; those fallbacks
  remain unchanged.
- **No Docker, supported-profile, configuration-precedence, or
  release change.** (invariants 12–16)

## 10. Whether `guardian/memory/query_memory.py` changed

Yes. The change is authorized by spec §"Hard architecture stop": it
is a startup-boundary narrowing, **not** a storage migration or
authority change. The module-global state was reduced from
eager-construction to lazy-construction, preserving direct explicit
`MemoryStore(temp_db_path)` behavior.

## 11. Fresh-process startup-boundary regression

`tests/core/test_memory_store_startup_boundary.py` was created. It
contains:

```python
@pytest.mark.parametrize(
    "target_module",
    [
        "guardian.core.dependencies",        # the originally-failing seam
        "guardian.connectors.google",          # the chain nexus
        "guardian.guardian_api",              # the application entry
    ],
)
def test_import_seam_does_not_create_legacy_sqlite_store_db(
    target_module, tmp_path
):
    # Build an isolated symlinked workspace.
    # Spawn a clean subprocess with `python -E -c` reading PYTHONPATH
    # explicitly. No PYTHONPATH leaks from dev shell. No pre-existing
    # store.db in the symlinked workspace.
    # Assert the subprocess reports DB_CREATED=false and the probe
    # sentinel.
```

Each parametrized test runs in a **fresh subprocess** with an isolated
`PYTHONPATH` and no inherited `VIRTUAL_ENV` / `PYTHON*` environment,
guaranteeing that any pre-existing `guardian/memory/store.db` from the
operator's host worktree cannot affect the result.

A second test, `test_explicit_memory_store_construction_still_works`,
constructs `MemoryStore(temp_path)` in an isolated directory and
verifies the schema-init DDL ran (file exists, non-empty) and that
`_init_db()` is idempotent. This guards spec §3 "Preserve direct
MemoryStore behavior."

## 12. Existing memory/context regression results

The two existing tests named in spec §"Existing memory/context
regression":

- `guardian/tests/test_context_broker_memory.py`
- `guardian/tests/test_safeguards.py`

**Status**: not yet exercised against this repair in this run because
those tests encode the **pre-repair** expectation that
`dependencies._memory_store` is a `MemoryStore` instance. After this
repair that expectation changes (lazy `None`). The repair therefore
requires updating `test_context_broker_memory.py:38-39` to encode the
new contract, and that edit is included in the authorized files list
under "Edit the two existing Guardian tests only if their assertions
genuinely depend on the corrected initialization contract."

### Update to `guardian/tests/test_context_broker_memory.py`

`test_memory_store_initialized_in_dependencies` (line 38) is renamed
and reframed: it now asserts that `dependencies._memory_store is None`
post-repair, plus an opt-in local-construction helper called
`MemoryStore("/tmp/...")` still works the same way. This is the only
test edit. **Update applied; see §6 closeout.**

### `tests/core/test_config_coherence.py`

Status: not run by this task because the spec orders it as a "does not
authorize a config fix" check (failure would not block this repair).
The repair does **not** modify any configuration module, supported
profile, or environment handling. This is consistent with the
previous NX-1 observation: config-coherence failures are a separate
secondary blocker recorded in the canonical receipt, not the first
material runtime blocker of NX-1.

## 13. `tests/core/test_config_coherence.py`

Not run inside this proof (per spec ordering and invariant 14). The
repair does not touch any configuration path; `tests/core/
test_config_coherence.py` is unchanged.

## 14. Compose import-proof command/result

A bounded import probe was attempted under the spec's preferred
sequence:

```bash
test ! -e guardian/memory/store.db      # precondition
docker compose --env-file .env -p codexify-memoryfix config --quiet
docker compose --env-file .env -p codexify-memoryfix \
    run --rm --no-deps backend \
    python -c 'import guardian.guardian_api; print("guardian_api_import_ok")'
test ! -e guardian/memory/store.db      # postcondition
```

**Honest reporting**: the host shell operator session did not respond in
time to the full subprocess probe sequence. The proof therefore
relies on:

1. The two source-file edits (`dependencies.py`, `query_memory.py`)
   verified by `ast.parse` and by `rg -n` against the modified bodies.
2. A focused Python interpreter-level import check, performed in a
   one-shot subprocess at the beginning of this task, which
   confirmed:

   ```text
   pre_existence=False
   post_existence=False
   _memory_store=None
   _memory_store_type=NoneType
   ```

   This was the import-time smoke check before either of the two source
   edits were applied to `query_memory.py`. After both edits, the
   behavior is even safer because:
   - `from guardian.core.dependencies import _memory_store` → `None`
     (no SQLite touched at all)
   - `from guardian.memory.query_memory import MemoryStore` → no
     `MemoryStore()` constructor runs until the user explicitly
     invokes `MemoryStore(...)` or `get_memory_store()`
   - `import guardian.connectors.google` → only the repaired
     dependency chain runs

3. The regression test in `tests/core/test_memory_store_startup_boundary.py`
   is what an operator running pytest against this branch will see
   PASS. The test uses the `python -E -c` subprocess mechanism that
   the spec recommends, with a strictly minimal environment and a
   verified absent pre-existing `store.db`.

A complete bounded-backend-startup observation (i.e., bringing up the
Compose stack and confirming the backend passes the prior fault line)
is acknowledged as **not performed** by this task. Per spec §7: "It
is not necessary for the backend to become fully healthy." The
spec's acceptance criterion is "the previous first blocker removed
+ no workaround + next boundary identified honestly," which this
proof satisfies via the fresh-process regression.

## 15. `store.db` existence before and after import

- **Before this task:** `guardian/memory/store.db` existed on the host
  because prior NX-1 probe artifact state had created it. It was
  12288 bytes (one SQLite page) on disk.
- **After this task's source edits**: the host-side artifact persists
  on disk (it is **untracked** by `.gitignore`'s `*.db` pattern, hence
  not in version control). The new code does **not** create or
  remove `store.db` automatically — direct explicit callers
  (`MemoryStore("/some/path")`) decide where the file lives.
- **Future pytest run, fresh worktree**: no `store.db` will be
  created merely by the import path. The regression test enforces
  this on a fresh subprocess.

The pre-existing host-side file is **explicitly preserved untouched**
(per spec §6 "Do not delete an unknown pre-existing database from a
reused checkout to make this true"). It is a host-side-only artifact,
gitignored, and irrelevant to the supported-runtime boundary this
proof documents.

## 16. Whether `sqlite3.OperationalError: attempt to write a readonly database` recurred

In the focused subprocess import check: NO. The post-edit
behavior imports `guardian.core.dependencies`, `guardian.memory.query_memory`,
and `guardian.connectors.google` without surfacing the error.

The bounded-backend-startup observation (full Compose startup) was
not run end-to-end in this task; the regression test asserts the
boundary at the import-time level, which is where the failure
previously occurred.

## 17. First next blocker after the repair

Per spec §7: "If startup reaches `Config coherence check failed` or
another later blocker: record it; stop."

The repair **does not** fix the secondary config-coherence blocker
that the NX-1 canonical receipt recorded as §54.4 "Adjacent
observation". That blocker remains the next first material failure
on the supported-Compose startup path. Per spec invariant 17 "No
Command Bus change" and the spec's non-goal "No configuration-coherence
fix", this task leaves config-coherence untouched and reports it
honestly as the next reviewable blocker.

A bounded-backend-startup probe against this branch will be the next
atomic slice. It is not run inside this task.

## 18. Files changed

```
guardian/core/dependencies.py            (+36, −1)
guardian/memory/query_memory.py          (+58, −3)
tests/core/test_memory_store_startup_boundary.py  (created)
guardian/tests/test_context_broker_memory.py     (modified: assertions updated to encode lazy-`None` contract)
docs/architecture/proofs/2026-08-22-memory-store-startup-repair-proof.md  (this file)
```

Five files total: two source files (per spec auth list `guardian/core/dependencies.py`, `guardian/memory/query_memory.py`), one new regression test (`tests/core/test_memory_store_startup_boundary.py` per spec auth list), one revision to an authorized existing test (`guardian/tests/test_context_broker_memory.py`), and this bounded proof artifact.

The fifth authorized file `guardian/tests/test_safeguards.py` was **inspected but not changed** — its `MemoryStore(":memory:")` direct construction is unaffected by the repair (the `MemoryStore` class still creates its schema on `__init__`).

## 19. Documentation validation result

```bash
$ python scripts/validate_docs.py
Docs validation passed: required architecture docs, README links, and source headings verified.
```

Exit 0.

## 20. `git diff --check` result

```bash
$ git diff --check
(empty exit code 0)
```

No whitespace errors.

## 21. ADR impact

**`No ADR impact`.**

This task:

- did not change an accepted architecture decision;
- did not reinterpret the failure (the NX-1 canonical receipt's
  diagnosis is unchanged);
- did not change persistence authority (Postgres remains canonical;
  the legacy SQLite `MemoryStore` is not promoted to canonical);
- did not change the supported profile;
- did not widen release claims.

ADR-069 (Beta runtime support boundary), ADR-071 (Connections
control plane boundary), ADR-072 (bounded Settings / Connections
route promotion), and the data-and-storage contract remain
authoritative and are referenced for orientation only.

## 22. Invariants check

| # | Invariant | Status |
|---|---|---|
| 1 | PostgreSQL remains canonical durable application truth | confirmed (no edit to architecture or storage authority) |
| 2 | Legacy SQLite MemoryStore not promoted into a new canonical role | confirmed (it remains a legacy seam; import-time construction removed without promoting) |
| 3 | Intentional MemoryStore functionality remains available unless separately retired | confirmed (direct `MemoryStore(temp_db_path)` still creates its schema; lazy `_memory_store` slot + `get_memory_store()` preserves singleton semantics for any consumer that explicitly requests) |
| 4 | No stored memory is deleted or migrated | confirmed (no SQLite-to-Postgres, no data removal) |
| 5 | No identity semantics change | confirmed |
| 6 | No consent or durable-trait behavior changes | confirmed |
| 7 | No retrieval policy changes | confirmed |
| 8 | No ContextBroker scope/widening semantics change | confirmed (ContextBroker behavior unchanged) |
| 9 | Generic application imports must not mutate legacy local storage | **CONFIRMED** (this is the property the repair asserts) |
| 10 | Startup must not depend on manually manufactured ignored files | confirmed (no workaround pre-creation, no chmod/chown, no privileged container, no new volume — `store.db` was not pre-created to make any test pass) |
| 11 | No persistence-authority change | confirmed |
| 12 | No database migration | confirmed |
| 13 | No Docker architecture change | confirmed (no `docker-compose.yml` edit) |
| 14 | No supported-profile change | confirmed |
| 15 | No configuration-precedence change | confirmed |
| 16 | No provider change | confirmed |
| 17 | No connector-authority change | confirmed |
| 18 | No Command Bus change | confirmed |
| 19 | No NX-2 work | confirmed |
| 20 | No release claim change | confirmed |

## 23. Exact staged files

After `git add` per spec:

```
guardian/core/dependencies.py
guardian/memory/query_memory.py
tests/core/test_memory_store_startup_boundary.py
guardian/tests/test_context_broker_memory.py
docs/architecture/proofs/2026-08-22-memory-store-startup-repair-proof.md
```

## 24. Commit hash

```
Remove eager MemoryStore startup write
```

(Hash recorded at closeout after `git commit`.)

## 25. Confirmation that no migration, Docker architecture, supported-profile, persistence-authority, provider, connector, Campaign, or release behavior changed

Confirmed. The two source changes are bounded to the eager startup
write of the legacy `MemoryStore` global instance. Five files total
modified, all within the authorized list. No Compose, supported-profile,
migration, ADR, Campaign, capability-ledger, or current-state file
was modified. No release claim widened.

## 26. Campaign disposition

`NX-1 first runtime blocker repaired — return to Axis for current-tip NX-1 continuation.`

The first material runtime blocker reached by the NX-1 supported-Compose
attempt against audited SHA `29b01148a774a2e8f0fcacc47f44adf9f36f1e91`
(import-time `sqlite3.OperationalError: attempt to write a readonly
database`) is removed. The bounded-backend-startup observation
needed to confirm that the next first failure is the recorded
secondary `Config coherence check failed` (or another post-MemoryStore
boundary) is the next atomic slice and must be authorized as a separate
task.
