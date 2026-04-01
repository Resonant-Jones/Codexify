# guardian/api_exports.py
import io
import json
import logging
import os
import re
import zipfile
from datetime import datetime, timezone
from typing import Any, Iterable, Literal, Optional

import orjson
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse, Response, StreamingResponse
from starlette.background import BackgroundTask

from guardian.core import db
from guardian.core.auth import AuthenticatedUser, require_user
from guardian.services.account_export import (
    ZIP_FILENAME,
    build_account_export_zip,
)

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/exports",
    tags=["exports"],
)


def _serialize_chunk(row: Any) -> bytes:
    """
    Normalize the backend row into NDJSON bytes.
    """
    if isinstance(row, bytes):
        return row if row.endswith(b"\n") else row + b"\n"
    if isinstance(row, str):
        payload = row if row.endswith("\n") else row + "\n"
        return payload.encode("utf-8")
    # Fallback: assume a mapping/dict-like object.
    return orjson.dumps(row) + b"\n"


def _safe_slug(
    value: Any, *, default: str = "untitled", max_length: int = 72
) -> str:
    text = str(value or "").strip().lower()
    if not text:
        return default
    text = re.sub(r"[^a-z0-9]+", "-", text)
    text = text.strip("-")
    if not text:
        return default
    if len(text) > max_length:
        text = text[:max_length].rstrip("-")
    return text or default


def _safe_filename(
    value: Any, *, default: str = "untitled", max_length: int = 96
) -> str:
    text = str(value or "").strip()
    if not text:
        return default
    text = re.sub(r"[<>:\"/\\|?*]", "_", text)
    text = "".join(char for char in text if ord(char) >= 32)
    text = text.rstrip(". ")
    if not text:
        return default
    if len(text) > max_length:
        text = text[:max_length].rstrip()
    return text or default


def _cleanup_export_file(path: str) -> None:
    try:
        os.unlink(path)
    except FileNotFoundError:
        return


def _source_thread_short(
    thread: dict[str, Any], messages: list[dict[str, Any]]
) -> str:
    metadata = (
        thread.get("metadata")
        if isinstance(thread.get("metadata"), dict)
        else {}
    )
    source_thread_id = metadata.get("source_thread_id")
    if not source_thread_id and messages:
        first_meta = messages[0].get("extra_meta")
        if isinstance(first_meta, dict):
            source_thread_id = first_meta.get("source_thread_id")
    if not source_thread_id:
        source_thread_id = thread.get("id")

    token = str(source_thread_id or "thread").strip()
    token = re.sub(r"[^a-zA-Z0-9_-]", "", token)
    if not token:
        token = "thread"
    return token[:16]


def _dedupe_zip_path(path: str, seen_paths: set[str]) -> str:
    if path not in seen_paths:
        seen_paths.add(path)
        return path

    stem, dot, ext = path.rpartition(".")
    base = stem if dot else path
    suffix = f".{ext}" if dot else ""
    counter = 2
    while True:
        candidate = f"{base} ({counter}){suffix}"
        if candidate not in seen_paths:
            seen_paths.add(candidate)
            return candidate
        counter += 1


def _canonical_message_timestamp(message: dict[str, Any]) -> Optional[str]:
    extra_meta = message.get("extra_meta")
    if isinstance(extra_meta, dict):
        source_created = extra_meta.get("source_created_at")
        if isinstance(source_created, str) and source_created.strip():
            return source_created
    event_at = message.get("event_at")
    if isinstance(event_at, str) and event_at.strip():
        return event_at
    created_at = message.get("created_at")
    if isinstance(created_at, str) and created_at.strip():
        return created_at
    return None


def _build_export_message_payload(message: dict[str, Any]) -> dict[str, Any]:
    extra_meta = (
        message.get("extra_meta")
        if isinstance(message.get("extra_meta"), dict)
        else {}
    )
    payload = {
        "id": message.get("id"),
        "role": message.get("role"),
        "content": str(message.get("content") or ""),
        "timestamp": _canonical_message_timestamp(message),
    }
    source_thread_id = extra_meta.get("source_thread_id")
    if source_thread_id is not None:
        payload["source_thread_id"] = source_thread_id
    source_message_id = extra_meta.get("source_message_id")
    if source_message_id is not None:
        payload["source_message_id"] = source_message_id
    turn_index = extra_meta.get("turn_index")
    if turn_index is not None:
        payload["turn_index"] = turn_index
    return payload


def _build_project_folder(thread: dict[str, Any]) -> str:
    project_id = thread.get("project_id")
    if project_id is None:
        return "unassigned"

    project_name = str(thread.get("project_name") or "").strip()
    if project_name.lower() == "imports":
        return f"projects/imports__{project_id}"

    slug = _safe_slug(project_name or f"project-{project_id}")
    return f"projects/{slug}__{project_id}"


def _build_thread_json_payload(
    *,
    thread: dict[str, Any],
    messages: list[dict[str, Any]],
) -> dict[str, Any]:
    metadata = (
        thread.get("metadata")
        if isinstance(thread.get("metadata"), dict)
        else {}
    )
    clean_messages = [
        _build_export_message_payload(message) for message in messages
    ]
    return {
        "id": thread.get("id"),
        "title": thread.get("title"),
        "summary": thread.get("summary") or "",
        "project": {
            "id": thread.get("project_id"),
            "name": thread.get("project_name"),
        },
        "provenance": {
            "import_source": metadata.get("import_source"),
            "import_profile": metadata.get("import_profile"),
            "source_thread_id": metadata.get("source_thread_id"),
            "source_conversation_template_id": metadata.get(
                "source_conversation_template_id"
            ),
            "source_gizmo_id": metadata.get("source_gizmo_id"),
            "source_gizmo_type": metadata.get("source_gizmo_type"),
        },
        "messages": clean_messages,
    }


def _render_markdown(
    *,
    thread: dict[str, Any],
    thread_payload: dict[str, Any],
) -> str:
    provenance = (
        thread_payload.get("provenance")
        if isinstance(thread_payload.get("provenance"), dict)
        else {}
    )
    lines = ["---"]
    lines.append(f"thread_id: {thread_payload.get('id')}")
    lines.append(
        f"title: {json.dumps(str(thread_payload.get('title') or 'Imported Chat'))}"
    )
    lines.append(f"project_id: {thread.get('project_id')}")
    lines.append(
        f"project_name: {json.dumps(str(thread.get('project_name') or ''))}"
    )
    for key in (
        "import_source",
        "import_profile",
        "source_thread_id",
        "source_conversation_template_id",
        "source_gizmo_id",
        "source_gizmo_type",
    ):
        value = provenance.get(key)
        if value is not None:
            lines.append(f"{key}: {json.dumps(str(value))}")
    lines.append("---")
    lines.append("")

    title = str(thread_payload.get("title") or "Imported Chat")
    lines.append(f"# {title}")
    lines.append("")

    for message in thread_payload.get("messages", []):
        role = str(message.get("role") or "message").strip().lower()
        role_label = "Assistant" if role == "tool" else role.title()
        lines.append(f"## {role_label}")
        lines.append(str(message.get("content") or ""))
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"


@router.get(
    "/threads.ndjson",
    summary="Download all of the current user's threads as newline‑delimited JSON",
)
def export_threads(user: AuthenticatedUser = Depends(require_user)):
    """Stream every thread the authenticated user can access in NDJSON format."""
    fetch_fn = getattr(db, "fetch_threads_for_user", None)
    if fetch_fn is None:
        logger.error(
            "Active DB backend %s lacks fetch_threads_for_user; cannot export threads",
            type(db),
        )
        raise HTTPException(
            status_code=500, detail="Thread export not available"
        )

    def generate() -> Iterable[bytes]:
        try:
            for row in fetch_fn(user.id):
                try:
                    yield _serialize_chunk(row)
                except Exception as encode_err:
                    logger.exception(
                        "Failed to encode thread row for user %s: %s",
                        user.id,
                        encode_err,
                    )
        except Exception as stream_err:
            logger.exception(
                "Thread export stream failed for user %s: %s",
                user.id,
                stream_err,
            )
            # Re-raise so the client receives a 500 instead of hanging.
            raise

    try:
        return StreamingResponse(
            generate(),
            media_type="application/x-ndjson",
            headers={
                "Content-Disposition": 'attachment; filename="threads.ndjson"'
            },
        )
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception(
            "Failed to start thread export for user %s: %s", user.id, exc
        )
        raise HTTPException(
            status_code=500, detail="Failed to start export"
        ) from exc


@router.get(
    "/account.zip",
    summary="Download the authenticated user's canonical account export ZIP",
)
def export_account_zip(user: AuthenticatedUser = Depends(require_user)):
    try:
        zip_path = build_account_export_zip(db, user)
    except Exception as exc:
        logger.exception(
            "Failed to build account export zip for user %s: %s",
            user.id,
            exc,
        )
        raise HTTPException(
            status_code=500,
            detail="Failed to build account export",
        ) from exc

    return FileResponse(
        zip_path,
        media_type="application/zip",
        filename=ZIP_FILENAME,
        background=BackgroundTask(_cleanup_export_file, zip_path),
    )


@router.get(
    "/chatgpt.zip",
    summary="Download imported ChatGPT conversations as a project-aware ZIP bundle",
)
def export_chatgpt_zip(
    project_id: int | None = Query(default=None),
    format: Literal["both", "json", "markdown"] = Query(default="both"),
    user: AuthenticatedUser = Depends(require_user),
):
    fetch_threads_fn = getattr(
        db, "fetch_imported_chatgpt_threads_for_user", None
    )
    fetch_messages_fn = getattr(
        db,
        "fetch_imported_chatgpt_messages_for_thread",
        None,
    )
    if fetch_threads_fn is None or fetch_messages_fn is None:
        logger.error(
            "Active DB backend %s lacks ChatGPT export helpers",
            type(db),
        )
        raise HTTPException(
            status_code=500,
            detail="ChatGPT transcript export not available",
        )

    try:
        threads = list(
            fetch_threads_fn(
                user.id,
                project_id=project_id,
            )
        )
    except Exception as exc:
        logger.exception(
            "Failed to fetch imported ChatGPT threads for user %s: %s",
            user.id,
            exc,
        )
        raise HTTPException(
            status_code=500,
            detail="Failed to fetch imported chats",
        ) from exc

    include_json = format in {"both", "json"}
    include_markdown = format in {"both", "markdown"}

    zip_buffer = io.BytesIO()
    seen_paths: set[str] = set()
    exported_messages = 0

    with zipfile.ZipFile(
        zip_buffer, mode="w", compression=zipfile.ZIP_DEFLATED
    ) as archive:
        for thread in threads:
            thread_id = int(thread.get("id") or 0)
            if thread_id <= 0:
                continue

            try:
                messages = list(fetch_messages_fn(thread_id))
            except Exception as exc:
                logger.warning(
                    "Failed to fetch imported messages for thread %s (user=%s): %s",
                    thread_id,
                    user.id,
                    exc,
                )
                continue

            thread_payload = _build_thread_json_payload(
                thread=thread,
                messages=messages,
            )
            exported_messages += len(thread_payload.get("messages") or [])

            project_folder = _build_project_folder(thread)
            title_token = _safe_filename(thread_payload.get("title"))
            source_short = _source_thread_short(thread, messages)
            base_name = f"{title_token}__{source_short}"

            if include_json:
                json_path = _dedupe_zip_path(
                    f"{project_folder}/{base_name}.json",
                    seen_paths,
                )
                archive.writestr(
                    json_path,
                    json.dumps(thread_payload, indent=2, ensure_ascii=False),
                )

            if include_markdown:
                markdown_path = _dedupe_zip_path(
                    f"{project_folder}/{base_name}.md",
                    seen_paths,
                )
                markdown_body = _render_markdown(
                    thread=thread,
                    thread_payload=thread_payload,
                )
                archive.writestr(markdown_path, markdown_body)

        manifest = {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "user_id": user.id,
            "filters": {
                "project_id": project_id,
                "format": format,
            },
            "totals": {
                "threads": len(threads),
                "messages": exported_messages,
            },
        }
        archive.writestr(
            "manifest.json",
            json.dumps(manifest, indent=2, ensure_ascii=False),
        )

    payload = zip_buffer.getvalue()
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    filename = f"chatgpt_export_{timestamp}.zip"
    return Response(
        content=payload,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
