"""Tests for vision model source selection in the Whoosh'd integration.

Checks the static operator-configured vision and GGUF inputs separately
from the supported logical chat route. No live inference is exercised.
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
    assert backend_env["LOCAL_VISION_MODEL"] == "${LOCAL_VISION_MODEL:-}"


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


def test_vision_model_has_no_implicit_physical_model_default():
    """The optional vision input is supplied explicitly by the operator."""
    config = _load_smoke_compose()
    backend_env = config["services"]["backend"]["environment"]
    assert backend_env.get("LOCAL_VISION_MODEL") is not None
    assert backend_env["LOCAL_VISION_MODEL"] == "${LOCAL_VISION_MODEL:-}"


def test_gguf_model_preserved_in_smoke_override():
    """Explicit GGUF model must be preserved in smoke override."""
    config = _load_smoke_compose()
    backend_env = config["services"]["backend"]["environment"]
    assert backend_env.get("LOCAL_GGUF_MODEL") == "${LOCAL_GGUF_MODEL:-}"


def test_chat_model_uses_supported_logical_route():
    """The supported chat path requests Whoosh'd's stable logical route."""
    config = _load_smoke_compose()
    backend_env = config["services"]["backend"]["environment"]
    assert backend_env["LOCAL_CHAT_MODEL"] == "local-chat"
    # Text and vision models are different
    assert backend_env["LOCAL_CHAT_MODEL"] != backend_env["LOCAL_VISION_MODEL"]
