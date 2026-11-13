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

import json
import os
from urllib.parse import quote

GENERATIVE_UI_ENV_FLAG = "GUARDIAN_GENERATIVE_UI"
_TRUTHY = {"1", "true", "yes", "on", "enabled"}

GENERATIVE_UI_MARKER_PREFIX = "cfy-ui"

_SANDBOX_EXAMPLE = {
    "version": 1,
    "kind": "sandbox",
    "title": "Counter",
    "html": "<button>0</button>",
    "js": "const b=document.querySelector('button');b.onclick=()=>b.textContent=Number(b.textContent)+1;",
}
_SANDBOX_EXAMPLE_JSON = json.dumps(_SANDBOX_EXAMPLE, separators=(",", ":"))
_SANDBOX_EXAMPLE_MARKER = (
    f"<!-- {GENERATIVE_UI_MARKER_PREFIX}:{quote(_SANDBOX_EXAMPLE_JSON, safe='')} -->"
)

# Kept deliberately compact. This competes for the system-prompt token budget.
GENERATIVE_UI_GUIDANCE = f"""## Generative UI (interactive replies)

To deliver an interactive interface in chat, end your reply with one complete
`cfy-ui` HTML comment on its own line, outside code fences. Serialize the
widget as valid compact JSON first. Inside JSON strings, escape quotes,
backslashes, and line breaks. Percent-encode the entire serialized object
(including literal percent signs as `%25`) and put it inside the comment.
Output only the completed comment and any short introduction. Omit the JSON
source, HTML, CSS, JavaScript, and encoding placeholders from the visible reply.

Registered native component (preferred for structured data):
`{{"version":1,"kind":"native","component":"chart.bar","props":{{"title":"Weekly volume","series":[{{"label":"Mon","value":42}}]}}}}`

Available components: `chart.bar` (props: `title`, `series` of
`{{label, value}}`, `height`, `valueFormat` as number|percent|currency|compact)
and `table.rows` (props: `title`, `columns` of key strings, `rows` of objects).

Sandboxed custom interface (decoded JSON for reference, with optional `css`):
`{_SANDBOX_EXAMPLE_JSON}`

The complete reply for that counter ends with this encoded comment. For a new
widget, encode your own object and use it in the same position:

{_SANDBOX_EXAMPLE_MARKER}

Rules:
- Use `native` for data visualization. Use `sandbox` only when the user needs
  real controls or an interactive tool.
- Prefer plain prose for ordinary answers. Do not emit a marker for simple
  factual replies, summaries, or anything a sentence handles well.
- At most one artifact per reply.
- Either artifact kind may declare `"layout":"wide"` for a broad canvas;
  otherwise it uses compact width. The host always bounds layout to chat width.
- Sandbox content is measured and fitted vertically up to a safe height cap;
  `initialHeight` is a starting size, not a clipping requirement.
- Any prose before the marker is rendered normally; keep the marker last.
- The artifact source is stripped before you see it again later, so do not
  refer to it as if it persisted in conversation history.

Sandbox constraints — your code runs in an isolated frame with no network
access and no direct access to the host. Therefore:
- No `fetch`, `XMLHttpRequest`, WebSocket, remote fonts, images, or CDN scripts.
  There is no import map. Inline all CSS and JS.
- No `eval` and no `new Function`. Dynamic compilation is blocked; write the
  logic out directly.
- For instruments in Scout on iOS and iPadOS, use Web Audio oscillators,
  gain envelopes, and biquad filters.
- The only host functions available are `window.cfyUI.sendPrompt(text)`, which
  prefills the user's composer for them to review and send themselves, and
  `window.cfyUI.resize(height)`. Calling `sendPrompt` never sends anything.
  The host also observes content size, so manual resize is optional.
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
