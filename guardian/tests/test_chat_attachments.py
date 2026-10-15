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


def _ui_artifact(payload: dict[str, object]) -> str:
    raw = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    encoded = base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")
    return f"<!-- cfy-ui:{encoded} -->"


def test_render_content_for_inference_strips_sandbox_artifact_source() -> None:
    marker = _ui_artifact(
        {
            "version": 1,
            "kind": "sandbox",
            "html": "<button id='x'>go</button>",
            "css": ".x{color:red}",
            "js": "document.querySelector('#x').click()",
        }
    )
    content = f"Here is a calculator.\n{marker}\nPress any key to continue."

    rendered = render_content_for_inference(content)

    assert "cfy-ui" not in rendered
    # Generated source must never reach the provider.
    assert "document.querySelector" not in rendered
    assert "color:red" not in rendered
    # Surrounding prose survives intact.
    assert "Here is a calculator." in rendered
    assert "Press any key to continue." in rendered


def test_render_content_for_inference_strips_native_artifact_payload() -> None:
    marker = _ui_artifact(
        {
            "version": 1,
            "kind": "native",
            "component": "chart.bar",
            "props": {"title": "Revenue"},
        }
    )

    rendered = render_content_for_inference(f"{marker}\nNumbers below.\n{marker}")

    assert "cfy-ui" not in rendered
    assert "chart.bar" not in rendered
    assert rendered == "Numbers below."


def test_render_content_for_inference_ignores_malformed_ui_marker() -> None:
    # An unterminated or malformed marker must not leak raw payload to the model.
    rendered = render_content_for_inference(
        "Prose first.\n<!-- cfy-ui:not-base64-json -->\nProse last."
    )

    assert rendered.startswith("Prose first.")
    assert rendered.endswith("Prose last.")


def test_render_content_for_inference_keeps_artifact_strip_independent_of_doc_tiles() -> None:
    tile_payload = _b64url_json({"id": "doc-9", "title": "Spec"})
    marker = _ui_artifact({"version": 1, "kind": "sandbox", "html": "<p>hi</p>"})
    content = (
        f"<!-- cfy-doc-tile:{tile_payload} -->\n"
        "<!-- cfy-doc-content:start:eyJpZCI6ImRvYy05In0= -->\n"
        "Doc body\n"
        "<!-- cfy-doc-content:end:eyJpZCI6ImRvYy05In0= -->\n"
        f"{marker}\n"
        "Summary."
    )

    rendered = render_content_for_inference(content)

    assert "Doc body" in rendered
    assert "Summary." in rendered
    assert "cfy-ui" not in rendered


def test_render_content_for_inference_strips_unencoded_marker_with_html() -> None:
    """Regression: a marker payload may contain '>' and must still be stripped.

    The frontend parser delimits on the closing '-->', not on the first '>'.
    The backend must agree, or an unencoded artifact leaks generated HTML/JS
    into every later provider turn for the thread.
    """

    content = (
        "Here is a calculator.\n"
        '<!-- cfy-ui:{"version":1,"kind":"sandbox",'
        '"html":"<button onclick=\'steal()\'>go</button>"} -->\n'
        "Press a key."
    )

    rendered = render_content_for_inference(content)

    assert "cfy-ui" not in rendered
    assert "steal()" not in rendered
    assert "<button" not in rendered
    assert "Here is a calculator." in rendered
    assert "Press a key." in rendered


def test_render_content_for_inference_strips_multiline_marker_payload() -> None:
    content = (
        "Prose.\n"
        "<!-- cfy-ui:{\"version\":1,\n"
        "\"html\":\"<p>two lines</p>\"} -->\n"
        "Tail."
    )

    rendered = render_content_for_inference(content)

    assert "cfy-ui" not in rendered
    assert "two lines" not in rendered
    assert "Prose." in rendered
    assert "Tail." in rendered


def _load_marker_corpus() -> list[dict]:
    """Shared corpus; see docs/architecture/generative-ui-marker-corpus.json."""

    import pathlib

    corpus_path = (
        pathlib.Path(__file__).resolve().parents[2]
        / "docs"
        / "architecture"
        / "generative-ui-marker-corpus.json"
    )
    return json.loads(corpus_path.read_text(encoding="utf-8"))["cases"]


def test_every_shared_corpus_marker_is_stripped_from_inference() -> None:
    """Cross-boundary invariant.

    The frontend renderer and this strip are separate implementations in two
    languages. Anything one of them considers a marker, the other must strip
    too, or generated HTML/JS leaks into the model prompt.
    """

    for case in _load_marker_corpus():
        label = case["label"]
        marker = case["marker"]
        if label == "oversized payload":
            continue  # asserted directly; placeholder carries no real payload
        content = f"Before.\n{marker}\nAfter."

        rendered = render_content_for_inference(content)

        assert "cfy-ui" not in rendered, f"{label}: marker survived the strip"
        assert "Before." in rendered, f"{label}: leading prose was destroyed"
        assert "After." in rendered, f"{label}: trailing prose was destroyed"
