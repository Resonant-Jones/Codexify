# Legacy Tools Shim Dependency Inventory

**Date:** 2026-04-16
**Scope:** Repo-wide inventory of every dependency edge tied to the removed legacy `/api/tools` compatibility shim. The bare `/tools` mount has been removed from the primary app, and the shim route code was deleted in the final excision pass.
**Status:** Runtime shim and live `ToolJob` ORM surface were removed in this task. The tables below are retained as historical removal evidence only; upgraded databases may still carry the historical `tool_jobs` table until a separate schema-drop migration is chosen.
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
| `router` | `/tools` | Removed from the primary app during the 2026-04-18 reduction pass | historical |
| `api_router` | `/api/tools` | Removed from the primary app during the final excision pass | historical |

**Registration in `guardian/guardian_api.py`:**
- Line 532: `from guardian.routes.tools import api_router as api_tools_router`
- Lines 1112-1119: Only `api_tools_router` is included via `_include_router()` with label `api_tools`

**Registration in `guardian/server/app.py` (legacy/alternate entry):**
- Line 27: `from guardian.server.tools_api import router as tools_router`
- Line 31: Fallback `tools_router = APIRouter()` if import fails
- Line 96: `app.include_router(tools_router)`

**Classification:** `removed` — the runtime shim is no longer mounted in the primary `guardian_api.py` entry point.

---

## 2. Direct Imports of `guardian/routes/tools.py`

| File | Line | Import | Classification |
|---|---|---|---|
| `guardian/guardian_api.py` | 532 | `from guardian.routes.tools import api_router as api_tools_router` | `historical; import removed in this task` |
| `tests/routes/test_tools.py` | 15 | `from guardian.routes import tools` | `deleted in this task` |
| `tests/routes/test_tools_manifest_phase21_format.py` | 8 | `from guardian.routes import command_bus, tools` | `deleted in this task` |
| `tests/routes/test_tools_phase2_spec_policy.py` | 8 | `from guardian.routes import command_bus, tools` | `deleted in this task` |
| `tests/routes/test_tools_phase3_callable_contract.py` | 9 | `from guardian.routes import command_bus, tools` | `deleted in this task` |
| `tests/routes/test_tools_legacy_shims_phase15.py` | 8 | `from guardian.routes import command_bus, tools` | `deleted in this task` |

---

## 3. Frontend Callers of `/api/tools` or `/tools`

**Update 2026-04-21:** The last frontend compatibility adapter that still translated trigger actions through the legacy `/tools` execution shape was removed. The remaining frontend caller documented below now targets the command-bus invoke surface directly, so this inventory reflects a fully migrated frontend dependency picture.

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

### 3.2 `frontend/src/dcw-services/gc.ts`

- **What it does now:** Keeps the generic GC request helpers and unrelated API wrappers, but no longer exports a `Tools` adapter or any legacy job-polling translation layer.
- **Consumers:**
  - `frontend/src/main.tsx` (line 7): `import { configureGC } from "./dcw-services/gc"` — configures the GC service layer.
  - `frontend/src/hooks/useSaveRitual.ts` (line 1): imports `Notes, Agent` from gc.
- **Classification:** `cleaned` — the trigger-action compatibility seam has been removed from the frontend.

---

## 4. Tests Covering Legacy Tool Routes

| Test File | Routes Tested | Classification |
|---|---|---|
| `tests/routes/test_tools.py` | `/api/tools/execute`, `/api/tools/jobs/{job_id}` | `deleted in this task` |
| `tests/routes/test_tools_manifest_phase21_format.py` | `/api/tools/manifest` | `deleted in this task` |
| `tests/routes/test_tools_phase2_spec_policy.py` | `/api/tools/manifest`, `/api/tools/execute?legacy=1` | `deleted in this task` |
| `tests/routes/test_tools_phase3_callable_contract.py` | `/api/tools/execute`, `/api/tools/approve`, `/api/tools/manifest`, `/api/tools/execute?legacy=1`, `/api/tools/approve?legacy=1` | `deleted in this task` |
| `tests/routes/test_tools_legacy_shims_phase15.py` | `/api/tools/manifest`, `/api/tools/execute?legacy=1`, `/api/tools/approve?legacy=1` | `deleted in this task` |
| `tests/core/test_beta_router_quarantine.py` | `/api/tools/manifest` (quarantine check) | `retained; proves removal on quarantined profile` |
| `tests/core/test_supported_profile_quarantine.py` | `/api/tools/manifest`, `/tools/manifest` (quarantine check) | `retained; proves removal on supported profile` |
| `tests/routes/test_retrieve_health_or_mount.py` | `/api/tools/manifest` (health/mount check) | `retained; proves shim remains absent where expected` |

---

## 5. Storage / Model Dependencies

### 5.1 `tool_jobs` historical migration artifact

**Live model:** removed from `guardian/db/models.py` in this task

**Migration:** `guardian/db/migrations/versions/9b3d2d08f7c1_add_tool_jobs_table.py`

**Historical usage:** lived only in deleted `guardian/routes/tools.py` during the legacy shim era.

**Classification:** `historical migration truth` — the ORM model is gone, but upgraded databases may still retain the old table until a dedicated drop migration is applied.

### 5.2 In-memory `JOBS` dict

**Historical location:** `guardian/routes/tools.py` line 64

```python
JOBS: dict[str, dict[str, Any]] = {}
```

**Historical role:** legacy process-local job snapshots for the removed shim.

**Classification:** `historical removal evidence` — the registry lived only in the deleted shim file and no longer exists in runtime code.

### 5.3 `command_runs` and `command_run_events` tables

**Models:** `guardian/db/models.py` lines 2931+ (`CommandRun`), 2982+ (`CommandRunEvent`)

**Migrations:**
- `guardian/db/migrations/versions/e0f1a2b3c4d5_add_command_bus_phase1_tables.py`
- `guardian/db/migrations/versions/c2f4a8e1b9d0_add_command_run_idempotency_unique_constraint.py`

**Usage:** The shim calls `execute_invoke()` from `guardian/command_bus/invoke.py` which persists runs through `CommandBusStore` into `command_runs` / `command_run_events`. The shim does **not** directly query these tables — it delegates to the command bus store.

**Classification:** `active dependency` (indirect) — the shim is a consumer of the command bus execution lane, not an owner of these tables.

---

## 6. `guardian/tools/` Submodule Dependencies

The deleted shim historically imported from several modules under `guardian/tools/`:

| Module | Imported by `tools.py` | Purpose | Classification |
|---|---|---|---|
| `guardian/tools/approval_tokens.py` | Lines 34-41 | Approval token issuance/verification for the confirm flow | `historical removal evidence` |
| `guardian/tools/coercion.py` | Lines 42-45 | Argument coercion for tool calls | `historical removal evidence` |
| `guardian/tools/derive.py` | Line 46 | Derives `ToolSpec` list from command-bus manifest | `historical removal evidence` |
| `guardian/tools/policy.py` | Lines 47-51 | Tool policy evaluation and mode application | `historical removal evidence` |
| `guardian/tools/spec.py` | Lines 52-59 | Pydantic models: `ToolCallRequest`, `ToolCallResponse`, `ToolManifestEnvelope`, `ToolSpec`, etc. | `historical removal evidence` |

Additionally:
- `guardian/tools/registry.py` imports from `derive.py`, `overrides.py`, and `spec.py` — builds a `ToolRegistry` from the command manifest. Not directly imported by the deleted `tools.py` file but part of the same historical tool-lane ecosystem.
- `guardian/tools/overrides.py`, `guardian/tools/state_inspector.py`, `guardian/tools/context/` — exist in the directory but were not imported by the deleted shim. They remain outside this cleanup task.

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
| `router = APIRouter(prefix="/tools")` | `guardian/routes/tools.py` | Historical route object in the deleted shim file. | `historical` |
| `_dispatch_tool()` | `guardian/routes/tools.py` line 131 | Called only by `_execute_persisted_compat_tool()` which requires `_configured_tool_jobs_db` to be set (never in production). | `dead / likely dead` in production |
| `_execute_persisted_compat_tool()` | `guardian/routes/tools.py` line 862 | Only called from `api_tools_execute()` when `_uses_persisted_compat_seam()` returns true, which requires `_configured_tool_jobs_db` to be set. | `dead / likely dead` in production |
| `_persist_tool_job()` / `_load_persisted_tool_job()` | `guardian/routes/tools.py` lines 810, 839 | Require `_configured_tool_jobs_db` — only set in tests via `configure_db()`. | `dead / likely dead` in production |

---

## 10. Dependency Class Summary

| Class | Count | Details |
|---|---|---|
| `active dependency` | 0 | No supported runtime or test path still depends on the removed shim surface |
| `compatibility surface` | 0 | Runtime shim removed; only historical docs and migration files remain |
| `historical migration truth` | 1 | `tool_jobs` migration remains as upgrade history after the model removal |
| `docs-only reference` | 6 | Historical architecture docs that describe the removed shim |
| `unclear requires manual verification` | 0 | The live shim file and ORM model were removed, so no live surface remains to verify |

---

## 11. Removal Recommendation

### Can the shim likely be removed now?

**Yes.** The runtime shim and live `ToolJob` model are gone. No supported path still depends on `/api/tools` or the old `tool_jobs` ORM surface.

1. **Frontend migration:** already completed for `GuardianChat.tsx` and `useTriggerAction.ts`; both now use the command-bus invoke surface.
2. **Test suite:** the legacy shim tests were deleted in this task; canonical command-bus tests now carry the proof surface.

### What must migrate first?

1. **Profile switching in `GuardianChat.tsx`** (line 2025):
   - Already completed in the frontend. Keep the command-bus route and tests as the supported profile-switch path.

2. **Trigger action in `useTriggerAction.ts`** (lines 5, 9):
   - Already migrated to the command bus invoke surface. The remaining local `Tools.job()` polling/cache behavior is a frontend implementation detail, not a `/tools` dependency.
   - If the polling path is later replaced by a command-bus-native job/status API, deprecate the `dcw-services/gc.ts` `Tools` namespace.

3. **Test suite**:
   - Canonical command-bus tests now cover the supported surface.
   - The legacy shim route tests were deleted in this task.

4. **`guardian/tools/` submodule audit**:
   - Any remaining live consumers should be checked independently now that the shim is gone.
   - `registry.py`, `overrides.py`, `state_inspector.py`, `context/` still need manual verification for liveness.

5. **`tool_jobs` table**:
   - The ORM model is gone.
   - The historical migration remains for upgrade history.
   - If the physical table should be dropped from live databases, do that in a dedicated schema-drop migration after confirming the rollback story you want to preserve.

### Minimum safe deletion sequence

1. **Delete legacy shim tests** — completed in this task.
2. **Remove route registrations** — completed in this task.
3. **Delete `guardian/routes/tools.py`** — completed in this task.
4. **Audit and consolidate `guardian/tools/`** — move or delete any remaining live utilities if separate consumers still need them.
5. **Decide on `tool_jobs` table drop** — the runtime model is gone; any physical table removal should happen in a dedicated schema migration if desired.
6. **Delete `guardian/server/tools_api.py`** and clean up `guardian/server/app.py` tools references if/when that legacy entry point becomes part of the supported path review.
7. **Update architecture docs** — keep historical removal records accurate and remove any stale runtime claims.

---

## Appendix: Exact Grep Hit Summary by Dependency Class

### Direct route exposure (historical)
- `guardian/routes/tools.py:120` — `router = APIRouter(prefix="/tools")`
- `guardian/routes/tools.py:121` — `api_router = APIRouter(prefix="/api/tools")`
- `guardian/guardian_api.py:1112-1119` — historical include block removed

### Direct imports (7 files)
- `guardian/guardian_api.py:532-533`
- `tests/routes/test_tools.py:15` (deleted)
- `tests/routes/test_tools_manifest_phase21_format.py:8` (deleted)
- `tests/routes/test_tools_phase2_spec_policy.py:8` (deleted)
- `tests/routes/test_tools_phase3_callable_contract.py:9` (deleted)
- `tests/routes/test_tools_legacy_shims_phase15.py:8` (deleted)

### Frontend callers (1 active surface, 1 removed adapter)
- `frontend/src/features/chat/GuardianChat.tsx:2025` — `api.post("/tools/execute", ...)`
- `frontend/src/dcw-services/gc.ts` — removed `Tools.execute()` / `Tools.job()` adapter
- `frontend/src/hooks/useTriggerAction.ts` — removed along with the adapter

### Storage dependencies
- `guardian/db/models.py` — `ToolJob` model removed in this task
- `guardian/db/models.py:2931+` — `CommandRun` model (`command_runs` table)
- `guardian/db/models.py:2982+` — `CommandRunEvent` model (`command_run_events` table)
- `guardian/db/migrations/versions/9b3d2d08f7c1_add_tool_jobs_table.py` — `tool_jobs` migration

### In-memory state
- `guardian/routes/tools.py` — deleted in this task

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
