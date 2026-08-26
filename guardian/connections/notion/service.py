"""Small, bounded Notion read adapter.

Only provider translation belongs here. It never persists retrieved content,
creates embeddings, or calls the historical connector subsystem.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import requests

from guardian.protocol_tokens import ConnectionCapability

NOTION_API_BASE = "https://api.notion.com/v1"
NOTION_API_VERSION = "2026-03-11"
REQUEST_TIMEOUT_SECONDS = 15
MAX_SEARCH_RESULTS = 50
MAX_BLOCKS = 200
MAX_BLOCK_DEPTH = 2
MAX_CONTENT_CHARS = 50_000


class NotionError(RuntimeError):
    error_code = "notion_provider_error"


class NotionNotConfiguredError(NotionError):
    error_code = "notion_not_configured"


class NotionAuthorizationError(NotionError):
    error_code = "notion_authorization_failed"


class NotionTransportError(NotionError):
    error_code = "notion_transport_error"


class NotionProviderError(NotionError):
    error_code = "notion_provider_error"


class NotionObjectNotFoundError(NotionProviderError):
    error_code = "notion_object_not_found"


def _retrieved_at() -> str:
    return datetime.now(timezone.utc).isoformat()


def _rich_text_text(value: Any) -> str:
    if not isinstance(value, list):
        return ""
    parts = [
        str(item.get("plain_text") or "")
        for item in value
        if isinstance(item, dict)
    ]
    return "".join(parts).strip()


def _page_title(page: dict[str, Any]) -> str:
    properties = page.get("properties")
    if isinstance(properties, dict):
        for property_value in properties.values():
            if not isinstance(property_value, dict):
                continue
            if property_value.get("type") == "title":
                title = _rich_text_text(property_value.get("title"))
                if title:
                    return title
    return "Untitled"


def _parent_metadata(page: dict[str, Any]) -> dict[str, Any] | None:
    parent = page.get("parent")
    if not isinstance(parent, dict):
        return None
    allowed = {
        key: str(value)
        for key, value in parent.items()
        if key in {"type", "page_id", "database_id", "data_source_id"}
        and isinstance(value, (str, int))
    }
    return allowed or None


def _provenance(page: dict[str, Any], retrieved_at: str) -> dict[str, Any]:
    return {
        "source_system": "notion",
        "provider": "notion",
        "external_object_id": str(page.get("id") or ""),
        "object_type": str(page.get("object") or "page"),
        "title": _page_title(page),
        "external_url": str(page.get("url") or "") or None,
        "retrieved_at": retrieved_at,
    }


def _normalize_search_page(page: dict[str, Any], retrieved_at: str) -> dict[str, Any]:
    provenance = _provenance(page, retrieved_at)
    return {
        **provenance,
        "parent": _parent_metadata(page),
        "created_at": page.get("created_time"),
        "last_edited_at": page.get("last_edited_time"),
        # Notion search does not guarantee a content snippet. A bounded title
        # is still enough to select the explicit object for content_read.
        "preview": provenance["title"][:512],
    }


def _block_text(block: dict[str, Any]) -> str:
    block_type = str(block.get("type") or "")
    payload = block.get(block_type)
    if not isinstance(payload, dict):
        return ""
    rich_text = _rich_text_text(payload.get("rich_text"))
    if rich_text:
        return rich_text
    if block_type in {"child_page", "child_database"}:
        return str(payload.get("title") or "").strip()
    if block_type == "bookmark":
        return str(payload.get("caption") or "").strip()
    return ""


class NotionClient:
    """Thin client for the Notion read endpoints used by this connection."""

    def __init__(self, integration_token: str) -> None:
        self._integration_token = integration_token

    @property
    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self._integration_token}",
            "Notion-Version": NOTION_API_VERSION,
            "Content-Type": "application/json",
        }

    def _request_json(
        self,
        method: str,
        path: str,
        *,
        json: dict[str, Any] | None = None,
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        try:
            response = requests.request(
                method,
                f"{NOTION_API_BASE}{path}",
                headers=self._headers,
                json=json,
                params=params,
                timeout=REQUEST_TIMEOUT_SECONDS,
            )
        except requests.RequestException as exc:
            raise NotionTransportError("Notion request could not be completed") from exc

        if response.status_code in {401, 403}:
            raise NotionAuthorizationError("Notion rejected the configured credential")
        if response.status_code == 404:
            raise NotionObjectNotFoundError("Requested Notion object was not found")
        if response.status_code >= 400:
            raise NotionProviderError("Notion returned an unsuccessful response")
        try:
            payload = response.json()
        except ValueError as exc:
            raise NotionProviderError("Notion returned an invalid response") from exc
        if not isinstance(payload, dict):
            raise NotionProviderError("Notion returned an invalid response")
        return payload

    def validate(self) -> None:
        # Search is a low-cost, read-only request that validates the actual
        # integration scope without assuming a global database identifier.
        self._request_json("POST", "/search", json={"page_size": 1})

    def search(
        self, *, query: str, cursor: str | None, limit: int
    ) -> dict[str, Any]:
        page_size = min(max(int(limit), 1), MAX_SEARCH_RESULTS)
        payload: dict[str, Any] = {
            "query": query,
            "page_size": page_size,
            # The read contract intentionally supports page-like content;
            # data-source querying is a later, separately bounded decision.
            "filter": {"property": "object", "value": "page"},
        }
        if cursor:
            payload["start_cursor"] = cursor
        response = self._request_json("POST", "/search", json=payload)
        retrieved_at = _retrieved_at()
        raw_results = response.get("results")
        results = [
            _normalize_search_page(item, retrieved_at)
            for item in raw_results
            if isinstance(item, dict) and item.get("object") == "page"
        ][:page_size]
        return {
            "connection_id": "notion",
            "capability": ConnectionCapability.CONTENT_SEARCH.value,
            "results": results,
            "next_cursor": (
                str(response.get("next_cursor"))
                if response.get("has_more") and response.get("next_cursor")
                else None
            ),
            "retrieved_at": retrieved_at,
        }

    def _block_children(
        self,
        block_id: str,
        *,
        depth: int,
        collected: list[dict[str, Any]],
    ) -> None:
        cursor: str | None = None
        while len(collected) < MAX_BLOCKS:
            params: dict[str, Any] = {
                "page_size": min(100, MAX_BLOCKS - len(collected)),
            }
            if cursor:
                params["start_cursor"] = cursor
            response = self._request_json(
                "GET", f"/blocks/{block_id}/children", params=params
            )
            rows = response.get("results")
            if not isinstance(rows, list):
                raise NotionProviderError("Notion returned invalid block content")
            for block in rows:
                if not isinstance(block, dict) or len(collected) >= MAX_BLOCKS:
                    continue
                collected.append(block)
                if block.get("has_children") and depth < MAX_BLOCK_DEPTH:
                    child_id = str(block.get("id") or "")
                    if child_id:
                        self._block_children(
                            child_id, depth=depth + 1, collected=collected
                        )
            if not response.get("has_more"):
                return
            next_cursor = response.get("next_cursor")
            if not next_cursor:
                return
            cursor = str(next_cursor)

    def read_page(self, object_id: str) -> dict[str, Any]:
        page = self._request_json("GET", f"/pages/{object_id}")
        if page.get("object") != "page":
            raise NotionProviderError("Selected Notion object is not a page")
        blocks: list[dict[str, Any]] = []
        self._block_children(object_id, depth=0, collected=blocks)
        lines = [text for block in blocks if (text := _block_text(block))]
        content = "\n".join(lines)[:MAX_CONTENT_CHARS]
        retrieved_at = _retrieved_at()
        provenance = _provenance(page, retrieved_at)
        return {
            "connection_id": "notion",
            "capability": ConnectionCapability.CONTENT_READ.value,
            "object": {
                **provenance,
                "parent": _parent_metadata(page),
                "created_at": page.get("created_time"),
                "last_edited_at": page.get("last_edited_time"),
            },
            "content": content,
            "content_truncated": len("\n".join(lines)) > len(content),
            "block_count": len(blocks),
            "retrieved_at": retrieved_at,
        }
