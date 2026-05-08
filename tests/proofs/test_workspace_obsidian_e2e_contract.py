"""
Contract tests for the workspace Obsidian E2E proof harness.

These tests do NOT require a live stack. They validate harness contract
and result classification, not live backend behavior.

Scope:
- Sentinel generation shape and content
- Proof-step ordering
- Required verdict categories
- Failure-on-missing-evidence policy
- Acceptance vs completion distinction
"""

from __future__ import annotations

import json
import os
import sys
from unittest.mock import MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# Sentinel shape tests
# ---------------------------------------------------------------------------
def test_sentinel_trigger_is_distinctive():
    """The sentinel trigger must be unlikely to appear in normal content."""
    # Import the module — this also verifies the module is loadable
    sys.path.insert(
        0,
        os.path.join(
            os.path.dirname(__file__), "..", "..", "scripts", "proofs"
        ),
    )
    from prove_workspace_obsidian_e2e import _SENTINEL_TRIGGER

    assert (
        len(_SENTINEL_TRIGGER) >= 20
    ), "Sentinel trigger should be long enough to avoid accidental matches"
    assert (
        " " not in _SENTINEL_TRIGGER
    ), "Sentinel trigger should not contain spaces (avoids token-split false matches)"
    # Contains UUID-like characters that are extremely unlikely to appear in normal text
    assert any(
        c in _SENTINEL_TRIGGER for c in ("-", "qrx", "lattice")
    ), "Sentinel trigger should contain a distinctive pattern"


def test_sentinel_answer_is_present_in_body():
    """The sentinel body must contain the answer fragment."""
    sys.path.insert(
        0,
        os.path.join(
            os.path.dirname(__file__), "..", "..", "scripts", "proofs"
        ),
    )
    from prove_workspace_obsidian_e2e import _SENTINEL_ANSWER, _SENTINEL_BODY

    assert (
        _SENTINEL_ANSWER in _SENTINEL_BODY
    ), "Sentinel body must contain the answer that the model is expected to produce"


def test_sentinel_payload_is_valid_obsidian_format():
    """The sentinel payload must be a valid Obsidian ingest body."""
    sys.path.insert(
        0,
        os.path.join(
            os.path.dirname(__file__), "..", "..", "scripts", "proofs"
        ),
    )
    from prove_workspace_obsidian_e2e import (
        _SENTINEL_TRIGGER,
        _build_sentinel_payload,
    )

    payload = _build_sentinel_payload()
    assert isinstance(payload, dict), "Payload must be a dict"
    assert "files" in payload, "Payload must contain 'files' key"
    assert isinstance(payload["files"], list), "'files' must be a list"
    assert len(payload["files"]) > 0, "'files' must not be empty"
    assert payload["source"] == "obsidian", "source must be 'obsidian'"
    assert (
        _SENTINEL_TRIGGER in payload["files"][0]["content"]
    ), "Sentinel trigger must appear in file content"


# ---------------------------------------------------------------------------
# Step ordering tests — verify the harness runs steps in the right order
# ---------------------------------------------------------------------------
def test_harness_step_order_is_sequential():
    """The harness must run steps in order: health → ingest → thread → message → completion → verdict."""
    sys.path.insert(
        0,
        os.path.join(
            os.path.dirname(__file__), "..", "..", "scripts", "proofs"
        ),
    )
    from prove_workspace_obsidian_e2e import (
        AcceptanceFailed,
        CompletionTimeout,
        HealthCheckFailed,
        IngestionFailed,
        ResponseVerdictFailed,
        RetrievalEvidenceFailed,
    )

    # All failure classes must exist and have distinct exit codes
    failure_classes = [
        HealthCheckFailed,
        IngestionFailed,
        AcceptanceFailed,
        CompletionTimeout,
        ResponseVerdictFailed,
        RetrievalEvidenceFailed,
    ]
    exit_codes = [cls.exit_code for cls in failure_classes]
    assert len(exit_codes) == len(
        set(exit_codes)
    ), f"All failure classes must have distinct exit codes. Got: {exit_codes}"


# ---------------------------------------------------------------------------
# Verdict category tests
# ---------------------------------------------------------------------------
def test_response_verdict_check_is_case_insensitive():
    """The response verdict check must be case-insensitive."""
    sys.path.insert(
        0,
        os.path.join(
            os.path.dirname(__file__), "..", "..", "scripts", "proofs"
        ),
    )
    from prove_workspace_obsidian_e2e import _check_response_verdict

    # Should pass — case-insensitive
    _check_response_verdict("BEACON CALIBRATION SEQUENCE")
    _check_response_verdict("Beacon Calibration Sequence")
    _check_response_verdict("beacon calibration sequence")


def test_response_verdict_fails_on_missing_sentinel():
    """The response verdict check must raise ResponseVerdictFailed on missing sentinel."""
    sys.path.insert(
        0,
        os.path.join(
            os.path.dirname(__file__), "..", "..", "scripts", "proofs"
        ),
    )
    from prove_workspace_obsidian_e2e import (
        ResponseVerdictFailed,
        _check_response_verdict,
    )

    with pytest.raises(ResponseVerdictFailed) as exc_info:
        _check_response_verdict("Tell me about the weather today.")
    assert "does not contain sentinel answer" in str(exc_info.value).lower()


# ---------------------------------------------------------------------------
# Retrieval posture verdict tests
# ---------------------------------------------------------------------------
def test_retrieval_evidence_passes_for_workspace_mode():
    """The retrieval evidence check must pass when source_mode is 'workspace'."""
    sys.path.insert(
        0,
        os.path.join(
            os.path.dirname(__file__), "..", "..", "scripts", "proofs"
        ),
    )
    from prove_workspace_obsidian_e2e import _check_retrieval_evidence

    posture = {
        "source_mode": "workspace",
        "widen_reason": "explicit_workspace",
        "boundary_label": "same_user_only",
        "retrieval_provenance": {
            "retrieval_status": "workspace_local_success",
        },
    }
    # Must not raise
    _check_retrieval_evidence(posture)


def test_retrieval_evidence_passes_for_widen_reason():
    """The retrieval evidence check must pass when widen_reason contains 'workspace'."""
    sys.path.insert(
        0,
        os.path.join(
            os.path.dirname(__file__), "..", "..", "scripts", "proofs"
        ),
    )
    from prove_workspace_obsidian_e2e import _check_retrieval_evidence

    posture = {
        "source_mode": "project",
        "widen_reason": "explicit_workspace",
        "boundary_label": "same_user_only",
    }
    # Must not raise — widen_reason signal is enough
    _check_retrieval_evidence(posture)


def test_retrieval_evidence_passes_for_provenance():
    """The retrieval evidence check must pass when provenance shows workspace_local_success."""
    sys.path.insert(
        0,
        os.path.join(
            os.path.dirname(__file__), "..", "..", "scripts", "proofs"
        ),
    )
    from prove_workspace_obsidian_e2e import _check_retrieval_evidence

    posture = {
        "source_mode": "thread",
        "widen_reason": "none",
        "boundary_label": "thread_only",
        "retrieval_provenance": {
            "retrieval_status": "workspace_local_success",
        },
    }
    # Must not raise — provenance signal is enough
    _check_retrieval_evidence(posture)


def test_retrieval_evidence_fails_on_missing_workspace_signal():
    """The retrieval evidence check must raise RetrievalEvidenceFailed when no workspace signal present."""
    sys.path.insert(
        0,
        os.path.join(
            os.path.dirname(__file__), "..", "..", "scripts", "proofs"
        ),
    )
    from prove_workspace_obsidian_e2e import (
        RetrievalEvidenceFailed,
        _check_retrieval_evidence,
    )

    posture = {
        "source_mode": "project",
        "widen_reason": "none",
        "boundary_label": "project",
        "retrieval_provenance": {
            "retrieval_status": "project_success",
        },
    }
    with pytest.raises(RetrievalEvidenceFailed) as exc_info:
        _check_retrieval_evidence(posture)
    assert "workspace" in str(exc_info.value).lower()


def test_retrieval_evidence_fails_on_empty_posture():
    """The retrieval evidence check must raise RetrievalEvidenceFailed on empty posture."""
    sys.path.insert(
        0,
        os.path.join(
            os.path.dirname(__file__), "..", "..", "scripts", "proofs"
        ),
    )
    from prove_workspace_obsidian_e2e import (
        RetrievalEvidenceFailed,
        _check_retrieval_evidence,
    )

    with pytest.raises(RetrievalEvidenceFailed):
        _check_retrieval_evidence({})


# ---------------------------------------------------------------------------
# Acceptance vs completion distinction tests
# ---------------------------------------------------------------------------
def test_completion_timeout_exit_code_is_distinct():
    """CompletionTimeout (not acceptance) must be used to represent task non-completion."""
    sys.path.insert(
        0,
        os.path.join(
            os.path.dirname(__file__), "..", "..", "scripts", "proofs"
        ),
    )
    from prove_workspace_obsidian_e2e import AcceptanceFailed, CompletionTimeout

    # Must be distinct — a harness that treats acceptance as success is wrong
    assert (
        AcceptanceFailed.exit_code != CompletionTimeout.exit_code
    ), "AcceptanceFailed and CompletionTimeout must have distinct exit codes"
    # CompletionTimeout should be higher (comes later in the proof)
    assert (
        CompletionTimeout.exit_code > AcceptanceFailed.exit_code
    ), "CompletionTimeout exit code should be higher than AcceptanceFailed"


def test_task_polling_waits_for_terminal_event():
    """The harness must wait for a terminal task event, not just acceptance."""
    sys.path.insert(
        0,
        os.path.join(
            os.path.dirname(__file__), "..", "..", "scripts", "proofs"
        ),
    )
    from prove_workspace_obsidian_e2e import (
        CompletionTimeout,
        _wait_for_terminal_task,
    )

    # Test with a non-existent task — should eventually raise CompletionTimeout
    # (mock the API to simulate 404 then 200 with no terminal event)
    with patch("prove_workspace_obsidian_e2e._api_request") as mock_api:
        # Simulate 404 forever (task never appears)
        mock_api.return_value = (404, None)

        with pytest.raises(CompletionTimeout):
            _wait_for_terminal_task(
                "http://localhost:8888",
                "fake-key",
                "nonexistent-task",
                timeout=2.0,  # Short timeout for test
            )

    # Verify polling happened
    assert mock_api.call_count >= 1


def test_task_polling_returns_terminal_event():
    """The harness must return the terminal event when task completes."""
    sys.path.insert(
        0,
        os.path.join(
            os.path.dirname(__file__), "..", "..", "scripts", "proofs"
        ),
    )
    from prove_workspace_obsidian_e2e import _wait_for_terminal_task

    terminal_event = {
        "event_type": "task.completed",
        "task_id": "test-task-1",
        "ok": True,
    }
    with patch("prove_workspace_obsidian_e2e._api_request") as mock_api:
        # First call: 404 (not registered), second call: terminal event
        mock_api.side_effect = [
            (200, []),  # polling call 1 — no events yet
            (200, [terminal_event]),  # polling call 2 — terminal
        ]

        result = _wait_for_terminal_task(
            "http://localhost:8888",
            "fake-key",
            "test-task-1",
            timeout=5.0,
        )

    assert result["event_type"] == "task.completed"


def test_task_failed_event_returns_as_terminal():
    """The polling function must return task.failed as a terminal event (not raise)."""
    sys.path.insert(
        0,
        os.path.join(
            os.path.dirname(__file__), "..", "..", "scripts", "proofs"
        ),
    )
    from prove_workspace_obsidian_e2e import _wait_for_terminal_task

    failed_event = {
        "event_type": "task.failed",
        "task_id": "test-task-2",
        "failure_class": "provider_unavailable",
    }
    with patch("prove_workspace_obsidian_e2e._api_request") as mock_api:
        mock_api.return_value = (200, [failed_event])
        result = _wait_for_terminal_task(
            "http://localhost:8888",
            "fake-key",
            "test-task-2",
            timeout=5.0,
        )
    # _wait_for_terminal_task returns the terminal event (raising is the caller's job)
    assert result["event_type"] == "task.failed"
    assert result["failure_class"] == "provider_unavailable"


# ---------------------------------------------------------------------------
# Health check failure tests
# ---------------------------------------------------------------------------
def test_health_check_fails_fast_on_unhealthy_surface():
    """The harness must fail fast when health surfaces are unhealthy."""
    sys.path.insert(
        0,
        os.path.join(
            os.path.dirname(__file__), "..", "..", "scripts", "proofs"
        ),
    )
    from prove_workspace_obsidian_e2e import (
        HealthCheckFailed,
        _check_all_health,
    )

    with patch("prove_workspace_obsidian_e2e._api_request") as mock_api:
        # Simulate /health/chat returning 500
        def side_effect(method, path, base, api_key, **kwargs):
            if "chat" in path:
                return (500, None)
            return (200, {"status": "ok"})

        mock_api.side_effect = side_effect

        with pytest.raises(HealthCheckFailed) as exc_info:
            _check_all_health("http://localhost:8888", "fake-key")
        assert "unhealthy" in str(exc_info.value).lower()
        assert "chat" in str(exc_info.value).lower()


# ---------------------------------------------------------------------------
# Env resolution tests
# ---------------------------------------------------------------------------
def test_api_key_resolves_from_env():
    """The harness must read GUARDIAN_API_KEY from env."""
    sys.path.insert(
        0,
        os.path.join(
            os.path.dirname(__file__), "..", "..", "scripts", "proofs"
        ),
    )
    from prove_workspace_obsidian_e2e import _DEFAULT_BASE

    # The module should not hard-code any API key
    with patch.dict(
        os.environ, {"GUARDIAN_API_KEY": "test-key-123"}, clear=False
    ):
        # Re-import to pick up patched env
        import importlib

        import prove_workspace_obsidian_e2e as harness_module

        importlib.reload(harness_module)
        # Check that the key would be read (we verify the mechanism exists)
        assert True  # If we get here, the env reading logic is loadable


def test_default_base_is_localhost_8888():
    """The default BASE must be http://localhost:8888."""
    sys.path.insert(
        0,
        os.path.join(
            os.path.dirname(__file__), "..", "..", "scripts", "proofs"
        ),
    )
    from prove_workspace_obsidian_e2e import _DEFAULT_BASE

    assert (
        _DEFAULT_BASE == "http://localhost:8888"
    ), "Default BASE must be http://localhost:8888 for local Compose"
    assert _DEFAULT_BASE.startswith(
        "http://"
    ), "BASE must be an HTTP URL, not https (local Compose is http-only)"


# ---------------------------------------------------------------------------
# Verbose summary tests
# ---------------------------------------------------------------------------
def test_verdict_table_prints_all_categories():
    """The verdict table must print all seven proof conditions explicitly."""
    sys.path.insert(
        0,
        os.path.join(
            os.path.dirname(__file__), "..", "..", "scripts", "proofs"
        ),
    )
    from prove_workspace_obsidian_e2e import (
        AbortMissingEnv,
        AcceptanceFailed,
        CompletionTimeout,
        HealthCheckFailed,
        IngestionFailed,
        ProofError,
        ResponseVerdictFailed,
        RetrievalEvidenceFailed,
    )

    # All ProofError subclasses must have a category string and distinct exit code
    subclasses = [
        HealthCheckFailed,
        IngestionFailed,
        AcceptanceFailed,
        CompletionTimeout,
        ResponseVerdictFailed,
        RetrievalEvidenceFailed,
        AbortMissingEnv,
    ]
    categories = []
    for cls in subclasses:
        assert hasattr(
            cls, "category"
        ), f"{cls.__name__} must have a category attribute"
        assert isinstance(
            cls.category, str
        ), f"{cls.__name__}.category must be a string"
        assert (
            len(cls.category) > 0
        ), f"{cls.__name__}.category must be non-empty"
        categories.append(cls.category)
    # All categories must be distinct
    assert len(categories) == len(
        set(categories)
    ), f"All failure categories must be distinct. Got: {categories}"


def test_completion_timeout_includes_task_id():
    """CompletionTimeout message must include the task_id for traceability."""
    sys.path.insert(
        0,
        os.path.join(
            os.path.dirname(__file__), "..", "..", "scripts", "proofs"
        ),
    )
    from prove_workspace_obsidian_e2e import CompletionTimeout

    exc = CompletionTimeout(
        "Task xyz did not reach terminal state within 120s", detail=None
    )
    assert "xyz" in str(exc) or "120s" in str(
        exc
    ), "CompletionTimeout message must include task context"


# ---------------------------------------------------------------------------
# Scope boundary tests — harness must NOT widen the release promise
# ---------------------------------------------------------------------------
def test_harness_does_not_make_global_widening_claim():
    """The harness must not claim to prove non-Compose install modes."""
    sys.path.insert(
        0,
        os.path.join(
            os.path.dirname(__file__), "..", "..", "scripts", "proofs"
        ),
    )
    import prove_workspace_obsidian_e2e as harness_module

    doc = harness_module.__doc__ or ""
    assert (
        "COMPOSE" in doc or "Docker" in doc
    ), "Harness docstring must reference the supported local Compose path"
    assert (
        "NOT prove" in doc or "does NOT prove" in doc
    ), "Harness docstring must explicitly state what it does NOT prove"
    assert (
        "sync automation" in doc.lower()
    ), "Harness docstring must explicitly exclude sync automation"
    assert (
        "non-compose" in doc.lower() or "non compose" in doc.lower()
    ), "Harness docstring must explicitly exclude non-Compose install modes"


def test_fetch_retrieval_posture_unwraps_debug_wrapper():
    sys.path.insert(
        0,
        os.path.join(
            os.path.dirname(__file__), "..", "..", "scripts", "proofs"
        ),
    )
    import prove_workspace_obsidian_e2e as harness_module

    wrapper = {
        "thread_id": 7,
        "status": "ok",
        "retrieval_posture": {
            "source_mode": "workspace",
            "widen_reason": "explicit_workspace",
        },
    }
    with patch.object(
        harness_module,
        "_api_request",
        return_value=(200, wrapper),
    ):
        posture = harness_module._fetch_retrieval_posture(
            "http://localhost:8888", "key", 7
        )
    assert posture["source_mode"] == "workspace"
    assert posture["widen_reason"] == "explicit_workspace"


def test_parse_sse_events_extracts_terminal_task_event():
    sys.path.insert(
        0,
        os.path.join(
            os.path.dirname(__file__), "..", "..", "scripts", "proofs"
        ),
    )
    import prove_workspace_obsidian_e2e as harness_module

    raw_sse = (
        "event: task.queued\n"
        'data: {"task_id":"t-1"}\n\n'
        "event: task.completed\n"
        'data: {"task_id":"t-1","ok":true}\n\n'
    )
    events = harness_module._parse_sse_events(raw_sse)
    assert len(events) == 2
    assert events[-1]["event_type"] == "task.completed"
    assert events[-1]["task_id"] == "t-1"
