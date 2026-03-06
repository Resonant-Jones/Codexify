import json
import logging
from dataclasses import dataclass
from typing import Any, Dict, Optional

import requests
from fastapi import HTTPException
from requests import exceptions as req_exc

from guardian.core.config import Settings, get_settings
from guardian.core.egress import EgressDeniedError, assert_egress_allowed

logger = logging.getLogger(__name__)

_DEFAULT_OPENAI_BASE = "https://api.openai.com"
_DEFAULT_GROQ_BASE = "https://api.groq.com"


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


def _normalize_provider(provider: Optional[str]) -> str:
    """
    Normalize provider identifiers coming from API/UI/config.

    Notes:
    - `auto` is accepted as an execution-time alias. Today it resolves to
      `local` (local-first + deterministic). This prevents config/UX mismatch
      from hard-failing completions when UI does not send an explicit provider.
    """
    normalized = (provider or "").strip().lower()
    if normalized in ("", "auto"):
        return "local"
    return normalized


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


def _append_reasoning_instruction(content: Any, instruction: str) -> str:
    text = str(content or "").strip()
    if not text:
        return instruction
    if instruction in text:
        return text
    return f"{text}\n\n{instruction}"


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
    settings: Optional[Settings] = None,
) -> tuple[list[dict[str, Any]], LocalReasoningDirective]:
    directive = resolve_local_reasoning_directive(model, settings=settings)
    if directive.mode != "no_think" or not directive.instruction:
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
    if provider == "local":
        return (
            settings.LOCAL_LLM_MODEL
            or settings.DEFAULT_LOCAL_MODEL
            or settings.LLM_MODEL
            or ""
        )
    if provider == "groq":
        return settings.LLM_MODEL or settings.DEFAULT_GROQ_MODEL
    if provider == "openai":
        return settings.DEFAULT_OPENAI_MODEL
    if provider == "minimax":
        return (settings.MINIMAX_MODEL or "").strip()
    return ""


def _normalize_openai_model(model: str, settings: Settings) -> str:
    """Ensure we send a chat-compatible OpenAI model."""
    if model.startswith("gpt-4.1") or model.startswith("o3"):
        # Map responses-only models to a chat-compatible default for now.
        return settings.DEFAULT_OPENAI_MODEL
    return model


def chat_with_ai(
    messages,
    model: Optional[str] = None,
    provider: Optional[str] = None,
    settings: Optional[Settings] = None,
):
    settings = _resolve_settings(settings)
    provider_name = _normalize_provider(provider or settings.LLM_PROVIDER)
    target_model = model or _default_model_for_provider(provider_name, settings)

    if not target_model:
        raise HTTPException(
            status_code=400,
            detail=(
                "No model configured for provider. Set LLM_MODEL or the provider-specific "
                "model setting (e.g. LOCAL_LLM_MODEL / DEFAULT_LOCAL_MODEL)."
            ),
        )

    if provider_name == "local":
        return call_local(messages, target_model, settings=settings)
    if provider_name == "groq":
        return call_groq(messages, target_model, settings=settings)
    if provider_name == "openai":
        return call_openai(
            messages,
            _normalize_openai_model(target_model, settings),
            settings=settings,
        )
    if provider_name == "minimax":
        return call_minimax(messages, target_model, settings=settings)

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
    return base_url.rstrip("/")


def call_local(
    messages,
    model: str,
    *,
    settings: Optional[Settings] = None,
    max_tokens: Optional[int] = None,
    temperature: Optional[float] = None,
    timeout: Optional[float] = None,
    log_exceptions: bool = True,
):
    settings = _resolve_settings(settings)
    runtime_policy = resolve_local_runtime_policy(
        model, settings=settings, timeout=timeout
    )
    adapted_messages, _ = apply_local_reasoning_directive(
        messages or [], model, settings=settings
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
    base_url = _resolve_local_base(settings)

    # Endpoints
    base_url_v1 = base_url if base_url.endswith("/v1") else f"{base_url}/v1"
    url_openai = f"{base_url_v1}/chat/completions"

    # Ollama-native base: strip explicit /v1 if present.
    base_url_ollama = base_url[:-3] if base_url.endswith("/v1") else base_url
    url_ollama_chat = f"{base_url_ollama}/api/chat"
    url_ollama_generate = f"{base_url_ollama}/api/generate"

    # Routing policy:
    # - If LOCAL_BASE_URL ends with /v1, treat it as an OpenAI-compatible gateway.
    # - Otherwise default local-first to Ollama-native /api/chat.
    # - Allow opt-in compat-first via settings.
    compat_first = bool(getattr(settings, "LOCAL_COMPAT_FIRST", False))
    # Back-compat aliases if you used different env names historically.
    compat_first = compat_first or bool(
        getattr(settings, "LOCAL_PREFER_OPENAI_COMPAT", False)
    )

    # Optional last-resort fallback to /api/generate (disabled by default).
    enable_generate_fallback = bool(
        getattr(settings, "LOCAL_ENABLE_OLLAMA_GENERATE_FALLBACK", False)
    )

    request_timeout = runtime_policy.request_timeout

    # If user explicitly configured /v1, do not silently try Ollama-native endpoints.
    is_gateway = base_url.endswith("/v1")

    def _post_json(url: str, payload_obj: Dict[str, Any]) -> requests.Response:
        return requests.post(
            url, json=payload_obj, headers=headers, timeout=request_timeout
        )

    # Attempt order
    if is_gateway:
        attempt_urls = [("openai", url_openai)]
    else:
        if compat_first:
            attempt_urls = [
                ("openai", url_openai),
                ("ollama_chat", url_ollama_chat),
            ]
        else:
            attempt_urls = [
                ("ollama_chat", url_ollama_chat),
                ("openai", url_openai),
            ]
        if enable_generate_fallback:
            attempt_urls.append(("ollama_generate", url_ollama_generate))

    last_response: Optional[requests.Response] = None

    try:
        for kind, url in attempt_urls:
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

            last_response = resp

            # If endpoint missing, try the next one (unless we are in gateway mode)
            if resp.status_code == 404:
                if is_gateway:
                    detail = (
                        f"Local inference endpoint not found: {url_openai} returned 404. "
                        "LOCAL_BASE_URL ends with '/v1', so OpenAI-compatible endpoints "
                        "(e.g. /v1/chat/completions) are required."
                    )
                    raise HTTPException(status_code=502, detail=detail)
                continue

            resp.raise_for_status()
            data = json.loads(resp.content.decode("utf-8"))

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
            return data["choices"][0]["message"]["content"]

        # If we exhausted attempts, surface the last response body.
        if last_response is not None:
            detail = _extract_provider_error_message(
                last_response, secret=api_key
            )
            raise HTTPException(
                status_code=502,
                detail=f"Local inference request failed ({last_response.status_code}): {detail}",
            )
        raise HTTPException(
            status_code=502, detail="Local inference request failed"
        )
    except req_exc.RequestException as e:
        failed_url = (
            last_response.url
            if last_response is not None and getattr(last_response, "url", None)
            else (attempt_urls[0][1] if attempt_urls else url_openai)
        )
        detail = _format_local_connect_error(
            failed_url,
            e,
            model=model,
            runtime_policy=runtime_policy,
        )
        if log_exceptions:
            logger.exception(detail)
        else:
            logger.warning(detail)
        raise HTTPException(status_code=502, detail=detail)
    except HTTPException:
        raise
    except Exception as e:
        if log_exceptions:
            logger.exception("Local backend error")
        else:
            logger.warning("Local backend error: %s", e)
        raise HTTPException(status_code=502, detail=str(e))


def stream_local(
    messages,
    model: str,
    *,
    settings: Optional[Settings] = None,
    max_tokens: Optional[int] = None,
    temperature: Optional[float] = None,
):
    settings = _resolve_settings(settings)
    runtime_policy = resolve_local_runtime_policy(model, settings=settings)
    adapted_messages, _ = apply_local_reasoning_directive(
        messages or [], model, settings=settings
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
    base_url = _resolve_local_base(settings)

    base_url_v1 = base_url if base_url.endswith("/v1") else f"{base_url}/v1"
    url_openai = f"{base_url_v1}/chat/completions"

    base_url_ollama = base_url[:-3] if base_url.endswith("/v1") else base_url
    url_ollama_chat = f"{base_url_ollama}/api/chat"

    timeout = runtime_policy.request_timeout

    compat_first = bool(getattr(settings, "LOCAL_COMPAT_FIRST", False))
    compat_first = compat_first or bool(
        getattr(settings, "LOCAL_PREFER_OPENAI_COMPAT", False)
    )

    is_gateway = base_url.endswith("/v1")

    # Attempt order for streaming (no /api/generate support in streaming mode)
    if is_gateway:
        attempt_urls = [("openai", url_openai)]
    else:
        if compat_first:
            attempt_urls = [
                ("openai", url_openai),
                ("ollama_chat", url_ollama_chat),
            ]
        else:
            attempt_urls = [
                ("ollama_chat", url_ollama_chat),
                ("openai", url_openai),
            ]

    current_url = attempt_urls[0][1] if attempt_urls else url_openai

    response: Optional[requests.Response] = None

    try:
        for kind, url in attempt_urls:
            current_url = url
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

            response = resp

            if resp.status_code == 404:
                if is_gateway:
                    detail = (
                        f"Local inference endpoint not found: {url_openai} returned 404. "
                        "LOCAL_BASE_URL ends with '/v1', so OpenAI-compatible endpoints "
                        "(e.g. /v1/chat/completions) are required."
                    )
                    raise HTTPException(status_code=502, detail=detail)
                # Try next endpoint
                resp.close()
                response = None
                continue

            resp.raise_for_status()
            break

        if response is None:
            raise HTTPException(
                status_code=502, detail="Local inference request failed"
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
            logger.warning(detail)
            raise HTTPException(status_code=502, detail=detail) from exc
    finally:
        if response is not None:
            try:
                response.close()
            except Exception:
                pass


def call_groq(messages, model: str, *, settings: Optional[Settings] = None):
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
        "temperature": 0.7,
    }
    base_url = (settings.GROQ_BASE_URL or _DEFAULT_GROQ_BASE).rstrip("/")
    url = f"{base_url}/openai/v1/chat/completions"

    try:
        response = requests.post(url, json=payload, headers=headers, timeout=30)
        response.raise_for_status()
        data = response.json()
        return data["choices"][0]["message"]["content"]
    except Exception as e:
        logger.exception("GROQ backend error")
        raise HTTPException(status_code=502, detail=str(e))


def call_openai(messages, model: str, *, settings: Optional[Settings] = None):
    settings = _resolve_settings(settings)
    try:
        assert_egress_allowed("openai", settings=settings)
    except EgressDeniedError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc

    api_key = settings.OPENAI_API_KEY
    if not api_key:
        raise HTTPException(
            status_code=400, detail="OPENAI_API_KEY is not configured"
        )

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload: Dict[str, Any] = {
        "model": model,
        "messages": messages,
        "temperature": 0.7,
    }
    base_url = (settings.OPENAI_BASE_URL or _DEFAULT_OPENAI_BASE).rstrip("/")
    url = f"{base_url}/v1/chat/completions"

    try:
        response = requests.post(url, json=payload, headers=headers, timeout=30)
        response.raise_for_status()
        data = response.json()
        return data["choices"][0]["message"]["content"]
    except Exception as e:
        logger.exception("OpenAI backend error")
        raise HTTPException(status_code=502, detail=str(e))


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


def _normalize_messages_for_anthropic(
    messages: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], str | None]:
    system_parts: list[str] = []
    normalized: list[dict[str, Any]] = []

    for raw in messages:
        if not isinstance(raw, dict):
            continue
        role = str(raw.get("role") or "user").strip().lower() or "user"
        text = str(raw.get("content") or "").strip()
        if not text:
            continue
        if role == "system":
            system_parts.append(text)
            continue
        if role not in {"user", "assistant"}:
            role = "user"
        normalized.append(
            {"role": role, "content": [{"type": "text", "text": text}]}
        )

    if not normalized:
        normalized = [
            {"role": "user", "content": [{"type": "text", "text": ""}]}
        ]

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


def call_minimax(messages, model: str, *, settings: Optional[Settings] = None):
    """Call MiniMax via OpenAI- or Anthropic-compatible endpoints."""
    settings = _resolve_settings(settings)

    try:
        assert_egress_allowed("minimax", settings=settings)
    except EgressDeniedError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc

    api_key = (settings.MINIMAX_API_KEY or "").strip()
    if not api_key:
        raise HTTPException(
            status_code=400,
            detail="MINIMAX_API_KEY is not configured",
        )

    base_url = (settings.MINIMAX_API_BASE or "").strip().rstrip("/")
    if not base_url:
        raise HTTPException(
            status_code=400,
            detail="MINIMAX_API_BASE is not configured",
        )

    api_flavor = str(getattr(settings, "MINIMAX_API_FLAVOR", "openai") or "")
    api_flavor = api_flavor.strip().lower() or "openai"
    if api_flavor not in {"openai", "anthropic"}:
        raise HTTPException(
            status_code=400,
            detail="MINIMAX_API_FLAVOR must be one of: openai, anthropic",
        )

    if api_flavor == "anthropic":
        anthropic_messages, system_prompt = _normalize_messages_for_anthropic(
            messages
        )
        payload: Dict[str, Any] = {
            "model": model,
            "messages": anthropic_messages,
            "temperature": 0.7,
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
        if base_url.endswith("/v1"):
            url = f"{base_url}/messages"
        else:
            url = f"{base_url}/v1/messages"
    else:
        payload = {
            "model": model,
            "messages": messages,
            "temperature": 0.7,
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
        logger.exception("MiniMax backend request error")
        detail = _sanitize_provider_error(str(exc), secret=api_key)
        raise HTTPException(
            status_code=502,
            detail=f"MiniMax request failed: {detail}",
        ) from exc

    if not (200 <= response.status_code < 300):
        detail = _extract_provider_error_message(response, secret=api_key)
        raise HTTPException(
            status_code=502,
            detail=f"MiniMax request failed ({response.status_code}): {detail}",
        )

    try:
        data = response.json()
        if api_flavor == "anthropic":
            text = _extract_anthropic_text(data)
            if text:
                return text
            raise KeyError("content")
        return data["choices"][0]["message"]["content"]
    except Exception as exc:
        logger.exception("MiniMax backend response parse error")
        detail = _sanitize_provider_error(str(exc), secret=api_key)
        raise HTTPException(
            status_code=502,
            detail=f"MiniMax response parse failed: {detail}",
        ) from exc
