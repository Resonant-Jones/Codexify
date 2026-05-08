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

import importlib.util
import sys
from pathlib import Path

SCRIPT_PATH = (
    Path(__file__).resolve().parents[2]
    / "scripts"
    / "proofs"
    / "prove_workspace_obsidian_e2e.py"
)


def _load_module():
    spec = importlib.util.spec_from_file_location(
        "prove_workspace_obsidian_e2e",
        SCRIPT_PATH,
    )
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_workspace_sentinel_shape_is_deterministic():
    module = _load_module()

    first = module.build_workspace_sentinel(seed="proof-seed")
    second = module.build_workspace_sentinel(seed="proof-seed")

    assert first == second
    assert first.token.startswith("workspace-seal-")
    assert first.expected_answer == first.token
    assert first.note_title in first.note_text
    assert first.token in first.note_text
    assert "supported local Compose path only" in first.note_text
    assert "Reply with only the phrase" in first.question


def test_workspace_evidence_normalization_prefers_obsidian_completion_counts():
    module = _load_module()

    evidence = module._normalize_workspace_retrieval_evidence(
        task_completed_payload={
            "payload_summary": {
                "source_mode": "workspace",
                "obsidian_count": 1,
                "semantic_count": 4,
                "graph_hit_count": 1,
                "linked_document_count": 2,
                "retrieval_injected": True,
                "obsidian_injected": True,
            }
        },
        retrieval_posture={
            "source_mode": "workspace",
            "boundary_label": "same_user_only",
            "widen_reason": "explicit_workspace",
        },
        trace={
            "source_mode": "workspace",
            "payload_summary": {
                "source_mode": "workspace",
                "obsidian_count": 1,
            },
        },
    )

    assert evidence["retrieval_status"] == "workspace_local_success"
    assert evidence["obsidian_count"] == 1
    assert evidence["retrieval_injected"] is True
    assert evidence["obsidian_injected"] is True


def test_proof_step_order_is_stable():
    module = _load_module()

    assert module.PROOF_STEP_ORDER == (
        "health",
        "obsidian_config",
        "obsidian_index",
        "obsidian_search",
        "thread_create",
        "user_message",
        "completion_acceptance",
        "task_events",
        "message_verification",
        "trace_verification",
        "final_verdict",
    )


def test_required_verdict_categories_are_present():
    module = _load_module()

    verdicts = module.classify_proof_verdicts(
        acceptance_status="accepted",
        substrate_searchable=True,
        terminal_event_type="task.completed",
        assistant_text="workspace-seal-123",
        retrieval_status="workspace_local_success",
        obsidian_semantic_hits=1,
        retrieval_source_mode="workspace",
        retrieval_posture={
            "source_mode": "workspace",
            "boundary_label": "same_user_only",
            "widen_reason": "explicit_workspace",
        },
        obsidian_injected=True,
        token="workspace-seal-123",
    )

    assert tuple(verdicts) == module.VERDICT_CATEGORIES


def test_missing_evidence_fails_closed():
    module = _load_module()

    verdicts = module.classify_proof_verdicts(
        acceptance_status="accepted",
        substrate_searchable=True,
        terminal_event_type="task.completed",
        assistant_text="workspace-seal-123",
        retrieval_status="workspace_local_missing_obsidian",
        obsidian_semantic_hits=0,
        retrieval_source_mode="workspace",
        retrieval_posture={
            "source_mode": "workspace",
            "boundary_label": "same_user_only",
            "widen_reason": "explicit_workspace",
        },
        obsidian_injected=False,
        token="workspace-seal-123",
    )

    assert verdicts["acceptance"]["passed"] is True
    assert verdicts["substrate_searchability"]["passed"] is True
    assert verdicts["completion"]["passed"] is True
    assert verdicts["workspace_eligibility"]["passed"] is True
    assert verdicts["broker_selection"]["passed"] is False
    assert verdicts["completion_injection"]["passed"] is False
    assert verdicts["final_verdict"]["passed"] is False
    assert set(verdicts["final_verdict"]["reasons"]) == {
        "broker_selection",
        "completion_injection",
    }


def test_worker_payload_evidence_is_not_backfilled_from_debug_trace():
    module = _load_module()

    evidence = module._normalize_workspace_retrieval_evidence(
        task_completed_payload={
            "payload_summary": {
                "message_count": 2,
                "source_mode": "workspace",
                "effective_source_mode": "workspace",
                "semantic_count": 1,
                "obsidian_count": 0,
                "retrieval_injected": False,
                "obsidian_injected": False,
            }
        },
        retrieval_posture={
            "source_mode": "workspace",
            "boundary_label": "same_user_only",
            "retrieval_override_mode": None,
            "widen_reason": "explicit_workspace",
            "conversation_only": False,
        },
        trace={
            "source_mode": "workspace",
            "payload_summary": {
                "source_mode": "workspace",
                "effective_source_mode": "workspace",
                "semantic_count": 1,
                "obsidian_count": 1,
                "retrieval_injected": True,
                "obsidian_injected": True,
            },
        },
    )

    assert evidence["source_mode"] == "workspace"
    assert evidence["obsidian_count"] == 0
    assert evidence["worker_payload_obsidian_count"] == 0
    assert evidence["trace_obsidian_count"] == 1
    assert evidence["obsidian_injected"] is False
    assert evidence["worker_payload_obsidian_injected"] is False
    assert evidence["trace_obsidian_injected"] is True

    verdicts = module.classify_proof_verdicts(
        acceptance_status="accepted",
        substrate_searchable=True,
        terminal_event_type="task.completed",
        assistant_text="workspace-seal-123",
        retrieval_status=evidence["retrieval_status"],
        obsidian_semantic_hits=evidence["obsidian_count"],
        retrieval_source_mode=evidence["source_mode"],
        retrieval_posture={
            "source_mode": "workspace",
            "boundary_label": "same_user_only",
            "retrieval_override_mode": None,
            "widen_reason": "explicit_workspace",
            "conversation_only": False,
        },
        obsidian_injected=evidence["obsidian_injected"],
        token="workspace-seal-123",
    )

    assert verdicts["broker_selection"]["passed"] is False
    assert verdicts["completion_injection"]["passed"] is False
    assert verdicts["final_verdict"]["passed"] is False


def test_worker_payload_posture_is_not_backfilled_from_debug_trace(monkeypatch):
    module = _load_module()

    def _fake_request_json(_session, _method, url, **_kwargs):
        if "rag-trace" in url:
            return {
                "trace": {
                    "source_mode": "workspace",
                    "widen_reason": "explicit_workspace",
                },
                "payload_summary": {
                    "source_mode": "workspace",
                    "effective_source_mode": "workspace",
                    "retrieval_posture": {
                        "source_mode": "workspace",
                        "boundary_label": "same_user_only",
                        "retrieval_override_mode": None,
                        "widen_reason": "explicit_workspace",
                        "conversation_only": False,
                    },
                },
            }
        raise AssertionError(f"unexpected request: {url}")

    monkeypatch.setattr(module, "_request_json", _fake_request_json)

    worker_posture, trace = module._latest_retrieval_artifacts(
        object(),
        "http://example.test",
        {},
        1,
        {
            "payload_summary": {
                "source_mode": "workspace",
                "effective_source_mode": "workspace",
            }
        },
    )

    assert worker_posture is None
    assert isinstance(trace, dict)
    assert trace["payload_summary"]["retrieval_posture"]["source_mode"] == (
        "workspace"
    )


def test_acceptance_alone_is_not_success():
    module = _load_module()

    verdicts = module.classify_proof_verdicts(
        acceptance_status="accepted",
        substrate_searchable=False,
        terminal_event_type=None,
        assistant_text=None,
        retrieval_status=None,
        obsidian_semantic_hits=0,
        retrieval_source_mode="workspace",
        retrieval_posture=None,
        obsidian_injected=False,
        token="workspace-seal-123",
    )

    assert verdicts["acceptance"]["passed"] is True
    assert verdicts["substrate_searchability"]["passed"] is False
    assert verdicts["completion"]["passed"] is False
    assert verdicts["workspace_eligibility"]["passed"] is False
    assert verdicts["broker_selection"]["passed"] is False
    assert verdicts["completion_injection"]["passed"] is False
    assert verdicts["assistant_match"]["passed"] is False
    assert verdicts["final_verdict"]["passed"] is False
    assert set(verdicts["final_verdict"]["reasons"]) == {
        "substrate_searchability",
        "completion",
        "workspace_eligibility",
        "broker_selection",
        "completion_injection",
        "assistant_match",
    }


def test_harness_does_not_make_global_widening_claim():
    """The harness must not claim to prove non-Compose install modes."""
    module = _load_module()

    doc = module.__doc__ or ""
    assert (
        "supported local Compose path" in doc
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


def test_sentinel_trigger_is_distinctive():
    """The sentinel trigger must be unlikely to appear in normal content."""
    module = _load_module()

    sentinel = module.build_workspace_sentinel()
    # Token should be long enough to avoid accidental matches
    assert len(sentinel.token) >= 20, "Sentinel token should be long enough"
    assert " " not in sentinel.token, "Sentinel token should not contain spaces"
    # Contains distinctive pattern
    assert "workspace-seal-" in sentinel.token


def test_sentinel_payload_is_valid_obsidian_format():
    """The sentinel payload must be a valid Obsidian ingest body."""
    module = _load_module()

    sentinel = module.build_workspace_sentinel()
    # The note_text should be a valid markdown note
    assert sentinel.note_text.startswith("---")
    assert "title:" in sentinel.note_text
    assert sentinel.token in sentinel.note_text
    assert "Reply with only the phrase" in sentinel.question
