from pathlib import Path
from types import SimpleNamespace

import pytest


def test_compiled_runtime_docker_target_and_overlay_exist() -> None:
    repo_root = Path(__file__).resolve().parents[2]

    dockerfile = (repo_root / "backend" / "Dockerfile").read_text(
        encoding="utf-8"
    )
    overlay = (repo_root / "docker-compose.compiled.yml").read_text(
        encoding="utf-8"
    )

    assert "FROM builder AS compiled-builder" in dockerfile
    assert (
        "FROM dhi.io/python:3.11.14-debian13-dev AS compiled-runtime"
        in dockerfile
    )
    assert (
        "pyinstaller /src/packaging/pyinstaller/codexify_runtime.spec"
        in dockerfile
    )
    assert "COPY backend/alembic.ini /app/runtime/alembic.ini" in dockerfile
    assert "COPY backend/migrations /app/runtime/migrations" in dockerfile
    assert "ENTRYPOINT [\"/app/runtime/codexify-runtime\"]" in dockerfile
    assert "CMD [\"backend\"]" in dockerfile
    assert "image: codexify-runtime-compiled:local" in overlay
    assert 'entrypoint: ["/app/runtime/codexify-runtime"]' in overlay
    assert 'command: ["backend"]' in overlay


def test_compiled_runtime_dispatcher_migrator_role_uses_runtime_migrations(
    tmp_path: Path,
) -> None:
    from backend import compiled_runtime_entry as runtime_entry

    calls: dict[str, object] = {}
    alembic_cfg = tmp_path / "alembic.ini"
    alembic_cfg.write_text("[alembic]\n", encoding="utf-8")

    class DummyConfig:
        def __init__(self, path: str) -> None:
            calls["config_path"] = path

        def set_main_option(self, key: str, value: str) -> None:
            calls[key] = value

    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.setattr(runtime_entry, "Config", DummyConfig)
    monkeypatch.setattr(
        runtime_entry,
        "command",
        SimpleNamespace(
            upgrade=lambda config, target: calls.update(
                upgraded_to=target, upgrade_config=config
            )
        ),
    )
    monkeypatch.setattr(runtime_entry, "_wait_for_db", lambda: "dsn")
    monkeypatch.setattr(runtime_entry, "seed_defaults_main", lambda: 0)
    monkeypatch.setenv("ALEMBIC_CONFIG", str(alembic_cfg))

    try:
        runtime_entry._run_migrator()
    finally:
        monkeypatch.undo()

    assert calls["config_path"] == str(alembic_cfg)
    assert calls["script_location"] == "/app/runtime/migrations"
    assert calls["upgraded_to"] == "heads"
    assert isinstance(calls["upgrade_config"], DummyConfig)


def test_compiled_runtime_dispatcher_backend_preflight_still_blocks_missing_models(
) -> None:
    from backend import compiled_runtime_entry as runtime_entry

    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.setenv("LOCAL_EMBEDDINGS_REQUIRED", "1")
    monkeypatch.setenv("LOCAL_EMBED_MODEL", "/private/tmp/codexify-missing-model")

    backend_called = {"value": False}

    monkeypatch.setattr(
        runtime_entry,
        "backend_main",
        lambda: backend_called.update(value=True),
    )

    try:
        with pytest.raises(SystemExit) as excinfo:
            runtime_entry._run_backend()
    finally:
        monkeypatch.undo()

    assert excinfo.value.code == 1
    assert backend_called["value"] is False
