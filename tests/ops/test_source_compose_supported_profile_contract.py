from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
COMPOSE_PATH = ROOT / "docker-compose.yml"


def _service_block(text: str, service: str) -> str:
    marker = f"  {service}:\n"
    start = text.index(marker) + len(marker)
    block_lines: list[str] = []
    for line in text[start:].splitlines(keepends=True):
        if line.startswith("  ") and not line.startswith("    "):
            break
        block_lines.append(line)
    return "".join(block_lines)


def test_source_backend_compose_defaults_supported_profile() -> None:
    text = COMPOSE_PATH.read_text(encoding="utf-8")
    backend_block = _service_block(text, "backend")

    assert COMPOSE_PATH.is_file()
    assert (
        'CODEXIFY_SUPPORTED_PROFILE: "${CODEXIFY_SUPPORTED_PROFILE:-v1-local-core-web-mcp}"'
        in backend_block
    )
    assert 'CODEXIFY_SUPPORTED_PROFILE: "${CODEXIFY_SUPPORTED_PROFILE}"' not in text
