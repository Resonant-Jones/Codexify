from __future__ import annotations

import hashlib
import io
import json
import logging
import zipfile
from collections import Counter
from dataclasses import dataclass
from typing import Any

from guardian.cognition.system_profiles.manifest import PersonaProfileManifest
from guardian.extensions.tokens import (
    EXTENSION_INSTALL_BINDING_SCOPES,
    EXTENSION_INSTALL_BINDING_STATUSES,
    CapabilityEntryProvenanceClass,
    CapabilityRegistryStatus,
    ExtensionInstallBindingScope,
    ExtensionInstallBindingStatus,
    InstallGateDecisionToken,
)
from guardian.services.account_export import (
    EXPORT_KIND,
    MANIFEST_SCHEMA_VERSION,
    PAYLOAD_FAMILIES,
    PAYLOAD_ORDER,
    PAYLOAD_ORDER_BY_SCHEMA,
)

logger = logging.getLogger(__name__)

SUPPORTED_SCHEMA_VERSIONS = {
    "account-export.v1",
    "account-export.v2",
    MANIFEST_SCHEMA_VERSION,
}

# Restore order is dependency-safe for the current schema. It differs from the
# export order because `chat_threads` must exist before any row that points at a
# thread, and `media_assets` must exist before document/image rows that carry an
# `asset_id` FK. V3 also restores Persona state before any pinned thread.
HISTORICAL_RESTORE_ORDER = (
    "projects",
    "chat_threads",
    "chat_messages",
    "media_assets",
    "media_aliases",
    "uploaded_documents",
    "generated_documents",
    "uploaded_images",
    "generated_images",
    "thread_documents",
    "project_document_links",
    "extension_proposals",
    "extension_install_gate_decisions",
    "extension_registry_entries",
    "extension_install_bindings",
)
RESTORE_ORDER = (
    "persona_profiles",
    "persona_profile_revisions",
    "persona_profile_bindings",
    *HISTORICAL_RESTORE_ORDER,
)

RESTORE_METHODS = {
    family: f"restore_account_export_{family}" for family in RESTORE_ORDER
}

PAYLOAD_PATHS = {family: path for family, path, _ in PAYLOAD_ORDER}
REQUIRED_PAYLOAD_PATHS = tuple(PAYLOAD_PATHS[family] for family in PAYLOAD_FAMILIES)


def _zero_counts() -> dict[str, int]:
    return {
        "imported": 0,
        "skipped": 0,
        "failed": 0,
        "unresolved": 0,
    }


def _empty_blob_coverage() -> dict[str, Any]:
    return {
        "bundled_families": [],
        "missing_families": [],
        "bundled_blob_paths": [],
        "unresolved_rows": [],
        "validated_only": True,
    }


def _restore_order_for_schema(schema_version: str | None) -> tuple[str, ...]:
    if schema_version == MANIFEST_SCHEMA_VERSION:
        return RESTORE_ORDER
    return HISTORICAL_RESTORE_ORDER


def _empty_family_reports(
    restore_order: tuple[str, ...] = RESTORE_ORDER,
) -> list[dict[str, Any]]:
    return [
        {
            "family": family,
            "status": "not_started",
            "payload_rows": 0,
            "imported": 0,
            "skipped": 0,
            "failed": 0,
            "unresolved": 0,
        }
        for family in restore_order
    ]


def _sort_text(value: Any) -> str:
    if value is None:
        return ""
    return str(value)


def _normalize_row_value(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: _normalize_row_value(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_normalize_row_value(item) for item in value]
    if isinstance(value, tuple):
        return [_normalize_row_value(item) for item in value]
    if hasattr(value, "isoformat"):
        try:
            return value.isoformat()
        except Exception:
            return str(value)
    return value


def _copy_default(value: Any) -> Any:
    if isinstance(value, dict):
        return dict(value)
    if isinstance(value, list):
        return list(value)
    if isinstance(value, tuple):
        return list(value)
    return value


@dataclass(slots=True)
class ParsedArchive:
    manifest: dict[str, Any]
    payload_rows: dict[str, list[dict[str, Any]]]
    archive_names: tuple[str, ...]
    integrity_files: dict[str, dict[str, Any]]
    archive_includes_blob_coverage: bool
    blob_coverage: dict[str, Any]
    schema_version: str
    export_kind: str
    user_id: str


@dataclass(slots=True)
class FamilyRestoreReport:
    family: str
    status: str
    payload_rows: int
    imported: int = 0
    skipped: int = 0
    failed: int = 0
    unresolved: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "family": self.family,
            "status": self.status,
            "payload_rows": self.payload_rows,
            "imported": self.imported,
            "skipped": self.skipped,
            "failed": self.failed,
            "unresolved": self.unresolved,
        }


class AccountRestoreError(Exception):
    status_code = 400
    code = "account_restore_failed"
    validated = False

    def __init__(
        self,
        message: str,
        *,
        code: str | None = None,
        status_code: int | None = None,
        validated: bool | None = None,
        schema_version: str | None = None,
        export_kind: str | None = None,
        archive_includes_blob_coverage: bool = False,
        blob_coverage: dict[str, Any] | None = None,
        families: list[dict[str, Any]] | None = None,
        counts: dict[str, int] | None = None,
        notes: list[str] | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.code = code or self.code
        self.status_code = status_code or self.status_code
        self.validated = self.validated if validated is None else validated
        self.schema_version = schema_version
        self.export_kind = export_kind
        self.archive_includes_blob_coverage = archive_includes_blob_coverage
        self.blob_coverage = blob_coverage or _empty_blob_coverage()
        self.families = families or _empty_family_reports()
        self.counts = counts or _zero_counts()
        self.notes = list(notes or [])
        self.details = details or {}

    def to_payload(self) -> dict[str, Any]:
        notes = list(self.notes)
        if self.message and self.message not in notes:
            notes.append(self.message)
        return {
            "ok": False,
            "schema_version": self.schema_version,
            "export_kind": self.export_kind,
            "validated": self.validated,
            "metadata_restore_only": True,
            "blob_restore_supported": False,
            "archive_includes_blob_coverage": self.archive_includes_blob_coverage,
            "blob_coverage": self.blob_coverage or _empty_blob_coverage(),
            "families": self.families or _empty_family_reports(),
            "counts": self.counts or _zero_counts(),
            "notes": notes,
            "error": {
                "code": self.code,
                "message": self.message,
                "details": self.details,
            },
        }


class AccountRestoreValidationError(AccountRestoreError):
    status_code = 400
    code = "account_restore_validation_failed"
    validated = False


class AccountRestoreConflictError(AccountRestoreError):
    status_code = 409
    code = "account_restore_conflict"
    validated = True


class AccountRestoreService:
    def __init__(self, db: Any):
        self.db = db

    def restore_from_zip(self, archive_bytes: bytes, *, user_id: str) -> dict[str, Any]:
        parsed = self._parse_and_validate_archive(archive_bytes, user_id=user_id)
        families, counts = self._rehydrate(parsed)
        return self._build_success_report(parsed, families, counts)

    def _parse_and_validate_archive(
        self, archive_bytes: bytes, *, user_id: str
    ) -> ParsedArchive:
        try:
            with zipfile.ZipFile(io.BytesIO(archive_bytes), "r") as archive:
                archive_names = tuple(
                    info.filename for info in archive.infolist() if not info.is_dir()
                )
                duplicate_names = sorted(
                    name for name, count in Counter(archive_names).items() if count > 1
                )
                if duplicate_names:
                    raise self._validation_error(
                        "duplicate_entries",
                        "Archive contains duplicate file entries",
                        details={"duplicate_paths": duplicate_names},
                    )

                if "manifest.json" not in archive_names:
                    raise self._validation_error(
                        "manifest_missing",
                        "manifest.json is required for account restore",
                    )

                try:
                    manifest = json.loads(archive.read("manifest.json").decode("utf-8"))
                except Exception as exc:  # pragma: no cover - defensive decode guard
                    raise self._validation_error(
                        "manifest_invalid",
                        "manifest.json is not valid JSON",
                        details={"reason": str(exc)},
                    ) from exc

                if not isinstance(manifest, dict):
                    raise self._validation_error(
                        "manifest_invalid",
                        "manifest.json must decode to a JSON object",
                    )

                schema_version = str(manifest.get("schema_version") or "").strip()
                export_kind = str(manifest.get("export_kind") or "").strip()
                manifest_user_id = str(manifest.get("user_id") or "").strip()

                if not schema_version:
                    raise self._validation_error(
                        "manifest_invalid",
                        "manifest.json is missing schema_version",
                        manifest=manifest,
                    )
                if schema_version not in SUPPORTED_SCHEMA_VERSIONS:
                    raise self._validation_error(
                        "schema_version_unsupported",
                        f"Unsupported archive schema_version: {schema_version}",
                        manifest=manifest,
                    )
                if not export_kind:
                    raise self._validation_error(
                        "manifest_invalid",
                        "manifest.json is missing export_kind",
                        manifest=manifest,
                    )
                if export_kind != EXPORT_KIND:
                    raise self._validation_error(
                        "export_kind_invalid",
                        f"Unsupported export_kind: {export_kind}",
                        manifest=manifest,
                    )
                if not manifest_user_id:
                    raise self._validation_error(
                        "manifest_invalid",
                        "manifest.json is missing user_id",
                        manifest=manifest,
                    )
                if user_id and manifest_user_id != str(user_id):
                    raise self._validation_error(
                        "user_mismatch",
                        "Archive user_id does not match the authenticated user",
                        status_code=403,
                        manifest=manifest,
                        details={
                            "archive_user_id": manifest_user_id,
                            "authenticated_user_id": user_id,
                        },
                    )

                schema_payload_order = PAYLOAD_ORDER_BY_SCHEMA[schema_version]
                schema_payload_families = tuple(
                    entry[0] for entry in schema_payload_order
                )

                entity_counts = manifest.get("entity_counts")
                if not isinstance(entity_counts, dict):
                    raise self._validation_error(
                        "manifest_invalid",
                        "manifest.json is missing entity_counts",
                        manifest=manifest,
                    )

                included_families = manifest.get("included_families")
                if (
                    not isinstance(included_families, list)
                    or {str(item) for item in included_families}
                    != set(schema_payload_families)
                    or len(included_families) != len(schema_payload_families)
                ):
                    raise self._validation_error(
                        "manifest_invalid",
                        "manifest.json must enumerate the canonical payload families",
                        manifest=manifest,
                        details={"expected_families": list(schema_payload_families)},
                    )

                integrity = manifest.get("integrity")
                if not isinstance(integrity, dict):
                    raise self._validation_error(
                        "integrity_missing",
                        "manifest.json is missing integrity metadata",
                        manifest=manifest,
                    )

                if str(integrity.get("algorithm") or "").strip().lower() != "sha256":
                    raise self._validation_error(
                        "integrity_algorithm_unsupported",
                        "Only sha256 integrity digests are supported",
                        manifest=manifest,
                    )

                integrity_files = integrity.get("files")
                if not isinstance(integrity_files, dict):
                    raise self._validation_error(
                        "integrity_missing",
                        "manifest.json is missing integrity.files",
                        manifest=manifest,
                    )

                manifest_blob_coverage = manifest.get("blob_coverage")
                blob_coverage = (
                    dict(manifest_blob_coverage)
                    if isinstance(manifest_blob_coverage, dict)
                    else {}
                )
                blob_coverage.setdefault("validated_only", True)
                archive_includes_blob_coverage = bool(
                    blob_coverage.get("bundled_blob_paths")
                )

                unknown_files = sorted(
                    name
                    for name in archive_names
                    if name != "manifest.json" and name not in integrity_files
                )
                if unknown_files:
                    raise self._validation_error(
                        "unexpected_files",
                        "Archive contains files that are not declared in the manifest",
                        manifest=manifest,
                        details={"unexpected_paths": unknown_files},
                    )

                payload_rows: dict[str, list[dict[str, Any]]] = {}
                for family, path, _reader_name in schema_payload_order:
                    if path not in archive_names:
                        raise self._validation_error(
                            "payload_missing",
                            f"Archive is missing required payload file: {path}",
                            manifest=manifest,
                            details={"family": family, "path": path},
                        )

                    expected_digest = integrity_files.get(path)
                    if not isinstance(expected_digest, dict):
                        raise self._validation_error(
                            "integrity_missing",
                            f"Archive integrity metadata is missing for {path}",
                            manifest=manifest,
                            details={"path": path},
                        )

                    payload_bytes = archive.read(path)
                    self._validate_digest(
                        manifest=manifest,
                        path=path,
                        body=payload_bytes,
                        expected=expected_digest,
                    )

                    try:
                        rows = json.loads(payload_bytes.decode("utf-8"))
                    except Exception as exc:
                        raise self._validation_error(
                            "payload_invalid",
                            f"Payload file {path} is not valid JSON",
                            manifest=manifest,
                            details={"path": path, "reason": str(exc)},
                        ) from exc

                    if not isinstance(rows, list):
                        raise self._validation_error(
                            "payload_invalid",
                            f"Payload file {path} must contain a JSON array",
                            manifest=manifest,
                            details={"path": path},
                        )

                    normalized_rows: list[dict[str, Any]] = []
                    for index, row in enumerate(rows):
                        if not isinstance(row, dict):
                            raise self._validation_error(
                                "payload_invalid",
                                f"Payload file {path} contains a non-object row",
                                manifest=manifest,
                                details={"path": path, "row_index": index},
                            )
                        normalized_rows.append(dict(row))

                    declared_count = entity_counts.get(family)
                    if declared_count is None:
                        raise self._validation_error(
                            "manifest_invalid",
                            f"manifest.json is missing entity_counts[{family!r}]",
                            manifest=manifest,
                            details={"family": family},
                        )
                    if int(declared_count) != len(normalized_rows):
                        raise self._validation_error(
                            "payload_count_mismatch",
                            f"Entity count for {family} does not match the payload",
                            manifest=manifest,
                            details={
                                "family": family,
                                "declared": int(declared_count),
                                "actual": len(normalized_rows),
                            },
                        )
                    payload_rows[family] = normalized_rows

                for path, expected in integrity_files.items():
                    if path == "manifest.json":
                        continue
                    if path not in archive_names:
                        raise self._validation_error(
                            "integrity_missing",
                            f"Archive is missing integrity-covered file: {path}",
                            manifest=manifest,
                            details={"path": path},
                        )
                    self._validate_digest(
                        manifest=manifest,
                        path=path,
                        body=archive.read(path),
                        expected=expected,
                    )

                self._validate_relationships(
                    manifest=manifest,
                    payload_rows=payload_rows,
                    user_id=manifest_user_id,
                )

                return ParsedArchive(
                    manifest=manifest,
                    payload_rows=payload_rows,
                    archive_names=archive_names,
                    integrity_files=dict(integrity_files),
                    archive_includes_blob_coverage=archive_includes_blob_coverage,
                    blob_coverage=blob_coverage,
                    schema_version=schema_version,
                    export_kind=export_kind,
                    user_id=manifest_user_id,
                )
        except zipfile.BadZipFile as exc:
            raise self._validation_error(
                "invalid_zip",
                "Uploaded file is not a valid ZIP archive",
                details={"reason": str(exc)},
            ) from exc

    def _validate_digest(
        self,
        *,
        manifest: dict[str, Any],
        path: str,
        body: bytes,
        expected: dict[str, Any],
    ) -> None:
        sha256 = hashlib.sha256(body).hexdigest()
        size_bytes = len(body)
        expected_sha256 = str(expected.get("sha256") or "").strip().lower()
        expected_size = expected.get("size_bytes")
        if expected_sha256 != sha256 or int(expected_size) != size_bytes:
            raise self._validation_error(
                "integrity_mismatch",
                f"Integrity digest mismatch for {path}",
                manifest=manifest,
                details={
                    "path": path,
                    "expected_sha256": expected_sha256,
                    "actual_sha256": sha256,
                    "expected_size_bytes": expected_size,
                    "actual_size_bytes": size_bytes,
                },
            )

    def _validate_relationships(
        self,
        *,
        manifest: dict[str, Any],
        payload_rows: dict[str, list[dict[str, Any]]],
        user_id: str,
    ) -> None:
        projects = self._index_rows(payload_rows["projects"], "id", manifest)
        threads = self._index_rows(payload_rows["chat_threads"], "id", manifest)
        messages = self._index_rows(payload_rows["chat_messages"], "id", manifest)
        media_assets = self._index_rows(payload_rows["media_assets"], "id", manifest)
        media_aliases = self._index_rows(payload_rows["media_aliases"], "id", manifest)
        uploaded_documents = self._index_rows(
            payload_rows["uploaded_documents"], "id", manifest
        )
        generated_documents = self._index_rows(
            payload_rows["generated_documents"], "id", manifest
        )
        uploaded_images = self._index_rows(
            payload_rows["uploaded_images"], "id", manifest
        )
        generated_images = self._index_rows(
            payload_rows["generated_images"], "id", manifest
        )
        thread_documents = self._index_rows(
            payload_rows["thread_documents"], "id", manifest
        )
        project_document_links = self._index_rows(
            payload_rows["project_document_links"], "id", manifest
        )

        document_ids_uploaded = set(uploaded_documents)
        document_ids_generated = set(generated_documents)
        document_ids_all = document_ids_uploaded | document_ids_generated
        if document_ids_uploaded & document_ids_generated:
            raise self._validation_error(
                "document_id_ambiguity",
                "Uploaded and generated documents must not share archive IDs",
                manifest=manifest,
                details={
                    "colliding_document_ids": sorted(
                        document_ids_uploaded & document_ids_generated
                    )
                },
            )

        for row in payload_rows["projects"]:
            project_id = row.get("id")
            if project_id is None:
                raise self._validation_error(
                    "payload_invalid",
                    "projects rows require an id",
                    manifest=manifest,
                )
            identity_depth = str(row.get("identity_depth") or "light").strip()
            if identity_depth not in {"light", "deep"}:
                raise self._validation_error(
                    "payload_invalid",
                    "projects.identity_depth must be light or deep",
                    manifest=manifest,
                    details={"project_id": project_id},
                )

        for row in payload_rows["chat_threads"]:
            thread_id = row.get("id")
            if thread_id is None:
                raise self._validation_error(
                    "payload_invalid",
                    "chat_threads rows require an id",
                    manifest=manifest,
                )
            project_id = row.get("project_id")
            if project_id is not None and project_id not in projects:
                raise self._validation_error(
                    "relationship_missing",
                    "chat_threads.project_id does not reference a restored project",
                    manifest=manifest,
                    details={"thread_id": thread_id, "project_id": project_id},
                )
            parent_id = row.get("parent_id")
            if parent_id is not None and parent_id not in threads:
                raise self._validation_error(
                    "relationship_missing",
                    "chat_threads.parent_id does not reference a restored thread",
                    manifest=manifest,
                    details={"thread_id": thread_id, "parent_id": parent_id},
                )

        thread_ids = set(threads)
        for row in payload_rows["chat_messages"]:
            message_id = row.get("id")
            thread_id = row.get("thread_id")
            if message_id is None or thread_id is None:
                raise self._validation_error(
                    "payload_invalid",
                    "chat_messages rows require id and thread_id",
                    manifest=manifest,
                )
            if thread_id not in thread_ids:
                raise self._validation_error(
                    "relationship_missing",
                    "chat_messages.thread_id does not reference a restored thread",
                    manifest=manifest,
                    details={"message_id": message_id, "thread_id": thread_id},
                )

        for row in payload_rows["media_assets"]:
            asset_id = row.get("id")
            project_id = row.get("project_id")
            thread_id = row.get("thread_id")
            if asset_id is None or project_id is None:
                raise self._validation_error(
                    "payload_invalid",
                    "media_assets rows require id and project_id",
                    manifest=manifest,
                )
            kind = str(row.get("media_kind") or "").strip()
            provenance = str(row.get("provenance") or "").strip()
            if kind not in {"document", "image", "audio", "video", "other"}:
                raise self._validation_error(
                    "payload_invalid",
                    "media_assets.media_kind is invalid",
                    manifest=manifest,
                    details={"asset_id": asset_id, "media_kind": kind},
                )
            if provenance not in {
                "uploaded",
                "generated",
                "imported",
                "system",
            }:
                raise self._validation_error(
                    "payload_invalid",
                    "media_assets.provenance is invalid",
                    manifest=manifest,
                    details={"asset_id": asset_id, "provenance": provenance},
                )
            if project_id not in projects:
                raise self._validation_error(
                    "relationship_missing",
                    "media_assets.project_id does not reference a restored project",
                    manifest=manifest,
                    details={"asset_id": asset_id, "project_id": project_id},
                )
            if thread_id is not None and thread_id not in thread_ids:
                raise self._validation_error(
                    "relationship_missing",
                    "media_assets.thread_id does not reference a restored thread",
                    manifest=manifest,
                    details={"asset_id": asset_id, "thread_id": thread_id},
                )

        asset_ids = set(media_assets)
        for row in payload_rows["media_aliases"]:
            alias_id = row.get("id")
            asset_id = row.get("asset_id")
            alias_type = str(row.get("alias_type") or "").strip()
            if alias_id is None or asset_id is None:
                raise self._validation_error(
                    "payload_invalid",
                    "media_aliases rows require id and asset_id",
                    manifest=manifest,
                )
            if not row.get("alias"):
                raise self._validation_error(
                    "payload_invalid",
                    "media_aliases rows require alias text",
                    manifest=manifest,
                    details={"alias_id": alias_id},
                )
            if alias_type not in {
                "original_name",
                "prompt",
                "user_alias",
                "system_generated",
            }:
                raise self._validation_error(
                    "payload_invalid",
                    "media_aliases.alias_type is invalid",
                    manifest=manifest,
                    details={"alias_id": alias_id, "alias_type": alias_type},
                )
            if asset_id not in asset_ids:
                raise self._validation_error(
                    "relationship_missing",
                    "media_aliases.asset_id does not reference a restored media asset",
                    manifest=manifest,
                    details={"alias_id": alias_id, "asset_id": asset_id},
                )

        for row in payload_rows["uploaded_documents"]:
            document_id = row.get("id")
            project_id = row.get("project_id")
            thread_id = row.get("thread_id")
            asset_id = row.get("asset_id")
            embedding_status = str(row.get("embedding_status") or "").strip()
            if document_id is None or row.get("filename") is None:
                raise self._validation_error(
                    "payload_invalid",
                    "uploaded_documents rows require id and filename",
                    manifest=manifest,
                )
            if embedding_status not in {
                "pending",
                "processing",
                "ready",
                "failed",
            }:
                raise self._validation_error(
                    "payload_invalid",
                    "uploaded_documents.embedding_status is invalid",
                    manifest=manifest,
                    details={
                        "document_id": document_id,
                        "embedding_status": embedding_status,
                    },
                )
            if project_id is not None and project_id not in projects:
                raise self._validation_error(
                    "relationship_missing",
                    "uploaded_documents.project_id does not reference a restored project",
                    manifest=manifest,
                    details={
                        "document_id": document_id,
                        "project_id": project_id,
                    },
                )
            if thread_id is not None and thread_id not in thread_ids:
                raise self._validation_error(
                    "relationship_missing",
                    "uploaded_documents.thread_id does not reference a restored thread",
                    manifest=manifest,
                    details={
                        "document_id": document_id,
                        "thread_id": thread_id,
                    },
                )
            if asset_id is not None and asset_id not in asset_ids:
                raise self._validation_error(
                    "relationship_missing",
                    "uploaded_documents.asset_id does not reference a restored media asset",
                    manifest=manifest,
                    details={"document_id": document_id, "asset_id": asset_id},
                )

        for row in payload_rows["generated_documents"]:
            document_id = row.get("id")
            project_id = row.get("project_id")
            thread_id = row.get("thread_id")
            document_format = str(row.get("format") or "").strip().lower()
            if document_id is None:
                raise self._validation_error(
                    "payload_invalid",
                    "generated_documents rows require id",
                    manifest=manifest,
                )
            if project_id is None:
                raise self._validation_error(
                    "payload_invalid",
                    "generated_documents rows require project_id",
                    manifest=manifest,
                    details={"document_id": document_id},
                )
            if not row.get("title"):
                raise self._validation_error(
                    "payload_invalid",
                    "generated_documents rows require title",
                    manifest=manifest,
                    details={"document_id": document_id},
                )
            if document_format not in {
                "txt",
                "md",
                "docx",
                "pdf",
                "html",
                "json",
            }:
                raise self._validation_error(
                    "payload_invalid",
                    "generated_documents.format is invalid",
                    manifest=manifest,
                    details={
                        "document_id": document_id,
                        "format": document_format,
                    },
                )
            if project_id is not None and project_id not in projects:
                raise self._validation_error(
                    "relationship_missing",
                    "generated_documents.project_id does not reference a restored project",
                    manifest=manifest,
                    details={
                        "document_id": document_id,
                        "project_id": project_id,
                    },
                )
            if thread_id is not None and thread_id not in thread_ids:
                raise self._validation_error(
                    "relationship_missing",
                    "generated_documents.thread_id does not reference a restored thread",
                    manifest=manifest,
                    details={
                        "document_id": document_id,
                        "thread_id": thread_id,
                    },
                )

        for row in payload_rows["uploaded_images"]:
            image_id = row.get("id")
            project_id = row.get("project_id")
            thread_id = row.get("thread_id")
            asset_id = row.get("asset_id")
            if image_id is None or row.get("filename") is None:
                raise self._validation_error(
                    "payload_invalid",
                    "uploaded_images rows require id and filename",
                    manifest=manifest,
                )
            if project_id is None:
                raise self._validation_error(
                    "payload_invalid",
                    "uploaded_images rows require project_id",
                    manifest=manifest,
                    details={"image_id": image_id},
                )
            if thread_id is None:
                raise self._validation_error(
                    "payload_invalid",
                    "uploaded_images rows require thread_id",
                    manifest=manifest,
                    details={"image_id": image_id},
                )
            if project_id not in projects:
                raise self._validation_error(
                    "relationship_missing",
                    "uploaded_images.project_id does not reference a restored project",
                    manifest=manifest,
                    details={"image_id": image_id, "project_id": project_id},
                )
            if thread_id not in thread_ids:
                raise self._validation_error(
                    "relationship_missing",
                    "uploaded_images.thread_id does not reference a restored thread",
                    manifest=manifest,
                    details={"image_id": image_id, "thread_id": thread_id},
                )
            if asset_id is not None and asset_id not in asset_ids:
                raise self._validation_error(
                    "relationship_missing",
                    "uploaded_images.asset_id does not reference a restored media asset",
                    manifest=manifest,
                    details={"image_id": image_id, "asset_id": asset_id},
                )

        for row in payload_rows["generated_images"]:
            image_id = row.get("id")
            project_id = row.get("project_id")
            thread_id = row.get("thread_id")
            asset_id = row.get("asset_id")
            if image_id is None:
                raise self._validation_error(
                    "payload_invalid",
                    "generated_images rows require id",
                    manifest=manifest,
                )
            if project_id is None:
                raise self._validation_error(
                    "payload_invalid",
                    "generated_images rows require project_id",
                    manifest=manifest,
                    details={"image_id": image_id},
                )
            if thread_id is None:
                raise self._validation_error(
                    "payload_invalid",
                    "generated_images rows require thread_id",
                    manifest=manifest,
                    details={"image_id": image_id},
                )
            if project_id not in projects:
                raise self._validation_error(
                    "relationship_missing",
                    "generated_images.project_id does not reference a restored project",
                    manifest=manifest,
                    details={"image_id": image_id, "project_id": project_id},
                )
            if thread_id not in thread_ids:
                raise self._validation_error(
                    "relationship_missing",
                    "generated_images.thread_id does not reference a restored thread",
                    manifest=manifest,
                    details={"image_id": image_id, "thread_id": thread_id},
                )
            if asset_id is not None and asset_id not in asset_ids:
                raise self._validation_error(
                    "relationship_missing",
                    "generated_images.asset_id does not reference a restored media asset",
                    manifest=manifest,
                    details={"image_id": image_id, "asset_id": asset_id},
                )

        for row in payload_rows["thread_documents"]:
            link_id = row.get("id")
            thread_id = row.get("thread_id")
            document_id = row.get("document_id")
            relation = str(row.get("relation") or "").strip()
            if link_id is None or thread_id is None or document_id is None:
                raise self._validation_error(
                    "payload_invalid",
                    "thread_documents rows require id, thread_id, and document_id",
                    manifest=manifest,
                )
            if thread_id not in thread_ids:
                raise self._validation_error(
                    "relationship_missing",
                    "thread_documents.thread_id does not reference a restored thread",
                    manifest=manifest,
                    details={"link_id": link_id, "thread_id": thread_id},
                )
            if relation not in {"autosave", "attached", "reference"}:
                raise self._validation_error(
                    "payload_invalid",
                    "thread_documents.relation is invalid",
                    manifest=manifest,
                    details={"link_id": link_id, "relation": relation},
                )
            if document_id not in document_ids_all:
                raise self._validation_error(
                    "relationship_missing",
                    "thread_documents.document_id does not reference a restored document",
                    manifest=manifest,
                    details={"link_id": link_id, "document_id": document_id},
                )

        for row in payload_rows["project_document_links"]:
            link_id = row.get("id")
            project_id = row.get("project_id")
            document_id = row.get("document_id")
            document_type = str(row.get("document_type") or "").strip()
            if link_id is None or project_id is None or document_id is None:
                raise self._validation_error(
                    "payload_invalid",
                    "project_document_links rows require id, project_id, and document_id",
                    manifest=manifest,
                )
            if project_id not in projects:
                raise self._validation_error(
                    "relationship_missing",
                    "project_document_links.project_id does not reference a restored project",
                    manifest=manifest,
                    details={"link_id": link_id, "project_id": project_id},
                )
            if document_type not in {"uploaded", "generated"}:
                raise self._validation_error(
                    "payload_invalid",
                    "project_document_links.document_type is invalid",
                    manifest=manifest,
                    details={
                        "link_id": link_id,
                        "document_type": document_type,
                    },
                )
            if document_type == "uploaded" and document_id not in document_ids_uploaded:
                raise self._validation_error(
                    "relationship_missing",
                    "project_document_links.document_id does not match an uploaded document",
                    manifest=manifest,
                    details={"link_id": link_id, "document_id": document_id},
                )
            if (
                document_type == "generated"
                and document_id not in document_ids_generated
            ):
                raise self._validation_error(
                    "relationship_missing",
                    "project_document_links.document_id does not match a generated document",
                    manifest=manifest,
                    details={"link_id": link_id, "document_id": document_id},
                )

        proposal_rows = self._index_rows(
            payload_rows["extension_proposals"], "proposal_id", manifest
        )
        decision_rows = self._index_rows(
            payload_rows["extension_install_gate_decisions"],
            "decision_id",
            manifest,
        )
        registry_rows = self._index_rows(
            payload_rows["extension_registry_entries"],
            "registry_id",
            manifest,
        )
        binding_rows = self._index_rows(
            payload_rows["extension_install_bindings"],
            "binding_id",
            manifest,
        )
        for row in payload_rows["extension_proposals"]:
            proposal_id = row.get("proposal_id")
            account_id = str(row.get("account_id") or "").strip()
            if not proposal_id or not account_id:
                raise self._validation_error(
                    "payload_invalid",
                    "extension_proposals rows require proposal_id and account_id",
                    manifest=manifest,
                    details={"proposal_id": proposal_id},
                )
            if account_id != user_id:
                raise self._validation_error(
                    "user_mismatch",
                    "extension_proposals.account_id does not match the archive user",
                    status_code=403,
                    manifest=manifest,
                    details={
                        "proposal_id": proposal_id,
                        "archive_user_id": user_id,
                        "row_account_id": account_id,
                    },
                )

        for row in payload_rows["extension_install_gate_decisions"]:
            decision_id = row.get("decision_id")
            proposal_id = row.get("proposal_id")
            account_id = str(row.get("account_id") or "").strip()
            decision_token = str(row.get("decision_token") or "").strip()
            if not decision_id or not proposal_id or not account_id:
                raise self._validation_error(
                    "payload_invalid",
                    "extension_install_gate_decisions rows require decision_id, proposal_id, and account_id",
                    manifest=manifest,
                    details={"decision_id": decision_id},
                )
            if account_id != user_id:
                raise self._validation_error(
                    "user_mismatch",
                    "extension_install_gate_decisions.account_id does not match the archive user",
                    status_code=403,
                    manifest=manifest,
                    details={
                        "decision_id": decision_id,
                        "archive_user_id": user_id,
                        "row_account_id": account_id,
                    },
                )
            if decision_token not in {
                InstallGateDecisionToken.APPROVED.value,
                InstallGateDecisionToken.REJECTED.value,
            }:
                raise self._validation_error(
                    "payload_invalid",
                    "extension_install_gate_decisions.decision_token is invalid",
                    manifest=manifest,
                    details={
                        "decision_id": decision_id,
                        "decision_token": decision_token,
                    },
                )
            if proposal_id not in proposal_rows:
                raise self._validation_error(
                    "relationship_missing",
                    "extension_install_gate_decisions.proposal_id does not reference a restored proposal",
                    manifest=manifest,
                    details={
                        "decision_id": decision_id,
                        "proposal_id": proposal_id,
                    },
                )
            requested_permissions = row.get("requested_permissions_json")
            approved_permissions = row.get("approved_permissions_json")
            if not isinstance(requested_permissions, list) or not isinstance(
                approved_permissions, list
            ):
                raise self._validation_error(
                    "payload_invalid",
                    "extension_install_gate_decisions permission snapshots must be arrays",
                    manifest=manifest,
                    details={"decision_id": decision_id},
                )

        for row in payload_rows["extension_registry_entries"]:
            registry_id = row.get("registry_id")
            proposal_id = row.get("proposal_id")
            decision_id = row.get("decision_id")
            account_id = str(row.get("account_id") or "").strip()
            status_token = str(row.get("status_token") or "").strip()
            target_surface = str(row.get("target_surface_token") or "").strip()
            scope_token = str(row.get("scope_token") or "").strip()
            manifest_snapshot = row.get("manifest_snapshot_json")
            requested_permissions = row.get("requested_permissions_json")
            approved_permissions = row.get("approved_permissions_json")
            registration_metadata = row.get("registration_metadata_json")
            provenance_json = row.get("provenance_json")
            provenance_class = str(row.get("provenance_class_token") or "").strip()
            if not registry_id or not proposal_id or not decision_id or not account_id:
                raise self._validation_error(
                    "payload_invalid",
                    "extension_registry_entries rows require registry_id, proposal_id, decision_id, and account_id",
                    manifest=manifest,
                    details={"registry_id": registry_id},
                )
            if account_id != user_id:
                raise self._validation_error(
                    "user_mismatch",
                    "extension_registry_entries.account_id does not match the archive user",
                    status_code=403,
                    manifest=manifest,
                    details={
                        "registry_id": registry_id,
                        "archive_user_id": user_id,
                        "row_account_id": account_id,
                    },
                )
            if status_token not in {
                CapabilityRegistryStatus.REGISTERED.value,
                CapabilityRegistryStatus.SUSPENDED.value,
                CapabilityRegistryStatus.RETIRED.value,
                CapabilityRegistryStatus.ARCHIVED.value,
            }:
                raise self._validation_error(
                    "payload_invalid",
                    "extension_registry_entries.status_token is invalid",
                    manifest=manifest,
                    details={
                        "registry_id": registry_id,
                        "status_token": status_token,
                    },
                )
            if provenance_class not in {
                CapabilityEntryProvenanceClass.PROPOSAL_APPROVAL.value,
            }:
                raise self._validation_error(
                    "payload_invalid",
                    "extension_registry_entries.provenance_class_token is invalid",
                    manifest=manifest,
                    details={
                        "registry_id": registry_id,
                        "provenance_class_token": provenance_class,
                    },
                )
            if proposal_id not in proposal_rows:
                raise self._validation_error(
                    "relationship_missing",
                    "extension_registry_entries.proposal_id does not reference a restored proposal",
                    manifest=manifest,
                    details={
                        "registry_id": registry_id,
                        "proposal_id": proposal_id,
                    },
                )
            if decision_id not in decision_rows:
                raise self._validation_error(
                    "relationship_missing",
                    "extension_registry_entries.decision_id does not reference a restored decision",
                    manifest=manifest,
                    details={
                        "registry_id": registry_id,
                        "decision_id": decision_id,
                    },
                )
            if decision_rows[decision_id].get("proposal_id") != proposal_id:
                raise self._validation_error(
                    "relationship_missing",
                    "extension_registry_entries.decision_id does not match the proposed extension",
                    manifest=manifest,
                    details={
                        "registry_id": registry_id,
                        "decision_id": decision_id,
                        "proposal_id": proposal_id,
                    },
                )
            if manifest_snapshot is None or not isinstance(manifest_snapshot, dict):
                raise self._validation_error(
                    "payload_invalid",
                    "extension_registry_entries.manifest_snapshot_json must be an object",
                    manifest=manifest,
                    details={"registry_id": registry_id},
                )
            if not isinstance(requested_permissions, list) or not isinstance(
                approved_permissions, list
            ):
                raise self._validation_error(
                    "payload_invalid",
                    "extension_registry_entries permission snapshots must be arrays",
                    manifest=manifest,
                    details={"registry_id": registry_id},
                )
            if not isinstance(registration_metadata, dict) or not isinstance(
                provenance_json, dict
            ):
                raise self._validation_error(
                    "payload_invalid",
                    "extension_registry_entries metadata payloads must be objects",
                    manifest=manifest,
                    details={"registry_id": registry_id},
                )
            if not target_surface or not scope_token:
                raise self._validation_error(
                    "payload_invalid",
                    "extension_registry_entries require target_surface_token and scope_token",
                    manifest=manifest,
                    details={"registry_id": registry_id},
                )

        for row in binding_rows.values():
            binding_id = row.get("binding_id")
            registry_id = row.get("registry_entry_id")
            proposal_id = row.get("proposal_id")
            account_id = str(row.get("account_id") or "").strip()
            scope_token = str(row.get("scope_token") or "").strip()
            status_token = str(row.get("binding_status_token") or "").strip()
            project_id = row.get("project_id")
            profile_id = row.get("profile_id")
            account_scope_target_id = row.get("account_scope_target_id")
            bind_notes = row.get("bind_notes_json")
            bind_metadata = row.get("bind_metadata_json")
            unbind_metadata = row.get("unbind_metadata_json")
            if not binding_id or not registry_id or not proposal_id or not account_id:
                raise self._validation_error(
                    "payload_invalid",
                    "extension_install_bindings rows require binding_id, registry_entry_id, proposal_id, and account_id",
                    manifest=manifest,
                    details={"binding_id": binding_id},
                )
            if account_id != user_id:
                raise self._validation_error(
                    "user_mismatch",
                    "extension_install_bindings.account_id does not match the archive user",
                    status_code=403,
                    manifest=manifest,
                    details={
                        "binding_id": binding_id,
                        "archive_user_id": user_id,
                        "row_account_id": account_id,
                    },
                )
            if registry_id not in registry_rows:
                raise self._validation_error(
                    "relationship_missing",
                    "extension_install_bindings.registry_entry_id does not reference a restored registry entry",
                    manifest=manifest,
                    details={
                        "binding_id": binding_id,
                        "registry_entry_id": registry_id,
                    },
                )
            if proposal_id not in proposal_rows:
                raise self._validation_error(
                    "relationship_missing",
                    "extension_install_bindings.proposal_id does not reference a restored proposal",
                    manifest=manifest,
                    details={
                        "binding_id": binding_id,
                        "proposal_id": proposal_id,
                    },
                )
            if registry_rows[registry_id].get("proposal_id") != proposal_id:
                raise self._validation_error(
                    "relationship_missing",
                    "extension_install_bindings.registry_entry_id does not match the originating proposal",
                    manifest=manifest,
                    details={
                        "binding_id": binding_id,
                        "registry_entry_id": registry_id,
                        "proposal_id": proposal_id,
                    },
                )
            if scope_token not in EXTENSION_INSTALL_BINDING_SCOPES:
                raise self._validation_error(
                    "payload_invalid",
                    "extension_install_bindings.scope_token is invalid",
                    manifest=manifest,
                    details={
                        "binding_id": binding_id,
                        "scope_token": scope_token,
                    },
                )
            if status_token not in EXTENSION_INSTALL_BINDING_STATUSES:
                raise self._validation_error(
                    "payload_invalid",
                    "extension_install_bindings.binding_status_token is invalid",
                    manifest=manifest,
                    details={
                        "binding_id": binding_id,
                        "binding_status_token": status_token,
                    },
                )
            if (
                status_token == ExtensionInstallBindingStatus.UNBOUND.value
                and row.get("unbound_at") is None
            ):
                raise self._validation_error(
                    "payload_invalid",
                    "unbound extension_install_bindings rows require unbound_at",
                    manifest=manifest,
                    details={"binding_id": binding_id},
                )
            if scope_token == ExtensionInstallBindingScope.PROJECT.value:
                if (
                    project_id is None
                    or profile_id is not None
                    or account_scope_target_id is not None
                ):
                    raise self._validation_error(
                        "payload_invalid",
                        "project-scoped bindings require project_id and must not carry profile or account scope targets",
                        manifest=manifest,
                        details={"binding_id": binding_id},
                    )
            elif scope_token == ExtensionInstallBindingScope.PROFILE.value:
                if (
                    profile_id is None
                    or project_id is not None
                    or account_scope_target_id is not None
                ):
                    raise self._validation_error(
                        "payload_invalid",
                        "profile-scoped bindings require profile_id and must not carry project or account scope targets",
                        manifest=manifest,
                        details={"binding_id": binding_id},
                    )
            elif scope_token == ExtensionInstallBindingScope.ACCOUNT.value:
                if (
                    account_scope_target_id is None
                    or project_id is not None
                    or profile_id is not None
                ):
                    raise self._validation_error(
                        "payload_invalid",
                        "account-scoped bindings require account_scope_target_id and must not carry project or profile targets",
                        manifest=manifest,
                        details={"binding_id": binding_id},
                    )
            if not isinstance(bind_notes, dict):
                raise self._validation_error(
                    "payload_invalid",
                    "extension_install_bindings.bind_notes_json must be an object",
                    manifest=manifest,
                    details={"binding_id": binding_id},
                )
            if not isinstance(bind_metadata, dict):
                raise self._validation_error(
                    "payload_invalid",
                    "extension_install_bindings.bind_metadata_json must be an object",
                    manifest=manifest,
                    details={"binding_id": binding_id},
                )
            if not isinstance(unbind_metadata, dict):
                raise self._validation_error(
                    "payload_invalid",
                    "extension_install_bindings.unbind_metadata_json must be an object",
                    manifest=manifest,
                    details={"binding_id": binding_id},
                )
            source_thread_id = row.get("source_thread_id")
            source_message_id = row.get("source_message_id")
            if source_thread_id is None or source_message_id is None:
                raise self._validation_error(
                    "payload_invalid",
                    "extension_install_bindings require source_thread_id and source_message_id lineage snapshots",
                    manifest=manifest,
                    details={"binding_id": binding_id},
                )
            if registry_rows[registry_id].get("source_thread_id") != source_thread_id:
                raise self._validation_error(
                    "relationship_missing",
                    "extension_install_bindings.source_thread_id does not match the registry entry lineage",
                    manifest=manifest,
                    details={"binding_id": binding_id},
                )
            if registry_rows[registry_id].get("source_message_id") != source_message_id:
                raise self._validation_error(
                    "relationship_missing",
                    "extension_install_bindings.source_message_id does not match the registry entry lineage",
                    manifest=manifest,
                    details={"binding_id": binding_id},
                )

        if "persona_profiles" in payload_rows:
            self._validate_persona_profiles(
                manifest=manifest,
                payload_rows=payload_rows,
                user_id=user_id,
            )
        payload_rows["chat_threads"] = self._prepare_thread_profile_pins(
            manifest=manifest, payload_rows=payload_rows, user_id=user_id
        )

    def _prepare_thread_profile_pins(
        self,
        *,
        manifest: dict[str, Any],
        payload_rows: dict[str, list[dict[str, Any]]],
        user_id: str,
    ) -> list[dict[str, Any]]:
        """Validate pins before writes; normalize historical archive omissions.

        Derivation consults only this validated archive, never the receiving
        database's current profiles. Explicit NULL remains revisionless.
        """
        profiles = {row["id"]: row for row in payload_rows.get("persona_profiles", [])}
        bindings = {
            row["profile_id"]: row
            for row in payload_rows.get("persona_profile_bindings", [])
        }
        revision_keys = {
            (row["profile_id"], row["revision"])
            for row in payload_rows.get("persona_profile_revisions", [])
        }
        normalized = []
        for original in payload_rows["chat_threads"]:
            row = dict(original)
            profile_id = row.get("active_profile_id")
            if profile_id is not None and not isinstance(profile_id, str):
                raise self._validation_error(
                    "payload_invalid",
                    "Thread active_profile_id must be a string or null",
                    manifest=manifest,
                    details={"thread_id": row.get("id")},
                )
            if manifest.get("schema_version") != MANIFEST_SCHEMA_VERSION:
                row["active_profile_revision"] = None
            elif "active_profile_revision" not in row:
                row["active_profile_revision"] = None
                metadata = row.get("metadata") or {}
                overrides = (
                    metadata.get("profile_overrides")
                    if isinstance(metadata, dict)
                    else None
                )
                if (
                    profile_id in profiles
                    and bindings.get(profile_id, {}).get("owner_account_id") == user_id
                    and row.get("user_id") == user_id
                    and not (isinstance(overrides, dict) and profile_id in overrides)
                ):
                    current = profiles[profile_id]["current_revision"]
                    if (profile_id, current) in revision_keys:
                        row["active_profile_revision"] = current
            revision = row.get("active_profile_revision")
            if revision is not None and (
                type(revision) is not int
                or revision <= 0
                or row.get("user_id") != user_id
                or bindings.get(profile_id, {}).get("owner_account_id") != user_id
                or (profile_id, revision) not in revision_keys
            ):
                raise self._validation_error(
                    "persona_thread_revision_unavailable",
                    "Thread Persona Profile revision is unavailable in this account archive",
                    manifest=manifest,
                    details={"thread_id": row.get("id")},
                )
            normalized.append(row)
        return normalized

    def _validate_persona_profiles(
        self,
        *,
        manifest: dict[str, Any],
        payload_rows: dict[str, list[dict[str, Any]]],
        user_id: str,
    ) -> None:
        profiles = self._index_rows(payload_rows["persona_profiles"], "id", manifest)
        bindings = self._index_rows(
            payload_rows["persona_profile_bindings"],
            "profile_id",
            manifest,
        )
        revision_keys: set[tuple[str, int]] = set()

        for profile_id, row in profiles.items():
            try:
                current_revision = int(row.get("current_revision"))
            except (TypeError, ValueError) as exc:
                raise self._validation_error(
                    "payload_invalid",
                    "persona_profiles.current_revision must be a positive integer",
                    manifest=manifest,
                    details={"profile_id": profile_id},
                ) from exc
            if current_revision <= 0 or any(
                row.get(field) is None for field in ("created_at", "updated_at")
            ):
                raise self._validation_error(
                    "payload_invalid",
                    "persona_profiles rows require a positive current_revision and timestamps",
                    manifest=manifest,
                    details={"profile_id": profile_id},
                )

        for row in payload_rows["persona_profile_revisions"]:
            profile_id = str(row.get("profile_id") or "").strip()
            try:
                revision_number = int(row.get("revision"))
                persona_manifest = PersonaProfileManifest.model_validate(
                    row.get("manifest_json")
                )
            except Exception as exc:
                raise self._validation_error(
                    "persona_manifest_invalid",
                    "Persona Profile revision contains an invalid canonical manifest",
                    manifest=manifest,
                    details={"profile_id": profile_id},
                ) from exc
            key = (profile_id, revision_number)
            if key in revision_keys:
                raise self._validation_error(
                    "duplicate_ids",
                    "Archive contains duplicate Persona Profile revisions",
                    manifest=manifest,
                    details={"profile_id": profile_id, "revision": revision_number},
                )
            if profile_id not in profiles:
                raise self._validation_error(
                    "relationship_missing",
                    "Persona Profile revision does not reference an exported profile",
                    manifest=manifest,
                    details={"profile_id": profile_id, "revision": revision_number},
                )
            if (
                revision_number <= 0
                or persona_manifest.profile_identity != profile_id
                or persona_manifest.revision != revision_number
                or persona_manifest.api_version
                != str(row.get("api_version") or "").strip()
                or row.get("created_at") is None
            ):
                raise self._validation_error(
                    "persona_revision_mismatch",
                    "Persona Profile revision metadata does not match its manifest",
                    manifest=manifest,
                    details={"profile_id": profile_id, "revision": revision_number},
                )
            revision_keys.add(key)

        if set(bindings) != set(profiles):
            raise self._validation_error(
                "persona_binding_mismatch",
                "Every exported Persona Profile must have exactly one account binding",
                manifest=manifest,
            )
        for profile_id, row in bindings.items():
            owner_account_id = str(row.get("owner_account_id") or "").strip()
            if owner_account_id != user_id:
                raise self._validation_error(
                    "user_mismatch",
                    "Persona Profile binding owner does not match the archive user",
                    status_code=403,
                    manifest=manifest,
                    details={
                        "profile_id": profile_id,
                        "archive_user_id": user_id,
                        "row_account_id": owner_account_id,
                    },
                )
            if any(row.get(field) is None for field in ("created_at", "updated_at")):
                raise self._validation_error(
                    "payload_invalid",
                    "persona_profile_bindings rows require timestamps",
                    manifest=manifest,
                    details={"profile_id": profile_id},
                )

        for profile_id, row in profiles.items():
            if (profile_id, int(row["current_revision"])) not in revision_keys:
                raise self._validation_error(
                    "persona_current_revision_missing",
                    "Persona Profile current_revision is absent from immutable history",
                    manifest=manifest,
                    details={
                        "profile_id": profile_id,
                        "current_revision": row["current_revision"],
                    },
                )

    def _index_rows(
        self,
        rows: list[dict[str, Any]],
        key_name: str,
        manifest: dict[str, Any],
    ) -> dict[Any, dict[str, Any]]:
        indexed: dict[Any, dict[str, Any]] = {}
        for index, row in enumerate(rows):
            key = row.get(key_name)
            if key is None:
                raise self._validation_error(
                    "payload_invalid",
                    f"{manifest.get('export_kind')} payload row is missing {key_name}",
                    manifest=manifest,
                    details={"row_index": index, "key_name": key_name},
                )
            if key in indexed:
                raise self._validation_error(
                    "duplicate_ids",
                    "Archive contains duplicate row IDs",
                    manifest=manifest,
                    details={"key_name": key_name, "duplicate_id": key},
                )
            indexed[key] = row
        return indexed

    def _rehydrate(
        self, parsed: ParsedArchive
    ) -> tuple[list[dict[str, Any]], dict[str, int]]:
        counts = _zero_counts()
        family_reports: list[FamilyRestoreReport] = []
        unresolved_rows: list[dict[str, Any]] = []
        if isinstance(parsed.blob_coverage, dict):
            maybe_rows = parsed.blob_coverage.get("unresolved_rows") or []
            if isinstance(maybe_rows, list):
                unresolved_rows = [row for row in maybe_rows if isinstance(row, dict)]
        unresolved_by_family = Counter(
            family
            for family in (
                str(row.get("family") or "").strip() for row in unresolved_rows
            )
            if family
        )

        def _call_restore(
            method_name: str,
            rows: list[dict[str, Any]],
            conn: Any | None,
            **kwargs: Any,
        ) -> dict[str, Any]:
            helper = getattr(self.db, method_name, None)
            if not callable(helper):
                raise AccountRestoreError(
                    f"Restore helper {method_name} is not available on {type(self.db).__name__}",
                    code="restore_helper_missing",
                    status_code=500,
                    validated=True,
                    schema_version=parsed.schema_version,
                    export_kind=parsed.export_kind,
                    archive_includes_blob_coverage=parsed.archive_includes_blob_coverage,
                    blob_coverage=parsed.blob_coverage,
                    families=[report.to_dict() for report in family_reports],
                    counts=dict(counts),
                    notes=[
                        "Archive validation succeeded before restore began.",
                    ],
                )
            if conn is None:
                result = helper(rows, **kwargs)
            else:
                result = helper(rows, conn=conn, **kwargs)
            if not isinstance(result, dict):
                raise AccountRestoreError(
                    f"Restore helper {method_name} must return a mapping of counts",
                    code="restore_helper_invalid",
                    status_code=500,
                    validated=True,
                    schema_version=parsed.schema_version,
                    export_kind=parsed.export_kind,
                    archive_includes_blob_coverage=parsed.archive_includes_blob_coverage,
                    blob_coverage=parsed.blob_coverage,
                    families=[report.to_dict() for report in family_reports],
                    counts=dict(counts),
                )
            return result

        def _record_family(
            family: str, rows: list[dict[str, Any]], result: dict[str, Any]
        ) -> None:
            imported = int(result.get("imported") or 0)
            skipped = int(result.get("skipped") or 0)
            failed = int(result.get("failed") or 0)
            unresolved = int(result.get("unresolved") or 0)
            unresolved += int(unresolved_by_family.get(family, 0))
            payload_rows = len(rows)
            if failed:
                status = "failed"
            elif unresolved:
                status = "unresolved"
            elif payload_rows == 0:
                status = "empty"
            elif imported and skipped:
                status = "partial"
            elif imported:
                status = "imported"
            elif skipped:
                status = "already_present"
            else:
                status = "empty"
            family_report = FamilyRestoreReport(
                family=family,
                status=status,
                payload_rows=payload_rows,
                imported=imported,
                skipped=skipped,
                failed=failed,
                unresolved=unresolved,
            )
            family_reports.append(family_report)
            counts["imported"] += imported
            counts["skipped"] += skipped
            counts["failed"] += failed
            counts["unresolved"] += unresolved

        restore_order = _restore_order_for_schema(parsed.schema_version)
        ordered_rows = {
            "projects": self._sort_projects(parsed.payload_rows["projects"]),
            "chat_threads": self._sort_threads(parsed.payload_rows["chat_threads"]),
            "chat_messages": self._sort_chat_messages(
                parsed.payload_rows["chat_messages"]
            ),
            "media_assets": self._sort_media_assets(
                parsed.payload_rows["media_assets"]
            ),
            "media_aliases": self._sort_media_aliases(
                parsed.payload_rows["media_aliases"]
            ),
            "uploaded_documents": self._sort_documents(
                parsed.payload_rows["uploaded_documents"]
            ),
            "generated_documents": self._sort_documents(
                parsed.payload_rows["generated_documents"]
            ),
            "uploaded_images": self._sort_documents(
                parsed.payload_rows["uploaded_images"]
            ),
            "generated_images": self._sort_documents(
                parsed.payload_rows["generated_images"]
            ),
            "thread_documents": self._sort_thread_documents(
                parsed.payload_rows["thread_documents"]
            ),
            "project_document_links": self._sort_project_document_links(
                parsed.payload_rows["project_document_links"]
            ),
            "extension_proposals": self._sort_extension_proposals(
                parsed.payload_rows["extension_proposals"]
            ),
            "extension_install_gate_decisions": self._sort_extension_install_gate_decisions(
                parsed.payload_rows["extension_install_gate_decisions"]
            ),
            "extension_registry_entries": self._sort_extension_registry_entries(
                parsed.payload_rows["extension_registry_entries"]
            ),
            "extension_install_bindings": self._sort_extension_install_bindings(
                parsed.payload_rows["extension_install_bindings"]
            ),
        }
        if parsed.schema_version == MANIFEST_SCHEMA_VERSION:
            ordered_rows.update(
                {
                    "persona_profiles": self._prepare_persona_profiles(
                        parsed.payload_rows["persona_profiles"],
                        parsed.payload_rows["persona_profile_revisions"],
                    ),
                    "persona_profile_revisions": self._sort_persona_revisions(
                        parsed.payload_rows["persona_profile_revisions"]
                    ),
                    "persona_profile_bindings": self._sort_persona_bindings(
                        parsed.payload_rows["persona_profile_bindings"]
                    ),
                }
            )

        try:
            if hasattr(self.db, "_connect") and callable(getattr(self.db, "_connect")):
                with self.db._connect() as conn:  # type: ignore[attr-defined]
                    for family in restore_order:
                        rows = ordered_rows[family]
                        if family == "persona_profile_bindings":
                            result = _call_restore(
                                RESTORE_METHODS[family],
                                rows,
                                conn,
                                target_user_id=parsed.user_id,
                            )
                        else:
                            result = _call_restore(RESTORE_METHODS[family], rows, conn)
                        _record_family(family, rows, result)
            else:
                for family in restore_order:
                    rows = ordered_rows[family]
                    if family == "persona_profile_bindings":
                        result = _call_restore(
                            RESTORE_METHODS[family],
                            rows,
                            None,
                            target_user_id=parsed.user_id,
                        )
                    else:
                        result = _call_restore(RESTORE_METHODS[family], rows, None)
                    _record_family(family, rows, result)
        except AccountRestoreError:
            raise
        except ValueError as exc:
            raise self._restore_conflict(
                parsed=parsed,
                family_reports=family_reports,
                counts=counts,
                message=str(exc),
                details={"reason": str(exc)},
            ) from exc
        except Exception as exc:
            raise AccountRestoreError(
                f"Account metadata restore failed: {exc}",
                code="restore_failed",
                status_code=500,
                validated=True,
                schema_version=parsed.schema_version,
                export_kind=parsed.export_kind,
                archive_includes_blob_coverage=parsed.archive_includes_blob_coverage,
                blob_coverage=parsed.blob_coverage,
                families=[report.to_dict() for report in family_reports],
                counts=dict(counts),
                notes=[
                    "Archive validation succeeded before restore began.",
                ],
                details={"reason": str(exc)},
            ) from exc

        return [report.to_dict() for report in family_reports], counts

    def _restore_conflict(
        self,
        *,
        parsed: ParsedArchive,
        family_reports: list[FamilyRestoreReport],
        counts: dict[str, int],
        message: str,
        details: dict[str, Any],
    ) -> AccountRestoreConflictError:
        if family_reports:
            family_reports = list(family_reports)
            family_reports[-1] = FamilyRestoreReport(
                family=family_reports[-1].family,
                status="failed",
                payload_rows=family_reports[-1].payload_rows,
                imported=family_reports[-1].imported,
                skipped=family_reports[-1].skipped,
                failed=1,
                unresolved=family_reports[-1].unresolved,
            )
        else:
            family_reports = _empty_family_reports(
                _restore_order_for_schema(parsed.schema_version)
            )  # type: ignore[assignment]
        counts = dict(counts)
        counts["failed"] = counts.get("failed", 0) + 1
        return AccountRestoreConflictError(
            message,
            validated=True,
            schema_version=parsed.schema_version,
            export_kind=parsed.export_kind,
            archive_includes_blob_coverage=parsed.archive_includes_blob_coverage,
            blob_coverage=parsed.blob_coverage,
            families=[
                report.to_dict() if isinstance(report, FamilyRestoreReport) else report
                for report in family_reports
            ],
            counts=counts,
            notes=[
                "Archive validation succeeded before restore began.",
                "The archive conflicts with pre-existing rows and was not merged.",
            ],
            details=details,
        )

    def _build_success_report(
        self,
        parsed: ParsedArchive,
        families: list[dict[str, Any]],
        counts: dict[str, int],
    ) -> dict[str, Any]:
        notes = [
            "Metadata restore only; blob restoration is not implemented in this slice.",
            "Bundled blob files were validated against manifest digests and not written back to storage.",
        ]
        if parsed.blob_coverage.get("missing_families"):
            notes.append(
                "The archive manifest reports incomplete blob coverage; unresolved blob rows were validated only."
            )
        if parsed.blob_coverage.get("unresolved_rows"):
            notes.append(
                "Some bundled blob rows remain unresolved in this slice; metadata was restored without blob write-back."
            )
        return {
            "ok": True,
            "schema_version": parsed.schema_version,
            "export_kind": parsed.export_kind,
            "validated": True,
            "metadata_restore_only": True,
            "blob_restore_supported": False,
            "archive_includes_blob_coverage": parsed.archive_includes_blob_coverage,
            "blob_coverage": {
                **parsed.blob_coverage,
                "validated_only": True,
            },
            "families": families,
            "counts": counts,
            "notes": notes,
        }

    def _sort_projects(self, rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
        return sorted(rows, key=lambda row: (_sort_text(row.get("id")),))

    def _sort_threads(self, rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
        indexed: dict[Any, dict[str, Any]] = {row.get("id"): row for row in rows}
        order: list[dict[str, Any]] = []
        visiting: set[Any] = set()
        visited: set[Any] = set()

        def visit(thread_id: Any) -> None:
            if thread_id in visited:
                return
            if thread_id in visiting:
                raise ValueError("chat_threads contains a cycle")
            row = indexed.get(thread_id)
            if row is None:
                raise ValueError(f"chat_threads row {thread_id!r} missing")
            visiting.add(thread_id)
            parent_id = row.get("parent_id")
            if parent_id is not None:
                visit(parent_id)
            visiting.remove(thread_id)
            visited.add(thread_id)
            order.append(row)

        for thread_id in sorted(
            indexed,
            key=lambda value: (
                _sort_text(indexed[value].get("created_at")),
                _sort_text(value),
            ),
        ):
            visit(thread_id)
        return order

    def _sort_chat_messages(self, rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
        return sorted(
            rows,
            key=lambda row: (
                _sort_text(row.get("thread_id")),
                _sort_text(row.get("event_at") or row.get("created_at")),
                _sort_text(row.get("id")),
            ),
        )

    def _sort_media_assets(self, rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
        return sorted(
            rows,
            key=lambda row: (
                _sort_text(row.get("ingested_at")),
                _sort_text(row.get("id")),
            ),
        )

    def _sort_media_aliases(self, rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
        return sorted(
            rows,
            key=lambda row: (
                _sort_text(row.get("asset_id")),
                _sort_text(row.get("created_at")),
                _sort_text(row.get("id")),
            ),
        )

    def _sort_documents(self, rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
        return sorted(
            rows,
            key=lambda row: (
                _sort_text(row.get("created_at")),
                _sort_text(row.get("id")),
            ),
        )

    def _sort_thread_documents(
        self, rows: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        return sorted(
            rows,
            key=lambda row: (
                _sort_text(row.get("thread_id")),
                _sort_text(row.get("created_at")),
                _sort_text(row.get("id")),
            ),
        )

    def _sort_project_document_links(
        self, rows: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        return sorted(
            rows,
            key=lambda row: (
                _sort_text(row.get("project_id")),
                _sort_text(row.get("attached_at")),
                _sort_text(row.get("id")),
            ),
        )

    def _sort_extension_proposals(
        self, rows: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        return sorted(
            rows,
            key=lambda row: (
                _sort_text(row.get("created_at")),
                _sort_text(row.get("proposal_id") or row.get("id")),
            ),
        )

    def _sort_extension_install_gate_decisions(
        self, rows: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        return sorted(
            rows,
            key=lambda row: (
                _sort_text(row.get("created_at")),
                _sort_text(row.get("decision_id") or row.get("id")),
            ),
        )

    def _sort_extension_registry_entries(
        self, rows: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        return sorted(
            rows,
            key=lambda row: (
                _sort_text(row.get("created_at")),
                _sort_text(row.get("registry_id") or row.get("id")),
            ),
        )

    def _sort_extension_install_bindings(
        self, rows: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        return sorted(
            rows,
            key=lambda row: (
                _sort_text(row.get("created_at")),
                _sort_text(row.get("binding_id") or row.get("id")),
            ),
        )

    def _prepare_persona_profiles(
        self,
        profiles: list[dict[str, Any]],
        revisions: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        revisions_by_key = {
            (str(row["profile_id"]), int(row["revision"])): row for row in revisions
        }
        prepared: list[dict[str, Any]] = []
        for profile in profiles:
            profile_id = str(profile["id"])
            current_revision = int(profile["current_revision"])
            revision_row = revisions_by_key[(profile_id, current_revision)]
            persona_manifest = PersonaProfileManifest.model_validate(
                revision_row["manifest_json"]
            )
            prepared.append(
                {
                    "id": profile_id,
                    "name": persona_manifest.identity.name,
                    "system_prompt": persona_manifest.prompt.system_prompt,
                    "model_provider": persona_manifest.model.provider,
                    "model_id": persona_manifest.model.model,
                    "temperature": persona_manifest.model.temperature,
                    "current_revision": current_revision,
                    "created_at": profile["created_at"],
                    "updated_at": profile["updated_at"],
                }
            )
        return sorted(prepared, key=lambda row: _sort_text(row["id"]))

    def _sort_persona_revisions(
        self, rows: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        return sorted(
            rows,
            key=lambda row: (
                _sort_text(row.get("profile_id")),
                int(row.get("revision") or 0),
            ),
        )

    def _sort_persona_bindings(
        self, rows: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        return sorted(rows, key=lambda row: _sort_text(row.get("profile_id")))

    def _validation_error(
        self,
        code: str,
        message: str,
        *,
        status_code: int = 400,
        manifest: dict[str, Any] | None = None,
        details: dict[str, Any] | None = None,
    ) -> AccountRestoreValidationError:
        schema_version = None
        export_kind = None
        archive_includes_blob_coverage = False
        blob_coverage = _empty_blob_coverage()
        if isinstance(manifest, dict):
            schema_version = str(manifest.get("schema_version") or None)
            export_kind = str(manifest.get("export_kind") or None)
            blob = manifest.get("blob_coverage")
            if isinstance(blob, dict):
                blob_coverage = {**blob, "validated_only": True}
                archive_includes_blob_coverage = bool(
                    blob_coverage.get("bundled_blob_paths")
                )
        return AccountRestoreValidationError(
            message,
            code=code,
            status_code=status_code,
            validated=False,
            schema_version=schema_version,
            export_kind=export_kind,
            archive_includes_blob_coverage=archive_includes_blob_coverage,
            blob_coverage=blob_coverage,
            families=_empty_family_reports(_restore_order_for_schema(schema_version)),
            notes=[
                "No database writes were performed.",
            ],
            details=details,
        )


def _restore_connection(conn: Any | None, db: Any):
    if conn is not None:
        return conn
    return db._connect()


# =============================================================================
# UMS-04C-A: canonical-memory restore preflight
# =============================================================================
#
# This preflight consumes an already-parsed v4 canonical-memory payload and the
# explicit identity maps produced by the existing restore process, and returns
# a deterministic reconstruction plan. It performs all structural and authority
# checks that can be proven before any database write. It does NOT persist.
#
# Production v4 restore remains unsupported. ``SUPPORTED_SCHEMA_VERSIONS`` does
# not include ``"account-export.v4"``. This preflight is intended for a later
# persistence slice; it is not wired into
# ``AccountRestoreService.restore_from_zip``.

UNIFIED_MEMORY_RESTORE_LINK_KINDS: frozenset[str] = frozenset(
    {"captured_under", "suggested_by", "associated_with"}
)
UNIFIED_MEMORY_RESTORE_PLAN_FAMILIES: tuple[str, ...] = (
    "persona_subjects",
    "persona_subject_bindings",
    "memory_records",
    "memory_persona_links",
    "memory_provenance",
)
_UNIFIED_MEMORY_REQUIRED_FIELDS: dict[str, tuple[str, ...]] = {
    "persona_subjects": (
        "persona_subject_id",
        "user_id",
        "display_name_snapshot",
        "lifecycle",
        "created_at",
        "updated_at",
    ),
    "persona_subject_bindings": (
        "binding_id",
        "persona_subject_id",
        "subject_user_id",
        "source_account_id",
        "ref_kind",
        "ref_id",
        "valid_from",
        "valid_until",
        "created_at",
    ),
    "memory_records": (
        "memory_id",
        "user_id",
        "project_id",
        "semantic_species",
        "text_content",
        "fact_key",
        "fact_value",
        "fact_confidence",
        "reviewed_at",
        "activated_at",
        "pinned",
        "held",
        "extensions",
        "created_at",
        "updated_at",
    ),
    "memory_persona_links": (
        "link_id",
        "memory_id",
        "user_id",
        "persona_subject_id",
        "persona_user_id",
        "link_kind",
        "created_at",
    ),
    "memory_provenance": (
        "provenance_id",
        "memory_id",
        "user_id",
        "source_system",
        "source_record_id",
        "source_thread_id",
        "source_message_id",
        "source_import_job_id",
        "source_export_fingerprint",
        "source_subject_kind",
        "source_subject_id",
        "is_imported",
        "extensions",
        "created_at",
    ),
}
_UNIFIED_MEMORY_SORT_KEYS: dict[str, tuple[str, ...]] = {
    "persona_subjects": ("persona_subject_id",),
    "persona_subject_bindings": (
        "persona_subject_id",
        "valid_from",
        "binding_id",
    ),
    "memory_records": ("memory_id",),
    "memory_persona_links": (
        "memory_id",
        "persona_subject_id",
        "link_kind",
        "link_id",
    ),
    "memory_provenance": ("memory_id", "provenance_id"),
}


class UnifiedMemoryRestorePreflightError(AccountRestoreValidationError):
    code = "unified_memory_restore_preflight_failed"
    validated = False


def _preflight_error(
    code: str,
    message: str,
    *,
    details: dict[str, Any] | None = None,
) -> UnifiedMemoryRestorePreflightError:
    return UnifiedMemoryRestorePreflightError(
        message,
        code=code,
        details=details or {},
    )


@dataclass(slots=True)
class PlannedPersonaSubject:
    source_persona_subject_id: str
    target_persona_subject_id: str
    target_account_id: str
    display_name_snapshot: str
    lifecycle: str
    created_at: str
    updated_at: str


@dataclass(slots=True)
class PlannedPersonaSubjectBinding:
    source_binding_id: str
    target_binding_id: str
    target_persona_subject_id: str
    target_account_id: str
    ref_kind: str
    ref_id: str
    valid_from: str | None
    valid_until: str | None
    created_at: str


@dataclass(slots=True)
class PlannedMemoryRecord:
    source_memory_id: str
    target_memory_id: str
    target_account_id: str
    target_project_id: int | None
    semantic_species: str
    text_content: str | None
    fact_key: str | None
    fact_value: str | None
    fact_confidence: float | None
    reviewed_at: str | None
    activated_at: str | None
    pinned: bool
    held: bool
    extensions: dict[str, Any]


@dataclass(slots=True)
class PlannedPersonaLink:
    source_link_id: str
    target_link_id: str
    target_memory_id: str
    target_persona_subject_id: str
    target_account_id: str
    link_kind: str
    created_at: str


@dataclass(slots=True)
class PlannedMemoryProvenance:
    source_provenance_id: str
    target_provenance_id: str
    target_memory_id: str
    target_account_id: str
    source_system: str
    source_record_id: str
    target_source_thread_id: int | None
    target_source_message_id: int | None
    source_import_job_id: str | None
    source_export_fingerprint: str | None
    source_subject_kind: str | None
    source_subject_id: str | None
    is_imported: bool
    extensions: dict[str, Any]
    created_at: str


@dataclass(slots=True)
class CanonicalMemoryRestorePlan:
    """Mutation-free canonical-memory reconstruction plan for ``account-export.v4``.

    Contains all validated, classified, and deterministically ordered information
    needed by a later persistence slice to execute canonical writes in
    dependency order without reinterpreting the archive. ``account-export.v4``
    production restore remains unsupported at this point; this plan is the
    pre-mutation boundary that a later UMS-04C persistence slice must consume.
    """

    target_account_id: str
    source_account_id: str
    persona_subjects: tuple[PlannedPersonaSubject, ...]
    persona_subject_bindings: tuple[PlannedPersonaSubjectBinding, ...]
    memory_records: tuple[PlannedMemoryRecord, ...]
    memory_persona_links: tuple[PlannedPersonaLink, ...]
    memory_provenance: tuple[PlannedMemoryProvenance, ...]


def _preflight_identity_str(value: Any, *, field: str) -> str:
    text = str(value or "").strip() if value is not None else ""
    if not text:
        raise _preflight_error(
            "payload_invalid_required_field",
            f"{field} is required and must be non-empty",
            details={"field": field},
        )
    return text


def _preflight_optional_str(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _preflight_optional_int(value: Any, *, field: str) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError) as exc:
        raise _preflight_error(
            "payload_invalid_required_field",
            f"{field} must be an integer when present",
            details={"field": field, "value": value},
        ) from exc


def _preflight_extensions(value: Any, *, field: str) -> dict[str, Any]:
    if value is None:
        return {}
    if not isinstance(value, dict):
        raise _preflight_error(
            "payload_invalid_required_field",
            f"{field} must be a JSON object when present",
            details={"field": field},
        )
    return dict(value)


def _preflight_dict_copy(value: dict[str, Any]) -> dict[str, Any]:
    return dict(value)


def _preflight_required_fields_present(row: dict[str, Any], family: str) -> None:
    required = _UNIFIED_MEMORY_REQUIRED_FIELDS[family]
    for field in required:
        if field not in row:
            raise _preflight_error(
                "payload_invalid_required_field",
                f"{family} row is missing required field {field!r}",
                details={"family": family, "field": field},
            )


def _preflight_stable_subject_id(row: dict[str, Any], *, family: str) -> str:
    value = _preflight_identity_str(
        row.get("persona_subject_id"), field=f"{family}.persona_subject_id"
    )
    return value


def _preflight_memory_id(row: dict[str, Any], *, family: str) -> str:
    value = _preflight_identity_str(row.get("memory_id"), field=f"{family}.memory_id")
    return value


def _preflight_binding_id(row: dict[str, Any]) -> str:
    return _preflight_identity_str(
        row.get("binding_id"), field="persona_subject_bindings.binding_id"
    )


def _preflight_link_id(row: dict[str, Any]) -> str:
    return _preflight_identity_str(
        row.get("link_id"), field="memory_persona_links.link_id"
    )


def _preflight_provenance_id(row: dict[str, Any]) -> str:
    return _preflight_identity_str(
        row.get("provenance_id"), field="memory_provenance.provenance_id"
    )


def _preflight_owner_matches(
    row: dict[str, Any],
    *,
    family: str,
    expected_owner: str,
) -> None:
    actual = _preflight_identity_str(row.get("user_id"), field=f"{family}.user_id")
    if actual != expected_owner:
        raise _preflight_error(
            "memory_account_mismatch",
            f"{family} row targets account {actual!r}; expected {expected_owner!r}",
            details={
                "family": family,
                "actual": actual,
                "expected": expected_owner,
            },
        )


def _preflight_binding_subject_and_source_match(
    row: dict[str, Any],
    *,
    expected_account: str,
) -> None:
    subject_user = _preflight_identity_str(
        row.get("subject_user_id"), field="persona_subject_bindings.subject_user_id"
    )
    if subject_user != expected_account:
        raise _preflight_error(
            "persona_binding_account_mismatch",
            "persona_subject_bindings.subject_user_id must match the source account",
            details={
                "binding_id": row.get("binding_id"),
                "actual": subject_user,
                "expected": expected_account,
            },
        )
    source_account = _preflight_identity_str(
        row.get("source_account_id"), field="persona_subject_bindings.source_account_id"
    )
    if source_account != expected_account:
        raise _preflight_error(
            "persona_binding_account_mismatch",
            "persona_subject_bindings.source_account_id must match the source account",
            details={
                "binding_id": row.get("binding_id"),
                "actual": source_account,
                "expected": expected_account,
            },
        )


def _preflight_memory_link_owner_matches(
    row: dict[str, Any], *, expected_account: str
) -> None:
    user_id = _preflight_identity_str(
        row.get("user_id"), field="memory_persona_links.user_id"
    )
    persona_user_id = _preflight_identity_str(
        row.get("persona_user_id"), field="memory_persona_links.persona_user_id"
    )
    if user_id != expected_account or persona_user_id != expected_account:
        raise _preflight_error(
            "memory_persona_link_account_mismatch",
            "memory_persona_links row references an account outside the restored account",
            details={
                "link_id": row.get("link_id"),
                "user_id": user_id,
                "persona_user_id": persona_user_id,
                "expected": expected_account,
            },
        )


def _preflight_memory_provenance_owner_matches(
    row: dict[str, Any], *, expected_account: str
) -> None:
    user_id = _preflight_identity_str(
        row.get("user_id"), field="memory_provenance.user_id"
    )
    if user_id != expected_account:
        raise _preflight_error(
            "memory_provenance_account_mismatch",
            "memory_provenance row references an account outside the restored account",
            details={
                "provenance_id": row.get("provenance_id"),
                "actual": user_id,
                "expected": expected_account,
            },
        )


def _preflight_link_kind(row: dict[str, Any]) -> str:
    kind = _preflight_identity_str(
        row.get("link_kind"), field="memory_persona_links.link_kind"
    )
    if kind not in UNIFIED_MEMORY_RESTORE_LINK_KINDS:
        raise _preflight_error(
            "memory_persona_link_invalid_kind",
            f"memory_persona_links.link_kind {kind!r} is not a canonical link kind",
            details={
                "link_id": row.get("link_id"),
                "link_kind": kind,
                "allowed": sorted(UNIFIED_MEMORY_RESTORE_LINK_KINDS),
            },
        )
    return kind


class UnifiedMemoryRestorePreflight:
    """Mutation-free canonical-memory preflight for ``account-export.v4``.

    Consumes:

      - parsed canonical-memory payload rows;
      - explicit source→target identity maps for Projects, threads, and
        messages.

    Produces:

      - a deterministic :class:`CanonicalMemoryRestorePlan` containing the
        classified reconstruction targets.

    Does NOT persist.

    Failure modes (each raises ``UnifiedMemoryRestorePreflightError``):

      - missing required field;
      - cross-account reference;
      - missing Project map for Project-scoped memory;
      - missing local thread/message map for provenance with local lineage;
      - invalid ``link_kind`` / ``semantic_species`` / lifecycle token;
      - orphan Persona binding / Persona link / provenance row;
      - cross-account relationship.
    """

    def __init__(
        self,
        *,
        target_account_id: str,
        source_account_id: str,
        project_map: dict[int, int] | None = None,
        thread_map: dict[int, int] | None = None,
        message_map: dict[int, int] | None = None,
    ) -> None:
        target = _preflight_identity_str(target_account_id, field="target_account_id")
        source = _preflight_identity_str(source_account_id, field="source_account_id")
        if not target:
            raise _preflight_error(
                "preflight_target_account_missing",
                "target_account_id is required for the canonical-memory restore preflight",
            )
        if not source:
            raise _preflight_error(
                "preflight_source_account_missing",
                "source_account_id is required for the canonical-memory restore preflight",
            )
        self._target_account_id = target
        self._source_account_id = source
        self._project_map: dict[int, int] = dict(project_map or {})
        self._thread_map: dict[int, int] = dict(thread_map or {})
        self._message_map: dict[int, int] = dict(message_map or {})

    @property
    def target_account_id(self) -> str:
        return self._target_account_id

    @property
    def source_account_id(self) -> str:
        return self._source_account_id

    def plan(
        self,
        payload_rows: dict[str, list[dict[str, Any]]],
    ) -> CanonicalMemoryRestorePlan:
        for family in UNIFIED_MEMORY_RESTORE_PLAN_FAMILIES:
            if family not in payload_rows:
                raise _preflight_error(
                    "payload_family_missing",
                    f"canonical-memory payload is missing family {family!r}",
                    details={"family": family},
                )

        # Phase 1: validate subject row set and build planned subjects.
        subjects_by_id: dict[str, PlannedPersonaSubject] = {}
        for raw_row in payload_rows["persona_subjects"]:
            row = _preflight_dict_copy(raw_row)
            _preflight_required_fields_present(row, "persona_subjects")
            subject_id = _preflight_stable_subject_id(row, family="persona_subjects")
            _preflight_owner_matches(
                row, family="persona_subjects", expected_owner=self._source_account_id
            )
            if subject_id in subjects_by_id:
                raise _preflight_error(
                    "persona_subject_duplicate",
                    "persona_subjects row is duplicated by persona_subject_id",
                    details={"persona_subject_id": subject_id},
                )
            subjects_by_id[subject_id] = PlannedPersonaSubject(
                source_persona_subject_id=subject_id,
                target_persona_subject_id=subject_id,
                target_account_id=self._target_account_id,
                display_name_snapshot=_preflight_identity_str(
                    row.get("display_name_snapshot"),
                    field="persona_subjects.display_name_snapshot",
                ),
                lifecycle=_preflight_identity_str(
                    row.get("lifecycle"),
                    field="persona_subjects.lifecycle",
                ),
                created_at=_preflight_identity_str(
                    row.get("created_at"),
                    field="persona_subjects.created_at",
                ),
                updated_at=_preflight_identity_str(
                    row.get("updated_at"),
                    field="persona_subjects.updated_at",
                ),
            )

        # Phase 2: validate bindings and plan them.
        planned_bindings: list[PlannedPersonaSubjectBinding] = []
        seen_binding_ids: set[str] = set()
        for raw_row in payload_rows["persona_subject_bindings"]:
            row = _preflight_dict_copy(raw_row)
            _preflight_required_fields_present(row, "persona_subject_bindings")
            binding_id = _preflight_binding_id(row)
            if binding_id in seen_binding_ids:
                raise _preflight_error(
                    "persona_binding_duplicate",
                    "persona_subject_bindings row is duplicated by binding_id",
                    details={"binding_id": binding_id},
                )
            seen_binding_ids.add(binding_id)
            subject_id = _preflight_stable_subject_id(
                row, family="persona_subject_bindings"
            )
            if subject_id not in subjects_by_id:
                raise _preflight_error(
                    "persona_binding_orphan",
                    "persona_subject_bindings references a persona_subject_id that is not in the planned subject set",
                    details={
                        "binding_id": binding_id,
                        "persona_subject_id": subject_id,
                    },
                )
            _preflight_binding_subject_and_source_match(
                row, expected_account=self._source_account_id
            )
            planned_bindings.append(
                PlannedPersonaSubjectBinding(
                    source_binding_id=binding_id,
                    target_binding_id=binding_id,
                    target_persona_subject_id=subject_id,
                    target_account_id=self._target_account_id,
                    ref_kind=_preflight_identity_str(
                        row.get("ref_kind"),
                        field="persona_subject_bindings.ref_kind",
                    ),
                    ref_id=_preflight_identity_str(
                        row.get("ref_id"),
                        field="persona_subject_bindings.ref_id",
                    ),
                    valid_from=_preflight_optional_str(row.get("valid_from")),
                    valid_until=_preflight_optional_str(row.get("valid_until")),
                    created_at=_preflight_identity_str(
                        row.get("created_at"),
                        field="persona_subject_bindings.created_at",
                    ),
                )
            )

        # Phase 3: validate memory records and plan them. This phase also
        # resolves Project mapping for Project-scoped records.
        planned_memories: dict[str, PlannedMemoryRecord] = {}
        memory_provenance_required: set[str] = set()
        for raw_row in payload_rows["memory_records"]:
            row = _preflight_dict_copy(raw_row)
            _preflight_required_fields_present(row, "memory_records")
            memory_id = _preflight_memory_id(row, family="memory_records")
            if memory_id in planned_memories:
                raise _preflight_error(
                    "memory_record_duplicate",
                    "memory_records row is duplicated by memory_id",
                    details={"memory_id": memory_id},
                )
            _preflight_owner_matches(
                row, family="memory_records", expected_owner=self._source_account_id
            )
            source_project_id = _preflight_optional_int(
                row.get("project_id"), field="memory_records.project_id"
            )
            if source_project_id is None:
                target_project_id: int | None = None
            else:
                if source_project_id not in self._project_map:
                    raise _preflight_error(
                        "memory_project_mapping_missing",
                        "memory_records row references a project_id that is not in the explicit restore Project map; refusing to widen scope to account-owned",
                        details={
                            "memory_id": memory_id,
                            "project_id": source_project_id,
                        },
                    )
                target_project_id = self._project_map[source_project_id]
                if target_project_id is None:
                    raise _preflight_error(
                        "memory_project_mapping_null",
                        "explicit Project map may not map a Project to NULL target",
                        details={
                            "memory_id": memory_id,
                            "project_id": source_project_id,
                        },
                    )
            species = row.get("semantic_species")
            if species is None or not str(species).strip():
                raise _preflight_error(
                    "memory_species_missing",
                    "memory_records row is missing semantic_species",
                    details={"memory_id": memory_id},
                )
            species = str(species).strip()
            reviewed_at = _preflight_optional_str(row.get("reviewed_at"))
            activated_at = _preflight_optional_str(row.get("activated_at"))
            pinned = row.get("pinned")
            held = row.get("held")
            if not isinstance(pinned, bool):
                raise _preflight_error(
                    "memory_governance_state_invalid",
                    "memory_records.pinned must be a boolean",
                    details={"memory_id": memory_id, "pinned": pinned},
                )
            if not isinstance(held, bool):
                raise _preflight_error(
                    "memory_governance_state_invalid",
                    "memory_records.held must be a boolean",
                    details={"memory_id": memory_id, "held": held},
                )
            planned_memories[memory_id] = PlannedMemoryRecord(
                source_memory_id=memory_id,
                target_memory_id=memory_id,
                target_account_id=self._target_account_id,
                target_project_id=target_project_id,
                semantic_species=species,
                text_content=_preflight_optional_str(row.get("text_content")),
                fact_key=_preflight_optional_str(row.get("fact_key")),
                fact_value=_preflight_optional_str(row.get("fact_value")),
                fact_confidence=(
                    float(row["fact_confidence"])
                    if row.get("fact_confidence") is not None
                    else None
                ),
                reviewed_at=reviewed_at,
                activated_at=activated_at,
                pinned=pinned,
                held=held,
                extensions=_preflight_extensions(
                    row.get("extensions"), field="memory_records.extensions"
                ),
            )
            # Every canonical memory requires at least one provenance row,
            # which is the closure rule mirrored from the export side.
            memory_provenance_required.add(memory_id)

        # Phase 4: validate Persona links.
        planned_links: list[PlannedPersonaLink] = []
        seen_link_ids: set[str] = set()
        for raw_row in payload_rows["memory_persona_links"]:
            row = _preflight_dict_copy(raw_row)
            _preflight_required_fields_present(row, "memory_persona_links")
            link_id = _preflight_link_id(row)
            if link_id in seen_link_ids:
                raise _preflight_error(
                    "memory_persona_link_duplicate",
                    "memory_persona_links row is duplicated by link_id",
                    details={"link_id": link_id},
                )
            seen_link_ids.add(link_id)
            memory_id = _preflight_memory_id(row, family="memory_persona_links")
            if memory_id not in planned_memories:
                raise _preflight_error(
                    "memory_persona_link_orphan",
                    "memory_persona_links row references a memory_id that is not in the planned memory set",
                    details={"link_id": link_id, "memory_id": memory_id},
                )
            subject_id = _preflight_stable_subject_id(
                row, family="memory_persona_links"
            )
            if subject_id not in subjects_by_id:
                raise _preflight_error(
                    "memory_persona_link_orphan",
                    "memory_persona_links row references a persona_subject_id that is not in the planned subject set",
                    details={
                        "link_id": link_id,
                        "persona_subject_id": subject_id,
                    },
                )
            _preflight_memory_link_owner_matches(
                row, expected_account=self._source_account_id
            )
            kind = _preflight_link_kind(row)
            planned_links.append(
                PlannedPersonaLink(
                    source_link_id=link_id,
                    target_link_id=link_id,
                    target_memory_id=memory_id,
                    target_persona_subject_id=subject_id,
                    target_account_id=self._target_account_id,
                    link_kind=kind,
                    created_at=_preflight_identity_str(
                        row.get("created_at"),
                        field="memory_persona_links.created_at",
                    ),
                )
            )

        # Phase 5: validate provenance rows. Local thread/message references
        # must resolve through the explicit restore maps; opaque external
        # identifiers are preserved verbatim and never treated as local.
        planned_provenance: list[PlannedMemoryProvenance] = []
        seen_provenance_ids: set[str] = set()
        for raw_row in payload_rows["memory_provenance"]:
            row = _preflight_dict_copy(raw_row)
            _preflight_required_fields_present(row, "memory_provenance")
            provenance_id = _preflight_provenance_id(row)
            if provenance_id in seen_provenance_ids:
                raise _preflight_error(
                    "memory_provenance_duplicate",
                    "memory_provenance row is duplicated by provenance_id",
                    details={"provenance_id": provenance_id},
                )
            seen_provenance_ids.add(provenance_id)
            memory_id = _preflight_memory_id(row, family="memory_provenance")
            if memory_id not in planned_memories:
                raise _preflight_error(
                    "memory_provenance_orphan",
                    "memory_provenance row references a memory_id that is not in the planned memory set",
                    details={
                        "provenance_id": provenance_id,
                        "memory_id": memory_id,
                    },
                )
            _preflight_memory_provenance_owner_matches(
                row, expected_account=self._source_account_id
            )
            source_thread_id = _preflight_optional_int(
                row.get("source_thread_id"),
                field="memory_provenance.source_thread_id",
            )
            source_message_id = _preflight_optional_int(
                row.get("source_message_id"),
                field="memory_provenance.source_message_id",
            )
            target_source_thread_id: int | None = None
            target_source_message_id: int | None = None
            if source_thread_id is not None:
                if source_thread_id not in self._thread_map:
                    raise _preflight_error(
                        "memory_provenance_thread_mapping_missing",
                        "memory_provenance.source_thread_id is not in the explicit restore thread map",
                        details={
                            "provenance_id": provenance_id,
                            "source_thread_id": source_thread_id,
                        },
                    )
                target_source_thread_id = self._thread_map[source_thread_id]
            if source_message_id is not None:
                if source_message_id not in self._message_map:
                    raise _preflight_error(
                        "memory_provenance_message_mapping_missing",
                        "memory_provenance.source_message_id is not in the explicit restore message map",
                        details={
                            "provenance_id": provenance_id,
                            "source_message_id": source_message_id,
                        },
                    )
                target_source_message_id = self._message_map[source_message_id]
            planned_provenance.append(
                PlannedMemoryProvenance(
                    source_provenance_id=provenance_id,
                    target_provenance_id=provenance_id,
                    target_memory_id=memory_id,
                    target_account_id=self._target_account_id,
                    source_system=_preflight_identity_str(
                        row.get("source_system"),
                        field="memory_provenance.source_system",
                    ),
                    source_record_id=_preflight_identity_str(
                        row.get("source_record_id"),
                        field="memory_provenance.source_record_id",
                    ),
                    target_source_thread_id=target_source_thread_id,
                    target_source_message_id=target_source_message_id,
                    source_import_job_id=_preflight_optional_str(
                        row.get("source_import_job_id")
                    ),
                    source_export_fingerprint=_preflight_optional_str(
                        row.get("source_export_fingerprint")
                    ),
                    source_subject_kind=_preflight_optional_str(
                        row.get("source_subject_kind")
                    ),
                    source_subject_id=_preflight_optional_str(
                        row.get("source_subject_id")
                    ),
                    is_imported=bool(row.get("is_imported")),
                    extensions=_preflight_extensions(
                        row.get("extensions"),
                        field="memory_provenance.extensions",
                    ),
                    created_at=_preflight_identity_str(
                        row.get("created_at"),
                        field="memory_provenance.created_at",
                    ),
                )
            )

        # Phase 6: archive closure. Every planned memory must have at least
        # one provenance row, mirroring the export-side closure rule.
        provenance_memory_ids = {row.target_memory_id for row in planned_provenance}
        missing = memory_provenance_required - provenance_memory_ids
        if missing:
            raise _preflight_error(
                "memory_provenance_missing",
                "one or more memory_records rows lack a memory_provenance row",
                details={"memory_ids": sorted(missing)},
            )

        # Phase 7: deterministic ordering.
        return CanonicalMemoryRestorePlan(
            target_account_id=self._target_account_id,
            source_account_id=self._source_account_id,
            persona_subjects=tuple(
                sorted(
                    subjects_by_id.values(),
                    key=lambda plan: _sort_text(plan.source_persona_subject_id),
                )
            ),
            persona_subject_bindings=tuple(
                sorted(
                    planned_bindings,
                    key=lambda plan: (
                        _sort_text(plan.target_persona_subject_id),
                        _sort_text(plan.valid_from),
                        _sort_text(plan.source_binding_id),
                    ),
                )
            ),
            memory_records=tuple(
                sorted(
                    planned_memories.values(),
                    key=lambda plan: _sort_text(plan.source_memory_id),
                )
            ),
            memory_persona_links=tuple(
                sorted(
                    planned_links,
                    key=lambda plan: (
                        _sort_text(plan.target_memory_id),
                        _sort_text(plan.target_persona_subject_id),
                        _sort_text(plan.link_kind),
                        _sort_text(plan.source_link_id),
                    ),
                )
            ),
            memory_provenance=tuple(
                sorted(
                    planned_provenance,
                    key=lambda plan: (
                        _sort_text(plan.target_memory_id),
                        _sort_text(plan.source_provenance_id),
                    ),
                )
            ),
        )
