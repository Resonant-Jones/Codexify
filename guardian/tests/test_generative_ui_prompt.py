"""Generative UI emission guidance: gating, wording, and payload shape.

Proves that the model-facing half of the generative UI contract describes a
payload the renderer actually accepts. See
``docs/architecture/generative-ui-contract.md``.
"""

from __future__ import annotations

import json
from typing import Any
import urllib.parse

import pytest

from guardian.cognition import system_prompt_builder
from guardian.cognition.generative_ui_prompt import (
    GENERATIVE_UI_ENV_FLAG,
    GENERATIVE_UI_MARKER_PREFIX,
    build_generative_ui_guidance_block,
    generative_ui_enabled,
)
from guardian.cognition.identity_resolution import ResolvedImprint, ResolvedPersona


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


# ---------------------------------------------------------------------------
# Integration: does the block actually reach the assembled system prompt?
#
# The unit tests above exercise the builder in isolation. These prove the block
# survives prompt assembly, budget, and truncation, which is the seam that
# would silently drop it.
# ---------------------------------------------------------------------------


def _stub_identity(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        system_prompt_builder,
        "resolve_imprint",
        lambda *args, **kwargs: ResolvedImprint(
            source="system_default",
            imprint_id=None,
            user_id="user-1",
            project_id=None,
            guardian_name="Guardian",
            preferred_name="Resonant",
            style="Warm",
            grammar_prefs={},
            metrics={},
            heat_score=None,
        ),
    )
    monkeypatch.setattr(
        system_prompt_builder,
        "resolve_persona",
        lambda *args, **kwargs: ResolvedPersona(
            source="system_default",
            persona_id=None,
            user_id="user-1",
            project_id=None,
            body="Be precise.",
            record_source="system_default",
        ),
    )
    monkeypatch.setattr(
        system_prompt_builder, "get_docs_for", lambda *args, **kwargs: []
    )


def _assemble(monkeypatch: pytest.MonkeyPatch, **kwargs: Any) -> str:
    _stub_identity(monkeypatch)
    system_prompt, _meta = system_prompt_builder.build_guardian_system_prompt(
        user_id="user-1",
        project_id=None,
        depth="normal",
        bundle={},
        **kwargs,
    )
    return system_prompt


def test_assembled_prompt_omits_the_block_when_disabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv(GENERATIVE_UI_ENV_FLAG, raising=False)
    prompt = _assemble(monkeypatch)

    assert GENERATIVE_UI_MARKER_PREFIX not in prompt
    assert "Generative UI (interactive replies)" not in prompt


def test_assembled_prompt_includes_the_block_when_enabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(GENERATIVE_UI_ENV_FLAG, "true")
    prompt = _assemble(monkeypatch)

    assert "Generative UI (interactive replies)" in prompt
    assert f"<!-- {GENERATIVE_UI_MARKER_PREFIX}:PERCENT_ENCODED_JSON -->" in prompt
    # The rest of the prompt is untouched.
    assert "Be precise." in prompt


def test_block_survives_the_default_token_budget(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Scratchpad content is budgeted and truncated.

    A block silently dropped by truncation would make the feature inert while
    every isolated unit test still passed.
    """

    monkeypatch.setenv(GENERATIVE_UI_ENV_FLAG, "true")
    prompt = _assemble(monkeypatch, token_cap=2000)
    assert "Generative UI (interactive replies)" in prompt

    # Even at an unusually tight cap the block must remain reachable, because
    # losing it silently disables the whole feature.
    tight = _assemble(monkeypatch, token_cap=1200)
    assert "Generative UI (interactive replies)" in tight


def test_enabling_does_not_change_the_base_prompt(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv(GENERATIVE_UI_ENV_FLAG, raising=False)
    off = _assemble(monkeypatch)

    monkeypatch.setenv(GENERATIVE_UI_ENV_FLAG, "1")
    on = _assemble(monkeypatch)

    # Additive only: removing the block must reproduce the off prompt exactly.
    assert on.replace(build_generative_ui_guidance_block(), "").strip() == off.strip()