from pathlib import Path


def test_compiled_backend_docker_target_and_overlay_exist() -> None:
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
        "pyinstaller /src/packaging/pyinstaller/codexify_backend.spec"
        in dockerfile
    )
    assert "ENTRYPOINT [\"/app/runtime/codexify-backend\"]" in dockerfile
    assert "image: codexify-runtime-compiled:local" in overlay
    assert "command: []" in overlay
