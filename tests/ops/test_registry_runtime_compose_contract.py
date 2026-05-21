from pathlib import Path


def _service_block(text: str, service: str) -> str:
    marker = f"  {service}:\n"
    start = text.index(marker) + len(marker)
    block_lines: list[str] = []
    for line in text[start:].splitlines(keepends=True):
        if line.startswith("  ") and not line.startswith("    "):
            break
        block_lines.append(line)
    return "".join(block_lines)


def test_packaged_registry_compose_contract_exists_and_avoids_bind_mounts() -> (
    None
):
    compose_path = (
        Path(__file__).resolve().parents[2] / "docker-compose.runtime.yml"
    )
    text = compose_path.read_text(encoding="utf-8")

    required_services = [
        "db:",
        "redis:",
        "neo4j:",
        "graph-init:",
        "migrator:",
        "model-prep:",
        "backend:",
        "worker-chat:",
        "worker-document-embed:",
        "worker-chat-embed:",
        "worker-warmup:",
    ]

    assert compose_path.is_file()
    assert "\n      - ./" not in text
    assert "frontend:" not in text
    assert (
        "image: ${CODEXIFY_IMAGE_REGISTRY:-ghcr.io/resonant-jones}/codexify-runtime:${CODEXIFY_IMAGE_TAG:-local-beta}"
        in text
    )
    assert 'CODEXIFY_CONFIG_SOURCE: "${CODEXIFY_CONFIG_SOURCE:-core}"' in text
    assert "/app/backend/scripts/docker/run_migrator.py" not in text
    assert "/app/backend" not in text
    assert "/app/guardian" not in text
    assert "python -m guardian." not in text
    assert "runpy.run_path" not in text
    assert "codexify-backend" not in text
    assert 'command: ["migrator"]' in text
    assert 'command: ["model-prep"]' in text
    assert 'command: ["backend"]' in text
    assert 'command: ["worker-chat"]' in text
    assert 'command: ["worker-document-embed"]' in text
    assert 'command: ["worker-chat-embed"]' in text
    assert 'command: ["worker-warmup"]' in text

    runtime_services = [
        "migrator",
        "model-prep",
        "backend",
        "worker-chat",
        "worker-document-embed",
        "worker-chat-embed",
        "worker-warmup",
    ]

    for service in runtime_services:
        block = _service_block(text, service)
        assert "build:" not in block

    for marker in required_services:
        assert marker in text


def test_packaged_registry_compose_dispatcher_services_require_runtime_entrypoint(
) -> None:
    compose_path = (
        Path(__file__).resolve().parents[2] / "docker-compose.runtime.yml"
    )
    text = compose_path.read_text(encoding="utf-8")

    dispatcher_services = [
        "migrator",
        "model-prep",
        "backend",
        "worker-chat",
        "worker-document-embed",
        "worker-chat-embed",
        "worker-warmup",
    ]

    for service in dispatcher_services:
        block = _service_block(text, service)
        assert 'entrypoint: ["/app/runtime/codexify-runtime"]' in block

    worker_coding_block = _service_block(text, "worker-coding")
    assert 'entrypoint: ["/app/runtime/codexify-runtime"]' not in worker_coding_block
    assert 'command: ["python", "-m", "guardian.workers.coding_worker"]' in worker_coding_block
