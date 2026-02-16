from __future__ import annotations

import json
import logging
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from guardian.codexify import create_notion_database_from_records
from guardian.core.event_graph import get_event_writer
from guardian.export_engine import (
    export_records,
    export_to_gdrive,
    import_from_gdrive,
    import_from_icloud,
)
from guardian.integrations.google_drive import build_drive_service
from guardian.integrations.google_oauth import ensure_oauth_credentials

router = APIRouter(prefix="/codexify", tags=["codexify"])
logger = logging.getLogger(__name__)


class GDriveExportRequest(BaseModel):
    records: list[dict[str, Any]]
    format: str = "md"
    # Accept either explicit folder ID or a full folder URL. If both are provided, `folder` (ID) wins
    folder: str | None = None
    folder_url: str | None = None
    # Return clickable links for created items
    return_links: bool = False
    dry_run: bool = False
    share_anyone_with_link: bool = False
    front_matter: dict[str, Any] | None = None


class GDriveImportRequest(BaseModel):
    query: str | None = None
    folder: str | None = None


class ICloudImportRequest(BaseModel):
    pattern: str = "*"
    subfolder: str = "Guardian Exports"


class SaveEntryRequest(BaseModel):
    title: str
    body: str = ""
    format: str = "md"
    folder: str | None = None
    folder_url: str | None = None
    return_links: bool = True
    dry_run: bool = False
    share_anyone_with_link: bool = False
    front_matter: dict[str, Any] | None = None


class NotionImportRequest(BaseModel):
    records: list[dict]
    parent_id: str
    token: str
    db_title: str | None = None
    with_template: bool = True


# --- Helpers ---
_FILE_LINK = "https://drive.google.com/file/d/{id}/view"
_FOLDER_LINK = "https://drive.google.com/drive/folders/{id}"
_FOLDER_RE = re.compile(
    r"(?:/folders/|/drive/folders/|[?&]id=)([A-Za-z0-9_-]{10,})"
)


def _normalize_folder_id(folder_or_url: str | None) -> str | None:
    if not folder_or_url:
        return None
    s = folder_or_url.strip()
    # Accept bare IDs directly
    if re.fullmatch(r"[A-Za-z0-9_-]{10,}", s):
        return s
    # Tolerate /u/{n}/ variants in the URL
    s = re.sub(r"/u/\d+/", "/", s)
    m = (
        re.search(_FOLDER_RE, s)
        if hasattr(re, "search")
        else _FOLDER_RE.search(s)
    )
    return m.group(1) if m else None


def _raise_helpful_drive_error(e: Exception):
    """Map Google Drive API errors to helpful messages for the client."""
    try:
        from googleapiclient.errors import HttpError  # type: ignore
    except Exception:
        HttpError = None  # type: ignore

    status = None
    if HttpError and isinstance(e, HttpError):
        try:
            status = int(getattr(e, "status_code", None) or getattr(e, "resp", {}).status)  # type: ignore[attr-defined]
        except Exception:
            status = None

    # Fallback: attempt to glean from text
    msg = str(e)
    if status is None:
        if "403" in msg:
            status = 403
        elif "404" in msg:
            status = 404

    if status == 403:
        raise HTTPException(
            status_code=400,
            detail="Permission denied for the target Drive folder. Ensure the OAuth user or service account has access. If using OAuth, try re-running /codexify/oauth-begin to refresh consent and token.",
        )
    if status == 404:
        raise HTTPException(
            status_code=400,
            detail="Invalid or missing Drive folder. Verify the folder ID/URL and that it exists.",
        )
    # Unknown error: surface original message as 500
    raise HTTPException(status_code=500, detail=msg)


def _looks_like_service_account(json_path: Path) -> bool:
    try:
        data = json.loads(json_path.read_text())
        return isinstance(data, dict) and data.get("type") == "service_account"
    except Exception:
        return False


def _extract_drive_id(url: str) -> str | None:
    """
    Extract a Drive file/folder id from common URL shapes:
      - https://drive.google.com/drive/folders/<FOLDER_ID>
      - https://drive.google.com/file/d/<FILE_ID>/view
      - https://drive.google.com/open?id=<ID>
    Returns None if no id can be parsed.
    """
    if not url:
        return None
    m = re.search(r"/file/d/([A-Za-z0-9_-]{10,})", url)
    if m:
        return m.group(1)
    m = re.search(r"/folders/([A-Za-z0-9_-]{10,})", url)
    if m:
        return m.group(1)
    m = re.search(r"[?&]id=([A-Za-z0-9_-]{10,})", url)
    if m:
        return m.group(1)
    return None


def _with_links(result: Any) -> dict[str, Any]:
    """
    Normalize exporter result into { files: [{id, webViewLink}], count }.
    - If result items already include webViewLink / id, keep them.
    - Otherwise, construct a web link from id using a generic template.
    """
    files: list[dict[str, Any]] = []
    # Accept a variety of shapes: list[str], list[dict], dict with 'files'
    items = None
    if isinstance(result, dict) and "files" in result:
        items = result["files"]
    else:
        items = result
    if not isinstance(items, list):
        items = [items] if items is not None else []
    for it in items:
        if isinstance(it, dict):
            _id = it.get("id")
            _link = it.get("webViewLink") or (
                _FILE_LINK.format(id=_id) if _id else None
            )
            base = {
                k: v for k, v in it.items() if k not in ("id", "webViewLink")
            }
            files.append({"id": _id, "webViewLink": _link, **base})
        else:
            # assume string id
            _id = str(it)
            files.append({"id": _id, "webViewLink": _FILE_LINK.format(id=_id)})
    return {"files": files, "count": len(files)}


def _coerce_int(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _emit_codex_result_event(req: SaveEntryRequest, result: Any) -> None:
    links = _with_links(result)
    files = links.get("files") or []
    first = files[0] if files else {}
    codex_entry_id = (
        (first or {}).get("id")
        or (first or {}).get("name")
        or datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    )

    front_matter = req.front_matter or {}
    source_thread_id = _coerce_int(
        front_matter.get("source_thread_id") or front_matter.get("thread_id")
    )
    source_message_id = _coerce_int(
        front_matter.get("source_message_id") or front_matter.get("message_id")
    )

    parent_event_id = None
    if source_thread_id is not None:
        parent_event_id = get_event_writer().get_latest_event_id(
            thread_id=source_thread_id,
            event_type="thread.update",
        )

    idempotency_key = f"codex.result:{codex_entry_id}:{source_thread_id or 'na'}:{source_message_id or 'na'}"
    get_event_writer().emit_event(
        event_type="codex.result",
        actor_user_id=None,
        project_id=_coerce_int(front_matter.get("project_id")),
        thread_id=source_thread_id,
        entity_type="codex",
        entity_id=str(codex_entry_id),
        payload={
            "codex_entry_id": codex_entry_id,
            "source_thread_id": source_thread_id,
            "source_message_id": source_message_id,
            "format": req.format,
            "result_count": links.get("count"),
        },
        parent_event_id=parent_event_id,
        idempotency_key=idempotency_key,
    )


@router.get("/folder-id")
def resolve_folder_id(url: str):
    """Utility endpoint: resolve folder/file id from a Google Drive URL."""
    _id = _extract_drive_id(url)
    if not _id:
        raise HTTPException(
            status_code=400,
            detail="Could not parse an id from the provided URL.",
        )
    return {"id": _id, "webLink": _FOLDER_LINK.format(id=_id)}


@router.get("/oauth-status")
def oauth_status():
    creds = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
    token = os.environ.get("GDRIVE_OAUTH_TOKEN")
    if not creds and not token:
        return {"status": "missing_secret"}
    if token and not creds:
        return {"status": "token_only", "token": token}

    cpath = Path(creds) if creds else None
    if cpath and cpath.exists() and _looks_like_service_account(cpath):
        return {"status": "service_account", "credentials": str(cpath)}

    # Assume OAuth client secret style
    if token:
        tpath = Path(token)
    else:
        repo_root = Path(__file__).resolve().parents[2]
        tpath = repo_root / "secrets" / "token.json"
    if tpath.exists():
        return {
            "status": "oauth_ready",
            "credentials": creds,
            "token": str(tpath),
        }
    return {
        "status": "oauth_no_token",
        "credentials": creds,
        "token": str(tpath),
    }


@router.post("/oauth-begin")
def oauth_begin():
    """
    Kick off the OAuth browser flow and persist token.json in secrets/.
    Returns token path on success.
    """
    try:
        path = ensure_oauth_credentials()
        return {"ok": True, "token": path}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


def _service_account_email(p: Path) -> str | None:
    try:
        data = json.loads(p.read_text())
        if isinstance(data, dict):
            return data.get("client_email")
    except Exception:
        pass
    return None


@router.get("/service-account")
def service_account_info():
    """Return service account email if configured via GOOGLE_APPLICATION_CREDENTIALS."""
    creds = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
    if not creds:
        return {"status": "missing_credentials"}
    cpath = Path(creds)
    if not cpath.exists():
        return {"status": "missing_credentials", "credentials": creds}
    if not _looks_like_service_account(cpath):
        return {"status": "not_service_account", "credentials": str(cpath)}
    email = _service_account_email(cpath)
    resp: dict[str, Any] = {
        "status": "service_account",
        "credentials": str(cpath),
    }
    if email:
        resp["email"] = email
    return resp


@router.post("/export-gdrive")
def export_gdrive(req: GDriveExportRequest):
    try:
        # Resolve folder: accept either raw ID or URL (including /u/{n}/ variants)
        folder_id = req.folder or _normalize_folder_id(
            getattr(req, "folder_url", None)
        )
        # Apply default folder from env if none provided
        if not folder_id:
            default_folder = os.environ.get("CODEXIFY_DEFAULT_FOLDER")
            if default_folder:
                folder_id = (
                    _normalize_folder_id(default_folder) or default_folder
                )
        if getattr(req, "folder_url", None) and not folder_id:
            raise HTTPException(
                status_code=400,
                detail="Invalid folder_url: could not parse an id.",
            )
        # Dry-run: validate only
        if req.dry_run:
            count = len(req.records or [])
            return {
                "ok": True,
                "dry_run": True,
                "records": count,
                "format": req.format,
                "folder": folder_id or req.folder,
                "folder_url": getattr(req, "folder_url", None),
            }
        # Ensure OAuth token exists if using OAuth
        if os.environ.get("GOOGLE_APPLICATION_CREDENTIALS"):
            try:
                ensure_oauth_credentials()
            except Exception as e:
                raise HTTPException(
                    status_code=400, detail=f"OAuth setup failed: {e}"
                )
        # Real call: build Drive service explicitly
        service = build_drive_service(logger=logger)
        # Optional front matter for md batch export: prepend once at top
        if req.format == "md" and req.front_matter:
            import yaml

            fm = (
                "---\n"
                + yaml.dump(req.front_matter, sort_keys=False).strip()
                + "\n---\n\n"
            )
            body = export_records(req.records, req.format)
            content = fm + body
        else:
            content = None
        share_flag = req.share_anyone_with_link or (
            os.environ.get("CODEXIFY_SHARE_ANYONE", "").strip().lower()
            in ("1", "true", "yes", "on")
        )
        try:
            result = export_to_gdrive(
                req.records,
                format=req.format,
                folder_id=folder_id,
                service=service,
                share_anyone=share_flag,
                content=content,
            )
        except Exception as e:
            _raise_helpful_drive_error(e)
        if req.return_links:
            enriched = _with_links(result)
            # Lightweight server-side logging of exported file URLs
            if not req.dry_run:
                try:
                    urls = [
                        f.get("webViewLink")
                        for f in enriched.get("files", [])
                        if f.get("webViewLink")
                    ]
                    if urls:
                        logger.info(
                            "Exported to Google Drive:\n%s", "\n".join(urls)
                        )
                except Exception:
                    pass
            return {"ok": True, **enriched}
        # When return_links is False, derive URLs just for logging without changing response payload
        if not req.dry_run:
            try:
                tmp = _with_links(result)
                urls = [
                    f.get("webViewLink")
                    for f in tmp.get("files", [])
                    if f.get("webViewLink")
                ]
                if urls:
                    logger.info(
                        "Exported to Google Drive:\n%s", "\n".join(urls)
                    )
            except Exception:
                pass
        return {"ok": True, "result": result}
    except HTTPException:
        raise
    except HTTPException:
        # Propagate mapped HTTP errors
        raise
    except HTTPException:
        raise
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/import-gdrive")
def import_gdrive(req: GDriveImportRequest):
    try:
        files = import_from_gdrive(query=req.query, folder_id=req.folder)
        return {"files": files}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/import-icloud")
def import_icloud(req: ICloudImportRequest):
    try:
        files = import_from_icloud(req.pattern, req.subfolder)
        return {"files": files}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/create")
def codexify_create(req: NotionImportRequest):
    try:
        db_id = create_notion_database_from_records(
            req.records,
            req.parent_id,
            req.token,
            db_title=req.db_title,
            with_template=req.with_template,
        )
        return {"db_id": db_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/save-entry")
def save_entry(req: SaveEntryRequest):
    """Preview and optionally export a single entry to Google Drive."""
    # Build single-record payload
    records: list[dict[str, Any]] = [{"title": req.title, "body": req.body}]
    # Preview formatted content
    try:
        if req.format == "md" and req.front_matter:
            import yaml

            fm = (
                "---\n"
                + yaml.dump(req.front_matter, sort_keys=False).strip()
                + "\n---\n\n"
            )
            preview = fm + (req.body or "")
        else:
            preview = export_records(records, req.format)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Preview failed: {e}")

    folder_id = req.folder or _normalize_folder_id(
        getattr(req, "folder_url", None)
    )
    if not folder_id:
        default_folder = os.environ.get("CODEXIFY_DEFAULT_FOLDER")
        if default_folder:
            folder_id = _normalize_folder_id(default_folder) or default_folder
    if getattr(req, "folder_url", None) and not folder_id:
        raise HTTPException(
            status_code=400, detail="Invalid folder_url: could not parse an id."
        )

    if req.dry_run:
        return {
            "ok": True,
            "dry_run": True,
            "preview": preview,
            "format": req.format,
            "folder": folder_id or req.folder,
            "folder_url": getattr(req, "folder_url", None),
        }

    if os.environ.get("GOOGLE_APPLICATION_CREDENTIALS"):
        try:
            ensure_oauth_credentials()
        except Exception as e:
            raise HTTPException(
                status_code=400, detail=f"OAuth setup failed: {e}"
            )

    try:
        service = build_drive_service(logger=logger)

        # Build a friendly filename: YYYY-MM-DD_<sanitized-title>.<ext>
        def _sanitize(name: str) -> str:
            name = (name or "note").strip()
            out = []
            for ch in name:
                if ch.isalnum() or ch in ("-", "_"):
                    out.append(ch)
                elif ch.isspace():
                    out.append("_")
            safe = "".join(out).strip("._-") or "note"
            return safe[:80]

        ext = req.format if req.format in ("md", "txt", "html") else "md"
        date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        time_str = datetime.now(timezone.utc).strftime("%H-%M-%S")
        slug = _sanitize(req.title)
        tmpl = os.environ.get("CODEXIFY_FILENAME_TEMPLATE", "")
        if tmpl:
            try:
                filename = tmpl.format(
                    date=date_str, time=time_str, slug=slug, ext=ext
                )
            except Exception:
                filename = f"{date_str}_{slug}.{ext}"
        else:
            filename = f"{date_str}_{slug}.{ext}"

        share_flag = req.share_anyone_with_link or (
            os.environ.get("CODEXIFY_SHARE_ANYONE", "").strip().lower()
            in ("1", "true", "yes", "on")
        )
        if req.format == "md" and req.front_matter:
            import yaml

            fm = (
                "---\n"
                + yaml.dump(req.front_matter, sort_keys=False).strip()
                + "\n---\n\n"
            )
            content = fm + (req.body or "")
        else:
            content = None
        try:
            result = export_to_gdrive(
                records,
                format=req.format,
                filename=filename,
                folder_id=folder_id,
                service=service,
                share_anyone=share_flag,
                content=content,
            )
        except Exception as e:
            _raise_helpful_drive_error(e)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    try:
        _emit_codex_result_event(req, result)
    except Exception:
        logger.debug(
            "[codex.result] event graph emit failed",
            exc_info=True,
        )

    if req.return_links:
        enriched = _with_links(result)
        return {"ok": True, "preview": preview, **enriched}
    return {"ok": True, "preview": preview, "result": result}
