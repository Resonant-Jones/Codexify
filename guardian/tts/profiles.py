"""Persistent TTS voice profile contract and storage helpers."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import uuid4

from sqlalchemy.orm import Session

from guardian.db.models import TTSVoiceProfile
from guardian.tts.contracts import (
    TTS_BACKEND_LOCAL_MOCK,
    TTS_BACKEND_LOCAL_OPENAI_COMPATIBLE,
    TTS_BACKEND_QWEN3,
    TTS_LOCAL_BACKEND_IDS,
    TTS_OUTPUT_FORMATS,
    TTS_VOICE_MODE_PRESET,
    TTS_VOICE_MODES,
)

PROFILE_FIELD_NAMES = (
    "id",
    "name",
    "backend_id",
    "is_default",
    "description",
    "voice_mode",
    "speaker",
    "voice_prompt",
    "style_instructions",
    "language",
    "speed",
    "temperature",
    "top_k",
    "top_p",
    "repetition_penalty",
    "max_new_tokens",
    "do_sample",
    "backend_params",
    "reference_audio_asset_id",
    "reference_text",
    "x_vector_only_mode",
    "sample_rate",
    "output_format",
    "loudness_normalization",
    "pause_profile",
)
PROFILE_MUTABLE_FIELDS = tuple(name for name in PROFILE_FIELD_NAMES if name != "id")


class TTSVoiceProfileError(ValueError):
    """Profile validation/storage error with an API-safe code."""

    def __init__(self, code: str, message: str | None = None):
        super().__init__(message or code)
        self.code = code


def serialize_tts_voice_profile(profile: TTSVoiceProfile) -> dict[str, Any]:
    return {
        "id": profile.id,
        "name": profile.name,
        "backend_id": profile.backend_id,
        "is_default": bool(profile.is_default),
        "description": profile.description,
        "voice_mode": profile.voice_mode,
        "speaker": profile.speaker,
        "voice_prompt": profile.voice_prompt,
        "style_instructions": profile.style_instructions,
        "language": profile.language,
        "speed": profile.speed,
        "temperature": profile.temperature,
        "top_k": profile.top_k,
        "top_p": profile.top_p,
        "repetition_penalty": profile.repetition_penalty,
        "max_new_tokens": profile.max_new_tokens,
        "do_sample": profile.do_sample,
        "backend_params": profile.backend_params or {},
        "reference_audio_asset_id": profile.reference_audio_asset_id,
        "reference_text": profile.reference_text,
        "x_vector_only_mode": profile.x_vector_only_mode,
        "sample_rate": profile.sample_rate,
        "output_format": profile.output_format,
        "loudness_normalization": profile.loudness_normalization,
        "pause_profile": profile.pause_profile,
        "created_at": _isoformat_or_none(profile.created_at),
        "updated_at": _isoformat_or_none(profile.updated_at),
    }


def list_tts_voice_profiles(session: Session) -> list[TTSVoiceProfile]:
    return (
        session.query(TTSVoiceProfile)
        .order_by(
            TTSVoiceProfile.is_default.desc(),
            TTSVoiceProfile.updated_at.desc(),
            TTSVoiceProfile.name.asc(),
        )
        .all()
    )


def get_tts_voice_profile(session: Session, profile_id: str) -> TTSVoiceProfile:
    profile = session.get(TTSVoiceProfile, _normalize_profile_id(profile_id))
    if profile is None:
        raise TTSVoiceProfileError("tts_voice_profile_not_found")
    return profile


def create_tts_voice_profile(
    session: Session,
    values: dict[str, Any],
) -> TTSVoiceProfile:
    payload = _normalize_profile_payload(values, partial=False)
    if not payload.get("id"):
        payload["id"] = f"tts_{uuid4().hex[:16]}"

    existing_count = session.query(TTSVoiceProfile.id).count()
    requested_default = bool(payload.pop("is_default", False))
    should_default = requested_default or existing_count == 0
    profile = TTSVoiceProfile(**payload, is_default=should_default)

    if should_default:
        _clear_default_profiles(session)

    session.add(profile)
    session.commit()
    session.refresh(profile)
    return profile


def update_tts_voice_profile(
    session: Session,
    profile_id: str,
    values: dict[str, Any],
) -> TTSVoiceProfile:
    profile = get_tts_voice_profile(session, profile_id)
    payload = _normalize_profile_payload(values, partial=True)

    if payload.pop("is_default", None) is True:
        _clear_default_profiles(session)
        profile.is_default = True
    elif "is_default" in values and values.get("is_default") is False:
        profile.is_default = False

    for field_name, field_value in payload.items():
        if field_name == "id":
            continue
        setattr(profile, field_name, field_value)

    session.commit()
    session.refresh(profile)
    return profile


def delete_tts_voice_profile(session: Session, profile_id: str) -> None:
    profile = get_tts_voice_profile(session, profile_id)
    session.delete(profile)
    session.commit()


def set_default_tts_voice_profile(
    session: Session,
    profile_id: str,
) -> TTSVoiceProfile:
    profile = get_tts_voice_profile(session, profile_id)
    _clear_default_profiles(session)
    profile.is_default = True
    session.commit()
    session.refresh(profile)
    return profile


def resolve_tts_profile(
    session: Session,
    profile_id: str | None = None,
) -> TTSVoiceProfile:
    """Resolve a selected profile or the default without running synthesis."""

    if profile_id:
        return get_tts_voice_profile(session, profile_id)

    profile = (
        session.query(TTSVoiceProfile)
        .filter(TTSVoiceProfile.is_default.is_(True))
        .order_by(TTSVoiceProfile.updated_at.desc())
        .first()
    )
    if profile is None:
        raise TTSVoiceProfileError("tts_default_profile_missing")
    return profile


def profile_to_render_kwargs(profile: TTSVoiceProfile) -> dict[str, Any]:
    backend_params = dict(profile.backend_params or {})
    if profile.x_vector_only_mode is not None:
        backend_params["x_vector_only_mode"] = profile.x_vector_only_mode
    if profile.reference_audio_asset_id:
        backend_params["reference_audio_asset_id"] = profile.reference_audio_asset_id
    if profile.reference_text:
        backend_params["reference_text"] = profile.reference_text

    return {
        "profile_id": profile.id,
        "backend_id": profile.backend_id,
        "voice_id": profile.speaker or "default",
        "voice_prompt": profile.voice_prompt,
        "style_instructions": profile.style_instructions,
        "language": profile.language,
        "speed": profile.speed,
        "temperature": profile.temperature,
        "top_k": profile.top_k,
        "top_p": profile.top_p,
        "repetition_penalty": profile.repetition_penalty,
        "max_new_tokens": profile.max_new_tokens,
        "do_sample": profile.do_sample,
        "backend_params": backend_params,
    }


def get_tts_backend_control_schemas(
    active_backend_id: str = TTS_BACKEND_QWEN3,
) -> list[dict[str, Any]]:
    active = _normalize_backend_id(active_backend_id)
    return [
        _backend_schema(
            backend_id=TTS_BACKEND_QWEN3,
            display_name="Qwen3-TTS",
            active=active == TTS_BACKEND_QWEN3,
            controls=_qwen3_controls(),
        ),
        _backend_schema(
            backend_id=TTS_BACKEND_LOCAL_OPENAI_COMPATIBLE,
            display_name="Local OpenAI-Compatible TTS",
            active=active == TTS_BACKEND_LOCAL_OPENAI_COMPATIBLE,
            controls=[],
        ),
        _backend_schema(
            backend_id=TTS_BACKEND_LOCAL_MOCK,
            display_name="Local Mock TTS",
            active=active == TTS_BACKEND_LOCAL_MOCK,
            controls=[],
        ),
    ]


def _backend_schema(
    *,
    backend_id: str,
    display_name: str,
    active: bool,
    controls: list[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "backend_id": backend_id,
        "display_name": display_name,
        "local_only": True,
        "active": active,
        "controls": controls,
    }


def _qwen3_controls() -> list[dict[str, Any]]:
    return [
        _control("speaker", "Speaker", "text", "common", native=True),
        _control("voice_prompt", "Voice Prompt", "textarea", "common", native=True),
        _control(
            "style_instructions",
            "Style Instructions",
            "textarea",
            "common",
            native=True,
            backend_parameter="instruct",
        ),
        _control("language", "Language", "text", "common", native=True),
        _control(
            "speed",
            "Speed",
            "number",
            "common",
            native=False,
            delivery_control=True,
            min=0.5,
            max=2.0,
            step=0.05,
        ),
        _control(
            "temperature",
            "Temperature",
            "number",
            "advanced",
            native=True,
            min=0.0,
            max=2.0,
            step=0.05,
        ),
        _control("top_k", "Top K", "number", "advanced", native=True, min=0, step=1),
        _control(
            "top_p",
            "Top P",
            "number",
            "advanced",
            native=True,
            min=0.0,
            max=1.0,
            step=0.01,
        ),
        _control(
            "repetition_penalty",
            "Repetition Penalty",
            "number",
            "advanced",
            native=True,
            min=0.1,
            step=0.05,
        ),
        _control(
            "max_new_tokens",
            "Max New Tokens",
            "number",
            "advanced",
            native=True,
            min=1,
            step=1,
        ),
        _control("do_sample", "Do Sample", "boolean", "advanced", native=True),
        _control(
            "subtalker_dosample",
            "Subtalker Do Sample",
            "boolean",
            "conditional",
            native=True,
            backend_param=True,
        ),
        _control(
            "subtalker_top_k",
            "Subtalker Top K",
            "number",
            "conditional",
            native=True,
            backend_param=True,
        ),
        _control(
            "subtalker_top_p",
            "Subtalker Top P",
            "number",
            "conditional",
            native=True,
            backend_param=True,
        ),
        _control(
            "subtalker_temperature",
            "Subtalker Temperature",
            "number",
            "conditional",
            native=True,
            backend_param=True,
        ),
        _control(
            "x_vector_only_mode",
            "X-Vector Only Mode",
            "boolean",
            "conditional",
            native=True,
        ),
        _control(
            "reference_audio",
            "Reference Audio",
            "asset",
            "conditional",
            native=True,
            preview_supported=False,
        ),
        _control(
            "reference_text",
            "Reference Text",
            "textarea",
            "conditional",
            native=True,
        ),
        _control(
            "non_streaming_mode",
            "Non-Streaming Mode",
            "boolean",
            "conditional",
            native=True,
            backend_param=True,
        ),
    ]


def _control(
    control_id: str,
    label: str,
    control_type: str,
    group: str,
    *,
    native: bool,
    delivery_control: bool = False,
    backend_param: bool = False,
    backend_parameter: str | None = None,
    preview_supported: bool = True,
    **constraints: Any,
) -> dict[str, Any]:
    return {
        "id": control_id,
        "label": label,
        "type": control_type,
        "group": group,
        "backend_native": native,
        "delivery_control": delivery_control,
        "backend_param": backend_param,
        "backend_parameter": backend_parameter,
        "preview_supported": preview_supported,
        **constraints,
    }


def _clear_default_profiles(session: Session) -> None:
    session.query(TTSVoiceProfile).filter(TTSVoiceProfile.is_default.is_(True)).update(
        {"is_default": False}, synchronize_session=False
    )


def _normalize_profile_payload(
    values: dict[str, Any],
    *,
    partial: bool,
) -> dict[str, Any]:
    payload: dict[str, Any] = {}
    allowed = PROFILE_MUTABLE_FIELDS if partial else PROFILE_FIELD_NAMES
    for key in allowed:
        if key in values:
            payload[key] = values[key]

    if not partial and not _clean_required_text(payload.get("name")):
        raise TTSVoiceProfileError("tts_voice_profile_name_required")
    if "name" in payload:
        payload["name"] = _clean_required_text(payload["name"])
        if not payload["name"]:
            raise TTSVoiceProfileError("tts_voice_profile_name_required")

    if not partial:
        payload.setdefault("backend_id", TTS_BACKEND_QWEN3)
        payload.setdefault("voice_mode", TTS_VOICE_MODE_PRESET)
        payload.setdefault("speaker", "default")
        payload.setdefault("speed", 1.0)
        payload.setdefault("output_format", "wav")
        payload.setdefault("backend_params", {})

    if "id" in payload and payload["id"]:
        payload["id"] = _normalize_profile_id(str(payload["id"]))
    if "backend_id" in payload:
        payload["backend_id"] = _normalize_backend_id(payload["backend_id"])
    if "voice_mode" in payload:
        payload["voice_mode"] = _normalize_voice_mode(payload["voice_mode"])
    if "output_format" in payload and payload["output_format"] is not None:
        payload["output_format"] = _normalize_output_format(payload["output_format"])

    for text_field in (
        "description",
        "speaker",
        "voice_prompt",
        "style_instructions",
        "language",
        "reference_audio_asset_id",
        "reference_text",
    ):
        if text_field in payload:
            payload[text_field] = _clean_optional_text(payload[text_field])

    if "speed" in payload:
        payload["speed"] = _normalize_float(
            payload["speed"],
            "tts_voice_profile_speed_invalid",
            minimum=0.01,
            maximum=4.0,
        )
    if "temperature" in payload:
        payload["temperature"] = _normalize_float(
            payload["temperature"],
            "tts_voice_profile_temperature_invalid",
            minimum=0.0,
            maximum=2.0,
        )
    if "top_p" in payload:
        payload["top_p"] = _normalize_float(
            payload["top_p"],
            "tts_voice_profile_top_p_invalid",
            minimum=0.0,
            maximum=1.0,
        )
    if "repetition_penalty" in payload:
        payload["repetition_penalty"] = _normalize_float(
            payload["repetition_penalty"],
            "tts_voice_profile_repetition_penalty_invalid",
            minimum=0.01,
        )
    if "top_k" in payload:
        payload["top_k"] = _normalize_int(
            payload["top_k"], "tts_voice_profile_top_k_invalid", minimum=0
        )
    if "max_new_tokens" in payload:
        payload["max_new_tokens"] = _normalize_int(
            payload["max_new_tokens"],
            "tts_voice_profile_max_new_tokens_invalid",
            minimum=1,
        )
    if "sample_rate" in payload:
        payload["sample_rate"] = _normalize_int(
            payload["sample_rate"], "tts_voice_profile_sample_rate_invalid", minimum=1
        )
    if "backend_params" in payload:
        payload["backend_params"] = _normalize_dict(payload["backend_params"])
    if "pause_profile" in payload and payload["pause_profile"] is not None:
        payload["pause_profile"] = _normalize_dict(payload["pause_profile"])

    return payload


def _normalize_profile_id(value: str) -> str:
    cleaned = (value or "").strip()
    if not cleaned:
        raise TTSVoiceProfileError("tts_voice_profile_id_required")
    return cleaned


def _normalize_backend_id(value: Any) -> str:
    backend_id = str(value or "").strip().lower()
    if backend_id not in TTS_LOCAL_BACKEND_IDS:
        raise TTSVoiceProfileError(f"unsupported_tts_backend:{backend_id or '<empty>'}")
    return backend_id


def _normalize_voice_mode(value: Any) -> str:
    voice_mode = str(value or "").strip().lower()
    if voice_mode not in TTS_VOICE_MODES:
        raise TTSVoiceProfileError(
            f"unsupported_tts_voice_mode:{voice_mode or '<empty>'}"
        )
    return voice_mode


def _normalize_output_format(value: Any) -> str:
    output_format = str(value or "").strip().lower()
    if output_format not in TTS_OUTPUT_FORMATS:
        raise TTSVoiceProfileError(
            f"unsupported_tts_output_format:{output_format or '<empty>'}"
        )
    return output_format


def _clean_required_text(value: Any) -> str:
    return str(value or "").strip()


def _clean_optional_text(value: Any) -> str | None:
    cleaned = str(value or "").strip()
    return cleaned or None


def _normalize_float(
    value: Any,
    error_code: str,
    *,
    minimum: float | None = None,
    maximum: float | None = None,
) -> float | None:
    if value is None or value == "":
        return None
    try:
        parsed = float(value)
    except (TypeError, ValueError) as exc:
        raise TTSVoiceProfileError(error_code) from exc
    if minimum is not None and parsed < minimum:
        raise TTSVoiceProfileError(error_code)
    if maximum is not None and parsed > maximum:
        raise TTSVoiceProfileError(error_code)
    return parsed


def _normalize_int(
    value: Any,
    error_code: str,
    *,
    minimum: int | None = None,
) -> int | None:
    if value is None or value == "":
        return None
    try:
        parsed = int(value)
    except (TypeError, ValueError) as exc:
        raise TTSVoiceProfileError(error_code) from exc
    if minimum is not None and parsed < minimum:
        raise TTSVoiceProfileError(error_code)
    return parsed


def _normalize_dict(value: Any) -> dict[str, Any]:
    if value is None:
        return {}
    if not isinstance(value, dict):
        raise TTSVoiceProfileError("tts_voice_profile_json_object_required")
    return dict(value)


def _isoformat_or_none(value: datetime | None) -> str | None:
    if value is None:
        return None
    return value.isoformat()
