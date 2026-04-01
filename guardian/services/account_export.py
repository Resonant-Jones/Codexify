from __future__ import annotations

import hashlib
import importlib.metadata
import json
import os
import tempfile
import zipfile
from contextlib import suppress
from dataclasses import dataclass
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Any, Iterable

from guardian.core.auth import AuthenticatedUser

MANIFEST_SCHEMA_VERSION = "1"
EXPORT_KIND = "full_account"
ZIP_FILENAME = "Codexify-Export.zip"
PAYLOAD_ORDER = (
    (
        "projects",
        "entities/projects.json",
        "fetch_account_export_projects_for_user",
    ),
    (
        "chat_threads",
        "entities/chat_threads.json",
        "fetch_account_export_chat_threads_for_user",
    ),
    (
        "chat_messages",
        "entities/chat_messages.json",
        "fetch_account_export_chat_messages_for_user",
    ),
    (
        "uploaded_documents",
        "entities/uploaded_documents.json",
        "fetch_account_export_uploaded_documents_for_user",
    ),
    (
        "generated_documents",
        "entities/generated_documents.json",
        "fetch_account_export_generated_documents_for_user",
    ),
    (
        "uploaded_images",
        "entities/uploaded_images.json",
        "fetch_account_export_uploaded_images_for_user",
    ),
    (
        "generated_images",
        "entities/generated_images.json",
        "fetch_account_export_generated_images_for_user",
    ),
    (
        "media_assets",
        "entities/media_assets.json",
        "fetch_account_export_media_assets_for_user",
    ),
    (
        "media_aliases",
        "entities/media_aliases.json",
        "fetch_account_export_media_aliases_for_user",
    ),
    (
        "thread_documents",
        "entities/thread_documents.json",
        "fetch_account_export_thread_documents_for_user",
    ),
    (
        "project_document_links",
        "entities/project_document_links.json",
        "fetch_account_export_project_document_links_for_user",
    ),
)

OMITTED_BINARY_COVERAGE = (
    "uploaded_documents.binary_payload",
    "generated_documents.binary_payload",
    "uploaded_images.binary_payload",
    "generated_images.binary_payload",
    "media_assets.binary_payload",
)


@dataclass(frozen=True)
class _PayloadArtifact:
    family: str
    path: str
    row_count: int
    size_bytes: int
    sha256: str


def _json_default(value: Any) -> Any:
    if isinstance(value, (datetime, date)):
        if isinstance(value, datetime) and value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc).isoformat()
        return value.isoformat()
    if isinstance(value, Decimal):
        return float(value)
    return str(value)


def _dump_json(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        default=_json_default,
    ).encode("utf-8")


def _resolve_app_version() -> str:
    try:
        return importlib.metadata.version("guardian_codex")
    except Exception:
        return "0.1.0"


def _reader_rows(
    db: Any, method_name: str, user_id: str
) -> list[dict[str, Any]]:
    reader = getattr(db, method_name, None)
    if not callable(reader):
        raise RuntimeError(
            f"Account export reader {method_name} is not available on {type(db).__name__}"
        )
    rows = reader(user_id)
    if rows is None:
        return []
    return [dict(row) for row in rows]


def _iter_account_export_payloads(
    db: Any, user: AuthenticatedUser
) -> Iterable[tuple[str, str, list[dict[str, Any]]]]:
    iterator = getattr(db, "iter_account_export_payloads_for_user", None)
    if callable(iterator):
        yield from iterator(user.id)
        return

    for family, path, reader_name in PAYLOAD_ORDER:
        yield family, path, _reader_rows(db, reader_name, user.id)


def _build_manifest(
    *,
    user: AuthenticatedUser,
    created_at: str,
    app_version: str,
    payload_files: Iterable[_PayloadArtifact],
) -> dict[str, Any]:
    payload_files_list = list(payload_files)
    entity_counts = {
        payload.family: payload.row_count for payload in payload_files_list
    }
    integrity = {
        "algorithm": "sha256",
        "payload_files": {
            payload.path: {
                "sha256": payload.sha256,
                "size_bytes": payload.size_bytes,
            }
            for payload in payload_files_list
        },
    }
    return {
        "schema_version": MANIFEST_SCHEMA_VERSION,
        "app_version": app_version,
        "export_kind": EXPORT_KIND,
        "created_at": created_at,
        "user_id": user.id,
        "entity_counts": entity_counts,
        "integrity": integrity,
        "compatibility": {
            "reader": "account_export.v1",
            "restore_mode": "metadata_only",
            "binary_payloads_included": False,
        },
        "blob_mode": "metadata_only",
        "included_families": [payload.family for payload in payload_files_list],
        "omitted_families": list(OMITTED_BINARY_COVERAGE),
        "notes": [
            "manifest.json is the source of truth for this archive.",
            "This export slice includes metadata rows only; binary document, image, and media payloads are not bundled.",
            "Projects are exported by reachability from user-owned rows because project ownership is not stored directly on the projects table.",
        ],
    }


def build_account_export_zip(
    db: Any,
    user: AuthenticatedUser,
    *,
    app_version: str | None = None,
) -> str:
    created_at = datetime.now(timezone.utc).isoformat()
    resolved_app_version = app_version or _resolve_app_version()
    payload_files: list[_PayloadArtifact] = []
    temp_zip = tempfile.NamedTemporaryFile(
        mode="wb",
        suffix=".zip",
        prefix="codexify-account-export-",
        delete=False,
    )
    temp_path = temp_zip.name
    try:
        with temp_zip:
            with zipfile.ZipFile(
                temp_zip, mode="w", compression=zipfile.ZIP_DEFLATED
            ) as archive:
                for family, path, rows in _iter_account_export_payloads(
                    db, user
                ):
                    body = _dump_json(rows)
                    archive.writestr(path, body)
                    payload_files.append(
                        _PayloadArtifact(
                            family=family,
                            path=path,
                            row_count=len(rows),
                            size_bytes=len(body),
                            sha256=hashlib.sha256(body).hexdigest(),
                        )
                    )

                manifest = _build_manifest(
                    user=user,
                    created_at=created_at,
                    app_version=resolved_app_version,
                    payload_files=payload_files,
                )
                archive.writestr("manifest.json", _dump_json(manifest))
        return temp_path
    except Exception:
        with suppress(Exception):
            os.unlink(temp_path)
        raise
