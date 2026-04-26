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
    assert "image: ${CODEXIFY_IMAGE_REGISTRY:-ghcr.io/resonant-jones}/codexify-backend:${CODEXIFY_IMAGE_TAG:-local-beta}" in text

    for marker in required_services:
        assert marker in text
