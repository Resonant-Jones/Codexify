# TASK_2026_02_16_06_plugin_loader_consolidation

## Task ID
TASK-2026-02-16-006_plugin_loader_consolidation

## Goal
Consolidate plugin loader logic behind a single hardened entrypoint and route plugin-loading call sites through it.

## Files Touched
- guardian/core/plugins.py
- guardian/system_init.py
- guardian/chat/cli/guardianctl.py
- guardian/graph/capability_index.py
- guardian/routes/devtools.py
- guardian/audio/tts_trigger.py
- tests/core/test_plugins.py

## Tests Run
- `pytest -v tests/core/test_plugins.py`
  - Result: pass (`4 passed`)
- `pytest -v`
  - Result: partial pass with one unrelated, pre-existing failure:
    `tests/integration/test_rag_integration_loop.py::test_rag_integration_memory_loop`
  - Summary: `1 failed, 689 passed, 15 skipped, 33 xfailed, 11 xpassed`

## Notes / Risks
- Added `guardian/core/plugins.py` as the single entrypoint for:
  - Runtime plugin loader access and guarded initialization (`get_runtime_plugin_loader`, `load_runtime_plugins`)
  - Manifest loading with validation/deduplication (`list_plugin_manifests`)
  - Capability/id lookups (`get_plugin_manifest_by_capability`, `get_plugin_manifest_by_id`)
- Routed plugin-loading call sites through the new facade:
  - `guardian/system_init.py` now initializes/checks plugins via `load_runtime_plugins()`
  - `guardian/chat/cli/guardianctl.py` initializes plugins via `load_runtime_plugins()`
  - `guardian/graph/capability_index.py` resolves loader via `get_runtime_plugin_loader()`
  - `guardian/routes/devtools.py` and `guardian/audio/tts_trigger.py` now consume centralized manifest access
- Risk: runtime loader initialization is intentionally idempotent when plugin registry is non-empty; explicit reload behavior remains with existing loader methods.

## Commit A
- `0329032a78b11a09ac35b6aa9035260db0ad72cf`

## Commit B
- `<this-commit>`
