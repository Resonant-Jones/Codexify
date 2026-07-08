from __future__ import annotations

from typing import Any

import pytest
from fastapi import FastAPI

from guardian.codex_runner_bridge import command_bus as bridge_command_bus
from guardian.command_bus import manifest as manifest_module
from guardian.command_bus.contracts import CommandSpec
from guardian.routes import command_bus as command_bus_routes


def _build_app() -> FastAPI:
    command_bus_routes.configure_db(None)
    app = FastAPI()

    @app.get("/health", operation_id="health_check")
    def health() -> dict[str, bool]:
        return {"ok": True}

    @app.post("/write", operation_id="write_item")
    def write(payload: dict[str, Any]) -> dict[str, Any]:
        return {"ok": True, "payload": payload}

    app.include_router(command_bus_routes.router)
    return app


def test_manifest_includes_internal_bridge_commands_and_raw_routes_unchanged() -> None:
    app = _build_app()
    manifest = manifest_module.build_manifest(app)

    internal_commands = [
        command for command in manifest.commands if command.layer == "internal"
    ]
    raw_commands = [command for command in manifest.commands if command.layer == "raw"]

    assert len(internal_commands) == 2
    assert {command.command_id for command in internal_commands} == {
        bridge_command_bus.INTERNAL_VALIDATE_PLAN_PACK_COMMAND_ID,
        bridge_command_bus.INTERNAL_ORCHESTRATE_DRY_RUN_PREFLIGHT_COMMAND_ID,
    }
    for command in internal_commands:
        assert command.risk == "read_only"
        assert command.effect == "read"
        assert command.idempotency == "safe"
        assert command.approval_mode == "none"
        assert command.aliases == []
        assert command.method == "INTERNAL"
        assert command.path_template == ""
        assert command.operation_id is None

    health = next(
        command
        for command in raw_commands
        if command.command_id == "op::health_check"
    )
    assert health.layer == "raw"
    assert health.risk == "read_only"
    assert health.effect == "read"
    assert health.idempotency == "safe"
    assert health.approval_mode == "none"

    raw_ids = {command.command_id for command in raw_commands}
    raw_aliases = {
        alias for command in raw_commands for alias in command.aliases
    }
    internal_ids = {command.command_id for command in internal_commands}
    assert internal_ids.isdisjoint(raw_ids)
    assert internal_ids.isdisjoint(raw_aliases)


def test_build_command_index_includes_internal_bridge_commands() -> None:
    app = _build_app()
    index, manifest = manifest_module.build_command_index(app)

    assert manifest.commands
    assert index[bridge_command_bus.INTERNAL_VALIDATE_PLAN_PACK_COMMAND_ID].layer == "internal"
    assert index[
        bridge_command_bus.INTERNAL_ORCHESTRATE_DRY_RUN_PREFLIGHT_COMMAND_ID
    ].layer == "internal"
    assert index["op::health_check"].layer == "raw"


def test_build_manifest_raises_on_internal_command_collision(monkeypatch) -> None:
    app = _build_app()
    collision = CommandSpec(
        command_id="op::health_check",
        aliases=[],
        layer="internal",
        method="INTERNAL",
        path_template="",
        operation_id=None,
        risk="read_only",
        effect="read",
        idempotency="safe",
        approval_mode="none",
        input_schema={},
    )
    monkeypatch.setattr(
        manifest_module,
        "build_guardian_bridge_command_specs",
        lambda: [collision],
    )

    with pytest.raises(ValueError, match="collision"):
        manifest_module.build_manifest(app)
