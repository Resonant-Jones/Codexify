"""Helpers for chat attachment markers embedded in message content."""

from __future__ import annotations

import base64
import json
import re
from typing import Any

_ATTACHMENT_MARKER_RE = re.compile(
    r"<!--\s*(cfy-media(?:-src|-name)?):([^>]*?)\s*-->",
    flags=re.IGNORECASE,
)
_DOC_TILE_MARKER_RE = re.compile(
    r"<!--\s*cfy-doc-tile:([^>]*?)\s*-->",
    flags=re.IGNORECASE,
)
_DOC_CONTENT_BLOCK_RE = re.compile(
    r"<!--\s*cfy-doc-content:start:([^>]*?)\s*-->\s*([\s\S]*?)\s*<!--\s*cfy-doc-content:end:\1\s*-->",
    flags=re.IGNORECASE,
)
_EXCESSIVE_BLANK_LINES_RE = re.compile(r"\n{3,}")


def _decode_base64url_json(raw: str) -> dict[str, Any] | None:
    value = (raw or "").strip()
    if not value:
        return None
    try:
        padded = value.replace("-", "+").replace("_", "/")
        padded += "=" * ((4 - len(padded) % 4) % 4)
        decoded = base64.b64decode(padded).decode("utf-8")
        payload = json.loads(decoded)
        return payload if isinstance(payload, dict) else None
    except Exception:
        return None


def extract_attachments_and_text(
    content: str,
) -> tuple[list[dict[str, str | None]], str]:
    attachments: list[dict[str, str | None]] = []
    current: dict[str, str | None] | None = None

    for match in _ATTACHMENT_MARKER_RE.finditer(content or ""):
        marker_type = (match.group(1) or "").strip().lower()
        value = (match.group(2) or "").strip()

        if marker_type == "cfy-media":
            kind_raw, _, id_raw = value.partition(":")
            kind = kind_raw.strip().lower()
            if kind not in {"image", "document"}:
                current = None
                continue
            current = {
                "kind": kind,
                "id": id_raw.strip() or None,
                "src": None,
                "name": None,
            }
            attachments.append(current)
            continue

        target = current or (attachments[-1] if attachments else None)
        if target is None or not value:
            continue

        if marker_type == "cfy-media-src":
            target["src"] = value
        elif marker_type == "cfy-media-name":
            target["name"] = value

    text = _ATTACHMENT_MARKER_RE.sub("", content or "").strip()
    text = _EXCESSIVE_BLANK_LINES_RE.sub("\n\n", text)
    return attachments, text.strip()


def _extract_document_context(
    content: str,
) -> tuple[list[dict[str, str | None]], list[dict[str, str]], str]:
    tiles: list[dict[str, str | None]] = []
    blocks: list[dict[str, str]] = []
    stripped = content or ""

    def _replace_tile(match: re.Match[str]) -> str:
        payload = _decode_base64url_json(match.group(1) or "")
        if not payload:
            return ""
        doc_id = str(payload.get("id") or "").strip()
        if not doc_id:
            return ""
        tile = {
            "id": doc_id,
            "title": str(payload.get("title") or "").strip() or "Untitled",
            "preview": str(payload.get("preview") or "").strip() or None,
            "ext": str(payload.get("ext") or "").strip() or None,
        }
        tiles.append(tile)
        return ""

    stripped = _DOC_TILE_MARKER_RE.sub(_replace_tile, stripped)

    def _replace_block(match: re.Match[str]) -> str:
        payload = _decode_base64url_json(match.group(1) or "")
        if not payload:
            return ""
        doc_id = str(payload.get("id") or "").strip()
        if not doc_id:
            return ""
        block_content = str(match.group(2) or "").strip()
        blocks.append({"id": doc_id, "content": block_content})
        return ""

    stripped = _DOC_CONTENT_BLOCK_RE.sub(_replace_block, stripped)
    stripped = _EXCESSIVE_BLANK_LINES_RE.sub("\n\n", stripped)
    return tiles, blocks, stripped.strip()


def render_content_for_inference(content: Any) -> str:
    if not isinstance(content, str):
        return ""

    tiles, blocks, stripped = _extract_document_context(content)
    attachments, text = extract_attachments_and_text(stripped)
    attachment_lines: list[str] = []
    block_by_id = {block["id"]: block["content"] for block in blocks}
    tile_ids = {tile["id"] for tile in tiles}

    for attachment in attachments:
        kind = str(attachment.get("kind") or "").strip().lower()
        if kind not in {"image", "document"}:
            continue
        label = (
            str(attachment.get("name") or "").strip()
            or str(attachment.get("id") or "").strip()
            or f"{kind} attachment"
        )
        prefix = "Attached document" if kind == "document" else "Attached image"
        attachment_lines.append(f"{prefix}: {label}")

    parts = []
    document_lines: list[str] = []
    for tile in tiles:
        label = (
            str(tile.get("title") or "").strip()
            or str(tile.get("preview") or "").strip()
            or str(tile.get("id") or "").strip()
            or "document"
        )
        block = block_by_id.get(str(tile.get("id") or "").strip())
        if block:
            document_lines.append(f"Referenced document: {label}\n{block}")
        elif tile.get("preview"):
            document_lines.append(
                f"Referenced document: {label}\n{tile['preview']}"
            )
        else:
            document_lines.append(f"Referenced document: {label}")
    for block_id, block_content in block_by_id.items():
        if block_id in tile_ids:
            continue
        if block_content:
            document_lines.append(block_content)

    if attachment_lines:
        parts.append("\n".join(attachment_lines))
    if document_lines:
        parts.append("\n\n".join(document_lines))
    if text:
        parts.append(text)
    return "\n\n".join(part for part in parts if part).strip()


__all__ = ["extract_attachments_and_text", "render_content_for_inference"]
