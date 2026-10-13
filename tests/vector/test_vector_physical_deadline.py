"""Actual child ownership, coherent FAISS views and inherited deadline behavior."""

from datetime import datetime, timedelta, timezone
import os
import threading
import time

import pytest

from backend.rag.embedder import LocalSemanticEmbedder
from guardian.core.chat_postgres_deadline import accepted_postgres_query_scope
from guardian.tasks.chat_deadline import (
    AcceptedChatTaskDeadlineExceeded,
    build_accepted_chat_task_deadline,
)
from guardian.vector import accepted_deadline as boundary


def envelope(seconds):
    return build_accepted_chat_task_deadline(
        datetime.now(timezone.utc) - timedelta(seconds=720 - seconds)
    )


def track_children(monkeypatch):
    children = []
    original = boundary.subprocess.Popen

    def start(*args, **kwargs):
        child = original(*args, **kwargs)
        children.append(child)
        return child

    monkeypatch.setattr(boundary.subprocess, "Popen", start)
    return children


def assert_reaped(children):
    assert children
    for child in children:
        assert child.poll() is not None
        with pytest.raises(ProcessLookupError):
            os.kill(child.pid, 0)


def test_constructor_expiry_stops_native_process_and_cannot_index(monkeypatch):
    children = track_children(monkeypatch)
    deadline = envelope(0.05)
    frozen = deadline.to_dict()
    start = time.monotonic()
    with accepted_postgres_query_scope(deadline):
        with pytest.raises(AcceptedChatTaskDeadlineExceeded):
            LocalSemanticEmbedder(store="faiss", backend="mock")
    assert time.monotonic() - start < 0.5
    assert deadline.to_dict() == frozen
    assert_reaped(children)


def test_expired_constructor_starts_no_child(monkeypatch):
    children = track_children(monkeypatch)
    with accepted_postgres_query_scope(envelope(-0.1)):
        with pytest.raises(AcceptedChatTaskDeadlineExceeded):
            LocalSemanticEmbedder(store="faiss", backend="mock")
    assert children == []


def test_accepted_constructor_retains_parent_add_authority(monkeypatch):
    children = track_children(monkeypatch)
    with accepted_postgres_query_scope(envelope(30)):
        parent = LocalSemanticEmbedder(store="faiss", backend="mock")
        assert parent._model is None
        assert parent.search("empty", user_id="owner") == []
        with pytest.raises(RuntimeError, match="read-only search"):
            parent.embed_and_index(["forbidden"], metadatas=[{"user_id": "owner"}])
    assert_reaped(children)
    assert (
        parent.embed_and_index(["retained"], metadatas=[{"user_id": "owner"}])["count"]
        == 1
    )
    assert parent._index.ntotal == len(parent._texts) == len(parent._metadatas) == 1
    with accepted_postgres_query_scope(envelope(30)):
        assert parent.search("retained", user_id="owner")[0]["text"] == "retained"
    assert_reaped(children)


def test_snapshot_is_coherent_and_next_search_observes_acknowledged_add(monkeypatch):
    children = track_children(monkeypatch)
    parent = LocalSemanticEmbedder(store="faiss", backend="mock")
    meta = {"user_id": "owner", "namespace": "thread:one"}
    parent.embed_and_index(["first"], metadatas=[meta])
    expected = parent.search("first", k=8, namespace="thread:one", user_id="owner")
    trigger = threading.Event()
    done = threading.Event()
    errors = []

    def add():
        try:
            assert trigger.wait(10)
            parent.embed_and_index(["second"], metadatas=[meta])
        except BaseException as exc:
            errors.append(exc)
        finally:
            done.set()

    thread = threading.Thread(target=add)
    thread.start()
    fork = boundary.os.fork

    def capture():
        pid = fork()
        if pid:
            trigger.set()
        return pid

    monkeypatch.setattr(boundary.os, "fork", capture)
    # Ambient changes must not rebind the actual mock model.
    monkeypatch.setenv("CODEXIFY_EMBEDDINGS_BACKEND", "local")
    monkeypatch.setenv("LOCAL_EMBED_MODEL", "/unavailable-proof-model")
    try:
        deadline = envelope(30)
        frozen = deadline.to_dict()
        with accepted_postgres_query_scope(deadline):
            assert (
                parent.search("first", k=8, namespace="thread:one", user_id="owner")
                == expected
            )
        assert deadline.to_dict() == frozen
        assert done.wait(1) and not errors
        with accepted_postgres_query_scope(envelope(30)):
            assert (
                len(
                    parent.search(
                        "second", k=8, namespace="thread:one", user_id="owner"
                    )
                )
                == 2
            )
        with accepted_postgres_query_scope(envelope(30)):
            assert (
                parent.search("second", namespace="thread:one", user_id="other-owner")
                == []
            )
        with accepted_postgres_query_scope(envelope(30)):
            assert (
                parent.search("second", namespace="thread:other", user_id="owner") == []
            )
    finally:
        trigger.set()
        thread.join(10)
        assert not thread.is_alive()
    assert parent._index.ntotal == len(parent._texts) == len(parent._metadatas) == 2
    assert_reaped(children)


def test_snapshot_lock_wait_fails_closed_without_search_child(monkeypatch):
    children = track_children(monkeypatch)
    parent = LocalSemanticEmbedder(store="faiss", backend="mock")
    parent.embed_and_index(["retained"], metadatas=[{"user_id": "owner"}])
    held = threading.Event()
    release = threading.Event()

    def hold():
        with parent._faiss_state_lock:
            held.set()
            assert release.wait(5)

    thread = threading.Thread(target=hold)
    thread.start()
    assert held.wait(1)
    try:
        with accepted_postgres_query_scope(envelope(0.05)):
            with pytest.raises(AcceptedChatTaskDeadlineExceeded):
                parent.search("retained", user_id="owner")
        assert not children
    finally:
        release.set()
        thread.join(1)
        assert not thread.is_alive()
    assert parent._index.ntotal == 1


def test_search_expiry_reaps_serializer_and_native_child(monkeypatch):
    children = track_children(monkeypatch)
    pids = []
    fork = boundary.os.fork

    def capture():
        pid = fork()
        if pid:
            pids.append(pid)
        return pid

    monkeypatch.setattr(boundary.os, "fork", capture)
    parent = LocalSemanticEmbedder(store="faiss", backend="mock")
    parent.embed_and_index(["retained"], metadatas=[{"user_id": "owner"}])
    with accepted_postgres_query_scope(envelope(0.1)):
        with pytest.raises(AcceptedChatTaskDeadlineExceeded):
            parent.search("retained", user_id="owner")
    assert pids
    for pid in pids:
        with pytest.raises(ProcessLookupError):
            os.kill(pid, 0)
    assert_reaped(children)
    assert parent._index.ntotal == 1


def test_chroma_bound_search_preserves_results_and_deferred_parent_handle(
    tmp_path, monkeypatch
):
    children = track_children(monkeypatch)
    path = str(tmp_path / "chroma")
    original = LocalSemanticEmbedder(store="chroma", backend="mock", chroma_path=path)
    original.embed_and_index(
        ["retained"],
        metadatas=[{"user_id": "owner", "namespace": "thread:one"}],
        ids=["retained-id"],
    )
    expected = original.search("retained", namespace="thread:one", user_id="owner")
    with accepted_postgres_query_scope(envelope(30)):
        deferred = LocalSemanticEmbedder(
            store="chroma", backend="mock", chroma_path=path
        )
        assert deferred._model is None
        assert (
            deferred.search("retained", namespace="thread:one", user_id="owner")
            == expected
        )
        assert (
            deferred.search("retained", namespace="thread:one", user_id="other-owner")
            == []
        )
    assert deferred.get_ids({"user_id": "owner"}) == ["retained-id"]
    assert_reaped(children)
    assert original._chroma_collection.count() == 1


def test_failed_fork_closes_both_owned_snapshot_descriptors(monkeypatch):
    parent = LocalSemanticEmbedder(store="faiss", backend="mock")
    parent.embed_and_index(["retained"], metadatas=[{"user_id": "owner"}])
    descriptors = []
    pipe = boundary.os.pipe

    def capture_pipe():
        ends = pipe()
        descriptors.extend(ends)
        return ends

    def fail_fork():
        raise OSError("owned fork failure")

    monkeypatch.setattr(boundary.os, "pipe", capture_pipe)
    monkeypatch.setattr(boundary.os, "fork", fail_fork)
    with accepted_postgres_query_scope(envelope(30)):
        with pytest.raises(OSError, match="owned fork failure"):
            parent.search("retained", user_id="owner")
    assert len(descriptors) == 2
    for descriptor in descriptors:
        with pytest.raises(OSError):
            os.fstat(descriptor)
    assert parent._index.ntotal == 1


def test_changed_native_tensor_weights_cannot_silently_rebind(monkeypatch):
    import torch
    from guardian.vector.accepted_child import load_bound_model, model_weight_digest

    monkeypatch.setenv("CODEXIFY_ALLOW_EMBEDDINGS_FALLBACK", "1")
    model = torch.nn.Linear(2, 2)
    binding = {
        "backend": "local",
        "model": "/captured-model",
        "device": "cpu",
        "max_seq_length": 32,
        "prompts": {},
        "default_prompt_name": None,
        "truncate_dim": None,
        "model_digest": model_weight_digest(model),
    }
    monkeypatch.setattr(
        LocalSemanticEmbedder,
        "_load_sentence_transformer",
        lambda *args, **kwargs: model,
    )
    assert load_bound_model(binding) is model
    assert os.environ["CODEXIFY_ALLOW_EMBEDDINGS_FALLBACK"] == "1"
    with torch.no_grad():
        model.weight.add_(1)
    with pytest.raises(RuntimeError, match="weights are unavailable"):
        load_bound_model(binding)
    assert os.environ["CODEXIFY_ALLOW_EMBEDDINGS_FALLBACK"] == "1"
