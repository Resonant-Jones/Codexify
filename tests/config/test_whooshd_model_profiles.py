"""Tests for Whoosh'd local model profile metadata."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
PROFILE_PATH = (
    ROOT
    / "config"
    / "whooshd"
    / "model-profiles"
    / "gemma-4-e2b-it-4bit.json"
)
VALIDATOR_PATH = ROOT / "scripts" / "validate_whooshd_model_profiles.py"


def _load_profile() -> dict:
    return json.loads(PROFILE_PATH.read_text(encoding="utf-8"))


def test_validator_passes_for_committed_profiles() -> None:
    result = subprocess.run(
        [sys.executable, str(VALIDATOR_PATH)],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
    assert "Validated 1 Whoosh'd model profile(s)." in result.stdout


def test_gemma_4_e2b_profile_preserves_local_provider_boundary() -> None:
    profile = _load_profile()

    assert profile["id"] == "gemma-4-e2b-it-4bit"
    assert profile["provider_id"] == "local"
    assert profile["runtime"]["server"] == "mlx_vlm.server"
    assert profile["model"]["repo"] == "mlx-community/gemma-4-e2b-it-4bit"
    assert profile["guardian_defaults"]["requires_final_answer_extraction"] is True
    assert profile["guardian_defaults"]["reject_thought_channel_leaks"] is True
    assert profile["release_posture"]["release_supported"] is False
