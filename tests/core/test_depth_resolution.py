"""Unit tests for chat depth-resolution contract."""

from __future__ import annotations

import pytest

from guardian.depth import (
    classify_project_identity_depth,
    normalize_project_identity_depth,
    normalize_requested_depth_raw,
    project_requested_depth_mode,
    resolve_depth,
)


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        (None, "deep"),
        ("deep", "deep"),
        ("  DEEP  ", "deep"),
        ("normal", "normal"),
        ("weird", "weird"),
    ],
)
def test_normalize_requested_depth_raw(raw, expected):
    assert normalize_requested_depth_raw(raw) == expected


@pytest.mark.parametrize(
    ("requested_raw", "expected"),
    [
        ("deep", "deep"),
        ("normal", "light"),
        ("diagnostic", "light"),
        ("weird", "light"),
    ],
)
def test_project_requested_depth_mode(requested_raw, expected):
    assert project_requested_depth_mode(requested_raw) == expected


@pytest.mark.parametrize(
    ("raw", "expected_norm", "expected_state"),
    [
        (None, "", "missing"),
        ("deep", "deep", "known"),
        ("  light  ", "light", "known"),
        ("DEEPER", "deeper", "malformed"),
    ],
)
def test_project_identity_depth_normalization_and_classification(
    raw, expected_norm, expected_state
):
    assert normalize_project_identity_depth(raw) == expected_norm
    assert classify_project_identity_depth(raw) == expected_state


def test_resolve_depth_non_deep_known_request():
    assert resolve_depth(
        "normal",
        thread_has_project=True,
        project_depth_state="known",
        project_identity_depth_norm="deep",
        policy_allows_deep=True,
    ) == ("light", None)


def test_resolve_depth_deep_no_project():
    assert resolve_depth(
        "deep",
        thread_has_project=False,
        project_depth_state="missing",
        project_identity_depth_norm="",
        policy_allows_deep=False,
    ) == ("light", "no_project")


def test_resolve_depth_deep_project_light():
    assert resolve_depth(
        "deep",
        thread_has_project=True,
        project_depth_state="known",
        project_identity_depth_norm="light",
        policy_allows_deep=False,
    ) == ("light", "project_identity_depth_light")


def test_resolve_depth_deep_project_deep_policy_rejected():
    assert resolve_depth(
        "deep",
        thread_has_project=True,
        project_depth_state="known",
        project_identity_depth_norm="deep",
        policy_allows_deep=False,
    ) == ("light", "policy_gate_rejected")


def test_resolve_depth_deep_project_deep_policy_allowed():
    assert resolve_depth(
        "deep",
        thread_has_project=True,
        project_depth_state="known",
        project_identity_depth_norm="deep",
        policy_allows_deep=True,
    ) == ("deep", None)


def test_resolve_depth_malformed_requested_is_unknown():
    assert resolve_depth(
        "not-a-depth",
        thread_has_project=False,
        project_depth_state="missing",
        project_identity_depth_norm="",
        policy_allows_deep=False,
    ) == ("light", "unknown")


def test_resolve_depth_malformed_project_depth_is_unknown():
    assert resolve_depth(
        "deep",
        thread_has_project=True,
        project_depth_state="malformed",
        project_identity_depth_norm="banana",
        policy_allows_deep=False,
    ) == ("light", "unknown")
