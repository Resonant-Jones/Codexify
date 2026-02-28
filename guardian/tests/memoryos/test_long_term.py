from collections import deque

import numpy as np
import pytest
from memoryos.long_term import LongTermMemory


class FakeEmbedder:
    name = "fake"
    model_name = "fake-v1"

    def embed(self, text: str) -> list[float]:
        lowered = text.lower()
        if "query about apple" in lowered:
            return [1.0, 0.0, 0.0]
        if "apple" in lowered:
            return [1.0, 0.1, 0.2]
        if "banana" in lowered:
            return [0.1, 1.0, 0.3]
        return [1.0, 0.0, 0.0]

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        return [self.embed(text) for text in texts]


@pytest.fixture
def ltm_instance(tmp_path) -> LongTermMemory:
    """
    This fixture creates a fresh LongTermMemory instance for each test.
    - It uses a temporary directory (`tmp_path`) for the database file.
    - It mocks (`monkeypatch`) external dependencies like get_embedding.
    """
    db_path = tmp_path / "ltm_test.json"
    ltm = LongTermMemory(
        file_path=str(db_path),
        knowledge_capacity=10,
        embedder=FakeEmbedder(),
    )
    return ltm


def test_add_and_get_knowledge(ltm_instance: LongTermMemory):
    """Verify that adding and retrieving a knowledge entry works."""
    ltm_instance.add_user_knowledge("An apple is a fruit.")
    knowledge = ltm_instance.get_user_knowledge()

    assert len(knowledge) == 1
    assert knowledge[0]["knowledge"] == "An apple is a fruit."
    assert "knowledge_embedding" in knowledge[0]
    expected = np.array([1.0, 0.1, 0.2], dtype=np.float32)
    expected = expected / np.linalg.norm(expected)
    assert np.allclose(knowledge[0]["knowledge_embedding"], expected.tolist())
    assert knowledge[0]["embedding_provider"] == "fake"
    assert knowledge[0]["embedding_model"] == "fake-v1"
    assert knowledge[0]["embedding_dim"] == 3


def test_save_and_load_cycle(ltm_instance: LongTermMemory, tmp_path):
    """Verify that data persists correctly after a save and load."""
    ltm_instance.add_user_knowledge("A banana is yellow.")
    ltm_instance.update_user_profile("user123", "Loves bananas.")

    # Create a new instance that loads from the same file path
    db_path = tmp_path / "ltm_test.json"
    new_ltm = LongTermMemory(file_path=str(db_path))

    # Check if data was loaded correctly
    assert len(new_ltm.get_user_knowledge()) == 1
    assert new_ltm.get_user_knowledge()[0]["knowledge"] == "A banana is yellow."
    assert new_ltm.get_raw_user_profile("user123") == "Loves bananas."


def test_legacy_embedder_fallback_remains_compatible(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "memoryos.utils.get_embedding",
        lambda _text: np.array([1.0, 0.0, 0.0], dtype=np.float32),
    )
    db_path = tmp_path / "ltm_legacy.json"
    ltm = LongTermMemory(file_path=str(db_path), knowledge_capacity=10)
    ltm.add_user_knowledge("legacy compatible")

    knowledge = ltm.get_user_knowledge()
    assert len(knowledge) == 1
    assert knowledge[0]["embedding_provider"] == "legacy_get_embedding"
    assert knowledge[0]["embedding_dim"] == 3


def test_search_knowledge_finds_closest_match(ltm_instance: LongTermMemory):
    """Verify that vector search returns the most similar item."""
    ltm_instance.add_user_knowledge("I like to eat apples.")
    ltm_instance.add_user_knowledge("I also like bananas.")

    # Search for "query about apple"
    # Our mock will give this query a vector similar to the "apple" entry.
    results = ltm_instance.search_user_knowledge("query about apple", top_k=1)

    assert len(results) == 1
    assert results[0]["knowledge"] == "I like to eat apples."


def test_search_skips_dimension_mismatch(ltm_instance: LongTermMemory):
    ltm_instance.add_user_knowledge("I like to eat apples.")
    # Simulate legacy/cross-provider vector with incompatible dimension.
    ltm_instance.knowledge_base.append(
        {
            "knowledge": "legacy-mismatch",
            "timestamp": "2026-01-01 00:00:00",
            "knowledge_embedding": [0.1, 0.2, 0.3, 0.4],
            "embedding_provider": "legacy",
            "embedding_model": "legacy-v0",
            "embedding_dim": 4,
        }
    )

    results = ltm_instance.search_user_knowledge("query about apple", top_k=5)
    assert any(item["knowledge"] == "I like to eat apples." for item in results)
    assert not any(item["knowledge"] == "legacy-mismatch" for item in results)


def test_knowledge_capacity_is_respected(ltm_instance: LongTermMemory):
    """Verify that the deque correctly respects the maxlen capacity."""
    ltm_instance.knowledge_capacity = 2
    ltm_instance.knowledge_base = deque(maxlen=2)

    ltm_instance.add_user_knowledge("Fact 1")
    ltm_instance.add_user_knowledge("Fact 2")
    ltm_instance.add_user_knowledge("Fact 3")  # This should push "Fact 1" out

    knowledge_texts = [
        k["knowledge"] for k in ltm_instance.get_user_knowledge()
    ]
    assert len(knowledge_texts) == 2
    assert "Fact 1" not in knowledge_texts
    assert "Fact 3" in knowledge_texts
