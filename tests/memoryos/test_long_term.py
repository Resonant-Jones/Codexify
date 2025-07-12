import pytest
import numpy as np
from collections import deque

from memoryos.long_term import LongTermMemory


# A mock embedding function to return predictable vectors for testing.
def mock_get_embedding(text: str) -> np.ndarray:
    """Returns a deterministic vector based on the text content."""
    text = text.lower()
    if "apple" in text:
        return np.array([1.0, 0.1, 0.2])
    if "banana" in text:
        return np.array([0.1, 1.0, 0.3])
    # Return a different vector for the query to test similarity
    return np.array([1.0, 0.0, 0.0])


@pytest.fixture
def ltm_instance(tmp_path, monkeypatch) -> LongTermMemory:
    """
    This fixture creates a fresh LongTermMemory instance for each test.
    - It uses a temporary directory (`tmp_path`) for the database file.
    - It mocks (`monkeypatch`) external dependencies like get_embedding.
    """
    # Replace the real get_embedding function with our mock
    monkeypatch.setattr("memoryos.long_term.get_embedding", mock_get_embedding)

    db_path = tmp_path / "ltm_test.json"
    ltm = LongTermMemory(file_path=str(db_path), knowledge_capacity=10)
    return ltm


def test_add_and_get_knowledge(ltm_instance: LongTermMemory):
    """Verify that adding and retrieving a knowledge entry works."""
    ltm_instance.add_user_knowledge("An apple is a fruit.")
    knowledge = ltm_instance.get_user_knowledge()

    assert len(knowledge) == 1
    assert knowledge[0]["knowledge"] == "An apple is a fruit."
    assert "knowledge_embedding" in knowledge[0]
    # The mock normalizes to a list, so we check the original un-normalized vector
    assert np.allclose(knowledge[0]["knowledge_embedding"], [1.0, 0.1, 0.2])


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


def test_search_knowledge_finds_closest_match(ltm_instance: LongTermMemory):
    """Verify that vector search returns the most similar item."""
    ltm_instance.add_user_knowledge("I like to eat apples.")
    ltm_instance.add_user_knowledge("I also like bananas.")

    # Search for "query about apple"
    # Our mock will give this query a vector similar to the "apple" entry.
    results = ltm_instance.search_user_knowledge("query about apple", top_k=1)

    assert len(results) == 1
    assert results[0]["knowledge"] == "I like to eat apples."


def test_knowledge_capacity_is_respected(ltm_instance: LongTermMemory):
    """Verify that the deque correctly respects the maxlen capacity."""
    ltm_instance.knowledge_capacity = 2
    ltm_instance.knowledge_base = deque(maxlen=2)

    ltm_instance.add_user_knowledge("Fact 1")
    ltm_instance.add_user_knowledge("Fact 2")
    ltm_instance.add_user_knowledge("Fact 3")  # This should push "Fact 1" out

    knowledge_texts = [k["knowledge"] for k in ltm_instance.get_user_knowledge()]
    assert len(knowledge_texts) == 2
    assert "Fact 1" not in knowledge_texts
    assert "Fact 3" in knowledge_texts