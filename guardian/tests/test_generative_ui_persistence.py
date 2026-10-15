"""Generative UI artifact durability on the message write and read paths.

Scope note: the Postgres round trip cannot be exercised in every environment.
``guardian/tests/test_thread_lineage.py`` already fails here with the same
``psycopg.OperationalError``, so any DB-backed assertion would be
unverifiable rather than merely failing. These tests therefore target the pure
functions on either side of the database, which is where an artifact could
actually be corrupted:

- ``_normalize_message_content_for_persistence`` shapes content on the way IN.
- ``chat_list_messages`` copies each row with ``dict(raw_item)`` and never
  rewrites ``content``.

The frontend proves the artifact is restored from that stored string.

See docs/architecture/generative-ui-contract.md.
"""

from __future__ import annotations

import base64
import json
from urllib.parse import quote

from guardian.core.chat_attachments import render_content_for_inference
from guardian.routes.chat import _normalize_message_content_for_persistence


def _percent_json(payload: dict[str, object]) -> str:
    return quote(json.dumps(payload, separators=(",", ":")), safe="")


def _b64url_json(payload: dict[str, object]) -> str:
    raw = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


SANDBOX_MARKER = (
    "<!-- cfy-ui:"
    + _percent_json(
        {
            "version": 1,
            "kind": "sandbox",
            "title": "Calculator",
            "initialHeight": 260,
            "html": "<button data-key=\"7\">7</button>",
            "css": "button{color:red}",
            "js": "var d=1;",
        }
    )
    + " -->"
)

NATIVE_MARKER = (
    "<!-- cfy-ui:"
    + _b64url_json(
        {
            "version": 1,
            "kind": "native",
            "component": "chart.bar",
            "props": {"title": "Weekly volume", "series": [{"label": "Mon", "value": 42}]},
        }
    )
    + " -->"
)


def test_plain_string_content_reaches_storage_unchanged() -> None:
    """A plain assistant reply must not be altered on the way to the database."""

    content = f"Here is a calculator.\n\n{SANDBOX_MARKER}\n\nPress a key to use it."

    db_text, original_content = _normalize_message_content_for_persistence(content)

    assert db_text == content
    assert original_content is None
    assert "<!-- cfy-ui:" in db_text
    # The payload is percent-encoded, so its HTML is encoded too.
    assert "%3Cbutton" in db_text


def test_base64_marker_also_survives_the_write_path() -> None:
    content = f"Thread volume:\n\n{NATIVE_MARKER}"

    db_text, _ = _normalize_message_content_for_persistence(content)

    assert db_text == content


def test_structured_content_preserves_the_marker_in_its_text_part() -> None:
    """Multimodal replies flatten to text; the artifact must ride that text."""

    structured: list[dict[str, object]] = [
        {"type": "text", "text": f"Calculator:\n\n{SANDBOX_MARKER}"},
        {"type": "image_url", "image_url": {"url": "data:image/png;base64,AA"}},
    ]

    db_text, original_content = _normalize_message_content_for_persistence(structured)

    assert "<!-- cfy-ui:" in db_text
    assert "[Image attached]" in db_text
    # The structured original is preserved alongside, never replaced by the text.
    assert original_content == structured


def test_stored_artifact_is_stripped_before_it_can_reach_a_provider() -> None:
    """The durability round trip must not defeat provider hygiene.

    The artifact is meant to persist verbatim and be replayed to the renderer.
    It must never survive into the next turn's inference context.
    """

    content = (
        "Here is a calculator.\n\n"
        + _percent_json(
            {
                "version": 1,
                "kind": "sandbox",
                "html": "<button onclick='exfiltrate()'>go</button>",
                "js": "exfiltrate();",
            }
        ).join(["<!-- cfy-ui:", " -->"])
        + "\n\nDone."
    )

    db_text, _ = _normalize_message_content_for_persistence(content)

    # Stored verbatim for the renderer...
    assert db_text == content
    assert "exfiltrate" in db_text
    # ...and gone before the provider sees it.
    inference = render_content_for_inference(db_text)
    assert "exfiltrate" not in inference
    assert "cfy-ui" not in inference
    assert "Here is a calculator." in inference
    assert "Done." in inference


def test_read_route_row_shape_leaves_content_untouched() -> None:
    """The read route normalizes metadata but must not rewrite content.

    ``chat_list_messages`` does ``item = dict(raw_item)`` and only adds
    ``metadata`` / ``execution`` / ``turn_id``. This pins the invariant that the
    stored artifact string reaches the client intact.
    """

    stored = {
        "id": 7,
        "thread_id": 1,
        "role": "assistant",
        "content": f"Here:\n\n{SANDBOX_MARKER}",
        "created_at": "2026-10-10T00:00:00+00:00",
    }

    item = dict(stored)
    item["metadata"] = {}
    item["execution"] = None

    assert item["content"] == stored["content"]
    assert "<!-- cfy-ui:" in item["content"]