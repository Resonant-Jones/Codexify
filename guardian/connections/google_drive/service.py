"""Bounded Google Drive metadata and Google Docs read adapter."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import requests

from guardian.protocol_tokens import ConnectionCapability

GOOGLE_DRIVE_API_BASE = "https://www.googleapis.com/drive/v3"
GOOGLE_DOCS_API_BASE = "https://docs.googleapis.com/v1"
GOOGLE_DOCUMENT_MIME_TYPE = "application/vnd.google-apps.document"
REQUEST_TIMEOUT_SECONDS = 15
MAX_SEARCH_RESULTS = 50
MAX_CONTENT_CHARS = 50_000


class GoogleDriveError(RuntimeError):
    error_code = "google_drive_provider_error"


class GoogleDriveAuthorizationError(GoogleDriveError):
    error_code = "google_drive_authorization_failed"


class GoogleDriveTransportError(GoogleDriveError):
    error_code = "google_drive_transport_error"


class GoogleDriveProviderError(GoogleDriveError):
    error_code = "google_drive_provider_error"


class GoogleDriveObjectNotFoundError(GoogleDriveProviderError):
    error_code = "google_drive_object_not_found"


class GoogleDriveUnsupportedObjectError(GoogleDriveProviderError):
    error_code = "google_drive_unsupported_object_type"


def _retrieved_at() -> str:
    return datetime.now(timezone.utc).isoformat()


def _drive_query(query: str) -> str:
    # Google Drive query literals escape both backslash and apostrophe.
    escaped = query.replace("\\", "\\\\").replace("'", "\\'")
    clauses = [
        f"mimeType = '{GOOGLE_DOCUMENT_MIME_TYPE}'",
        "trashed = false",
    ]
    if escaped:
        clauses.append(f"name contains '{escaped}'")
    return " and ".join(clauses)


def _owner_metadata(file_data: dict[str, Any]) -> list[str]:
    owners = file_data.get("owners")
    if not isinstance(owners, list):
        return []
    return [
        str(owner.get("displayName") or "").strip()
        for owner in owners
        if isinstance(owner, dict) and str(owner.get("displayName") or "").strip()
    ][:10]


def _provenance(file_data: dict[str, Any], retrieved_at: str) -> dict[str, Any]:
    object_id = str(file_data.get("id") or "")
    return {
        "source_system": "google_drive",
        "provider": "google_drive",
        "external_object_id": object_id,
        "object_type": "google_document",
        "title": str(file_data.get("name") or "Untitled"),
        "mime_type": str(file_data.get("mimeType") or ""),
        "external_url": str(file_data.get("webViewLink") or "")
        or f"https://docs.google.com/document/d/{object_id}/edit",
        "retrieved_at": retrieved_at,
    }


def _normalize_search_result(file_data: dict[str, Any], retrieved_at: str) -> dict[str, Any]:
    provenance = _provenance(file_data, retrieved_at)
    description = str(file_data.get("description") or "")
    return {
        **provenance,
        "parents": [str(parent) for parent in file_data.get("parents", [])][:20]
        if isinstance(file_data.get("parents"), list)
        else [],
        "drive_id": str(file_data.get("driveId") or "") or None,
        "created_at": file_data.get("createdTime"),
        "modified_at": file_data.get("modifiedTime"),
        "owner_display_names": _owner_metadata(file_data),
        "preview": description[:512] or provenance["title"][:512],
        "readable": True,
    }


def _paragraph_text(paragraph: dict[str, Any]) -> str:
    elements = paragraph.get("elements")
    if not isinstance(elements, list):
        return ""
    text = "".join(
        str(element.get("textRun", {}).get("content") or "")
        for element in elements
        if isinstance(element, dict) and isinstance(element.get("textRun"), dict)
    ).rstrip("\n")
    if not text:
        return ""
    style = str(paragraph.get("paragraphStyle", {}).get("namedStyleType") or "")
    heading_level = {
        "HEADING_1": 1,
        "HEADING_2": 2,
        "HEADING_3": 3,
        "HEADING_4": 4,
        "HEADING_5": 5,
        "HEADING_6": 6,
    }.get(style)
    if heading_level:
        return f"{'#' * heading_level} {text}"
    if paragraph.get("bullet") is not None:
        return f"- {text}"
    return text


def _content_lines(content: Any) -> list[str]:
    if not isinstance(content, list):
        return []
    lines: list[str] = []
    for element in content:
        if not isinstance(element, dict):
            continue
        paragraph = element.get("paragraph")
        if isinstance(paragraph, dict):
            if text := _paragraph_text(paragraph):
                lines.append(text)
            continue
        table = element.get("table")
        if not isinstance(table, dict):
            continue
        rows = table.get("tableRows")
        if not isinstance(rows, list):
            continue
        for row in rows:
            cells = row.get("tableCells") if isinstance(row, dict) else None
            if not isinstance(cells, list):
                continue
            cell_text = [" ".join(_content_lines(cell.get("content"))) for cell in cells if isinstance(cell, dict)]
            lines.append(" | ".join(part for part in cell_text if part))
    return lines


class GoogleDriveClient:
    """Google REST translation for discovery and native Google Docs reads."""

    def __init__(self, access_token: str) -> None:
        self._access_token = access_token

    @property
    def _headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self._access_token}"}

    def _request_json(
        self,
        method: str,
        url: str,
        *,
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        try:
            response = requests.request(
                method,
                url,
                headers=self._headers,
                params=params,
                timeout=REQUEST_TIMEOUT_SECONDS,
            )
        except requests.RequestException as exc:
            raise GoogleDriveTransportError("Google request could not be completed") from exc
        if response.status_code in {401, 403}:
            raise GoogleDriveAuthorizationError("Google rejected the credential")
        if response.status_code == 404:
            raise GoogleDriveObjectNotFoundError("Google object was not found")
        if response.status_code >= 400:
            raise GoogleDriveProviderError("Google returned an unsuccessful response")
        try:
            payload = response.json()
        except ValueError as exc:
            raise GoogleDriveProviderError("Google returned invalid JSON") from exc
        if not isinstance(payload, dict):
            raise GoogleDriveProviderError("Google returned invalid JSON")
        return payload

    def validate(self) -> None:
        # A bounded metadata query proves the token can access the scoped Drive
        # surface without fetching document content or mutating anything.
        self._request_json(
            "GET",
            f"{GOOGLE_DRIVE_API_BASE}/files",
            params={
                "q": _drive_query(""),
                "pageSize": 1,
                "fields": "files(id)",
                "spaces": "drive",
                "supportsAllDrives": "true",
                "includeItemsFromAllDrives": "true",
            },
        )

    def search(self, *, query: str, cursor: str | None, limit: int) -> dict[str, Any]:
        page_size = min(max(int(limit), 1), MAX_SEARCH_RESULTS)
        params: dict[str, Any] = {
            "q": _drive_query(query),
            "pageSize": page_size,
            "orderBy": "modifiedTime desc,name",
            "spaces": "drive",
            "supportsAllDrives": "true",
            "includeItemsFromAllDrives": "true",
            "fields": (
                "nextPageToken,incompleteSearch,files("
                "id,name,mimeType,parents,webViewLink,createdTime,modifiedTime,"
                "description,driveId,owners(displayName))"
            ),
        }
        if cursor:
            params["pageToken"] = cursor
        response = self._request_json("GET", f"{GOOGLE_DRIVE_API_BASE}/files", params=params)
        retrieved_at = _retrieved_at()
        files = response.get("files")
        results = [
            _normalize_search_result(file_data, retrieved_at)
            for file_data in files
            if isinstance(file_data, dict)
            and file_data.get("mimeType") == GOOGLE_DOCUMENT_MIME_TYPE
        ][:page_size]
        return {
            "connection_id": "google_drive",
            "capability": ConnectionCapability.CONTENT_SEARCH.value,
            "results": results,
            "next_cursor": str(response.get("nextPageToken") or "") or None,
            "incomplete_search": bool(response.get("incompleteSearch")),
            "shared_drive_flags": {
                "supports_all_drives": True,
                "include_items_from_all_drives": True,
            },
            "retrieved_at": retrieved_at,
        }

    def _file_metadata(self, object_id: str) -> dict[str, Any]:
        return self._request_json(
            "GET",
            f"{GOOGLE_DRIVE_API_BASE}/files/{object_id}",
            params={
                "fields": (
                    "id,name,mimeType,parents,webViewLink,createdTime,modifiedTime,"
                    "description,driveId,owners(displayName)"
                ),
                "supportsAllDrives": "true",
            },
        )

    def read_document(self, object_id: str) -> dict[str, Any]:
        file_data = self._file_metadata(object_id)
        if file_data.get("mimeType") != GOOGLE_DOCUMENT_MIME_TYPE:
            raise GoogleDriveUnsupportedObjectError("Selected object is not a Google Doc")
        document = self._request_json(
            "GET",
            f"{GOOGLE_DOCS_API_BASE}/documents/{object_id}",
            params={"includeTabsContent": "false"},
        )
        lines = _content_lines(document.get("body", {}).get("content"))
        full_content = "\n".join(line for line in lines if line).strip()
        content = full_content[:MAX_CONTENT_CHARS]
        retrieved_at = _retrieved_at()
        return {
            "connection_id": "google_drive",
            "capability": ConnectionCapability.CONTENT_READ.value,
            "object": {
                **_provenance(file_data, retrieved_at),
                "parents": [str(parent) for parent in file_data.get("parents", [])][:20]
                if isinstance(file_data.get("parents"), list)
                else [],
                "drive_id": str(file_data.get("driveId") or "") or None,
                "created_at": file_data.get("createdTime"),
                "modified_at": file_data.get("modifiedTime"),
                "document_title": str(document.get("title") or file_data.get("name") or "Untitled"),
            },
            "content": content,
            "content_truncated": len(full_content) > len(content),
            "structure": {"line_count": len(lines), "document_tabs": "default_tab_only"},
            "retrieved_at": retrieved_at,
        }
