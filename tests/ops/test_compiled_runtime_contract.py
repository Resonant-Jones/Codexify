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
    assert "FROM python:3.11.14-slim AS compiled-runtime" in dockerfile
    assert (
        "pyinstaller /src/packaging/pyinstaller/codexify_runtime.spec"
        in dockerfile
    )
    assert "COPY backend/alembic.ini /app/runtime/alembic.ini" in dockerfile
    assert "COPY backend/migrations /app/runtime/migrations" in dockerfile
    assert 'ENTRYPOINT ["/app/runtime/codexify-runtime"]' in dockerfile
    assert 'CMD ["backend"]' in dockerfile
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


def test_compiled_runtime_dispatcher_backend_preflight_still_blocks_missing_models() -> (
    None
):
    from backend import compiled_runtime_entry as runtime_entry

    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.setenv("LOCAL_EMBEDDINGS_REQUIRED", "1")
    monkeypatch.setenv(
        "LOCAL_EMBED_MODEL", "/private/tmp/codexify-missing-model"
    )

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


@pytest.fixture
def image_verifier(tmp_path, monkeypatch):
    import json
    import os
    import subprocess

    image_id = "sha256:" + "a" * 64
    revision = "b" * 40
    calls_path = tmp_path / "docker-calls.jsonl"
    docker = tmp_path / "docker"
    docker.write_text(
        """#!/usr/bin/env python3
import json
import os
import sys
from pathlib import Path
args = sys.argv[1:]
with Path(os.environ['FAKE_DOCKER_CALLS']).open('a') as stream:
    stream.write(json.dumps(args) + '\\n')
if args[:2] == ['image', 'inspect']:
    if args[3] == '{{.Id}}':
        if os.environ.get('FAKE_MISSING_IMAGE') == '1':
            sys.exit(1)
        print(os.environ['FAKE_IMAGE_ID'])
    else:
        print(os.environ['FAKE_REVISION'])
elif args[0] == 'run':
    print('c' * 64 + '  /app/runtime/codexify-runtime')
    sys.exit(int(os.environ.get('FAKE_RUN_EXIT', '0')))
else:
    sys.exit(99)
""",
        encoding="utf-8",
    )
    docker.chmod(0o755)
    monkeypatch.setenv("PATH", str(tmp_path) + os.pathsep + os.environ["PATH"])
    monkeypatch.setenv("FAKE_DOCKER_CALLS", str(calls_path))
    monkeypatch.setenv("FAKE_IMAGE_ID", image_id)
    monkeypatch.setenv("FAKE_REVISION", revision)
    script = Path(__file__).resolve().parents[2] / "scripts/verification/check_compiled_runtime_image.sh"

    def invoke(*args):
        result = subprocess.run(["bash", str(script), *args], text=True, capture_output=True)
        calls = [json.loads(line) for line in calls_path.read_text().splitlines()] if calls_path.exists() else []
        return result, calls

    return invoke, image_id, revision


def test_image_verifier_matches_revision_and_runs_pinned_local_content(image_verifier):
    invoke, image_id, revision = image_verifier
    result, calls = invoke("task-owned:changing-tag", revision)
    assert result.returncode == 0, result.stderr
    assert calls[0][-1] == "task-owned:changing-tag"
    assert calls[1][-1] == image_id
    run = calls[2]
    assert run[:9] == ["run", "--rm", "--pull", "never", "--network", "none", "--read-only", "--entrypoint", "sh"]
    assert run[9] == image_id
    assert "sha256sum /app/runtime/codexify-runtime" in run[-1]
    assert "image_id=" + image_id in result.stdout
    assert "source_revision=" + revision in result.stdout
    assert "behavioral readiness unproven" in result.stdout
    assert not any(call[0] == "pull" for call in calls)


@pytest.mark.parametrize("observed", ["", "d" * 40, "<no value>"])
def test_image_verifier_rejects_mismatched_or_missing_provenance(image_verifier, monkeypatch, observed):
    invoke, _, revision = image_verifier
    monkeypatch.setenv("FAKE_REVISION", observed)
    result, calls = invoke("task-owned:local", revision)
    assert result.returncode == 1
    assert "Source revision mismatch" in result.stderr
    assert not any(call[0] == "run" for call in calls)


@pytest.mark.parametrize("revision", ["", "short", "a" * 39, "g" * 40, "A" * 40])
def test_image_verifier_rejects_invalid_expected_revision_before_docker(image_verifier, revision):
    invoke, _, _ = image_verifier
    result, calls = invoke("task-owned:local", revision)
    assert result.returncode == 2
    assert calls == []


def test_image_verifier_missing_local_image_never_pulls_or_runs(image_verifier, monkeypatch):
    invoke, _, revision = image_verifier
    monkeypatch.setenv("FAKE_MISSING_IMAGE", "1")
    result, calls = invoke("task-owned:missing", revision)
    assert result.returncode != 0
    assert len(calls) == 1
    assert calls[0][:2] == ["image", "inspect"]


def test_image_verifier_structural_only_does_not_claim_attestation(image_verifier):
    invoke, _, _ = image_verifier
    result, _ = invoke("task-owned:local")
    assert result.returncode == 0
    assert "verification=structural-only" in result.stdout
    assert "source attestation and behavioral readiness unproven" in result.stdout


def test_image_verifier_propagates_structural_failure(image_verifier, monkeypatch):
    invoke, _, revision = image_verifier
    monkeypatch.setenv("FAKE_RUN_EXIT", "7")
    result, _ = invoke("task-owned:local", revision)
    assert result.returncode == 7
    assert "verification=" not in result.stdout


@pytest.mark.parametrize("revision, expected_code", [("e" * 40, 0), ("", 1), ("short", 1), ("Z" * 40, 1)])
def test_compiled_build_executes_revision_validation(revision, expected_code):
    import os
    import subprocess
    import sys

    text = (Path(__file__).resolve().parents[2] / "backend/Dockerfile").read_text()
    validation = text.split("RUN python - <<'PY_REVISION'\n", 1)[1].split("\nPY_REVISION", 1)[0]
    result = subprocess.run([sys.executable, "-c", validation], env={**os.environ, "CODEXIFY_SOURCE_REVISION": revision}, capture_output=True, text=True)
    assert result.returncode == expected_code
    if expected_code:
        assert "full lowercase Git commit SHA" in result.stderr
