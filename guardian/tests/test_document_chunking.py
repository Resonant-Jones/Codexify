import pytest

from guardian.services.document_chunking import (
    DocumentChunk,
    chunk_document_text,
)


def test_chunk_document_text_returns_single_chunk_for_short_text():
    text = "short text"
    chunks = chunk_document_text(text, chunk_size=50, chunk_overlap=10)
    assert chunks == [DocumentChunk(index=0, text=text)]


def test_chunk_document_text_applies_overlap_and_order():
    text = "abcdefghijklmnopqrstuvwxyz"
    chunks = chunk_document_text(text, chunk_size=10, chunk_overlap=3)

    assert [chunk.index for chunk in chunks] == list(range(len(chunks)))
    for previous, current in zip(chunks, chunks[1:]):
        assert current.text.startswith(previous.text[-3:])


def test_chunk_document_text_is_deterministic():
    text = "repeatable text" * 10
    first = chunk_document_text(text, chunk_size=12, chunk_overlap=4)
    second = chunk_document_text(text, chunk_size=12, chunk_overlap=4)
    assert first == second


def test_chunk_document_text_rejects_invalid_overlap():
    with pytest.raises(ValueError):
        chunk_document_text("text", chunk_size=10, chunk_overlap=10)
