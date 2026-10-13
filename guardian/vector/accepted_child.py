"""Private child protocol: initialize or search; no additions or vector writes."""

from __future__ import annotations

import os
import hashlib
import pickle
import sys


def model_weight_digest(model):
    """Attest the actual tensor state; caller must run inside an owned child."""
    import torch

    digest = hashlib.sha256()
    for name, tensor in model.state_dict().items():
        digest.update(pickle.dumps((name, str(tensor.dtype), tuple(tensor.shape))))
        raw = tensor.detach().cpu().contiguous().reshape(-1).view(torch.uint8).numpy()
        digest.update(memoryview(raw))
    return digest.hexdigest()


def load_bound_model(binding):
    from backend.rag.embedder import LocalSemanticEmbedder
    from guardian.embeddings.mock_backend import MockEmbeddingBackend

    if binding["backend"] == "mock":
        return MockEmbeddingBackend(dim=binding["dim"], normalize=binding["normalize"])
    handle = LocalSemanticEmbedder.__new__(LocalSemanticEmbedder)
    handle._backend_type = binding["backend"]
    handle._model_override = binding["model"]
    model = handle._load_sentence_transformer(
        binding["model"], local_files_only=binding["backend"] == "local"
    )
    model.to(binding["device"])
    model.max_seq_length = binding["max_seq_length"]
    model.prompts = binding["prompts"]
    model.default_prompt_name = binding["default_prompt_name"]
    model.truncate_dim = binding["truncate_dim"]
    if model_weight_digest(model) != binding["model_digest"]:
        raise RuntimeError("Captured native embedding weights are unavailable")
    return model


def main():
    request = pickle.load(sys.stdin.buffer)
    os.environ["HF_HUB_OFFLINE"] = "1"
    os.environ["TRANSFORMERS_OFFLINE"] = "1"
    if request["operation"] == "initialize":
        if request["local_model"] is None:
            os.environ.pop("LOCAL_EMBED_MODEL", None)
        else:
            os.environ["LOCAL_EMBED_MODEL"] = request["local_model"]
    from backend.rag.embedder import LocalSemanticEmbedder, _create_chroma_client
    from guardian.vector.accepted_deadline import model_binding

    handle = LocalSemanticEmbedder.__new__(LocalSemanticEmbedder)
    handle.store = request["store"]
    handle.chroma_path = request["chroma_path"]
    handle.collection = request["collection"]
    handle._index = None
    handle._texts = []
    handle._metadatas = []
    handle._chroma_collection = None
    if request["operation"] == "initialize":
        handle._backend_type = request["backend"]
        handle._model_override = request["model"]
        os.environ["CODEXIFY_ALLOW_EMBEDDINGS_FALLBACK"] = (
            "1" if request["allow_fallback"] else "0"
        )
        handle._model = handle._init_embedding_model()
        if handle.store == "chroma":
            # Canonical unscoped bootstrap owns collection creation.
            _create_chroma_client(handle.chroma_path).get_collection(handle.collection)
        result = model_binding(handle)
        if result["backend"] != "mock":
            result["model_digest"] = model_weight_digest(handle._model)
    elif request["operation"] == "search":
        binding = request["binding"]
        handle._backend_type = binding["backend"]
        handle.model_name = binding["model"]
        snapshot = None
        if request["snapshot_fd"] is not None:
            with os.fdopen(request["snapshot_fd"], "rb") as stream:
                snapshot = pickle.load(stream)
            if binding["backend"] != "mock":
                binding["model_digest"] = snapshot["model_digest"]
        if handle.store == "faiss":
            import faiss

            handle._index = faiss.deserialize_index(snapshot["index"])
            handle._index_dim = handle._index.d
            handle._texts = snapshot["texts"]
            handle._metadatas = snapshot["metadata"]
        elif handle.store == "chroma":
            handle._chroma_collection = _create_chroma_client(
                handle.chroma_path
            ).get_collection(handle.collection)
        else:
            raise ValueError("Unknown vector backend")
        handle._model = load_bound_model(binding)
        result = handle.search(
            request["query"],
            k=request["k"],
            namespace=request["namespace"],
            user_id=request["user_id"],
        )
    else:
        raise ValueError("Unknown bounded vector operation")
    pickle.dump(result, sys.stdout.buffer, protocol=5)
    sys.stdout.buffer.flush()


if __name__ == "__main__":
    main()
