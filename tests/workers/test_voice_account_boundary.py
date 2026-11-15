"""Synthetic queue execution must retain account/thread authority."""

import base64
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from guardian.core import dependencies
from guardian.tasks.types import VoiceTurnTask, task_from_dict
from guardian.workers import voice_worker


@pytest.fixture
def execution(monkeypatch):
    thread = {"id": 1, "user_id": "account-a"}
    db = SimpleNamespace(
        get_chat_thread=Mock(side_effect=lambda _: thread or None),
        create_message=Mock(return_value=11),
        write_audit_log=Mock(),
    )
    monkeypatch.setattr(dependencies, "chatlog_db", db)
    monkeypatch.setattr(dependencies, "is_private_preview", lambda: False)
    monkeypatch.setattr(dependencies, "_auth_mode", lambda: "local")
    monkeypatch.setattr(dependencies, "_multi_user_mode_enabled", lambda: False)
    monkeypatch.setattr(dependencies, "get_single_user_id", lambda: "local")
    monkeypatch.setattr(
        voice_worker,
        "get_voice_runtime_config",
        lambda: SimpleNamespace(
            stt_timeout_seconds=1,
            completion_timeout_seconds=1,
            tts_timeout_seconds=1,
            tts_provider="local_openai_compatible",
        ),
    )
    monkeypatch.setattr(voice_worker, "is_cancelled", lambda _: False)
    monkeypatch.setattr(voice_worker, "release_turn_lock", Mock())
    monkeypatch.setattr(voice_worker.event_bus, "emit_event", Mock())
    publish = Mock()
    stt = Mock(return_value="synthetic transcript")
    completion = Mock(
        return_value={"message_id": 12, "assistant_text": "synthetic answer"}
    )
    tts = Mock(return_value=(b"synthetic-audio", "wav"))
    save = Mock(return_value={"id": 111})
    for name, value in [
        ("_safe_publish", publish),
        ("transcribe", stt),
        ("run_chat_completion_task", completion),
        ("synthesize", tts),
        ("save_message_audio_asset", save),
    ]:
        monkeypatch.setattr(voice_worker, name, value)
    return SimpleNamespace(
        thread=thread,
        db=db,
        publish=publish,
        stt=stt,
        completion=completion,
        tts=tts,
        save=save,
    )


def task(**updates):
    fields = dict(
        user_id="account-a",
        account_id="account-a",
        thread_id=1,
        audio_b64=base64.b64encode(b"synthetic").decode("ascii"),
        audio_mime="audio/wav",
        turn_lock_owner="synthetic-lock",
    )
    fields.update(updates)
    return task_from_dict(VoiceTurnTask(**fields).to_dict())


def assert_denied(execution):
    for call in (
        execution.stt,
        execution.db.create_message,
        execution.completion,
        execution.tts,
        execution.save,
    ):
        call.assert_not_called()
    events = [call.args[1] for call in execution.publish.call_args_list]
    assert "task.failed" in events
    assert "task.completed" not in events


@pytest.mark.parametrize("owner", ["account-b", None, "", "missing"])
def test_worker_denies_changed_null_and_missing_thread(execution, owner):
    if owner == "missing":
        execution.thread.clear()
    else:
        execution.thread["user_id"] = owner
    voice_worker._run_voice_task(task())
    assert_denied(execution)


@pytest.mark.parametrize(
    "account_id,user_id",
    [("", "account-a"), (17, "account-a"), ("account-a", "account-b")],
)
def test_worker_denies_invalid_or_conflicting_binding(execution, account_id, user_id):
    voice_worker._run_voice_task(task(account_id=account_id, user_id=user_id))
    assert_denied(execution)


@pytest.mark.parametrize("boundary", ["remote", "preview", "multi_user"])
def test_missing_legacy_binding_never_falls_back_in_account_deployment(
    execution, monkeypatch, boundary
):
    if boundary == "remote":
        monkeypatch.setattr(dependencies, "_auth_mode", lambda: "remote")
    elif boundary == "preview":
        monkeypatch.setattr(dependencies, "is_private_preview", lambda: True)
    else:
        monkeypatch.setattr(dependencies, "_multi_user_mode_enabled", lambda: True)
    voice_worker._run_voice_task(task(account_id=None, user_id=""))
    assert_denied(execution)


def test_worker_rechecks_owner_after_stt_before_persistence(execution):
    def transcribe(*args, **kwargs):
        execution.thread["user_id"] = "account-b"
        return "synthetic transcript"

    execution.stt.side_effect = transcribe
    voice_worker._run_voice_task(task())
    execution.stt.assert_called_once()
    execution.db.create_message.assert_not_called()
    execution.completion.assert_not_called()
    execution.save.assert_not_called()


def test_owner_completion_and_tts_retain_account_identity(execution):
    voice_worker._run_voice_task(task())
    execution.stt.assert_called_once()
    execution.db.create_message.assert_called_once_with(
        1, "user", "synthetic transcript"
    )
    completion_task = execution.completion.call_args.args[0]
    assert completion_task.user_id == "account-a"
    assert execution.completion.call_args.kwargs["user_id"] == "account-a"
    assert not any(
        call.args[1] == "task.failed" for call in execution.publish.call_args_list
    )
    execution.tts.assert_called_once()
    execution.save.assert_called_once()


def test_local_legacy_task_still_completes(execution):
    voice_worker._run_voice_task(task(account_id=None, user_id=""))
    assert execution.completion.call_args.args[0].user_id == "local"
    execution.save.assert_called_once()


def test_owner_change_during_tts_prevents_save_and_completion(execution):
    def synthesize(*args, **kwargs):
        execution.thread["user_id"] = "account-b"
        return b"synthetic-audio", "wav"

    execution.tts.side_effect = synthesize
    voice_worker._run_voice_task(task())
    execution.save.assert_not_called()
    assert not any(
        call.args[1] == "task.completed" for call in execution.publish.call_args_list
    )


@pytest.mark.parametrize("callback", ["token_callback", "cancel_check"])
def test_owner_change_during_completion_revalidates_before_output_or_persist(
    execution, callback
):
    persist = Mock()

    def complete(*args, **kwargs):
        execution.thread["user_id"] = "account-b"
        if callback == "token_callback":
            kwargs[callback]("protected synthetic token")
        else:
            kwargs[callback]()
        persist()
        return {"message_id": 12, "assistant_text": "synthetic answer"}

    execution.completion.side_effect = complete
    voice_worker._run_voice_task(task())
    assert not any(
        call.args[1] == "task.completed"
        or call.args[2].get("stage") == "completion.token"
        for call in execution.publish.call_args_list
    )
    execution.save.assert_not_called()
    persist.assert_not_called()
