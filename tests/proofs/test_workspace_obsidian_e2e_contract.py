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
        token="workspace-seal-123",
    )

    assert tuple(verdicts) == module.VERDICT_CATEGORIES


def test_missing_evidence_fails_closed():
    module = _load_module()

    verdicts = module.classify_proof_verdicts(
        acceptance_status="accepted",
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
        token="workspace-seal-123",
    )

    assert verdicts["acceptance"]["passed"] is True
    assert verdicts["completion"]["passed"] is True
    assert verdicts["retrieval_evidence"]["passed"] is False
    assert verdicts["final_verdict"]["passed"] is False
    assert "retrieval_evidence" in verdicts["final_verdict"]["reasons"]


def test_acceptance_alone_is_not_success():
    module = _load_module()

    verdicts = module.classify_proof_verdicts(
        acceptance_status="accepted",
        terminal_event_type=None,
        assistant_text=None,
        retrieval_status=None,
        obsidian_semantic_hits=0,
        retrieval_source_mode="workspace",
        retrieval_posture=None,
        token="workspace-seal-123",
    )

    assert verdicts["acceptance"]["passed"] is True
    assert verdicts["completion"]["passed"] is False
    assert verdicts["retrieval_evidence"]["passed"] is False
    assert verdicts["assistant_match"]["passed"] is False
    assert verdicts["final_verdict"]["passed"] is False
    assert set(verdicts["final_verdict"]["reasons"]) == {
        "completion",
        "retrieval_evidence",
        "assistant_match",
    }
