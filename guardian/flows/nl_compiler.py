"""Two-stage NL -> FlowSpec compiler with confirmation gating."""

from __future__ import annotations

import re
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from guardian.flows.compiler import compile_flow
from guardian.flows.spec import CompiledFlow, FlowSpec


class DraftFlowResult(BaseModel):
    """Stage-1 draft produced from natural language input."""

    source_text: str
    draft_flow_spec: dict[str, Any]
    confidence: float = Field(ge=0.0, le=1.0)
    clarifying_questions: list[str] = Field(default_factory=list)

    model_config = ConfigDict(extra="forbid")


class GatedCompileResult(BaseModel):
    """Stage-2 compiled output with explicit confirmation gating."""

    draft_flow_spec: dict[str, Any]
    compiled_flow: CompiledFlow
    confidence: float = Field(ge=0.0, le=1.0)
    clarifying_questions: list[str] = Field(default_factory=list)
    needs_confirmation: bool = False
    warnings: list[str] = Field(default_factory=list)
    summary: str
    diff: list[str] = Field(default_factory=list)

    model_config = ConfigDict(extra="forbid")


def _slugify(text: str) -> str:
    base = re.sub(r"[^a-zA-Z0-9]+", "_", text.strip().lower()).strip("_")
    if not base:
        base = "flow"
    return f"{base[:48]}_v1"


def _infer_trigger(text_lower: str) -> dict[str, Any]:
    if "every morning" in text_lower or "every day" in text_lower or "daily" in text_lower:
        return {"type": "cron", "schedule": "0 7 * * *", "event_name": None}
    if "every friday" in text_lower or "weekly" in text_lower:
        return {"type": "cron", "schedule": "0 9 * * FRI", "event_name": None}
    if text_lower.startswith("when ") or " on event " in text_lower:
        return {"type": "event", "schedule": None, "event_name": "flow.event.triggered"}
    return {"type": "manual", "schedule": None, "event_name": None}


def _contains_side_effect_request(text_lower: str) -> bool:
    side_effect_markers = (
        "save",
        "write",
        "post",
        "create thread",
        "append",
        "emit event",
        "codex entry",
    )
    return any(marker in text_lower for marker in side_effect_markers)


def _infer_steps(text: str) -> list[dict[str, Any]]:
    text_lower = text.lower()
    steps: list[dict[str, Any]] = [
        {
            "step_id": "ctx",
            "primitive": "assemble_context",
            "params": {
                "intent": text,
                "sources": {"threads": True, "memory": True, "codex": True},
                "window": {"threads_days": 14, "memory_days": 30, "codex_days": 30},
                "search_depth": 2,
                "max_items": 50,
            },
        }
    ]

    if "classify" in text_lower or "categorize" in text_lower:
        steps.append(
            {
                "step_id": "classify",
                "primitive": "classify",
                "params": {
                    "schema_name": "nl_classification_v1",
                    "labels": ["important", "neutral", "ignore"],
                    "instructions": ["Classify major points from context."],
                },
            }
        )
    else:
        steps.append(
            {
                "step_id": "summarize",
                "primitive": "summarize",
                "params": {
                    "schema_name": "nl_summary_v1",
                    "instructions": [
                        "Summarize relevant context.",
                        "Label speculation as speculation.",
                    ],
                },
            }
        )

    if "action" in text_lower or "next step" in text_lower:
        steps.append(
            {
                "step_id": "actions",
                "primitive": "extract_actions",
                "params": {
                    "schema_name": "nl_actions_v1",
                    "max_actions": 3,
                    "actionable_definition": [
                        "Start with a verb",
                        "Be specific and feasible",
                    ],
                },
            }
        )

    if _contains_side_effect_request(text_lower):
        steps.append(
            {
                "step_id": "post_thread",
                "primitive": "create_thread",
                "params": {
                    "title_template": "Flow Output - {{date}}",
                    "body_template": {
                        "format": "markdown",
                        "sections": [{"title": "Result", "from_step": steps[-1]["step_id"]}],
                    },
                },
            }
        )

    if "event" in text_lower:
        steps.append(
            {
                "step_id": "emit",
                "primitive": "emit_event",
                "params": {
                    "event_name": "codexify.flow.generated",
                    "payload_from_steps": [steps[-1]["step_id"]],
                },
            }
        )

    return steps


def _clarifying_questions(text: str, trigger: dict[str, Any], side_effects: bool) -> list[str]:
    text_lower = text.lower()
    questions: list[str] = []
    if trigger["type"] == "cron" and all(token not in text_lower for token in ("7:", "8:", "9:", "am", "pm")):
        questions.append("What exact time should this scheduled flow run in your timezone?")
    if trigger["type"] == "manual" and any(token in text_lower for token in ("daily", "weekly", "every ")):
        questions.append("Should this flow be scheduled or stay manual?")
    if side_effects and "thread" not in text_lower and "codex" not in text_lower:
        questions.append("Where should side effects be written (thread, codex, both, or none)?")
    if len(text.split()) < 6:
        questions.append("Can you provide more detail on the desired output format?")
    return questions


def _estimate_confidence(text: str, trigger: dict[str, Any], questions: list[str]) -> float:
    score = 0.55
    if trigger["type"] != "manual":
        score += 0.15
    if len(text.split()) >= 8:
        score += 0.15
    score -= 0.08 * len(questions)
    return max(0.0, min(1.0, round(score, 2)))


def draft_flow_from_text(
    text: str,
    user_context: dict[str, Any] | None = None,
) -> DraftFlowResult:
    """Stage 1: draft FlowSpec + confidence + clarifying questions."""
    normalized_text = text.strip()
    text_lower = normalized_text.lower()
    trigger = _infer_trigger(text_lower)
    side_effects = _contains_side_effect_request(text_lower)
    questions = _clarifying_questions(normalized_text, trigger, side_effects)
    confidence = _estimate_confidence(normalized_text, trigger, questions)

    context = user_context or {}
    flow_id = _slugify(normalized_text)
    steps = _infer_steps(normalized_text)

    draft_spec: dict[str, Any] = {
        "flow_id": flow_id,
        "version": "0.1",
        "enabled": True,
        "trigger": trigger,
        "scope": {
            "user_id": str(context.get("user_id", "default")),
            "project_ids": list(context.get("project_ids", [])),
            "thread_ids": list(context.get("thread_ids", [])),
            "persona": context.get("persona", "guardian.flow_builder"),
        },
        "budget": {"max_steps": 12, "max_tokens": 5000, "timeout_seconds": 180},
        "policy": {
            "min_confidence": 0.75,
            "require_confirmation_below_threshold": True,
            "allow_side_effects_without_confirmation": not side_effects,
        },
        "steps": steps,
        "output": {
            "store_as_thread": side_effects,
            "store_as_codex": "codex" in text_lower,
            "emit_event": None,
        },
        "idempotency": {
            "key_template": f"{flow_id}::{{date}}",
            "mode": "return_cached",
        },
        "audit": {
            "log_trace": True,
            "record_cost": True,
            "redact_fields": ["api_key", "authorization", "cookie"],
        },
    }

    return DraftFlowResult(
        source_text=normalized_text,
        draft_flow_spec=draft_spec,
        confidence=confidence,
        clarifying_questions=questions,
    )


def _build_diff(draft_flow_spec: dict[str, Any], compiled_flow: CompiledFlow) -> list[str]:
    draft_normalized = FlowSpec.model_validate(draft_flow_spec).model_dump(mode="json")
    compiled_dump = compiled_flow.model_dump(mode="json")
    lines: list[str] = []
    for key in ("trigger", "budget", "policy", "steps", "output", "idempotency", "audit"):
        if draft_normalized.get(key) != compiled_dump.get(key):
            lines.append(f"{key}: normalized by compiler")
    if not lines:
        lines.append("No normalization differences detected between draft and compiled flow.")
    return lines


def _build_summary(
    draft: DraftFlowResult,
    compiled: CompiledFlow,
    needs_confirmation: bool,
) -> str:
    return (
        f"Drafted flow '{compiled.flow_id}' with {len(compiled.steps)} steps, "
        f"trigger '{compiled.trigger.type}', confidence {draft.confidence:.2f}, "
        f"needs_confirmation={str(needs_confirmation).lower()}."
    )


def compile_draft_with_gating(
    draft: DraftFlowResult | dict[str, Any],
    confidence_threshold: float | None = None,
) -> GatedCompileResult:
    """Stage 2: compile draft and apply confidence/warning gating."""
    draft_result = (
        draft if isinstance(draft, DraftFlowResult) else DraftFlowResult.model_validate(draft)
    )
    compiled = compile_flow(draft_result.draft_flow_spec)
    threshold = confidence_threshold if confidence_threshold is not None else compiled.policy.min_confidence
    warnings = [warning.message for warning in compiled.warnings]
    needs_confirmation = draft_result.confidence < threshold or bool(warnings)

    if needs_confirmation:
        compiled = compiled.model_copy(update={"requires_confirmation": True})

    return GatedCompileResult(
        draft_flow_spec=draft_result.draft_flow_spec,
        compiled_flow=compiled,
        confidence=draft_result.confidence,
        clarifying_questions=draft_result.clarifying_questions,
        needs_confirmation=needs_confirmation,
        warnings=warnings,
        summary=_build_summary(draft_result, compiled, needs_confirmation),
        diff=_build_diff(draft_result.draft_flow_spec, compiled),
    )


def propose_flow_from_text(
    text: str,
    user_context: dict[str, Any] | None = None,
    confidence_threshold: float | None = None,
) -> GatedCompileResult:
    """Convenience helper running stage-1 draft + stage-2 compile/gating."""
    draft = draft_flow_from_text(text=text, user_context=user_context)
    return compile_draft_with_gating(draft, confidence_threshold=confidence_threshold)
