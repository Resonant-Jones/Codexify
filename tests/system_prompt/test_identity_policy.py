from guardian.cognition.identity_policy import (
    can_run_deep_identity_modeling,
    normalize_identity_depth,
    thread_blocks_identity_modeling,
)


def test_thread_blocks_identity_modeling_for_diary_mode():
    assert thread_blocks_identity_modeling({"diary_mode": True}) is True
    assert thread_blocks_identity_modeling({"is_diary": True}) is True


def test_thread_blocks_identity_modeling_for_modeling_excluded():
    assert thread_blocks_identity_modeling({"modeling_excluded": True}) is True
    assert (
        thread_blocks_identity_modeling({"exclude_from_identity": True}) is True
    )


def test_identity_depth_normalization_and_deep_gate():
    assert normalize_identity_depth("light") == "light"
    assert normalize_identity_depth("deep") == "deep"
    assert can_run_deep_identity_modeling("light") is False
    assert can_run_deep_identity_modeling("deep") is True
