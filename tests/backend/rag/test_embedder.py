from __future__ import annotations

import logging
from types import SimpleNamespace

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


def test_preflight_stub_backend_reports_not_applicable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("CODEXIFY_EMBEDDINGS_BACKEND", raising=False)
    monkeypatch.setenv("EMBEDDING_BACKEND", "stub")
    monkeypatch.delenv("LOCAL_EMBED_MODEL", raising=False)

    result = embedder_module.inspect_embedder_preflight()

    assert result["backend"] == "stub"
    assert result["model"] is None
    assert result["present"] is None
    assert result["ready"] is True
    assert "not applicable for stub backend" in str(result["reason"])


def test_preflight_local_model_present_ready_true(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("CODEXIFY_EMBEDDINGS_BACKEND", "local")
    monkeypatch.setenv("LOCAL_EMBED_MODEL", "/models/default-local-embedder")
    monkeypatch.setattr(
        embedder_module,
        "require_local_embed_model",
        lambda: "/models/default-local-embedder",
    )

    result = embedder_module.inspect_embedder_preflight()

    assert result == {
        "backend": "local",
        "model": "/models/default-local-embedder",
        "ready": True,
        "present": True,
        "reason": "local embedder preflight passed",
    }


def test_preflight_local_model_missing_no_download_attempt(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("CODEXIFY_EMBEDDINGS_BACKEND", "local")
    monkeypatch.setenv("LOCAL_EMBED_MODEL", "/models/default-local-embedder")
    monkeypatch.setattr(
        embedder_module,
        "require_local_embed_model",
        lambda: (_ for _ in ()).throw(RuntimeError("missing local model")),
    )
    monkeypatch.setattr(
        embedder_module.LocalSemanticEmbedder,
        "_attempt_local_model_autodownload",
        lambda *args, **kwargs: (_ for _ in ()).throw(
            AssertionError("preflight must not trigger auto-download")
        ),
    )

    result = embedder_module.inspect_embedder_preflight()

    assert result["backend"] == "local"
    assert result["model"] == "/models/default-local-embedder"
    assert result["ready"] is False
    assert result["present"] is False
    assert "configured local embedder not found in cache or invalid" in str(
        result["reason"]
    )


def test_chroma_client_disables_telemetry(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_faiss_available(monkeypatch)

    captured: dict[str, object] = {}

    class _FakeCollection:
        pass

    class _FakeClient:
        def __init__(self, path: str, settings=None) -> None:
            captured["path"] = path
            captured["settings"] = settings

        def get_or_create_collection(self, name: str):
            captured["collection"] = name
            return _FakeCollection()

    monkeypatch.setattr(
        embedder_module,
        "chromadb",
        SimpleNamespace(PersistentClient=_FakeClient),
    )
    monkeypatch.setattr(
        embedder_module,
        "ChromaSettings",
        lambda anonymized_telemetry=False: {
            "anonymized_telemetry": anonymized_telemetry
        },
    )
    monkeypatch.setattr(
        embedder_module.LocalSemanticEmbedder,
        "_init_embedding_model",
        lambda _self: object(),
    )

    embedder_module.LocalSemanticEmbedder(
        model="/models/default-local-embedder",
        store="chroma",
        chroma_path="/tmp/chroma-no-telemetry",
        collection="telemetry_suppressed",
        backend="mock",
    )

    assert captured == {
        "path": "/tmp/chroma-no-telemetry",
        "settings": {"anonymized_telemetry": False},
        "collection": "telemetry_suppressed",
    }
