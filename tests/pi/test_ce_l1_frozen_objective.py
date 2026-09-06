"""CE-L1 v1 frozen objective byte-integrity regression.

The 42-byte target sequence ``CE_L1_POST_INSTRUMENTATION_DRIVER_PASS_OK``
is wrapped in a 210-byte immutable control description in
``tests/pi/fixtures/ce_l1/frozen_objective_v1.txt``.

This fixture is the sole byte authority for the CE-L1 v1 frozen objective. It
was recovered after the original disposable ``/tmp`` driver was lost and
must not be retype-reconstructed.

This regression protects durability and byte identity only. It does not prove
CE-L1 execution and does not authorize any provider call.

Any future CE-L1 objective change requires a new versioned fixture (for
example ``frozen_objective_v2.txt``) rather than mutating ``v1``.
"""
from __future__ import annotations

import hashlib
from pathlib import Path

import pytest


FROZEN_OBJECTIVE_SHA256 = (
    "007c158087abd81234209e93b1cdde3cc37ede1e8437defd0b05a9a3a4c56a0c"
)
FROZEN_OBJECTIVE_SIZE = 210
FROZEN_OBJECTIVE_TRAILING_LF = False
FROZEN_OBJECTIVE_FIXTURE_PATH = (
    Path(__file__).parent / "fixtures" / "ce_l1" / "frozen_objective_v1.txt"
)
FROZEN_OBJECTIVE_MARKER = "CE_L1_POST_INSTRUMENTATION_DRIVER_PASS_OK"


def _read_frozen_objective() -> bytes:
    assert FROZEN_OBJECTIVE_FIXTURE_PATH.is_file(), (
        f"Missing frozen-objective fixture: {FROZEN_OBJECTIVE_FIXTURE_PATH}"
    )
    return FROZEN_OBJECTIVE_FIXTURE_PATH.read_bytes()


def test_frozen_objective_byte_count_is_210() -> None:
    data = _read_frozen_objective()
    assert len(data) == FROZEN_OBJECTIVE_SIZE, (
        f"Expected {FROZEN_OBJECTIVE_SIZE} bytes, got {len(data)}"
    )


def test_frozen_objective_sha256_matches() -> None:
    data = _read_frozen_objective()
    assert hashlib.sha256(data).hexdigest() == FROZEN_OBJECTIVE_SHA256, (
        f"Expected SHA {FROZEN_OBJECTIVE_SHA256}, got "
        f"{hashlib.sha256(data).hexdigest()}"
    )


def test_frozen_objective_has_no_trailing_newline() -> None:
    data = _read_frozen_objective()
    assert data.endswith(b"\n") is FROZEN_OBJECTIVE_TRAILING_LF, (
        f"Trailing newline posture must be {FROZEN_OBJECTIVE_TRAILING_LF}"
    )


def test_frozen_objective_is_ascii() -> None:
    data = _read_frozen_objective()
    assert data.isascii(), "Frozen objective must remain ASCII / UTF-8 text"


def test_frozen_objective_contains_marker() -> None:
    data = _read_frozen_objective()
    assert FROZEN_OBJECTIVE_MARKER.encode("ascii") in data, (
        f"Marker {FROZEN_OBJECTIVE_MARKER!r} must be present in frozen objective"
    )


def test_frozen_objective_test_does_not_duplicate_full_objective_text() -> None:
    """The full objective text must live only in the fixture.

    This test must not inline the complete objective string to avoid
    turning the test file into a second source of authority.
    """
    import re
    from pathlib import Path

    self_path = Path(__file__).read_text()
    # The marker is intentionally allowed to appear once for assertion
    # purposes, but the full sentence spanning from "Replace the entire
    # contents" to the closing apostrophe must not be duplicated in this
    # test source file.
    full_pattern = re.compile(
        r"Replace the entire contents of proof_target\.txt.*'CE_L1_POST_INSTRUMENTATION_DRIVER_PASS_OK'",
        re.DOTALL,
    )
    assert not full_pattern.search(self_path), (
        "Full frozen-objective sentence must not be duplicated in the test"
    )
