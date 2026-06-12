"""Tests for Whoosh'd local model profile manifests."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from scripts.validate_whooshd_model_profiles import validate_profiles

ROOT = Path(__file__).resolve().parents[2]
PROFILE_DIR = ROOT / "config" / "whooshd" / "model-profiles"
GEMMA_E2B_PROFILE_PATH = PROFILE_DIR / "gemma-4-e2b-it-4bit.json"
GEMMA_12B_QAT_PROFILE_PATH = PROFILE_DIR / "gemma-4-12b-it-qat-4bit.json"
VALIDATOR = ROOT / "scripts" / "validate_whooshd_model_profiles.py"


def _load_profile(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_validator_passes_for_committed_profiles() -> None:
    result = subprocess.run(
        [sys.executable, str(VALIDATOR)],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
    assert "Validated 2 Whoosh'd model profile(s)." in result.stdout


def test_gemma_4_e2b_profile_keeps_local_candidate_posture() -> None:
    profile = _load_profile(GEMMA_E2B_PROFILE_PATH)

    assert profile["id"] == "gemma-4-e2b-it-4bit"
    assert profile["provider_id"] == "local"
    assert profile["runtime"]["server"] == "mlx_vlm.server"
    assert profile["runtime"]["preferred_local_invocation_path"] == "mlx-vlm"
    assert profile["runtime"]["mlx_vlm_compatible"] is True
    assert profile["runtime"]["offline_probe_command"] == [
        "python",
        "-m",
        "mlx_vlm.generate",
        "--model",
        "mlx-community/gemma-4-e2b-it-4bit",
        "--max-tokens",
        "100",
        "--temperature",
        "0.0",
        "--prompt",
        "Describe this image.",
        "--image",
        "<path_to_image>",
    ]
    assert profile["model"]["repo"] == "mlx-community/gemma-4-e2b-it-4bit"
    assert profile["capabilities"]["multimodal"] is True
    assert profile["capabilities"]["image_input"] is True
    assert profile["guardian_defaults"]["requires_final_answer_extraction"] is True
    assert profile["guardian_defaults"]["reject_thought_channel_leaks"] is True
    assert profile["release_posture"]["release_supported"] is False


def test_gemma_4_12b_qat_profile_keeps_offline_candidate_posture() -> None:
    profile = _load_profile(GEMMA_12B_QAT_PROFILE_PATH)

    assert profile["id"] == "gemma-4-12b-it-qat-4bit"
    assert profile["provider_id"] == "local"
    assert profile["runtime"]["server"] == "mlx_vlm.server"
    assert profile["runtime"]["preferred_local_invocation_path"] == "mlx-vlm"
    assert profile["runtime"]["mlx_vlm_compatible"] is True
    assert profile["runtime"]["offline_probe_command"] == [
        "python",
        "-m",
        "mlx_vlm.generate",
        "--model",
        "mlx-community/gemma-4-12B-it-qat-4bit",
        "--max-tokens",
        "100",
        "--temperature",
        "0.0",
        "--prompt",
        "Describe this image.",
        "--image",
        "<path_to_image>",
    ]
    assert profile["model"]["repo"] == "mlx-community/gemma-4-12B-it-qat-4bit"
    assert profile["model"]["quantization"] == "qat-4bit"
    assert profile["capabilities"]["multimodal"] is True
    assert profile["capabilities"]["image_input"] is True
    assert profile["guardian_defaults"]["requires_final_answer_extraction"] is True
    assert profile["guardian_defaults"]["reject_thought_channel_leaks"] is True
    assert profile["release_posture"]["release_supported"] is False


def test_validator_fails_closed_on_missing_required_fields(tmp_path: Path) -> None:
    profile_dir = tmp_path / "model-profiles"
    profile_dir.mkdir()
    (profile_dir / "broken.json").write_text(
        json.dumps({"id": "broken"}),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="missing required keys"):
        validate_profiles(profile_dir)


def test_non_gemma_profile_does_not_need_mlx_vlm_hint_fields(tmp_path: Path) -> None:
    profile_dir = tmp_path / "model-profiles"
    profile_dir.mkdir()
    profile = {
        "schema_version": 1,
        "id": "other-local-model",
        "display_name": "Other Local Model",
        "family": "other-family",
        "provider_id": "local",
        "display_vendor": "Whoosh'd",
        "runtime": {
            "kind": "mlx",
            "server": "mlx_vlm.server",
            "openai_compatible": True,
            "default_base_url": "http://host.docker.internal:8000/v1",
            "startup_command": [
                "mlx_vlm.server",
                "--model",
                "local-model",
                "--port",
                "8000",
            ],
        },
        "model": {
            "repo": "mlx-community/local-model",
            "upstream_family": "other-family/model",
            "quantization": "4bit",
            "instruction_tuned": True,
            "effective_size": "small",
        },
        "capabilities": {
            "chat": True,
            "vision": False,
            "audio_input": False,
            "tool_calling": False,
            "coding": "candidate",
            "long_context": "candidate",
        },
        "guardian_defaults": {
            "mode": "chat",
            "thinking_default": False,
            "history_policy": "final_answer_only",
            "requires_final_answer_extraction": True,
            "reject_thought_channel_leaks": True,
            "provider_id_must_remain": "local",
        },
        "acceptance_checks": [
            {
                "id": "no_prompt_echo",
                "kind": "transcript",
                "description": "No prompt echo.",
            },
            {
                "id": "no_thought_channel_leak",
                "kind": "transcript",
                "description": "No hidden channel leak.",
            },
            {
                "id": "guardian_completion_smoke",
                "kind": "codexify",
                "description": "Guardian completion smoke.",
            },
        ],
        "release_posture": {
            "status": "candidate",
            "release_supported": False,
            "proof_required": True,
            "notes": "Metadata only.",
        },
    }
    (profile_dir / "other-local-model.json").write_text(
        json.dumps(profile),
        encoding="utf-8",
    )

    assert validate_profiles(profile_dir) == 1
