"""Generative UI emission guidance for the Guardian system prompt.

This is the model-facing half of the generative UI contract. The rendering
half lives in the frontend; the wire format is shared. See
``docs/architecture/generative-ui-contract.md``.

The block is emitted only when the operator has enabled the feature. It
instructs the model to emit a structured marker that the chat renderer
recognizes. Generated code is untrusted and is executed inside an isolated
frame; this block describes what that frame actually permits, so the model does
not write code that silently fails.

Provider-neutral by design: it rides the ordinary system prompt, so it works
with every user-selected inference provider rather than only the providers
served by the tool-exposure rail.
"""

from __future__ import annotations

import os

GENERATIVE_UI_ENV_FLAG = "GUARDIAN_GENERATIVE_UI"
_TRUTHY = {"1", "true", "yes", "on", "enabled"}

GENERATIVE_UI_MARKER_PREFIX = "cfy-ui"

# Kept deliberately compact. This competes for the system-prompt token budget.
# Not an f-string: the payload examples are full of literal braces.
GENERATIVE_UI_GUIDANCE = """## Generative UI (interactive replies)

You can reply with an interactive interface instead of plain prose, by ending
your reply with a marker comment on its own line:

<!-- cfy-ui:PERCENT_ENCODED_JSON -->

The payload is compact JSON, percent-encoded (escape `{`, `}`, `"`, `:` and
spaces as their `%XX` forms so it never contains `>`). Two shapes are valid:

Registered native component (preferred for structured data):
`{"version":1,"kind":"native","component":"chart.bar","props":{"title":"Weekly volume","series":[{"label":"Mon","value":42}]}}`

Available components: `chart.bar` (props: `title`, `series` of
`{label, value}`, `height`, `valueFormat` as number|percent|currency|compact)
and `table.rows` (props: `title`, `columns` of key strings, `rows` of objects).

Sandboxed custom interface:
`{"version":1,"kind":"sandbox","title":"Calculator","initialHeight":260,"html":"<button>..</button>","css":"button{...}","js":"document.querySelector('button').onclick=()=>{...}"}`

Rules:
- Use `native` for data visualization. Use `sandbox` only when the user needs
  real controls or an interactive tool.
- Prefer plain prose for ordinary answers. Do not emit a marker for simple
  factual replies, summaries, or anything a sentence handles well.
- At most one artifact per reply.
- Any prose before the marker is rendered normally; keep the marker last.
- The artifact source is stripped before you see it again later, so do not
  refer to it as if it persisted in conversation history.

Sandbox constraints — your code runs in an isolated frame with no network
access and no direct access to the host. Therefore:
- No `fetch`, `XMLHttpRequest`, WebSocket, remote fonts, images, or CDN scripts.
  There is no import map. Inline all CSS and JS.
- No `eval` and no `new Function`. Dynamic compilation is blocked; write the
  logic out directly.
- The only host functions available are `window.cfyUI.sendPrompt(text)`, which
  prefills the user's composer for them to review and send themselves, and
  `window.cfyUI.resize(height)`. Calling `sendPrompt` never sends anything.
- Keep the interface self-contained, accessible, and light on dark backgrounds.
"""


def generative_ui_enabled(env: dict[str, str] | None = None) -> bool:
    """Return whether generative UI emission guidance is enabled.

    Default is off. Enabling only adds the guidance block; it grants the model
    no capability beyond emitting a marker the renderer already validates.
    """

    source = env if env is not None else os.environ
    raw = source.get(GENERATIVE_UI_ENV_FLAG)
    if raw is None:
        return False
    return raw.strip().lower() in _TRUTHY


def build_generative_ui_guidance_block(env: dict[str, str] | None = None) -> str:
    """Return the prompt block, or an empty string when disabled."""

    if not generative_ui_enabled(env):
        return ""
    return GENERATIVE_UI_GUIDANCE.strip()


__all__ = [
    "GENERATIVE_UI_ENV_FLAG",
    "GENERATIVE_UI_GUIDANCE",
    "GENERATIVE_UI_MARKER_PREFIX",
    "build_generative_ui_guidance_block",
    "generative_ui_enabled",
]