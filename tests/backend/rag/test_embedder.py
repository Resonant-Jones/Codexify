from __future__ import annotations

import logging

import pytest

from backend.rag import embedder as embedder_module


def _patch_faiss_available(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(embedder_module, "faiss", object())


def test_local_model_present_skips_autodownload(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_faiss_available(monkeypatch)

    calls: list[tuple[str, bool]] = []
    model_obj = object()

    def fake_sentence_transformer(
        model_name: str,
        local_files_only: bool,
    ):
        calls.append((model_name, local_files_only))
        return model_obj

    def fail_if_called(*_args, **_kwargs):
        raise AssertionError("auto-download should not be attempted")

    monkeypatch.setattr(
        embedder_module,
        "SentenceTransformer",
        fake_sentence_transformer,
    )
    monkeypatch.setattr(
        embedder_module.LocalSemanticEmbedder,
        "_attempt_local_model_autodownload",
        fail_if_called,
    )

    embedder = embedder_module.LocalSemanticEmbedder(
        model="/models/default-local-embedder",
        backend="local",
    )

    assert embedder._model is model_obj
    assert calls == [("/models/default-local-embedder", True)]


def test_local_model_missing_autodownload_then_retry_success(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    _patch_faiss_available(monkeypatch)
    caplog.set_level(logging.INFO)

    calls: list[tuple[str, bool]] = []
    recovered_model = object()

    def fake_sentence_transformer(
        model_name: str,
        local_files_only: bool,
    ):
        calls.append((model_name, local_files_only))
        if len(calls) == 1:
            raise RuntimeError("not in cache")
        if len(calls) == 2:
            assert local_files_only is False
            return object()  # download/installation path
        if len(calls) == 3:
            assert local_files_only is True
            return recovered_model
        raise AssertionError("unexpected extra retry")

    monkeypatch.setattr(
        embedder_module,
        "SentenceTransformer",
        fake_sentence_transformer,
    )

    embedder = embedder_module.LocalSemanticEmbedder(
        model="/models/default-local-embedder",
        backend="local",
    )

    assert embedder._model is recovered_model
    assert calls == [
        ("/models/default-local-embedder", True),
        ("/models/default-local-embedder", False),
        ("/models/default-local-embedder", True),
    ]
    assert "attempting one-time auto-download" in caplog.text
    assert "recovered after auto-download" in caplog.text


def test_local_model_missing_autodownload_fails_raises_clear_error(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    _patch_faiss_available(monkeypatch)
    caplog.set_level(logging.INFO)

    calls: list[tuple[str, bool]] = []

    def fake_sentence_transformer(
        model_name: str,
        local_files_only: bool,
    ):
        calls.append((model_name, local_files_only))
        if len(calls) == 1:
            raise RuntimeError("not in cache")
        if len(calls) == 2:
            raise RuntimeError("download unavailable")
        raise AssertionError("unexpected retry")

    monkeypatch.setattr(
        embedder_module,
        "SentenceTransformer",
        fake_sentence_transformer,
    )

    with pytest.raises(RuntimeError) as exc_info:
        embedder_module.LocalSemanticEmbedder(
            model="/models/default-local-embedder",
            backend="local",
        )

    message = str(exc_info.value)
    assert "/models/default-local-embedder" in message
    assert "Auto-download was attempted" in message
    assert "download unavailable" in message
    assert calls == [
        ("/models/default-local-embedder", True),
        ("/models/default-local-embedder", False),
    ]
    assert "auto-download failed" in caplog.text


def test_local_model_missing_download_succeeds_retry_still_fails(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    _patch_faiss_available(monkeypatch)
    caplog.set_level(logging.INFO)

    calls: list[tuple[str, bool]] = []

    def fake_sentence_transformer(
        model_name: str,
        local_files_only: bool,
    ):
        calls.append((model_name, local_files_only))
        if len(calls) == 1:
            raise RuntimeError("not in cache")
        if len(calls) == 2:
            assert local_files_only is False
            return object()
        if len(calls) == 3:
            assert local_files_only is True
            raise RuntimeError("still unavailable")
        raise AssertionError("unexpected extra retry")

    monkeypatch.setattr(
        embedder_module,
        "SentenceTransformer",
        fake_sentence_transformer,
    )

    with pytest.raises(RuntimeError) as exc_info:
        embedder_module.LocalSemanticEmbedder(
            model="/models/default-local-embedder",
            backend="local",
        )

    message = str(exc_info.value)
    assert "/models/default-local-embedder" in message
    assert "Auto-download was attempted" in message
    assert "still unavailable" in message
    assert calls == [
        ("/models/default-local-embedder", True),
        ("/models/default-local-embedder", False),
        ("/models/default-local-embedder", True),
    ]
    assert "still unavailable after auto-download" in caplog.text
