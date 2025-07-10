from dotenv import load_dotenv
import pytest
import os

load_dotenv()

from .local_embedder import LocalEmbedder
from .groq_embedder import GroqEmbedder
from .openai_embedder import OpenAIEmbedder
from .anthropic_embedder import AnthropicEmbedder
from .gemini_embedder import GeminiEmbedder

# Expected dimensions for various models to make tests more robust and maintainable.
EXPECTED_DIMS = {
    "local": 384,        # all-MiniLM-L6-v2
    "openai": 3072,      # text-embedding-3-large
    "gemini": 768,       # embedding-001
    "groq": 768,         # nomic-embed-text
}

@pytest.mark.parametrize(
    "embedder_class, dim_key, api_key_env_var, init_with_key",
    [
        (LocalEmbedder, "local", None, False),
        pytest.param(GroqEmbedder, "groq", "GROQ_API_KEY", False, marks=pytest.mark.api),
        pytest.param(OpenAIEmbedder, "openai", "OPENAI_API_KEY", True, marks=pytest.mark.api),
        pytest.param(GeminiEmbedder, "gemini", "GEMINI_API_KEY", False, marks=pytest.mark.api),
    ],
    ids=["local", "groq", "openai", "gemini"]
)
def test_embedders_common_interface(embedder_class, dim_key, api_key_env_var, init_with_key):
    """Tests that embedders correctly produce a vector of the expected shape."""
    api_key = None
    if api_key_env_var:
        api_key = os.getenv(api_key_env_var)
        if not api_key:
            pytest.skip(f"Skipping {embedder_class.__name__} test: {api_key_env_var} not set.")

    # Instantiate the embedder
    if init_with_key:
        embedder = embedder_class(api_key=api_key)
    else:
        embedder = embedder_class()

    # Test embedding and validate the output
    embedding = embedder.embed("This is a test sentence.")
    assert isinstance(embedding, list)
    assert len(embedding) == EXPECTED_DIMS[dim_key], "Embedding has incorrect dimension."
    assert all(isinstance(x, float) for x in embedding)

@pytest.mark.api
def test_anthropic_embedder():
    """Tests that the Anthropic embedder correctly raises NotImplementedError."""
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        pytest.skip("Skipping Anthropic test: ANTHROPIC_API_KEY not set.")

    embedder = AnthropicEmbedder()
    with pytest.raises(NotImplementedError):
        embedder.embed("This is a test sentence.")