"""Provider base interfaces."""

# SPDX-License-Identifier: MIT
from typing import Iterator, List, Optional, Protocol


class ChatProvider(Protocol):
    name: str

    def generate(self, prompt: str, model: Optional[str] = None, **kw) -> str: ...

    def stream(
        self, prompt: str, model: Optional[str] = None, **kw
    ) -> Iterator[str]: ...


class EmbeddingsProvider(Protocol):
    name: str

    def embed(
        self, texts: List[str], model: Optional[str] = None, **kw
    ) -> List[List[float]]: ...
