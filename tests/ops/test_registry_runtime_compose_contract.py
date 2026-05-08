from pathlib import Path


def test_packaged_registry_compose_contract_exists_and_avoids_bind_mounts() -> None:
    compose_path = Path(__file__).resolve().parents[2] / "docker-compose.runtime.yml"
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
    assert "build:" not in text
    assert "\n      - ./" not in text
    assert "frontend:" not in text
    assert "image: ${CODEXIFY_IMAGE_REGISTRY:-ghcr.io/resonant-jones}/codexify-runtime:${CODEXIFY_IMAGE_TAG:-local-beta}" in text
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

    for marker in required_services:
        assert marker in text
