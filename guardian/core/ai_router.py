import json
import logging
from typing import Any, Dict, Optional, Sequence

import requests
from fastapi import HTTPException
from requests import exceptions as req_exc

from guardian.core.config import Settings, get_settings

logger = logging.getLogger(__name__)

_DEFAULT_OPENAI_BASE = "https://api.openai.com"
_DEFAULT_GROQ_BASE = "https://api.groq.com"


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
    provider_name = (
        (provider or settings.LLM_PROVIDER or "groq").strip().lower()
    )
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
