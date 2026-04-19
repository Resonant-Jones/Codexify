# Legacy Tools Shim Dependency Inventory

**Date:** 2026-04-16
**Scope:** Repo-wide inventory of every dependency edge tied to `guardian/routes/tools.py` and the legacy `/api/tools` compatibility shim. The bare `/tools` mount has been removed from the primary app and is now only present as unmounted route code.
**Method:** Grep-driven evidence collection. No runtime behavior changed.

---

## Evidence Commands Run

```bash
rg -n "guardian/routes/tools" . --type py --type ts --type tsx --type md --type yaml --type json
rg -n '"/tools"|"/api/tools"|/tools\b' . --type py --type ts --type tsx --type md --type yaml --type json
rg -n "tool_jobs|command_runs|command_run_events" . --type py --type ts --type tsx --type md --type yaml --type json
rg -n "CommandBusStore" . --type py --type ts --type tsx --type md
rg -n "legacy tools|compatibility shim|tools shim|legacy shim" . --type py --type ts --type tsx --type md
rg -n "include_router\(|APIRouter\(" guardian/
rg -n "from guardian.routes.tools|import.*tools" guardian/ tests/
rg -n "tools" frontend/src/ --type ts --type tsx
rg -n "ToolJob|tool_job" guardian/db/models.py
rg -n "tools" guardian/guardian_api.py
rg -n "tools" guardian/server/app.py
rg -n "tools" guardian/tools/overrides.py guardian/tools/registry.py
rg -n "tools" guardian/tools/derive.py guardian/tools/spec.py guardian/tools/policy.py guardian/tools/coercion.py guardian/tools/approval_tokens.py
rg -n "tools" tests/routes/test_tools*.py tests/core/test_beta_router_quarantine.py tests/core/test_supported_profile_quarantine.py tests/routes/test_retrieve_health_or_mount.py
rg -n "tool_jobs" guardian/db/migrations/
rg -n "command_runs|command_run_events" guardian/db/migrations/
```

---

## 1. Direct Route Exposure

### Routes defined in `guardian/routes/tools.py`

| Router | Prefix | Endpoints | Deprecation headers |
|---|---|---|---|
| `router` | `/tools` | Defined in `guardian/routes/tools.py` but no longer mounted by `guardian/guardian_api.py` | N/A in primary app |
| `api_router` | `/api/tools` | `GET /api/tools/manifest`, `POST /api/tools/execute`, `POST /api/tools/approve`, `GET /api/tools/jobs/{job_id}` | Yes — same headers |

**Registration in `guardian/guardian_api.py`:**
- Line 532: `from guardian.routes.tools import api_router as api_tools_router`
- Lines 1112-1119: Only `api_tools_router` is included via `_include_router()` with label `api_tools`

**Registration in `guardian/server/app.py` (legacy/alternate entry):**
- Line 27: `from guardian.server.tools_api import router as tools_router`
- Line 31: Fallback `tools_router = APIRouter()` if import fails
- Line 96: `app.include_router(tools_router)`

**Classification:** `active dependency` — only `/api/tools` is mounted in the primary `guardian_api.py` entry point; the bare `/tools` router object remains defined but unmounted.

---

## 2. Direct Imports of `guardian/routes/tools.py`

| File | Line | Import | Classification |
|---|---|---|---|
| `guardian/guardian_api.py` | 532 | `from guardian.routes.tools import api_router as api_tools_router` | `active dependency` |
| `tests/routes/test_tools.py` | 15 | `from guardian.routes import tools` | `active dependency` (test) |
| `tests/routes/test_tools_manifest_phase21_format.py` | 8 | `from guardian.routes import command_bus, tools` | `active dependency` (test) |
| `tests/routes/test_tools_phase2_spec_policy.py` | 8 | `from guardian.routes import command_bus, tools` | `active dependency` (test) |
| `tests/routes/test_tools_phase3_callable_contract.py` | 9 | `from guardian.routes import command_bus, tools` | `active dependency` (test) |
| `tests/routes/test_tools_legacy_shims_phase15.py` | 8 | `from guardian.routes import command_bus, tools` | `active dependency` (test) |

---

## 3. Frontend Callers of `/api/tools` or `/tools`

**Update 2026-04-18:** The two live frontend callers documented below have been migrated to the canonical command-bus invoke surface. They remain here as historical inventory entries so the remaining shim deletion sequence stays explicit, but they are no longer active frontend dependencies on `/tools/execute`. The bare `/tools` mount was also removed in this pass; the remaining runtime compatibility surface is `/api/tools/*`.

### 3.1 `frontend/src/features/chat/GuardianChat.tsx` (line 2025)

```typescript
const response = await api.post("/tools/execute", {
  name: "guardian.profile.switch",
  args: { thread_id: threadId, profile_id: profileId },
});
```

- **What it does:** Profile switching via the legacy shim's `tools_execute` endpoint.
- **Uses:** The `name`/`args` legacy request shape, not the command-bus `InvokeRequest` shape.
- **Classification:** `migrated` — this live frontend caller now targets `/api/guardian/commands/invoke` with the command-bus request shape.

### 3.2 `frontend/src/dcw-services/gc.ts` (lines 50-52)

```typescript
export const Tools = {
  execute:(b:any)=>req('/tools/execute',{method:'POST',body:JSON.stringify(b)}),
  job:(id:string)=>req(`/jobs/${id}`)
};
```

- **What it does:** Defines a `Tools` namespace wrapping `/tools/execute` and `/jobs/{id}`.
- **Consumers:**
  - `frontend/src/hooks/useTriggerAction.ts` (lines 1, 5, 9): `import { Tools } from "@/dcw-services/gc"` — calls `Tools.execute()` and `Tools.job()`.
  - `frontend/src/main.tsx` (line 7): `import { configureGC } from "./dcw-services/gc"` — configures the GC service layer.
  - `frontend/src/hooks/useSaveRitual.ts` (line 1): imports `Notes, Agent` from gc (not Tools).
- **Classification:** `migrated` — the wrapper now invokes the command bus and keeps only local polling/cache semantics.

---

## 4. Tests Covering Legacy Tool Routes

| Test File | Routes Tested | Classification |
|---|---|---|
| `tests/routes/test_tools.py` | `/api/tools/execute`, `/api/tools/jobs/{job_id}` | `active dependency` |
| `tests/routes/test_tools_manifest_phase21_format.py` | `/api/tools/manifest` | `active dependency` |
| `tests/routes/test_tools_phase2_spec_policy.py` | `/api/tools/manifest`, `/api/tools/execute?legacy=1` | `active dependency` |
| `tests/routes/test_tools_phase3_callable_contract.py` | `/api/tools/execute`, `/api/tools/approve`, `/api/tools/manifest`, `/api/tools/execute?legacy=1`, `/api/tools/approve?legacy=1` | `active dependency` |
| `tests/routes/test_tools_legacy_shims_phase15.py` | `/api/tools/manifest`, `/api/tools/execute?legacy=1`, `/api/tools/approve?legacy=1` | `active dependency` |
| `tests/core/test_beta_router_quarantine.py` | `/api/tools/manifest` (quarantine check) | `compatibility surface` |
| `tests/core/test_supported_profile_quarantine.py` | `/api/tools/manifest`, `/tools/manifest` (quarantine check) | `compatibility surface` |
| `tests/routes/test_retrieve_health_or_mount.py` | `/api/tools/manifest` (health/mount check) | `compatibility surface` |

---

## 5. Storage / Model Dependencies

### 5.1 `tool_jobs` table

**Model:** `guardian/db/models.py` lines 941-969

```python
class ToolJob(Base):
    __tablename__ = "tool_jobs"
    # id, tool_name, status, request_json, result_json, error, error_json, created_at, updated_at
```

**Migration:** `guardian/db/migrations/versions/9b3d2d08f7c1_add_tool_jobs_table.py`

**Usage in `guardian/routes/tools.py`:**
- `_configured_tool_jobs_db` (line 65): Global optional DB handle for test injection.
- `_persist_tool_job()` (line 810): Writes to `tool_jobs` when `_configured_tool_jobs_db` is set.
- `_load_persisted_tool_job()` (line 839): Reads from `tool_jobs` for job status lookup.
- `_execute_persisted_compat_tool()` (line 862): Uses the `tool_jobs` table for the persisted compat seam.
- `api_tools_job_status()` (line 1431): Falls back to `tool_jobs` lookup before checking in-memory `JOBS`.

**Classification:** `active dependency` — the table exists, the model is defined, and the shim code references it. However, `_configured_tool_jobs_db` is `None` by default and only set via `configure_db()` for tests. In production runtime, the `tool_jobs` path is a dead letter unless explicitly configured.

### 5.2 In-memory `JOBS` dict

**Location:** `guardian/routes/tools.py` line 64

```python
JOBS: dict[str, dict[str, Any]] = {}
```

**Writers:**
- `_store_job_snapshot()` (line 786): Stores job snapshots after command-bus execute/approve.

**Readers:**
- `tools_job_status()` (line 1365): Returns job status from `JOBS` dict.
- `api_tools_job_status()` (line 1434): Falls back to `JOBS` dict if no `tool_jobs` row found.

**Classification:** `active dependency` — process-local job tracking is still live for the retained `/api/tools` compatibility path. The direct local helper was removed, but `JOBS` remains part of the retained shim behavior until the `api_tools_job_status` path is retired.

### 5.3 `command_runs` and `command_run_events` tables

**Models:** `guardian/db/models.py` lines 2931+ (`CommandRun`), 2982+ (`CommandRunEvent`)

**Migrations:**
- `guardian/db/migrations/versions/e0f1a2b3c4d5_add_command_bus_phase1_tables.py`
- `guardian/db/migrations/versions/c2f4a8e1b9d0_add_command_run_idempotency_unique_constraint.py`

**Usage:** The shim calls `execute_invoke()` from `guardian/command_bus/invoke.py` which persists runs through `CommandBusStore` into `command_runs` / `command_run_events`. The shim does **not** directly query these tables — it delegates to the command bus store.

**Classification:** `active dependency` (indirect) — the shim is a consumer of the command bus execution lane, not an owner of these tables.

---

## 6. `guardian/tools/` Submodule Dependencies

The shim imports from several modules under `guardian/tools/`:

| Module | Imported by `tools.py` | Purpose | Classification |
|---|---|---|---|
| `guardian/tools/approval_tokens.py` | Lines 34-41 | Approval token issuance/verification for the confirm flow | `active dependency` |
| `guardian/tools/coercion.py` | Lines 42-45 | Argument coercion for tool calls | `active dependency` |
| `guardian/tools/derive.py` | Line 46 | Derives `ToolSpec` list from command-bus manifest | `active dependency` |
| `guardian/tools/policy.py` | Lines 47-51 | Tool policy evaluation and mode application | `active dependency` |
| `guardian/tools/spec.py` | Lines 52-59 | Pydantic models: `ToolCallRequest`, `ToolCallResponse`, `ToolManifestEnvelope`, `ToolSpec`, etc. | `active dependency` |

Additionally:
- `guardian/tools/registry.py` imports from `derive.py`, `overrides.py`, and `spec.py` — builds a `ToolRegistry` from the command manifest. Not directly imported by `tools.py` but part of the same tool-lane ecosystem.
- `guardian/tools/overrides.py`, `guardian/tools/state_inspector.py`, `guardian/tools/context/` — exist in the directory but are **not** imported by `tools.py`. Classification: `unclear requires manual verification` — may be dead code or used by other surfaces.

---

## 7. Command-Bus Cross-References

The shim depends on the command bus for execution:

| Reference | Location in `tools.py` | Classification |
|---|---|---|
| `from guardian.command_bus.contracts import ActorSpec, InvokeArguments, InvokeRequest` | Lines 25-29 | `active dependency` |
| `from guardian.command_bus.invoke import execute_invoke` | Line 30 | `active dependency` |
| `from guardian.command_bus.manifest import build_command_index` | Line 31 | `active dependency` |
| `from guardian.routes import command_bus as command_bus_routes` | Lines 1057, 1251 | `active dependency` (lazy import) |
| `store=command_bus_routes._store` | Lines 1064, 1258 | `active dependency` — uses command bus store directly |

The shim does **not** define its own `CommandBusStore` — it borrows the one from `command_bus_routes`.

---

## 8. Docs-Only References

| File | Reference | Classification |
|---|---|---|
| `docs/architecture/modules-and-ownership.md` | Lines 38, 55-56, 65, 95, 112-113: describes shim as "experimental", notes two-surface problem | `docs-only reference` |
| `docs/architecture/flows.md` | Lines 222, 230, 237, 250-251, 254: documents tool execution flow including shim | `docs-only reference` |
| `docs/architecture/data-and-storage.md` | Line 74: `tool_jobs` table description | `docs-only reference` |
| `docs/architecture/system-overview.md` | Lines 32, 131-138: mentions tools layer and shim | `docs-only reference` |
| `docs/architecture/tech-debt-and-risks.md` | Lines 75-76: risk statements about `/tools` vs command bus coexistence and process-local job state | `docs-only reference` |
| `docs/architecture/README.md` | Line 89: source anchor listing `guardian/routes/tools.py` | `docs-only reference` |

---

## 9. Dead / Likely Dead Code

| Code | Location | Reason | Classification |
|---|---|---|---|
| `guardian/server/tools_api.py` | `guardian/server/tools_api.py` | Contains a `ToolSpec` model that duplicates `guardian/tools/spec.py`. Only referenced by `guardian/server/app.py` with a try/except fallback. The `guardian/server/app.py` path is a legacy/alternate entry point not used by the primary `guardian_api.py` bootstrap. | `dead / likely dead` |
| `guardian/server/app.py` tools import | Lines 27, 31, 96 | Alternate app bootstrap that includes a stub `tools_router`. Not the primary entry point. | `dead / likely dead` |
| `router = APIRouter(prefix="/tools")` | `guardian/routes/tools.py` | Router object remains defined for future deletion cleanup, but the primary app no longer mounts it. | `unmounted compatibility object` |
| `_dispatch_tool()` | `guardian/routes/tools.py` line 131 | Called only by `_execute_persisted_compat_tool()` which requires `_configured_tool_jobs_db` to be set (never in production). | `dead / likely dead` in production |
| `_execute_persisted_compat_tool()` | `guardian/routes/tools.py` line 862 | Only called from `api_tools_execute()` when `_uses_persisted_compat_seam()` returns true, which requires `_configured_tool_jobs_db` to be set. | `dead / likely dead` in production |
| `_persist_tool_job()` / `_load_persisted_tool_job()` | `guardian/routes/tools.py` lines 810, 839 | Require `_configured_tool_jobs_db` — only set in tests via `configure_db()`. | `dead / likely dead` in production |

---

## 10. Dependency Class Summary

| Class | Count | Details |
|---|---|---|
| `active dependency` | 14+ | Route registrations, frontend callers (`GuardianChat.tsx`, `useTriggerAction.ts`), test suite (5 test files), `guardian/tools/` submodule imports, command-bus cross-references, in-memory `JOBS` dict |
| `compatibility surface` | 3 | Quarantine/health test checks that verify the shim routes are or are not mounted |
| `dead / likely dead` | 5 | `guardian/server/tools_api.py`, alternate `server/app.py` path, `_dispatch_tool()`, `_execute_persisted_compat_tool()`, `_persist_tool_job()`/`_load_persisted_tool_job()` |
| `docs-only reference` | 6 | Architecture docs that describe the shim |
| `unclear requires manual verification` | 3 | `guardian/tools/overrides.py`, `guardian/tools/state_inspector.py`, `guardian/tools/context/` — exist in directory but not imported by `tools.py` |

---

## 11. Removal Recommendation

### Can the shim likely be removed now?

**No.** The shim is still retained by the `/api/tools` compatibility path and its backend tests:

1. **Frontend migration:** already completed for `GuardianChat.tsx` and `useTriggerAction.ts`; both now use the command-bus invoke surface.
2. **Test suite:** 5 test files still directly import and exercise the retained `/api/tools` shim routes.

### What must migrate first?

1. **Profile switching in `GuardianChat.tsx`** (line 2025):
   - Already completed in the frontend. Keep the command-bus route and tests as the supported profile-switch path.

2. **Trigger action in `useTriggerAction.ts`** (lines 5, 9):
   - Already migrated to the command bus invoke surface. The remaining local `Tools.job()` polling/cache behavior is a frontend implementation detail, not a `/tools` dependency.
   - If the polling path is later replaced by a command-bus-native job/status API, deprecate the `dcw-services/gc.ts` `Tools` namespace.

3. **Test suite** (5 files):
   - `tests/routes/test_tools.py`
   - `tests/routes/test_tools_manifest_phase21_format.py`
   - `tests/routes/test_tools_phase2_spec_policy.py`
   - `tests/routes/test_tools_phase3_callable_contract.py`
   - `tests/routes/test_tools_legacy_shims_phase15.py`
   - These should be migrated to test the command bus endpoints directly (`/api/guardian/commands/*`) or deleted if they only test shim-specific behavior that no longer applies.

4. **`guardian/tools/` submodule audit**:
   - `approval_tokens.py`, `coercion.py`, `derive.py`, `policy.py`, `spec.py` are all actively imported by the shim.
   - Determine which of these should move under `guardian/command_bus/` (since they are command-bus concerns) and which can be deleted.
   - `registry.py`, `overrides.py`, `state_inspector.py`, `context/` need manual verification for liveness.

5. **`tool_jobs` table**:
   - Decide whether to keep the table (it is a valid durable job store) or migrate its purpose entirely to `command_runs`/`command_run_events`.
   - If kept, remove the shim's references but preserve the model for any future consumer.
   - If dropped, a migration is required.

### Minimum safe deletion sequence

1. **Migrate or delete test files** — convert the 5 test files to command-bus tests or delete them.
2. **Remove route registrations** — delete the `_include_router()` call for `api_tools_router` in `guardian/guardian_api.py`.
3. **Delete `guardian/routes/tools.py`** — the shim file itself.
4. **Audit and consolidate `guardian/tools/`** — move live utilities (`derive.py`, `spec.py`, `coercion.py`, `policy.py`, `approval_tokens.py`) under `guardian/command_bus/` or another appropriate home. Delete unused modules.
5. **Decide on `tool_jobs` table** — keep or drop with a migration.
6. **Delete `guardian/server/tools_api.py`** and clean up `guardian/server/app.py` tools references (dead code).
7. **Update architecture docs** — remove shim references from `modules-and-ownership.md`, `flows.md`, `data-and-storage.md`, `system-overview.md`, `tech-debt-and-risks.md`, `README.md`.

---

## Appendix: Exact Grep Hit Summary by Dependency Class

### Direct route exposure (1 mounted router, 1 unmounted router object, 4 mounted endpoints)
- `guardian/routes/tools.py:120` — `router = APIRouter(prefix="/tools")`
- `guardian/routes/tools.py:121` — `api_router = APIRouter(prefix="/api/tools")`
- `guardian/guardian_api.py:1112-1119` — only `api_tools_router` included

### Direct imports (7 files)
- `guardian/guardian_api.py:532-533`
- `tests/routes/test_tools.py:15`
- `tests/routes/test_tools_manifest_phase21_format.py:8`
- `tests/routes/test_tools_phase2_spec_policy.py:8`
- `tests/routes/test_tools_phase3_callable_contract.py:9`
- `tests/routes/test_tools_legacy_shims_phase15.py:8`

### Frontend callers (2 active surfaces)
- `frontend/src/features/chat/GuardianChat.tsx:2025` — `api.post("/tools/execute", ...)`
- `frontend/src/dcw-services/gc.ts:51` — `req('/tools/execute', ...)`
- `frontend/src/hooks/useTriggerAction.ts:5,9` — `Tools.execute()`, `Tools.job()`

### Storage dependencies
- `guardian/db/models.py:941-969` — `ToolJob` model (`tool_jobs` table)
- `guardian/db/models.py:2931+` — `CommandRun` model (`command_runs` table)
- `guardian/db/models.py:2982+` — `CommandRunEvent` model (`command_run_events` table)
- `guardian/db/migrations/versions/9b3d2d08f7c1_add_tool_jobs_table.py` — `tool_jobs` migration

### In-memory state
- `guardian/routes/tools.py:64` — `JOBS: dict[str, dict[str, Any]] = {}`
- `guardian/routes/tools.py:65` — `_configured_tool_jobs_db: Any | None = None`

### Command-bus cross-references
- `guardian/routes/tools.py:25-31` — imports from `guardian.command_bus.*`
- `guardian/routes/tools.py:1057,1251` — lazy import of `command_bus_routes`
- `guardian/routes/tools.py:1064,1258` — uses `command_bus_routes._store`

### `guardian/tools/` submodule
- `guardian/tools/spec.py` — Pydantic models for tool lane
- `guardian/tools/derive.py` — derives tools from command manifest
- `guardian/tools/policy.py` — tool policy evaluation
- `guardian/tools/coercion.py` — argument coercion
- `guardian/tools/approval_tokens.py` — approval token helpers
- `guardian/tools/registry.py` — tool registry (not imported by shim)
- `guardian/tools/overrides.py` — overrides (not imported by shim)
- `guardian/tools/state_inspector.py` — state inspector (not imported by shim)
- `guardian/tools/context/` — context directory (not imported by shim)
