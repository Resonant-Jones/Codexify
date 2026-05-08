"""Regression test for _build_model_selection_trace helper invocation.

This test ensures the model selection trace helper is called with all required
keyword arguments, preventing the missing-args exception that blocked chat
completion on main in 2026-05-08.
"""

from __future__ import annotations

from guardian.core.chat_completion_service import _build_model_selection_trace


def test_build_model_selection_trace_returns_successfully_with_all_args():
    """Prove the trace helper accepts the full argument set without raising."""
    result = _build_model_selection_trace(
        requested_provider="local",
        requested_model="gemma4-e4b-hauhau:latest",
        attempted_provider="local",
        attempted_model="gemma4-e4b-hauhau:latest",
        resolved_provider="local",
        resolved_model="gemma4-e4b-hauhau:latest",
        final_provider="local",
        final_model="gemma4-e4b-hauhau:latest",
        selection_source="profile",
        fallback_reason=None,
        model_resolution=None,
    )

    assert isinstance(result, dict)
    assert result.get("final_provider") == "local"
    assert result.get("final_model") == "gemma4-e4b-hauhau:latest"


def test_build_model_selection_trace_handles_none_values():
    """Prove the trace helper accepts None for optional resolution fields."""
    result = _build_model_selection_trace(
        requested_provider=None,
        requested_model=None,
        attempted_provider="local",
        attempted_model="ministral-3:8b",
        resolved_provider=None,
        resolved_model=None,
        final_provider="local",
        final_model="ministral-3:8b",
        selection_source=None,
        fallback_reason=None,
        model_resolution=None,
    )

    assert isinstance(result, dict)
    assert result.get("final_provider") == "local"


def test_build_model_selection_trace_with_model_resolution_dict():
    """Prove the trace helper accepts a model_resolution dict."""
    resolution = {
        "source": "profile_override",
        "original_model": "gpt-4o",
        "resolved_model": "gemma4-e4b-hauhau:latest",
    }
    result = _build_model_selection_trace(
        requested_provider="openai",
        requested_model="gpt-4o",
        attempted_provider="local",
        attempted_model="gemma4-e4b-hauhau:latest",
        resolved_provider="local",
        resolved_model="gemma4-e4b-hauhau:latest",
        final_provider="local",
        final_model="gemma4-e4b-hauhau:latest",
        selection_source="profile",
        fallback_reason="cloud_disabled",
        model_resolution=resolution,
    )

    assert isinstance(result, dict)
    assert result.get("final_provider") == "local"
    assert result.get("final_model") == "gemma4-e4b-hauhau:latest"
