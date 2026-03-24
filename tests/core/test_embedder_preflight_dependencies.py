from __future__ import annotations

from guardian.core import dependencies


def test_embedder_preflight_dependency_accessor_is_lightweight(
    monkeypatch,
) -> None:
    monkeypatch.setenv("EMBEDDER_PREFLIGHT_CACHE_TTL_SECONDS", "0")
    monkeypatch.setattr(dependencies, "_vector_store", None)
    monkeypatch.setattr(
        dependencies,
        "VectorStore",
        lambda *args, **kwargs: (_ for _ in ()).throw(
            AssertionError("VectorStore must not be constructed")
        ),
    )

    monkeypatch.setattr(
        "backend.rag.embedder.inspect_embedder_preflight",
        lambda: {
            "backend": "local",
            "model": "/models/default-local-embedder",
            "ready": True,
            "present": True,
            "reason": "local embedder preflight passed",
        },
    )

    payload = dependencies.get_embedder_preflight_status(force_refresh=True)

    assert payload["backend"] == "local"
    assert payload["ready"] is True
    assert payload["present"] is True


def test_embedder_preflight_dependency_accessor_uses_cache(
    monkeypatch,
) -> None:
    monkeypatch.setenv("EMBEDDER_PREFLIGHT_CACHE_TTL_SECONDS", "60")
    monkeypatch.setattr(dependencies, "_embedder_preflight_cache", None)
    monkeypatch.setattr(dependencies, "_embedder_preflight_cache_ts", 0.0)

    calls = {"count": 0}

    def _fake_preflight() -> dict[str, object]:
        calls["count"] += 1
        return {
            "backend": "stub",
            "model": None,
            "ready": True,
            "present": None,
            "reason": "local embedder preflight not applicable for stub backend",
        }

    monkeypatch.setattr(
        "backend.rag.embedder.inspect_embedder_preflight",
        _fake_preflight,
    )

    first = dependencies.get_embedder_preflight_status(force_refresh=False)
    second = dependencies.get_embedder_preflight_status(force_refresh=False)

    assert first == second
    assert calls["count"] == 1
