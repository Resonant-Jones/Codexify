from __future__ import annotations

import subprocess
from pathlib import Path

from guardian.core.supported_profile import load_supported_profile


REPO_ROOT = Path(__file__).resolve().parents[2]
PROFILES_DIR = REPO_ROOT / "config" / "supported_profiles"
DEFAULT_PROFILE_NAME = "v1-local-core-web-mcp"
PROOF_PROFILE_NAME = "v1-user-profile-accent-proof"
DEFAULT_PROFILE_PATH = (
    PROFILES_DIR / f"{DEFAULT_PROFILE_NAME}.yaml"
)


def _profile_route_labels(profile) -> set[str]:
    return {
        *profile.enabled_routes,
        *profile.internal_only_routes,
        *profile.quarantined_routes,
    }


def _assert_route_sets_do_not_overlap(profile) -> None:
    enabled = set(profile.enabled_routes)
    internal_only = set(profile.internal_only_routes)
    quarantined = set(profile.quarantined_routes)
    assert not enabled & internal_only
    assert not enabled & quarantined
    assert not internal_only & quarantined


def test_user_profile_accent_proof_profile_loads() -> None:
    profile = load_supported_profile(
        PROOF_PROFILE_NAME,
        profiles_dir=str(PROFILES_DIR),
    )

    assert profile.name == PROOF_PROFILE_NAME
    assert profile.version == 1
    assert profile.surface == "internal-proof-only-local-docker-compose-webui"


def test_user_profile_route_posture_is_internal_only_and_default_is_quarantined() -> None:
    proof_profile = load_supported_profile(
        PROOF_PROFILE_NAME,
        profiles_dir=str(PROFILES_DIR),
    )
    default_profile = load_supported_profile(
        DEFAULT_PROFILE_NAME,
        profiles_dir=str(PROFILES_DIR),
    )

    assert proof_profile.route_status("user_profile") == "internal_only"
    assert default_profile.route_status("user_profile") == "quarantined"


def test_default_profile_file_is_unchanged_from_head() -> None:
    expected = subprocess.check_output(
        ["git", "show", f"HEAD:config/supported_profiles/{DEFAULT_PROFILE_NAME}.yaml"],
        cwd=REPO_ROOT,
    )

    assert DEFAULT_PROFILE_PATH.read_bytes() == expected


def test_proof_profile_changes_only_name_surface_and_user_profile_posture() -> None:
    proof_profile = load_supported_profile(
        PROOF_PROFILE_NAME,
        profiles_dir=str(PROFILES_DIR),
    )
    default_profile = load_supported_profile(
        DEFAULT_PROFILE_NAME,
        profiles_dir=str(PROFILES_DIR),
    )

    assert proof_profile.version == default_profile.version
    assert proof_profile.required_services == default_profile.required_services
    assert proof_profile.optional_services == default_profile.optional_services
    assert proof_profile.public_extensions == default_profile.public_extensions
    assert proof_profile.internal_extensions == default_profile.internal_extensions
    assert proof_profile.provider_contract == default_profile.provider_contract
    assert proof_profile.criticality == default_profile.criticality

    all_labels = _profile_route_labels(proof_profile) | _profile_route_labels(
        default_profile
    )
    for label in all_labels - {"user_profile"}:
        assert proof_profile.route_status(label) == default_profile.route_status(
            label
        )


def test_route_sets_are_disjoint_for_both_profiles() -> None:
    proof_profile = load_supported_profile(
        PROOF_PROFILE_NAME,
        profiles_dir=str(PROFILES_DIR),
    )
    default_profile = load_supported_profile(
        DEFAULT_PROFILE_NAME,
        profiles_dir=str(PROFILES_DIR),
    )

    _assert_route_sets_do_not_overlap(proof_profile)
    _assert_route_sets_do_not_overlap(default_profile)
