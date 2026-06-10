"""Tests for Whoosh'd local model profile manifests."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
PROFILE_DIR = ROOT / "config" / "whooshd" / "model-profiles"
PROFILE_PATH = PROFILE_DIR / "gemma-4-e2b-it-4bit.json"
E4B_PROFILE_PATH = PROFILE_DIR / "gemma-4-e4b-it-4bit.json"
OPTIQ_PROFILE_PATH = PROFILE_DIR / "gemma-4-12b-it-optiq-4bit.json"
QAT_PROFILE_PATH = PROFILE_DIR / "gemma-4-12b-it-qat-4bit.json"
VALIDATOR_PATH = ROOT / "scripts" / "validate_whooshd_model_profiles.py"


def _load_profile() -> dict:
    return json.loads(PROFILE_PATH.read_text(encoding="utf-8"))


def _load_e4b_profile() -> dict:
    return json.loads(E4B_PROFILE_PATH.read_text(encoding="utf-8"))


def _load_optiq_profile() -> dict:
    return json.loads(OPTIQ_PROFILE_PATH.read_text(encoding="utf-8"))


def _load_qat_profile() -> dict:
    return json.loads(QAT_PROFILE_PATH.read_text(encoding="utf-8"))


def test_validator_passes_for_committed_profiles() -> None:
    result = subprocess.run(
        [sys.executable, str(VALIDATOR_PATH)],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
    assert "Validated 4 Whoosh'd model profile(s)." in result.stdout


def test_gemma_4_e2b_profile_preserves_local_provider_boundary() -> None:
    profile = _load_profile()

    assert profile["id"] == "gemma-4-e2b-it-4bit"
    assert profile["provider_id"] == "local"
    assert profile["runtime"]["server"] == "mlx_vlm.server"
    assert profile["model"]["repo"] == "mlx-community/gemma-4-e2b-it-4bit"
    assert profile["guardian_defaults"]["requires_final_answer_extraction"] is True
    assert profile["guardian_defaults"]["reject_thought_channel_leaks"] is True
    assert profile["release_posture"]["release_supported"] is False


def test_gemma_4_e4b_profile_preserves_local_provider_boundary() -> None:
    profile = _load_e4b_profile()

    assert profile["id"] == "gemma-4-e4b-it-4bit"
    assert profile["provider_id"] == "local"
    assert profile["runtime"]["server"] == "mlx_vlm.server"
    assert profile["model"]["repo"] == "mlx-community/gemma-4-e4b-it-4bit"
    assert profile["capabilities"]["vision"] is True
    assert profile["weights"]["storage_root"].startswith("/Volumes/Dev_SSD/")
    assert profile["guardian_defaults"]["requires_final_answer_extraction"] is True
    assert profile["guardian_defaults"]["reject_thought_channel_leaks"] is True
    assert profile["release_posture"]["release_supported"] is False


def test_gemma_4_12b_optiq_profile_preserves_local_provider_boundary() -> None:
    profile = _load_optiq_profile()

    assert profile["id"] == "gemma-4-12b-it-optiq-4bit"
    assert profile["provider_id"] == "local"
    assert profile["runtime"]["server"] == "mlx_vlm.server"
    assert profile["model"]["repo"] == (
        "mlx-community/gemma-4-12B-it-OptiQ-4bit"
    )
    assert profile["capabilities"]["vision"] is False
    assert profile["weights"]["storage_root"].startswith("/Volumes/Dev_SSD/")
    assert profile["guardian_defaults"]["requires_final_answer_extraction"] is True
    assert profile["guardian_defaults"]["reject_thought_channel_leaks"] is True
    assert profile["release_posture"]["release_supported"] is False


def test_gemma_4_12b_qat_profile_preserves_local_provider_boundary() -> None:
    profile = _load_qat_profile()

    assert profile["id"] == "gemma-4-12b-it-qat-4bit"
    assert profile["provider_id"] == "local"
    assert profile["runtime"]["server"] == "mlx_vlm.server"
    assert profile["model"]["repo"] == (
        "mlx-community/gemma-4-12B-it-qat-4bit"
    )
    assert profile["capabilities"]["vision"] is True
    assert profile["weights"]["storage_root"].startswith("/Volumes/Dev_SSD/")
    assert profile["guardian_defaults"]["requires_final_answer_extraction"] is True
    assert profile["guardian_defaults"]["reject_thought_channel_leaks"] is True
    assert profile["release_posture"]["release_supported"] is False
