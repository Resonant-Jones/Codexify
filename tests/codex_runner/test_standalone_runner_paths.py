from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


def _load_runner_module():
    runner_path = (
        Path(__file__).resolve().parents[2]
        / "tools"
        / "codex-runner"
        / "src"
        / "codex_runner"
        / "runner.py"
    )
    spec = importlib.util.spec_from_file_location(
        "standalone_codex_runner_runner",
        runner_path,
    )
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load runner module from {runner_path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


runner = _load_runner_module()


def test_validate_campaign_payload_accepts_canonical_paths() -> None:
    payload = {
        "campaign_id": "2026-02-18::security_alpha::001",
        "campaign_slug": "security_alpha",
        "campaign_doc_path": (
            "docs/work/campaigns/2026/02/CAMPAIGN_2026_02_18_SECURITY.md"
        ),
        "campaign_markdown": "# Campaign",
        "tasks": [
            {
                "id": "TASK-001",
                "slug": "alpha",
                "area": "backend",
                "files": ["backend/app.py"],
                "tests": ["pytest -q tests/test_app.py"],
                "commit_message": "TASK-001: implement alpha",
                "task_artifact_path": (
                    "docs/work/tasks/2026/02/TASK_2026_02_18_001_alpha.md"
                ),
                "task_artifact_markdown": "# Task",
                "activation_prompt": "Do task",
            }
        ],
    }

    runner.validate_campaign_payload(payload)


def test_validate_campaign_payload_accepts_legacy_paths() -> None:
    payload = {
        "campaign_id": "2026-02-18::security_alpha::001",
        "campaign_slug": "security_alpha",
        "campaign_doc_path": "docs/Campaign/CAMPAIGN_2026_02_18_SECURITY.md",
        "campaign_markdown": "# Campaign",
        "tasks": [
            {
                "id": "TASK-001",
                "slug": "alpha",
                "area": "backend",
                "files": ["backend/app.py"],
                "tests": ["pytest -q tests/test_app.py"],
                "commit_message": "TASK-001: implement alpha",
                "task_artifact_path": "docs/tasks/TASK_2026_02_18_001_alpha.md",
                "task_artifact_markdown": "# Task",
                "activation_prompt": "Do task",
            }
        ],
    }

    runner.validate_campaign_payload(payload)


def test_ensure_codex_available_explains_install_auth_and_verify(
    monkeypatch,
) -> None:
    monkeypatch.setattr(runner.shutil, "which", lambda binary: None)

    try:
        runner.ensure_codex_available()
    except runner.RunnerError as exc:
        message = str(exc)
    else:
        raise AssertionError("expected RunnerError when codex is missing")

    assert "Codex CLI preflight failed" in message
    assert "curl -fsSL https://chatgpt.com/codex/install.sh | sh" in message
    assert "npm install -g @openai/codex" in message
    assert "brew install --cask codex" in message
    assert "codex login" in message
    assert "codex login --api-key <OPENAI_API_KEY>" in message
    assert "codex login status" in message
    assert 'codex exec "Return only: OK"' in message
