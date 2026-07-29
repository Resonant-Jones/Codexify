from __future__ import annotations

from dataclasses import fields

import pytest

from guardian.tasks.types import (
    ChatCompletionTask,
    HostedRoomInvocationMetadata,
    task_from_dict,
)


ROOM_ID = "11111111-1111-4111-8111-111111111111"
ACTOR_PARTICIPANT_ID = "22222222-2222-4222-8222-222222222222"
REQUESTER_PARTICIPANT_ID = "33333333-3333-4333-8333-333333333333"


def _owner_metadata() -> HostedRoomInvocationMetadata:
    return HostedRoomInvocationMetadata(
        room_id=ROOM_ID,
        source_message_id=123,
        actor_participant_id=ACTOR_PARTICIPANT_ID,
        actor_source="resident",
        actor_ref="guardian",
        requester_authority="owner",
        requester_participant_id=None,
    )


def _guest_metadata() -> HostedRoomInvocationMetadata:
    return HostedRoomInvocationMetadata(
        room_id=ROOM_ID,
        source_message_id=123,
        actor_participant_id=ACTOR_PARTICIPANT_ID,
        actor_source="resident",
        actor_ref="guardian",
        requester_authority="guest",
        requester_participant_id=REQUESTER_PARTICIPANT_ID,
    )


def _task_payload(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "task_id": "task-9c",
        "request_id": "req-9c",
        "type": "chat_completion",
        "created_at": "2026-07-28T00:00:00+00:00",
        "origin": "api:chat.complete|turn_id=turn-9c|source_mode=project",
        "user_id": "user-1",
        "thread_id": 7,
        "latest_turn_message_id": 123,
        "latest_turn_messages": [{"type": "text", "text": "hello"}],
        "provider": "local",
        "model": "test-model",
        "requested_provider": "local",
        "requested_model": "test-model",
        "selection_source": "explicit",
        "provider_pinned": True,
        "reasoning_mode": "normal",
        "max_context": 50,
        "depth_mode": "normal",
        "requested_source_mode": "project",
        "system_override": None,
        "retrieval_override": None,
        "preferred_name": None,
        "profession": None,
        "guardian_name": None,
        "attempt_id": "attempt-9c",
    }
    payload.update(overrides)
    return payload


def _metadata_payload(metadata: HostedRoomInvocationMetadata) -> dict[str, object]:
    return {
        "room_id": metadata.room_id,
        "source_message_id": metadata.source_message_id,
        "actor_participant_id": metadata.actor_participant_id,
        "actor_source": metadata.actor_source,
        "actor_ref": metadata.actor_ref,
        "requester_authority": metadata.requester_authority,
        "requester_participant_id": metadata.requester_participant_id,
    }


def test_valid_owner_metadata_is_immutable_and_bounded():
    metadata = _owner_metadata()

    assert metadata.requester_authority == "owner"
    assert metadata.requester_participant_id is None
    assert metadata.actor_source == "resident"
    assert metadata.actor_ref == "guardian"
    with pytest.raises((AttributeError, TypeError)):
        metadata.room_id = "changed"  # type: ignore[misc]


def test_valid_guest_metadata_requires_distinct_human_participant():
    metadata = _guest_metadata()

    assert metadata.requester_authority == "guest"
    assert metadata.requester_participant_id == REQUESTER_PARTICIPANT_ID
    assert metadata.requester_participant_id != metadata.actor_participant_id


@pytest.mark.parametrize(
    "updates",
    [
        {"requester_authority": "guest", "requester_participant_id": None},
        {
            "requester_authority": "owner",
            "requester_participant_id": REQUESTER_PARTICIPANT_ID,
        },
        {"requester_authority": "admin"},
        {"actor_source": "local_persona"},
        {"actor_source": "remote_persona"},
        {"actor_source": "unsupported"},
        {"actor_ref": "luna"},
        {"actor_ref": "display-name"},
        {"room_id": ""},
        {"actor_participant_id": " "},
        {"source_message_id": 0},
        {"source_message_id": -1},
        {"source_message_id": True},
        {"requester_participant_id": ""},
    ],
)
def test_invalid_direct_metadata_construction_raises_value_error(updates):
    values = _metadata_payload(_owner_metadata())
    values.update(updates)

    with pytest.raises(ValueError):
        HostedRoomInvocationMetadata(**values)


def test_metadata_serialization_has_exact_bounded_shape():
    task = ChatCompletionTask(
        user_id="user-1",
        thread_id=7,
        hosted_room_invocation=_owner_metadata(),
    )

    serialized = task.to_dict()
    nested = serialized["hosted_room_invocation"]

    assert set(nested) == {
        "room_id",
        "source_message_id",
        "actor_participant_id",
        "actor_source",
        "actor_ref",
        "requester_authority",
        "requester_participant_id",
    }
    assert nested == _metadata_payload(_owner_metadata())
    assert "display_name" not in nested
    assert "password" not in nested
    assert "session_token" not in nested
    assert "system_prompt" not in nested
    assert "provider" not in nested
    assert "model_id" not in nested


@pytest.mark.parametrize("metadata", [_owner_metadata(), _guest_metadata()])
def test_owner_and_guest_metadata_round_trip_all_declared_fields(metadata):
    task = ChatCompletionTask(
        task_id="task-roundtrip",
        request_id="req-roundtrip",
        user_id="user-1",
        thread_id=7,
        hosted_room_invocation=metadata,
    )

    serialized = task.to_dict()
    restored = ChatCompletionTask.from_dict(serialized)

    assert restored.hosted_room_invocation == metadata
    assert restored.to_dict() == serialized
    assert {item.name for item in fields(restored.hosted_room_invocation)} == {
        "room_id",
        "source_message_id",
        "actor_participant_id",
        "actor_source",
        "actor_ref",
        "requester_authority",
        "requester_participant_id",
    }


def test_ordinary_task_serialization_uses_null_optional_metadata_posture():
    task = ChatCompletionTask(
        task_id="task-ordinary",
        request_id="req-ordinary",
        user_id="user-1",
        thread_id=7,
    )

    serialized = task.to_dict()
    assert serialized["hosted_room_invocation"] is None

    legacy = ChatCompletionTask.from_dict(
        {
            key: value
            for key, value in serialized.items()
            if key != "hosted_room_invocation"
        }
    )
    assert legacy.hosted_room_invocation is None
    assert {
        key: value
        for key, value in legacy.to_dict().items()
        if key != "hosted_room_invocation"
    } == {
        key: value
        for key, value in serialized.items()
        if key != "hosted_room_invocation"
    }


@pytest.mark.parametrize(
    "raw_metadata",
    [
        None,
        "not-an-object",
        [],
        {},
        {"room_id": ROOM_ID},
        {
            **_metadata_payload(_owner_metadata()),
            "unknown_nested_key": "discard-me",
        },
        {**_metadata_payload(_owner_metadata()), "source_message_id": 0},
        {**_metadata_payload(_owner_metadata()), "actor_source": "local_persona"},
        {**_metadata_payload(_owner_metadata()), "actor_ref": "luna"},
        {**_metadata_payload(_owner_metadata()), "requester_authority": "admin"},
        {
            **_metadata_payload(_guest_metadata()),
            "requester_participant_id": None,
        },
        {
            **_metadata_payload(_owner_metadata()),
            "requester_participant_id": REQUESTER_PARTICIPANT_ID,
        },
    ],
)
def test_malformed_metadata_fails_closed_to_none(raw_metadata):
    task = ChatCompletionTask.from_dict(
        _task_payload(hosted_room_invocation=raw_metadata)
    )

    assert task.hosted_room_invocation is None


def test_direct_metadata_from_dict_rejects_unknown_and_non_mapping_payloads():
    with pytest.raises(ValueError):
        HostedRoomInvocationMetadata.from_dict(
            {**_metadata_payload(_owner_metadata()), "extra": "nope"}
        )
    with pytest.raises(ValueError):
        HostedRoomInvocationMetadata.from_dict(  # type: ignore[arg-type]
            "not-a-mapping"
        )


def test_legacy_payload_remains_readable_and_preserves_existing_fields():
    legacy_payload = _task_payload()
    restored = task_from_dict(legacy_payload)

    assert isinstance(restored, ChatCompletionTask)
    assert restored.task_id == "task-9c"
    assert restored.request_id == "req-9c"
    assert restored.thread_id == 7
    assert restored.latest_turn_message_id == 123
    assert restored.latest_turn_messages == [{"type": "text", "text": "hello"}]
    assert restored.provider == "local"
    assert restored.model == "test-model"
    assert restored.hosted_room_invocation is None


def test_identity_boundaries_remain_distinct():
    task = ChatCompletionTask(
        task_id="task-identity",
        user_id="user-1",
        thread_id=7,
        hosted_room_invocation=_guest_metadata(),
    )

    assert task.hosted_room_invocation.room_id != str(task.thread_id)
    assert task.hosted_room_invocation.source_message_id != task.task_id
    assert task.hosted_room_invocation.actor_participant_id != (
        task.hosted_room_invocation.requester_participant_id
    )
    assert task.hosted_room_invocation.actor_ref == "guardian"
