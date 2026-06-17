"""Tests for Codexify → Whoosh'd ThreadWake segment metadata emission."""

from __future__ import annotations

import hashlib
import json

import pytest

from guardian.core.ai_router import (
    _build_threadwake_config,
    _build_threadwake_segments,
)
from guardian.core.config import Settings


# ── helpers ────────────────────────────────────────────────────────────────


def _mock_settings(**overrides) -> Settings:
    defaults = {
        "LLM_MODEL": "mlx-community/Llama-3.2-3B-Instruct-4bit",
        "CODEXIFY_WHOOSHD_THREADWAKE_SEGMENTS_ENABLED": True,
        "LOCAL_PROVIDER_VENDOR": "whooshd",
        "CODEXIFY_WHOOSHD_THREADWAKE_MODE": "observe",
        "CODEXIFY_WHOOSHD_THREADWAKE_SCOPE": "thread",
    }
    defaults.update(overrides)
    return Settings(**defaults)


def _sample_messages():
    return [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "What is the weather?"},
        {"role": "assistant", "content": "I'll check for you."},
        {"role": "tool", "content": "Sunny, 72F", "name": "get_weather"},
    ]


# ── Feature flag gating ───────────────────────────────────────────────────


class TestFeatureFlag:
    def test_metadata_omitted_by_default(self):
        settings = Settings(LLM_MODEL="test-model")
        segments = _build_threadwake_segments(_sample_messages(), settings=settings)
        assert segments is None

        config = _build_threadwake_config(settings)
        assert config is None

    def test_metadata_omitted_for_non_whooshd_vendor(self):
        settings = _mock_settings(
            CODEXIFY_WHOOSHD_THREADWAKE_SEGMENTS_ENABLED=True,
            LOCAL_PROVIDER_VENDOR="ollama",
        )
        segments = _build_threadwake_segments(_sample_messages(), settings=settings)
        assert segments is None

    def test_metadata_included_when_enabled_and_whooshd(self):
        settings = _mock_settings()
        segments = _build_threadwake_segments(_sample_messages(), settings=settings)
        assert segments is not None
        assert len(segments) == 4  # system, user, assistant, tool

    def test_settings_none_returns_none(self):
        assert _build_threadwake_segments([], settings=None) is None
        assert _build_threadwake_config(None) is None


# ── Segment type mapping ──────────────────────────────────────────────────


class TestSegmentTypeMapping:
    def test_system_message_maps_to_system_stable(self):
        settings = _mock_settings()
        messages = [{"role": "system", "content": "Guardian prompt"}]
        segments = _build_threadwake_segments(messages, settings=settings)
        assert segments is not None
        assert segments[0]["segment_type"] == "system"
        assert segments[0]["stability"] == "stable"

    def test_user_message_maps_to_user_dynamic(self):
        settings = _mock_settings()
        messages = [{"role": "user", "content": "Hello"}]
        segments = _build_threadwake_segments(messages, settings=settings)
        assert segments is not None
        assert segments[0]["segment_type"] == "user"
        assert segments[0]["stability"] == "dynamic"

    def test_tool_message_maps_to_tool_output_dynamic(self):
        settings = _mock_settings()
        messages = [{"role": "tool", "content": "Result", "name": "lookup"}]
        segments = _build_threadwake_segments(messages, settings=settings)
        assert segments is not None
        assert segments[0]["segment_type"] == "tool_output"
        assert segments[0]["stability"] == "dynamic"

    def test_assistant_message_maps_to_thread_semi_stable(self):
        settings = _mock_settings()
        messages = [{"role": "assistant", "content": "Response"}]
        segments = _build_threadwake_segments(messages, settings=settings)
        assert segments is not None
        assert segments[0]["segment_type"] == "thread"
        assert segments[0]["stability"] == "semi_stable"

    def test_unknown_role_maps_to_unknown_dynamic(self):
        settings = _mock_settings()
        messages = [{"role": "developer", "content": "Instructions"}]
        segments = _build_threadwake_segments(messages, settings=settings)
        assert segments is not None
        assert segments[0]["segment_type"] == "unknown"
        assert segments[0]["stability"] == "dynamic"


# ── Content hash ──────────────────────────────────────────────────────────


class TestContentHash:
    def test_hash_is_deterministic(self):
        settings = _mock_settings()
        messages = [{"role": "system", "content": "Deterministic test content"}]
        s1 = _build_threadwake_segments(messages, settings=settings)
        s2 = _build_threadwake_segments(messages, settings=settings)
        assert s1 is not None and s2 is not None
        assert s1[0]["content_hash"] == s2[0]["content_hash"]

    def test_hash_is_sha256_hex(self):
        settings = _mock_settings()
        messages = [{"role": "user", "content": "test"}]
        segments = _build_threadwake_segments(messages, settings=settings)
        assert segments is not None
        h = segments[0]["content_hash"]
        assert len(h) == 64  # SHA-256 produces 64 hex chars
        assert all(c in "0123456789abcdef" for c in h)

    def test_hash_changes_with_content(self):
        settings = _mock_settings()
        s1 = _build_threadwake_segments([{"role": "user", "content": "Hello"}], settings=settings)
        s2 = _build_threadwake_segments([{"role": "user", "content": "World"}], settings=settings)
        assert s1 is not None and s2 is not None
        assert s1[0]["content_hash"] != s2[0]["content_hash"]

    def test_raw_content_not_duplicated_in_metadata(self):
        """Content hash should be present, but raw content should not be duplicated."""
        settings = _mock_settings()
        messages = [{"role": "system", "content": "SECRET_PROMPT"}]
        segments = _build_threadwake_segments(messages, settings=settings)
        assert segments is not None

        seg_json = json.dumps(segments)
        # The content hash is present
        assert "content_hash" in seg_json
        # But the raw content should NOT be duplicated in segment metadata
        # (the hash is a derivative, not the raw content)
        assert "SECRET_PROMPT" not in seg_json


# ── Message index ─────────────────────────────────────────────────────────


class TestMessageIndex:
    def test_message_index_matches_position(self):
        settings = _mock_settings()
        segments = _build_threadwake_segments(_sample_messages(), settings=settings)
        assert segments is not None
        for i, seg in enumerate(segments):
            assert seg["message_index"] == i

    def test_message_name_preserved(self):
        settings = _mock_settings()
        messages = [{"role": "tool", "content": "Result", "name": "get_weather"}]
        segments = _build_threadwake_segments(messages, settings=settings)
        assert segments is not None
        assert segments[0]["name"] == "get_weather"


# ── Config block ──────────────────────────────────────────────────────────


class TestThreadWakeConfig:
    def test_config_defaults(self):
        settings = _mock_settings()
        config = _build_threadwake_config(settings)
        assert config is not None
        assert config["enabled"] is True
        assert config["mode"] == "observe"
        assert config["scope"] == "thread"

    def test_config_custom_mode(self):
        settings = _mock_settings(CODEXIFY_WHOOSHD_THREADWAKE_MODE="ephemeral")
        config = _build_threadwake_config(settings)
        assert config is not None
        assert config["mode"] == "ephemeral"

    def test_config_custom_scope(self):
        settings = _mock_settings(CODEXIFY_WHOOSHD_THREADWAKE_SCOPE="user")
        config = _build_threadwake_config(settings)
        assert config is not None
        assert config["scope"] == "user"


# ── Edge cases ────────────────────────────────────────────────────────────


class TestEdgeCases:
    def test_empty_messages_produces_empty_segments(self):
        settings = _mock_settings()
        segments = _build_threadwake_segments([], settings=settings)
        assert segments == []

    def test_non_dict_message_skipped(self):
        settings = _mock_settings()
        messages = ["not a dict", {"role": "user", "content": "Hello"}]
        segments = _build_threadwake_segments(messages, settings=settings)
        assert segments is not None
        assert len(segments) == 1  # Only the valid dict

    def test_cacheable_flag_false_for_dynamic(self):
        settings = _mock_settings()
        messages = [{"role": "user", "content": "Hello"}]
        segments = _build_threadwake_segments(messages, settings=settings)
        assert segments is not None
        assert segments[0]["cacheable"] is False  # User = dynamic = not cacheable

    def test_cacheable_flag_true_for_stable(self):
        settings = _mock_settings()
        messages = [{"role": "system", "content": "System prompt"}]
        segments = _build_threadwake_segments(messages, settings=settings)
        assert segments is not None
        assert segments[0]["cacheable"] is True  # System = stable = cacheable
