"""Guardian-side Saved Widget eligibility validation: codec parity and E1-E4.

These tests cover the part of the Saved Widget contract that needs no
database: the structural mirror of the frontend artifact codec, and the
artifact-side preconditions E1 (envelope), E2 (kind), E3 (executable
behavior), E4 (declared dependencies), and E6 (size caps).

E5 (server-proven provenance) lives in
tests/db/test_saved_widget_validation_provenance.py, because it needs a
database.

Contract: docs/architecture/saved-widget-contract.md
ADR: docs/architecture/adr/102-saved-widget-identity-and-revision-boundary.md
"""

from __future__ import annotations

import base64
import json
import pathlib
import re
from typing import Any

import pytest

from guardian.core import chat_attachments
from guardian.core.saved_widget_validation import (
    MAX_NATIVE_PROPS_CHARS,
    MAX_SANDBOX_HTML_CHARS,
    MAX_SANDBOX_SCRIPT_CHARS,
    MAX_SANDBOX_STYLE_CHARS,
    MAX_TITLE_CHARS,
    NETWORK_DENIAL_BOUNDARY,
    REASON_AMBIGUOUS_DEPENDENCY,
    REASON_ENVELOPE_INVALID,
    REASON_EXTERNAL_DEPENDENCY,
    REASON_KIND_NOT_SANDBOX,
    REASON_MISSING_EXECUTABLE_CODE,
    REASON_SIZE_LIMIT_EXCEEDED,
    REASON_UNAVAILABLE_LOCAL_DEPENDENCY,
    WidgetCandidateStatus,
    assess_saved_widget_candidate,
    decode_ui_artifact_payload,
    evaluate_eligibility,
    extract_ui_artifact_markers,
    parse_ui_artifacts,
    validate_ui_artifact,
)

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
CORPUS_PATH = REPO_ROOT / "docs" / "architecture" / "generative-ui-marker-corpus.json"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _js_unreserved(text: str) -> str:
    """JavaScript's encodeURIComponent, used to build realistic markers."""
    safe = set(
        "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_.!~*'()"
    )
    out: list[str] = []
    for byte in text.encode("utf-8"):
        char = chr(byte)
        out.append(char if char in safe else f"%{byte:02X}")
    return "".join(out)


def _marker(payload: dict[str, Any], encoding: str = "percent") -> str:
    text = json.dumps(payload, separators=(",", ":"), ensure_ascii=False)
    if encoding == "percent":
        encoded = _js_unreserved(text)
    else:
        encoded = (
            base64.b64encode(text.encode("utf-8"))
            .decode("ascii")
            .replace("+", "-")
            .replace("/", "_")
            .rstrip("=")
        )
    return f"<!-- cfy-ui:{encoded} -->"


def _sandbox(**overrides: Any) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "version": 1,
        "kind": "sandbox",
        "html": "<button id='go'>go</button>",
        "js": "document.getElementById('go').addEventListener('click', function () {});",
    }
    payload.update(overrides)
    return payload


def _reasons(
    artifact: dict[str, Any] | None, decoded_payload: Any = None
) -> tuple[str, ...]:
    reasons, _ = evaluate_eligibility(
        artifact, decoded_payload=artifact if decoded_payload is None else decoded_payload
    )
    return reasons


# ---------------------------------------------------------------------------
# Shared corpus parity
# ---------------------------------------------------------------------------


def _load_corpus() -> list[dict[str, Any]]:
    return json.loads(CORPUS_PATH.read_text(encoding="utf-8"))["cases"]


def test_shared_corpus_cases_parse_the_same_way_the_frontend_expects() -> None:
    """Cross-boundary invariant.

    The frontend renderer and this codec are separate implementations in two
    languages. Reading the same corpus from both suites is what prevents a
    silent divergence that leaks generated HTML/JS into the model prompt.

    The frontend asserts `parsed.artifacts.length > 0` equals the corpus
    `parses` flag; this asserts the same flag for the Guardian decoder.
    """
    cases = _load_corpus()
    assert len(cases) >= 15

    for case in cases:
        if case["label"] == "oversized payload":
            continue  # asserted directly below; the placeholder carries no payload
        marker = case["marker"]
        match = re.search(
            r"<!--\s*cfy-ui:(.*?)-->", marker, re.IGNORECASE | re.DOTALL
        )
        if match is None:
            # An unterminated marker can never parse.
            assert not case["parses"], case["label"]
            continue
        artifact = validate_ui_artifact(decode_ui_artifact_payload(match.group(1)))
        assert (artifact is not None) is case["parses"], case["label"]


def test_marker_spans_match_the_inference_strip_exactly() -> None:
    """The capture form must find the same markers the strip removes.

    If the two ever disagree, generated source survives in one path and not
    the other, which is precisely the leak the corpus exists to prevent.
    """
    capture = re.compile(r"<!--\s*cfy-ui:(.*?)-->", re.IGNORECASE | re.DOTALL)
    strip = chat_attachments._UI_ARTIFACT_MARKER_RE

    samples = [
        "<!-- cfy-ui:AAA -->",
        "<!--   cfy-ui:AAA   -->",
        "<!-- CFY-UI:AAA -->",
        "prose\n<!-- cfy-ui:AAA -->\nmore prose",
        "<!-- cfy-ui:AAA --> and <!-- cfy-ui:BBB -->",
        "<!-- cfy-ui:unterminated",
        "no marker here",
        "<!-- cfy-ui:{\"a\":1} -->",
    ]
    for sample in samples:
        capture_spans = [match.span() for match in capture.finditer(sample)]
        strip_spans = [match.span() for match in strip.finditer(sample)]
        assert capture_spans == strip_spans, sample


def test_unterminated_marker_never_parses() -> None:
    content = "Prose.\n<!-- cfy-ui:%7B%22version%22%3A1%2C%22kind%22\nTail."
    assert parse_ui_artifacts(content) == []
    assert extract_ui_artifact_markers(content) == []


def test_invalid_marker_is_retained_but_not_counted_as_a_valid_artifact() -> None:
    """The eligibility service must be able to name a malformed marker."""
    content = (
        "<!-- cfy-ui:not-a-payload -->\n"
        + _marker(_sandbox())
    )
    markers = extract_ui_artifact_markers(content)
    assert len(markers) == 2
    assert markers[0].artifact is None
    assert markers[0].valid_artifact_index is None
    assert markers[1].artifact is not None
    assert markers[1].valid_artifact_index == 0


# ---------------------------------------------------------------------------
# E1 and E6: envelope structure and size caps
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "payload",
    [
        {"kind": "sandbox", "html": "<p>x</p>"},  # missing version
        {"version": "1", "kind": "sandbox", "html": "<p>x</p>"},  # string version
        {"version": 2, "kind": "sandbox", "html": "<p>x</p>"},  # unknown version
        {"version": 1, "kind": "sandbox"},  # missing html
        {"version": 1, "kind": "sandbox", "html": "   "},  # blank html
        {"version": 1, "kind": "sandbox", "html": 42},  # non-string html
        {"version": 1, "kind": "sandbox", "html": "<p>x</p>", "layout": "tall"},
        {"version": 1, "kind": "sandbox", "html": "<p>x</p>", "layout": None},
        {"version": 1, "kind": "sandbox", "html": "<p>x</p>", "initialHeight": "tall"},
        {"version": 1, "kind": "native", "component": "chart.bar", "props": None},
        {"version": 1, "kind": "native", "component": "chart.bar", "props": "no"},
        {"version": 1, "kind": "native", "component": "", "props": {}},
        {"version": 1, "kind": "unknown", "html": "<p>x</p>"},
        [1, 2, 3],
        "scalar",
        42,
    ],
)
def test_malformed_envelopes_fail_closed(payload: Any) -> None:
    assert validate_ui_artifact(payload) is None


def test_oversized_fields_fail_closed() -> None:
    """The corpus carries a placeholder for this; assert the real path."""
    oversized_html = _sandbox(html="x" * (MAX_SANDBOX_HTML_CHARS + 1))
    assert validate_ui_artifact(oversized_html) is None
    assert REASON_SIZE_LIMIT_EXCEEDED in _reasons(None, decoded_payload=oversized_html)

    oversized_css = _sandbox(css="x" * (MAX_SANDBOX_STYLE_CHARS + 1))
    assert validate_ui_artifact(oversized_css) is None

    oversized_js = _sandbox(js="x" * (MAX_SANDBOX_SCRIPT_CHARS + 1))
    assert validate_ui_artifact(oversized_js) is None

    oversized_title = _sandbox(title="t" * (MAX_TITLE_CHARS + 1))
    assert validate_ui_artifact(oversized_title) is None

    oversized_props = {
        "version": 1,
        "kind": "native",
        "component": "chart.bar",
        "props": {"blob": "x" * (MAX_NATIVE_PROPS_CHARS + 1)},
    }
    assert validate_ui_artifact(oversized_props) is None


def test_size_violations_are_reported_independently_of_structure() -> None:
    """E6 must be provable on its own, not only as a side effect of E1."""
    oversized = _sandbox(html="x" * (MAX_SANDBOX_HTML_CHARS + 1))
    reasons, _ = evaluate_eligibility(None, decoded_payload=oversized)
    assert REASON_SIZE_LIMIT_EXCEEDED in reasons
    assert REASON_ENVELOPE_INVALID in reasons


def test_unicode_length_boundary_counts_utf16_code_units() -> None:
    """JavaScript String.length counts UTF-16 code units, not code points.

    A length check written in code points would accept a title that the
    frontend rejects, which is exactly the divergence the corpus catches.
    """
    at_limit = _sandbox(title="\U0001f600" * 100)  # 200 code units
    assert validate_ui_artifact(at_limit) is not None

    over_limit = _sandbox(title="\U0001f600" * 101)  # 202 code units
    assert validate_ui_artifact(over_limit) is None


def test_optional_fields_are_normalized_like_the_frontend() -> None:
    artifact = validate_ui_artifact(_sandbox(css="  ", title="  spaced  "))
    assert artifact is not None
    # A whitespace-only stylesheet is dropped, exactly as the frontend does.
    assert "css" not in artifact
    assert artifact["title"] == "spaced"
    assert "initialHeight" not in artifact


def test_string_initial_height_coerces_the_way_javascript_does() -> None:
    artifact = validate_ui_artifact(_sandbox(initialHeight="320"))
    assert artifact is not None
    assert artifact["initialHeight"] == 320


# ---------------------------------------------------------------------------
# E2: kind
# ---------------------------------------------------------------------------


def test_native_artifact_is_structurally_valid_but_not_a_v1_candidate() -> None:
    """A native artifact parses. It is still not a Saved Widget candidate."""
    native = {
        "version": 1,
        "kind": "native",
        "component": "chart.bar",
        "props": {"series": [{"label": "Mon", "value": 42}]},
    }
    artifact = validate_ui_artifact(native)
    assert artifact is not None, "a native envelope is structurally valid"

    reasons = _reasons(artifact)
    assert REASON_KIND_NOT_SANDBOX in reasons
    assert REASON_MISSING_EXECUTABLE_CODE not in reasons


def test_unknown_native_component_is_still_structurally_valid() -> None:
    """The registry rejects an unregistered id at render time, not parse time."""
    native = {"version": 1, "kind": "native", "component": "evil.shell", "props": {}}
    assert validate_ui_artifact(native) is not None


# ---------------------------------------------------------------------------
# E3: executable behavior
# ---------------------------------------------------------------------------


def test_html_only_card_is_not_a_candidate() -> None:
    artifact = validate_ui_artifact(
        {"version": 1, "kind": "sandbox", "html": "<p>informational only</p>"}
    )
    assert artifact is not None, "an HTML-only card is structurally valid"
    reasons = _reasons(artifact)
    assert REASON_MISSING_EXECUTABLE_CODE in reasons


def test_empty_executable_code_is_not_a_candidate() -> None:
    artifact = validate_ui_artifact(_sandbox(js=""))
    assert artifact is not None
    assert REASON_MISSING_EXECUTABLE_CODE in _reasons(artifact)


def test_whitespace_only_executable_code_is_not_a_candidate() -> None:
    artifact = validate_ui_artifact(_sandbox(js="   \n  "))
    assert artifact is not None
    assert REASON_MISSING_EXECUTABLE_CODE in _reasons(artifact)


def test_inline_event_handler_text_is_not_executable_behavior() -> None:
    """Markup that merely looks interactive is not a reusable program."""
    artifact = validate_ui_artifact(
        {
            "version": 1,
            "kind": "sandbox",
            "html": "<button onclick='steal()'>go</button>",
        }
    )
    assert artifact is not None
    reasons = _reasons(artifact)
    assert REASON_MISSING_EXECUTABLE_CODE in reasons
    assert REASON_EXTERNAL_DEPENDENCY not in reasons


# ---------------------------------------------------------------------------
# E4: declared dependencies
# ---------------------------------------------------------------------------


def test_self_contained_sandbox_passes_the_dependency_gate() -> None:
    artifact = validate_ui_artifact(
        _sandbox(
            html="<button id='go'>go</button>",
            css="button { color: red; }",
            js="document.getElementById('go').onclick = function () {};",
        )
    )
    assert artifact is not None
    reasons, findings = evaluate_eligibility(artifact, decoded_payload=artifact)
    assert REASON_EXTERNAL_DEPENDENCY not in reasons
    assert REASON_AMBIGUOUS_DEPENDENCY not in reasons
    assert findings == ()


@pytest.mark.parametrize(
    "html",
    [
        "<script src='https://cdn.example.com/lib.js'></script>",
        "<link rel='stylesheet' href='https://cdn.example.com/lib.css'>",
        "<img src='https://cdn.example.com/logo.png'>",
        "<iframe src='https://example.com/frame'></iframe>",
        "<script src='//cdn.example.com/lib.js'></script>",
        "<form action='https://example.com/collect'></form>",
    ],
)
def test_known_external_dependencies_fail_e4(html: str) -> None:
    artifact = validate_ui_artifact(_sandbox(html=html))
    assert artifact is not None
    reasons, findings = evaluate_eligibility(artifact, decoded_payload=artifact)
    assert REASON_EXTERNAL_DEPENDENCY in reasons
    assert findings, "an external dependency must be reported"


def test_external_stylesheet_import_fails_e4() -> None:
    artifact = validate_ui_artifact(
        _sandbox(css="@import url('https://cdn.example.com/base.css');")
    )
    assert artifact is not None
    reasons, _ = evaluate_eligibility(artifact, decoded_payload=artifact)
    assert REASON_EXTERNAL_DEPENDENCY in reasons


def test_external_module_specifier_fails_e4() -> None:
    artifact = validate_ui_artifact(
        _sandbox(js="import { thing } from 'https://cdn.example.com/mod.js';")
    )
    assert artifact is not None
    reasons, _ = evaluate_eligibility(artifact, decoded_payload=artifact)
    assert REASON_EXTERNAL_DEPENDENCY in reasons


def test_unavailable_local_dependencies_fail_e4() -> None:
    """A local-looking reference is not a self-contained reference.

    Generated UI ships no asset package and the runtime serves no additional
    files, so a scheme-less reference cannot resolve to anything the frame
    could load. It is therefore a known *unavailable* dependency, not a
    dependency that happens to be local and therefore fine.
    """
    artifact = validate_ui_artifact(
        _sandbox(
            html="<script src='./local.js'></script><img src='data:image/png;base64,AA'>",
            css="@import url('./base.css');",
            js="const mod = require('./helper.js');",
        )
    )
    assert artifact is not None
    reasons, findings = evaluate_eligibility(artifact, decoded_payload=artifact)
    assert REASON_UNAVAILABLE_LOCAL_DEPENDENCY in reasons
    assert REASON_EXTERNAL_DEPENDENCY not in reasons
    assert REASON_AMBIGUOUS_DEPENDENCY not in reasons
    assert findings


@pytest.mark.parametrize(
    "field,value",
    [
        # Root-relative
        ("html", "<img src='/assets/logo.png'>"),
        # Dot-relative
        ("html", "<script src='./local.js'></script>"),
        # Parent-relative
        ("html", "<img src='../shared/module.js'>"),
        # Bare filename
        ("html", "<img src='logo.png'>"),
        # Bare module specifier
        ("js", "import { thing } from 'lodash';"),
        # Query-relative asset path
        ("html", "<img src='?resource=module.js'>"),
        # Relative stylesheet import on the CSS surface
        ("css", "@import url('./base.css');"),
        # Relative stylesheet import on the HTML link surface
        ("html", "<link rel='stylesheet' href='./base.css'>"),
        # Relative CSS url()
        ("css", "body { background: url('./bg.png'); }"),
        # Relative JavaScript module import
        ("js", "import { thing } from './mod.js';"),
        # Relative JavaScript require()
        ("js", "const mod = require('./helper.js');"),
        # Inline style resource reference
        ("html", "<div style=\"background: url('./bg.png')\"></div>"),
    ],
)
def test_every_unsupported_local_resource_category_fails_e4(
    field: str, value: str
) -> None:
    """Each supported relative-resource category is rejected by E4.

    The list mirrors the declaration surfaces the validator already inspected.
    A new surface is not added here; the correction only changes how a
    scheme-less reference on an existing surface is classified.
    """
    artifact = validate_ui_artifact(_sandbox(**{field: value}))
    assert artifact is not None
    reasons, findings = evaluate_eligibility(artifact, decoded_payload=artifact)
    assert REASON_UNAVAILABLE_LOCAL_DEPENDENCY in reasons
    assert REASON_EXTERNAL_DEPENDENCY not in reasons
    assert REASON_AMBIGUOUS_DEPENDENCY not in reasons
    assert findings
    assert all(finding.kind == "unavailable_local" for finding in findings)


def test_an_unavailable_local_resource_reports_its_own_reason_and_finding() -> None:
    """The failure names what is actually wrong.

    An unavailable local resource is neither external (it names no other
    origin) nor ambiguous (its status is known), so it gets its own reason
    code and its own finding kind.
    """
    artifact = validate_ui_artifact(_sandbox(html="<img src='./logo.png'>"))
    assert artifact is not None
    reasons, findings = evaluate_eligibility(artifact, decoded_payload=artifact)
    assert reasons == (REASON_UNAVAILABLE_LOCAL_DEPENDENCY,)
    assert len(findings) == 1
    finding = findings[0]
    assert finding.kind == "unavailable_local"
    assert finding.reference == "./logo.png"
    assert finding.surface == "html"
    assert finding.detail == "img[src]"
    assert set(finding.as_dict()) == {"surface", "detail", "reference", "kind"}


def test_external_and_unavailable_local_dependencies_are_reported_separately() -> None:
    """The two known-unsupported cases keep distinct reason codes."""
    artifact = validate_ui_artifact(
        _sandbox(
            html="<script src='https://cdn.example.com/lib.js'></script>",
            css="@import url('./base.css');",
        )
    )
    assert artifact is not None
    reasons, findings = evaluate_eligibility(artifact, decoded_payload=artifact)
    assert REASON_EXTERNAL_DEPENDENCY in reasons
    assert REASON_UNAVAILABLE_LOCAL_DEPENDENCY in reasons
    assert {finding.kind for finding in findings} == {
        "external",
        "unavailable_local",
    }


@pytest.mark.parametrize(
    "html",
    [
        # A same-document fragment consumes no additional document.
        "<img src='#icon'>",
        "<link rel='stylesheet' href='#theme'>",
        # Local schemes that carry their own content.
        "<img src='data:image/png;base64,AA'>",
        "<img src='blob:https://example.com/id'>",
    ],
)
def test_same_document_and_self_carrying_references_remain_eligible(
    html: str,
) -> None:
    """The correction does not sweep up references that need nothing loaded."""
    artifact = validate_ui_artifact(_sandbox(html=html))
    assert artifact is not None
    reasons, findings = evaluate_eligibility(artifact, decoded_payload=artifact)
    assert reasons == ()
    assert findings == ()


def test_incidental_relative_paths_are_not_dependencies() -> None:
    """A relative path in prose, a comment, or a string is not a declaration."""
    artifact = validate_ui_artifact(
        _sandbox(
            html="<p>Read ./docs/guide.md for details.</p><!-- see ./docs/guide.md -->",
            js="var p = './docs/guide.md'; void p;",
        )
    )
    assert artifact is not None
    reasons, findings = evaluate_eligibility(artifact, decoded_payload=artifact)
    assert REASON_UNAVAILABLE_LOCAL_DEPENDENCY not in reasons
    assert findings == ()


def test_incidental_relative_path_in_a_javascript_comment_is_not_a_dependency() -> None:
    artifact = validate_ui_artifact(_sandbox(js="// see ./docs/guide.md\nvoid 0;"))
    assert artifact is not None
    reasons, findings = evaluate_eligibility(artifact, decoded_payload=artifact)
    assert REASON_UNAVAILABLE_LOCAL_DEPENDENCY not in reasons
    assert findings == ()


def test_anchor_hrefs_are_not_treated_as_resource_dependencies() -> None:
    """The correction does not widen the inspected surface.

    An ``a[href]`` is navigation, not a resource load, so it stays outside
    the dependency gate even when it is relative.
    """
    artifact = validate_ui_artifact(_sandbox(html="<a href='./other.html'>go</a>"))
    assert artifact is not None
    reasons, findings = evaluate_eligibility(artifact, decoded_payload=artifact)
    assert reasons == ()
    assert findings == ()


def test_unavailable_local_dependency_evaluation_is_deterministic() -> None:
    artifact = validate_ui_artifact(_sandbox(html="<img src='./logo.png'>"))
    assert artifact is not None
    first = evaluate_eligibility(artifact, decoded_payload=artifact)
    second = evaluate_eligibility(artifact, decoded_payload=artifact)
    assert first == second
    assert first[0] == (REASON_UNAVAILABLE_LOCAL_DEPENDENCY,)


def test_an_e4_rejected_artifact_is_ineligible_after_provenance_is_proven(
    monkeypatch,
) -> None:
    """E4 still fires once E5 has been established.

    The provenance lookup is stubbed so this suite stays database-free; the
    artifact-side evaluation and the reason-to-status mapping are the real
    production code. A structurally valid artifact with an unavailable
    relative dependency is *ineligible*, not structurally invalid.
    """
    core_db = pytest.importorskip("guardian.core.db")

    artifact_payload = _sandbox(html="<img src='./logo.png'>")
    content = _marker(artifact_payload)

    def _stub_provenance(chatlog_db, *, thread_id, message_id, account_id):
        return {
            "resolved": True,
            "content": content,
            "thread_id": thread_id,
            "message_id": message_id,
            "attempts": [
                {
                    "request_id": "req-e4-unavailable-local",
                    "accepted_at": "2026-10-26T00:00:00+00:00",
                    "terminal_event_type": None,
                }
            ],
        }

    monkeypatch.setattr(
        core_db,
        "read_saved_widget_source_provenance",
        _stub_provenance,
        raising=True,
    )

    assessment = assess_saved_widget_candidate(
        None,
        account_id="saved-widget-account-a",
        thread_id=1,
        message_id=2,
    )

    assert assessment.status is WidgetCandidateStatus.INELIGIBLE
    assert assessment.status is not WidgetCandidateStatus.STRUCTURALLY_INVALID
    assert assessment.reasons == (REASON_UNAVAILABLE_LOCAL_DEPENDENCY,)
    # E5 was proven; only the artifact-side gate failed.
    assert assessment.lineage is not None
    assert [
        (finding.kind, finding.reference)
        for finding in assessment.dependency_findings
    ] == [("unavailable_local", "./logo.png")]


def test_incidental_url_in_an_html_comment_is_not_a_dependency() -> None:
    artifact = validate_ui_artifact(
        _sandbox(html="<!-- see https://example.com/docs for details --><p>x</p>")
    )
    assert artifact is not None
    reasons, findings = evaluate_eligibility(artifact, decoded_payload=artifact)
    assert REASON_EXTERNAL_DEPENDENCY not in reasons
    assert findings == ()


def test_incidental_url_in_text_content_is_not_a_dependency() -> None:
    artifact = validate_ui_artifact(
        _sandbox(html="<p>Read https://example.com/docs for details.</p>")
    )
    assert artifact is not None
    reasons, findings = evaluate_eligibility(artifact, decoded_payload=artifact)
    assert REASON_EXTERNAL_DEPENDENCY not in reasons
    assert findings == ()


def test_incidental_url_in_a_javascript_string_is_not_a_dependency() -> None:
    """A URL in a string is not a declared dependency."""
    artifact = validate_ui_artifact(
        _sandbox(js="var link = 'https://example.com/docs'; void link;")
    )
    assert artifact is not None
    reasons, findings = evaluate_eligibility(artifact, decoded_payload=artifact)
    assert REASON_EXTERNAL_DEPENDENCY not in reasons
    assert findings == ()


def test_incidental_url_in_a_javascript_comment_is_not_a_dependency() -> None:
    artifact = validate_ui_artifact(
        _sandbox(js="// see https://example.com/docs\nvoid 0;")
    )
    assert artifact is not None
    reasons, findings = evaluate_eligibility(artifact, decoded_payload=artifact)
    assert REASON_EXTERNAL_DEPENDENCY not in reasons
    assert findings == ()


def test_ambiguous_dependency_declaration_fails_closed() -> None:
    """A declaration that cannot be classified is not treated as safe."""
    artifact = validate_ui_artifact(
        _sandbox(html="<script src='%zz-not-a-valid-escape'></script>")
    )
    assert artifact is not None
    reasons, findings = evaluate_eligibility(artifact, decoded_payload=artifact)
    assert REASON_AMBIGUOUS_DEPENDENCY in reasons
    assert findings


def test_regular_expression_literal_is_not_mistaken_for_a_comment() -> None:
    """A regex body containing // must not hide a later module declaration."""
    artifact = validate_ui_artifact(
        _sandbox(
            js="var re = /\\/\\//;\nimport { x } from 'https://cdn.example.com/m.js';"
        )
    )
    assert artifact is not None
    reasons, _ = evaluate_eligibility(artifact, decoded_payload=artifact)
    assert REASON_EXTERNAL_DEPENDENCY in reasons


def test_regular_expression_literal_alone_is_not_a_dependency() -> None:
    artifact = validate_ui_artifact(
        _sandbox(js="var re = /https?:\\/\\/\\//; void re;")
    )
    assert artifact is not None
    reasons, findings = evaluate_eligibility(artifact, decoded_payload=artifact)
    assert REASON_EXTERNAL_DEPENDENCY not in reasons
    assert findings == ()


def test_e4_makes_no_false_network_safety_claim() -> None:
    """E4 is a packaging filter. It must not report network safety.

    A payload can attempt a network request at runtime, and no static
    inspection can rule that out. The module must therefore name the real
    control rather than implying the artifact is network-safe.
    """
    artifact = validate_ui_artifact(
        _sandbox(js="fetch('https://example.com/data').then(r => r.json());")
    )
    assert artifact is not None
    reasons, findings = evaluate_eligibility(artifact, decoded_payload=artifact)

    # A runtime fetch is not a declared dependency, so E4 does not fire.
    assert REASON_EXTERNAL_DEPENDENCY not in reasons
    assert findings == ()

    # And the assessment names the actual enforcement boundary instead of
    # claiming the artifact is safe.
    from guardian.core.saved_widget_validation import WidgetCandidateAssessment

    assessment = WidgetCandidateAssessment(
        status=WidgetCandidateStatus.ELIGIBLE, artifact=artifact
    )
    assert assessment.network_denial_boundary == NETWORK_DENIAL_BOUNDARY
    assert assessment.network_denial_boundary == "sandbox-csp"
    assert "network_safe" not in assessment.as_dict()
    assert "network_safety" not in assessment.as_dict()


def test_dependency_findings_are_bounded_and_structured() -> None:
    artifact = validate_ui_artifact(
        _sandbox(html="<script src='https://cdn.example.com/lib.js'></script>")
    )
    assert artifact is not None
    _, findings = evaluate_eligibility(artifact, decoded_payload=artifact)
    assert len(findings) == 1
    finding = findings[0]
    assert finding.surface == "html"
    assert finding.kind == "external"
    assert "cdn.example.com" in finding.reference
    assert set(finding.as_dict()) == {"surface", "detail", "reference", "kind"}


# ---------------------------------------------------------------------------
# Determinism
# ---------------------------------------------------------------------------


def test_evaluation_is_deterministic() -> None:
    artifact = validate_ui_artifact(_sandbox())
    assert artifact is not None
    first = evaluate_eligibility(artifact, decoded_payload=artifact)
    second = evaluate_eligibility(artifact, decoded_payload=artifact)
    assert first == second


def test_validation_never_executes_artifact_content() -> None:
    """The module parses; it does not run. A payload that would explode if
    evaluated is still only ever decoded as text."""
    payload = _sandbox(js="raise SystemExit('should never run');")
    artifact = validate_ui_artifact(payload)
    assert artifact is not None
    reasons, _ = evaluate_eligibility(artifact, decoded_payload=artifact)
    assert reasons == ()
