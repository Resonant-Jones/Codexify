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

    declared_version = runtime_package["dependencies"]["@earendil-works/pi-coding-agent"]
    assert declared_version == vendored_package["version"] == "0.82.1"
    assert (
        runtime_lock["packages"][""]["dependencies"]["@earendil-works/pi-coding-agent"]
        == "0.82.1"
    )
    assert (
        runtime_lock["packages"][""]["dependencies"]["@earendil-works/pi-ai"] == "0.82.1"
    )
    assert "FROM node:22.19.0-bookworm-slim AS pi-sdk-runtime" in dockerfile
    assert "npm ci --omit=dev --ignore-scripts --no-audit --no-fund" in dockerfile
    assert "FROM runtime AS worker-coding-runtime" in dockerfile
    assert "ANTHROPIC_API_KEY" not in dockerfile
    assert "auth.json" not in dockerfile


def test_active_runtime_loader_targets_maintained_pi_ai() -> None:
    """The wrapper loader must import the maintained Pi AI package, not the
    deprecated upstream namespace."""
    loader = (ROOT / "codex_runner/src/agent-wrapper.js").read_text(encoding="utf-8")

    assert "@earendil-works/pi-ai" in loader
    assert "@mariozechner/pi-ai" not in loader


def test_active_runtime_loader_imports_maintained_coding_agent() -> None:
    """The wrapper loader must read coding-agent from the maintained package
    metadata; the deprecated upstream namespace must not appear in active
    loader paths."""
    loader = (ROOT / "codex_runner/src/agent-wrapper.js").read_text(encoding="utf-8")

    assert "@earendil-works" in loader
    assert "@mariozechner" not in loader


def test_runbook_uses_compose_owned_environment_and_canonical_readiness() -> None:
    runbook = RUNBOOK.read_text(encoding="utf-8")

    assert "source .env" not in runbook
    assert "docker compose config --quiet" in runbook
    assert "docker compose build worker-coding" in runbook
    assert "docker compose up -d worker-coding" in runbook
    assert "check_worker_coding_readiness.py --format human" in runbook
    assert "LOCAL_PROVIDER_DISPLAY_NAME" in runbook
    assert "apostrophe" in runbook.lower()


def test_canonical_pi_source_vendor_runtime_bundle_is_complete() -> None:
    """The source-vendored Pi runtime must ship its executable payload so the
    wrapper's source-relative fallback can load it without external SDK
    overrides.

    A metadata-only vendor tree (e.g. only ``package.json``, docs, and
    examples) lets CI pass without actually providing the runtime the
    wrapper imports.  This regression contract fails closed when those
    runtime artifacts are absent.
    """
    coding_agent_dist_index = (
        ROOT / "codex_runner/vendor/pi-coding-agent/dist/index.js"
    )
    nested_pi_ai_dist_index = (
        ROOT
        / "codex_runner/vendor/pi-coding-agent/node_modules/@earendil-works/pi-ai/dist/index.js"
    )
    nested_pi_ai_openai_codex_models = (
        ROOT
        / "codex_runner/vendor/pi-coding-agent/node_modules/@earendil-works/pi-ai/dist/providers/openai-codex.models.js"
    )

    assert coding_agent_dist_index.is_file(), (
        "Canonical source-vendored coding-agent dist/index.js is missing; "
        "the wrapper's source-relative default cannot load the Pi runtime."
    )
    assert nested_pi_ai_dist_index.is_file(), (
        "Canonical source-vendored nested @earendil-works/pi-ai/dist/index.js "
        "is missing; the wrapper's source-relative default cannot load the "
        "maintained Pi AI runtime."
    )
    assert nested_pi_ai_openai_codex_models.is_file(), (
        "Canonical source-vendored nested openai-codex.models.js is missing; "
        "openai-codex provider/model catalog cannot be resolved from the "
        "source-vendor fallback."
    )

    vendored_coding_agent = json.loads(VENDORED_PACKAGE.read_text(encoding="utf-8"))
    assert vendored_coding_agent["name"] == "@earendil-works/pi-coding-agent"
    assert vendored_coding_agent["version"] == "0.82.1"

    nested_pi_ai_pkg = json.loads(
        (ROOT / "codex_runner/vendor/pi-coding-agent/node_modules/@earendil-works/pi-ai/package.json").read_text(
            encoding="utf-8"
        )
    )
    assert nested_pi_ai_pkg["name"] == "@earendil-works/pi-ai"
    assert nested_pi_ai_pkg["version"] == "0.82.1"
