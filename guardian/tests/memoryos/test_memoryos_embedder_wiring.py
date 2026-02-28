from __future__ import annotations

from memoryos.memoryos import Memoryos


class DummyLLMClient:
    def chat_completion(self, **kwargs) -> str:
        return "ok"

    def tokenize(self, text: str) -> list[int]:
        return list(range(len((text or "").split())))


class FakeEmbedder:
    name = "fake"
    model_name = "fake-v1"

    def embed(self, text: str) -> list[float]:
        return [0.1, 0.2, 0.3]

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        return [[0.1, 0.2, 0.3] for _ in texts]


def test_memoryos_propagates_embedder_to_memory_modules(tmp_path, monkeypatch):
    monkeypatch.setattr("memoryos.memoryos.load_codemap", lambda: {})

    embedder = FakeEmbedder()
    mem = Memoryos(
        user_id="u1",
        data_storage_path=str(tmp_path),
        embedder=embedder,
        llm_client=DummyLLMClient(),
        llm_model="test-model",
    )

    assert mem.embedder is embedder
    assert mem.mid_term_memory.embedder is embedder
    assert mem.user_long_term_memory.embedder is embedder
    assert mem.assistant_long_term_memory.embedder is embedder
