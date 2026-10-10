"""Generative UI emission guidance: gating, wording, and payload shape.

Proves that the model-facing half of the generative UI contract describes a
payload the renderer actually accepts. See
``docs/architecture/generative-ui-contract.md``.
"""

from __future__ import annotations

import json
import urllib.parse

from guardian.cognition.generative_ui_prompt import (
    GENERATIVE_UI_ENV_FLAG,
    GENERATIVE_UI_MARKER_PREFIX,
    build_generative_ui_guidance_block,
    generative_ui_enabled,
)


def test_disabled_by_default() -> None:
    assert generative_ui_enabled({}) is False
    assert build_generative_ui_guidance_block({}) == ""


def test_enables_on_truthy_values_only() -> None:
    for raw in ("1", "true", "TRUE", "yes", "on", "enabled"):
        assert generative_ui_enabled({GENERATIVE_UI_ENV_FLAG: raw}) is True
    for raw in ("0", "false", "no", "off", "", "maybe"):
        assert generative_ui_enabled({GENERATIVE_UI_ENV_FLAG: raw}) is False


def test_guidance_is_present_only_when_enabled() -> None:
    off = build_generative_ui_guidance_block({})
    on = build_generative_ui_guidance_block({GENERATIVE_UI_ENV_FLAG: "true"})
    assert off == ""
    assert "cfy-ui" in on
    assert "Generative UI" in on


def test_guidance_documents_the_marker_shape_models_must_emit() -> None:
    block = build_generative_ui_guidance_block({GENERATIVE_UI_ENV_FLAG: "true"})
    assert f"<!-- {GENERATIVE_UI_MARKER_PREFIX}:PERCENT_ENCODED_JSON -->" in block
    # Both artifact kinds and both registered component ids must be named.
    assert '"kind":"native"' in block
    assert '"kind":"sandbox"' in block
    assert "chart.bar" in block
    assert "table.rows" in block
    assert '"version":1' in block


def test_guidance_states_the_real_sandbox_limits() -> None:
    """The block must match what the frame actually enforces.

    If these drift, the model writes code that silently fails at runtime.
    """

    block = build_generative_ui_guidance_block({GENERATIVE_UI_ENV_FLAG: "true"})
    assert "No `fetch`" in block
    assert "No `eval` and no `new Function`" in block
    assert "window.cfyUI.sendPrompt" in block
    assert "never sends anything" in block
    # openLink is not implemented, so guidance must not imply it exists.
    assert "openLink" not in block


def test_documented_examples_decode_to_the_shapes_they_claim() -> None:
    """Each worked example in the guidance must be valid JSON of the right kind.

    Guards against shipping an example that teaches a payload the renderer
    would reject.
    """

    block = build_generative_ui_guidance_block({GENERATIVE_UI_ENV_FLAG: "true"})
    examples = [
        chunk
        for chunk in block.split("`")
        if chunk.startswith('{"version":1')
    ]
    assert len(examples) >= 2, "expected a native and a sandbox worked example"

    kinds = set()
    for example in examples:
        payload = json.loads(example)
        assert payload["version"] == 1
        kinds.add(payload["kind"])
        if payload["kind"] == "native":
            assert payload["component"] in {"chart.bar", "table.rows"}
            assert isinstance(payload["props"], dict)
        else:
            assert isinstance(payload["html"], str) and payload["html"]

    assert kinds == {"native", "sandbox"}


def test_percent_encoding_excludes_the_html_comment_terminator() -> None:
    """Percent-encoded JSON must be safe inside an HTML comment."""

    payload = {
        "version": 1,
        "kind": "sandbox",
        "html": "<button>go</button>-->",
        "title": "Tricky > title",
    }
    encoded = urllib.parse.quote(json.dumps(payload, separators=(",", ":")))
    assert ">" not in encoded
    assert "-->" not in encoded
    assert json.loads(urllib.parse.unquote(encoded)) == payload