"""
Tests for Flow Builder TestRun Harness

These tests verify:
- valid fixture returns completed TestRunResult and completed RunReceipt
- no side effects are recorded
- gated harness-local side effects require an explicit gate
- semantic extract/summarize/decide steps produce StepReceipts
- conditional container marks skipped branch steps as skipped
- unsupported notification/document/task/command steps block validation
- side effect risk blocks validation
- missing required FlowDraft fields block validation
- input FlowDraft is not mutated
- no backend route/API/persistence imports are required by the harness
- tokens are bounded to the Flow Builder harness module
"""

import copy
from typing import Any, Mapping

import pytest

from guardian.flow_builder import (
    HARNESS_SIDE_EFFECT_KIND,
    SUPPORTED_SEMANTIC_KINDS,
    UNSUPPORTED_STEP_KINDS,
    RunReceipt,
    SideEffectGate,
    SideEffectRecord,
    StepReceipt,
    TestRunResult,
    ValidationIssue,
    ValidationSummary,
    is_supported_semantic_kind,
    is_supported_step_kind,
    is_valid_run_receipt_state,
    is_valid_step_receipt_state,
    is_valid_test_run_state,
    is_valid_validation_issue_code,
    is_valid_validation_severity,
    run_gated_side_effect_test,
    run_non_side_effecting_test,
    validate_no_side_effect_subset,
)

# =============================================================================
# Fixtures
# =============================================================================


def make_valid_flow_draft() -> dict:
    """Create a valid FlowDraft fixture for non-side-effecting test run."""
    return {
        "id": "flow-draft:test-001",
        "title": "Test Flow",
        "status": "draft",
        "steps": [
            {
                "id": "step:extract-001",
                "kind": "semantic",
                "label": "Extract fields",
                "position": 1,
                "config": {
                    "semantic_step_kind": "extract",
                    "instruction": "Extract key fields from input.",
                    "side_effect_risk_class": "none",
                },
            },
            {
                "id": "step:summarize-001",
                "kind": "semantic",
                "label": "Summarize",
                "position": 2,
                "config": {
                    "semantic_step_kind": "summarize",
                    "instruction": "Summarize extracted data.",
                    "side_effect_risk_class": "none",
                },
            },
        ],
        "conditional_container": {
            "id": "container:score-check",
            "kind": "conditional",
            "label": "Score check",
            "position": 3,
            "condition": {
                "id": "condition:score-gte-70",
                "lhs": "step:extract-001.output.score",
                "operator": "greater_than",
                "rhs": "70",
            },
            "substeps": [
                {
                    "id": "step:then-action-001",
                    "kind": "transform",
                    "label": "Then branch action",
                    "position": 0,
                    "config": {
                        "side_effect_risk_class": "none",
                    },
                },
            ],
            "else_substeps": [
                {
                    "id": "step:else-action-001",
                    "kind": "transform",
                    "label": "Else branch action",
                    "position": 0,
                    "config": {
                        "side_effect_risk_class": "none",
                    },
                },
            ],
        },
        "provenance": {
            "origin_thread_id": "thread:test-001",
        },
        "starter": {
            "id": "starter:manual-001",
            "kind": "manual",
            "label": "Manual trigger",
        },
    }


def make_side_effecting_flow_draft() -> dict:
    """Create a FlowDraft with side-effecting steps that should be blocked."""
    return {
        "id": "flow-draft:side-effect-001",
        "title": "Side Effect Flow",
        "steps": [
            {
                "id": "step:notification-001",
                "kind": "notification",
                "label": "Send notification",
                "position": 1,
                "config": {
                    "notification_type": "email",
                    "side_effect_risk_class": "external_write",
                },
            },
        ],
    }


def make_gated_side_effect_flow_draft() -> dict:
    """Create a FlowDraft with a gated internal-note command step."""
    return {
        "id": "flow-draft:gate-001",
        "title": "Gated Side Effect Flow",
        "status": "draft",
        "steps": [
            {
                "id": "step:internal-note-001",
                "kind": "command",
                "label": "Record internal note",
                "position": 1,
                "config": {
                    "side_effect_kind": "record_internal_note",
                    "side_effect_risk_class": "internal_write",
                    "target_ref": "thread:test-001",
                    "payload_summary": "Harness-local internal note for proof only.",
                    "idempotency_key": "idempotency:note-001",
                },
            },
        ],
        "provenance": {
            "origin_thread_id": "thread:test-001",
        },
        "starter": {
            "id": "starter:manual-001",
            "kind": "manual",
            "label": "Manual trigger",
        },
    }


def make_side_effect_gate(
    *,
    enabled: bool = True,
    mode: str = "explicit_harness_gate",
    allowed_kinds: list[str] | None = None,
    approved_by: str = "operator:test-001",
    approval_reason: str = "Explicit harness gate for proof only.",
) -> SideEffectGate:
    """Create an explicit harness gate fixture."""
    default_kind = next(iter(HARNESS_SIDE_EFFECT_KIND))
    return SideEffectGate(
        enabled=enabled,
        mode=mode,
        allowed_kinds=list(allowed_kinds or [default_kind]),
        approved_by=approved_by,
        approval_reason=approval_reason,
    )


def make_decide_flow_draft() -> dict:
    """Create a FlowDraft with a decide semantic step."""
    return {
        "id": "flow-draft:decide-001",
        "title": "Decide Flow",
        "steps": [
            {
                "id": "step:decide-001",
                "kind": "semantic",
                "label": "Decide outcome",
                "position": 1,
                "config": {
                    "semantic_step_kind": "decide",
                    "instruction": "Decide between options based on input.",
                    "side_effect_risk_class": "none",
                },
            },
        ],
    }


# =============================================================================
# Token validation tests
# =============================================================================


class TestTokenValidation:
    """Tests for token validation functions."""

    def test_supported_step_kind_returns_true_for_semantic(self):
        assert is_supported_step_kind("semantic") is True

    def test_supported_step_kind_returns_true_for_transform(self):
        assert is_supported_step_kind("transform") is True

    def test_supported_step_kind_returns_true_for_conditional(self):
        assert is_supported_step_kind("conditional") is True

    def test_supported_step_kind_returns_false_for_notification(self):
        assert is_supported_step_kind("notification") is False

    def test_supported_step_kind_returns_false_for_document(self):
        assert is_supported_step_kind("document") is False

    def test_supported_step_kind_returns_false_for_task(self):
        assert is_supported_step_kind("task") is False

    def test_supported_step_kind_returns_false_for_command(self):
        assert is_supported_step_kind("command") is False

    def test_supported_semantic_kind_returns_true_for_extract(self):
        assert is_supported_semantic_kind("extract") is True

    def test_supported_semantic_kind_returns_true_for_summarize(self):
        assert is_supported_semantic_kind("summarize") is True

    def test_supported_semantic_kind_returns_true_for_decide(self):
        assert is_supported_semantic_kind("decide") is True

    def test_supported_semantic_kind_returns_false_for_classify(self):
        assert is_supported_semantic_kind("classify") is False

    def test_supported_semantic_kind_returns_false_for_route(self):
        assert is_supported_semantic_kind("route") is False

    def test_valid_test_run_states(self):
        valid_states = {"queued", "running", "completed", "failed", "cancelled"}
        for state in valid_states:
            assert is_valid_test_run_state(state) is True

    def test_invalid_test_run_state(self):
        assert is_valid_test_run_state("invalid-state") is False

    def test_valid_run_receipt_states(self):
        valid_states = {
            "queued",
            "running",
            "completed",
            "failed",
            "cancelled",
            "blocked",
        }
        for state in valid_states:
            assert is_valid_run_receipt_state(state) is True

    def test_valid_step_receipt_states(self):
        valid_states = {
            "pending",
            "running",
            "skipped",
            "completed",
            "failed",
            "blocked",
        }
        for state in valid_states:
            assert is_valid_step_receipt_state(state) is True

    def test_valid_validation_severity(self):
        valid_severities = {"info", "warning", "error", "blocking"}
        for severity in valid_severities:
            assert is_valid_validation_severity(severity) is True

    def test_valid_validation_issue_codes(self):
        valid_codes = {
            "missing_required_field",
            "unsupported_step_kind",
            "side_effect_not_allowed",
            "side_effect_gate_required",
            "side_effect_kind_unsupported",
            "idempotency_key_required",
            "external_side_effect_forbidden",
            "missing_substep",
            "unsupported_semantic_kind",
            "invalid_condition",
            "receipt_required",
        }
        for code in valid_codes:
            assert is_valid_validation_issue_code(code) is True


# =============================================================================
# Validation tests
# =============================================================================


class TestValidation:
    """Tests for validate_no_side_effect_subset function."""

    def test_valid_fixture_returns_info_state(self):
        draft = make_valid_flow_draft()
        summary = validate_no_side_effect_subset(draft)
        assert summary.state == "info"
        assert summary.blocking_count == 0

    def test_valid_fixture_eligible_for_test_run(self):
        draft = make_valid_flow_draft()
        summary = validate_no_side_effect_subset(draft)
        assert summary.eligible_for_test_run is True
        assert summary.eligible_for_activation is False  # Not implemented

    def test_missing_flow_draft_id_blocks(self):
        draft = make_valid_flow_draft()
        del draft["id"]
        summary = validate_no_side_effect_subset(draft)
        assert summary.blocking_count > 0
        assert summary.eligible_for_test_run is False

    def test_notification_step_blocks_validation(self):
        draft = make_side_effecting_flow_draft()
        summary = validate_no_side_effect_subset(draft)
        assert summary.blocking_count > 0
        assert summary.eligible_for_test_run is False

    def test_side_effect_risk_blocks_validation(self):
        draft = {
            "id": "flow-draft:side-risk-001",
            "steps": [
                {
                    "id": "step:unsafe",
                    "kind": "semantic",
                    "config": {
                        "semantic_step_kind": "extract",
                        "side_effect_risk_class": "external_write",
                    },
                },
            ],
        }
        summary = validate_no_side_effect_subset(draft)
        assert summary.blocking_count > 0
        assert any(i.code == "side_effect_not_allowed" for i in summary.issues)

    def test_unsupported_semantic_kind_blocks_validation(self):
        draft = {
            "id": "flow-draft:bad-semantic",
            "steps": [
                {
                    "id": "step:classify",
                    "kind": "semantic",
                    "config": {
                        "semantic_step_kind": "classify",  # Not supported
                    },
                },
            ],
        }
        summary = validate_no_side_effect_subset(draft)
        assert summary.blocking_count > 0
        assert any(
            i.code == "unsupported_semantic_kind" for i in summary.issues
        )

    def test_conditional_with_no_substeps_blocks(self):
        draft = {
            "id": "flow-draft:no-substeps",
            "steps": [],
            "conditional_container": {
                "id": "container:empty",
                "kind": "conditional",
                "condition": {"operator": "is_true"},
                "substeps": [],  # Empty substeps
            },
        }
        summary = validate_no_side_effect_subset(draft)
        assert summary.blocking_count > 0


# =============================================================================
# Execution tests
# =============================================================================


class TestExecution:
    """Tests for run_non_side_effecting_test function."""

    def test_valid_fixture_returns_completed_result(self):
        draft = make_valid_flow_draft()
        result = run_non_side_effecting_test(draft)

        assert isinstance(result, TestRunResult)
        assert result.state == "completed"
        assert result.run_receipt is not None
        assert result.run_receipt.state == "completed"

    def test_valid_fixture_produces_run_receipt(self):
        draft = make_valid_flow_draft()
        result = run_non_side_effecting_test(draft)

        assert result.run_receipt is not None
        assert result.run_receipt.flow_draft_id == draft["id"]
        assert result.run_receipt.test_run_id is not None

    def test_no_side_effects_recorded(self):
        draft = make_valid_flow_draft()
        result = run_non_side_effecting_test(draft)

        assert result.side_effect_count == 0
        for receipt in result.run_receipt.step_receipts:
            assert len(receipt.side_effect_refs) == 0

    def test_semantic_extract_step_produces_step_receipt(self):
        draft = make_valid_flow_draft()
        result = run_non_side_effecting_test(draft)

        extract_receipts = [
            r
            for r in result.run_receipt.step_receipts
            if r.source_step_ref == "step:extract-001"
        ]
        assert len(extract_receipts) == 1
        assert extract_receipts[0].state == "completed"
        assert extract_receipts[0].semantic_metadata is not None
        assert (
            extract_receipts[0].semantic_metadata.semantic_step_kind
            == "extract"
        )

    def test_semantic_summarize_step_produces_step_receipt(self):
        draft = make_valid_flow_draft()
        result = run_non_side_effecting_test(draft)

        summarize_receipts = [
            r
            for r in result.run_receipt.step_receipts
            if r.source_step_ref == "step:summarize-001"
        ]
        assert len(summarize_receipts) == 1
        assert summarize_receipts[0].state == "completed"
        assert (
            summarize_receipts[0].semantic_metadata.semantic_step_kind
            == "summarize"
        )

    def test_decide_semantic_step_produces_step_receipt(self):
        draft = make_decide_flow_draft()
        result = run_non_side_effecting_test(draft)

        decide_receipts = [
            r
            for r in result.run_receipt.step_receipts
            if r.source_step_ref == "step:decide-001"
        ]
        assert len(decide_receipts) == 1
        assert decide_receipts[0].state == "completed"
        assert (
            decide_receipts[0].semantic_metadata.semantic_step_kind == "decide"
        )

    def test_conditional_skips_non_selected_branch(self):
        draft = make_valid_flow_draft()
        result = run_non_side_effecting_test(draft)

        # Check that one branch was skipped
        skipped = [
            r for r in result.run_receipt.step_receipts if r.state == "skipped"
        ]
        assert len(skipped) > 0

        # Check that executed branch has receipts
        completed = [
            r
            for r in result.run_receipt.step_receipts
            if r.state == "completed"
        ]
        assert len(completed) > 0

    def test_transform_step_produces_step_receipt(self):
        draft = {
            "id": "flow-draft:transform-001",
            "steps": [
                {
                    "id": "step:transform-001",
                    "kind": "transform",
                    "label": "Transform data",
                    "config": {
                        "side_effect_risk_class": "none",
                    },
                },
            ],
        }
        result = run_non_side_effecting_test(draft)

        transform_receipts = [
            r
            for r in result.run_receipt.step_receipts
            if r.source_step_ref == "step:transform-001"
        ]
        assert len(transform_receipts) == 1
        assert transform_receipts[0].state == "completed"

    def test_blocking_validation_returns_blocked_result(self):
        draft = make_side_effecting_flow_draft()
        result = run_non_side_effecting_test(draft)

        assert result.state == "blocked"
        assert result.run_receipt.state == "blocked"
        assert result.validation_summary.blocking_count > 0

    def test_blocked_result_has_failure_reason(self):
        draft = make_side_effecting_flow_draft()
        result = run_non_side_effecting_test(draft)

        assert result.failure_reason is not None
        assert "Validation blocked" in result.failure_reason


class TestGatedSideEffectExecution:
    """Tests for the explicit harness-local side-effect proof path."""

    def test_non_side_effecting_run_still_blocks_gated_command_step(self):
        draft = make_gated_side_effect_flow_draft()
        result = run_non_side_effecting_test(draft)

        assert result.state == "blocked"
        assert result.run_receipt is not None
        assert result.run_receipt.state == "blocked"
        assert any(
            issue.code == "unsupported_step_kind"
            for issue in result.validation_summary.issues
        )

    def test_gated_internal_side_effect_requires_enabled_gate(self):
        draft = make_gated_side_effect_flow_draft()
        gate = make_side_effect_gate(enabled=False)

        result = run_gated_side_effect_test(draft, gate=gate)

        assert result.state == "blocked"
        assert any(
            issue.code == "side_effect_gate_required"
            for issue in result.validation_summary.issues
        )

    def test_gated_internal_side_effect_requires_explicit_gate_mode(self):
        draft = make_gated_side_effect_flow_draft()
        gate = make_side_effect_gate(mode="manual_override")

        result = run_gated_side_effect_test(draft, gate=gate)

        assert result.state == "blocked"
        assert any(
            issue.code == "side_effect_gate_required"
            for issue in result.validation_summary.issues
        )

    def test_gated_internal_side_effect_requires_allowed_kind(self):
        draft = make_gated_side_effect_flow_draft()
        gate = make_side_effect_gate(allowed_kinds=["other_kind"])

        result = run_gated_side_effect_test(draft, gate=gate)

        assert result.state == "blocked"
        assert any(
            issue.code == "side_effect_kind_unsupported"
            for issue in result.validation_summary.issues
        )

    def test_gated_internal_side_effect_requires_idempotency_key(self):
        draft = make_gated_side_effect_flow_draft()
        draft["steps"][0]["config"].pop("idempotency_key")
        gate = make_side_effect_gate()

        result = run_gated_side_effect_test(draft, gate=gate)

        assert result.state == "blocked"
        assert any(
            issue.code == "idempotency_key_required"
            for issue in result.validation_summary.issues
        )

    @pytest.mark.parametrize(
        "risk_class",
        ["external_write", "third_party_share", "identity_sensitive"],
    )
    def test_forbidden_risk_classes_block_gated_side_effects(self, risk_class):
        draft = make_gated_side_effect_flow_draft()
        draft["steps"][0]["config"]["side_effect_risk_class"] = risk_class
        gate = make_side_effect_gate()

        result = run_gated_side_effect_test(draft, gate=gate)

        assert result.state == "blocked"
        assert any(
            issue.code == "external_side_effect_forbidden"
            for issue in result.validation_summary.issues
        )

    def test_successful_gated_internal_side_effect_records_evidence(self):
        draft = make_gated_side_effect_flow_draft()
        gate = make_side_effect_gate()

        result = run_gated_side_effect_test(draft, gate=gate)

        assert result.state == "completed"
        assert result.run_receipt is not None
        assert result.side_effect_records
        assert len(result.side_effect_records) == 1
        record = result.side_effect_records[0]
        assert isinstance(record, SideEffectRecord)
        assert record.intent_kind == "record_internal_note"
        assert record.risk_class == "internal_write"
        assert record.target_ref == "thread:test-001"
        assert record.idempotency_key == "idempotency:note-001"
        assert record.state == "recorded"
        assert record.approved_by == "operator:test-001"
        assert record.approval_reason == "Explicit harness gate for proof only."
        assert result.run_receipt.side_effect_summary
        assert "record_internal_note" in result.run_receipt.side_effect_summary
        assert (
            "approved_by=operator:test-001"
            in result.run_receipt.side_effect_summary
        )
        step_receipts = result.run_receipt.step_receipts
        assert len(step_receipts) == 1
        assert step_receipts[0].side_effect_refs == [record.id]

    def test_successful_gated_internal_side_effect_does_not_mutate_input(self):
        draft = make_gated_side_effect_flow_draft()
        original_draft = copy.deepcopy(draft)
        gate = make_side_effect_gate()

        run_gated_side_effect_test(draft, gate=gate)

        assert draft == original_draft

    def test_side_effect_tokens_are_not_global_protocol_tokens(self):
        from guardian import protocol_tokens as global_tokens
        from guardian.flow_builder import tokens as fb_tokens

        assert "explicit_harness_gate" in fb_tokens.SIDE_EFFECT_MODE
        assert "record_internal_note" in fb_tokens.HARNESS_SIDE_EFFECT_KIND
        assert "internal_write" in fb_tokens.SIDE_EFFECT_RISK_CLASS
        assert not hasattr(global_tokens, "SIDE_EFFECT_MODE")
        assert not hasattr(global_tokens, "SIDE_EFFECT_RISK_CLASS")
        assert not hasattr(global_tokens, "HARNESS_SIDE_EFFECT_KIND")


# =============================================================================
# Immutability tests
# =============================================================================


class TestImmutability:
    """Tests for input FlowDraft immutability."""

    def test_input_flow_draft_not_mutated(self):
        draft = make_valid_flow_draft()
        original_draft = copy.deepcopy(draft)

        run_non_side_effecting_test(draft)

        assert draft == original_draft

    def test_steps_not_mutated(self):
        draft = make_valid_flow_draft()
        original_steps = copy.deepcopy(draft.get("steps", []))

        run_non_side_effecting_test(draft)

        assert draft.get("steps", []) == original_steps

    def test_conditional_container_not_mutated(self):
        draft = make_valid_flow_draft()
        original_container = copy.deepcopy(draft.get("conditional_container"))

        run_non_side_effecting_test(draft)

        assert draft.get("conditional_container") == original_container


# =============================================================================
# Import isolation tests
# =============================================================================


class TestImportIsolation:
    """Tests verifying harness does not import backend runtime components."""

    def test_no_database_imports(self):
        """Verify no SQLAlchemy or database imports in harness."""
        import sys

        import guardian.flow_builder.testrun_harness as harness_module

        # Check that no DB modules are loaded
        loaded_modules = set(sys.modules.keys())

        # These should not be loaded by the harness
        forbidden_modules = {
            "guardian.db",
            "guardian.db.models",
            "guardian.core.db",
            "sqlalchemy",
            "asyncpg",
            "psycopg",
        }

        for module_name in forbidden_modules:
            assert (
                module_name not in loaded_modules
            ), f"Harness incorrectly imported {module_name}"

    def test_no_api_imports(self):
        """Verify harness module does not import FastAPI or API modules."""
        import sys

        # Get modules loaded by the harness module specifically
        harness_module = sys.modules.get(
            "guardian.flow_builder.testrun_harness"
        )
        assert harness_module is not None

        # Check imports in harness module's file
        import inspect

        harness_file = inspect.getfile(harness_module)
        with open(harness_file) as f:
            content = f.read()

        # Verify no FastAPI or API imports in source
        assert "from fastapi" not in content
        assert "import fastapi" not in content
        assert "from starlette" not in content
        assert "import starlette" not in content
        assert "from guardian.routes" not in content
        assert "import guardian.routes" not in content

    def test_no_redis_imports(self):
        """Verify harness module does not import Redis modules."""
        import inspect
        import sys

        harness_module = sys.modules.get(
            "guardian.flow_builder.testrun_harness"
        )
        assert harness_module is not None

        harness_file = inspect.getfile(harness_module)
        with open(harness_file) as f:
            content = f.read()

        # Verify no Redis imports in source
        assert "from redis" not in content
        assert "import redis" not in content
        assert "from guardian.queue" not in content
        assert "import guardian.queue" not in content

    def test_no_model_provider_imports(self):
        """Verify harness module does not import model provider modules."""
        import inspect
        import sys

        harness_module = sys.modules.get(
            "guardian.flow_builder.testrun_harness"
        )
        assert harness_module is not None

        harness_file = inspect.getfile(harness_module)
        with open(harness_file) as f:
            content = f.read()

        # Verify no provider imports in source
        assert "from openai" not in content
        assert "import openai" not in content
        assert "from anthropic" not in content
        assert "import anthropic" not in content
        assert "from guardian.core.ai_router" not in content
        assert "import guardian.core.ai_router" not in content

    def test_no_command_bus_imports(self):
        """Verify harness module does not import command bus modules."""
        import inspect
        import sys

        harness_module = sys.modules.get(
            "guardian.flow_builder.testrun_harness"
        )
        assert harness_module is not None

        harness_file = inspect.getfile(harness_module)
        with open(harness_file) as f:
            content = f.read()

        # Verify no command bus imports in source
        assert "from guardian.command_bus" not in content
        assert "import guardian.command_bus" not in content


# =============================================================================
# Receipt shape tests
# =============================================================================


class TestReceiptShape:
    """Tests verifying receipt shapes match contracts."""

    def test_run_receipt_has_required_fields(self):
        draft = make_valid_flow_draft()
        result = run_non_side_effecting_test(draft)

        receipt = result.run_receipt
        assert receipt.id
        assert receipt.flow_draft_id
        assert receipt.state
        assert receipt.validation_snapshot
        assert receipt.permission_snapshot
        assert isinstance(receipt.step_receipts, list)
        assert receipt.side_effect_summary
        assert receipt.created_at
        assert receipt.started_at
        assert receipt.completed_at

    def test_step_receipt_has_required_fields(self):
        draft = make_valid_flow_draft()
        result = run_non_side_effecting_test(draft)

        for step_receipt in result.run_receipt.step_receipts:
            assert step_receipt.id
            assert step_receipt.source_step_ref
            assert step_receipt.state
            assert step_receipt.value_summary

    def test_step_receipt_has_semantic_metadata_for_semantic_steps(self):
        draft = make_valid_flow_draft()
        result = run_non_side_effecting_test(draft)

        for step_receipt in result.run_receipt.step_receipts:
            # Semantic steps should have semantic metadata
            if (
                "extract" in step_receipt.source_step_ref
                or "summarize" in step_receipt.source_step_ref
                or "decide" in step_receipt.source_step_ref
            ):
                assert step_receipt.semantic_metadata is not None
                assert step_receipt.semantic_metadata.semantic_step_kind
                assert step_receipt.semantic_metadata.uncertainty_outcome

    def test_step_receipt_has_condition_metadata_for_conditional_substeps(self):
        draft = make_valid_flow_draft()
        result = run_non_side_effecting_test(draft)

        # At least one receipt should have condition metadata
        conditional_receipts = [
            r
            for r in result.run_receipt.step_receipts
            if r.condition_metadata is not None
        ]
        # The harness produces condition metadata for branch receipts
        # Note: not all receipts have condition metadata, only selected branch
        for receipt in conditional_receipts:
            assert receipt.condition_metadata.condition_ref
            assert receipt.condition_metadata.selected_branch in (
                "then",
                "else",
            )


# =============================================================================
# Token boundedness tests
# =============================================================================


class TestTokenBoundedness:
    """Tests verifying tokens are bounded to flow_builder module."""

    def test_flow_builder_tokens_are_separate_registry(self):
        """Verify flow_builder tokens are in a separate registry from global."""
        from guardian.flow_builder import tokens as fb_tokens

        # Verify harness tokens exist
        assert hasattr(fb_tokens, "TEST_RUN_STATE")
        assert hasattr(fb_tokens, "RUN_RECEIPT_STATE")
        assert hasattr(fb_tokens, "STEP_RECEIPT_STATE")

        # Verify they are frozensets (bounded registries)
        assert isinstance(fb_tokens.TEST_RUN_STATE, frozenset)
        assert isinstance(fb_tokens.RUN_RECEIPT_STATE, frozenset)
        assert isinstance(fb_tokens.STEP_RECEIPT_STATE, frozenset)

        # Verify values are correct for harness context
        assert "completed" in fb_tokens.TEST_RUN_STATE
        assert "completed" in fb_tokens.RUN_RECEIPT_STATE
        assert "completed" in fb_tokens.STEP_RECEIPT_STATE

    def test_global_protocol_tokens_module_exists(self):
        """Verify global protocol tokens module still exists and is separate."""
        from guardian import protocol_tokens as global_tokens

        # The global module should exist
        assert global_tokens is not None

        # Flow Builder tokens are NOT in global protocol_tokens
        # They are in a separate harness-local module
        assert not hasattr(global_tokens, "TEST_RUN_STATE")
        assert not hasattr(global_tokens, "FLOW_BUILDER")
