from __future__ import annotations

from pathlib import Path

import yaml


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _read_text(relative_path: str) -> str:
    return (_repo_root() / relative_path).read_text(encoding="utf-8")


def _read_yaml(relative_path: str) -> dict[str, object]:
    return yaml.safe_load(_read_text(relative_path))


def test_compiled_runtime_contract_files_exist() -> None:
    dockerfile = _read_text("backend/Dockerfile")
    runtime_compose = _read_yaml("docker-compose.runtime.yml")
    compiled_compose = _read_yaml("docker-compose.compiled.yml")
    verifier = _read_text("scripts/verification/check_compiled_runtime_image.sh")

    assert "FROM builder AS compiled-builder" in dockerfile
    assert "FROM dhi.io/python:3.11.14-debian13-dev AS compiled-runtime" in dockerfile
    assert "pyinstaller /src/packaging/pyinstaller/codexify_runtime.spec" in dockerfile
    assert "COPY backend/alembic.ini /app/runtime/alembic.ini" in dockerfile
    assert "COPY guardian/db/migrations /app/runtime/migrations" in dockerfile
    assert "ENTRYPOINT [\"/app/runtime/codexify-runtime\"]" in dockerfile

    runtime_services = runtime_compose["services"]
    assert isinstance(runtime_services, dict)
    assert "frontend" not in runtime_services

    runtime_image = (
        "${CODEXIFY_RUNTIME_IMAGE:-${CODEXIFY_IMAGE_REGISTRY:-ghcr.io/"
        "resonant-jones}/codexify-runtime:${CODEXIFY_IMAGE_TAG:-local-beta}}"
    )
    expected_roles = {
        "migrator": "migrator",
        "model-prep": "model-prep",
        "backend": "backend",
        "worker-warmup": "worker-warmup",
        "worker-chat": "worker-chat",
        "worker-document-embed": "worker-document-embed",
        "worker-chat-embed": "worker-chat-embed",
    }
    for service_name, expected_command in expected_roles.items():
        service = runtime_services[service_name]
        assert service["image"] == runtime_image
        assert service["entrypoint"] == ["/app/runtime/codexify-runtime"]
        assert service["command"] == [expected_command]
        for volume in service.get("volumes", []) or []:
            if isinstance(volume, str) and ":" in volume:
                source = volume.split(":", 1)[0]
                assert not source.startswith((".", "/"))

    compiled_services = compiled_compose["services"]
    assert isinstance(compiled_services, dict)
    for service_name, expected_command in expected_roles.items():
        service = compiled_services[service_name]
        assert service["image"] == "codexify-runtime-compiled:local"
        assert service["entrypoint"] == ["/app/runtime/codexify-runtime"]
        assert service["command"] == [expected_command]

    assert "test -x /app/runtime/codexify-runtime" in verifier
    assert "test -L /app/runtime/codexify-backend" in verifier
    assert "test -d /app/runtime/_internal" in verifier
    assert "test -f /app/runtime/alembic.ini" in verifier
    assert "test -d /app/runtime/migrations" in verifier
    assert "test ! -d /app/backend" in verifier
    assert "test ! -d /app/tests" in verifier
    assert "test ! -d /app/guardian" in verifier
