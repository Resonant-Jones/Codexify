"""Minimal, dependency-light context assembly broker for enriching chat completions."""

import logging
import os
from typing import Any, Dict, List, Optional, Sequence, Tuple, TypedDict

import requests

from guardian.context.memory_preselector import (
    MemoryCandidateHeader,
    MemoryPreselectorRequest,
    select_memory_candidates,
)
from guardian.context.retrieval_router_policy import (
    SOURCE_MODE_CONVERSATION,
    SOURCE_MODE_OBSIDIAN_ONLY,
    SOURCE_MODE_PERSONAL_KNOWLEDGE,
    SOURCE_MODE_PROJECT,
    SOURCE_MODE_WORKSPACE,
    WIDEN_REASON_EXPLICIT_PERSONAL_KNOWLEDGE,
    WIDEN_REASON_EXPLICIT_WORKSPACE,
    WIDEN_REASON_INSUFFICIENT_THREAD_HITS,
    WIDEN_REASON_LOW_CONFIDENCE_THREAD_HITS,
    WIDEN_REASON_NONE,
    normalize_source_mode,
    normalize_widen_reason,
    resolve_context_assembly_policy,
    source_mode_boundary_label,
)
from guardian.context.tool_intents import (
    ToolIntentParseError,
    ToolRisk,
    classify_tool_intent,
    parse_tool_intents,
    redact_tool_intent_dict,
)
from guardian.core.config import Settings, get_settings
from guardian.memoryos.retriever import MemoryOSRetriever
from guardian.obsidian.indexer import OBSIDIAN_NAMESPACE
from guardian.protocol_tokens import (
    PersonalFactStatus,
    TraceSnapshotAbsenceReason,
)

logger = logging.getLogger(__name__)
_OBSIDIAN_CONNECTOR_NAME = "obsidian_local"
_LOW_CONFIDENCE_SCORE_THRESHOLD = 0.1
_THREAD_CANDIDATE_LIMIT = 500
_PERSONAL_FACT_LIMIT = 12
_WORKSPACE_RETRIEVAL_PROBE_TIMEOUT_SECONDS = 5.0
_WORKSPACE_RETRIEVAL_PROBE_BASE_URL_ENV = "GUARDIAN_COMMAND_BUS_LOOPBACK_BASE"


class EffectiveRetrievalPolicy(TypedDict):
    source_mode: str
    widening_enabled: bool
    identity_scope: str


def _identity_scope_for_source_mode(source_mode: str) -> str:
    normalized_source_mode = normalize_source_mode(source_mode)
    if normalized_source_mode == SOURCE_MODE_CONVERSATION:
        return "thread"
    return normalized_source_mode


def derive_default_retrieval_policy(
    source_mode: str,
) -> EffectiveRetrievalPolicy:
    normalized_source_mode = normalize_source_mode(source_mode)
    return {
        "source_mode": normalized_source_mode,
        "widening_enabled": normalized_source_mode
        not in {SOURCE_MODE_CONVERSATION, SOURCE_MODE_OBSIDIAN_ONLY},
        "identity_scope": _identity_scope_for_source_mode(
            normalized_source_mode
        ),
    }


def merge_retrieval_policy(
    base_policy: EffectiveRetrievalPolicy,
    retrieval_override: dict[str, Any] | None,
) -> EffectiveRetrievalPolicy:
    policy = dict(base_policy)

    if policy.get("source_mode") == SOURCE_MODE_OBSIDIAN_ONLY:
        policy["widening_enabled"] = False
        policy["identity_scope"] = SOURCE_MODE_OBSIDIAN_ONLY
        return policy  # type: ignore[return-value]

    if not retrieval_override:
        return policy  # type: ignore[return-value]

    mode = str(retrieval_override.get("mode") or "").strip().lower()
    if mode == "conversation":
        policy["source_mode"] = "thread"
        policy["widening_enabled"] = False
        policy["identity_scope"] = "thread"
    elif mode == "project":
        policy["source_mode"] = SOURCE_MODE_PROJECT
        policy["widening_enabled"] = True
        policy["identity_scope"] = SOURCE_MODE_PROJECT
    elif mode == "personal_knowledge":
        policy["source_mode"] = SOURCE_MODE_PERSONAL_KNOWLEDGE
        policy["widening_enabled"] = True
        policy["identity_scope"] = SOURCE_MODE_PERSONAL_KNOWLEDGE
    elif mode == "workspace":
        policy["source_mode"] = SOURCE_MODE_WORKSPACE
        policy["widening_enabled"] = True
        policy["identity_scope"] = SOURCE_MODE_WORKSPACE

    return policy  # type: ignore[return-value]


def _append_retrieval_warning(context: Dict[str, Any], warning: str) -> None:
    warnings = context.get("retrieval_warnings")
    if not isinstance(warnings, list):
        warnings = []
    warnings.append(warning)
    context["retrieval_warnings"] = warnings


def _build_policy_suppression_summary(
    *,
    thread_id: int,
    project_id: Optional[int],
    retrieval_policy: dict[str, Any] | None,
) -> dict[str, Any] | None:
    if not isinstance(retrieval_policy, dict):
        return None

    source_mode = str(retrieval_policy.get("source_mode") or "").strip().lower()
    if not source_mode:
        return None

    boundary_label = str(
        retrieval_policy.get("boundary_label")
        or source_mode_boundary_label(source_mode)
    ).strip()
    allow_semantic_widening = bool(
        retrieval_policy.get("allow_semantic_widening", True)
    )
    allow_thread_docs = bool(retrieval_policy.get("allow_thread_docs", True))
    allow_project_docs = bool(retrieval_policy.get("allow_project_docs", True))
    allow_global_widening = bool(
        retrieval_policy.get("allow_global_widening", True)
    )

    counts_by_reason: dict[str, int] = {}
    items: list[dict[str, Any]] = []

    blocked_scopes: list[tuple[str, str, bool]] = [
        (
            "thread_semantic",
            "thread_semantic_excluded_by_policy",
            allow_semantic_widening,
        ),
        ("thread_docs", "thread_docs_excluded_by_policy", allow_thread_docs),
        (
            "project_docs",
            "project_docs_excluded_by_policy",
            allow_project_docs,
        ),
        (
            "global_search",
            "global_search_excluded_by_policy",
            allow_global_widening,
        ),
    ]
    for lane, reason, allowed in blocked_scopes:
        if allowed:
            continue
        counts_by_reason[reason] = counts_by_reason.get(reason, 0) + 1
        items.append(
            {
                "id": f"policy:{lane}",
                "source_type": "policy",
                "role": "policy",
                "thread_id": thread_id,
                "project_id": project_id,
                "retrieval_lane": lane,
                "score": None,
                "policy_reason": boundary_label or source_mode,
                "retrieval_policy": dict(retrieval_policy),
                "suppressed": True,
                "suppression_reason": reason,
                "count": 1,
            }
        )

    if not counts_by_reason:
        return None

    return {
        "items": items,
        "counts_by_reason": counts_by_reason,
        "policy": {
            "source_mode": source_mode,
            "boundary_label": boundary_label,
            "allow_semantic_widening": allow_semantic_widening,
            "allow_thread_docs": allow_thread_docs,
            "allow_project_docs": allow_project_docs,
            "allow_global_widening": allow_global_widening,
        },
    }


def _workspace_retrieval_probe_base_url() -> str | None:
    base_url = str(
        os.getenv(_WORKSPACE_RETRIEVAL_PROBE_BASE_URL_ENV) or ""
    ).strip()
    return base_url.rstrip("/") or None


def _thread_namespace(thread_id: int) -> str:
    return f"thread:{thread_id}"


def _coerce_int(value: Any) -> Optional[int]:
    try:
        num = int(value)
    except (TypeError, ValueError):
        return None
    return num if num > 0 else None


def _is_verified_active_personal_fact(fact: Any) -> bool:
    if not isinstance(fact, dict):
        return False
    if str(fact.get("status") or "").strip().lower() != (
        PersonalFactStatus.VERIFIED.value
    ):
        return False
    if fact.get("is_active") is False:
        return False

    key = str(fact.get("key") or "").strip()
    value = str(fact.get("value") or "").strip()
    return bool(key and value)


def _coerce_graph_value(value: Any) -> Any:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, dict):
        return {
            str(key): _coerce_graph_value(item) for key, item in value.items()
        }
    if isinstance(value, (list, tuple, set)):
        return [_coerce_graph_value(item) for item in value]

    isoformat = getattr(value, "isoformat", None)
    if callable(isoformat):
        try:
            return isoformat()
        except Exception:
            pass

    to_native = getattr(value, "to_native", None)
    if callable(to_native):
        try:
            return _coerce_graph_value(to_native())
        except Exception:
            pass

    return str(value)


def _annotate_retrieval_item(item: Any, **fields: Any) -> Any:
    if not isinstance(item, dict):
        return item

    annotated = dict(item)
    for key, value in fields.items():
        if value is None:
            continue
        if key not in annotated or annotated.get(key) in (None, ""):
            annotated[key] = value
    return annotated


def _serialize_rag_trace_document(item: Any) -> dict[str, Any]:
    metadata = item.get("metadata") if isinstance(item, dict) else None
    if not isinstance(metadata, dict):
        metadata = {}
    score = 0.0
    if isinstance(item, dict):
        try:
            raw_score = item.get("score")
            if raw_score is not None:
                score = float(raw_score)
        except (TypeError, ValueError):
            score = 0.0
    return {
        "id": str(item.get("id", "")) if isinstance(item, dict) else "",
        "title": str(
            metadata.get("filename", "unknown")
            if isinstance(item, dict)
            else "unknown"
        ),
        "score": score,
        "snippet": (
            str(item.get("text", ""))[:100] + "..."
            if isinstance(item, dict)
            else "..."
        ),
        "source_type": str(
            item.get("source_type") or metadata.get("source_type") or ""
        ).strip()
        or None,
        "role": str(item.get("role") or metadata.get("role") or "").strip()
        or None,
        "thread_id": _coerce_int(
            item.get("thread_id") or metadata.get("thread_id")
        )
        if isinstance(item, dict)
        else None,
        "project_id": _coerce_int(
            item.get("project_id") or metadata.get("project_id")
        )
        if isinstance(item, dict)
        else None,
        "retrieval_lane": str(item.get("retrieval_lane") or "").strip()
        if isinstance(item, dict)
        else None,
        "policy_reason": str(item.get("policy_reason") or "").strip()
        if isinstance(item, dict)
        else None,
        "retrieval_policy": dict(item.get("retrieval_policy") or {})
        if isinstance(item, dict)
        else {},
    }


def _extract_result_user_id(item: Any) -> Optional[str]:
    if item is None:
        return None
    if isinstance(item, dict):
        for key in ("user_id", "owner_user_id", "actor_user_id"):
            value = item.get(key)
            if value not in (None, ""):
                return str(value).strip() or None
        metadata = item.get("metadata")
        if isinstance(metadata, dict):
            for key in ("user_id", "owner_user_id", "actor_user_id"):
                value = metadata.get(key)
                if value not in (None, ""):
                    return str(value).strip() or None
    for attr_name in ("user_id", "owner_user_id", "actor_user_id"):
        value = getattr(item, attr_name, None)
        if value not in (None, ""):
            return str(value).strip() or None
    return None


def _extract_result_namespace(item: Any) -> Optional[str]:
    if item is None:
        return None
    if isinstance(item, dict):
        for key in ("namespace", "vault_namespace"):
            value = item.get(key)
            if value not in (None, ""):
                return str(value).strip() or None
        metadata = item.get("metadata")
        if isinstance(metadata, dict):
            for key in ("namespace", "vault_namespace"):
                value = metadata.get(key)
                if value not in (None, ""):
                    return str(value).strip() or None
        meta = item.get("meta")
        if isinstance(meta, dict):
            for key in ("namespace", "vault_namespace"):
                value = meta.get(key)
                if value not in (None, ""):
                    return str(value).strip() or None
    for attr_name in ("namespace", "vault_namespace"):
        value = getattr(item, attr_name, None)
        if value not in (None, ""):
            return str(value).strip() or None
    return None


def _assert_user_scoped_results(
    results: list[Any], *, user_id: str
) -> list[Any]:
    normalized_user_id = str(user_id or "").strip()
    if not normalized_user_id:
        raise AssertionError("retrieval_user_isolation_violation")

    raw_results = list(results)
    if any(
        _extract_result_user_id(item) != normalized_user_id
        for item in raw_results
    ):
        raise AssertionError("retrieval_user_isolation_violation")

    filtered = [
        item
        for item in raw_results
        if _extract_result_user_id(item) == normalized_user_id
    ]
    if any(
        _extract_result_user_id(item) != normalized_user_id for item in filtered
    ):
        raise AssertionError("retrieval_user_isolation_violation")
    return filtered


def _workspace_backend_obsidian_results(
    *,
    query: str,
    user_id: str,
    k: int,
) -> list[dict[str, Any]]:
    base_url = _workspace_retrieval_probe_base_url()
    if not base_url:
        return []

    api_key = str(
        getattr(get_settings(), "GUARDIAN_API_KEY", None)
        or os.getenv("GUARDIAN_API_KEY")
        or ""
    ).strip()
    headers = {"X-API-Key": api_key} if api_key else None
    search_url = f"{base_url}/api/health/retrieval"
    try:
        response = requests.get(
            search_url,
            headers=headers,
            params={
                "q": query,
                "k": k,
                "namespace": OBSIDIAN_NAMESPACE,
            },
            timeout=_WORKSPACE_RETRIEVAL_PROBE_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        payload = response.json()
    except Exception as exc:
        logger.debug(
            "[ContextBroker] workspace backend retrieval probe failed base=%s: %s",
            base_url,
            exc,
        )
        return []

    search_payload = payload.get("search")
    if not isinstance(search_payload, dict):
        return []
    matches = search_payload.get("matches")
    if not isinstance(matches, list):
        return []

    normalized_user_id = str(user_id or "").strip()
    normalized_results: list[dict[str, Any]] = []
    for item in matches:
        if not isinstance(item, dict):
            continue
        namespace = _extract_result_namespace(item)
        if namespace != OBSIDIAN_NAMESPACE:
            continue
        item_user_id = _extract_result_user_id(item)
        if normalized_user_id and item_user_id not in {
            normalized_user_id,
            None,
        }:
            continue
        scoped_item = dict(item)
        scoped_metadata = dict(item.get("metadata") or {})
        scoped_metadata["namespace"] = OBSIDIAN_NAMESPACE
        if normalized_user_id:
            scoped_metadata["user_id"] = normalized_user_id
            scoped_metadata["owner_user_id"] = normalized_user_id
            scoped_item["user_id"] = normalized_user_id
            scoped_item["owner_user_id"] = normalized_user_id
        scoped_item["metadata"] = scoped_metadata
        scoped_item["meta"] = dict(scoped_metadata)
        normalized_results.append(scoped_item)
        if len(normalized_results) >= k:
            break

    if normalized_results:
        logger.info(
            "[ContextBroker] workspace backend retrieval probe selected obsidian=%s base=%s",
            len(normalized_results),
            base_url,
        )
    return normalized_results


def _normalize_obsidian_retrieval_results(
    results: list[Any],
    *,
    user_id: str,
    retrieval_policy: dict[str, Any] | None,
    policy_reason: str,
    assume_obsidian_namespace: bool = False,
) -> list[dict[str, Any]]:
    normalized_user_id = str(user_id or "").strip()
    normalized_results: list[dict[str, Any]] = []
    for item in results:
        if not isinstance(item, dict):
            continue
        namespace = _extract_result_namespace(item)
        if namespace and namespace != OBSIDIAN_NAMESPACE:
            continue
        if not namespace and not assume_obsidian_namespace:
            continue
        item_user_id = _extract_result_user_id(item)
        if normalized_user_id and item_user_id not in {
            normalized_user_id,
            None,
        }:
            continue

        scoped_item = dict(item)
        scoped_metadata = dict(item.get("metadata") or {})
        scoped_metadata["namespace"] = OBSIDIAN_NAMESPACE
        scoped_metadata["source_type"] = "obsidian"
        scoped_metadata["role"] = "document"
        if normalized_user_id and not item_user_id:
            scoped_metadata["user_id"] = normalized_user_id
            scoped_metadata["owner_user_id"] = normalized_user_id
            scoped_item["user_id"] = normalized_user_id
            scoped_item["owner_user_id"] = normalized_user_id
        scoped_item["metadata"] = scoped_metadata
        scoped_item["meta"] = dict(scoped_metadata)
        scoped_item["namespace"] = OBSIDIAN_NAMESPACE
        scoped_item["source_type"] = "obsidian"
        scoped_item["role"] = "document"
        scoped_item["retrieval_lane"] = "obsidian_semantic"
        scoped_item["policy_reason"] = policy_reason
        scoped_item["retrieval_policy"] = dict(retrieval_policy or {})
        normalized_results.append(
            _annotate_retrieval_item(
                scoped_item,
                source_type="obsidian",
                role="document",
                thread_id=_coerce_int(
                    scoped_item.get("thread_id")
                    or scoped_metadata.get("thread_id")
                ),
                project_id=_coerce_int(
                    scoped_item.get("project_id")
                    or scoped_metadata.get("project_id")
                ),
                retrieval_lane="obsidian_semantic",
                policy_reason=policy_reason,
                retrieval_policy=dict(retrieval_policy or {}),
            )
        )
    return normalized_results


def _looks_like_json(text: str) -> bool:
    s = (text or "").lstrip()
    if not s:
        return False
    if s[0] in "{[":
        return True
    # Accept fenced JSON (```json ...``` or ``` ... ```)
    if s.startswith("```"):
        return True
    return False


def maybe_extract_tool_intents(
    model_text: str,
) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    """Extract tool intents from model output if it appears to be JSON."""
    if not _looks_like_json(model_text):
        return None, None

    try:
        intents = parse_tool_intents(model_text)
    except ToolIntentParseError as exc:
        return None, str(exc)

    normalized: List[Dict[str, Any]] = []
    pending: List[Dict[str, Any]] = []
    for intent in intents:
        policy = classify_tool_intent(intent)
        record = {
            "id": intent.intent_id,
            "tool": intent.tool,
            "args": intent.args,
            "reason": intent.reason,
            "risk": policy.risk.value,
            "description": policy.description,
            "requires_consent": policy.requires_consent,
            "approved": policy.risk == ToolRisk.SAFE_READONLY,
        }
        normalized.append(record)
        if policy.requires_consent:
            pending.append(record)

    return {
        "tool_intents": normalized,
        "pending_tool_intents": pending,
    }, None


def build_assistant_response_payload(assistant_text: str) -> Dict[str, Any]:
    """Build a normalized assistant payload with optional tool intent metadata."""
    response: Dict[str, Any] = {"assistant_text": assistant_text}
    tool_block, tool_err = maybe_extract_tool_intents(assistant_text)

    if tool_block is not None:
        response.update(tool_block)
        tool_intents = tool_block.get("tool_intents", [])
        pending_tool_intents = tool_block.get("pending_tool_intents", [])
        tool_intents_redacted = [
            redact_tool_intent_dict(intent) for intent in tool_intents
        ]
        pending_tool_intents_redacted = [
            redact_tool_intent_dict(intent) for intent in pending_tool_intents
        ]
        # Secure-by-default exposure surface for UI/client consumers.
        response["tool_intents"] = tool_intents_redacted
        response["pending_tool_intents"] = pending_tool_intents_redacted
        # Explicit aliases retained for clarity and compatibility.
        response["tool_intents_redacted"] = tool_intents_redacted
        response[
            "pending_tool_intents_redacted"
        ] = pending_tool_intents_redacted
        debug_unredacted = (
            os.getenv("CODEXIFY_DEBUG_UNREDACTED_TOOL_INTENTS") == "1"
        )
        if debug_unredacted:
            response["tool_intents_unredacted"] = tool_intents
            response["pending_tool_intents_unredacted"] = pending_tool_intents
        response["consent_required"] = bool(
            tool_block.get("pending_tool_intents")
        )
    if tool_err:
        response["tool_intent_error"] = tool_err

    return response


def _coerce_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    normalized = str(value or "").strip().lower()
    return normalized in {"1", "true", "yes", "y", "on"}


def _coerce_tags(raw: Any) -> tuple[str, ...]:
    if raw is None:
        return ()
    if isinstance(raw, str):
        return tuple(
            token
            for token in (piece.strip() for piece in raw.split(","))
            if token
        )
    if isinstance(raw, (list, tuple, set)):
        values = []
        for item in raw:
            text = str(item or "").strip()
            if text:
                values.append(text)
        return tuple(values)
    text = str(raw).strip()
    return (text,) if text else ()


def _normalize_memory_candidate_header_dict(
    raw: dict[str, Any], *, fallback_candidate_id: str
) -> MemoryCandidateHeader:
    candidate_id = str(
        raw.get("candidate_id") or raw.get("id") or fallback_candidate_id
    ).strip() or fallback_candidate_id
    user_id = str(
        raw.get("user_id") or raw.get("owner_user_id") or ""
    ).strip()
    kind = str(
        raw.get("kind") or raw.get("source_type") or "semantic"
    ).strip() or "semantic"
    title = str(raw.get("title") or "").strip() or None
    summary = str(raw.get("summary") or "").strip() or None
    silo = str(raw.get("silo") or "").strip() or None
    project_id = str(raw.get("project_id") or "").strip() or None
    thread_id = str(raw.get("thread_id") or "").strip() or None
    persona_id = str(raw.get("persona_id") or "").strip() or None
    identity_depth = str(raw.get("identity_depth") or "").strip()
    if not identity_depth:
        # Keep missing depth fail-closed in preselector normalization.
        identity_depth = ""

    return MemoryCandidateHeader(
        candidate_id=candidate_id,
        user_id=user_id,
        kind=kind,
        title=title,
        summary=summary,
        tags=_coerce_tags(raw.get("tags")),
        silo=silo,
        project_id=project_id,
        thread_id=thread_id,
        persona_id=persona_id,
        identity_depth=identity_depth,
        diary_excluded=_coerce_bool(raw.get("diary_excluded")),
        created_at=str(raw.get("created_at") or "").strip() or None,
        updated_at=str(raw.get("updated_at") or "").strip() or None,
    )


def _memory_preselection_headers_from_memory_items(
    memory_items: Sequence[Any],
) -> list[MemoryCandidateHeader]:
    headers: list[MemoryCandidateHeader] = []
    for index, item in enumerate(memory_items):
        if not isinstance(item, dict):
            continue
        metadata = item.get("metadata")
        if not isinstance(metadata, dict):
            metadata = {}

        raw: dict[str, Any] = {
            "candidate_id": item.get("id")
            or metadata.get("id")
            or metadata.get("source_message_id"),
            "user_id": item.get("user_id")
            or item.get("owner_user_id")
            or metadata.get("user_id")
            or metadata.get("owner_user_id"),
            "kind": item.get("kind")
            or metadata.get("kind")
            or item.get("source_type")
            or metadata.get("source_type"),
            "title": item.get("title")
            or metadata.get("title")
            or metadata.get("filename")
            or metadata.get("name"),
            "summary": item.get("summary")
            or metadata.get("summary")
            or metadata.get("description"),
            "tags": item.get("tags") or metadata.get("tags"),
            "silo": item.get("silo") or metadata.get("silo"),
            "project_id": item.get("project_id") or metadata.get("project_id"),
            "thread_id": item.get("thread_id")
            or metadata.get("thread_id")
            or metadata.get("source_thread_id"),
            "persona_id": item.get("persona_id")
            or metadata.get("persona_id"),
            "identity_depth": item.get("identity_depth")
            or metadata.get("identity_depth"),
            "diary_excluded": item.get("diary_excluded")
            if "diary_excluded" in item
            else metadata.get("diary_excluded"),
            "created_at": item.get("created_at")
            or metadata.get("created_at")
            or metadata.get("source_created_at"),
            "updated_at": item.get("updated_at")
            or metadata.get("updated_at"),
        }
        headers.append(
            _normalize_memory_candidate_header_dict(
                raw,
                fallback_candidate_id=f"memory-candidate-{index}",
            )
        )
    return headers


def _coerce_memory_preselection_headers(
    candidate_headers: Sequence[MemoryCandidateHeader | dict[str, Any]] | None,
) -> list[MemoryCandidateHeader]:
    if not candidate_headers:
        return []
    normalized: list[MemoryCandidateHeader] = []
    for index, item in enumerate(candidate_headers):
        if isinstance(item, MemoryCandidateHeader):
            normalized.append(item)
            continue
        if isinstance(item, dict):
            normalized.append(
                _normalize_memory_candidate_header_dict(
                    item,
                    fallback_candidate_id=f"memory-candidate-{index}",
                )
            )
    return normalized


def _build_memory_preselection_trace(
    *,
    enabled: bool,
    query: str,
    user_id: str,
    project_id: int | None,
    thread_id: int,
    persona_id: str | None,
    identity_depth: str | None,
    include_diary_excluded: bool,
    memory_items: Sequence[Any],
    candidate_headers: Sequence[MemoryCandidateHeader | dict[str, Any]] | None,
) -> dict[str, Any] | None:
    if not enabled:
        return None

    normalized_headers = _coerce_memory_preselection_headers(candidate_headers)
    if not normalized_headers:
        normalized_headers = _memory_preselection_headers_from_memory_items(
            memory_items
        )

    request = MemoryPreselectorRequest(
        query=str(query or ""),
        user_id=str(user_id or "").strip(),
        project_id=str(project_id) if project_id is not None else None,
        thread_id=str(thread_id),
        persona_id=(str(persona_id).strip() if persona_id is not None else None)
        or None,
        identity_depth=(
            str(identity_depth).strip() if identity_depth is not None else ""
        ),
        include_diary_excluded=bool(include_diary_excluded),
        limit=max(1, min(50, len(normalized_headers) or 20)),
        min_score=1,
    )
    result = select_memory_candidates(normalized_headers, request)

    selected_entries = [
        {
            "candidate_id": selected.candidate_id,
            "score": selected.score,
            "matched_terms": list(selected.matched_terms),
            "boost_hints": list(selected.boost_hints),
        }
        for selected in result.selected
    ]
    suppressed_entries = [
        {
            "candidate_id": suppressed.candidate_id,
            "reason": str(suppressed.reason),
        }
        for suppressed in result.suppressed
    ]

    return {
        "enabled": True,
        "selected_count": len(selected_entries),
        "suppressed_count": len(suppressed_entries),
        "selected_candidate_ids": [
            entry["candidate_id"] for entry in selected_entries
        ],
        "selected": selected_entries,
        "suppressed": suppressed_entries,
        "affected_retrieval": False,
        "affected_prompt_injection": False,
    }


class ContextBroker:
    """Assembles context bundles for chat completions at different depth levels.

    Supports four depth modes:
    - "shallow": Only recent messages from the thread
    - "normal": Messages + semantic search results
    - "deep": Messages + semantic + memory search results
    - "diagnostic": Messages + semantic + memory + sensor snapshots
    """

    always_search_thread_first = True

    def __init__(
        self,
        chatlog_db: Any,
        vector_store: Any,
        memory_store: Optional[Any] = None,
        sensors: Optional[Any] = None,
        settings: Optional[Settings] = None,
    ):
        """Initialize ContextBroker with required and optional stores.

        Args:
            chatlog_db: Database providing chatlog access (required)
            vector_store: Vector store for semantic search (required)
            memory_store: Optional memory search backend
            sensors: Optional system sensors provider
        """
        self.chatlog = chatlog_db
        self.vector = vector_store
        self.memory = memory_store
        self.sensors = sensors
        self.settings = settings or get_settings()
        # Initialize MemoryOS semantic retriever for RAG-based memory search when available
        self.memory_retriever = None
        try:
            if vector_store is not None:
                self.memory_retriever = MemoryOSRetriever(
                    vector_store,
                    chatlog_db=chatlog_db,
                )
        except Exception as exc:
            logger.debug(
                "[ContextBroker] Memory retriever init failed: %s", exc
            )
        logger.info(
            "[ContextBroker] Initialized with MemoryOS semantic retriever"
        )

    async def assemble(
        self,
        thread_id: int,
        query: str,
        *,
        depth_mode: Optional[str] = None,
        depth: Optional[str] = None,
        project_id: Optional[int] = None,
        n_messages: int = 6,
        k_semantic: int = 4,
        k_memory: int = 5,
        k_project_docs: int = 4,
        k_thread_docs: int = 4,
        doc_excerpt_chars: int = 420,
        federated: bool = False,
        user_id: Optional[str] = None,
        source_mode: str = SOURCE_MODE_PROJECT,
        retrieval_override: Optional[dict[str, Any]] = None,
        retrieval_policy: Optional[dict[str, Any]] = None,
        enable_memory_preselection_trace: bool = False,
        memory_preselection_candidate_headers: Optional[
            Sequence[MemoryCandidateHeader | dict[str, Any]]
        ] = None,
        memory_preselection_persona_id: Optional[str] = None,
        memory_preselection_identity_depth: Optional[str] = None,
        memory_preselection_include_diary_excluded: bool = False,
    ) -> tuple[Dict[str, Any], Dict[str, Any]]:
        """Assemble a context bundle for the given thread and query.

        Args:
            thread_id: ID of the chat thread
            query: Query string for semantic search
            depth_mode: Retrieval depth ("shallow", "normal", "deep", "diagnostic")
            project_id: Optional project scope override for project-library docs
            source_mode: Retrieval boundary beyond the active thread
            n_messages: Number of recent messages to fetch
            k_semantic: Number of semantic results to fetch
            k_memory: Number of memory results to fetch
            k_project_docs: Max explicit project library documents to include
            k_thread_docs: Max thread-linked documents to include
            doc_excerpt_chars: Max characters per document excerpt
            federated: If True, include federated context from peer nodes

        Returns:
            A tuple of (context, rag_trace):

            context: Dict with keys depending on depth:
                - "messages": Recent thread messages (all depths)
                - "semantic": Semantic search results (all depths except "shallow")
                - "docs": Project/thread document library excerpts (normal+)
                - "graph": Graph-derived context (if enabled)
                - "memory": Memory search results (deep, diagnostic)
                - "sensors": System sensor snapshot (diagnostic only)
                - "federated": Federated search results (if federated=True)

            rag_trace: Dict summarizing contributing items:
                - "documents": List of {id, title, score, snippet}
                - "graph": List of {node_id, kind, text}
        """
        # Normalize depth. `depth` is a legacy alias kept for compatibility.
        widened = False
        widen_reason: str | None = None
        resolved_user_id = str(user_id or "").strip()
        if not resolved_user_id:
            raise ValueError("ContextBroker requires user_id")
        memory_preselection_active = bool(enable_memory_preselection_active)
        memory_preselection_enabled = bool(
            enable_memory_preselection_trace or memory_preselection_active
        )
        normalized_depth = str(depth_mode or depth or "normal").strip().lower()
        requested_source_mode = normalize_source_mode(source_mode)
        base_policy = derive_default_retrieval_policy(source_mode)
        effective_policy = merge_retrieval_policy(
            base_policy,
            retrieval_override,
        )
        policy_source_mode = (
            str(effective_policy.get("source_mode") or source_mode)
            .strip()
            .lower()
        )
        if policy_source_mode == "thread":
            policy_source_mode = SOURCE_MODE_CONVERSATION
        effective_source_mode = normalize_source_mode(policy_source_mode)
        resolved_project_id = await self._resolve_project_id(
            thread_id=thread_id, project_id=project_id
        )
        if retrieval_policy is None:
            effective_context_policy = resolve_context_assembly_policy(
                query,
                normalized_depth,
                source_mode=effective_source_mode,
                retrieval_override=retrieval_override,
                active_thread_id=thread_id,
                active_project_id=resolved_project_id,
                active_persona=None,
            ).as_dict()
        else:
            effective_context_policy = dict(retrieval_policy)
        policy_source_mode = (
            str(
                effective_context_policy.get("source_mode")
                or effective_source_mode
            )
            .strip()
            .lower()
        )
        if policy_source_mode == "thread":
            normalized_source_mode = SOURCE_MODE_CONVERSATION
            widening_source_mode = SOURCE_MODE_CONVERSATION
        else:
            normalized_source_mode = normalize_source_mode(policy_source_mode)
            widening_source_mode = normalize_source_mode(
                str(
                    effective_context_policy.get("widening_source_mode")
                    or policy_source_mode
                )
            )
        widening_enabled = bool(
            effective_context_policy.get("allow_semantic_widening", True)
        )
        allow_project_docs = bool(
            effective_context_policy.get("allow_project_docs", True)
        )
        allow_thread_docs = bool(
            effective_context_policy.get("allow_thread_docs", True)
        )
        conversation_only = normalized_source_mode == SOURCE_MODE_CONVERSATION
        source_mode_boundary = source_mode_boundary_label(
            normalized_source_mode
        )

        context: Dict[str, Any] = {}
        widened = normalized_source_mode == SOURCE_MODE_WORKSPACE
        widen_reason = (
            WIDEN_REASON_EXPLICIT_WORKSPACE
            if normalized_source_mode == SOURCE_MODE_WORKSPACE
            else WIDEN_REASON_NONE
        )
        context["retrieval_policy"] = dict(effective_context_policy)
        policy_suppression_summary = _build_policy_suppression_summary(
            thread_id=thread_id,
            project_id=resolved_project_id,
            retrieval_policy=effective_context_policy,
        )
        if policy_suppression_summary is not None:
            context["retrieval_suppression"] = policy_suppression_summary

        # Always include recent messages
        try:
            messages = await self._fetch_messages(
                thread_id, n_messages, user_id=resolved_user_id
            )
            context["messages"] = messages
        except Exception as e:
            logger.warning(
                "[ContextBroker] Failed to fetch messages for thread %s: %s",
                thread_id,
                e,
            )
            context["messages"] = []

        # Default path includes semantic search (for all depths except
        # "shallow"). Hard obsidian-only mode short-circuits above.
        context["obsidian"] = []
        semantic_widen_reason = WIDEN_REASON_NONE
        if normalized_source_mode == SOURCE_MODE_OBSIDIAN_ONLY:
            obsidian_docs = await self._retrieve_obsidian_documents(
                query,
                user_id=resolved_user_id,
                project_scope=resolved_project_id,
                k=k_semantic,
                retrieval_policy=effective_context_policy,
            )
            context.update(
                {
                    "semantic": [],
                    "memory": [],
                    "docs": {"project": [], "thread": [], "global": []},
                    "obsidian": obsidian_docs,
                    "graph": [],
                    "federated": [],
                    "retrieval_status": (
                        "obsidian_only_success"
                        if obsidian_docs
                        else "no_obsidian_results"
                    ),
                }
            )
            rag_trace = {
                "thread_id": thread_id,
                "project_id": resolved_project_id,
                "depth_mode": normalized_depth,
                "documents": [
                    _serialize_rag_trace_document(item)
                    for item in obsidian_docs
                ],
                "graph": [],
                "source_mode": normalized_source_mode,
                "effective_policy": effective_policy,
                "retrieval_policy": dict(effective_context_policy),
                "retrieval_suppression": context.get("retrieval_suppression"),
                "widen_reason": WIDEN_REASON_NONE,
                "graph_context": {
                    "attempted": False,
                    "status": "skipped",
                    "reason": "obsidian_only",
                    "count": 0,
                    "source_mode": normalized_source_mode,
                    "boundary": source_mode_boundary,
                },
                "memory_context": {
                    "attempted": False,
                    "status": "skipped",
                    "reason": "obsidian_only",
                    "count": 0,
                    "source_mode": normalized_source_mode,
                    "boundary": source_mode_boundary,
                },
                "personal_facts_context": {
                    "attempted": False,
                    "status": "skipped",
                    "reason": "obsidian_only",
                    "count": 0,
                    "retrieved_count": 0,
                    "included_ids": [],
                    "user_id": resolved_user_id or "default",
                    "source_mode": normalized_source_mode,
                    "boundary": source_mode_boundary,
                },
                "verified_personal_facts_context": {
                    "attempted": False,
                    "status": "skipped",
                    "reason": "obsidian_only",
                    "count": 0,
                    "retrieved_count": 0,
                    "included_ids": [],
                    "user_id": resolved_user_id or "default",
                    "source_mode": normalized_source_mode,
                    "boundary": source_mode_boundary,
                },
                "retrieval_status": context["retrieval_status"],
                "obsidian_count": len(obsidian_docs),
            }
            memory_preselection_trace = _build_memory_preselection_trace(
                enabled=enable_memory_preselection_trace,
                query=query,
                user_id=resolved_user_id,
                project_id=resolved_project_id,
                thread_id=thread_id,
                persona_id=memory_preselection_persona_id,
                identity_depth=memory_preselection_identity_depth,
                include_diary_excluded=memory_preselection_include_diary_excluded,
                memory_items=(),
                candidate_headers=memory_preselection_candidate_headers,
            )
            if memory_preselection_trace is not None:
                rag_trace["memory_preselection"] = memory_preselection_trace
            logger.info(
                "[ContextBroker] thread=%s depth=%s messages=%s semantic=%s obsidian=%s docs(project/thread)=%s/%s memory=%s(%s) graph=%s(%s)",
                thread_id,
                normalized_depth,
                len(context.get("messages", [])),
                len(context.get("semantic", [])),
                len(context.get("obsidian", [])),
                len(context.get("docs", {}).get("project", [])),
                len(context.get("docs", {}).get("thread", [])),
                0,
                "skipped",
                0,
                "skipped",
            )
            context["obsidian"] = self._filter_codex_entries(
                context.get("obsidian", [])
            )
            return context, rag_trace
        if normalized_depth != "shallow" and self.always_search_thread_first:
            try:
                (
                    semantic_thread,
                    semantic_widen_reason,
                    _semantic_trace,
                ) = await self._search_with_widening(
                    query=query,
                    k=k_semantic,
                    thread_id=thread_id,
                    user_id=resolved_user_id,
                    project_id=resolved_project_id,
                    source_mode=widening_source_mode,
                    widening_enabled=widening_enabled,
                    search_fn=self._search_semantic,
                    retrieval_policy=effective_context_policy,
                )
                widened = widened or semantic_widen_reason != WIDEN_REASON_NONE
                widen_reason = self._merge_widen_reason(
                    widen_reason,
                    semantic_widen_reason,
                )
                semantic_obsidian: list[dict[str, Any]] = []
                if normalized_source_mode in (
                    SOURCE_MODE_PERSONAL_KNOWLEDGE,
                    SOURCE_MODE_WORKSPACE,
                ):
                    semantic_obsidian = await self._retrieve_obsidian_documents(
                        query,
                        user_id=resolved_user_id,
                        project_scope=resolved_project_id,
                        k=k_semantic,
                        retrieval_policy=effective_context_policy,
                    )
                    if (
                        not semantic_obsidian
                        and normalized_source_mode
                        == SOURCE_MODE_PERSONAL_KNOWLEDGE
                    ):
                        _append_retrieval_warning(
                            context,
                            "obsidian_empty_in_personal_knowledge",
                        )
                    widened = True
                    widen_reason = self._merge_widen_reason(
                        widen_reason or WIDEN_REASON_NONE,
                        (
                            WIDEN_REASON_EXPLICIT_PERSONAL_KNOWLEDGE
                            if normalized_source_mode
                            == SOURCE_MODE_PERSONAL_KNOWLEDGE
                            else WIDEN_REASON_EXPLICIT_WORKSPACE
                        ),
                    )
                elif (
                    not conversation_only and self._obsidian_retrieval_enabled()
                ):
                    try:
                        raw_obsidian_results = await self._search_semantic(
                            query,
                            k_semantic,
                            namespace=OBSIDIAN_NAMESPACE,
                            user_id=resolved_user_id,
                        )
                        semantic_obsidian = (
                            _normalize_obsidian_retrieval_results(
                                raw_obsidian_results,
                                user_id=resolved_user_id,
                                retrieval_policy=effective_context_policy,
                                policy_reason="workspace",
                                assume_obsidian_namespace=True,
                            )
                        )
                    except Exception as exc:
                        logger.warning(
                            "[ContextBroker] Obsidian retrieval failed; continuing without it: %s",
                            exc,
                        )
                context["obsidian"] = semantic_obsidian
                context["semantic"] = semantic_thread + semantic_obsidian
            except Exception as e:
                logger.warning(f"Failed to perform semantic search: {e}")
                context["semantic"] = []
                context["obsidian"] = []
        else:
            context["semantic"] = []
            context["obsidian"] = []

        context["docs"] = {"project": [], "thread": [], "global": []}
        if not conversation_only and normalized_depth in (
            "normal",
            "deep",
            "diagnostic",
        ):
            try:
                scoped_docs = await self.get_scoped_documents(
                    thread_id=thread_id,
                    project_id=resolved_project_id,
                    user_id=resolved_user_id,
                    k_project_docs=k_project_docs,
                    k_thread_docs=k_thread_docs,
                    doc_excerpt_chars=doc_excerpt_chars,
                    include_project_docs=allow_project_docs,
                    include_thread_docs=allow_thread_docs,
                    retrieval_policy=effective_context_policy,
                )
                context["docs"] = scoped_docs
            except Exception as e:
                logger.warning(
                    "[ContextBroker] Failed to fetch scoped documents: %s", e
                )

        personal_facts_trace: Dict[str, Any] = {
            "attempted": False,
            "status": "skipped",
            "reason": (
                f"source_mode_{SOURCE_MODE_CONVERSATION}"
                if conversation_only
                else "depth_not_allowed"
            ),
            "count": 0,
            "retrieved_count": 0,
            "included_ids": [],
            "user_id": resolved_user_id or "default",
            "source_mode": normalized_source_mode,
            "boundary": source_mode_boundary,
        }
        if (
            not conversation_only
            and normalized_source_mode != SOURCE_MODE_OBSIDIAN_ONLY
        ):
            try:
                (
                    personal_facts,
                    personal_facts_trace,
                ) = await self._fetch_verified_personal_facts(
                    user_id=resolved_user_id,
                    limit=_PERSONAL_FACT_LIMIT,
                )
                if personal_facts:
                    context["verified_personal_facts"] = [
                        {
                            "id": fact.get("id"),
                            "key": fact.get("key"),
                            "value": fact.get("value"),
                            "user_id": resolved_user_id,
                        }
                        for fact in personal_facts
                    ]
                    context["personal_facts"] = personal_facts
                personal_facts_trace = {
                    **personal_facts_trace,
                    "source_mode": normalized_source_mode,
                    "boundary": source_mode_boundary,
                }
                context["verified_personal_facts_context"] = dict(
                    personal_facts_trace
                )
                context["personal_facts_context"] = dict(personal_facts_trace)
            except Exception as e:
                logger.warning(
                    "[ContextBroker] Personal facts unavailable; continuing without them: %s",
                    e,
                )
                personal_facts_trace = {
                    "attempted": True,
                    "status": "failed",
                    "reason": "retrieval_error",
                    "error": str(e),
                    "count": 0,
                    "retrieved_count": 0,
                    "included_ids": [],
                    "user_id": resolved_user_id or "default",
                    "source_mode": normalized_source_mode,
                    "boundary": source_mode_boundary,
                }

        # Optional graph-derived context (explicit flag; deferred for CORE LOOP by default)
        context["graph"] = []
        graph_trace: Dict[str, Any] = {
            "attempted": False,
            "status": "skipped",
            "reason": (
                f"source_mode_{SOURCE_MODE_CONVERSATION}"
                if conversation_only
                else "disabled"
            ),
            "count": 0,
            "source_mode": normalized_source_mode,
            "boundary": source_mode_boundary,
        }
        if not conversation_only and getattr(
            self.settings, "GUARDIAN_ENABLE_GRAPH_CONTEXT", False
        ):
            try:
                graph_chunks, graph_trace = await self._get_graph_context(
                    user_id=resolved_user_id or "default",
                    thread_id=str(thread_id),
                )
                context["graph"] = graph_chunks
                graph_trace = {
                    **graph_trace,
                    "source_mode": normalized_source_mode,
                    "boundary": source_mode_boundary,
                }
            except Exception as e:
                logger.warning(
                    "[ContextBroker] Graph context unavailable; continuing without it: %s",
                    e,
                )
                graph_trace = {
                    **graph_trace,
                    "status": "failed",
                    "reason": "retrieval_error",
                    "error": str(e),
                    "source_mode": normalized_source_mode,
                    "boundary": source_mode_boundary,
                }

        # Include memory search for deep and diagnostic modes
        memory_widen_reason = WIDEN_REASON_NONE
        memory_preselection_trace: dict[str, Any] | None = None
        memory_trace: Dict[str, Any] = {
            "attempted": False,
            "status": "skipped",
            "reason": (
                f"source_mode_{SOURCE_MODE_CONVERSATION}"
                if conversation_only
                else "depth_not_allowed"
            ),
            "count": 0,
            "boundary": source_mode_boundary,
            "source_mode": normalized_source_mode,
        }
        if normalized_depth in ("deep", "diagnostic"):
            try:
                if conversation_only:
                    context["memory"] = []
                elif self.memory:
                    (
                        memory,
                        memory_widen_reason,
                        memory_trace,
                    ) = await self._search_with_widening(
                        query=query,
                        k=k_memory,
                        thread_id=thread_id,
                        user_id=resolved_user_id,
                        project_id=resolved_project_id,
                        source_mode=normalized_source_mode,
                        widening_enabled=widening_enabled,
                        search_fn=self._search_memory,
                        retrieval_policy=effective_context_policy,
                    )
                    widened = (
                        widened or memory_widen_reason != WIDEN_REASON_NONE
                    )
                    widen_reason = self._merge_widen_reason(
                        widen_reason,
                        memory_widen_reason,
                    )
                    context["memory"] = memory
                    if memory_widen_reason != WIDEN_REASON_NONE:
                        widened = True
                        widen_reason = self._merge_widen_reason(
                            widen_reason or WIDEN_REASON_NONE,
                            memory_widen_reason,
                        )
                else:
                    context["memory"] = []
                    memory_trace = {
                        "attempted": False,
                        "status": "skipped",
                        "reason": "no_memory_store",
                        "count": 0,
                        "boundary": source_mode_boundary,
                        "source_mode": normalized_source_mode,
                    }
            except Exception as e:
                logger.warning(f"Failed to fetch memory results: {e}")
                context["memory"] = []
                memory_trace = {
                    "attempted": True,
                    "status": "failed",
                    "reason": "retrieval_error",
                    "error": str(e),
                    "count": 0,
                    "boundary": source_mode_boundary,
                    "source_mode": normalized_source_mode,
                }

        memory_preselection_trace = _build_memory_preselection_trace(
            enabled=memory_preselection_enabled,
            active=memory_preselection_active,
            query=query,
            user_id=resolved_user_id,
            project_id=resolved_project_id,
            thread_id=thread_id,
            persona_id=memory_preselection_persona_id,
            identity_depth=memory_preselection_identity_depth,
            include_diary_excluded=memory_preselection_include_diary_excluded,
            memory_items=context.get("memory", []),
            candidate_headers=memory_preselection_candidate_headers,
        )
        if (
            memory_preselection_active
            and memory_preselection_trace is not None
            and isinstance(context.get("memory"), list)
        ):
            selected_candidate_ids = [
                str(candidate_id).strip()
                for candidate_id in memory_preselection_trace.get(
                    "selected_candidate_ids", []
                )
                if str(candidate_id).strip()
            ]
            scoped_candidate_ids = selected_candidate_ids + [
                str(entry.get("candidate_id") or "").strip()
                for entry in memory_preselection_trace.get("suppressed", [])
                if isinstance(entry, dict)
                and str(entry.get("candidate_id") or "").strip()
            ]
            filtered_memory_items, active_influence, applied = (
                _apply_memory_preselection_active_influence(
                    context.get("memory", []),
                    selected_candidate_ids=selected_candidate_ids,
                    scoped_candidate_ids=scoped_candidate_ids,
                )
            )
            if applied:
                context["memory"] = filtered_memory_items
            memory_preselection_trace["active_influence"] = active_influence
            memory_preselection_trace["affected_retrieval"] = applied
            memory_preselection_trace["affected_prompt_injection"] = applied

        # Include sensor snapshot for diagnostic mode only
        if normalized_depth == "diagnostic":
            try:
                if self.sensors:
                    snapshot = await self._snapshot_sensors()
                    context["sensors"] = snapshot
                else:
                    context["sensors"] = {}
            except Exception as e:
                logger.warning(f"Failed to snapshot sensors: {e}")
                context["sensors"] = {}

        # Include federated context if requested
        if federated:
            try:
                if conversation_only:
                    context["federated"] = []
                else:
                    federated_results = await self._search_federated(
                        query, k_semantic
                    )
                    context["federated"] = federated_results
            except Exception as e:
                logger.warning(f"Failed to fetch federated context: {e}")
                context["federated"] = []

        if normalized_source_mode == SOURCE_MODE_WORKSPACE:
            workspace_result_count = 0
            for key in ("semantic", "obsidian"):
                value = context.get(key)
                if isinstance(value, list):
                    workspace_result_count += len(value)
            docs_value = context.get("docs")
            if isinstance(docs_value, dict):
                for key in ("project", "thread"):
                    value = docs_value.get(key)
                    if isinstance(value, list):
                        workspace_result_count += len(value)
            context["retrieval_status"] = (
                "workspace_local_success"
                if workspace_result_count > 0
                else "no_workspace_results"
            )

        all_results: list[Any] = []
        for key in (
            "semantic",
            "obsidian",
            "memory",
            "graph",
            "personal_facts",
        ):
            value = context.get(key)
            if isinstance(value, list):
                all_results.extend(value)
        docs_value = context.get("docs")
        if isinstance(docs_value, dict):
            for value in docs_value.values():
                if isinstance(value, list):
                    all_results.extend(value)

        filtered_results = [
            item
            for item in all_results
            if self._result_user_id(item) == resolved_user_id
        ]
        if len(filtered_results) != len(all_results):
            raise AssertionError("retrieval_user_isolation_violation")

        if widened and not widen_reason:
            raise AssertionError("missing_widen_reason")
        if not widened:
            widen_reason = WIDEN_REASON_NONE
        if not widened and widen_reason != WIDEN_REASON_NONE:
            raise AssertionError("invalid_widen_reason_without_widening")

        source_hit_counts = {
            "semantic_total": len(context.get("semantic", [])),
            "thread_semantic": len(
                [
                    item
                    for item in context.get("semantic", [])
                    if isinstance(item, dict)
                    and str(item.get("namespace") or "").startswith("thread:")
                ]
            ),
            "obsidian_semantic": len(
                [
                    item
                    for item in context.get("semantic", [])
                    if isinstance(item, dict)
                    and _extract_result_namespace(item) == OBSIDIAN_NAMESPACE
                ]
            ),
            "other_semantic": 0,
            "project_documents": len(
                [
                    item
                    for item in context.get("docs", {}).get("project", [])
                    if isinstance(item, dict)
                ]
            ),
            "thread_documents": len(
                [
                    item
                    for item in context.get("docs", {}).get("thread", [])
                    if isinstance(item, dict)
                ]
            ),
            "global_documents": len(
                [
                    item
                    for item in context.get("docs", {}).get("global", [])
                    if isinstance(item, dict)
                ]
            ),
            "other_documents": 0,
            "memory": len(
                [
                    item
                    for item in context.get("memory", [])
                    if isinstance(item, dict)
                ]
            ),
            "graph": len(
                [
                    item
                    for item in context.get("graph", [])
                    if isinstance(item, dict)
                ]
            ),
        }
        retrieval_executed = normalized_depth != "shallow"
        retrieval_absence_reason = None
        if not retrieval_executed:
            retrieval_absence_reason = (
                TraceSnapshotAbsenceReason.RETRIEVAL_NOT_EXECUTED.value
            )
        elif not any(source_hit_counts.values()):
            retrieval_absence_reason = (
                TraceSnapshotAbsenceReason.RETRIEVAL_NO_CANDIDATES.value
            )

        retrieval_provenance = {
            "requested_source_mode": requested_source_mode,
            "normalized_source_mode": normalized_source_mode,
            "source_hit_counts": source_hit_counts,
            "retrieval_status": context.get("retrieval_status")
            or (
                "obsidian_only_success"
                if normalized_source_mode == SOURCE_MODE_OBSIDIAN_ONLY
                and context.get("obsidian")
                else "no_candidates"
            ),
        }

        # Keep source-boundary diagnostics stable while source_mode still
        # crosses the worker boundary through the temporary origin bridge.
        rag_trace = {
            "thread_id": thread_id,
            "project_id": resolved_project_id,
            "depth_mode": normalized_depth,
            "documents": [
                _serialize_rag_trace_document(item)
                for item in context.get("semantic", [])
            ],
            "graph": [
                {
                    "node_id": str(item.get("message_id", "")),
                    "kind": str(item.get("kind", "unknown")),
                    "text": str(item.get("text", ""))[:100] + "...",
                }
                for item in context.get("graph", [])
            ],
            "source_mode": normalized_source_mode,
            "effective_policy": effective_policy,
            "retrieval_policy": dict(effective_policy),
            "retrieval_provenance": retrieval_provenance,
            "retrieval_suppression": {
                "items": [],
                "summary": {"total_suppressed": 0},
            },
            "retrieval_executed": retrieval_executed,
            "retrieval_absence_reason": retrieval_absence_reason,
            "image_routing_path": None,
            "image_routing_absence_reason": (
                TraceSnapshotAbsenceReason.IMAGE_ROUTING_NOT_EVALUATED.value
            ),
            "widen_reason": widen_reason,
            "graph_context": graph_trace,
            "memory_context": memory_trace,
            "personal_facts_context": personal_facts_trace,
            "verified_personal_facts_context": personal_facts_trace,
        }
        memory_preselection_trace = _build_memory_preselection_trace(
            enabled=enable_memory_preselection_trace,
            query=query,
            user_id=resolved_user_id,
            project_id=resolved_project_id,
            thread_id=thread_id,
            persona_id=memory_preselection_persona_id,
            identity_depth=memory_preselection_identity_depth,
            include_diary_excluded=memory_preselection_include_diary_excluded,
            memory_items=context.get("memory", []),
            candidate_headers=memory_preselection_candidate_headers,
        )
        if memory_preselection_trace is not None:
            rag_trace["memory_preselection"] = memory_preselection_trace

        try:
            logger.info(
                "[ContextBroker] thread=%s depth=%s messages=%s semantic=%s obsidian=%s docs(project/thread)=%s/%s memory=%s(%s) graph=%s(%s)",
                thread_id,
                normalized_depth,
                len(context.get("messages", [])),
                len(context.get("semantic", [])),
                len(context.get("obsidian", [])),
                len(context.get("docs", {}).get("project", [])),
                len(context.get("docs", {}).get("thread", [])),
                len(context.get("memory", [])) if "memory" in context else 0,
                memory_trace.get("status"),
                len(context.get("graph", [])),
                graph_trace.get("status"),
            )
        except Exception:
            pass

        # Apply codex entry retrieval exclusion before returning
        context["semantic"] = self._filter_codex_entries(
            context.get("semantic", [])
        )
        context["obsidian"] = self._filter_codex_entries(
            context.get("obsidian", [])
        )
        if isinstance(context.get("docs"), dict):
            context["docs"] = self._filter_codex_from_doc_buckets(context["docs"])
        if "memory" in context:
            context["memory"] = self._filter_codex_entries(
                context.get("memory", [])
            )

        return context, rag_trace

    @staticmethod
    def _result_user_id(item: Any) -> Optional[str]:
        if isinstance(item, dict):
            user_value = item.get("user_id") or item.get("owner_user_id")
            if user_value not in (None, ""):
                return str(user_value).strip() or None
            metadata = item.get("metadata")
            if isinstance(metadata, dict):
                nested_user_value = metadata.get("user_id") or metadata.get(
                    "owner_user_id"
                )
                if nested_user_value not in (None, ""):
                    return str(nested_user_value).strip() or None

        user_value = getattr(item, "user_id", None) or getattr(
            item, "owner_user_id", None
        )
        if user_value not in (None, ""):
            return str(user_value).strip() or None
        return None

    async def _fetch_verified_personal_facts(
        self,
        *,
        user_id: Optional[str],
        limit: int,
    ) -> tuple[List[Dict[str, Any]], Dict[str, Any]]:
        """Fetch verified, active personal facts from the chatlog adapter."""
        effective_user_id = str(user_id or "default").strip() or "default"
        trace: Dict[str, Any] = {
            "attempted": False,
            "status": "skipped",
            "reason": "no_fact_adapter",
            "count": 0,
            "retrieved_count": 0,
            "included_ids": [],
            "user_id": effective_user_id,
        }

        getter = getattr(self.chatlog, "list_facts", None)
        if not callable(getter):
            return [], trace

        try:
            try:
                result = getter(
                    effective_user_id,
                    status="verified",
                    active_only=True,
                    limit=limit,
                )
            except TypeError:
                result = getter(
                    effective_user_id,
                    status="verified",
                    active_only=True,
                )
            if hasattr(result, "__await__"):
                result = await result
            raw_facts = result if isinstance(result, list) else []
            eligible_facts = [
                fact
                for fact in raw_facts
                if _is_verified_active_personal_fact(fact)
            ]
            eligible_facts.sort(
                key=lambda fact: (
                    _coerce_int(fact.get("id")) or 0,
                    str(fact.get("key") or ""),
                    str(fact.get("value") or ""),
                )
            )
            if limit > 0:
                eligible_facts = eligible_facts[:limit]
            trace.update(
                attempted=True,
                retrieved_count=len(raw_facts),
                count=len(eligible_facts),
                included_ids=[
                    _coerce_int(fact.get("id"))
                    for fact in eligible_facts
                    if _coerce_int(fact.get("id")) is not None
                ],
                status=(
                    "contributed" if eligible_facts else "attempted_no_hits"
                ),
                reason=(
                    "verified_active_facts"
                    if eligible_facts
                    else "no_verified_facts"
                ),
            )
            return eligible_facts, trace
        except Exception as exc:
            trace.update(
                attempted=True,
                status="failed",
                reason="retrieval_error",
                error=str(exc),
                count=0,
                retrieved_count=0,
                included_ids=[],
            )
            return [], trace

    def _obsidian_retrieval_enabled(self) -> bool:
        getter = getattr(self.chatlog, "get_connector_config", None)
        if not callable(getter):
            return False
        try:
            config = getter(_OBSIDIAN_CONNECTOR_NAME)
            if hasattr(config, "__await__"):
                return False
            if not isinstance(config, dict):
                return False
            settings = config.get("settings")
            if not isinstance(settings, dict):
                return False
            if not str(settings.get("vault_root") or "").strip():
                return False
            if settings.get("enabled") is False:
                return False
            return True
        except Exception as exc:
            logger.debug(
                "[ContextBroker] Obsidian connector check failed: %s", exc
            )
            return False

    async def _fetch_messages(
        self, thread_id: int, n: int, *, user_id: str
    ) -> List[Dict[str, Any]]:
        """Fetch recent messages from a thread.

        Uses chatlog.last_messages when available, otherwise falls back to
        chatlog.list_messages(thread_id, limit=n, offset=0).
        """
        # Preferred: use last_messages if adapter provides it (ordered newest→oldest)
        if hasattr(self.chatlog, "last_messages"):
            try:
                result = self.chatlog.last_messages(
                    thread_id, n=n, user_id=user_id
                )
            except TypeError:
                result = self.chatlog.last_messages(thread_id, n=n)
        # Fallback for adapters that only expose list_messages (e.g., ChatDB/PgDB)
        elif hasattr(self.chatlog, "list_messages"):
            try:
                result = self.chatlog.list_messages(
                    thread_id,
                    limit=n,
                    offset=0,
                    user_id=user_id,
                )
            except TypeError:
                result = self.chatlog.list_messages(
                    thread_id,
                    limit=n,
                    offset=0,
                )
        else:
            return []

        # Handle both sync and async returns
        if hasattr(result, "__await__"):
            result = await result

        return result if isinstance(result, list) else []

    async def _search_semantic(
        self,
        query: str,
        k: int,
        *,
        namespace: Optional[str] = None,
        user_id: str,
    ) -> List[Dict[str, Any]]:
        """Search for semantic matches via vector store."""
        if hasattr(self.vector, "search"):
            try:
                result = self.vector.search(
                    query,
                    k=k,
                    namespace=namespace,
                    user_id=user_id,
                )
            except TypeError:
                result = self.vector.search(
                    query,
                    k=k,
                    namespace=namespace,
                )
            # Handle both sync and async returns
            if hasattr(result, "__await__"):
                result = await result
            if not isinstance(result, list):
                return []
            normalized_user_id = str(user_id or "").strip()
            normalized_namespace = str(namespace or "").strip()
            filtered: list[dict[str, Any]] = []
            for item in result:
                if not isinstance(item, dict):
                    continue
                item_user_id = str(
                    (
                        item.get("user_id")
                        or item.get("owner_user_id")
                        or item.get("metadata", {}).get("user_id")
                        or item.get("metadata", {}).get("owner_user_id")
                    )
                    or ""
                ).strip()
                if item_user_id == normalized_user_id:
                    filtered.append(item)
                    continue
                if normalized_namespace != OBSIDIAN_NAMESPACE:
                    continue
                scoped_item = dict(item)
                scoped_metadata = dict(item.get("metadata") or {})
                scoped_metadata["user_id"] = normalized_user_id
                scoped_metadata["owner_user_id"] = normalized_user_id
                scoped_item["metadata"] = scoped_metadata
                scoped_item["user_id"] = normalized_user_id
                scoped_item["owner_user_id"] = normalized_user_id
                filtered.append(scoped_item)
            return self._sort_retrieval_items(filtered)
        return []

    async def _retrieve_obsidian_documents(
        self,
        query: str,
        *,
        user_id: Optional[str],
        project_scope: Optional[int],
        k: int,
        retrieval_policy: dict[str, Any] | None = None,
    ) -> List[Dict[str, Any]]:
        """Fetch Obsidian-backed documents from the shared vector corpus."""
        if k <= 0:
            return []

        try:
            results = await self._search_semantic(
                query,
                k,
                namespace=OBSIDIAN_NAMESPACE,
                user_id=str(user_id or "").strip(),
            )
            normalized_source_mode = normalize_source_mode(
                (retrieval_policy or {}).get("source_mode")
            )
            policy_reason = (
                "personal_knowledge"
                if normalized_source_mode == SOURCE_MODE_PERSONAL_KNOWLEDGE
                else "workspace"
            )
            normalized_results = _normalize_obsidian_retrieval_results(
                results,
                user_id=str(user_id or ""),
                retrieval_policy=retrieval_policy,
                policy_reason=policy_reason,
                assume_obsidian_namespace=True,
            )
            if normalized_results:
                return normalized_results

            # The worker-local vector store can be empty even when the
            # supported workspace backend has the same Obsidian corpus.
            backend_results = _workspace_backend_obsidian_results(
                query=query,
                user_id=str(user_id or "").strip(),
                k=k,
            )
            return _normalize_obsidian_retrieval_results(
                backend_results,
                user_id=str(user_id or ""),
                retrieval_policy=retrieval_policy,
                policy_reason=policy_reason,
                assume_obsidian_namespace=True,
            )
        except Exception as exc:
            logger.warning(
                "[ContextBroker] Obsidian retrieval failed user=%s project=%s: %s",
                user_id or "default",
                project_scope,
                exc,
            )
            return []

    async def retrieve_obsidian_context_command(
        self,
        *,
        query: str,
        user_id: str,
        project_id: int | None = None,
        k: int = 4,
        retrieval_policy: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """Run the turn-scoped Obsidian connector context command."""

        normalized_query = str(query or "").strip()
        if not normalized_query:
            return []

        retrieved = await self._retrieve_obsidian_documents(
            normalized_query,
            user_id=str(user_id or "").strip(),
            project_scope=project_id,
            k=k,
            retrieval_policy=retrieval_policy,
        )
        if not retrieved:
            return []

        annotated: list[dict[str, Any]] = []
        for item in retrieved:
            if not isinstance(item, dict):
                continue
            metadata = item.get("metadata")
            if isinstance(metadata, dict):
                metadata_copy = dict(metadata)
            else:
                metadata_copy = {}
            meta = item.get("meta")
            if isinstance(meta, dict):
                meta_copy = dict(meta)
            else:
                meta_copy = dict(metadata_copy)

            project_value = _coerce_int(project_id)
            if project_value is not None:
                metadata_copy.setdefault("project_id", project_value)
                meta_copy.setdefault("project_id", project_value)

            metadata_copy.setdefault("source_type", "obsidian")
            metadata_copy["connector_id"] = "obsidian"
            metadata_copy["retrieval_lane"] = "connector_context"
            metadata_copy["context_command"] = True
            meta_copy.setdefault("source_type", "obsidian")
            meta_copy["connector_id"] = "obsidian"
            meta_copy["retrieval_lane"] = "connector_context"
            meta_copy["context_command"] = True

            annotated_item = _annotate_retrieval_item(
                item,
                source_type=str(
                    item.get("source_type")
                    or metadata_copy.get("source_type")
                    or "obsidian"
                ).strip()
                or "obsidian",
                role=str(
                    item.get("role") or metadata_copy.get("role") or "document"
                ).strip()
                or "document",
                thread_id=_coerce_int(
                    item.get("thread_id") or metadata_copy.get("thread_id")
                ),
                project_id=project_value
                or _coerce_int(
                    item.get("project_id") or metadata_copy.get("project_id")
                ),
                retrieval_lane="connector_context",
                connector_id="obsidian",
                context_command=True,
                context_request_kind="read_only_context_request",
                retrieval_policy=dict(retrieval_policy or {}),
            )
            if isinstance(annotated_item, dict):
                annotated_item["source_type"] = metadata_copy["source_type"]
                annotated_item["retrieval_lane"] = "connector_context"
                annotated_item["connector_id"] = "obsidian"
                annotated_item["context_command"] = True
                annotated_item[
                    "context_request_kind"
                ] = "read_only_context_request"
                annotated_item["metadata"] = metadata_copy
                annotated_item["meta"] = meta_copy
                annotated.append(annotated_item)

        return annotated
        """Fetch turn-scoped Obsidian connector context for a context command."""
        normalized_query = str(query or "").strip()
        if not normalized_query or k <= 0:
            return []

        resolved_user_id = str(user_id or "").strip()
        if not resolved_user_id:
            raise ValueError("ContextBroker requires user_id")

        resolved_project_id = _coerce_int(project_id)
        items = await self._retrieve_obsidian_documents(
            normalized_query,
            user_id=resolved_user_id,
            project_scope=resolved_project_id,
            k=k,
        )
        if not items:
            return []

        annotated_items: list[dict[str, Any]] = []
        for item in items:
            if not isinstance(item, dict):
                continue
            annotated_item = dict(item)
            metadata = annotated_item.get("metadata")
            if isinstance(metadata, dict):
                metadata = dict(metadata)
            else:
                metadata = {}

            metadata.setdefault("source_type", "obsidian")
            metadata["connector_id"] = "obsidian"
            metadata["retrieval_lane"] = "connector_context"
            metadata["context_command"] = "turn_scoped"
            metadata["user_id"] = resolved_user_id
            if resolved_project_id is not None:
                metadata["project_id"] = resolved_project_id
            if isinstance(retrieval_policy, dict) and retrieval_policy:
                metadata["retrieval_policy"] = dict(retrieval_policy)

            annotated_item["metadata"] = metadata
            annotated_item.setdefault("source_type", "obsidian")
            annotated_item["connector_id"] = "obsidian"
            annotated_item["retrieval_lane"] = "connector_context"
            annotated_item["context_command"] = "turn_scoped"
            annotated_item["user_id"] = resolved_user_id
            if resolved_project_id is not None:
                annotated_item["project_id"] = resolved_project_id
            annotated_items.append(annotated_item)

        return annotated_items

    async def _search_memory(
        self,
        query: str,
        k: int,
        *,
        namespace: Optional[str] = None,
        user_id: str,
    ) -> tuple[List[Dict[str, Any]], Dict[str, Any]]:
        """Search for related memory entries using MemoryOS semantic retriever.

        Primary: Uses MemoryOSRetriever for vector-based semantic memory search.
        Fallback: Falls back to legacy memory_store.search_related() if available.
        """
        trace: Dict[str, Any] = {
            "attempted": False,
            "status": "skipped",
            "reason": "no_retriever",
            "count": 0,
        }
        if self.memory_retriever:
            try:
                retrieve_with_trace = getattr(
                    self.memory_retriever, "retrieve_with_trace", None
                )
                if callable(retrieve_with_trace):
                    memory_results, retriever_trace = await retrieve_with_trace(
                        query,
                        limit=k,
                        namespace=namespace,
                        user_id=user_id,
                    )
                else:
                    try:
                        memory_results = await self.memory_retriever.retrieve(
                            query,
                            limit=k,
                            namespace=namespace,
                            user_id=user_id,
                        )
                    except TypeError:
                        memory_results = await self.memory_retriever.retrieve(
                            query, limit=k, user_id=user_id
                        )
                    retriever_trace = {
                        "attempted": True,
                        "status": (
                            "contributed"
                            if memory_results
                            else "attempted_no_hits"
                        ),
                        "reason": ("results" if memory_results else "no_hits"),
                        "count": len(memory_results),
                    }
                if isinstance(memory_results, list):
                    normalized_user_id = str(user_id or "").strip()
                    memory_results = [
                        item
                        for item in memory_results
                        if str(
                            (
                                item.get("user_id")
                                or item.get("owner_user_id")
                                or item.get("metadata", {}).get("user_id")
                                or item.get("metadata", {}).get("owner_user_id")
                            )
                            or ""
                        ).strip()
                        == normalized_user_id
                    ]
                    retriever_trace["count"] = len(memory_results)
                    if not memory_results:
                        retriever_trace["status"] = "attempted_no_hits"
                        retriever_trace["reason"] = "no_hits"
                trace = {"attempted": True, **retriever_trace}
                logger.debug(
                    f"[ContextBroker] Retrieved {len(memory_results)} memory chunks "
                    f"via MemoryOSRetriever"
                )
                return memory_results, trace
            except Exception as e:
                logger.warning(
                    f"[ContextBroker] MemoryOS retriever failed: {e}"
                )
                trace = {
                    "attempted": True,
                    "status": "failed",
                    "reason": "retriever_error",
                    "error": str(e),
                    "count": 0,
                }

        # Fallback: Use legacy memory_store if available.
        if (
            namespace is None
            and self.memory
            and hasattr(self.memory, "search_related")
        ):
            try:
                try:
                    result = self.memory.search_related(
                        query, limit=k, user_id=user_id
                    )
                except TypeError:
                    result = self.memory.search_related(query, limit=k)
                if hasattr(result, "__await__"):
                    result = await result
                if isinstance(result, list):
                    normalized_user_id = str(user_id or "").strip()
                    filtered = [
                        item
                        for item in result
                        if str(
                            (
                                item.get("user_id")
                                or item.get("owner_user_id")
                                or item.get("metadata", {}).get("user_id")
                                or item.get("metadata", {}).get("owner_user_id")
                            )
                            or ""
                        ).strip()
                        == normalized_user_id
                    ]
                    trace = {
                        "attempted": True,
                        "status": (
                            "contributed" if filtered else "attempted_no_hits"
                        ),
                        "reason": (
                            "legacy_results" if filtered else "legacy_no_hits"
                        ),
                        "count": len(filtered),
                    }
                    logger.debug(
                        f"[ContextBroker] Fallback: Retrieved {len(filtered)} "
                        f"results from legacy memory_store"
                    )
                    return filtered, trace
            except Exception as fallback_error:
                logger.warning(
                    f"[ContextBroker] Legacy memory_store also failed: {fallback_error}"
                )
                trace = {
                    "attempted": True,
                    "status": "failed",
                    "reason": "legacy_retriever_error",
                    "error": str(fallback_error),
                    "count": 0,
                }

        return [], trace

    async def _resolve_user_id(
        self, *, thread_id: int, user_id: Optional[str]
    ) -> Optional[str]:
        explicit_user = str(user_id or "").strip()
        if explicit_user:
            return explicit_user

        getter = getattr(self.chatlog, "get_chat_thread", None)
        if not callable(getter):
            return None

        try:
            thread = getter(thread_id)
            if hasattr(thread, "__await__"):
                thread = await thread
            if isinstance(thread, dict):
                resolved_user = str(thread.get("user_id") or "").strip()
                return resolved_user or None
        except Exception as exc:
            logger.debug(
                "[ContextBroker] Failed to resolve user_id for thread %s: %s",
                thread_id,
                exc,
            )
        return None

    @staticmethod
    def _unpack_search_output(
        result: Any,
    ) -> tuple[List[Dict[str, Any]], Dict[str, Any]]:
        if (
            isinstance(result, tuple)
            and len(result) == 2
            and isinstance(result[1], dict)
        ):
            hits = result[0] if isinstance(result[0], list) else []
            return hits, dict(result[1])
        if isinstance(result, list):
            return result, {}
        return [], {}

    @staticmethod
    def _retrieval_trust_rank(item: Any) -> int:
        if not isinstance(item, dict):
            return 1

        metadata = item.get("metadata")
        if not isinstance(metadata, dict):
            metadata = item.get("meta")
        if not isinstance(metadata, dict):
            metadata = {}

        role = (
            str(
                item.get("role")
                or metadata.get("role")
                or metadata.get("author_role")
                or metadata.get("speaker_role")
                or metadata.get("source_role")
                or ""
            )
            .strip()
            .lower()
        )
        scope = (
            str(
                item.get("scope")
                or metadata.get("scope")
                or item.get("source")
                or metadata.get("source")
                or metadata.get("document_scope")
                or ""
            )
            .strip()
            .lower()
        )
        if role == "assistant":
            return 2
        if role == "user":
            return 0
        if scope in {
            "document",
            "project",
            "thread",
            "project_document",
            "thread_document",
            "uploaded_document",
            "generated_document",
        }:
            return 0
        return 1

    @staticmethod
    def _filter_codex_entries(
        items: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """Filter out codex entries with retrieval disabled.

        Codex entries are excluded from retrieval by default unless
        explicitly opted in via ``retrieval_enabled: true`` in their
        frontmatter. This filter checks both top-level and nested
        metadata fields.
        """
        filtered: list[dict[str, Any]] = []
        for item in items:
            if not isinstance(item, dict):
                filtered.append(item)
                continue

            source_type = str(item.get("source_type") or "").strip().lower()
            if source_type == "codex_entry":
                retrieval_enabled = item.get("retrieval_enabled")
                metadata = item.get("metadata")
                if isinstance(metadata, dict):
                    if retrieval_enabled is None:
                        retrieval_enabled = metadata.get("retrieval_enabled")
                if retrieval_enabled is not True:
                    continue

            doc_type = str(item.get("type") or "").strip().lower()
            if doc_type == "codex_entry":
                retrieval_enabled = item.get("retrieval_enabled")
                if retrieval_enabled is not True:
                    continue

            filtered.append(item)
        return filtered

    @staticmethod
    def _filter_codex_from_doc_buckets(
        docs: Dict[str, List[Dict[str, Any]]],
    ) -> Dict[str, List[Dict[str, Any]]]:
        """Apply codex entry filtering across all doc buckets."""
        return {
            key: ContextBroker._filter_codex_entries(value)
            for key, value in docs.items()
        }

    @classmethod
    def _sort_retrieval_items(
        cls, items: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        decorated: list[tuple[int, float, int, Dict[str, Any]]] = []
        for index, item in enumerate(items):
            raw_score = item.get("score", 0.0)
            try:
                score = float(raw_score)
            except (TypeError, ValueError):
                score = 0.0
            decorated.append(
                (cls._retrieval_trust_rank(item), -score, index, item)
            )
        decorated.sort()
        return [item for *_prefix, item in decorated]

    async def _search_with_widening(
        self,
        *,
        query: str,
        k: int,
        thread_id: int,
        user_id: str,
        project_id: Optional[int],
        source_mode: str,
        search_fn: Any,
        widening_enabled: bool = True,
        retrieval_policy: dict[str, Any] | None = None,
    ) -> tuple[List[Dict[str, Any]], str, Dict[str, Any]]:
        normalized_source_mode = normalize_source_mode(source_mode)
        diagnostics: Dict[str, Any] = {
            "attempted": False,
            "status": "skipped",
            "reason": "not_attempted",
            "source_mode": normalized_source_mode,
            "boundary": source_mode_boundary_label(normalized_source_mode),
            "widening_enabled": bool(widening_enabled),
            "primary_hit_count": 0,
            "candidate_thread_count": 0,
            "candidate_hit_count": 0,
            "result_count": 0,
            "widened": False,
        }
        if k <= 0:
            diagnostics["reason"] = "invalid_limit"
            return [], WIDEN_REASON_NONE, diagnostics

        try:
            primary_output = await search_fn(
                query,
                k,
                namespace=_thread_namespace(thread_id),
                user_id=user_id,
            )
        except Exception as exc:
            diagnostics.update(
                attempted=True,
                status="failed",
                reason="primary_search_error",
                error=str(exc),
            )
            return [], WIDEN_REASON_NONE, diagnostics

        primary_hits, search_trace = self._unpack_search_output(primary_output)
        diagnostics.update(
            attempted=True,
            retriever=search_trace,
            primary_hit_count=len(primary_hits),
        )
        if search_trace.get("status") == "failed" and not primary_hits:
            diagnostics.update(
                status="failed",
                reason=search_trace.get("reason", "primary_search_error"),
                error=search_trace.get("error"),
                result_count=0,
            )
            return [], WIDEN_REASON_NONE, diagnostics

        widen_reason = self._determine_widen_reason(primary_hits, k)
        is_memory_search = (
            getattr(search_fn, "__name__", "") == "_search_memory"
        )
        primary_lane = "memory" if is_memory_search else "thread_semantic"
        primary_policy_reason = search_trace.get("reason") or "local_hits"

        def _annotate_hits(
            hits: list[dict[str, Any]],
            *,
            retrieval_lane: str,
            policy_reason: str,
            source_thread_id: int,
        ) -> list[dict[str, Any]]:
            source_type = "memory" if is_memory_search else "retrieval"
            annotated: list[dict[str, Any]] = []
            for item in hits:
                score_value: float | None = None
                try:
                    raw_score = item.get("score")
                    if raw_score is not None:
                        score_value = float(raw_score)
                except (TypeError, ValueError):
                    score_value = None
                annotated.append(
                    _annotate_retrieval_item(
                        item,
                        source_type=str(
                            item.get("source_type")
                            or item.get("metadata", {}).get("source_type")
                            or source_type
                        ).strip()
                        or source_type,
                        role=str(
                            item.get("role")
                            or item.get("metadata", {}).get("role")
                            or item.get("metadata", {}).get("author_role")
                            or item.get("metadata", {}).get("speaker_role")
                            or ("memory" if is_memory_search else "retrieval")
                        ).strip()
                        or ("memory" if is_memory_search else "retrieval"),
                        thread_id=source_thread_id,
                        project_id=project_id,
                        retrieval_lane=retrieval_lane,
                        score=score_value,
                        policy_reason=policy_reason,
                        retrieval_policy=dict(retrieval_policy or {}),
                    )
                )
            return annotated

        primary_annotated_hits = _annotate_hits(
            primary_hits[:k],
            retrieval_lane=primary_lane,
            policy_reason=primary_policy_reason,
            source_thread_id=thread_id,
        )

        if not widening_enabled:
            diagnostics.update(
                status="contributed" if primary_hits else "attempted_no_hits",
                reason=(
                    "local_hits"
                    if primary_hits
                    else search_trace.get("reason", "no_hits")
                ),
                result_count=len(primary_annotated_hits),
                candidate_thread_count=0,
                widened=False,
            )
            return (
                self._sort_retrieval_items(primary_annotated_hits),
                WIDEN_REASON_NONE,
                diagnostics,
            )
        if widen_reason == WIDEN_REASON_NONE:
            diagnostics.update(
                status="contributed" if primary_hits else "attempted_no_hits",
                reason=(
                    "local_hits"
                    if primary_hits
                    else search_trace.get("reason", "no_hits")
                ),
                result_count=len(primary_annotated_hits),
                candidate_thread_count=0,
                widened=False,
            )
            return (
                self._sort_retrieval_items(primary_annotated_hits),
                WIDEN_REASON_NONE,
                diagnostics,
            )

        candidate_threads = await self._list_widening_threads(
            thread_id=thread_id,
            user_id=user_id,
            project_id=project_id,
            source_mode=normalized_source_mode,
        )
        diagnostics["candidate_thread_count"] = len(candidate_threads)
        if not candidate_threads:
            if primary_hits:
                diagnostics.update(
                    status="contributed",
                    reason="local_hits",
                    result_count=len(primary_annotated_hits),
                    widened=False,
                )
            else:
                diagnostics.update(
                    status=(
                        "skipped"
                        if not user_id
                        or (
                            normalized_source_mode == SOURCE_MODE_PROJECT
                            and project_id is None
                        )
                        else "no_eligible_candidates"
                    ),
                    reason=(
                        "boundary_blocked"
                        if not user_id
                        or (
                            normalized_source_mode == SOURCE_MODE_PROJECT
                            and project_id is None
                        )
                        else "no_eligible_candidates"
                    ),
                )
            return (
                self._sort_retrieval_items(primary_annotated_hits),
                WIDEN_REASON_NONE,
                diagnostics,
            )

        merged_hits = self._seed_thread_hits_for_widening(
            primary_annotated_hits,
            target_count=k,
            widen_reason=widen_reason,
        )
        widened_executed = False
        candidate_hit_count = 0

        for thread in candidate_threads:
            candidate_id = _coerce_int(thread.get("id"))
            if candidate_id is None:
                continue
            remaining_slots = max(k - len(merged_hits), 0)
            if (
                remaining_slots <= 0
                and widen_reason != WIDEN_REASON_LOW_CONFIDENCE_THREAD_HITS
            ):
                break
            request_k = remaining_slots if remaining_slots > 0 else 1
            try:
                outcome = await search_fn(
                    query,
                    request_k,
                    namespace=_thread_namespace(candidate_id),
                    user_id=user_id,
                )
            except Exception as exc:
                diagnostics.update(
                    status="failed",
                    reason="candidate_search_error",
                    error=str(exc),
                )
                break
            hits, _candidate_trace = self._unpack_search_output(outcome)
            if not hits:
                continue
            widened_executed = True
            candidate_hit_count += len(hits)
            candidate_hits = _annotate_hits(
                hits,
                retrieval_lane=(
                    "memory"
                    if is_memory_search
                    else "candidate_thread_semantic"
                ),
                policy_reason=widen_reason or "widened_by_policy",
                source_thread_id=candidate_id,
            )
            merged_hits = self._dedupe_retrieval_items(
                [*merged_hits, *candidate_hits]
            )[:k]
            if len(merged_hits) >= k:
                break

        final_hits = (
            self._sort_retrieval_items(merged_hits)[:k]
            if widened_executed
            else self._sort_retrieval_items(primary_annotated_hits)
        )
        effective_widen_reason = (
            WIDEN_REASON_EXPLICIT_PERSONAL_KNOWLEDGE
            if widened_executed
            and normalized_source_mode == SOURCE_MODE_PERSONAL_KNOWLEDGE
            else (widen_reason if widened_executed else WIDEN_REASON_NONE)
        )
        if diagnostics.get("status") == "failed":
            diagnostics.update(
                widened=widened_executed,
                candidate_hit_count=candidate_hit_count,
                result_count=len(final_hits),
            )
            return final_hits, effective_widen_reason, diagnostics
        diagnostics.update(
            widened=widened_executed,
            candidate_hit_count=candidate_hit_count,
            result_count=len(final_hits),
            status="contributed" if final_hits else "attempted_no_hits",
            reason=(
                "widened"
                if widened_executed
                else (search_trace.get("reason") or "candidate_search_no_hits")
            ),
        )
        return final_hits, effective_widen_reason, diagnostics

    async def _list_widening_threads(
        self,
        *,
        thread_id: int,
        user_id: Optional[str],
        project_id: Optional[int],
        source_mode: str,
    ) -> List[Dict[str, Any]]:
        normalized_source_mode = normalize_source_mode(source_mode)
        if not user_id:
            return []
        if normalized_source_mode == SOURCE_MODE_CONVERSATION:
            return []
        if normalized_source_mode == SOURCE_MODE_OBSIDIAN_ONLY:
            return []
        if normalized_source_mode == SOURCE_MODE_PROJECT and project_id is None:
            return []

        list_threads = getattr(self.chatlog, "list_chat_threads", None)
        if not callable(list_threads):
            return []

        scoped_project_id = (
            project_id
            if normalized_source_mode == SOURCE_MODE_PROJECT
            else None
        )
        try:
            threads = list_threads(
                limit=_THREAD_CANDIDATE_LIMIT,
                offset=0,
                user_id=user_id,
                project_id=scoped_project_id,
            )
        except TypeError:
            try:
                threads = list_threads(limit=_THREAD_CANDIDATE_LIMIT, offset=0)
            except TypeError:
                threads = list_threads()
        if hasattr(threads, "__await__"):
            threads = await threads
        if not isinstance(threads, list):
            return []

        same_project_threads: List[Dict[str, Any]] = []
        cross_project_threads: List[Dict[str, Any]] = []
        for thread in threads:
            if not self._is_eligible_widening_thread(
                thread,
                thread_id=thread_id,
                user_id=user_id,
                project_id=project_id,
                source_mode=normalized_source_mode,
            ):
                continue
            thread_project_id = _coerce_int(thread.get("project_id"))
            if project_id is not None and thread_project_id == project_id:
                same_project_threads.append(thread)
            else:
                cross_project_threads.append(thread)

        if normalized_source_mode == SOURCE_MODE_PROJECT:
            return same_project_threads
        return same_project_threads + cross_project_threads

    def _is_eligible_widening_thread(
        self,
        thread: Any,
        *,
        thread_id: int,
        user_id: str,
        project_id: Optional[int],
        source_mode: str,
    ) -> bool:
        if not isinstance(thread, dict):
            return False
        if normalize_source_mode(source_mode) == SOURCE_MODE_CONVERSATION:
            return False
        candidate_id = _coerce_int(thread.get("id"))
        if candidate_id is None or candidate_id == thread_id:
            return False
        candidate_user_id = str(thread.get("user_id") or "").strip()
        if not candidate_user_id or candidate_user_id != user_id:
            return False
        if thread.get("archived_at"):
            return False
        if bool(thread.get("exclude_from_identity")):
            return False
        if bool(thread.get("modeling_excluded")):
            return False
        if normalize_source_mode(source_mode) == SOURCE_MODE_PROJECT:
            return _coerce_int(thread.get("project_id")) == project_id
        return True

    def _determine_widen_reason(
        self, hits: List[Dict[str, Any]], target_count: int
    ) -> str:
        if target_count <= 0:
            return WIDEN_REASON_NONE
        limited_hits = list(hits[:target_count])
        if len(limited_hits) < target_count:
            return WIDEN_REASON_INSUFFICIENT_THREAD_HITS
        best_score = self._best_numeric_score(limited_hits)
        if (
            best_score is not None
            and best_score < _LOW_CONFIDENCE_SCORE_THRESHOLD
        ):
            return WIDEN_REASON_LOW_CONFIDENCE_THREAD_HITS
        return WIDEN_REASON_NONE

    def _seed_thread_hits_for_widening(
        self,
        hits: List[Dict[str, Any]],
        *,
        target_count: int,
        widen_reason: str,
    ) -> List[Dict[str, Any]]:
        limited_hits = self._dedupe_retrieval_items(hits[:target_count])
        if (
            widen_reason == WIDEN_REASON_LOW_CONFIDENCE_THREAD_HITS
            and target_count > 0
            and len(limited_hits) >= target_count
        ):
            preserve_count = max(target_count - 1, 0)
            return limited_hits[:preserve_count]
        return limited_hits[:target_count]

    def _best_numeric_score(
        self, hits: List[Dict[str, Any]]
    ) -> Optional[float]:
        scores: List[float] = []
        for item in hits:
            raw_score = item.get("score")
            try:
                if isinstance(raw_score, bool):
                    continue
                scores.append(float(raw_score))
            except (TypeError, ValueError):
                continue
        if not scores:
            return None
        return max(scores)

    def _dedupe_retrieval_items(
        self, hits: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        deduped: List[Dict[str, Any]] = []
        seen: set[str] = set()
        for item in hits:
            key = self._retrieval_item_key(item, len(deduped))
            if key in seen:
                continue
            seen.add(key)
            deduped.append(item)
        return deduped

    def _retrieval_item_key(
        self, item: Dict[str, Any], fallback_index: int
    ) -> str:
        metadata = item.get("metadata")
        if not isinstance(metadata, dict):
            metadata = item.get("meta")
        if isinstance(metadata, dict):
            for key in ("source_message_id", "message_id", "id", "chunk_id"):
                value = metadata.get(key)
                if value not in (None, ""):
                    return f"meta:{key}:{value}"
        item_id = item.get("id")
        if item_id not in (None, ""):
            return f"id:{item_id}"
        text = str(item.get("text") or "").strip()
        if text:
            return f"text:{text[:240]}"
        return f"fallback:{fallback_index}"

    def _merge_widen_reason(self, *reasons: str) -> str:
        priority = {
            WIDEN_REASON_NONE: 0,
            WIDEN_REASON_INSUFFICIENT_THREAD_HITS: 1,
            WIDEN_REASON_LOW_CONFIDENCE_THREAD_HITS: 2,
            WIDEN_REASON_EXPLICIT_PERSONAL_KNOWLEDGE: 3,
            WIDEN_REASON_EXPLICIT_WORKSPACE: 4,
        }
        selected = WIDEN_REASON_NONE
        for reason in reasons:
            normalized_reason = normalize_widen_reason(reason)
            if priority.get(normalized_reason, -1) > priority[selected]:
                selected = normalized_reason
        return selected

    async def get_scoped_documents(
        self,
        *,
        thread_id: int,
        user_id: str,
        project_id: Optional[int] = None,
        k_project_docs: int = 4,
        k_thread_docs: int = 4,
        doc_excerpt_chars: int = 420,
        include_project_docs: bool = True,
        include_thread_docs: bool = True,
        retrieval_policy: dict[str, Any] | None = None,
    ) -> Dict[str, List[Dict[str, Any]]]:
        """Fetch scoped document excerpts for RAG with project-first priority."""
        resolved_project_id = await self._resolve_project_id(
            thread_id=thread_id, project_id=project_id
        )
        return self._fetch_scoped_documents(
            thread_id=thread_id,
            project_id=resolved_project_id,
            user_id=user_id,
            k_project_docs=k_project_docs,
            k_thread_docs=k_thread_docs,
            doc_excerpt_chars=doc_excerpt_chars,
            include_project_docs=include_project_docs,
            include_thread_docs=include_thread_docs,
            retrieval_policy=retrieval_policy,
        )

    async def _resolve_project_id(
        self, *, thread_id: int, project_id: Optional[int]
    ) -> Optional[int]:
        explicit_project = _coerce_int(project_id)
        if explicit_project is not None:
            return explicit_project

        getter = getattr(self.chatlog, "get_chat_thread", None)
        if not callable(getter):
            return None

        try:
            thread = getter(thread_id)
            if hasattr(thread, "__await__"):
                thread = await thread
            if isinstance(thread, dict):
                return _coerce_int(thread.get("project_id"))
        except Exception as exc:
            logger.debug(
                "[ContextBroker] Failed to resolve project_id for thread %s: %s",
                thread_id,
                exc,
            )
        return None

    def _fetch_scoped_documents(
        self,
        *,
        thread_id: int,
        project_id: Optional[int],
        user_id: str,
        k_project_docs: int,
        k_thread_docs: int,
        doc_excerpt_chars: int,
        include_project_docs: bool,
        include_thread_docs: bool,
        retrieval_policy: dict[str, Any] | None = None,
    ) -> Dict[str, List[Dict[str, Any]]]:
        docs: Dict[str, List[Dict[str, Any]]] = {
            "project": [],
            "thread": [],
            "global": [],
        }

        session_provider = self._resolve_session_provider()
        if session_provider is None:
            return docs

        try:
            from guardian.db.models import (
                GeneratedDocument,
                ProjectDocumentLink,
                ThreadDocument,
                UploadedDocument,
            )
        except Exception as exc:
            logger.debug(
                "[ContextBroker] Document models unavailable; skipping doc retrieval: %s",
                exc,
            )
            return docs

        session = None
        try:
            session = session_provider()
            if hasattr(session, "__enter__") and hasattr(session, "__exit__"):
                with session as managed_session:
                    if include_project_docs:
                        docs["project"] = self._query_project_docs(
                            managed_session,
                            project_id=project_id,
                            user_id=user_id,
                            k_docs=k_project_docs,
                            doc_excerpt_chars=doc_excerpt_chars,
                            generated_model=GeneratedDocument,
                            uploaded_model=UploadedDocument,
                            project_link_model=ProjectDocumentLink,
                            retrieval_policy=retrieval_policy,
                        )
                    if include_thread_docs:
                        docs["thread"] = self._query_thread_docs(
                            managed_session,
                            thread_id=thread_id,
                            user_id=user_id,
                            k_docs=k_thread_docs,
                            doc_excerpt_chars=doc_excerpt_chars,
                            generated_model=GeneratedDocument,
                            uploaded_model=UploadedDocument,
                            thread_link_model=ThreadDocument,
                            retrieval_policy=retrieval_policy,
                        )
                return docs

            if include_project_docs:
                docs["project"] = self._query_project_docs(
                    session,
                    project_id=project_id,
                    user_id=user_id,
                    k_docs=k_project_docs,
                    doc_excerpt_chars=doc_excerpt_chars,
                    generated_model=GeneratedDocument,
                    uploaded_model=UploadedDocument,
                    project_link_model=ProjectDocumentLink,
                    retrieval_policy=retrieval_policy,
                )
            if include_thread_docs:
                docs["thread"] = self._query_thread_docs(
                    session,
                    thread_id=thread_id,
                    user_id=user_id,
                    k_docs=k_thread_docs,
                    doc_excerpt_chars=doc_excerpt_chars,
                    generated_model=GeneratedDocument,
                    uploaded_model=UploadedDocument,
                    thread_link_model=ThreadDocument,
                    retrieval_policy=retrieval_policy,
                )
        except Exception as exc:
            logger.warning(
                "[ContextBroker] Scoped document retrieval failed thread=%s project=%s err=%s",
                thread_id,
                project_id,
                exc,
            )
        finally:
            if session is not None and hasattr(session, "close"):
                try:
                    session.close()
                except Exception:
                    pass

        return docs

    def _query_project_docs(
        self,
        session: Any,
        *,
        project_id: Optional[int],
        user_id: str,
        k_docs: int,
        doc_excerpt_chars: int,
        generated_model: Any,
        uploaded_model: Any,
        project_link_model: Any,
        retrieval_policy: dict[str, Any] | None = None,
    ) -> List[Dict[str, Any]]:
        if project_id is None or k_docs <= 0:
            return []

        links = (
            session.query(project_link_model)
            .filter(project_link_model.project_id == project_id)
            .filter(project_link_model.is_enabled.is_(True))
            .order_by(project_link_model.attached_at.desc())
            .limit(max(k_docs * 4, k_docs))
            .all()
        )

        docs: List[Dict[str, Any]] = []
        seen: set[tuple[str, str]] = set()
        for link in links:
            doc_type = self._normalize_doc_type(
                getattr(link, "document_type", "")
            )
            doc_id = str(getattr(link, "document_id", "") or "")
            if not doc_type or not doc_id:
                continue
            dedupe_key = (doc_type, doc_id)
            if dedupe_key in seen:
                continue

            loaded = self._load_doc_by_type(
                session=session,
                doc_id=doc_id,
                doc_type=doc_type,
                user_id=user_id,
                generated_model=generated_model,
                uploaded_model=uploaded_model,
            )
            if not loaded:
                continue
            seen.add(dedupe_key)
            docs.append(
                self._serialize_doc_record(
                    row=loaded,
                    doc_type=doc_type,
                    scope="project",
                    excerpt_chars=doc_excerpt_chars,
                    relation="project_library",
                    attached_at=getattr(link, "attached_at", None),
                    attached_by=getattr(link, "attached_by", None),
                    retrieval_policy=retrieval_policy,
                )
            )
            if len(docs) >= k_docs:
                break
        return docs

    def _query_thread_docs(
        self,
        session: Any,
        *,
        thread_id: int,
        user_id: str,
        k_docs: int,
        doc_excerpt_chars: int,
        generated_model: Any,
        uploaded_model: Any,
        thread_link_model: Any,
        retrieval_policy: dict[str, Any] | None = None,
    ) -> List[Dict[str, Any]]:
        if k_docs <= 0:
            return []

        links = (
            session.query(thread_link_model)
            .filter(thread_link_model.thread_id == thread_id)
            .order_by(thread_link_model.created_at.desc())
            .limit(max(k_docs * 4, k_docs))
            .all()
        )

        docs: List[Dict[str, Any]] = []
        seen: set[str] = set()
        for link in links:
            doc_id = str(getattr(link, "document_id", "") or "")
            if not doc_id or doc_id in seen:
                continue

            loaded = self._load_doc_from_thread_link(
                session=session,
                doc_id=doc_id,
                user_id=user_id,
                generated_model=generated_model,
                uploaded_model=uploaded_model,
            )
            if not loaded:
                continue

            row, doc_type = loaded
            seen.add(doc_id)
            docs.append(
                self._serialize_doc_record(
                    row=row,
                    doc_type=doc_type,
                    scope="thread",
                    excerpt_chars=doc_excerpt_chars,
                    relation=str(
                        getattr(link, "relation", "attached") or "attached"
                    ),
                    attached_at=getattr(link, "created_at", None),
                    attached_by=None,
                    retrieval_policy=retrieval_policy,
                )
            )
            if len(docs) >= k_docs:
                break
        return docs

    def _load_doc_by_type(
        self,
        *,
        session: Any,
        doc_id: str,
        doc_type: str,
        user_id: str,
        generated_model: Any,
        uploaded_model: Any,
    ) -> Any | None:
        if doc_type == "generated":
            row = (
                session.query(generated_model)
                .filter(generated_model.id == doc_id)
                .first()
            )
            if row and getattr(row, "deleted_at", None) is None:
                row_user_id = str(getattr(row, "user_id", "") or "").strip()
                if row_user_id != str(user_id).strip():
                    return None
                return row
            return None

        row = (
            session.query(uploaded_model)
            .filter(uploaded_model.id == doc_id)
            .first()
        )
        if row and getattr(row, "deleted_at", None) is None:
            row_user_id = str(getattr(row, "user_id", "") or "").strip()
            if row_user_id != str(user_id).strip():
                return None
            return row
        return None

    def _load_doc_from_thread_link(
        self,
        *,
        session: Any,
        doc_id: str,
        user_id: str,
        generated_model: Any,
        uploaded_model: Any,
    ) -> tuple[Any, str] | None:
        generated = self._load_doc_by_type(
            session=session,
            doc_id=doc_id,
            doc_type="generated",
            user_id=user_id,
            generated_model=generated_model,
            uploaded_model=uploaded_model,
        )
        if generated is not None:
            return generated, "generated"

        uploaded = self._load_doc_by_type(
            session=session,
            doc_id=doc_id,
            doc_type="uploaded",
            user_id=user_id,
            generated_model=generated_model,
            uploaded_model=uploaded_model,
        )
        if uploaded is not None:
            return uploaded, "uploaded"

        return None

    def _serialize_doc_record(
        self,
        *,
        row: Any,
        doc_type: str,
        scope: str,
        excerpt_chars: int,
        relation: str,
        attached_at: Any,
        attached_by: Any,
        retrieval_policy: dict[str, Any] | None = None,
    ) -> Dict[str, Any]:
        if doc_type == "generated":
            title = str(
                getattr(row, "title", "") or getattr(row, "id", "document")
            )
            raw_content = str(getattr(row, "content", "") or "")
            source = str(getattr(row, "model", "") or "generated")
            source_table = "generated_documents"
        else:
            title = str(
                getattr(row, "filename", "") or getattr(row, "id", "document")
            )
            raw_content = str(getattr(row, "parsed_text", "") or "")
            source = str(
                getattr(row, "source_tag", "")
                or getattr(row, "mime_type", "")
                or "uploaded"
            )
            source_table = "uploaded_documents"

        scope_lane = f"{scope}_docs"
        return {
            "id": str(getattr(row, "id", "")),
            "title": title,
            "excerpt": self._build_excerpt(raw_content, excerpt_chars),
            "scope": scope,
            "document_type": doc_type,
            "source_table": source_table,
            "source": source,
            "source_type": doc_type,
            "role": "document",
            "project_id": _coerce_int(getattr(row, "project_id", None)),
            "thread_id": _coerce_int(getattr(row, "thread_id", None)),
            "user_id": getattr(row, "user_id", None),
            "created_at": self._to_iso(getattr(row, "created_at", None)),
            "retrieval_lane": scope_lane,
            "policy_reason": relation,
            "retrieval_policy": dict(retrieval_policy or {}),
            "provenance": {
                "relation": relation,
                "attached_at": self._to_iso(attached_at),
                "attached_by": attached_by,
                "source_tag": getattr(row, "source_tag", None),
                "model": getattr(row, "model", None),
            },
        }

    def _build_excerpt(self, raw_content: str, max_chars: int) -> str:
        content = str(raw_content or "").strip()
        if not content:
            return ""
        if max_chars <= 0:
            return ""
        if len(content) <= max_chars:
            return content
        return content[:max_chars].rstrip() + "..."

    def _to_iso(self, value: Any) -> Optional[str]:
        if value is None:
            return None
        if hasattr(value, "isoformat"):
            try:
                return value.isoformat()
            except Exception:
                return str(value)
        return str(value)

    def _normalize_doc_type(self, value: Any) -> Optional[str]:
        normalized = str(value or "").strip().lower()
        if normalized.startswith("gen"):
            return "generated"
        if normalized.startswith("up"):
            return "uploaded"
        return None

    def _resolve_session_provider(self) -> Optional[Any]:
        """Find a callable that yields a SQLAlchemy session."""
        if self.chatlog is None:
            return None

        explicit = getattr(self.chatlog, "get_session", None)
        if callable(explicit):
            return explicit

        sa_session = getattr(self.chatlog, "_sa_session", None)
        if callable(sa_session):
            return sa_session

        session_local = getattr(self.chatlog, "_SessionLocal", None)
        if session_local is not None:
            return lambda: session_local()

        return None

    async def _snapshot_sensors(self) -> Dict[str, Any]:
        """Snapshot current system sensors state."""
        if self.sensors and hasattr(self.sensors, "snapshot"):
            result = self.sensors.snapshot()
            # Handle both sync and async returns
            if hasattr(result, "__await__"):
                return await result
            return result if isinstance(result, dict) else {}
        return {}

    async def _search_federated(
        self, query: str, k: int
    ) -> List[Dict[str, Any]]:
        """Search for context from federated peer nodes.

        This method calls the federated context search API if available.

        Args:
            query: Query string
            k: Number of results to fetch

        Returns:
            List of federated search results
        """
        try:
            # Try to import and call the federation context API
            from guardian.routes.federation_context import _search_peers

            results = await _search_peers(query, k)
            return results if isinstance(results, list) else []
        except ImportError:
            logger.debug("Federation context module not available")
            return []
        except Exception as e:
            logger.warning(f"Error searching federated peers: {e}")
            return []

    async def _get_graph_context(
        self, *, user_id: str, thread_id: Optional[str]
    ) -> tuple[List[Dict[str, Any]], Dict[str, Any]]:
        """Fetch lightweight graph context for a thread/user pair."""
        trace: Dict[str, Any] = {
            "attempted": False,
            "status": "skipped",
            "reason": "disabled",
            "count": 0,
            "scope": None,
        }
        try:
            from neomodel import db as neo_db

            from guardian.graph.connection import connect_neo4j
        except Exception as exc:  # pragma: no cover - optional dependency
            logger.debug("[ContextBroker] Graph modules unavailable: %s", exc)
            trace.update(reason="modules_unavailable", error=str(exc))
            return [], trace

        try:
            connect_neo4j()
            trace["attempted"] = True

            def _rows_to_snippets(
                rows: Any, meta: Any, scope: str
            ) -> List[Dict[str, Any]]:
                columns = (
                    [str(column) for column in meta]
                    if isinstance(meta, (list, tuple))
                    else []
                )
                snippets: List[Dict[str, Any]] = []
                if not isinstance(rows, list):
                    return snippets
                for row in rows:
                    if isinstance(row, dict):
                        record = row
                    elif isinstance(row, (list, tuple)):
                        if columns:
                            record = {
                                columns[idx]: row[idx]
                                for idx in range(min(len(columns), len(row)))
                            }
                        else:
                            record = {
                                str(idx): value for idx, value in enumerate(row)
                            }
                    else:
                        continue

                    snippet: Dict[str, Any] = {
                        "kind": "graph-fact",
                        "text": str(record.get("content") or ""),
                        "source": "neo4j",
                        "message_id": str(record.get("message_id") or ""),
                        "scope": scope,
                    }
                    created_at = record.get("created_at")
                    if created_at not in (None, ""):
                        snippet["created_at"] = _coerce_graph_value(created_at)
                    thread_value = record.get("thread_id")
                    if thread_value not in (None, ""):
                        snippet["thread_id"] = str(thread_value)
                    user_value = record.get("user_id")
                    if user_value not in (None, ""):
                        snippet["user_id"] = str(user_value)
                    snippets.append(snippet)
                return snippets

            if thread_id:
                rows, meta = neo_db.cypher_query(
                    """
                    MATCH (t:ThreadNode {thread_id: $thread_id})
                    <-[:PART_OF]-(m:MessageNode)
                    OPTIONAL MATCH (m)-[:SENT_BY]->(u:UserNode)
                    RETURN m.message_id AS message_id,
                           m.content AS content,
                           m.created_at AS created_at,
                           t.thread_id AS thread_id,
                           u.user_id AS user_id
                    ORDER BY m.created_at ASC
                    """,
                    {"thread_id": str(thread_id)},
                )
                snippets = _rows_to_snippets(rows, meta, "thread")
                if snippets:
                    trace.update(
                        status="contributed",
                        reason="thread_match",
                        scope="thread",
                        count=len(snippets),
                    )
                    return snippets, trace

            if user_id:
                rows, meta = neo_db.cypher_query(
                    """
                    MATCH (u:UserNode {user_id: $user_id})
                    <-[:SENT_BY]-(m:MessageNode)
                    OPTIONAL MATCH (m)-[:PART_OF]->(t:ThreadNode)
                    RETURN m.message_id AS message_id,
                           m.content AS content,
                           m.created_at AS created_at,
                           t.thread_id AS thread_id,
                           u.user_id AS user_id
                    ORDER BY m.created_at ASC
                    """,
                    {"user_id": str(user_id)},
                )
                snippets = _rows_to_snippets(rows, meta, "user")
                if snippets:
                    trace.update(
                        status="contributed",
                        reason="user_match",
                        scope="user",
                        count=len(snippets),
                    )
                    return snippets, trace

            trace.update(status="empty", reason="no_rows")
            return [], trace
        except Exception as exc:
            logger.warning(
                "[ContextBroker] Graph context unavailable; proceeding without it: %s",
                exc,
            )
            trace.update(
                attempted=True,
                status="failed",
                reason="query_error",
                error=str(exc),
            )
            return [], trace
