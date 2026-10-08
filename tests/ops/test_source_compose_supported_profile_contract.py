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


def test_source_frontend_installs_canonical_workspace_without_rewriting_lockfiles():
    text = COMPOSE_PATH.read_text()
    frontend = _service_block(text, "frontend")
    assert "- .:/app" in frontend
    assert "pnpm install --frozen-lockfile --ignore-scripts" in frontend
    assert "frozen-lockfile=false" not in frontend
    assert "cd /app/frontend/src" in frontend


def test_personal_packaged_webui_uses_canonical_workspace_without_changing_other_profiles():
    root = Path(__file__).resolve().parents[2]
    compose = (root / 'docker-compose.runtime.yml').read_text()
    dockerfile = (root / 'frontend/Dockerfile.webui.workspace').read_text()
    assert 'dockerfile: frontend/Dockerfile.webui.workspace' in compose
    assert 'COPY pnpm-lock.yaml pnpm-workspace.yaml ./' in dockerfile
    assert 'pnpm install --frozen-lockfile --ignore-scripts' in dockerfile
    assert 'RUN pnpm --dir frontend/src exec vite build' in dockerfile
    # Preserve the existing front door behavior, including API/event/media proxying.
    original = (root / 'frontend/Dockerfile.webui').read_text()
    assert dockerfile.split("RUN cat >", 1)[1] == original.split("RUN cat >", 1)[1]
