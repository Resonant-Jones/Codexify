from __future__ import annotations

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from guardian.db.models import TTSVoiceProfile
from guardian.tts.profiles import (
    TTSVoiceProfileError,
    create_tts_voice_profile,
    delete_tts_voice_profile,
    get_tts_backend_control_schemas,
    get_tts_voice_profile,
    profile_to_render_kwargs,
    resolve_tts_profile,
    serialize_tts_voice_profile,
    set_default_tts_voice_profile,
    update_tts_voice_profile,
)


@pytest.fixture()
def session():
    engine = create_engine("sqlite:///:memory:", future=True)
    TTSVoiceProfile.__table__.create(engine)
    Session = sessionmaker(bind=engine, future=True)
    with Session() as db_session:
        yield db_session


def test_tts_profile_create_read_update_delete(session):
    profile = create_tts_voice_profile(
        session,
        {
            "name": "Narrator",
            "backend_id": "qwen3_tts",
            "speaker": "Ryan",
            "style_instructions": "Warm and grounded.",
        },
    )

    assert profile.id.startswith("tts_")
    assert profile.is_default is True

    updated = update_tts_voice_profile(
        session,
        profile.id,
        {"name": "Narrator Prime", "speed": 1.15},
    )
    payload = serialize_tts_voice_profile(updated)
    assert payload["name"] == "Narrator Prime"
    assert payload["speed"] == 1.15

    delete_tts_voice_profile(session, profile.id)
    with pytest.raises(TTSVoiceProfileError) as exc_info:
        get_tts_voice_profile(session, profile.id)
    assert exc_info.value.code == "tts_voice_profile_not_found"


def test_tts_profile_default_uniqueness(session):
    first = create_tts_voice_profile(
        session,
        {"name": "First", "backend_id": "qwen3_tts", "is_default": True},
    )
    second = create_tts_voice_profile(
        session,
        {"name": "Second", "backend_id": "qwen3_tts", "is_default": True},
    )

    session.refresh(first)
    assert first.is_default is False
    assert second.is_default is True

    set_default_tts_voice_profile(session, first.id)
    session.refresh(first)
    session.refresh(second)
    assert first.is_default is True
    assert second.is_default is False


def test_tts_profile_backend_params_preserved(session):
    profile = create_tts_voice_profile(
        session,
        {
            "name": "Qwen Advanced",
            "backend_id": "qwen3_tts",
            "backend_params": {
                "non_streaming_mode": True,
                "subtalker_top_k": 24,
            },
        },
    )

    payload = serialize_tts_voice_profile(profile)
    assert payload["backend_params"] == {
        "non_streaming_mode": True,
        "subtalker_top_k": 24,
    }

    render_kwargs = profile_to_render_kwargs(profile)
    assert render_kwargs["backend_params"]["subtalker_top_k"] == 24


def test_tts_profile_resolver_returns_default_and_named_profile(session):
    default_profile = create_tts_voice_profile(
        session,
        {"name": "Default", "backend_id": "qwen3_tts", "is_default": True},
    )
    named_profile = create_tts_voice_profile(
        session,
        {"name": "Named", "backend_id": "qwen3_tts"},
    )

    assert resolve_tts_profile(session).id == default_profile.id
    assert resolve_tts_profile(session, named_profile.id).id == named_profile.id


def test_tts_profile_resolver_fails_when_default_missing(session):
    create_tts_voice_profile(
        session,
        {"name": "Only", "backend_id": "qwen3_tts", "is_default": False},
    )
    update_tts_voice_profile(
        session,
        resolve_tts_profile(session).id,
        {"is_default": False},
    )

    with pytest.raises(TTSVoiceProfileError) as exc_info:
        resolve_tts_profile(session)
    assert exc_info.value.code == "tts_default_profile_missing"


def test_tts_profile_invalid_backend_fails_clearly(session):
    with pytest.raises(TTSVoiceProfileError) as exc_info:
        create_tts_voice_profile(
            session,
            {"name": "Cloud", "backend_id": "elevenlabs"},
        )
    assert exc_info.value.code == "unsupported_tts_backend:elevenlabs"


def test_qwen3_supported_controls_advertise_speed_as_delivery_control():
    qwen = get_tts_backend_control_schemas("qwen3_tts")[0]
    controls = {control["id"]: control for control in qwen["controls"]}

    assert controls["speaker"]["backend_native"] is True
    assert controls["voice_prompt"]["backend_native"] is True
    assert controls["temperature"]["backend_native"] is True
    assert controls["speed"]["backend_native"] is False
    assert controls["speed"]["delivery_control"] is True
