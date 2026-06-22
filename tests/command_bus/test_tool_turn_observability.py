"""Tests for tool-turn observability read-model helper."""

from __future__ import annotations

from typing import Any

from guardian.command_bus.tool_turn_observability import (
    ToolTurnObservabilityReadModel,
    build_tool_turn_observability_read_model,
    _summarize_result,
    _summarize_error,
    _extract_canonical_field,
)


class TestCanonicalFieldExtraction:
    def test_camelcase_wins_over_snake_case(self) -> None:
        meta = {"messageId": "msg-camel", "message_id": "msg-snake"}
        result = _extract_canonical_field(meta, "messageId", "message_id")
        assert result == "msg-camel"

    def test_falls_back_to_snake_case(self) -> None:
        meta = {"message_id": "msg-snake"}
        result = _extract_canonical_field(meta, "messageId", "message_id")
        assert result == "msg-snake"

    def test_returns_none_for_missing(self) -> None:
        assert _extract_canonical_field({}, "messageId", "message_id") is None
        assert _extract_canonical_field(None, "messageId", "message_id") is None


class TestBuildFromExtraMeta:
    def test_builds_read_model_from_camelcase_extra_meta(self) -> None:
        meta = {
            "messageId": "msg-1",
            "requestId": "req-1",
            "toolTurnId": "tt-1",
            "toolTurnState": "completed",
            "loopStopReason": "tool_turn_completed",
            "commandRunId": "run-1",
        }
        model = build_tool_turn_observability_read_model(assistant_extra_meta=meta)

        assert model.message_id == "msg-1"
        assert model.request_id == "req-1"
        assert model.tool_turn_id == "tt-1"
        assert model.tool_turn_state == "completed"
        assert model.loop_stop_reason == "tool_turn_completed"
        assert model.command_run_id == "run-1"
        assert model.evidence_durability == "durable"

    def test_snake_case_fallback(self) -> None:
        meta = {
            "message_id": "msg-1",
            "request_id": "req-1",
            "tool_turn_id": "tt-1",
            "tool_turn_state": "completed",
            "loop_stop_reason": "tool_turn_completed",
            "command_run_id": "run-1",
        }
        model = build_tool_turn_observability_read_model(assistant_extra_meta=meta)
        assert model.tool_turn_id == "tt-1"
        assert model.command_run_id == "run-1"


class TestCommandRunEnrichment:
    def test_enriches_from_mapping(self) -> None:
        meta = {"toolTurnId": "tt-1", "commandRunId": "run-1"}
        cr = {
            "run_id": "run-1",
            "command_id": "op::health_health_get",
            "status": "completed",
            "result_json": {"body": {"status": "ok", "service": "core"}},
            "error_text": None,
            "created_at": "2026-01-01T00:00:00Z",
        }
        model = build_tool_turn_observability_read_model(
            assistant_extra_meta=meta, command_run=cr
        )
        assert model.command_id == "op::health_health_get"
        assert model.command_status == "completed"
        assert model.command_result_summary == "ok"
        assert model.command_error_summary is None
        assert model.created_at == "2026-01-01T00:00:00Z"
        assert model.evidence_durability == "durable"

    def test_enriches_from_orm_object(self) -> None:
        class FakeCommandRun:
            run_id = "run-2"
            command_id = "op::health_check"
            status = "failed"
            result_json = {"body": {"message": "something broke"}}
            error_text = "timeout"
            created_at = "2026-01-02T00:00:00Z"
            updated_at = "2026-01-02T01:00:00Z"

        model = build_tool_turn_observability_read_model(
            assistant_extra_meta={"toolTurnId": "tt-2"},
            command_run=FakeCommandRun(),
        )
        assert model.command_id == "op::health_check"
        assert model.command_status == "failed"
        assert model.command_result_summary == "something broke"
        assert model.command_error_summary == "timeout"
        assert model.created_at == "2026-01-02T00:00:00Z"
        assert model.updated_at == "2026-01-02T01:00:00Z"

    def test_prefers_extra_meta_command_run_id(self) -> None:
        meta = {"commandRunId": "run-meta"}
        cr = {"run_id": "run-cr"}
        model = build_tool_turn_observability_read_model(
            assistant_extra_meta=meta, command_run=cr
        )
        assert model.command_run_id == "run-meta"

    def test_falls_back_to_cr_run_id(self) -> None:
        meta: dict[str, Any] = {}
        cr = {"run_id": "run-cr"}
        model = build_tool_turn_observability_read_model(
            assistant_extra_meta=meta, command_run=cr
        )
        assert model.command_run_id == "run-cr"

    def test_blocked_status_sets_reason(self) -> None:
        cr = {"run_id": "run-3", "status": "blocked"}
        model = build_tool_turn_observability_read_model(
            assistant_extra_meta={}, command_run=cr
        )
        assert model.command_blocked_reason is not None
        assert "blocked" in model.command_blocked_reason.lower()


class TestReceiptEnrichment:
    def test_receipt_ids_and_latest_set(self) -> None:
        model = build_tool_turn_observability_read_model(
            assistant_extra_meta={"toolTurnId": "tt-1"},
            receipt_ids=["rec-1", "rec-2"],
            latest_receipt_id="rec-2",
        )
        assert model.receipt_ids == ("rec-1", "rec-2")
        assert model.latest_receipt_id == "rec-2"
        assert model.evidence_durability == "receipt_enriched"


class TestRedactionAndSafety:
    def test_does_not_expose_raw_args(self) -> None:
        cr = {
            "run_id": "run-4",
            "result_json": {
                "body": {"raw_args": "SECRET_ARGS", "password": "hunter2"}
            },
        }
        model = build_tool_turn_observability_read_model(
            assistant_extra_meta={}, command_run=cr
        )
        summary = (model.command_result_summary or "").lower()
        assert "secret_args" not in summary
        assert "hunter2" not in summary

    def test_does_not_expose_secrets_in_error(self) -> None:
        cr = {"error_text": "Failed with secret: abc123 token: xyz"}
        model = build_tool_turn_observability_read_model(
            assistant_extra_meta={}, command_run=cr
        )
        assert model.command_error_summary is not None
        assert "abc123" not in (model.command_error_summary or "")

    def test_does_not_expose_local_surrogate_ids(self) -> None:
        cr = {"id": 99999, "run_id": "run-stable"}
        model = build_tool_turn_observability_read_model(
            assistant_extra_meta={}, command_run=cr
        )
        assert model.command_run_id == "run-stable"

    def test_redaction_summary_present(self) -> None:
        model = build_tool_turn_observability_read_model(assistant_extra_meta={})
        rs = model.redaction_summary
        assert rs["raw_args_rendered"] is False
        assert rs["secrets_rendered"] is False
        assert rs["prompts_rendered"] is False
        assert rs["unredacted_payload_rendered"] is False
        assert rs["local_surrogate_ids_rendered"] is False


class TestMissingEvidence:
    def test_empty_inputs_return_safe_model(self) -> None:
        model = build_tool_turn_observability_read_model(assistant_extra_meta={})
        assert model.message_id is None
        assert model.tool_turn_id is None
        assert model.evidence_durability == "unknown"

    def test_none_inputs_return_safe_model(self) -> None:
        model = build_tool_turn_observability_read_model(assistant_extra_meta=None)
        assert model.message_id is None
        assert model.evidence_durability == "unknown"


class TestResultSummarizer:
    def test_summarizes_safe_body(self) -> None:
        assert _summarize_result({"body": {"status": "ok"}}) == "ok"

    def test_handles_string_result(self) -> None:
        assert _summarize_result("short result") == "short result"

    def test_handles_long_result(self) -> None:
        long_str = "x" * 300
        summary = _summarize_result(long_str)
        assert summary is not None
        assert "CommandRun readback" in (summary or "")

    def test_handles_none(self) -> None:
        assert _summarize_result(None) is None


class TestErrorSummarizer:
    def test_handles_short_safe_error(self) -> None:
        assert _summarize_error("timeout") == "timeout"

    def test_redacts_long_error(self) -> None:
        long_err = "x" * 600
        assert _summarize_error(long_err) == "Command failed; details redacted."

    def test_handles_none(self) -> None:
        assert _summarize_error(None) is None
