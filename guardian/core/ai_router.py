import json
import logging
from typing import Any, Dict, Optional

import requests
from fastapi import HTTPException
from requests import exceptions as req_exc

from guardian.core.config import Settings, get_settings
from guardian.core.egress import EgressDeniedError, assert_egress_allowed

logger = logging.getLogger(__name__)

_DEFAULT_OPENAI_BASE = "https://api.openai.com"
_DEFAULT_GROQ_BASE = "https://api.groq.com"


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


def _format_local_connect_error(url: str, err: Exception) -> str:
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
    if "timed out" in lowered or "timeout" in lowered:
        hints.append(
            "Connection timed out. Check routing/firewalls and consider increasing "
            "LLM_REQUEST_TIMEOUT_SECONDS."
        )

    hint_text = " " + " ".join(hints) if hints else ""
    return f"Local inference request failed for {url}: {message}.{hint_text}".strip()


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
    base_url = base_url.rstrip("/")
    # Normalize accidental trailing `/v1/` (already stripped) and keep explicit versioned paths.
    if base_url.endswith("/v1"):
        return base_url
    return f"{base_url}/v1"


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
    api_key = settings.LOCAL_API_KEY or "local"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload: Dict[str, Any] = {
        "model": model,
        "messages": messages,
        "temperature": 0.7 if temperature is None else float(temperature),
    }
    if max_tokens is not None:
        payload["max_tokens"] = int(max_tokens)
    base_url = _resolve_local_base(settings)
    url = f"{base_url}/chat/completions"
    default_timeout = getattr(settings, "LLM_REQUEST_TIMEOUT_SECONDS", 60)
    request_timeout = default_timeout if timeout is None else float(timeout)

    try:
        response = requests.post(
            url, json=payload, headers=headers, timeout=request_timeout
        )
        response.raise_for_status()
        data = json.loads(response.content.decode("utf-8"))
        return data["choices"][0]["message"]["content"]
    except req_exc.RequestException as e:
        # requests-level failures: DNS, connect, timeout, etc.
        detail = _format_local_connect_error(url, e)
        if log_exceptions:
            logger.exception(detail)
        else:
            logger.warning(detail)
        raise HTTPException(status_code=502, detail=detail)
    except Exception as e:
        # Non-request exceptions (e.g. JSON decode, unexpected payload shape)
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
    api_key = settings.LOCAL_API_KEY or "local"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload: Dict[str, Any] = {
        "model": model,
        "messages": messages,
        "temperature": 0.7 if temperature is None else float(temperature),
        "stream": True,
    }
    if max_tokens is not None:
        payload["max_tokens"] = int(max_tokens)
    base_url = _resolve_local_base(settings)
    url = f"{base_url}/chat/completions"
    timeout = getattr(settings, "LLM_REQUEST_TIMEOUT_SECONDS", 60)

    try:
        with requests.post(
            url,
            json=payload,
            headers=headers,
            stream=True,
            timeout=timeout,
        ) as response:
            response.raise_for_status()
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
                    payload = json.loads(data)
                except Exception:
                    continue
                try:
                    choice = payload.get("choices", [{}])[0]
                    delta = choice.get("delta") or {}
                    token = (
                        delta.get("content")
                        or choice.get("message", {}).get("content")
                        or choice.get("text")
                    )
                    if token:
                        yield token
                except Exception:
                    continue
    except req_exc.RequestException as e:
        detail = _format_local_connect_error(url, e)
        logger.exception(detail)
        raise HTTPException(status_code=502, detail=detail)
    except Exception as e:
        logger.exception("Local backend stream error")
        raise HTTPException(status_code=502, detail=str(e))


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
