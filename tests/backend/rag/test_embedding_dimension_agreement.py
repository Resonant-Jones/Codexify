"""Regression tests for the shared vector store's embedding dimension.

A Chroma collection's dimension is fixed by its FIRST write. If any writer
touches the shared collection with vectors of a different width than the
configured local model produces, the collection is permanently fixed at that
width and every subsequent real embedding is refused with:

    Collection expecting embedding with dimension of 384, got 1024

This is the failure the 2026-11-05 stock Compose qualification recorded:
the shared collection ``codexify_vault_supported`` was created at 384 while
the configured local embedder (``bge-large-en-v1.5``) produces 1024, so every
document embedding failed closed and document ingestion did not work on the
stock path.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest


# ---------------------------------------------------------------------------
# The configured model's own dimension is derived, not hardcoded
# ---------------------------------------------------------------------------


def _write_model_config(directory: Path, hidden_size: int) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "config.json").write_text(
        json.dumps({"hidden_size": hidden_size, "model_type": "bert"}),
        encoding="utf-8",
    )


def test_the_dimension_is_derived_from_the_configured_model(tmp_path, monkeypatch):
    """The helper reports the model's own width, not a constant."""
    from guardian.utils.embed_paths import resolve_local_embed_dimension

    model_dir = tmp_path / "bge-large-en-v1.5"
    _write_model_config(model_dir, 1024)
    monkeypatch.setenv("LOCAL_EMBED_MODEL", str(model_dir))

    assert resolve_local_embed_dimension(strict=False) == 1024


def test_a_different_model_reports_its_own_width(tmp_path, monkeypatch):
    """384 is bge-small's width; the helper must not assume one width."""
    from guardian.utils.embed_paths import resolve_local_embed_dimension

    model_dir = tmp_path / "bge-small-en-v1.5"
    _write_model_config(model_dir, 384)
    monkeypatch.setenv("LOCAL_EMBED_MODEL", str(model_dir))

    assert resolve_local_embed_dimension(strict=False) == 384


def test_no_configured_model_resolves_to_none(monkeypatch):
    from guardian.utils.embed_paths import resolve_local_embed_dimension

    monkeypatch.delenv("LOCAL_EMBED_MODEL", raising=False)
    assert resolve_local_embed_dimension(strict=False) is None


def test_an_unreadable_model_config_resolves_to_none(tmp_path, monkeypatch):
    from guardian.utils.embed_paths import resolve_local_embed_dimension

    model_dir = tmp_path / "no-config"
    model_dir.mkdir()
    monkeypatch.setenv("LOCAL_EMBED_MODEL", str(model_dir))
    assert resolve_local_embed_dimension(strict=False) is None


# ---------------------------------------------------------------------------
# The mock backend agrees with the configured model
# ---------------------------------------------------------------------------


def test_the_mock_backend_uses_the_configured_models_dimension(
    tmp_path, monkeypatch
):
    """The mock must not claim a width the configured model does not have.

    The mock backend previously hardcoded 384 under a comment claiming that
    matched ``bge-large-en-v1.5``. It does not: bge-large-en-v1.5 is
    1024-dimensional. Because a Chroma collection's dimension is fixed by its
    first write, a mock write fixed the shared collection at 384 and every
    real bge-large embedding was then refused.
    """
    from backend.rag.embedder import Embedder

    model_dir = tmp_path / "bge-large-en-v1.5"
    _write_model_config(model_dir, 1024)
    monkeypatch.setenv("LOCAL_EMBED_MODEL", str(model_dir))
    monkeypatch.setenv("CODEXIFY_EMBEDDINGS_BACKEND", "mock")
    monkeypatch.setenv("CODEXIFY_VECTOR_STORE", "faiss")

    embedder = Embedder(store="faiss", chroma_path=str(tmp_path / "chroma"))

    assert embedder._model.dim == 1024, (
        "the mock backend's vectors must be the same width as the configured "
        "model's, or the first write fixes the shared collection at the "
        "wrong dimension"
    )


def test_the_mock_backend_does_not_silently_use_384_for_a_1024_model(
    tmp_path, monkeypatch
):
    """Explicitly assert the specific defect does not recur."""
    from backend.rag.embedder import Embedder

    model_dir = tmp_path / "bge-large-en-v1.5"
    _write_model_config(model_dir, 1024)
    monkeypatch.setenv("LOCAL_EMBED_MODEL", str(model_dir))
    monkeypatch.setenv("CODEXIFY_EMBEDDINGS_BACKEND", "mock")
    monkeypatch.setenv("CODEXIFY_VECTOR_STORE", "faiss")

    embedder = Embedder(store="faiss", chroma_path=str(tmp_path / "chroma"))

    assert embedder._model.dim != 384


def test_the_zero_embedding_fallback_matches_the_configured_model(
    tmp_path, monkeypatch
):
    """The memoryos zero-embedding fallback must not be a second 384."""
    from guardian.memoryos import utils as memoryos_utils

    model_dir = tmp_path / "bge-large-en-v1.5"
    _write_model_config(model_dir, 1024)
    monkeypatch.setenv("LOCAL_EMBED_MODEL", str(model_dir))

    vector = memoryos_utils._zero_embedding()

    assert vector.shape[0] == 1024


# ---------------------------------------------------------------------------
# The original failure signature cannot recur
# ---------------------------------------------------------------------------


def test_a_mock_write_then_a_real_write_share_one_collection(tmp_path, monkeypatch):
    """The end-to-end proof: the original error is impossible now.

    A mock write fixes the collection's dimension. A later write carrying the
    real model's width must therefore be accepted. Before the fix this raised
    "Collection expecting embedding with dimension of 384, got 1024".
    """
    chromadb = pytest.importorskip("chromadb")

    from backend.rag.embedder import Embedder

    model_dir = tmp_path / "bge-large-en-v1.5"
    _write_model_config(model_dir, 1024)
    monkeypatch.setenv("LOCAL_EMBED_MODEL", str(model_dir))
    monkeypatch.setenv("CODEXIFY_EMBEDDINGS_BACKEND", "mock")
    monkeypatch.setenv("CODEXIFY_VECTOR_STORE", "chroma")

    chroma_path = str(tmp_path / "chroma")
    mock_embedder = Embedder(store="chroma", chroma_path=chroma_path)
    mock_result = mock_embedder.embed_and_index(
        ["first document"], metadatas=[{"kind": "probe"}], ids_prefix="probe"
    )
    assert int(mock_result.get("count", 0)) == 1

    # The real model's width must now be accepted by the same collection.
    real_embedder = Embedder(store="chroma", chroma_path=chroma_path)
    real_embedder._model = _FixedWidthModel(1024)
    real_result = real_embedder.embed_and_index(
        ["second document"], metadatas=[{"kind": "document"}], ids_prefix="doc"
    )
    assert int(real_result.get("count", 0)) == 1


class _FixedWidthModel:
    """Minimal stand-in for the loaded local model."""

    def __init__(self, dim: int) -> None:
        self.dim = dim

    def encode(self, texts, **_kwargs):
        import numpy as np

        return np.zeros((len(texts), self.dim), dtype="float32")


def test_the_health_probe_does_not_write_into_the_shared_collection(
    tmp_path, monkeypatch
):
    """A health probe must never pollute the collection it probes.

    The probe's backend detection could disagree with the canonical runtime
    (the env default for CODEXIFY_VECTOR_STORE is "faiss" while the supported
    runtime resolves "chroma"), which made it take the shared-store branch and
    write its probe vector into the shared collection.
    """
    chromadb = pytest.importorskip("chromadb")

    from guardian.core.config import resolve_vector_store_runtime

    monkeypatch.setenv("CODEXIFY_VECTOR_STORE", "chroma")
    monkeypatch.setenv("CODEXIFY_CHROMA_PATH", str(tmp_path / "chroma"))

    runtime = resolve_vector_store_runtime()
    assert runtime.backend == "chroma"

    # The shared collection must be untouched by a probe run.
    client = chromadb.PersistentClient(path=runtime.chroma_path)
    shared = client.get_or_create_collection(name=runtime.collection)
    before = shared.count()

    from guardian.routes import health as health_route

    monkeypatch.setattr(
        health_route, "get_single_user_id", lambda: "local", raising=False
    )
    response = health_route.health_vector()

    after = client.get_or_create_collection(name=runtime.collection).count()
    assert after == before, (
        "the health probe wrote into the shared collection; a probe vector of "
        "a different width would fix the collection's dimension for good"
    )
    assert response.get("status") in {"ok", "down", "error"}
