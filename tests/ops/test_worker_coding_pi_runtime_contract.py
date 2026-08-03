from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
COMPOSE = ROOT / "docker-compose.yml"
DOCKERFILE = ROOT / "backend/Dockerfile"
RUNBOOK = ROOT / "docs/Ops/SOLO_OPERATOR_CODING_WORKER_RUNBOOK.md"
RUNTIME_PACKAGE = ROOT / "codex_runner/pi-runtime/package.json"
RUNTIME_LOCK = ROOT / "codex_runner/pi-runtime/package-lock.json"
VENDORED_PACKAGE = ROOT / "codex_runner/vendor/pi-coding-agent/package.json"


def _service_block(text: str, service: str) -> str:
    marker = f"  {service}:\n"
    start = text.index(marker) + len(marker)
    lines: list[str] = []
    for line in text[start:].splitlines(keepends=True):
        if line.startswith("  ") and not line.startswith("    "):
            break
        lines.append(line)
    return "".join(lines)


def test_worker_coding_uses_dedicated_image_and_narrow_pi_auth_mount() -> None:
    text = COMPOSE.read_text(encoding="utf-8")
    worker = _service_block(text, "worker-coding")

    assert "image: codexify-worker-coding-runtime:latest" in worker
    assert "target: worker-coding-runtime" in worker
    assert "codexify_pi_auth:/home/codexify/.pi" in worker
    assert "codexify_cli_home:/home/codexify" not in worker
    assert "PI_PROVIDER:" in worker
    assert "PI_MODEL:" in worker
    assert "ANTHROPIC_API_KEY:" in worker
    assert "check_worker_coding_readiness.py" in worker


def test_worker_image_installs_exact_declared_pi_runtime_without_credentials() -> None:
    dockerfile = DOCKERFILE.read_text(encoding="utf-8")
    runtime_package = json.loads(RUNTIME_PACKAGE.read_text(encoding="utf-8"))
    runtime_lock = json.loads(RUNTIME_LOCK.read_text(encoding="utf-8"))
    vendored_package = json.loads(VENDORED_PACKAGE.read_text(encoding="utf-8"))

    declared_version = runtime_package["dependencies"]["@mariozechner/pi-coding-agent"]
    assert declared_version == vendored_package["version"] == "0.72.1"
    assert (
        runtime_lock["packages"][""]["dependencies"]["@mariozechner/pi-coding-agent"]
        == "0.72.1"
    )
    assert "FROM node:20.19.5-bookworm-slim AS pi-sdk-runtime" in dockerfile
    assert "npm ci --omit=dev --ignore-scripts --no-audit --no-fund" in dockerfile
    assert "FROM runtime AS worker-coding-runtime" in dockerfile
    assert "ANTHROPIC_API_KEY" not in dockerfile
    assert "auth.json" not in dockerfile


def test_runbook_uses_compose_owned_environment_and_canonical_readiness() -> None:
    runbook = RUNBOOK.read_text(encoding="utf-8")

    assert "source .env" not in runbook
    assert "docker compose config --quiet" in runbook
    assert "docker compose build worker-coding" in runbook
    assert "docker compose up -d worker-coding" in runbook
    assert "check_worker_coding_readiness.py --format human" in runbook
    assert "LOCAL_PROVIDER_DISPLAY_NAME" in runbook
    assert "apostrophe" in runbook.lower()
