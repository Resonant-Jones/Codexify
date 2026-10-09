"""Owned read-only native vector children inside the accepted chat envelope."""

from __future__ import annotations

import os
import pickle
import signal
import subprocess
import sys
import time

from guardian.core.chat_postgres_deadline import accepted_child_deadline_bounds
from guardian.tasks.chat_deadline import AcceptedChatTaskDeadlineExceeded


def _remaining(end: float) -> float:
    left = end - time.monotonic()
    if left <= 0:
        raise AcceptedChatTaskDeadlineExceeded()
    return left


def model_binding(embedder) -> dict:
    """Capture the actual initialized model, never select again from ambient env."""
    deferred = getattr(embedder, "_deferred_model_binding", None)
    if deferred is not None and embedder._model is None:
        return dict(deferred)
    model = embedder._model
    kind = type(model).__name__
    if kind == "MockEmbeddingBackend":
        return {
            "backend": "mock",
            "model": "mock",
            "dim": model.dim,
            "normalize": model.normalize,
        }
    if kind != "SentenceTransformer":
        raise RuntimeError("Native vector model binding cannot be reproduced safely")
    return {
        "backend": embedder._backend_type,
        "model": embedder.model_name,
        "device": str(model.device),
        "max_seq_length": model.max_seq_length,
        "prompts": dict(model.prompts),
        "default_prompt_name": model.default_prompt_name,
        "truncate_dim": model.truncate_dim,
    }


def _reap_serializer(
    pid: int, work_end: float, terminal_end: float, *, terminate: bool = False
) -> None:
    if terminate:
        try:
            os.kill(pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
    end = terminal_end if terminate else work_end
    while True:
        try:
            found, status = os.waitpid(pid, os.WNOHANG)
        except ChildProcessError:
            if terminate:
                return
            raise
        if found:
            if not terminate and os.waitstatus_to_exitcode(status) != 0:
                raise RuntimeError("Native vector snapshot preparation failed")
            return
        time.sleep(min(0.001, _remaining(end)))


def _operation(request: dict, *, embedder=None):
    ends = accepted_child_deadline_bounds()
    if ends is None:
        raise RuntimeError("Bounded vector operation requires an accepted deadline")
    work_end, terminal_end = ends
    serializer = None
    read_fd = None
    child = None
    try:
        if embedder is not None and (
            embedder.store == "faiss"
            or (request["binding"]["backend"] != "mock" and embedder._model is not None)
        ):
            lock = embedder._faiss_state_lock
            if not lock.acquire(timeout=_remaining(work_end)):
                raise AcceptedChatTaskDeadlineExceeded()
            try:
                _remaining(work_end)
                if embedder.store == "faiss" and (
                    embedder._index is None or not embedder._texts
                ):
                    return []
                if embedder.store == "faiss" and not (
                    embedder._index.ntotal
                    == len(embedder._texts)
                    == len(embedder._metadatas)
                ):
                    raise RuntimeError("FAISS snapshot state is inconsistent")
                read_fd, write_fd = os.pipe()
                try:
                    serializer = os.fork()
                except BaseException:
                    os.close(write_fd)
                    raise
                if serializer == 0:
                    try:
                        os.close(read_fd)
                        snapshot = {}
                        if request["binding"]["backend"] != "mock":
                            from guardian.vector.accepted_child import (
                                model_weight_digest,
                            )

                            snapshot["model_digest"] = (
                                model_weight_digest(embedder._model)
                                if embedder._model is not None
                                else request["binding"]["model_digest"]
                            )
                        if embedder.store == "faiss":
                            import faiss

                            snapshot.update(
                                index=faiss.serialize_index(embedder._index),
                                texts=embedder._texts,
                                metadata=embedder._metadatas,
                            )
                        with os.fdopen(write_fd, "wb") as stream:
                            pickle.dump(snapshot, stream, protocol=5)
                        os._exit(0)
                    except BaseException:
                        os._exit(1)
                os.close(write_fd)
            finally:
                lock.release()
        _remaining(work_end)
        request["snapshot_fd"] = read_fd
        child = subprocess.Popen(
            [sys.executable, "-m", "guardian.vector.accepted_child"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            pass_fds=() if read_fd is None else (read_fd,),
        )
        if read_fd is not None:
            os.close(read_fd)
            read_fd = None
        try:
            output, _ = child.communicate(
                pickle.dumps(request, protocol=5), timeout=_remaining(work_end)
            )
        except subprocess.TimeoutExpired:
            raise AcceptedChatTaskDeadlineExceeded() from None
        _remaining(work_end)
        if child.returncode != 0:
            raise RuntimeError("Bounded native vector child failed")
        if serializer is not None:
            pid, serializer = serializer, None
            try:
                _reap_serializer(pid, work_end, terminal_end)
            except BaseException:
                _reap_serializer(pid, work_end, terminal_end, terminate=True)
                raise
        result = pickle.loads(output)
        _remaining(work_end)
        return result
    finally:
        if read_fd is not None:
            os.close(read_fd)
        if child is not None and child.poll() is None:
            child.kill()
            child.communicate(timeout=max(0.001, terminal_end - time.monotonic()))
        if serializer is not None:
            _reap_serializer(serializer, work_end, terminal_end, terminate=True)


def initialize_accepted_vector(
    *, model, backend, store, chroma_path, collection, allow_fallback
) -> dict:
    return _operation(
        {
            "operation": "initialize",
            "model": model,
            "backend": backend,
            "store": store,
            "chroma_path": chroma_path,
            "collection": collection,
            "allow_fallback": allow_fallback,
            "local_model": os.getenv("LOCAL_EMBED_MODEL"),
        }
    )


def search_accepted_vector(embedder, query, k, namespace, user_id):
    accepted_child_deadline_bounds()
    binding = model_binding(embedder)
    return _operation(
        {
            "operation": "search",
            "binding": binding,
            "store": embedder.store,
            "chroma_path": embedder.chroma_path,
            "collection": embedder.collection,
            "query": query,
            "k": k,
            "namespace": namespace,
            "user_id": user_id,
        },
        embedder=embedder,
    )
