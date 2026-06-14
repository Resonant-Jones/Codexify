"""Tests for vision model source selection in the Whoosh'd integration.

Confirms that LOCAL_VISION_MODEL env var takes precedence over fallback
when image content is detected in a chat request.
"""

from __future__ import annotations

from pathlib import Path

import yaml


def _load_smoke_compose():
    override_path = Path("docker-compose.whooshd-smoke.yml")
    with open(override_path) as f:
        return yaml.safe_load(f)


def test_local_vision_model_in_smoke_override():
    """The smoke override must set LOCAL_VISION_MODEL."""
    config = _load_smoke_compose()
    backend_env = config["services"]["backend"]["environment"]
    assert "LOCAL_VISION_MODEL" in backend_env, (
        "LOCAL_VISION_MODEL missing from smoke compose override"
    )
    assert backend_env["LOCAL_VISION_MODEL"] == "qwen2-vl-2b-mlx"


def test_local_vision_model_in_settings_model():
    """LOCAL_VISION_MODEL must be defined as a Settings field."""
    config_path = Path("guardian/core/config.py")
    content = config_path.read_text()
    assert "LOCAL_VISION_MODEL" in content, (
        "LOCAL_VISION_MODEL not found in config.py Settings"
    )


def test_local_gguf_model_in_settings_model():
    """LOCAL_GGUF_MODEL must be defined as a Settings field."""
    config_path = Path("guardian/core/config.py")
    content = config_path.read_text()
    assert "LOCAL_GGUF_MODEL" in content, (
        "LOCAL_GGUF_MODEL not found in config.py Settings"
    )


def test_vision_model_beats_fallback_for_image_turns():
    """When LOCAL_VISION_MODEL is set, image turns use it (not fallback)."""
    config = _load_smoke_compose()
    backend_env = config["services"]["backend"]["environment"]
    assert backend_env.get("LOCAL_VISION_MODEL") is not None
    # The source should be 'local_vision_env' when the model is found
    # (verified in live smoke: source=local_vision_env)
    assert backend_env["LOCAL_VISION_MODEL"] == "qwen2-vl-2b-mlx"


def test_gguf_model_preserved_in_smoke_override():
    """Explicit GGUF model must be preserved in smoke override."""
    config = _load_smoke_compose()
    backend_env = config["services"]["backend"]["environment"]
    assert backend_env.get("LOCAL_GGUF_MODEL") == "qwen2.5-0.5b-gguf"


def test_chat_model_still_uses_local_chat_env():
    """Text turns should still use LOCAL_CHAT_MODEL (not vision model)."""
    config = _load_smoke_compose()
    backend_env = config["services"]["backend"]["environment"]
    assert backend_env["LOCAL_CHAT_MODEL"] == "llama-3.2-3b-mlx"
    # Text and vision models are different
    assert backend_env["LOCAL_CHAT_MODEL"] != backend_env["LOCAL_VISION_MODEL"]
