from dataclasses import dataclass
from typing import List, Optional

DEFAULT_CHUNK_SIZE = 1200
DEFAULT_CHUNK_OVERLAP = 200


@dataclass(frozen=True)
class DocumentChunk:
    index: int
    text: str


def chunk_document_text(
    text: Optional[str],
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    chunk_overlap: int = DEFAULT_CHUNK_OVERLAP,
) -> List[DocumentChunk]:
    if text is None:
        return []
    if chunk_size <= 0:
        raise ValueError("chunk_size must be positive.")
    if chunk_overlap < 0:
        raise ValueError("chunk_overlap must be non-negative.")
    if chunk_overlap >= chunk_size:
        raise ValueError("chunk_overlap must be smaller than chunk_size.")

    if len(text) <= chunk_size:
        return [DocumentChunk(index=0, text=text)]

    chunks: List[DocumentChunk] = []
    start = 0
    index = 0
    text_length = len(text)

    while start < text_length:
        end = min(start + chunk_size, text_length)
        chunks.append(DocumentChunk(index=index, text=text[start:end]))
        if end >= text_length:
            break
        start = end - chunk_overlap
        index += 1

    return chunks
