from dataclasses import FrozenInstanceError

import pytest

from guardian.queue.redis_queue import _deserialize, _serialize
from guardian.tasks.types import (
    ChatCompletionTask,
    PersonaSelectionSnapshot,
    task_from_dict,
)


@pytest.mark.parametrize(
    "profile_id,revision", [("axis", 2), ("local_mode", None), (None, None)]
)
def test_selection_round_trips_through_queue_contract(profile_id, revision):
    snapshot = PersonaSelectionSnapshot(profile_id, revision)
    task = ChatCompletionTask(user_id="owner", persona_selection_snapshot=snapshot)
    payload = _deserialize(_serialize(task))
    assert payload["persona_selection_snapshot"] == {
        "profile_id": profile_id,
        "profile_revision": revision,
    }
    restored = task_from_dict(payload)
    assert restored.persona_selection_snapshot == snapshot
    assert restored.to_dict() == task.to_dict()


def test_legacy_absence_stays_distinct_from_explicit_no_profile():
    task = task_from_dict({"type": "chat_completion", "user_id": "owner"})
    assert task.persona_selection_snapshot is None
    assert task_from_dict(task.to_dict()).persona_selection_snapshot is None
    assert PersonaSelectionSnapshot(None, None) is not None


@pytest.mark.parametrize(
    "payload",
    [
        {},
        [],
        "axis",
        1,
        {"profile_id": "axis"},
        {"profile_id": "axis", "profile_revision": 1, "owner": "forged"},
        *(
            {"profile_id": "axis", "profile_revision": value}
            for value in [0, -1, True, "1", 1.0, 1.5]
        ),
        {"profile_id": None, "profile_revision": 1},
        *(
            {"profile_id": value, "profile_revision": None}
            for value in ["", "  ", 1, True, {}]
        ),
    ],
)
def test_invalid_snapshots_are_rejected_at_construction_and_deserialization(payload):
    with pytest.raises(ValueError):
        ChatCompletionTask(user_id="owner", persona_selection_snapshot=payload)
    with pytest.raises(ValueError):
        task_from_dict(
            {
                "type": "chat_completion",
                "user_id": "owner",
                "persona_selection_snapshot": payload,
            }
        )


def test_snapshot_is_immutable():
    snapshot = PersonaSelectionSnapshot("axis", 1)
    with pytest.raises(FrozenInstanceError):
        snapshot.profile_revision = 2
