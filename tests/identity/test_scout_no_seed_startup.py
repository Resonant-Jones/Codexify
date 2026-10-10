"""Bounded preview startup skips provisioning while retaining service binding."""

import asyncio
import logging
from collections import Counter
from types import SimpleNamespace

import pytest

SEED_HOOKS = {
    "system_docs",
    "local_user",
    "builtin_help",
    "project",
    "sync_support",
    "providers",
    "import_replay",
}


@pytest.mark.parametrize("enabled", [True, False])
def test_guard_skips_seven_hooks_and_absent_flag_preserves_default(
    monkeypatch, caplog, enabled
):
    caplog.set_level(logging.INFO, logger="guardian.guardian_api")
    monkeypatch.setenv("GUARDIAN_API_KEY", "synthetic-no-seed-fixture")
    if enabled:
        monkeypatch.setenv("CODEXIFY_SKIP_STARTUP_SEEDING", "1")
    else:
        monkeypatch.delenv("CODEXIFY_SKIP_STARTUP_SEEDING", raising=False)
    from guardian import guardian_api as api
    from guardian.runtime.ingest import seed_pipeline

    called = Counter()

    def record(name, value=None):
        def invoke(*args, **kwargs):
            called[name] += 1
            return value

        return invoke

    db = SimpleNamespace(
        ensure_sync_job_support=record("sync_support"),
        sync_inference_provider_rows_from_catalog=record("providers", {}),
    )
    monkeypatch.setattr(api.dependencies, "init_database", record("database", db))
    monkeypatch.setattr(api, "init_services", record("services"))
    monkeypatch.setattr(api, "load_guardian_db_from_env", record("guardian_db", db))
    monkeypatch.setattr(
        api,
        "get_settings",
        lambda: SimpleNamespace(
            GUARDIAN_ENABLE_GRAPH_CONTEXT=False, GUARDIAN_ENABLE_GRAPH_LOGGING=False
        ),
    )
    monkeypatch.setattr(api, "_refresh_supported_profile_state", lambda *_: None)
    monkeypatch.setattr(api, "assert_config_coherence", record("config_validation"))
    monkeypatch.setattr(api, "ensure_system_dirs", record("system_dirs"))
    monkeypatch.setattr(
        api, "get_voice_runtime_config", lambda: SimpleNamespace(routes_enabled=False)
    )
    monkeypatch.setattr(api, "validate_voice_runtime_dependencies", lambda **_: None)
    monkeypatch.setattr(api, "get_vector_store", lambda: None)
    monkeypatch.setattr(
        seed_pipeline, "seed_global_system_docs", record("system_docs", {})
    )
    monkeypatch.setattr(api, "get_or_create_default_user", record("local_user"))
    monkeypatch.setattr(api, "_run_builtin_help_startup_ingest", record("builtin_help"))
    monkeypatch.setattr(api, "ensure_default_project", record("project"))
    monkeypatch.setattr(
        api, "_schedule_chatgpt_import_startup_sweep", record("import_replay")
    )
    monkeypatch.setattr(api.memory, "bind_dependencies", record("memory_binding"))
    route_modules = (
        "cron_routes",
        "account_observability",
        "documents",
        "share",
        "websocket_routes",
        "agent_orchestration",
        "coding_work_orders",
        "command_bus_routes",
        "connections_routes",
        "notion_connection_routes",
        "google_drive_connection_routes",
        "delegations",
        "guardian_delegations",
        "tts_routes",
        "collaboration",
    )
    for name in route_modules:
        monkeypatch.setattr(getattr(api, name), "configure_db", record(name))
    monkeypatch.setattr(api, "ENABLE_OUTBOX", False)
    monkeypatch.setattr(api, "ENABLE_CONNECTOR_WORKER", False)
    monkeypatch.setattr(api, "_CONNECTOR_WORKER_TASK", None)
    monkeypatch.setattr(api, "_CONNECTOR_WORKER_STOP", None)
    monkeypatch.delenv("LOCAL_LLM_MODEL", raising=False)
    monkeypatch.delenv("LOCAL_EMBED_MODEL", raising=False)

    async def run():
        async with api._app_lifespan_body(api.app):
            assert called["database"] == 1
            assert called["guardian_db"] == 1

    asyncio.run(run())
    assert {name: called[name] for name in SEED_HOOKS} == {
        name: 0 if enabled else 1 for name in SEED_HOOKS
    }
    required = {
        "database",
        "services",
        "guardian_db",
        "config_validation",
        "system_dirs",
        "memory_binding",
        *route_modules,
    }
    assert all(called[name] == 1 for name in required)
    assert caplog.text.count("scout_startup_provisioning_disabled") == int(enabled)
