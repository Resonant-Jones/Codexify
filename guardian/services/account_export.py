from __future__ import annotations

import hashlib
import importlib.metadata
import json
import logging
import mimetypes
import os
import tempfile
import zipfile
from collections import OrderedDict
from contextlib import suppress
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any, Mapping

from guardian.core.auth import AuthenticatedUser
from guardian.core.media_signing import extract_media_path
from guardian.core.storage import FileNotFoundError as StorageFileNotFoundError
from guardian.core.storage import StorageError, create_storage_from_env

logger = logging.getLogger(__name__)

MANIFEST_SCHEMA_VERSION = "account-export.v1"
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
    (
        "extension_proposals",
        "entities/extension_proposals.json",
        "fetch_account_export_extension_proposals_for_user",
    ),
    (
        "extension_install_gate_decisions",
        "entities/extension_install_gate_decisions.json",
        "fetch_account_export_extension_install_gate_decisions_for_user",
    ),
    (
        "extension_registry_entries",
        "entities/extension_registry_entries.json",
        "fetch_account_export_extension_registry_entries_for_user",
    ),
    (
        "extension_install_bindings",
        "entities/extension_install_bindings.json",
        "fetch_account_export_extension_install_bindings_for_user",
    ),
)

PAYLOAD_FAMILIES = tuple(entry[0] for entry in PAYLOAD_ORDER)
BINARY_FAMILIES = {
    "uploaded_documents",
    "generated_documents",
    "uploaded_images",
    "generated_images",
    "media_assets",
}
OMITTED_FAMILIES = (
    "memory_entries",
    "oauth_connections",
    "personal_facts",
    "personal_fact_evidences",
    "personal_fact_revisions",
    "tts_outputs",
    "message_audio_assets",
    "connector_configs",
    "connector_runs",
    "raw_documents",
    "sync_jobs",
    "agent_deployments",
    "agent_runs",
    "agent_run_steps",
    "agent_run_attempts",
    "agent_run_artifacts",
    "agent_confidence_reports",
    "events_outbox",
    # candidate_trace is intentionally excluded from export:
    # it is non-canonical, non-restorable runtime diagnostic data
)


@dataclass(slots=True)
class _PayloadArtifact:
    family: str
    path: str
    body: bytes
    row_count: int
    size_bytes: int
    sha256: str


@dataclass(slots=True)
class _BlobArtifact:
    canonical_key: str
    path: str
    body: bytes
    size_bytes: int
    sha256: str
    family: str
    mime_type: str | None


@dataclass(slots=True)
class _BlobGroup:
    canonical_key: str
    rows: list[tuple[str, dict[str, Any]]] = field(default_factory=list)
    path: str | None = None
    body: bytes | None = None
    sha256: str | None = None
    size_bytes: int | None = None
    mime_type: str | None = None
    source_locator: str | None = None
    source_family: str | None = None
    status: str = "unresolved"
    missing_reason: str | None = None


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


def _load_rows_by_family(
    db: Any, user: AuthenticatedUser
) -> dict[str, list[dict[str, Any]]]:
    bundle_reader = getattr(db, "fetch_account_export_bundle_for_user", None)
    if callable(bundle_reader):
        bundle = bundle_reader(user.id)
        if not isinstance(bundle, Mapping):
            raise RuntimeError(
                "fetch_account_export_bundle_for_user must return a mapping"
            )
        return {
            family: [dict(row) for row in bundle.get(family, []) or []]
            for family in PAYLOAD_FAMILIES
        }

    iterator = getattr(db, "iter_account_export_payloads_for_user", None)
    if callable(iterator):
        rows_by_family = {family: [] for family in PAYLOAD_FAMILIES}
        for family, _path, rows in iterator(user.id):
            rows_by_family[family] = [dict(row) for row in rows or []]
        return rows_by_family

    rows_by_family: dict[str, list[dict[str, Any]]] = {}
    for family, _path, reader_name in PAYLOAD_ORDER:
        rows_by_family[family] = _reader_rows(db, reader_name, user.id)
    return rows_by_family


def _family_rows(
    rows_by_family: dict[str, list[dict[str, Any]]]
) -> list[tuple[str, dict[str, Any]]]:
    ordered: list[tuple[str, dict[str, Any]]] = []
    for family in PAYLOAD_FAMILIES:
        for row in rows_by_family.get(family, []):
            ordered.append((family, row))
    return ordered


def _source_locator(family: str, row: dict[str, Any]) -> str:
    if family == "generated_documents":
        return f"generated_document:{row.get('id')}"

    src_url = str(row.get("src_url") or "").strip()
    if src_url:
        return src_url

    storage_prefix = str(row.get("storage_prefix") or "").strip()
    system_name = str(row.get("system_name") or "").strip()
    if storage_prefix and system_name:
        prefix = storage_prefix.strip("/")
        return f"/media/{prefix}/{system_name}"

    filename = str(row.get("filename") or "").strip()
    if filename:
        return filename

    return f"{family}:{row.get('id')}"


def _generated_document_mime_type(row: dict[str, Any]) -> str:
    fmt = str(row.get("format") or "").strip().lower()
    mapping = {
        "txt": "text/plain; charset=utf-8",
        "md": "text/markdown; charset=utf-8",
        "markdown": "text/markdown; charset=utf-8",
        "html": "text/html; charset=utf-8",
        "htm": "text/html; charset=utf-8",
        "json": "application/json; charset=utf-8",
        "xml": "application/xml; charset=utf-8",
        "csv": "text/csv; charset=utf-8",
    }
    return mapping.get(fmt, "text/plain; charset=utf-8")


def _generated_document_extension(row: dict[str, Any]) -> str:
    fmt = str(row.get("format") or "").strip().lower()
    if fmt in {"md", "markdown"}:
        return "md"
    if fmt in {"txt", "text", "plain"}:
        return "txt"
    if fmt in {"html", "htm", "json", "xml", "csv"}:
        return fmt
    return "txt"


def _blob_extension(
    family: str, row: dict[str, Any], mime_type: str | None
) -> str:
    if family == "generated_documents":
        return _generated_document_extension(row)

    if mime_type:
        guessed = mimetypes.guess_extension(mime_type.split(";", 1)[0].strip())
        if guessed:
            return guessed.lstrip(".")

    filename = str(row.get("filename") or "").strip()
    if filename:
        suffix = Path(filename).suffix.lstrip(".")
        if suffix:
            return suffix

    locator = _source_locator(family, row)
    suffix = Path(extract_media_path(locator)).suffix.lstrip(".")
    if suffix:
        return suffix

    return "bin"


def _blob_root(family: str, row: dict[str, Any]) -> str:
    if family == "generated_documents":
        return "blobs/documents/generated"
    if family == "uploaded_documents":
        return "blobs/documents/uploaded"
    if family == "uploaded_images":
        return "blobs/images/uploaded"
    if family == "generated_images":
        return "blobs/images/generated"
    if family == "media_assets":
        media_kind = str(row.get("media_kind") or "").strip().lower()
        provenance = str(row.get("provenance") or "").strip().lower()
        if media_kind == "document" and provenance == "uploaded":
            return "blobs/documents/uploaded"
        if media_kind == "document" and provenance == "generated":
            return "blobs/documents/generated"
        if media_kind == "image" and provenance == "uploaded":
            return "blobs/images/uploaded"
        if media_kind == "image" and provenance == "generated":
            return "blobs/images/generated"
    return "blobs/media"


def _canonical_blob_key(family: str, row: dict[str, Any]) -> str:
    if family == "generated_documents":
        content = str(row.get("content") or "").encode("utf-8")
        return f"generated-document:{hashlib.sha256(content).hexdigest()}"

    asset_id = row.get("asset_id")
    if asset_id:
        return f"asset:{asset_id}"

    if family == "media_assets":
        return f"asset:{row.get('id')}"

    locator = _source_locator(family, row)
    if locator:
        return f"source:{locator}"

    return f"row:{family}:{row.get('id')}"


def _resolve_blob_candidate(
    family: str, row: dict[str, Any], storage: Any
) -> tuple[bytes, str | None, str, str] | None:
    if family == "generated_documents":
        data = str(row.get("content") or "").encode("utf-8")
        mime_type = _generated_document_mime_type(row)
        locator = _source_locator(family, row)
        extension = _blob_extension(family, row, mime_type)
        return data, mime_type, locator, extension

    locator = _source_locator(family, row)
    if not locator:
        return None

    try:
        data = storage.download_file(extract_media_path(locator))
    except (StorageFileNotFoundError, StorageError, FileNotFoundError):
        return None
    except Exception:
        logger.warning(
            "Failed to resolve blob for %s row %s from %s",
            family,
            row.get("id"),
            locator,
            exc_info=True,
        )
        return None

    mime_type = str(row.get("mime_type") or "").strip() or None
    extension = _blob_extension(family, row, mime_type)
    return data, mime_type, locator, extension


def _build_blob_groups(
    rows_by_family: dict[str, list[dict[str, Any]]],
    storage: Any,
) -> dict[str, _BlobGroup]:
    groups: OrderedDict[str, _BlobGroup] = OrderedDict()
    for family, row in _family_rows(rows_by_family):
        if family not in BINARY_FAMILIES:
            continue
        key = _canonical_blob_key(family, row)
        group = groups.get(key)
        if group is None:
            group = _BlobGroup(canonical_key=key)
            groups[key] = group
        group.rows.append((family, row))

    for group in groups.values():
        for family, row in group.rows:
            resolved = _resolve_blob_candidate(family, row, storage)
            if resolved is None:
                continue

            body, mime_type, locator, extension = resolved
            digest = hashlib.sha256(body).hexdigest()
            group.path = f"{_blob_root(family, row)}/{digest}.{extension}"
            group.body = body
            group.sha256 = digest
            group.size_bytes = len(body)
            group.mime_type = mime_type
            group.source_locator = locator
            group.source_family = family
            group.status = "bundled"
            break

        if group.status != "bundled":
            group.missing_reason = (
                "blob could not be resolved from current storage"
            )

    return dict(groups)


def _decorate_binary_row(
    family: str, row: dict[str, Any], group: _BlobGroup
) -> dict[str, Any]:
    blob_status = "bundled" if group.status == "bundled" else "unresolved"
    canonical_blob_id = group.canonical_key
    blob: dict[str, Any] = {
        "status": blob_status,
        "canonical_blob_id": canonical_blob_id,
        "source_family": family,
        "row_id": row.get("id"),
        "asset_id": row.get("asset_id")
        or (row.get("id") if family == "media_assets" else None),
        "source_locator": _source_locator(family, row),
        "mime_type": group.mime_type or row.get("mime_type"),
        "content_hash": group.sha256 or row.get("content_hash"),
        "size_bytes": (
            group.size_bytes
            if group.size_bytes is not None
            else row.get("filesize")
        ),
    }

    if blob_status == "bundled":
        blob["bundle_path"] = group.path
        blob["sha256"] = group.sha256
    else:
        blob["bundle_path"] = None
        blob["sha256"] = None
        blob["missing_reason"] = group.missing_reason

    decorated = dict(row)
    decorated["export"] = {"blob": blob}
    return decorated


def _build_manifest(
    *,
    user: AuthenticatedUser,
    created_at: str,
    app_version: str,
    payload_files: list[_PayloadArtifact],
    blob_files: list[_BlobArtifact],
    rows_by_family: dict[str, list[dict[str, Any]]],
    decorated_binary_rows: dict[str, list[dict[str, Any]]],
    unresolved_rows: list[dict[str, Any]],
) -> dict[str, Any]:
    entity_counts = {
        artifact.family: artifact.row_count for artifact in payload_files
    }
    payload_integrity = {
        artifact.path: {
            "sha256": artifact.sha256,
            "size_bytes": artifact.size_bytes,
        }
        for artifact in payload_files
    }
    blob_integrity = {
        artifact.path: {
            "sha256": artifact.sha256,
            "size_bytes": artifact.size_bytes,
        }
        for artifact in blob_files
    }
    all_integrity = {**payload_integrity, **blob_integrity}
    bundled_families = sorted(
        {
            family
            for family, rows in decorated_binary_rows.items()
            if rows
            and any(
                row.get("export", {}).get("blob", {}).get("status") == "bundled"
                for row in rows
            )
        }
    )
    missing_families = sorted(
        {
            family
            for family, rows in decorated_binary_rows.items()
            if rows
            and any(
                row.get("export", {}).get("blob", {}).get("status")
                == "unresolved"
                for row in rows
            )
        }
    )
    binary_complete_families = sorted(
        family
        for family in BINARY_FAMILIES
        if rows_by_family.get(family)
        and all(
            row.get("export", {}).get("blob", {}).get("status") == "bundled"
            for row in decorated_binary_rows.get(family, [])
        )
    )

    return {
        "schema_version": MANIFEST_SCHEMA_VERSION,
        "app_version": app_version,
        "export_kind": EXPORT_KIND,
        "created_at": created_at,
        "user_id": user.id,
        "entity_counts": entity_counts,
        "integrity": {
            "algorithm": "sha256",
            "payload_files": payload_integrity,
            "blob_files": blob_integrity,
            "files": all_integrity,
        },
        "compatibility": {
            "reader": "account_export.v1",
            "restore_mode": "not_implemented",
            "binary_payloads_included": bool(blob_files),
            "blob_layout": "canonical-content-hash-v1",
        },
        "blob_mode": "canonical_bundled" if blob_files else "metadata_only",
        "included_families": list(PAYLOAD_FAMILIES),
        "binary_complete_families": binary_complete_families,
        "omitted_families": list(OMITTED_FAMILIES),
        "blob_coverage": {
            "bundled_families": bundled_families,
            "missing_families": missing_families,
            "bundled_blob_paths": [artifact.path for artifact in blob_files],
            "unresolved_rows": unresolved_rows,
        },
        "notes": [
            "manifest.json is the source of truth for this archive.",
            "Restore/import is not implemented in this task.",
            "Resolvable document, image, and media bytes are bundled as canonical blob files; unresolved rows are retained with export.blob.status='unresolved'.",
            "Generated documents are exported from stored UTF-8 content because the current schema stores the document body in the database rather than a separate binary file.",
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
    rows_by_family = _load_rows_by_family(db, user)
    storage = create_storage_from_env()
    blob_groups = _build_blob_groups(rows_by_family, storage)

    payload_files: list[_PayloadArtifact] = []
    blob_files: list[_BlobArtifact] = []
    decorated_binary_rows: dict[str, list[dict[str, Any]]] = {
        family: [] for family in BINARY_FAMILIES
    }
    unresolved_rows: list[dict[str, Any]] = []

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
                for family, path, _reader in PAYLOAD_ORDER:
                    source_rows = rows_by_family.get(family, [])
                    payload_rows: list[dict[str, Any]] = []
                    for row in source_rows:
                        if family in BINARY_FAMILIES:
                            group = blob_groups[
                                _canonical_blob_key(family, row)
                            ]
                            decorated = _decorate_binary_row(family, row, group)
                            payload_rows.append(decorated)
                            decorated_binary_rows[family].append(decorated)
                            blob = decorated["export"]["blob"]
                            if blob["status"] == "unresolved":
                                unresolved_rows.append(
                                    {
                                        "family": family,
                                        "row_id": row.get("id"),
                                        "canonical_blob_id": blob[
                                            "canonical_blob_id"
                                        ],
                                        "source_locator": blob[
                                            "source_locator"
                                        ],
                                        "reason": blob["missing_reason"],
                                    }
                                )
                        else:
                            payload_rows.append(dict(row))

                    body = _dump_json(payload_rows)
                    archive.writestr(path, body)
                    payload_files.append(
                        _PayloadArtifact(
                            family=family,
                            path=path,
                            body=body,
                            row_count=len(payload_rows),
                            size_bytes=len(body),
                            sha256=hashlib.sha256(body).hexdigest(),
                        )
                    )

                for group in sorted(
                    blob_groups.values(),
                    key=lambda item: (item.path or "", item.canonical_key),
                ):
                    if (
                        group.status != "bundled"
                        or group.path is None
                        or group.body is None
                    ):
                        continue
                    archive.writestr(group.path, group.body)
                    blob_files.append(
                        _BlobArtifact(
                            canonical_key=group.canonical_key,
                            path=group.path,
                            body=group.body,
                            size_bytes=group.size_bytes or len(group.body),
                            sha256=group.sha256
                            or hashlib.sha256(group.body).hexdigest(),
                            family=group.source_family or "media",
                            mime_type=group.mime_type,
                        )
                    )

                manifest = _build_manifest(
                    user=user,
                    created_at=created_at,
                    app_version=resolved_app_version,
                    payload_files=payload_files,
                    blob_files=blob_files,
                    rows_by_family=rows_by_family,
                    decorated_binary_rows=decorated_binary_rows,
                    unresolved_rows=unresolved_rows,
                )
                archive.writestr("manifest.json", _dump_json(manifest))
        return temp_path
    except Exception:
        with suppress(Exception):
            os.unlink(temp_path)
        raise
