"""Helpers for chat attachment markers embedded in message content."""

from __future__ import annotations

import re
from typing import Any

_ATTACHMENT_MARKER_RE = re.compile(
    r"<!--\s*(cfy-media(?:-src|-name)?):([^>]*?)\s*-->",
    flags=re.IGNORECASE,
)
_EXCESSIVE_BLANK_LINES_RE = re.compile(r"\n{3,}")


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


def render_content_for_inference(content: Any) -> str:
    if not isinstance(content, str):
        return ""

    attachments, text = extract_attachments_and_text(content)
    attachment_lines: list[str] = []

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
    if attachment_lines:
        parts.append("\n".join(attachment_lines))
    if text:
        parts.append(text)
    return "\n\n".join(part for part in parts if part).strip()


__all__ = ["extract_attachments_and_text", "render_content_for_inference"]
