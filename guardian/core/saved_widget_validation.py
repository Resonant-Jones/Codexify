"""Guardian-side Saved Widget candidate validation.

Read-only. Answers exactly one question: *is this server-stored generated UI
artifact eligible to be offered to the human for promotion into a Saved
Widget?* It never saves, promotes, installs, or publishes anything, and it
never executes artifact content.

Contract: docs/architecture/saved-widget-contract.md
ADR: docs/architecture/adr/102-saved-widget-identity-and-revision-boundary.md

Why this module exists
----------------------
The frontend generative UI codec already validates generated UI, but the
browser is not an authority. A durable, account-owned, cross-thread resource
needs the *server* to reach the same structural conclusion independently, and
it needs the server to be the one that proves where the artifact came from.
This module is that authority.

Three things this module deliberately does **not** do:

1. It does not claim that a static scan proves JavaScript cannot attempt a
   network request. It cannot, and it does not try. The runtime sandbox CSP is
   the network-denial boundary; the dependency gate here is a packaging
   filter, not a security control.
2. It does not treat an incidental URL in a comment or in prose as a
   dependency. Only *declared* dependencies are classified.
3. It does not accept a caller-supplied payload, role, owner, or metadata
   claim as proof. The artifact is resolved from stored assistant-message
   content, and the account comes from authenticated Guardian context.

JavaScript parity
-----------------
The structural rules below are a deliberate, line-for-line mirror of
``frontend/src/features/chat/components/generativeUi/artifactCodec.ts``. Two
languages must agree on what a marker is, or generated HTML/JS leaks into the
model prompt. That is why the JavaScript-specific semantics are reproduced
here rather than approximated:

* string length is counted in UTF-16 code units, as ``String.length`` is;
* ``trim`` removes the JavaScript whitespace set, including U+FEFF;
* ``Number()`` coercion and ``Math.round`` follow the JavaScript definitions;
* ``JSON.parse`` is strict (no ``NaN``/``Infinity``);
* percent-decoding is strict about malformed escapes and invalid UTF-8, while
  base64url decoding mirrors ``atob`` plus a non-fatal ``TextDecoder``;
* ``JSON.stringify`` output is compared byte-for-byte with the same compact
  separators and the same non-ASCII handling.

The shared corpus at
``docs/architecture/generative-ui-marker-corpus.json`` is read by both test
suites and is what keeps the two implementations honest.
"""

from __future__ import annotations

import base64
import binascii
import json
import math
import re
from dataclasses import dataclass, field
from enum import Enum
from html.parser import HTMLParser
from typing import Any, Iterable, Mapping, Sequence
from urllib.parse import unquote

__all__ = [
    "MAX_SANDBOX_HTML_CHARS",
    "MAX_SANDBOX_STYLE_CHARS",
    "MAX_SANDBOX_SCRIPT_CHARS",
    "MAX_SANDBOX_TOTAL_CHARS",
    "MAX_NATIVE_PROPS_CHARS",
    "MAX_TITLE_CHARS",
    "MAX_ENCODED_PAYLOAD_CHARS",
    "NETWORK_DENIAL_BOUNDARY",
    "WidgetCandidateStatus",
    "SourceLineage",
    "DependencyFinding",
    "WidgetCandidateAssessment",
    "decode_ui_artifact_payload",
    "validate_ui_artifact",
    "parse_ui_artifacts",
    "extract_ui_artifact_markers",
    "evaluate_eligibility",
    "assess_saved_widget_candidate",
]


# ---------------------------------------------------------------------------
# Bounds
# ---------------------------------------------------------------------------

# Mirrors of the frontend codec's limits. These are the renderer's bounds, and
# a durable record must fit them, so a Saved Widget can never be stored in a
# shape the renderer would refuse.
MAX_SANDBOX_HTML_CHARS = 120_000
MAX_SANDBOX_STYLE_CHARS = 60_000
MAX_SANDBOX_SCRIPT_CHARS = 80_000
MAX_SANDBOX_TOTAL_CHARS = 260_000
MAX_NATIVE_PROPS_CHARS = 20_000
MAX_TITLE_CHARS = 200

# Bound on the *encoded* marker payload, applied before any decoding work.
#
# Derivation: the decoded field caps sum to 260_000 characters. JSON escaping
# can expand a source character to six characters (\uXXXX), so the decoded
# JSON text is at most ~1.6M characters, and percent-encoding can expand each
# of those to at most three characters. 8_000_000 therefore sits above every
# legitimately encodable artifact.
#
# Anything above this bound would exceed the decoded caps and be rejected by
# the frontend as well, so the bound changes the *cost* of a rejection, never
# the *outcome*. That is what lets both sides agree on structural parsing.
MAX_ENCODED_PAYLOAD_CHARS = 8_000_000

# Bound on decoded JSON text, for the same reason.
MAX_DECODED_JSON_CHARS = 4_000_000


# ---------------------------------------------------------------------------
# JavaScript semantics
# ---------------------------------------------------------------------------

# The exact set JavaScript's String.prototype.trim removes. Python's
# str.strip() is close but does not remove U+FEFF, which JavaScript does.
_JS_WHITESPACE = (
    "\t\n\v\f\r           "
    "       　﻿"
)

# JavaScript's whitespace set, used by Number() coercion.
_JS_NUMBER_TRIM = _JS_WHITESPACE

_MISSING = object()


def _js_trim(value: str) -> str:
    """Mirror JavaScript's String.prototype.trim."""
    return value.strip(_JS_WHITESPACE)


def _js_length(value: str) -> int:
    """Mirror JavaScript's String.length, which counts UTF-16 code units.

    Python's len() counts code points, so an astral character such as an
    emoji counts as 1 in Python and 2 in JavaScript. The frontend caps are
    expressed in JavaScript units, so they must be compared in the same unit.
    """
    return len(value.encode("utf-16-le", errors="surrogatepass")) // 2


def _js_number(value: Any) -> float:
    """Mirror JavaScript's Number() coercion.

    Only the value shapes JSON can produce are handled. Anything JavaScript
    would turn into NaN is reported as NaN so the caller can fail closed.
    """
    if value is None:
        return 0.0
    if isinstance(value, bool):
        return 1.0 if value else 0.0
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        text = value.strip(_JS_NUMBER_TRIM)
        if not text:
            return 0.0
        if text in ("Infinity", "+Infinity"):
            return math.inf
        if text == "-Infinity":
            return -math.inf
        if re.fullmatch(r"0[xX][0-9a-fA-F]+", text):
            return float(int(text, 16))
        if re.fullmatch(r"0[oO][0-7]+", text):
            return float(int(text, 8))
        if re.fullmatch(r"0[bB][01]+", text):
            return float(int(text, 2))
        if re.fullmatch(r"[+-]?(?:\d+\.?\d*|\.\d+)(?:[eE][+-]?\d+)?", text):
            return float(text)
        return math.nan
    if isinstance(value, (list, tuple)):
        parts = []
        for item in value:
            if item is None:
                parts.append("")
            elif isinstance(item, bool):
                parts.append("true" if item else "false")
            else:
                parts.append(str(item))
        return _js_number(",".join(parts))
    return math.nan


def _js_round(value: float) -> float:
    """Mirror JavaScript's Math.round, which rounds halves toward +Infinity.

    Python's round() uses banker's rounding and would disagree on .5 values.
    """
    if not math.isfinite(value):
        return value
    return float(math.floor(value + 0.5))


def _js_json_stringify(value: Any) -> str | None:
    """Mirror JavaScript's JSON.stringify for JSON-derived values.

    JavaScript emits compact JSON with no separator whitespace and does not
    escape non-ASCII characters. Python's defaults differ on both counts, and
    the native-props cap is measured against the serialized bytes, so the
    serialization has to match exactly.
    """
    try:
        return json.dumps(
            value,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        )
    except (TypeError, ValueError):
        return None


def _strict_json_loads(text: str) -> Any:
    """Mirror JavaScript's JSON.parse, which rejects NaN and Infinity."""
    return json.loads(text, parse_constant=_reject_json_constant)


def _reject_json_constant(name: str) -> Any:
    raise ValueError(f"unsupported JSON constant: {name}")


# ---------------------------------------------------------------------------
# Payload decoding
# ---------------------------------------------------------------------------

_PERCENT_RE = re.compile(r"%(?![0-9A-Fa-f]{2})")
_SCHEME_RE = re.compile(r"^([A-Za-z][A-Za-z0-9+.\-]*):")
_BASE64URL_INVALID_RE = re.compile(r"[^A-Za-z0-9+/=]")


def _percent_decode_strict(text: str) -> str | None:
    """Mirror decodeURIComponent, which throws on malformed input.

    Python's unquote silently leaves a malformed escape in place, so the
    escape well-formedness is checked first. Invalid UTF-8 raises as well,
    which decodeURIComponent also does.
    """
    if _PERCENT_RE.search(text):
        return None
    try:
        return unquote(text, encoding="utf-8", errors="strict")
    except (UnicodeDecodeError, ValueError):
        return None


def _base64url_decode(text: str) -> str | None:
    """Mirror the frontend's base64url decode plus a non-fatal TextDecoder.

    atob() throws on characters outside the base64 alphabet; the decoder
    therefore validates strictly. TextDecoder() replaces invalid UTF-8 with
    U+FFFD instead of throwing, so the byte->text step is lenient.
    """
    padded = text.replace("-", "+").replace("_", "/")
    padded = padded + ("=" * ((4 - (len(padded) % 4)) % 4))
    # atob() ignores ASCII whitespace before validating the rest.
    cleaned = _BASE64URL_INVALID_RE.sub("", padded) if _BASE64URL_INVALID_RE.search(
        padded.replace("=", "")
    ) else padded
    try:
        raw = base64.b64decode(cleaned, validate=True)
    except (binascii.Error, ValueError):
        return None
    return raw.decode("utf-8", errors="replace")


def decode_ui_artifact_payload(payload: str) -> Any:
    """Decode a marker payload in either supported encoding.

    Mirrors the frontend's decodePayload. The two alphabets are disjoint:
    base64url uses only A-Za-z0-9_- and cannot contain '%', so a payload with
    a percent sign is percent-encoded. That makes the branch deterministic
    rather than order-dependent.
    """
    normalized = _js_trim(payload) if isinstance(payload, str) else ""
    if not normalized:
        return None
    if len(normalized) > MAX_ENCODED_PAYLOAD_CHARS:
        return None
    if "%" in normalized:
        text = _percent_decode_strict(normalized)
        if text is None:
            return None
        if len(text) > MAX_DECODED_JSON_CHARS:
            return None
        try:
            return _strict_json_loads(text)
        except ValueError:
            return None
    text = _base64url_decode(normalized)
    if text is None:
        return None
    if len(text) > MAX_DECODED_JSON_CHARS:
        return None
    try:
        return _strict_json_loads(text)
    except ValueError:
        return None


# ---------------------------------------------------------------------------
# Structural validation
# ---------------------------------------------------------------------------


def _is_falsy(value: Any) -> bool:
    """Mirror JavaScript truthiness for the values JSON can produce."""
    if value is None or value is False:
        return True
    if isinstance(value, (int, float)) and value == 0:
        return True
    if isinstance(value, str) and value == "":
        return True
    return False


def validate_ui_artifact(candidate: Any) -> dict[str, Any] | None:
    """Structurally validate one decoded envelope.

    Mirrors the frontend's validateUiArtifact. Returns the normalized
    artifact, or None for anything unrecognized. Nothing here executes,
    fetches, or resolves artifact content.
    """
    if _is_falsy(candidate):
        return None
    if not isinstance(candidate, dict):
        return None

    version = candidate.get("version", _MISSING)
    if isinstance(version, bool) or version != 1:
        return None

    layout = candidate.get("layout", _MISSING)
    if layout is not _MISSING and layout not in ("compact", "wide"):
        return None

    kind = candidate.get("kind")

    if kind == "native":
        raw_component = candidate.get("component", _MISSING)
        component = (
            _js_trim(raw_component) if isinstance(raw_component, str) else ""
        )
        if not component or _js_length(component) > MAX_TITLE_CHARS:
            return None
        props = candidate.get("props", _MISSING)
        if props is not _MISSING and not isinstance(props, dict):
            return None
        serialized = _js_json_stringify({} if props is _MISSING else props)
        if serialized is None:
            return None
        if _js_length(serialized) > MAX_NATIVE_PROPS_CHARS:
            return None
        artifact: dict[str, Any] = {
            "version": 1,
            "kind": "native",
            "component": component,
            "props": {} if props is _MISSING else props,
        }
        if layout is not _MISSING:
            artifact["layout"] = layout
        return artifact

    if kind == "sandbox":
        raw_html = candidate.get("html", _MISSING)
        html = raw_html if isinstance(raw_html, str) else ""
        if not _js_trim(html) or _js_length(html) > MAX_SANDBOX_HTML_CHARS:
            return None
        raw_css = candidate.get("css", _MISSING)
        css = raw_css if isinstance(raw_css, str) else ""
        raw_js = candidate.get("js", _MISSING)
        js = raw_js if isinstance(raw_js, str) else ""
        if _js_length(css) > MAX_SANDBOX_STYLE_CHARS:
            return None
        if _js_length(js) > MAX_SANDBOX_SCRIPT_CHARS:
            return None
        if _js_length(html) + _js_length(css) + _js_length(js) > MAX_SANDBOX_TOTAL_CHARS:
            return None
        raw_title = candidate.get("title", _MISSING)
        title = _js_trim(raw_title) if isinstance(raw_title, str) else ""
        if _js_length(title) > MAX_TITLE_CHARS:
            return None
        initial_height: float | None = None
        raw_height = candidate.get("initialHeight", _MISSING)
        if raw_height is not _MISSING and raw_height is not None:
            number = _js_number(raw_height)
            if not math.isfinite(number):
                return None
            initial_height = _js_round(number)
        artifact = {"version": 1, "kind": "sandbox"}
        if title:
            artifact["title"] = title
        artifact["html"] = html
        if _js_trim(css):
            artifact["css"] = css
        if _js_trim(js):
            artifact["js"] = js
        if initial_height is not None:
            artifact["initialHeight"] = initial_height
        if layout is not _MISSING:
            artifact["layout"] = layout
        return artifact

    return None


# ---------------------------------------------------------------------------
# Marker extraction
# ---------------------------------------------------------------------------

# The capture form of the strip regex in guardian.core.chat_attachments. The
# two must match the same spans; tests/core/test_saved_widget_validation.py
# asserts that they do.
_UI_MARKER_RE = re.compile(r"<!--\s*cfy-ui:(.*?)-->", flags=re.IGNORECASE | re.DOTALL)
_UI_UNTERMINATED_MARKER_RE = re.compile(
    r"<!--\s*cfy-ui:[^\n]*$", flags=re.MULTILINE
)


@dataclass(frozen=True)
class UiArtifactMarker:
    """One `cfy-ui` marker found in message content."""

    index: int
    payload: str
    decoded: Any
    artifact: dict[str, Any] | None
    valid_artifact_index: int | None


def extract_ui_artifact_markers(content: str) -> list[UiArtifactMarker]:
    """Return every `cfy-ui` marker in document order, valid or not.

    Unlike the frontend parser, invalid markers are *retained* rather than
    dropped, because the eligibility service has to be able to report
    "structurally invalid" for a specific marker instead of silently
    skipping it.
    """
    if not isinstance(content, str) or not content:
        return []
    markers: list[UiArtifactMarker] = []
    valid_index = 0
    for match in _UI_MARKER_RE.finditer(content):
        payload = match.group(1)
        decoded = decode_ui_artifact_payload(payload)
        artifact = validate_ui_artifact(decoded)
        markers.append(
            UiArtifactMarker(
                index=len(markers),
                payload=payload,
                decoded=decoded,
                artifact=artifact,
                valid_artifact_index=valid_index if artifact is not None else None,
            )
        )
        if artifact is not None:
            valid_index += 1
    return markers


def parse_ui_artifacts(content: str) -> list[dict[str, Any]]:
    """Return the valid artifacts in message content, in document order.

    Mirrors the frontend's parseUiArtifacts for the artifact list. The
    remaining prose is not needed here.
    """
    return [
        marker.artifact
        for marker in extract_ui_artifact_markers(content)
        if marker.artifact is not None
    ]


# ---------------------------------------------------------------------------
# Dependency classification (E4)
# ---------------------------------------------------------------------------

# Schemes that cannot reach outside the frame. Everything else with a scheme
# is treated as external.
_SELF_CONTAINED_SCHEMES = frozenset({"data", "blob", "about"})

# HTML attributes that declare a resource the frame would load. `a[href]` is
# deliberately absent: a hyperlink is navigation, not a loaded resource, and
# the sandbox confines it. `a[href]` is still visible in the source and the
# CSP still governs what the frame may load.
_HTML_RESOURCE_ATTRIBUTES = frozenset(
    {
        "src",
        "srcset",
        "data",
        "poster",
        "background",
        "codebase",
        "archive",
        "manifest",
        "action",
        "formaction",
        "xlink:href",
    }
)

# Attributes whose value is a comma-separated candidate list.
_HTML_SRCSET_ATTRIBUTES = frozenset({"srcset"})

# (tag, attribute) pairs that are dependencies even though the attribute name
# is shared with a non-dependency use.
_HTML_TAG_SCOPED_ATTRIBUTES = {
    ("link", "href"),
    ("base", "href"),
}


class _ReferenceKind(str, Enum):
    SELF_CONTAINED = "self_contained"
    EXTERNAL = "external"
    UNAVAILABLE_LOCAL = "unavailable_local"
    AMBIGUOUS = "ambiguous"


@dataclass(frozen=True)
class DependencyFinding:
    """One classified dependency declaration."""

    surface: str
    detail: str
    reference: str
    kind: str

    def as_dict(self) -> dict[str, str]:
        return {
            "surface": self.surface,
            "detail": self.detail,
            "reference": self.reference[:200],
            "kind": self.kind,
        }


def _classify_reference(raw: str) -> _ReferenceKind:
    """Classify one declared dependency target.

    Returns:

    * ``SELF_CONTAINED`` for a same-document fragment reference and for the
      local schemes ``data:``, ``blob:`` and ``about:``. A fragment reference
      names a resource inside the document that is already loaded, so it
      consumes no additional document.
    * ``EXTERNAL`` for anything that names another origin.
    * ``UNAVAILABLE_LOCAL`` for a scheme-less reference. Generated UI ships no
      asset package and serves no additional files, so a local path cannot
      resolve to anything the frame could load. Being local-looking is not
      the same as being self-contained.
    * ``AMBIGUOUS`` when the declaration itself cannot be classified, which
      fails closed.

    This is a packaging filter, not a network-security control. The runtime
    CSP is what denies network access; see the Saved Widget Contract.
    """
    value = _js_trim(raw)
    if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
        value = _js_trim(value[1:-1])
    if not value:
        return _ReferenceKind.AMBIGUOUS
    if any(ord(ch) < 0x20 or ord(ch) == 0x7F for ch in value):
        return _ReferenceKind.AMBIGUOUS
    if _PERCENT_RE.search(value):
        return _ReferenceKind.AMBIGUOUS
    if value.startswith("#"):
        return _ReferenceKind.SELF_CONTAINED
    if value.startswith("//"):
        return _ReferenceKind.EXTERNAL
    scheme = _SCHEME_RE.match(value)
    if scheme:
        if scheme.group(1).lower() in _SELF_CONTAINED_SCHEMES:
            return _ReferenceKind.SELF_CONTAINED
        return _ReferenceKind.EXTERNAL
    # Scheme-less. The frame is served from a document, not from an asset
    # package, so there is nothing for this reference to resolve to.
    return _ReferenceKind.UNAVAILABLE_LOCAL


def _findings_for(
    surface: str, detail: str, references: Iterable[str]
) -> list[DependencyFinding]:
    findings: list[DependencyFinding] = []
    for reference in references:
        kind = _classify_reference(reference)
        if kind is _ReferenceKind.SELF_CONTAINED:
            continue
        findings.append(
            DependencyFinding(
                surface=surface,
                detail=detail,
                reference=reference,
                kind=kind.value,
            )
        )
    return findings


class _DependencyHTMLParser(HTMLParser):
    """Collect declared resource dependencies from markup.

    Comments are ignored, so an incidental URL inside an HTML comment is not
    a dependency. Text content is ignored for the same reason.
    """

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.findings: list[DependencyFinding] = []

    def _handle(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        for name, value in attrs:
            if value is None:
                continue
            attribute = name.lower()
            if attribute == "style":
                self.findings.extend(
                    _findings_for(
                        "inline-style", f"{tag}[style]", _css_url_references(value)
                    )
                )
                continue
            if attribute in _HTML_SRCSET_ATTRIBUTES:
                self.findings.extend(
                    _findings_for(
                        "html", f"{tag}[{attribute}]", _srcset_references(value)
                    )
                )
                continue
            if attribute in _HTML_RESOURCE_ATTRIBUTES:
                self.findings.extend(
                    _findings_for("html", f"{tag}[{attribute}]", [value])
                )
                continue
            if (tag, attribute) in _HTML_TAG_SCOPED_ATTRIBUTES:
                self.findings.extend(
                    _findings_for("html", f"{tag}[{attribute}]", [value])
                )

    def handle_starttag(self, tag, attrs):  # noqa: D102 - stdlib callback
        self._handle(tag.lower(), attrs)

    def handle_startendtag(self, tag, attrs):  # noqa: D102 - stdlib callback
        self._handle(tag.lower(), attrs)


def _srcset_references(value: str) -> list[str]:
    """Split a srcset-style candidate list into its URLs."""
    references = []
    for candidate in value.split(","):
        candidate = candidate.strip()
        if not candidate:
            continue
        references.append(candidate.split()[0])
    return references


_CSS_COMMENT_RE = re.compile(r"/\*.*?\*/", flags=re.DOTALL)
_CSS_URL_RE = re.compile(r"url\(\s*(?P<quote>['\"]?)(?P<value>[^)'\"]*)(?P=quote)\s*\)", re.IGNORECASE)
_CSS_IMPORT_RE = re.compile(r"@import\s+(?P<quote>['\"])(?P<value>[^'\"]*)(?P=quote)", re.IGNORECASE)


def _css_url_references(value: str) -> list[str]:
    """Collect url() and @import targets from a stylesheet or style attribute."""
    without_comments = _CSS_COMMENT_RE.sub(" ", value)
    references = [match.group("value") for match in _CSS_URL_RE.finditer(without_comments)]
    references.extend(
        match.group("value") for match in _CSS_IMPORT_RE.finditer(without_comments)
    )
    return references


# A '/' begins a regular expression literal when the previous significant
# character cannot end an expression. This is the standard heuristic and it is
# only used to avoid mistaking a regex body for a comment.
_JS_REGEX_PRECEDERS = set("(,=:[!&|?{};+-*%~^<>")
_JS_REGEX_KEYWORDS = frozenset(
    {
        "return",
        "typeof",
        "instanceof",
        "case",
        "in",
        "of",
        "new",
        "delete",
        "void",
        "do",
        "else",
        "yield",
        "await",
    }
)


def _mask_js_source(source: str) -> str:
    """Blank out comments and string contents, preserving length and quotes.

    Comment bodies become spaces so an incidental URL inside a comment cannot
    be read as a declaration. String *contents* become spaces while the
    delimiters stay, so a module specifier can still be located by span and
    then read from the original text.

    A regular-expression literal is also masked, so that a regex body
    containing ``//`` is not mistaken for a line comment. Detecting a regex
    reliably needs a full JavaScript parser; this uses the standard
    heuristic, and a regex that is misread as division costs at most a
    masked span, never a false dependency.
    """
    out = list(source)
    length = len(source)
    index = 0
    state: str | None = None
    previous_significant = ""
    previous_word = ""

    def is_word_char(char: str) -> bool:
        return char.isalnum() or char == "_" or char == "$"

    while index < length:
        char = source[index]
        following = source[index + 1] if index + 1 < length else ""

        if state == "line_comment":
            if char == "\n":
                state = None
            else:
                out[index] = " "
            index += 1
            continue

        if state == "block_comment":
            if char == "*" and following == "/":
                out[index] = " "
                out[index + 1] = " "
                index += 2
                state = None
                continue
            if char != "\n":
                out[index] = " "
            index += 1
            continue

        if state in ("single_quote", "double_quote", "template"):
            closing = {
                "single_quote": "'",
                "double_quote": '"',
                "template": "`",
            }[state]
            if char == "\\":
                out[index] = " "
                if index + 1 < length:
                    out[index + 1] = " "
                index += 2
                continue
            if char == closing:
                state = None
                index += 1
                continue
            if char != "\n":
                out[index] = " "
            index += 1
            continue

        if state == "regex":
            if char == "\\":
                out[index] = " "
                if index + 1 < length:
                    out[index + 1] = " "
                index += 2
                continue
            if char == "/":
                out[index] = " "
                index += 1
                state = None
                previous_significant = "/"
                previous_word = ""
                continue
            if char == "\n":
                # A regular expression literal cannot span a line. Stop
                # masking here rather than swallowing the rest of the file.
                state = None
                index += 1
                continue
            out[index] = " "
            index += 1
            continue

        # Not currently inside a literal or comment.
        if char == "/" and following == "/":
            out[index] = " "
            out[index + 1] = " "
            index += 2
            state = "line_comment"
            continue
        if char == "/" and following == "*":
            out[index] = " "
            out[index + 1] = " "
            index += 2
            state = "block_comment"
            continue
        if char == "'":
            state = "single_quote"
            index += 1
            previous_significant = "'"
            previous_word = ""
            continue
        if char == '"':
            state = "double_quote"
            index += 1
            previous_significant = '"'
            previous_word = ""
            continue
        if char == "`":
            state = "template"
            index += 1
            previous_significant = "`"
            previous_word = ""
            continue
        if char == "/" and (
            previous_significant == ""
            or previous_significant in _JS_REGEX_PRECEDERS
            or previous_word in _JS_REGEX_KEYWORDS
        ):
            state = "regex"
            index += 1
            continue

        if char.isspace():
            # Whitespace does not end the current word, so a keyword followed
            # by a space is still visible to the regex heuristic.
            index += 1
            continue
        if is_word_char(char):
            previous_word += char
            previous_significant = char
        else:
            previous_word = ""
            previous_significant = char
        index += 1

    return "".join(out)


_JS_DEPENDENCY_RE = re.compile(
    r"""\b(?:import|export)\b[^;()]*?\bfrom\s*(?P<q1>['"])(?P<s1>[^'"]*)(?P=q1)"""
    r"""|\bimport\s*(?P<q2>['"])(?P<s2>[^'"]*)(?P=q2)"""
    r"""|\bimport\s*\(\s*(?P<q3>['"])(?P<s3>[^'"]*)(?P=q3)\s*\)"""
    r"""|\brequire\s*\(\s*(?P<q4>['"])(?P<s4>[^'"]*)(?P=q4)\s*\)""",
    re.VERBOSE,
)


def _js_module_references(source: str) -> list[str]:
    """Collect declared module specifiers from JavaScript.

    Only import, re-export, dynamic import, and require declarations count.
    A URL that merely appears in a string, a comment, or a literal is not a
    declared dependency and is not treated as one.
    """
    if not source:
        return []
    masked = _mask_js_source(source)
    references: list[str] = []
    for match in _JS_DEPENDENCY_RE.finditer(masked):
        for group in ("s1", "s2", "s3", "s4"):
            if match.group(group) is None:
                continue
            start, end = match.span(group)
            references.append(source[start:end])
            break
    return references


# ---------------------------------------------------------------------------
# Eligibility (E1-E6)
# ---------------------------------------------------------------------------

REASON_ENVELOPE_INVALID = "artifact_envelope_invalid"
REASON_SIZE_LIMIT_EXCEEDED = "artifact_size_limit_exceeded"
REASON_KIND_NOT_SANDBOX = "artifact_kind_not_sandbox"
REASON_MISSING_EXECUTABLE_CODE = "artifact_missing_executable_code"
REASON_EXTERNAL_DEPENDENCY = "artifact_external_dependency"
REASON_UNAVAILABLE_LOCAL_DEPENDENCY = "artifact_unavailable_local_dependency"
REASON_AMBIGUOUS_DEPENDENCY = "artifact_ambiguous_dependency"
REASON_PROVENANCE_UNPROVEN = "source_provenance_unproven"
REASON_PROVENANCE_NOT_ACCEPTED = "source_provenance_not_accepted"
REASON_PROVENANCE_CONTRADICTORY = "source_provenance_contradictory"
REASON_SOURCE_NOT_AUTHORIZED = "source_not_authorized"
REASON_SELECTION_INVALID = "source_artifact_selection_invalid"
REASON_SELECTION_MISMATCH = "source_artifact_selection_mismatch"

# The control that actually denies network access when a saved widget runs.
#
# The dependency gate in this module is a *packaging filter*. It rejects known
# external dependencies so that a widget does not depend on a resource it can
# never load. It is not, and must never be reported as, a guarantee that the
# program cannot attempt a network request: a payload can assemble a URL at
# runtime or derive one from encoded data, and no static inspection can rule
# that out. The sandbox's restrictive CSP is the enforcement boundary, and it
# is unchanged by ADR-102.
NETWORK_DENIAL_BOUNDARY = "sandbox-csp"


class WidgetCandidateStatus(str, Enum):
    """The three outcomes of an eligibility assessment."""

    STRUCTURALLY_INVALID = "structurally_invalid"
    INELIGIBLE = "ineligible"
    ELIGIBLE = "eligible"


@dataclass(frozen=True)
class SourceLineage:
    """Server-proven lineage for the source assistant message."""

    thread_id: int
    message_id: int
    request_id: str
    accepted_at: Any = None


@dataclass(frozen=True)
class WidgetCandidateAssessment:
    """A bounded, deterministic, read-only assessment.

    A Widget Candidate is ephemeral. This object is not a Saved Widget, it
    does not carry a widget identity, and nothing in it may be persisted as
    one.
    """

    status: WidgetCandidateStatus
    reasons: tuple[str, ...] = ()
    artifact: Mapping[str, Any] | None = None
    lineage: SourceLineage | None = None
    artifact_index: int | None = None
    valid_artifact_index: int | None = None
    dependency_findings: tuple[DependencyFinding, ...] = ()
    network_denial_boundary: str = NETWORK_DENIAL_BOUNDARY

    @property
    def is_eligible(self) -> bool:
        return self.status is WidgetCandidateStatus.ELIGIBLE

    def as_dict(self) -> dict[str, Any]:
        """A JSON-safe projection. Contains no cross-account existence detail."""
        return {
            "status": self.status.value,
            "reasons": list(self.reasons),
            "artifact_index": self.artifact_index,
            "valid_artifact_index": self.valid_artifact_index,
            "artifact": dict(self.artifact) if self.artifact is not None else None,
            "lineage": (
                {
                    "thread_id": self.lineage.thread_id,
                    "message_id": self.lineage.message_id,
                    "request_id": self.lineage.request_id,
                }
                if self.lineage is not None
                else None
            ),
            "dependency_findings": [f.as_dict() for f in self.dependency_findings],
            "network_denial_boundary": self.network_denial_boundary,
        }


def _size_violations(candidate: Any) -> list[str]:
    """Report which size cap a decoded payload exceeds, if any.

    Evaluated against the raw decoded payload so that E6 is provable on its
    own, independently of whether the envelope is otherwise well formed.
    """
    if not isinstance(candidate, dict):
        return []
    violations: list[str] = []
    kind = candidate.get("kind")
    if kind == "sandbox":
        html = candidate.get("html")
        css = candidate.get("css")
        js = candidate.get("js")
        html = html if isinstance(html, str) else ""
        css = css if isinstance(css, str) else ""
        js = js if isinstance(js, str) else ""
        if _js_length(html) > MAX_SANDBOX_HTML_CHARS:
            violations.append("sandbox_html")
        if _js_length(css) > MAX_SANDBOX_STYLE_CHARS:
            violations.append("sandbox_css")
        if _js_length(js) > MAX_SANDBOX_SCRIPT_CHARS:
            violations.append("sandbox_js")
        total = _js_length(html) + _js_length(css) + _js_length(js)
        if total > MAX_SANDBOX_TOTAL_CHARS:
            violations.append("sandbox_total")
    elif kind == "native":
        props = candidate.get("props", _MISSING)
        if props is not _MISSING and isinstance(props, dict):
            serialized = _js_json_stringify(props)
            if serialized is not None and _js_length(serialized) > MAX_NATIVE_PROPS_CHARS:
                violations.append("native_props")
    title = candidate.get("title")
    if isinstance(title, str) and _js_length(_js_trim(title)) > MAX_TITLE_CHARS:
        violations.append("title")
    return violations


def _collect_dependency_findings(artifact: Mapping[str, Any]) -> list[DependencyFinding]:
    """Collect and classify every declared dependency in a sandbox artifact."""
    findings: list[DependencyFinding] = []
    html = artifact.get("html") or ""
    css = artifact.get("css") or ""
    js = artifact.get("js") or ""

    parser = _DependencyHTMLParser()
    try:
        parser.feed(html)
        parser.close()
    except Exception:  # noqa: BLE001 - malformed markup must not crash the gate
        # An HTMLParser failure means the markup could not be inspected, so
        # the dependency set is unknown. That is an ambiguous declaration and
        # it fails closed.
        findings.append(
            DependencyFinding(
                surface="html",
                detail="markup",
                reference="",
                kind=_ReferenceKind.AMBIGUOUS.value,
            )
        )
    findings.extend(parser.findings)

    findings.extend(
        _findings_for("css", "stylesheet", _css_url_references(css))
    )
    findings.extend(
        _findings_for("js", "module", _js_module_references(js))
    )
    return findings


def evaluate_eligibility(
    artifact: Mapping[str, Any] | None,
    *,
    decoded_payload: Any = None,
) -> tuple[tuple[str, ...], tuple[DependencyFinding, ...]]:
    """Evaluate the artifact-side preconditions E1, E2, E3, E4, and E6.

    Returns the failing reason codes and any dependency findings. E5 is
    evaluated separately because it is a property of the source, not of the
    artifact.
    """
    reasons: list[str] = []
    findings: tuple[DependencyFinding, ...] = ()

    size_violations = _size_violations(decoded_payload)
    if size_violations:
        reasons.append(REASON_SIZE_LIMIT_EXCEEDED)

    if artifact is None:
        reasons.append(REASON_ENVELOPE_INVALID)
        return tuple(dict.fromkeys(reasons)), findings

    if artifact.get("kind") != "sandbox":
        reasons.append(REASON_KIND_NOT_SANDBOX)
        return tuple(dict.fromkeys(reasons)), findings

    # E3: executable behavior. Only the supported `js` field counts. Markup,
    # styling, and inline event-handler text are not executable behavior.
    js = artifact.get("js")
    if not isinstance(js, str) or not _js_trim(js):
        reasons.append(REASON_MISSING_EXECUTABLE_CODE)
        return tuple(dict.fromkeys(reasons)), findings

    # E4: declared dependencies.
    findings = tuple(_collect_dependency_findings(artifact))
    if any(finding.kind == _ReferenceKind.EXTERNAL.value for finding in findings):
        reasons.append(REASON_EXTERNAL_DEPENDENCY)
    if any(
        finding.kind == _ReferenceKind.UNAVAILABLE_LOCAL.value for finding in findings
    ):
        reasons.append(REASON_UNAVAILABLE_LOCAL_DEPENDENCY)
    if any(finding.kind == _ReferenceKind.AMBIGUOUS.value for finding in findings):
        reasons.append(REASON_AMBIGUOUS_DEPENDENCY)

    return tuple(dict.fromkeys(reasons)), findings


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------


def assess_saved_widget_candidate(
    chatlog_db: Any,
    *,
    account_id: str,
    thread_id: int,
    message_id: int,
    artifact_index: int = 0,
    claimed_payload: str | None = None,
) -> WidgetCandidateAssessment:
    """Assess whether a stored artifact may be offered for human promotion.

    Read-only. Resolves the source message and the artifact server-side,
    proves the lineage, and evaluates the accepted preconditions E1 through
    E6. It never creates a Saved Widget, a Saved Widget identity, or any
    other durable record.

    ``account_id`` must come from authenticated Guardian context. A
    caller-supplied owner claim is never accepted.

    ``artifact_index`` selects the Nth `cfy-ui` marker in the source message,
    counting invalid markers too, so that a malformed marker can be reported
    as structurally invalid rather than silently skipped.

    ``claimed_payload`` is optional and is never trusted. When supplied it
    must match the artifact the server resolved from stored content.
    """
    from guardian.core.db import read_saved_widget_source_provenance

    provenance = read_saved_widget_source_provenance(
        chatlog_db,
        thread_id=thread_id,
        message_id=message_id,
        account_id=account_id,
    )

    if not provenance.get("resolved"):
        # One uniform reason for every authorization failure. Distinguishing
        # "missing" from "belongs to another account" would leak the
        # existence of another account's data.
        return WidgetCandidateAssessment(
            status=WidgetCandidateStatus.INELIGIBLE,
            reasons=(REASON_SOURCE_NOT_AUTHORIZED,),
        )

    content = provenance.get("content") or ""
    markers = extract_ui_artifact_markers(content)
    if artifact_index < 0 or artifact_index >= len(markers):
        return WidgetCandidateAssessment(
            status=WidgetCandidateStatus.INELIGIBLE,
            reasons=(REASON_SELECTION_INVALID,),
        )

    marker = markers[artifact_index]

    if claimed_payload is not None:
        claimed = validate_ui_artifact(decode_ui_artifact_payload(claimed_payload))
        if claimed is None or claimed != marker.artifact:
            # The caller's payload does not describe the artifact the server
            # actually stored, so it cannot be used as proof of anything.
            return WidgetCandidateAssessment(
                status=WidgetCandidateStatus.INELIGIBLE,
                reasons=(REASON_SELECTION_MISMATCH,),
                artifact_index=marker.index,
                valid_artifact_index=marker.valid_artifact_index,
            )

    decoded_payload = marker.decoded
    reasons, findings = evaluate_eligibility(
        marker.artifact, decoded_payload=decoded_payload
    )

    lineage: SourceLineage | None = None
    attempts = provenance.get("attempts") or []
    accepted = [attempt for attempt in attempts if attempt.get("accepted_at")]
    contradictory = [
        attempt for attempt in attempts if attempt.get("terminal_event_type")
    ]
    if not attempts:
        reasons = reasons + (REASON_PROVENANCE_UNPROVEN,)
    elif contradictory:
        reasons = reasons + (REASON_PROVENANCE_CONTRADICTORY,)
    elif not accepted:
        reasons = reasons + (REASON_PROVENANCE_NOT_ACCEPTED,)
    else:
        lineage = SourceLineage(
            thread_id=int(provenance["thread_id"]),
            message_id=int(provenance["message_id"]),
            request_id=str(accepted[0].get("request_id") or ""),
            accepted_at=accepted[0].get("accepted_at"),
        )

    ordered_reasons = tuple(dict.fromkeys(reasons))
    if ordered_reasons:
        structural = {REASON_ENVELOPE_INVALID, REASON_SIZE_LIMIT_EXCEEDED}
        status = (
            WidgetCandidateStatus.STRUCTURALLY_INVALID
            if structural.intersection(ordered_reasons)
            else WidgetCandidateStatus.INELIGIBLE
        )
        return WidgetCandidateAssessment(
            status=status,
            reasons=ordered_reasons,
            artifact=marker.artifact,
            lineage=lineage,
            artifact_index=marker.index,
            valid_artifact_index=marker.valid_artifact_index,
            dependency_findings=findings,
        )

    return WidgetCandidateAssessment(
        status=WidgetCandidateStatus.ELIGIBLE,
        reasons=(),
        artifact=marker.artifact,
        lineage=lineage,
        artifact_index=marker.index,
        valid_artifact_index=marker.valid_artifact_index,
        dependency_findings=findings,
    )
