from __future__ import annotations

import base64
import json

from guardian.core.chat_attachments import render_content_for_inference


def _b64url_json(payload: dict[str, str]) -> str:
    raw = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def test_render_content_for_inference_inlines_document_context() -> None:
    tile_payload = _b64url_json(
        {
            "id": "doc-1",
            "title": "Project Spec",
            "preview": "Short excerpt",
            "ext": "md",
        }
    )
    content_payload = _b64url_json({"id": "doc-1"})
    content = (
        "<!-- cfy-media:document:doc-2 -->\n"
        "<!-- cfy-media-name:diagram.pdf -->\n"
        f"<!-- cfy-doc-tile:{tile_payload} -->\n"
        f"<!-- cfy-doc-content:start:{content_payload} -->\n"
        "Full document body\n"
        f"<!-- cfy-doc-content:end:{content_payload} -->\n"
        "Please review this."
    )

    rendered = render_content_for_inference(content)

    assert rendered.startswith("Attached document: diagram.pdf")
    assert "Referenced document: Project Spec" in rendered
    assert "Full document body" in rendered
    assert rendered.endswith("Please review this.")
    assert "cfy-doc-tile" not in rendered
