from __future__ import annotations

import logging

from memoryos.mid_term import MidTermMemory


class DummyLLMClient:
    def chat_completion(self, **kwargs) -> str:
        return "ok"

    def tokenize(self, text: str) -> list[int]:
        return list(range(len((text or "").split())))


class RecordingEmbedder:
    name = "recording"
    model_name = "recording-v1"

    def __init__(self) -> None:
        self.calls: list[str] = []

    def embed(self, text: str) -> list[float]:
        self.calls.append(text)
        lowered = text.lower()
        if "mismatch" in lowered:
            return [0.1, 0.2, 0.3, 0.4]
        return [1.0, 0.1, 0.2]

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        return [self.embed(text) for text in texts]


def test_mid_term_uses_injected_embedder_and_persists_metadata(tmp_path):
    mem_path = tmp_path / "mid_term.json"
    embedder = RecordingEmbedder()
    mtm = MidTermMemory(
        file_path=str(mem_path),
        client=DummyLLMClient(),
        embedder=embedder,
        max_capacity=10,
    )

    sid = mtm.add_session(
        "summary",
        [
            {
                "user_input": "hello",
                "agent_response": "world",
                "timestamp": "2026-01-01 00:00:00",
            }
        ],
    )

    assert sid in mtm.sessions
    session = mtm.sessions[sid]
    assert session["embedding_provider"] == "recording"
    assert session["embedding_model"] == "recording-v1"
    assert session["embedding_dim"] == 3
    assert session["details"][0]["embedding_dim"] == 3
    assert len(embedder.calls) >= 2


def test_mid_term_search_logs_high_skip_ratio_on_dim_mismatch(tmp_path, caplog):
    mem_path = tmp_path / "mid_term.json"
    embedder = RecordingEmbedder()
    mtm = MidTermMemory(
        file_path=str(mem_path),
        client=DummyLLMClient(),
        embedder=embedder,
        max_capacity=10,
    )

    matching_sid = mtm.add_session(
        "summary",
        [
            {
                "user_input": "hello",
                "agent_response": "world",
                "timestamp": "2026-01-01 00:00:00",
            }
        ],
    )
    mismatch_sid = mtm.add_session(
        "mismatch summary",
        [
            {
                "user_input": "mismatch user",
                "agent_response": "mismatch response",
                "timestamp": "2026-01-01 00:00:01",
            }
        ],
    )

    assert matching_sid in mtm.sessions
    assert mismatch_sid in mtm.sessions

    with caplog.at_level(logging.WARNING):
        results = mtm.search_sessions("summary query", top_k_sessions=10)

    assert any(item["session_id"] == matching_sid for item in results)
    assert all(item["session_id"] != mismatch_sid for item in results)
    assert any(
        "memoryos.embedding.high_skip_ratio" in rec.message
        for rec in caplog.records
    )
