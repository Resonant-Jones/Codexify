"""Groq Search-as-RAG adapter for Remote Recall.

This is the first concrete provider adapter behind the provider-neutral
Search-as-RAG boundary. It follows the current official Groq web-search support,
which is built into the ``groq/compound`` and ``groq/compound-mini`` Compound
systems (server-side web search with citations exposed via
``choices[0].message.executed_tools[*].search_results``).

Adapter behavior:

- calls Groq only when ``GROQ_WEB_SEARCH_ENABLED`` is true, ``GROQ_API_KEY`` is
  present, and the ``groq`` egress target is explicitly allowed
- normalizes Groq response citations / executed tool search-result metadata into
  the provider-neutral :class:`SearchProviderResult`
- never returns raw provider objects to the completion service
- exposes deterministic behavior in tests by allowing an injected fake transport

Remote Recall uses Groq as a search provider only. The synthesized
``message.content`` is **not** treated as the answer: only the normalized search
results become candidate evidence for the Web Evidence Intake Gate.

See:
- docs/architecture/web-search-provider-adapter-contract.md
- https://console.groq.com/docs/tool-use/built-in-tools/web-search
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Callable

from guardian.core.config import Settings
from guardian.core.egress import EgressDeniedError, assert_egress_allowed
from guardian.protocol_tokens import RemoteRecallFailureReason, RemoteRecallSourceKind
from guardian.web.contracts import (
    SearchProviderRequest,
    SearchProviderResult,
    SearchResultItem,
)

logger = logging.getLogger(__name__)

DEFAULT_GROQ_WEB_SEARCH_MODEL = "groq/compound-mini"
SUPPORTED_GROQ_WEB_SEARCH_MODELS = ("groq/compound", "groq/compound-mini")
_DEFAULT_GROQ_BASE = "https://api.groq.com"

# A transport takes the request payload and a timeout and returns the parsed
# Groq response JSON. Tests inject a fake transport; the default transport
# performs a real OpenAI-compatible HTTP POST using httpx.
SearchTransport = Callable[[dict[str, Any], float], dict[str, Any]]


def _coerce_str(value: Any) -> str:
    if value is None:
        return ""
    return str(value)


def _coerce_score(value: Any) -> float | None:
    if value is None:
        return None
    try:
        score = float(value)
    except (TypeError, ValueError):
        return None
    return score


def _extract_search_results(payload: dict[str, Any]) -> list[dict[str, Any]]:
    """Defensively extract raw search-result rows from a Groq response.

    Groq exposes web-search citations via
    ``choices[*].message.executed_tools[*].search_results``. ``search_results``
    may be a dict with a ``results`` list or a bare list, and individual rows
    may omit any field. This helper never raises on missing metadata.
    """

    rows: list[dict[str, Any]] = []
    choices = payload.get("choices") if isinstance(payload, dict) else None
    if not isinstance(choices, list):
        return rows
    for choice in choices:
        if not isinstance(choice, dict):
            continue
        message = choice.get("message")
        if not isinstance(message, dict):
            continue
        executed_tools = message.get("executed_tools")
        if not isinstance(executed_tools, list):
            continue
        for tool in executed_tools:
            if not isinstance(tool, dict):
                continue
            search_results = tool.get("search_results")
            candidate_rows: list[Any]
            if isinstance(search_results, dict):
                candidate_rows = search_results.get("results") or []
            elif isinstance(search_results, list):
                candidate_rows = search_results
            else:
                continue
            for row in candidate_rows:
                if isinstance(row, dict):
                    rows.append(row)
    return rows


def _normalize_result_row(
    row: dict[str, Any],
    *,
    rank: int,
    retrieved_at: str,
) -> SearchResultItem | None:
    url = _coerce_str(row.get("url")).strip()
    title = _coerce_str(row.get("title")).strip()
    content = _coerce_str(row.get("content")).strip()
    # Groq rows occasionally use "snippet" instead of "content".
    snippet = content or _coerce_str(row.get("snippet")).strip()
    if not url and not title and not snippet:
        return None
    score = _coerce_score(row.get("score"))
    return SearchResultItem(
        provider="groq",
        source_kind=RemoteRecallSourceKind.GROQ_WEB_SEARCH.value,
        url=url,
        title=title,
        snippet=snippet,
        text="",
        rank=rank,
        score=score,
        retrieved_at=retrieved_at,
        citation={
            "title": title,
            "url": url,
        },
        provider_metadata={"groq_score": score} if score is not None else {},
    )


class GroqSearchAdapter:
    """Search-as-RAG adapter targeting Groq built-in web search."""

    def __init__(
        self,
        settings: Settings,
        *,
        transport: SearchTransport | None = None,
        source_kind: str = RemoteRecallSourceKind.GROQ_WEB_SEARCH.value,
    ) -> None:
        self._settings = settings
        self._transport = transport
        self._source_kind = source_kind

    def _resolve_model(self) -> str:
        model = _coerce_str(getattr(self._settings, "GROQ_WEB_SEARCH_MODEL", "")).strip()
        if not model:
            model = DEFAULT_GROQ_WEB_SEARCH_MODEL
        if model not in SUPPORTED_GROQ_WEB_SEARCH_MODELS:
            logger.warning(
                "[remote-recall] GROQ_WEB_SEARCH_MODEL=%s is not in the official "
                "Groq web-search supported set %s; using %s",
                model,
                SUPPORTED_GROQ_WEB_SEARCH_MODELS,
                DEFAULT_GROQ_WEB_SEARCH_MODEL,
            )
            return DEFAULT_GROQ_WEB_SEARCH_MODEL
        return model

    def _resolve_base_url(self) -> str:
        base = _coerce_str(getattr(self._settings, "GROQ_BASE_URL", "")).strip()
        return (base or _DEFAULT_GROQ_BASE).rstrip("/")

    def is_enabled(self) -> bool:
        """Return True only when every gate for a Groq web-search call is open."""

        if not bool(getattr(self._settings, "GROQ_WEB_SEARCH_ENABLED", False)):
            return False
        if not _coerce_str(getattr(self._settings, "GROQ_API_KEY", "")).strip():
            return False
        try:
            assert_egress_allowed("groq", settings=self._settings)
        except EgressDeniedError:
            return False
        return True

    def _failure(
        self,
        request: SearchProviderRequest,
        reason: RemoteRecallFailureReason,
    ) -> SearchProviderResult:
        return SearchProviderResult(
            request_id=request.request_id,
            provider="groq",
            source_kind=self._source_kind,
            status="error",
            result_count=0,
            results=[],
            provider_metadata={},
            blocked_reason=reason.value,
        )

    def invoke(self, request: SearchProviderRequest) -> SearchProviderResult:
        """Invoke the Groq web-search adapter and normalize its response.

        Fails closed (returns a ``status="error"`` result with a canonical
        ``blocked_reason``) when any gate is closed or normalization yields no
        usable rows. Never returns raw provider objects.
        """

        if not self.is_enabled():
            return self._failure(request, RemoteRecallFailureReason.PROVIDER_NOT_CONFIGURED)

        transport = self._transport or _default_groq_transport(self._settings)
        retrieved_at = datetime.now(timezone.utc).isoformat()

        payload: dict[str, Any] = {
            "model": self._resolve_model(),
            "messages": [
                {"role": "user", "content": request.query},
            ],
        }
        search_settings = _build_search_settings(request)
        if search_settings:
            payload["search_settings"] = search_settings

        timeout = float(getattr(self._settings, "REMOTE_RECALL_TIMEOUT_SECONDS", 20.0))
        try:
            response = transport(payload, timeout)
        except Exception as exc:
            logger.warning("[remote-recall] groq transport failed: %s", exc)
            return self._failure(request, RemoteRecallFailureReason.PROVIDER_UNAVAILABLE)
        if not isinstance(response, dict):
            logger.warning(
                "[remote-recall] groq transport returned non-dict response"
            )
            return self._failure(request, RemoteRecallFailureReason.NORMALIZATION_FAILED)

        rows = _extract_search_results(response)
        items: list[SearchResultItem] = []
        for index, row in enumerate(rows):
            normalized = _normalize_result_row(
                row, rank=index, retrieved_at=retrieved_at
            )
            if normalized is not None:
                items.append(normalized)
            if len(items) >= request.max_results:
                break

        if not items:
            return SearchProviderResult(
                request_id=request.request_id,
                provider="groq",
                source_kind=self._source_kind,
                status="empty",
                result_count=0,
                results=[],
                provider_metadata={"raw_row_count": len(rows)},
                blocked_reason=RemoteRecallFailureReason.EMPTY_RESULT_SET.value,
            )

        return SearchProviderResult(
            request_id=request.request_id,
            provider="groq",
            source_kind=self._source_kind,
            status="ok",
            result_count=len(items),
            results=items,
            provider_metadata={"raw_row_count": len(rows)},
            blocked_reason=None,
        )


def _build_search_settings(request: SearchProviderRequest) -> dict[str, Any] | None:
    extra = request.extra or {}
    include_domains = extra.get("include_domains")
    exclude_domains = extra.get("exclude_domains")
    country = extra.get("country") or request.locale
    settings: dict[str, Any] = {}
    if isinstance(include_domains, list) and include_domains:
        settings["include_domains"] = [str(d) for d in include_domains]
    if isinstance(exclude_domains, list) and exclude_domains:
        settings["exclude_domains"] = [str(d) for d in exclude_domains]
    if country:
        settings["country"] = str(country)
    return settings or None


def _default_groq_transport(settings: Settings) -> SearchTransport:
    """Build the real OpenAI-compatible httpx transport for Groq web search."""

    base_url = (_coerce_str(getattr(settings, "GROQ_BASE_URL", "")).strip()
                or _DEFAULT_GROQ_BASE).rstrip("/")
    api_key = _coerce_str(getattr(settings, "GROQ_API_KEY", "")).strip()
    endpoint = f"{base_url}/openai/v1/chat/completions"

    def transport(payload: dict[str, Any], timeout: float) -> dict[str, Any]:
        try:
            import httpx
        except ImportError as exc:  # pragma: no cover - environment guard
            raise RuntimeError("httpx is required for the Groq web-search transport") from exc

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        with httpx.Client(timeout=timeout) as client:
            response = client.post(endpoint, headers=headers, json=payload)
            response.raise_for_status()
            return response.json()

    return transport


__all__ = [
    "DEFAULT_GROQ_WEB_SEARCH_MODEL",
    "GroqSearchAdapter",
    "SUPPORTED_GROQ_WEB_SEARCH_MODELS",
]
