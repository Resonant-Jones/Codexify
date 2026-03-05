import uuid

from guardian.routes.voice import _normalize_turn_id


def test_normalize_turn_id_preserves_valid_uuid() -> None:
    turn_id = "A0EebC99-9C0B-4EF8-BB6D-6BB9BD380A11"

    normalized = _normalize_turn_id(turn_id)

    assert normalized == "a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11"


def test_normalize_turn_id_replaces_invalid_with_generated_uuid() -> None:
    normalized = _normalize_turn_id("not-a-uuid")

    parsed = uuid.UUID(normalized)
    assert str(parsed) == normalized


def test_normalize_turn_id_missing_is_unique_per_request() -> None:
    first = _normalize_turn_id(None)
    second = _normalize_turn_id(None)

    assert first != second
    assert str(uuid.UUID(first)) == first
    assert str(uuid.UUID(second)) == second
