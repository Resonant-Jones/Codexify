"""Tests for heartbeat Makefile targets and package scripts."""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
MAKEFILE = ROOT / "Makefile"
PACKAGE_JSON = ROOT / "package.json"


def _read_makefile() -> str:
    return MAKEFILE.read_text(encoding="utf-8")


def _read_package_json() -> dict:
    return json.loads(PACKAGE_JSON.read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# heartbeat-full target exists
# ---------------------------------------------------------------------------

def test_heartbeat_full_target_exists() -> None:
    content = _read_makefile()
    assert re.search(r"^heartbeat-full:", content, re.MULTILINE), (
        "heartbeat-full target not found in Makefile"
    )


# ---------------------------------------------------------------------------
# heartbeat-full is in .PHONY
# ---------------------------------------------------------------------------

def test_heartbeat_full_is_phony() -> None:
    content = _read_makefile()
    phony_line = [l for l in content.splitlines() if l.startswith(".PHONY:")][0]
    assert "heartbeat-full" in phony_line, (
        f"heartbeat-full not in .PHONY: {phony_line[:80]}..."
    )


# ---------------------------------------------------------------------------
# heartbeat-full invokes each child target in order
# ---------------------------------------------------------------------------

def test_heartbeat_full_invokes_child_targets_in_order() -> None:
    content = _read_makefile()
    # Extract the heartbeat-full recipe
    match = re.search(
        r"^heartbeat-full:\n((?:\t.*\n?)*)",
        content,
        re.MULTILINE,
    )
    assert match, "heartbeat-full recipe not found"
    recipe = match.group(1)

    # Each child target should appear in the correct order
    child_order = ["heartbeat", "heartbeat-review", "heartbeat-stage", "heartbeat-outbox"]
    positions = {}
    for child in child_order:
        # Find the $(MAKE) invocation for this child
        # Pattern: $(MAKE) heartbeat or $(MAKE) heartbeat-review etc.
        pattern = rf"\$\(MAKE\)\s+{child}"
        m = re.search(pattern, recipe)
        assert m, f"{child} not invoked via $(MAKE) in heartbeat-full"
        positions[child] = m.start()

    # Verify order
    for i in range(len(child_order) - 1):
        assert positions[child_order[i]] < positions[child_order[i + 1]], (
            f"{child_order[i]} must come before {child_order[i+1]}"
        )


# ---------------------------------------------------------------------------
# heartbeat-full stops on first failure
# ---------------------------------------------------------------------------

def test_heartbeat_full_stops_on_first_failure() -> None:
    content = _read_makefile()
    match = re.search(
        r"^heartbeat-full:\n((?:\t.*\n?)*)",
        content,
        re.MULTILINE,
    )
    assert match
    recipe = match.group(1)

    # Each $(MAKE) call should be followed by || { echo ERROR... exit 1 }
    # This ensures stop-on-first-failure semantics
    make_calls = re.findall(r"\$\(MAKE\)\s+\S+", recipe)
    assert len(make_calls) >= 4, f"Expected at least 4 $(MAKE) calls, got {len(make_calls)}"

    # Each call should have error handling
    for call in make_calls:
        call_escaped = re.escape(call)
        # After each make call there should be error handling
        has_error_handling = bool(re.search(
            rf"{call_escaped}\s*(?:.*?\|\|.*?exit\s+1)",
            recipe,
        ))
        assert has_error_handling, f"No error handling after {call}"


# ---------------------------------------------------------------------------
# Pass-through variables: DATE, DEV_BLOG_SOURCE, INSIGHT_SOURCE, FORCE, STRICT
# are all passed via $(MAKE) variable inheritance
# ---------------------------------------------------------------------------

def test_date_passes_through_via_make_variable_inheritance() -> None:
    """DATE is inherited by child $(MAKE) invocations automatically."""
    content = _read_makefile()
    match = re.search(
        r"^heartbeat-full:\n((?:\t.*\n?)*)",
        content,
        re.MULTILINE,
    )
    assert match
    recipe = match.group(1)

    # Each child target uses $$DATE (or equivalent), so passing DATE at
    # the heartbeat-full level will inherit to all children automatically.
    # This test verifies the recipe uses $(MAKE) (which inherits variables).
    assert "$(MAKE)" in recipe

    # Verify key variables are documented in the comment block above heartbeat-full
    full_start = content.index("heartbeat-full:")
    # Get all content before heartbeat-full target definition (its comment block)
    pre_content = content[:full_start]
    # Find the last comment block (the one immediately before heartbeat-full)
    comment_blocks = pre_content.split("\n\n")
    last_block = comment_blocks[-1] if comment_blocks else ""
    # Also check the recipe comments
    check_text = last_block + "\n" + recipe
    for var in ("DATE", "FORCE", "STRICT", "DEV_BLOG_SOURCE", "INSIGHT_SOURCE"):
        assert var in check_text, f"{var} not documented in heartbeat-full target/comments"


# ---------------------------------------------------------------------------
# FORCE=1 and STRICT=1 are documented as pass-through
# ---------------------------------------------------------------------------

def test_force_and_strict_are_documented_pass_through() -> None:
    content = _read_makefile()
    # Get the comment block before heartbeat-full
    full_start = content.index("heartbeat-full:")
    comment_block = content[:full_start].split("\n")[-15:]

    vars_found = {"FORCE": False, "STRICT": False, "DATE": False}
    for line in comment_block:
        for var in vars_found:
            if var in line:
                vars_found[var] = True

    for var, found in vars_found.items():
        assert found, f"{var} not documented as pass-through in heartbeat-full comments"


# ---------------------------------------------------------------------------
# package.json includes heartbeat:full
# ---------------------------------------------------------------------------

def test_package_json_includes_heartbeat_full() -> None:
    pkg = _read_package_json()
    scripts = pkg.get("scripts", {})
    assert "heartbeat:full" in scripts, (
        f"heartbeat:full not found in package.json scripts"
    )


# ---------------------------------------------------------------------------
# heartbeat:full references Makefile target, not duplicated logic
# ---------------------------------------------------------------------------

def test_heartbeat_full_package_script_references_makefile() -> None:
    pkg = _read_package_json()
    script = pkg["scripts"]["heartbeat:full"]
    assert "make heartbeat-full" in script, (
        f"heartbeat:full script should delegate to make heartbeat-full, got: {script}"
    )


# ---------------------------------------------------------------------------
# Child targets are not inline-duplicated — they use $(MAKE)
# ---------------------------------------------------------------------------

def test_heartbeat_full_does_not_inline_child_logic() -> None:
    """The full target must invoke child targets via $(MAKE), not duplicate their logic."""
    content = _read_makefile()
    match = re.search(
        r"^heartbeat-full:\n((?:\t.*\n?)*)",
        content,
        re.MULTILINE,
    )
    assert match
    recipe = match.group(1)

    # Should not contain direct Python invocations
    py_calls = re.findall(r"\$\(PYTHON\)\s+scripts", recipe)
    assert len(py_calls) == 0, (
        f"heartbeat-full should not inline Python calls, found: {py_calls}"
    )
