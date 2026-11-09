"""Serve uploaded file bytes after the caller's access has been checked."""

from pathlib import Path
from urllib.parse import unquote

from fastapi import HTTPException
from fastapi.responses import FileResponse

from guardian.core.media_signing import extract_media_path

PRIVATE_DOCUMENT_HEADERS = {
    "Cache-Control": "private, no-store",
    "X-Content-Type-Options": "nosniff",
}
DOCUMENT_MEDIA_PREFIX = "/media/documents/"
INLINE_DOCUMENT_TYPES = {"application/pdf", "text/plain", "text/markdown"}


def resolve_media_file(root: Path, file_path: str) -> Path:
    candidate = (root / file_path).resolve()
    if not candidate.is_relative_to(root):
        raise HTTPException(status_code=403, detail="Invalid media path")
    if not candidate.is_file():
        raise HTTPException(status_code=404, detail="Media not found")
    return candidate


def document_media_path(src_url: str) -> str:
    path = unquote(extract_media_path(src_url))
    if not path.startswith(DOCUMENT_MEDIA_PREFIX):
        return ""
    return path


def deliver_document(document, root: Path) -> FileResponse:
    path = document_media_path(document.src_url)
    if not path:
        raise HTTPException(status_code=404, detail="Document file unavailable")
    return FileResponse(
        resolve_media_file(root, path.removeprefix("/media/")),
        filename=document.filename,
        media_type="application/octet-stream",
        headers=PRIVATE_DOCUMENT_HEADERS,
    )
