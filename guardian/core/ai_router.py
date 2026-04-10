import inspect
import json
import logging
from dataclasses import dataclass
from typing import Any, Dict, Optional
from urllib.parse import urlparse

import requests
from fastapi import HTTPException
from requests import exceptions as req_exc

from guardian.core.config import Settings, get_settings
from guardian.core.egress import EgressDeniedError, assert_egress_allowed
from guardian.core.event_contracts import _coerce_text
from guardian.core.provider_registry import (
    default_model_for_provider,
    normalize_model_id,
)
from guardian.core.provider_registry import (
    normalize_provider as normalize_registry_provider,
)
from guardian.core.provider_registry import (
    provider_routing_requires_discovered_inventory,
    validate_provider_model_selection,
)

logger = logging.getLogger(__name__)

_DEFAULT_OPENAI_BASE = "https://api.openai.com"
_DEFAULT_GROQ_BASE = "https://api.groq.com"
_DEFAULT_MINIMAX_BASE = "https://api.minimax.io/v1"
_DEFAULT_ALIBABA_BASE = "https://coding-intl.dashscope.aliyuncs.com/v1"
_DEFAULT_LOCAL_DOCKER_FALLBACK_BASE = "http://host.docker.internal:11434"
_LOCAL_LOOPBACK_HOSTS = frozenset({"localhost", "127.0.0.1", "::1", "0.0.0.0"})
LOCAL_MODEL_RESOLUTION_ERROR = "local_model_resolution_error"
LOCAL_MODEL_MISSING_FAILURE_KIND = "local_model_missing"
LOCAL_MODEL_UNAVAILABLE_FAILURE_KIND = "local_model_unavailable"


@dataclass(frozen=True)
class LocalRuntimePolicy:
    profile: str
    connect_timeout_seconds: float
    read_timeout_seconds: float
    timeout_source: str
    thinking_mode: bool
    profile_reason: str | None = None

    @property
    def request_timeout(self) -> tuple[float, float]:
        return (
            self.connect_timeout_seconds,
            self.read_timeout_seconds,
        )

    def as_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "profile": self.profile,
            "connect_timeout_seconds": self.connect_timeout_seconds,
            "read_timeout_seconds": self.read_timeout_seconds,
            "timeout_source": self.timeout_source,
            "thinking_mode": self.thinking_mode,
        }
        if self.profile_reason:
            payload["profile_reason"] = self.profile_reason
        return payload


@dataclass(frozen=True)
class LocalReasoningDirective:
    mode: str
    source: str
    instruction: str | None = None
    profile_reason: str | None = None

    def as_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "mode": self.mode,
            "source": self.source,
        }
        if self.instruction:
            payload["instruction"] = self.instruction
        if self.profile_reason:
            payload["profile_reason"] = self.profile_reason
        return payload


class ProviderResponse(str):
    """String-compatible provider result that preserves raw upstream data."""

    def __new__(
        cls,
        text: str,
        *,
        raw_payload: Any | None = None,
        content_blocks: Any | None = None,
        provider: str | None = None,
    ):
        obj = super().__new__(cls, text or "")
        obj.raw_payload = raw_payload  # type: ignore[attr-defined]
        obj.content_blocks = content_blocks  # type: ignore[attr-defined]
        obj.provider = provider  # type: ignore[attr-defined]
        return obj


@dataclass(frozen=True)
class LocalEndpointCandidate:
    base_url: str
    label: str
    source: str


@dataclass(frozen=True)
class LocalModelResolution:
    model: str | None
    source: str | None
    strict: bool
    requested_model: str | None = None
    failure_kind: str | None = None
    message: str | None = None
    endpoint_resolution: dict[str, Any] | None = None

    @property
    def ok(self) -> bool:
        return bool(self.model) and not self.failure_kind

    def as_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "strict": self.strict,
            "source": self.source,
            "model": self.model,
        }
        if self.requested_model:
            payload["requested_model"] = self.requested_model
        if self.failure_kind:
            payload["failure_kind"] = self.failure_kind
            payload["error"] = LOCAL_MODEL_RESOLUTION_ERROR
        if self.message:
            payload["message"] = self.message
        if self.endpoint_resolution is not None:
            payload["endpoint_resolution"] = dict(self.endpoint_resolution)
        return payload

    def error_detail(
        self,
        *,
        attempted_endpoints: list[str] | None = None,
        endpoint_resolution: dict[str, Any] | None = None,
        failure_kind: str | None = None,
        message: str | None = None,
    ) -> dict[str, Any]:
        detail: dict[str, Any] = {
            "error": LOCAL_MODEL_RESOLUTION_ERROR,
            "provider": "local",
            "failure_kind": (
                str(failure_kind or self.failure_kind or "").strip()
                or LOCAL_MODEL_UNAVAILABLE_FAILURE_KIND
            ),
            "message": (
                str(message or self.message or "").strip()
                or "Local model resolution failed"
            ),
        }
        if self.model:
            detail["model"] = self.model
        if self.source:
            detail["configured_source"] = self.source
        if self.requested_model:
            detail["requested_model"] = self.requested_model
        resolved_endpoint = endpoint_resolution or self.endpoint_resolution
        if resolved_endpoint is not None:
            detail["endpoint_resolution"] = dict(resolved_endpoint)
        if attempted_endpoints:
            detail["attempted_endpoints"] = list(attempted_endpoints)
        return detail


def _normalize_provider(provider: Optional[str]) -> str:
    """
    Normalize provider identifiers coming from API/UI/config.

    Notes:
    - `auto` is accepted as an execution-time alias. Today it resolves to
      `local` (local-first + deterministic). This prevents config/UX mismatch
      from hard-failing completions when UI does not send an explicit provider.
    """
    return normalize_registry_provider(provider)


def _coerce_positive_timeout(raw: Any, default: float) -> float:
    try:
        value = float(raw)
    except (TypeError, ValueError):
        value = float(default)
    return max(0.1, value)


def _local_extended_thinking_patterns(settings: Settings) -> tuple[str, ...]:
    raw = str(
        getattr(settings, "LOCAL_EXTENDED_THINKING_MODEL_PATTERNS", "") or ""
    ).strip()
    if not raw:
        raw = "qwen3.5,qwen-3.5,qwen 3.5,qwen3,qwen-3,qwen 3,qwq"
    return tuple(
        part.strip().lower() for part in raw.split(",") if part and part.strip()
    )


def _local_no_think_patterns(settings: Settings) -> tuple[str, ...]:
    raw = str(
        getattr(settings, "LOCAL_NO_THINK_MODEL_PATTERNS", "") or ""
    ).strip()
    if not raw:
        raw = "qwen3.5,qwen-3.5,qwen 3.5,qwen3,qwen-3,qwen 3"
    return tuple(
        part.strip().lower() for part in raw.split(",") if part and part.strip()
    )


def _local_no_think_skip_patterns(settings: Settings) -> tuple[str, ...]:
    raw = str(
        getattr(settings, "LOCAL_NO_THINK_SKIP_MODEL_PATTERNS", "") or ""
    ).strip()
    if not raw:
        raw = (
            "thinking-2507,qwen3.5-thinking,qwen-3.5-thinking,"
            "qwen 3.5 thinking,qwen3-thinking,qwen-3-thinking,"
            "qwen 3 thinking,instruct-2507"
        )
    return tuple(
        part.strip().lower() for part in raw.split(",") if part and part.strip()
    )


def _match_pattern(
    value: str, patterns: tuple[str, ...]
) -> tuple[bool, str | None]:
    normalized = str(value or "").strip().lower()
    if not normalized:
        return False, None
    for pattern in patterns:
        if pattern in normalized:
            return True, pattern
    return False, None


def _matches_local_extended_thinking_profile(
    model: str, settings: Settings
) -> tuple[bool, str | None]:
    return _match_pattern(model, _local_extended_thinking_patterns(settings))


def resolve_local_reasoning_directive(
    model: str,
    *,
    settings: Optional[Settings] = None,
) -> LocalReasoningDirective:
    resolved = _resolve_settings(settings)
    if not bool(getattr(resolved, "LOCAL_DEFAULT_NO_THINK_ENABLED", True)):
        return LocalReasoningDirective(
            mode="default",
            source="config_disabled",
            profile_reason="LOCAL_DEFAULT_NO_THINK_ENABLED=false",
        )

    normalized_model = str(model or "").strip().lower()
    if not normalized_model:
        return LocalReasoningDirective(mode="default", source="model_missing")

    skip_match, skip_pattern = _match_pattern(
        normalized_model, _local_no_think_skip_patterns(resolved)
    )
    if skip_match:
        return LocalReasoningDirective(
            mode="default",
            source="model_skip_pattern",
            profile_reason=(
                "model matched LOCAL_NO_THINK_SKIP_MODEL_PATTERNS "
                f"via '{skip_pattern}'"
            ),
        )

    match, matched_pattern = _match_pattern(
        normalized_model, _local_no_think_patterns(resolved)
    )
    if not match:
        return LocalReasoningDirective(mode="default", source="default")

    instruction = (
        str(
            getattr(resolved, "LOCAL_NO_THINK_INSTRUCTION", "/no_think") or ""
        ).strip()
        or "/no_think"
    )
    return LocalReasoningDirective(
        mode="no_think",
        source="profile",
        instruction=instruction,
        profile_reason=(
            "model matched LOCAL_NO_THINK_MODEL_PATTERNS "
            f"via '{matched_pattern}'"
        ),
    )


def describe_local_reasoning(
    model: str,
    *,
    settings: Optional[Settings] = None,
) -> dict[str, Any]:
    return resolve_local_reasoning_directive(model, settings=settings).as_dict()


def _resolve_reasoning_override_instruction(
    reasoning_mode: Optional[str],
    settings: Settings,
) -> LocalReasoningDirective | None:
    normalized = str(reasoning_mode or "").strip().lower()
    if not normalized or normalized == "default":
        return None
    if normalized in {"no_think", "fast", "/no_think"}:
        instruction = (
            str(
                getattr(settings, "LOCAL_NO_THINK_INSTRUCTION", "/no_think")
                or ""
            ).strip()
            or "/no_think"
        )
        return LocalReasoningDirective(
            mode="no_think",
            source="request_override",
            instruction=instruction,
            profile_reason="reasoning_mode override requested fast mode",
        )
    if normalized in {"think", "/think"}:
        return LocalReasoningDirective(
            mode="think",
            source="request_override",
            instruction="/think",
            profile_reason="reasoning_mode override requested think mode",
        )
    return None


def _last_qwen_reasoning_instruction(
    messages: list[dict[str, Any]],
) -> str | None:
    latest_instruction: str | None = None
    latest_position = -1
    for message in messages:
        content = str(message.get("content") or "")
        no_think_position = content.rfind("/no_think")
        think_position = content.rfind("/think")
        if no_think_position > latest_position:
            latest_position = no_think_position
            latest_instruction = "/no_think"
        if think_position > latest_position:
            latest_position = think_position
            latest_instruction = "/think"
    return latest_instruction


def _clone_content_block(block: dict[str, Any]) -> dict[str, Any]:
    cloned = dict(block)
    image_url = cloned.get("image_url")
    if isinstance(image_url, dict):
        cloned["image_url"] = dict(image_url)
    source = cloned.get("source")
    if isinstance(source, dict):
        cloned["source"] = dict(source)
    return cloned


def _content_block_contains_image(block: dict[str, Any]) -> bool:
    block_type = str(block.get("type") or "").strip().lower()
    if block_type in {"image", "image_url"}:
        return True

    image_url = block.get("image_url")
    if isinstance(image_url, dict):
        url = str(image_url.get("url") or "").strip()
        if url:
            return True

    source = block.get("source")
    if isinstance(source, dict):
        source_type = str(source.get("type") or "").strip().lower()
        if block_type == "image" and source_type in {"base64", "url"}:
            return True

    return False


def _content_has_image_payload(content: Any) -> bool:
    if isinstance(content, list):
        return any(
            isinstance(item, dict) and _content_block_contains_image(item)
            for item in content
        )
    if isinstance(content, dict):
        return _content_block_contains_image(content)
    return False


def _append_reasoning_instruction(content: Any, instruction: str) -> Any:
    instruction_text = str(instruction or "").strip()
    if not instruction_text:
        return content

    if isinstance(content, list):
        cloned_blocks: list[dict[str, Any]] = []
        for item in content:
            if not isinstance(item, dict):
                text = str(item or "").strip()
                if text:
                    cloned_blocks.append({"type": "text", "text": text})
                continue

            block = _clone_content_block(item)
            if str(block.get("type") or "").strip().lower() == "text":
                text = str(block.get("text") or "").strip()
                if instruction_text in text:
                    return content
                block["text"] = text
            cloned_blocks.append(block)

        if any(
            str(block.get("type") or "").strip().lower() == "text"
            and instruction_text in str(block.get("text") or "")
            for block in cloned_blocks
        ):
            return content

        cloned_blocks.append({"type": "text", "text": instruction_text})
        return cloned_blocks

    text = str(content or "").strip()
    if not text:
        return instruction_text
    if instruction_text in text:
        return text
    return f"{text}\n\n{instruction_text}"


def _find_last_message_index(messages: list[dict[str, Any]], role: str) -> int:
    target_role = str(role or "").strip().lower()
    for index in range(len(messages) - 1, -1, -1):
        message = messages[index]
        if not isinstance(message, dict):
            continue
        if str(message.get("role") or "").strip().lower() == target_role:
            return index
    return -1


def apply_local_reasoning_directive(
    messages: list[dict[str, Any]],
    model: str,
    *,
    reasoning_mode: Optional[str] = None,
    settings: Optional[Settings] = None,
) -> tuple[list[dict[str, Any]], LocalReasoningDirective]:
    resolved = _resolve_settings(settings)
    directive = _resolve_reasoning_override_instruction(
        reasoning_mode, resolved
    ) or resolve_local_reasoning_directive(model, settings=resolved)
    if directive.mode == "default" or not directive.instruction:
        return messages, directive
    if _last_qwen_reasoning_instruction(messages) is not None:
        return messages, directive

    adapted = [
        dict(message)
        for message in (messages or [])
        if isinstance(message, dict)
    ]
    target_index = _find_last_message_index(adapted, "user")
    if target_index < 0:
        target_index = _find_last_message_index(adapted, "system")

    if target_index >= 0:
        target_message = dict(adapted[target_index])
        target_message["content"] = _append_reasoning_instruction(
            target_message.get("content"),
            directive.instruction,
        )
        adapted[target_index] = target_message
    else:
        adapted.append(
            {
                "role": "system",
                "content": directive.instruction,
            }
        )
    return adapted, directive


def _messages_contain_image_payload(messages: list[dict[str, Any]]) -> bool:
    for message in messages or []:
        if not isinstance(message, dict):
            continue
        if _content_has_image_payload(message.get("content")):
            return True
        images = message.get("images")
        if isinstance(images, list) and images:
            return True
    return False


def resolve_local_runtime_policy(
    model: str,
    *,
    settings: Optional[Settings] = None,
    timeout: Optional[float] = None,
) -> LocalRuntimePolicy:
    resolved = _resolve_settings(settings)
    connect_timeout = _coerce_positive_timeout(
        getattr(resolved, "LOCAL_REQUEST_CONNECT_TIMEOUT_SECONDS", 10.0),
        10.0,
    )

    default_read_timeout = _coerce_positive_timeout(
        getattr(resolved, "LLM_REQUEST_TIMEOUT_SECONDS", 60),
        60.0,
    )
    thinking_timeout = _coerce_positive_timeout(
        getattr(resolved, "LOCAL_EXTENDED_THINKING_TIMEOUT_SECONDS", 300.0),
        max(default_read_timeout, 300.0),
    )

    if timeout is not None:
        read_timeout = _coerce_positive_timeout(timeout, default_read_timeout)
        return LocalRuntimePolicy(
            profile="explicit_override",
            connect_timeout_seconds=connect_timeout,
            read_timeout_seconds=read_timeout,
            timeout_source="explicit",
            thinking_mode=False,
            profile_reason="explicit timeout override",
        )

    (
        is_thinking_model,
        matched_pattern,
    ) = _matches_local_extended_thinking_profile(model, resolved)
    if is_thinking_model:
        return LocalRuntimePolicy(
            profile="extended_thinking",
            connect_timeout_seconds=connect_timeout,
            read_timeout_seconds=max(default_read_timeout, thinking_timeout),
            timeout_source="profile",
            thinking_mode=True,
            profile_reason=(
                f"model matched LOCAL_EXTENDED_THINKING_MODEL_PATTERNS via '{matched_pattern}'"
            ),
        )

    return LocalRuntimePolicy(
        profile="default",
        connect_timeout_seconds=connect_timeout,
        read_timeout_seconds=default_read_timeout,
        timeout_source="default",
        thinking_mode=False,
    )


def describe_local_runtime(
    model: str,
    *,
    settings: Optional[Settings] = None,
    timeout: Optional[float] = None,
) -> dict[str, Any]:
    payload = resolve_local_runtime_policy(
        model, settings=settings, timeout=timeout
    ).as_dict()
    payload["reasoning"] = describe_local_reasoning(model, settings=settings)
    return payload


def _format_local_connect_error(
    url: str,
    err: Exception,
    *,
    model: str,
    runtime_policy: LocalRuntimePolicy,
) -> str:
    """Produce an actionable error message for local inference failures.

    Common pitfall: Docker containers often cannot resolve mDNS `.local` hostnames
    (e.g. `VaultNode.local`). In that case, use an IP address, a resolvable DNS
    name, or `host.docker.internal` (when the target is on the host).
    """

    message = str(err)
    lowered = message.lower()

    hints = []
    # DNS / name resolution
    if (
        "name or service not known" in lowered
        or "temporary failure in name resolution" in lowered
        or "nodename nor servname provided" in lowered
        or "failed to resolve" in lowered
    ):
        hints.append(
            "DNS resolution failed. If running inside Docker, mDNS `.local` names "
            "(e.g. VaultNode.local) often do not resolve. Use an IP address or a "
            "resolvable hostname; if the target is the host machine, try "
            "`host.docker.internal`."
        )

    # Connection refused / unreachable
    if "connection refused" in lowered:
        hints.append(
            "Connection refused. Check the remote server is listening on that port "
            "and is reachable from the backend container/network."
        )
    if (
        isinstance(err, req_exc.Timeout)
        or "timed out" in lowered
        or "timeout" in lowered
    ):
        timeout_kind = (
            "read timeout"
            if isinstance(err, req_exc.ReadTimeout)
            else "timeout"
        )
        profile_hint = (
            " If this local model intentionally spends a long time reasoning before streaming, "
            "increase LOCAL_EXTENDED_THINKING_TIMEOUT_SECONDS or extend "
            "LOCAL_EXTENDED_THINKING_MODEL_PATTERNS."
            if runtime_policy.thinking_mode
            else " Increase LLM_REQUEST_TIMEOUT_SECONDS if this model legitimately needs more time."
        )
        hints.append(
            f"{timeout_kind.title()} after connect={runtime_policy.connect_timeout_seconds:.1f}s "
            f"read={runtime_policy.read_timeout_seconds:.1f}s for model '{model}' "
            f"(profile={runtime_policy.profile}).{profile_hint}"
        )

    hint_text = " " + " ".join(hints) if hints else ""
    return (
        f"Local inference request failed for model '{model}' at {url}: "
        f"{message}.{hint_text}"
    ).strip()


def _resolve_settings(settings: Optional[Settings]) -> Settings:
    return settings or get_settings()


def _default_model_for_provider(provider: str, settings: Settings) -> str:
    return default_model_for_provider(provider, settings)


def _local_chat_model_is_authoritative(settings: Settings) -> bool:
    if bool(getattr(settings, "CODEXIFY_LOCAL_ONLY_MODE", False)):
        return True

    from guardian.core.supported_profile import get_active_supported_profile

    manifest = get_active_supported_profile()
    if manifest is None:
        return False
    return (
        _normalize_provider(manifest.provider_contract.get("LLM_PROVIDER"))
        == "local"
    )


def _local_execution_model_candidates(
    settings: Settings,
    *,
    requested_model: str | None = None,
) -> tuple[list[tuple[str, str]], bool]:
    strict = _local_chat_model_is_authoritative(settings)
    raw_candidates: tuple[tuple[str, Any], ...]
    if strict:
        raw_candidates = (
            ("LOCAL_CHAT_MODEL", getattr(settings, "LOCAL_CHAT_MODEL", None)),
        )
    else:
        raw_candidates = (
            ("requested_model", requested_model),
            ("LOCAL_LLM_MODEL", getattr(settings, "LOCAL_LLM_MODEL", None)),
            (
                "DEFAULT_LOCAL_MODEL",
                getattr(settings, "DEFAULT_LOCAL_MODEL", None),
            ),
            ("LLM_MODEL", getattr(settings, "LLM_MODEL", None)),
            ("LOCAL_CHAT_MODEL", getattr(settings, "LOCAL_CHAT_MODEL", None)),
        )

    candidates: list[tuple[str, str]] = []
    seen: set[str] = set()
    for source, candidate in raw_candidates:
        normalized = normalize_model_id(candidate)
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        candidates.append((normalized, source))
    return candidates, strict


def _configured_local_model_resolution(
    settings: Settings,
) -> tuple[str, str | None, bool]:
    candidates, strict = _local_execution_model_candidates(settings)
    if candidates:
        model, source = candidates[0]
        return model, source, strict
    return "", "LOCAL_CHAT_MODEL" if strict else None, strict


def resolve_local_execution_model(
    *,
    settings: Optional[Settings] = None,
    requested_model: str | None = None,
    validate_availability: bool = False,
    discovered_model_names: list[str] | None = None,
    endpoint_resolution: dict[str, Any] | None = None,
    timeout_seconds: float | None = None,
    request_get: Any = None,
) -> LocalModelResolution:
    resolved = _resolve_settings(settings)
    requested = normalize_model_id(requested_model)
    candidates, strict = _local_execution_model_candidates(
        resolved,
        requested_model=requested_model,
    )
    if not candidates:
        source_name = "LOCAL_CHAT_MODEL" if strict else "local_model"
        return LocalModelResolution(
            model=None,
            source=source_name,
            strict=strict,
            requested_model=requested or None,
            failure_kind=LOCAL_MODEL_MISSING_FAILURE_KIND,
            message=(
                f"{source_name} is not configured for local chat execution"
            ),
            endpoint_resolution=endpoint_resolution,
        )
    configured_model, source = candidates[0]

    resolved_endpoint = endpoint_resolution
    names = list(discovered_model_names or [])
    if validate_availability and resolved_endpoint is None:
        names, resolved_endpoint = discover_local_model_inventory(
            resolved,
            timeout_seconds=timeout_seconds or 1.5,
            request_get=request_get,
        )

    if (
        validate_availability
        and resolved_endpoint is not None
        and str(resolved_endpoint.get("state") or "").strip() == "available"
    ):
        available_models = {
            normalized
            for normalized in (
                normalize_model_id(item) for item in (names or [])
            )
            if normalized
        }
        if strict and configured_model not in available_models:
            return LocalModelResolution(
                model=configured_model,
                source=source,
                strict=strict,
                requested_model=requested or None,
                failure_kind=LOCAL_MODEL_UNAVAILABLE_FAILURE_KIND,
                message=(
                    f"Configured local chat model '{configured_model}' from "
                    f"{source} is not advertised by the reachable local runtime"
                ),
                endpoint_resolution=resolved_endpoint,
            )
        if not strict:
            for candidate_model, candidate_source in candidates:
                if candidate_model in available_models:
                    return LocalModelResolution(
                        model=candidate_model,
                        source=candidate_source,
                        strict=strict,
                        requested_model=requested or None,
                        endpoint_resolution=resolved_endpoint,
                    )
            return LocalModelResolution(
                model=configured_model,
                source=source,
                strict=strict,
                requested_model=requested or None,
                failure_kind=LOCAL_MODEL_UNAVAILABLE_FAILURE_KIND,
                message=(
                    "No runnable local model was found among the requested "
                    "or configured local candidates"
                ),
                endpoint_resolution=resolved_endpoint,
            )

    return LocalModelResolution(
        model=configured_model,
        source=source,
        strict=strict,
        requested_model=requested or None,
        endpoint_resolution=resolved_endpoint,
    )


def _provider_failure_detail(
    *,
    provider: str,
    model: str,
    endpoint: str,
    failure_kind: str,
    message: str,
    upstream_status: int | None = None,
    provider_error: str | None = None,
    transport_classification: str | None = None,
) -> dict[str, Any]:
    detail: dict[str, Any] = {
        "error": "provider_request_failed",
        "provider": provider,
        "model": model,
        "endpoint": endpoint,
        "failure_kind": failure_kind,
        "message": message,
    }
    if upstream_status is not None:
        detail["upstream_status"] = upstream_status
    if provider_error:
        detail["provider_error"] = provider_error
    if transport_classification:
        detail["transport_classification"] = transport_classification
    return detail


def _classify_transport_error(exc: Exception) -> str:
    lowered = str(exc or "").strip().lower()
    if isinstance(exc, req_exc.Timeout) or "timed out" in lowered:
        return "timeout"
    if "connection refused" in lowered:
        return "connection_refused"
    if "name or service not known" in lowered or "failed to resolve" in lowered:
        return "dns_error"
    return "request_error"


def _provider_transport_failure_kind(exc: Exception) -> str:
    classification = _classify_transport_error(exc)
    if classification == "timeout":
        return "provider_timeout"
    return "transport_error"


def _normalize_openai_model(model: str, settings: Settings) -> str:
    """Ensure we send a chat-compatible OpenAI model."""
    if model.startswith("gpt-4.1") or model.startswith("o3"):
        # Map responses-only models to a chat-compatible default for now.
        return settings.DEFAULT_OPENAI_MODEL
    return model


def build_openai_vision_content(
    text: str | None,
    image_urls: list[str] | None,
) -> list[dict[str, Any]]:
    """Build OpenAI-compatible multimodal content parts."""
    parts: list[dict[str, Any]] = []
    clean_text = str(text or "").strip()
    if clean_text:
        parts.append({"type": "text", "text": clean_text})
    for raw_url in image_urls or []:
        url = str(raw_url or "").strip()
        if not url:
            continue
        parts.append({"type": "image_url", "image_url": {"url": url}})
    if not parts:
        parts.append({"type": "text", "text": ""})
    return parts


def _filter_callable_kwargs(
    func: Any, kwargs: dict[str, Any]
) -> dict[str, Any]:
    """Drop keyword arguments unsupported by a callable.

    This keeps the dispatch layer backward-compatible with older test doubles
    while still allowing the production handlers to receive new runtime fields
    like temperature.
    """

    try:
        signature = inspect.signature(func)
    except (TypeError, ValueError):
        return dict(kwargs)

    parameters = signature.parameters.values()
    if any(param.kind == inspect.Parameter.VAR_KEYWORD for param in parameters):
        return dict(kwargs)

    allowed = {
        param.name
        for param in signature.parameters.values()
        if param.kind
        in {
            inspect.Parameter.POSITIONAL_OR_KEYWORD,
            inspect.Parameter.KEYWORD_ONLY,
        }
    }
    return {key: value for key, value in kwargs.items() if key in allowed}


def chat_with_ai(
    messages,
    model: Optional[str] = None,
    provider: Optional[str] = None,
    reasoning_mode: Optional[str] = None,
    temperature: Optional[float] = None,
    prompt_meta: Optional[dict[str, Any]] = None,
    settings: Optional[Settings] = None,
):
    settings = _resolve_settings(settings)
    provider_name = _normalize_provider(provider or settings.LLM_PROVIDER)
    target_model = model or _default_model_for_provider(provider_name, settings)
    local_model_resolution: LocalModelResolution | None = None

    if provider_name == "local":
        strict_local_chat = _local_chat_model_is_authoritative(settings)
        authoritative_model = normalize_model_id(
            getattr(settings, "LOCAL_CHAT_MODEL", None)
        )
        requested_model = normalize_model_id(target_model)
        local_model_resolution = resolve_local_execution_model(
            settings=settings,
            requested_model=target_model,
            validate_availability=bool(
                strict_local_chat
                and authoritative_model
                and authoritative_model != requested_model
            ),
        )
        if not local_model_resolution.ok:
            raise HTTPException(
                status_code=400,
                detail=local_model_resolution.error_detail(),
            )
        if local_model_resolution.strict or not target_model:
            target_model = local_model_resolution.model

    if not target_model:
        raise HTTPException(
            status_code=400,
            detail=(
                "No model configured for provider. Set LLM_MODEL or the provider-specific "
                "model setting (e.g. LOCAL_LLM_MODEL / DEFAULT_LOCAL_MODEL)."
            ),
        )

    if provider_routing_requires_discovered_inventory(provider_name):
        valid, reason = validate_provider_model_selection(
            provider_id=provider_name,
            model_id=target_model,
            settings=settings,
        )
        if not valid:
            raise HTTPException(
                status_code=400,
                detail=reason or "Provider/model selection is invalid",
            )

    if provider_name == "local":
        return call_local(
            messages,
            target_model,
            **_filter_callable_kwargs(
                call_local,
                {
                    "reasoning_mode": reasoning_mode,
                    "temperature": temperature,
                    "settings": settings,
                },
            ),
        )
    if provider_name == "groq":
        return call_groq(
            messages,
            target_model,
            **_filter_callable_kwargs(
                call_groq,
                {
                    "temperature": temperature,
                    "settings": settings,
                },
            ),
        )
    if provider_name == "openai":
        return call_openai(
            messages,
            _normalize_openai_model(target_model, settings),
            **_filter_callable_kwargs(
                call_openai,
                {
                    "temperature": temperature,
                    "settings": settings,
                },
            ),
        )
    if provider_name == "alibaba":
        return call_alibaba(
            messages,
            target_model,
            **_filter_callable_kwargs(
                call_alibaba,
                {
                    "temperature": temperature,
                    "settings": settings,
                },
            ),
        )
    if provider_name == "minimax":
        return call_minimax(
            messages,
            target_model,
            **_filter_callable_kwargs(
                call_minimax,
                {
                    "reasoning_mode": reasoning_mode,
                    "temperature": temperature,
                    "prompt_meta": prompt_meta,
                    "settings": settings,
                },
            ),
        )

    logger.warning("Unsupported LLM provider: %s", provider_name)
    raise HTTPException(
        status_code=400, detail=f"Unsupported LLM provider: {provider_name}"
    )


def _resolve_local_base(settings: Settings) -> str:
    base_url = (settings.LOCAL_BASE_URL or "").strip()
    if not base_url:
        raise HTTPException(
            status_code=400, detail="LOCAL_BASE_URL is not configured"
        )
    normalized_base = base_url.rstrip("/")

    from guardian.core.supported_profile import get_active_supported_profile

    manifest = get_active_supported_profile()
    if manifest is not None:
        expected_base = str(
            manifest.provider_contract.get("LOCAL_BASE_URL") or ""
        ).strip()
        expected_base = expected_base.rstrip("/")
        if expected_base and normalized_base != expected_base:
            raise HTTPException(
                status_code=400,
                detail=(
                    f"Supported profile {manifest.name} requires "
                    f"LOCAL_BASE_URL={expected_base}"
                ),
            )
    return normalized_base


def _normalize_local_candidate_base(raw_base: str) -> str:
    clean = str(raw_base or "").strip()
    if not clean:
        return ""
    if "://" not in clean:
        clean = f"http://{clean}"
    return clean.rstrip("/")


def _local_candidate_label(base_url: str) -> str:
    parsed = urlparse(base_url)
    if parsed.netloc:
        return parsed.netloc
    if parsed.path:
        return parsed.path.rstrip("/")
    return base_url.rstrip("/")


def _configured_local_endpoint_chain(
    settings: Settings,
) -> list[LocalEndpointCandidate]:
    raw_chain = str(
        getattr(settings, "CODEXIFY_LOCAL_ENDPOINT_CHAIN", "") or ""
    ).strip()
    if not raw_chain:
        return []

    chain: list[LocalEndpointCandidate] = []
    seen: set[str] = set()
    for raw_part in raw_chain.split(","):
        base_url = _normalize_local_candidate_base(raw_part)
        if not base_url or base_url in seen:
            continue
        seen.add(base_url)
        chain.append(
            LocalEndpointCandidate(
                base_url=base_url,
                label=_local_candidate_label(base_url),
                source="configured_chain",
            )
        )
    return chain


def _resolve_local_endpoint_candidates(
    settings: Settings,
) -> list[LocalEndpointCandidate]:
    configured_chain = _configured_local_endpoint_chain(settings)
    if configured_chain:
        return configured_chain

    primary_base = _resolve_local_base(settings)
    candidates = [
        LocalEndpointCandidate(
            base_url=primary_base,
            label=_local_candidate_label(primary_base),
            source="primary",
        )
    ]

    parsed = urlparse(primary_base)
    host = str(parsed.hostname or "").strip().lower()
    if host not in _LOCAL_LOOPBACK_HOSTS:
        return candidates

    fallback_raw = str(
        getattr(settings, "LOCAL_DOCKER_FALLBACK_BASE_URL", "") or ""
    ).strip()
    fallback_base = _normalize_local_candidate_base(
        fallback_raw or _DEFAULT_LOCAL_DOCKER_FALLBACK_BASE
    )
    if not fallback_base:
        return candidates

    if primary_base.endswith("/v1") and not fallback_base.endswith("/v1"):
        fallback_base = f"{fallback_base}/v1"
    if any(item.base_url == fallback_base for item in candidates):
        return candidates
    candidates.append(
        LocalEndpointCandidate(
            base_url=fallback_base,
            label=_local_candidate_label(fallback_base),
            source="docker_fallback",
        )
    )
    return candidates


def describe_local_endpoint_resolution(
    settings: Settings,
    *,
    selected_base_url: str | None = None,
    attempted_base_urls: list[str] | None = None,
    state: str | None = None,
    failure_kind: str | None = None,
    reason: str | None = None,
) -> dict[str, Any]:
    candidates = _resolve_local_endpoint_candidates(settings)
    attempted = list(dict.fromkeys(attempted_base_urls or []))
    selected = str(selected_base_url or "").strip() or None
    payload: dict[str, Any] = {
        "state": state
        or (
            "available" if selected else "degraded" if attempted else "unknown"
        ),
        "attempted_sequence": attempted,
        "attempts": [
            {
                "base_url": candidate.base_url,
                "label": candidate.label,
                "source": candidate.source,
                "attempted": candidate.base_url in attempted,
                "selected": bool(selected and candidate.base_url == selected),
            }
            for candidate in candidates
        ],
    }
    if selected:
        payload["selected_endpoint"] = {
            "base_url": selected,
            "label": _local_candidate_label(selected),
        }
    if failure_kind:
        payload["failure_kind"] = failure_kind
    if reason:
        payload["reason"] = reason
    return payload


def _resolve_local_base_candidates(settings: Settings) -> list[str]:
    return [
        candidate.base_url
        for candidate in _resolve_local_endpoint_candidates(settings)
    ]


def _local_attempt_urls(
    base_url: str,
    *,
    compat_first: bool,
    enable_generate_fallback: bool,
    allow_generate: bool,
) -> list[tuple[str, str]]:
    base_url_v1 = base_url if base_url.endswith("/v1") else f"{base_url}/v1"
    url_openai = f"{base_url_v1}/chat/completions"

    # Ollama-native base: strip explicit /v1 if present.
    base_url_ollama = base_url[:-3] if base_url.endswith("/v1") else base_url
    url_ollama_chat = f"{base_url_ollama}/api/chat"
    url_ollama_generate = f"{base_url_ollama}/api/generate"

    is_gateway = base_url.endswith("/v1")
    if is_gateway:
        return [("openai", url_openai)]

    if compat_first:
        attempt_urls: list[tuple[str, str]] = [
            ("openai", url_openai),
            ("ollama_chat", url_ollama_chat),
        ]
    else:
        attempt_urls = [
            ("ollama_chat", url_ollama_chat),
            ("openai", url_openai),
        ]
    if allow_generate and enable_generate_fallback:
        attempt_urls.append(("ollama_generate", url_ollama_generate))
    return attempt_urls


def _summarize_local_attempt_failures(failures: list[str]) -> str:
    if not failures:
        return "none"
    limit = 6
    if len(failures) <= limit:
        return "; ".join(failures)
    head = "; ".join(failures[:limit])
    return f"{head}; ... ({len(failures) - limit} more)"


def _all_local_attempt_failures_are_404(failures: list[str]) -> bool:
    return bool(failures) and all(
        "(HTTP 404" in failure for failure in failures
    )


def _parse_local_catalog_payload(payload: Any) -> list[str]:
    names: list[str] = []
    if not isinstance(payload, dict):
        return names
    for key in ("models", "data"):
        collection = payload.get(key)
        if not isinstance(collection, list):
            continue
        for item in collection:
            if isinstance(item, str):
                model_name = item.strip()
            elif isinstance(item, dict):
                model_name = str(
                    item.get("name")
                    or item.get("model")
                    or item.get("id")
                    or ""
                ).strip()
            else:
                model_name = ""
            if model_name:
                names.append(model_name)
    return names


def discover_local_model_inventory(
    settings: Settings,
    *,
    timeout_seconds: float,
    request_get: Any = None,
) -> tuple[list[str], dict[str, Any]]:
    fetch = request_get or requests.get
    names: list[str] = []
    attempt_failures: list[str] = []
    attempted_base_urls: list[str] = []
    selected_base_url: str | None = None
    failure_kind: str | None = None

    for candidate in _resolve_local_endpoint_candidates(settings):
        attempted_base_urls.append(candidate.base_url)
        local_base_v1 = (
            candidate.base_url
            if candidate.base_url.endswith("/v1")
            else f"{candidate.base_url}/v1"
        )
        local_base = (
            local_base_v1[:-3]
            if local_base_v1.endswith("/v1")
            else local_base_v1
        )
        candidate_names: list[str] = []
        for url in (f"{local_base}/api/tags", f"{local_base_v1}/models"):
            try:
                response = fetch(url, timeout=timeout_seconds)
            except req_exc.RequestException as exc:
                failure_kind = _classify_transport_error(exc)
                attempt_failures.append(f"{url} ({failure_kind}: {exc})")
                continue
            except Exception as exc:
                failure_kind = "request_error"
                attempt_failures.append(f"{url} ({type(exc).__name__}: {exc})")
                continue
            if not (200 <= response.status_code < 300):
                failure_kind = "provider_http_error"
                attempt_failures.append(f"{url} (HTTP {response.status_code})")
                continue
            try:
                payload = response.json()
            except Exception as exc:
                failure_kind = "provider_payload_error"
                attempt_failures.append(
                    f"{url} (invalid JSON: {type(exc).__name__}: {exc})"
                )
                continue
            candidate_names.extend(_parse_local_catalog_payload(payload))
            if candidate_names:
                break
        if candidate_names:
            names.extend(candidate_names)
            selected_base_url = candidate.base_url
            failure_kind = None
            break

    deduped: list[str] = []
    seen: set[str] = set()
    for name in names:
        clean = str(name or "").strip()
        if not clean or clean in seen:
            continue
        seen.add(clean)
        deduped.append(clean)

    if not deduped:
        fallback, _source, _strict = _configured_local_model_resolution(
            settings
        )
        if fallback:
            deduped = [fallback]

    resolution_state = (
        "available"
        if selected_base_url
        else "degraded"
        if deduped
        else "unavailable"
    )
    if resolution_state == "degraded" and failure_kind is None:
        failure_kind = "local_discovery_failed"
    resolution = describe_local_endpoint_resolution(
        settings,
        selected_base_url=selected_base_url,
        attempted_base_urls=attempted_base_urls,
        state=resolution_state,
        failure_kind=failure_kind,
        reason=_summarize_local_attempt_failures(attempt_failures)
        if attempt_failures
        else None,
    )
    return deduped, resolution


def call_local(
    messages,
    model: str,
    *,
    reasoning_mode: Optional[str] = None,
    settings: Optional[Settings] = None,
    max_tokens: Optional[int] = None,
    temperature: Optional[float] = None,
    timeout: Optional[float] = None,
    log_exceptions: bool = True,
):
    settings = _resolve_settings(settings)
    local_model_resolution = resolve_local_execution_model(
        settings=settings,
        requested_model=model,
    )
    if not local_model_resolution.ok:
        raise HTTPException(
            status_code=400,
            detail=local_model_resolution.error_detail(),
        )
    model = local_model_resolution.model or model
    runtime_policy = resolve_local_runtime_policy(
        model, settings=settings, timeout=timeout
    )
    adapted_messages, _ = apply_local_reasoning_directive(
        messages or [],
        model,
        reasoning_mode=reasoning_mode,
        settings=settings,
    )
    api_key = settings.LOCAL_API_KEY or "local"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload: Dict[str, Any] = {
        "model": model,
        "messages": adapted_messages,
        "temperature": 0.7 if temperature is None else float(temperature),
    }
    if max_tokens is not None:
        payload["max_tokens"] = int(max_tokens)
    base_urls = _resolve_local_base_candidates(settings)

    # Routing policy:
    # - If LOCAL_BASE_URL ends with /v1, treat it as an OpenAI-compatible gateway.
    # - Otherwise default local-first to Ollama-native /api/chat.
    # - Allow opt-in compat-first via settings.
    compat_first = bool(getattr(settings, "LOCAL_COMPAT_FIRST", False))
    # Back-compat aliases if you used different env names historically.
    compat_first = compat_first or bool(
        getattr(settings, "LOCAL_PREFER_OPENAI_COMPAT", False)
    )
    if _messages_contain_image_payload(adapted_messages):
        compat_first = True

    # Optional last-resort fallback to /api/generate (disabled by default).
    enable_generate_fallback = bool(
        getattr(settings, "LOCAL_ENABLE_OLLAMA_GENERATE_FALLBACK", False)
    )

    request_timeout = runtime_policy.request_timeout

    def _post_json(url: str, payload_obj: Dict[str, Any]) -> requests.Response:
        return requests.post(
            url, json=payload_obj, headers=headers, timeout=request_timeout
        )

    attempt_failures: list[str] = []
    last_transport_error: req_exc.RequestException | None = None
    last_transport_url: str = ""

    for base_url in base_urls:
        is_gateway = base_url.endswith("/v1")
        attempt_urls = _local_attempt_urls(
            base_url,
            compat_first=compat_first,
            enable_generate_fallback=enable_generate_fallback,
            allow_generate=True,
        )
        for kind, url in attempt_urls:
            try:
                if kind == "openai":
                    resp = _post_json(url, payload)
                elif kind == "ollama_chat":
                    payload_ollama: Dict[str, Any] = {
                        "model": model,
                        "messages": adapted_messages,
                        "stream": False,
                    }
                    resp = _post_json(url, payload_ollama)
                else:
                    # /api/generate expects a single prompt string. Keep it as a last resort.
                    prompt = "\n\n".join(
                        str(m.get("content") or "").strip()
                        for m in adapted_messages
                        if isinstance(m, dict)
                        and str(m.get("content") or "").strip()
                    ).strip()
                    payload_generate: Dict[str, Any] = {
                        "model": model,
                        "prompt": prompt,
                        "stream": False,
                    }
                    resp = _post_json(url, payload_generate)
            except req_exc.RequestException as exc:
                last_transport_error = exc
                last_transport_url = url
                classification = _classify_transport_error(exc)
                attempt_failures.append(f"{url} ({classification}: {exc})")
                continue

            if resp.status_code == 404:
                if is_gateway:
                    attempt_failures.append(
                        f"{url} (HTTP 404: endpoint requires OpenAI-compatible /v1/chat/completions)"
                    )
                else:
                    attempt_failures.append(f"{url} (HTTP 404)")
                continue

            if not (200 <= resp.status_code < 300):
                detail = _extract_provider_error_message(resp, secret=api_key)
                attempt_failures.append(
                    f"{url} (HTTP {resp.status_code}: {detail})"
                )
                continue

            try:
                data = json.loads(resp.content.decode("utf-8"))
            except Exception as exc:
                attempt_failures.append(f"{url} (invalid JSON: {exc})")
                continue

            # Ollama /api/chat format
            if (
                isinstance(data.get("message"), dict)
                and "content" in data["message"]
            ):
                return data["message"]["content"]

            # Ollama /api/generate format
            if "response" in data and isinstance(data.get("response"), str):
                return data.get("response") or ""

            # OpenAI-compatible format
            choices = data.get("choices")
            if isinstance(choices, list) and choices:
                message = choices[0].get("message")
                if isinstance(message, dict) and "content" in message:
                    return message.get("content") or ""

            attempt_failures.append(
                f"{url} (response did not include assistant content)"
            )

    if last_transport_error is not None:
        detail = _format_local_connect_error(
            last_transport_url,
            last_transport_error,
            model=model,
            runtime_policy=runtime_policy,
        )
    elif local_model_resolution.strict and _all_local_attempt_failures_are_404(
        attempt_failures
    ):
        endpoint_resolution = describe_local_endpoint_resolution(
            settings,
            attempted_base_urls=base_urls,
            state="degraded",
            failure_kind=LOCAL_MODEL_UNAVAILABLE_FAILURE_KIND,
            reason=_summarize_local_attempt_failures(attempt_failures),
        )
        detail_payload = local_model_resolution.error_detail(
            attempted_endpoints=attempt_failures,
            endpoint_resolution=endpoint_resolution,
            failure_kind=LOCAL_MODEL_UNAVAILABLE_FAILURE_KIND,
            message=(
                f"Configured local chat model '{model}' from "
                f"{local_model_resolution.source} could not be executed; "
                "all supported local endpoints returned HTTP 404"
            ),
        )
        if log_exceptions:
            logger.error(detail_payload["message"])
        else:
            logger.warning(detail_payload["message"])
        raise HTTPException(status_code=502, detail=detail_payload)
    else:
        detail = f"Local inference request failed for model '{model}'."

    attempt_summary = _summarize_local_attempt_failures(attempt_failures)
    detail = f"{detail} Attempted endpoints: {attempt_summary}"

    if log_exceptions:
        logger.error(detail)
    else:
        logger.warning(detail)
    raise HTTPException(status_code=502, detail=detail)


def stream_local(
    messages,
    model: str,
    *,
    reasoning_mode: Optional[str] = None,
    settings: Optional[Settings] = None,
    max_tokens: Optional[int] = None,
    temperature: Optional[float] = None,
):
    settings = _resolve_settings(settings)
    local_model_resolution = resolve_local_execution_model(
        settings=settings,
        requested_model=model,
    )
    if not local_model_resolution.ok:
        raise HTTPException(
            status_code=400,
            detail=local_model_resolution.error_detail(),
        )
    model = local_model_resolution.model or model
    runtime_policy = resolve_local_runtime_policy(model, settings=settings)
    adapted_messages, _ = apply_local_reasoning_directive(
        messages or [],
        model,
        reasoning_mode=reasoning_mode,
        settings=settings,
    )
    api_key = settings.LOCAL_API_KEY or "local"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload: Dict[str, Any] = {
        "model": model,
        "messages": adapted_messages,
        "temperature": 0.7 if temperature is None else float(temperature),
        "stream": True,
    }
    if max_tokens is not None:
        payload["max_tokens"] = int(max_tokens)
    base_urls = _resolve_local_base_candidates(settings)

    timeout = runtime_policy.request_timeout

    compat_first = bool(getattr(settings, "LOCAL_COMPAT_FIRST", False))
    compat_first = compat_first or bool(
        getattr(settings, "LOCAL_PREFER_OPENAI_COMPAT", False)
    )
    if _messages_contain_image_payload(adapted_messages):
        compat_first = True

    response: Optional[requests.Response] = None
    current_url = ""
    attempt_failures: list[str] = []
    last_transport_error: req_exc.RequestException | None = None

    try:
        for base_url in base_urls:
            is_gateway = base_url.endswith("/v1")
            attempt_urls = _local_attempt_urls(
                base_url,
                compat_first=compat_first,
                enable_generate_fallback=False,
                allow_generate=False,
            )
            for kind, url in attempt_urls:
                current_url = url
                try:
                    if kind == "openai":
                        resp = requests.post(
                            url,
                            json=payload,
                            headers=headers,
                            stream=True,
                            timeout=timeout,
                        )
                    else:
                        payload_ollama = {
                            "model": model,
                            "messages": adapted_messages,
                            "temperature": 0.7
                            if temperature is None
                            else float(temperature),
                            "stream": True,
                        }
                        resp = requests.post(
                            url,
                            json=payload_ollama,
                            headers=headers,
                            stream=True,
                            timeout=timeout,
                        )
                except req_exc.RequestException as exc:
                    last_transport_error = exc
                    classification = _classify_transport_error(exc)
                    attempt_failures.append(f"{url} ({classification}: {exc})")
                    continue

                if resp.status_code == 404:
                    if is_gateway:
                        attempt_failures.append(
                            f"{url} (HTTP 404: endpoint requires OpenAI-compatible /v1/chat/completions)"
                        )
                    else:
                        attempt_failures.append(f"{url} (HTTP 404)")
                    resp.close()
                    continue

                if not (200 <= resp.status_code < 300):
                    detail = _extract_provider_error_message(
                        resp, secret=api_key
                    )
                    attempt_failures.append(
                        f"{url} (HTTP {resp.status_code}: {detail})"
                    )
                    resp.close()
                    continue

                response = resp
                break
            if response is not None:
                break

        if response is None:
            if last_transport_error is not None:
                detail = _format_local_connect_error(
                    current_url,
                    last_transport_error,
                    model=model,
                    runtime_policy=runtime_policy,
                )
            elif (
                local_model_resolution.strict
                and _all_local_attempt_failures_are_404(attempt_failures)
            ):
                endpoint_resolution = describe_local_endpoint_resolution(
                    settings,
                    attempted_base_urls=base_urls,
                    state="degraded",
                    failure_kind=LOCAL_MODEL_UNAVAILABLE_FAILURE_KIND,
                    reason=_summarize_local_attempt_failures(attempt_failures),
                )
                raise HTTPException(
                    status_code=502,
                    detail=local_model_resolution.error_detail(
                        attempted_endpoints=attempt_failures,
                        endpoint_resolution=endpoint_resolution,
                        failure_kind=LOCAL_MODEL_UNAVAILABLE_FAILURE_KIND,
                        message=(
                            f"Configured local chat model '{model}' from "
                            f"{local_model_resolution.source} could not be executed; "
                            "all supported local endpoints returned HTTP 404"
                        ),
                    ),
                )
            else:
                detail = f"Local inference request failed for model '{model}'."
            summary = _summarize_local_attempt_failures(attempt_failures)
            raise HTTPException(
                status_code=502,
                detail=f"{detail} Attempted endpoints: {summary}",
            )

        try:
            for raw_line in response.iter_lines(decode_unicode=False):
                if not raw_line:
                    continue
                line = raw_line.decode("utf-8", errors="replace")
                if line.startswith("data:"):
                    data = line[5:].strip()
                else:
                    data = line.strip()
                if not data:
                    continue
                if data == "[DONE]":
                    break
                try:
                    chunk = json.loads(data)
                except Exception:
                    continue
                try:
                    # OpenAI-compatible SSE or Ollama /api/chat streaming
                    choice = chunk.get("choices", [{}])[0]
                    delta = choice.get("delta") or {}
                    token = (
                        delta.get("content")
                        or choice.get("message", {}).get("content")
                        or choice.get("text")
                    )
                    if not token and isinstance(chunk.get("message"), dict):
                        # Ollama /api/chat streaming shape:
                        # {"message":{"role":"assistant","content":"..."}, ...}
                        token = chunk["message"].get("content")
                    if not token and isinstance(chunk.get("response"), str):
                        # Ollama /api/generate streaming shape.
                        token = chunk.get("response")
                    if token:
                        yield token
                except Exception:
                    continue
        except req_exc.RequestException as exc:
            detail = _format_local_connect_error(
                current_url,
                exc,
                model=model,
                runtime_policy=runtime_policy,
            )
            summary = _summarize_local_attempt_failures(attempt_failures)
            detail = f"{detail} Attempted endpoints: {summary}"
            logger.warning(detail)
            raise HTTPException(status_code=502, detail=detail) from exc
    finally:
        if response is not None:
            try:
                response.close()
            except Exception:
                pass


def call_groq(
    messages,
    model: str,
    *,
    temperature: Optional[float] = None,
    settings: Optional[Settings] = None,
):
    settings = _resolve_settings(settings)
    try:
        assert_egress_allowed("groq", settings=settings)
    except EgressDeniedError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc

    api_key = settings.GROQ_API_KEY
    if not api_key:
        raise HTTPException(
            status_code=400, detail="GROQ_API_KEY is not configured"
        )

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload: Dict[str, Any] = {
        "model": model,
        "messages": messages,
        "temperature": 0.7 if temperature is None else float(temperature),
    }
    base_url = (settings.GROQ_BASE_URL or _DEFAULT_GROQ_BASE).rstrip("/")
    url = f"{base_url}/openai/v1/chat/completions"

    try:
        response = requests.post(url, json=payload, headers=headers, timeout=30)
    except req_exc.RequestException as exc:
        detail = _sanitize_provider_error(str(exc), secret=api_key)
        logger.exception(
            "GROQ backend request error model=%s endpoint=%s transport=%s",
            model,
            url,
            _classify_transport_error(exc),
        )
        raise HTTPException(
            status_code=502,
            detail=_provider_failure_detail(
                provider="groq",
                model=model,
                endpoint=url,
                failure_kind="request_error",
                message=f"Groq request failed: {detail}",
                provider_error=detail,
                transport_classification=_classify_transport_error(exc),
            ),
        ) from exc

    if not (200 <= response.status_code < 300):
        detail = _extract_provider_error_message(response, secret=api_key)
        logger.error(
            "GROQ backend non-2xx model=%s endpoint=%s status=%s detail=%s",
            model,
            url,
            response.status_code,
            detail,
        )
        raise HTTPException(
            status_code=502,
            detail=_provider_failure_detail(
                provider="groq",
                model=model,
                endpoint=url,
                failure_kind="http_error",
                message=f"Groq request failed ({response.status_code}): {detail}",
                upstream_status=response.status_code,
                provider_error=detail,
            ),
        )

    try:
        data = response.json()
        return data["choices"][0]["message"]["content"]
    except Exception as exc:
        detail = _sanitize_provider_error(str(exc), secret=api_key)
        logger.exception(
            "GROQ backend response parse error model=%s endpoint=%s",
            model,
            url,
        )
        raise HTTPException(
            status_code=502,
            detail=_provider_failure_detail(
                provider="groq",
                model=model,
                endpoint=url,
                failure_kind="parse_error",
                message=f"Groq response parse failed: {detail}",
                provider_error=detail,
            ),
        ) from exc


def _call_openai_compatible_chat(
    *,
    provider_name: str,
    provider_display_name: str,
    egress_target: str,
    api_key: str | None,
    base_url: str | None,
    default_base_url: str,
    base_path: str,
    messages,
    model: str,
    temperature: Optional[float],
    timeout: float,
    settings: Settings,
    typed_failure_kinds: bool = False,
):
    try:
        assert_egress_allowed(egress_target, settings=settings)
    except EgressDeniedError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc

    clean_api_key = str(api_key or "").strip()
    if not clean_api_key:
        raise HTTPException(
            status_code=400,
            detail=f"{provider_name.upper()}_API_KEY is not configured",
        )

    resolved_base = str(base_url or default_base_url or "").strip().rstrip("/")
    if not resolved_base:
        raise HTTPException(
            status_code=400,
            detail=f"{provider_name.upper()}_API_BASE is not configured",
        )

    headers = {
        "Authorization": f"Bearer {clean_api_key}",
        "Content-Type": "application/json",
    }
    payload: Dict[str, Any] = {
        "model": model,
        "messages": messages,
        "temperature": 0.7 if temperature is None else float(temperature),
    }
    url = f"{resolved_base}{base_path}"

    try:
        response = requests.post(
            url,
            json=payload,
            headers=headers,
            timeout=float(timeout),
        )
    except req_exc.RequestException as exc:
        detail = _sanitize_provider_error(str(exc), secret=clean_api_key)
        transport_classification = _classify_transport_error(exc)
        failure_kind = (
            _provider_transport_failure_kind(exc)
            if typed_failure_kinds
            else "request_error"
        )
        logger.exception(
            "%s backend request error model=%s endpoint=%s transport=%s",
            provider_display_name,
            model,
            url,
            transport_classification,
        )
        raise HTTPException(
            status_code=502,
            detail=_provider_failure_detail(
                provider=provider_name,
                model=model,
                endpoint=url,
                failure_kind=failure_kind,
                message=f"{provider_display_name} request failed: {detail}",
                provider_error=detail,
                transport_classification=transport_classification,
            ),
        ) from exc

    if not (200 <= response.status_code < 300):
        detail = _extract_provider_error_message(response, secret=clean_api_key)
        logger.error(
            "%s backend non-2xx model=%s endpoint=%s status=%s detail=%s",
            provider_display_name,
            model,
            url,
            response.status_code,
            detail,
        )
        raise HTTPException(
            status_code=502,
            detail=_provider_failure_detail(
                provider=provider_name,
                model=model,
                endpoint=url,
                failure_kind=(
                    "provider_http_error"
                    if typed_failure_kinds
                    else "http_error"
                ),
                message=(
                    f"{provider_display_name} request failed "
                    f"({response.status_code}): {detail}"
                ),
                upstream_status=response.status_code,
                provider_error=detail,
            ),
        )

    try:
        data = response.json()
        return data["choices"][0]["message"]["content"]
    except Exception as exc:
        detail = _sanitize_provider_error(str(exc), secret=clean_api_key)
        logger.exception(
            "%s backend response parse error model=%s endpoint=%s",
            provider_display_name,
            model,
            url,
        )
        raise HTTPException(
            status_code=502,
            detail=_provider_failure_detail(
                provider=provider_name,
                model=model,
                endpoint=url,
                failure_kind=(
                    "provider_payload_error"
                    if typed_failure_kinds
                    else "parse_error"
                ),
                message=f"{provider_display_name} response parse failed: {detail}",
                provider_error=detail,
            ),
        ) from exc


def call_openai(
    messages,
    model: str,
    *,
    temperature: Optional[float] = None,
    settings: Optional[Settings] = None,
):
    settings = _resolve_settings(settings)
    return _call_openai_compatible_chat(
        provider_name="openai",
        provider_display_name="OpenAI",
        egress_target="openai",
        api_key=settings.OPENAI_API_KEY,
        base_url=settings.OPENAI_BASE_URL,
        default_base_url=_DEFAULT_OPENAI_BASE,
        base_path="/v1/chat/completions",
        messages=messages,
        model=model,
        temperature=temperature,
        timeout=30.0,
        settings=settings,
    )


def call_alibaba(
    messages,
    model: str,
    *,
    temperature: Optional[float] = None,
    settings: Optional[Settings] = None,
):
    settings = _resolve_settings(settings)
    if not bool(getattr(settings, "ALLOW_CLOUD_PROVIDERS", True)):
        raise HTTPException(
            status_code=403,
            detail="Egress 'alibaba' blocked: ALLOW_CLOUD_PROVIDERS=false.",
        )

    api_key = str(settings.ALIBABA_API_KEY or "").strip()
    base_url_raw = settings.ALIBABA_API_BASE
    if base_url_raw is None:
        base_url = _DEFAULT_ALIBABA_BASE
    else:
        base_url = str(base_url_raw).strip()
    endpoint = f"{base_url.rstrip('/')}/chat/completions"
    if not api_key:
        raise HTTPException(
            status_code=400,
            detail=_provider_failure_detail(
                provider="alibaba",
                model=model,
                endpoint=endpoint,
                failure_kind="auth_config_error",
                message="Alibaba provider credentials are not configured",
                provider_error="ALIBABA_API_KEY is not configured",
            ),
        )
    if not base_url:
        raise HTTPException(
            status_code=400,
            detail=_provider_failure_detail(
                provider="alibaba",
                model=model,
                endpoint=endpoint,
                failure_kind="auth_config_error",
                message="Alibaba provider endpoint is not configured",
                provider_error="ALIBABA_API_BASE is not configured",
            ),
        )
    return _call_openai_compatible_chat(
        provider_name="alibaba",
        provider_display_name="Alibaba",
        egress_target="alibaba",
        api_key=settings.ALIBABA_API_KEY,
        base_url=settings.ALIBABA_API_BASE,
        default_base_url=_DEFAULT_ALIBABA_BASE,
        base_path="/chat/completions",
        messages=messages,
        model=model,
        temperature=temperature,
        timeout=float(
            getattr(
                settings,
                "ALIBABA_TIMEOUT_SECONDS",
                getattr(settings, "LLM_REQUEST_TIMEOUT_SECONDS", 60),
            )
        ),
        settings=settings,
        typed_failure_kinds=True,
    )


def _sanitize_provider_error(message: str, *, secret: str | None = None) -> str:
    detail = (message or "").strip()
    if secret:
        detail = detail.replace(secret, "<redacted>")
    return detail or "request failed"


def _extract_provider_error_message(
    response: requests.Response,
    *,
    secret: str | None = None,
) -> str:
    text = ""
    try:
        payload = response.json()
        if isinstance(payload, dict):
            error = payload.get("error")
            if isinstance(error, dict):
                text = str(error.get("message") or "").strip()
            elif isinstance(error, str):
                text = error.strip()
            if not text:
                text = str(payload.get("message") or "").strip()
    except Exception:
        text = ""

    if not text:
        text = (response.text or "").strip() or f"HTTP {response.status_code}"
    return _sanitize_provider_error(text, secret=secret)


def _anthropic_text_block(
    text: str,
    *,
    cacheable: bool = False,
) -> dict[str, Any]:
    block: dict[str, Any] = {
        "type": "text",
        "text": str(text or "").strip(),
    }
    if cacheable:
        block["cache_control"] = {"type": "ephemeral"}
    return block


def _anthropic_image_block(source: dict[str, Any]) -> dict[str, Any] | None:
    source_type = str(source.get("type") or "").strip().lower()
    if source_type == "base64":
        data = str(source.get("data") or "").strip()
        media_type = str(source.get("media_type") or "").strip()
        if not data or not media_type:
            return None
        return {
            "type": "image",
            "source": {
                "type": "base64",
                "media_type": media_type,
                "data": data,
            },
        }

    url = str(source.get("url") or "").strip()
    if source_type == "url" or url:
        if not url:
            return None
        return {
            "type": "image",
            "source": {
                "type": "url",
                "url": url,
            },
        }

    data = str(source.get("data") or "").strip()
    media_type = str(source.get("media_type") or "").strip()
    if data and media_type:
        return {
            "type": "image",
            "source": {
                "type": "base64",
                "media_type": media_type,
                "data": data,
            },
        }
    return None


def _coerce_anthropic_content_blocks(content: Any) -> list[dict[str, Any]]:
    if isinstance(content, list):
        blocks: list[dict[str, Any]] = []
        for item in content:
            if isinstance(item, dict):
                block = _clone_content_block(item)
                block_type = str(block.get("type") or "").strip().lower()
                if block_type:
                    if block_type == "text":
                        text = str(block.get("text") or "").strip()
                        if not text:
                            continue
                        block["text"] = text
                        blocks.append(block)
                        continue
                    if block_type == "image_url":
                        image_url = block.get("image_url")
                        if isinstance(image_url, dict):
                            image_block = _anthropic_image_block(image_url)
                            if image_block is not None:
                                blocks.append(image_block)
                        continue
                    if block_type == "image":
                        source = block.get("source")
                        if isinstance(source, dict):
                            image_block = _anthropic_image_block(source)
                            if image_block is not None:
                                blocks.append(image_block)
                                continue
                            if str(
                                source.get("type") or ""
                            ).strip().lower() in {
                                "base64",
                                "url",
                            }:
                                blocks.append(block)
                                continue
                    if block_type in {"thinking", "tool_use", "tool_result"}:
                        blocks.append(block)
                        continue
                text = _coerce_text(item).strip()
                if text:
                    blocks.append(_anthropic_text_block(text))
                continue
            text = str(item or "").strip()
            if text:
                blocks.append(_anthropic_text_block(text))
        return blocks

    if isinstance(content, dict):
        block = _clone_content_block(content)
        block_type = str(block.get("type") or "").strip().lower()
        if block_type:
            if block_type == "text":
                text = str(block.get("text") or "").strip()
                if text:
                    block["text"] = text
                    return [block]
                return []
            if block_type == "image_url":
                image_url = block.get("image_url")
                if isinstance(image_url, dict):
                    image_block = _anthropic_image_block(image_url)
                    if image_block is not None:
                        return [image_block]
                return []
            if block_type == "image":
                source = block.get("source")
                if isinstance(source, dict):
                    image_block = _anthropic_image_block(source)
                    if image_block is not None:
                        return [image_block]
                    if str(source.get("type") or "").strip().lower() in {
                        "base64",
                        "url",
                    }:
                        return [block]
                return []
            if block_type in {"thinking", "tool_use", "tool_result"}:
                return [block]

    text = str(content or "").strip()
    return [_anthropic_text_block(text)] if text else []


def _normalize_messages_for_anthropic(
    messages: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], str | list[dict[str, Any]] | None]:
    return _normalize_messages_for_anthropic_with_meta(messages, None)


def _normalize_messages_for_anthropic_with_meta(
    messages: list[dict[str, Any]],
    prompt_meta: dict[str, Any] | None,
) -> tuple[list[dict[str, Any]], str | list[dict[str, Any]] | None]:
    system_parts: list[str] = []
    normalized: list[dict[str, Any]] = []

    for raw in messages:
        if not isinstance(raw, dict):
            continue
        role = str(raw.get("role") or "user").strip().lower() or "user"
        content = raw.get("content")
        if role == "system":
            text = str(_coerce_text(content) or "").strip()
            if not text:
                continue
            system_parts.append(text)
            continue

        content_blocks = _coerce_anthropic_content_blocks(content)
        if not content_blocks:
            continue
        if role not in {"user", "assistant"}:
            role = "user"
        normalized.append({"role": role, "content": content_blocks})

    if not normalized:
        normalized = [
            {"role": "user", "content": [{"type": "text", "text": ""}]}
        ]

    if prompt_meta:
        segments = prompt_meta.get("segments")
        if isinstance(segments, list):
            system_blocks: list[dict[str, Any]] = []
            cacheable_indexes: list[int] = []
            for segment in segments:
                if not isinstance(segment, dict):
                    continue
                text = str(segment.get("text") or "").strip()
                if not text:
                    continue
                cacheable = bool(segment.get("cacheable"))
                if cacheable:
                    cacheable_indexes.append(len(system_blocks))
                system_blocks.append(_anthropic_text_block(text))
            if system_blocks:
                if cacheable_indexes:
                    system_blocks[cacheable_indexes[-1]]["cache_control"] = {
                        "type": "ephemeral"
                    }
                return normalized, system_blocks

    system_text = "\n\n".join(part for part in system_parts if part).strip()
    return normalized, (system_text or None)


def _extract_anthropic_text(payload: dict[str, Any]) -> str:
    content = payload.get("content")
    if not isinstance(content, list):
        return ""
    parts: list[str] = []
    for block in content:
        if not isinstance(block, dict):
            continue
        if str(block.get("type") or "").strip() != "text":
            continue
        text = str(block.get("text") or "").strip()
        if text:
            parts.append(text)
    return "".join(parts)


def call_minimax(
    messages,
    model: str,
    *,
    reasoning_mode: Optional[str] = None,
    temperature: Optional[float] = None,
    prompt_meta: Optional[dict[str, Any]] = None,
    settings: Optional[Settings] = None,
):
    """Call MiniMax via OpenAI- or Anthropic-compatible endpoints."""
    settings = _resolve_settings(settings)

    try:
        assert_egress_allowed("minimax", settings=settings)
    except EgressDeniedError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc

    api_key = (settings.MINIMAX_API_KEY or "").strip()
    endpoint_hint = "minimax://chat/completions"
    if not api_key:
        raise HTTPException(
            status_code=400,
            detail=_provider_failure_detail(
                provider="minimax",
                model=model,
                endpoint=endpoint_hint,
                failure_kind="auth_config_error",
                message="MiniMax provider credentials are not configured",
                provider_error="MINIMAX_API_KEY is not configured",
            ),
        )

    base_url = (settings.MINIMAX_API_BASE or "").strip().rstrip("/")
    if base_url:
        endpoint_hint = f"{base_url}/chat/completions"
    if not base_url:
        raise HTTPException(
            status_code=400,
            detail=_provider_failure_detail(
                provider="minimax",
                model=model,
                endpoint=endpoint_hint,
                failure_kind="auth_config_error",
                message="MiniMax provider endpoint is not configured",
                provider_error="MINIMAX_API_BASE is not configured",
            ),
        )

    api_flavor = str(getattr(settings, "MINIMAX_API_FLAVOR", "anthropic") or "")
    api_flavor = api_flavor.strip().lower() or "anthropic"
    if api_flavor not in {"openai", "anthropic"}:
        raise HTTPException(
            status_code=400,
            detail="MINIMAX_API_FLAVOR must be one of: openai, anthropic",
        )

    if api_flavor == "anthropic":
        (
            anthropic_messages,
            system_prompt,
        ) = _normalize_messages_for_anthropic_with_meta(messages, prompt_meta)
        payload: Dict[str, Any] = {
            "model": model,
            "messages": anthropic_messages,
            "temperature": 0.7 if temperature is None else float(temperature),
            "max_tokens": int(
                getattr(settings, "MINIMAX_ANTHROPIC_MAX_TOKENS", 1024)
            ),
        }
        if system_prompt:
            payload["system"] = system_prompt
        headers = {
            "x-api-key": api_key,
            "anthropic-version": str(
                getattr(settings, "MINIMAX_ANTHROPIC_VERSION", "2023-06-01")
                or "2023-06-01"
            ),
            "Content-Type": "application/json",
        }
        if str(reasoning_mode or "").strip().lower() in {"think", "/think"}:
            payload["thinking"] = {
                "type": "enabled",
                "budget_tokens": 1024,
            }
        if base_url.endswith("/v1"):
            url = f"{base_url}/messages"
        else:
            url = f"{base_url}/v1/messages"
    else:
        payload = {
            "model": model,
            "messages": messages,
            "temperature": 0.7 if temperature is None else float(temperature),
            "reasoning_split": True,
        }
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        url = f"{base_url}/chat/completions"

    timeout = float(
        getattr(
            settings,
            "MINIMAX_TIMEOUT_SECONDS",
            getattr(settings, "LLM_REQUEST_TIMEOUT_SECONDS", 60),
        )
    )

    try:
        response = requests.post(
            url,
            json=payload,
            headers=headers,
            timeout=timeout,
        )
    except req_exc.RequestException as exc:
        detail = _sanitize_provider_error(str(exc), secret=api_key)
        transport_classification = _classify_transport_error(exc)
        logger.exception(
            "MiniMax backend request error model=%s endpoint=%s transport=%s",
            model,
            url,
            transport_classification,
        )
        raise HTTPException(
            status_code=502,
            detail=_provider_failure_detail(
                provider="minimax",
                model=model,
                endpoint=url,
                failure_kind=_provider_transport_failure_kind(exc),
                message=f"MiniMax request failed: {detail}",
                provider_error=detail,
                transport_classification=transport_classification,
            ),
        ) from exc

    if not (200 <= response.status_code < 300):
        detail = _extract_provider_error_message(response, secret=api_key)
        raise HTTPException(
            status_code=502,
            detail=_provider_failure_detail(
                provider="minimax",
                model=model,
                endpoint=url,
                failure_kind="provider_http_error",
                message=f"MiniMax request failed ({response.status_code}): {detail}",
                upstream_status=response.status_code,
                provider_error=detail,
            ),
        )

    try:
        data = response.json()
        if api_flavor == "anthropic":
            return ProviderResponse(
                _extract_anthropic_text(data),
                raw_payload=data,
                content_blocks=data.get("content"),
                provider="minimax",
            )
        choices = data.get("choices")
        if isinstance(choices, list) and choices:
            message = choices[0].get("message")
            if isinstance(message, dict):
                return ProviderResponse(
                    _coerce_text(message.get("content")),
                    raw_payload=data,
                    content_blocks=message.get("content"),
                    provider="minimax",
                )
        raise KeyError("content")
    except Exception as exc:
        detail = _sanitize_provider_error(str(exc), secret=api_key)
        logger.exception(
            "MiniMax backend response parse error model=%s endpoint=%s",
            model,
            url,
        )
        raise HTTPException(
            status_code=502,
            detail=_provider_failure_detail(
                provider="minimax",
                model=model,
                endpoint=url,
                failure_kind="provider_payload_error",
                message=f"MiniMax response parse failed: {detail}",
                provider_error=detail,
            ),
        ) from exc
