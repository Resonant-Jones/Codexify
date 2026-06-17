"""Headless voiceover text planning for local TTS rendering."""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import StrEnum

from guardian.tts.config import LocalTTSConfig, get_local_tts_config


class VoiceoverChunkKind(StrEnum):
    SPEECH = "speech"
    SHORT_PAUSE = "short_pause"
    LONG_PAUSE = "long_pause"


@dataclass(frozen=True)
class VoiceoverChunk:
    kind: VoiceoverChunkKind
    text: str = ""
    pause_ms: int = 0

    def to_dict(self) -> dict[str, str | int]:
        return {
            "kind": self.kind.value,
            "text": self.text,
            "pause_ms": self.pause_ms,
        }


_TOKEN_PATTERN = re.compile(r"(\[pause\]|\.\.\.)", re.IGNORECASE)


def plan_voiceover_chunks(
    text: str,
    *,
    config: LocalTTSConfig | None = None,
) -> list[VoiceoverChunk]:
    """Split voiceover text while preserving timing intent markers."""

    cfg = config or get_local_tts_config()
    chunks: list[VoiceoverChunk] = []
    for part in _TOKEN_PATTERN.split(text or ""):
        if not part:
            continue
        marker = part.lower()
        if marker == "[pause]":
            chunks.append(
                VoiceoverChunk(
                    kind=VoiceoverChunkKind.LONG_PAUSE,
                    pause_ms=cfg.long_pause_ms,
                )
            )
            continue
        if marker == "...":
            chunks.append(
                VoiceoverChunk(
                    kind=VoiceoverChunkKind.SHORT_PAUSE,
                    pause_ms=cfg.short_pause_ms,
                )
            )
            continue
        chunks.extend(_split_speech(part, max_chars=cfg.chunk_max_chars))
    return _coalesce_pauses(chunks)


def _split_speech(text: str, *, max_chars: int) -> list[VoiceoverChunk]:
    normalized = " ".join(text.split())
    if not normalized:
        return []
    if len(normalized) <= max_chars:
        return [VoiceoverChunk(kind=VoiceoverChunkKind.SPEECH, text=normalized)]

    sentences = re.split(r"(?<=[.!?])\s+", normalized)
    chunks: list[VoiceoverChunk] = []
    current = ""
    for sentence in sentences:
        if not sentence:
            continue
        if len(sentence) > max_chars:
            if current:
                chunks.append(
                    VoiceoverChunk(kind=VoiceoverChunkKind.SPEECH, text=current)
                )
                current = ""
            chunks.extend(_split_long_sentence(sentence, max_chars=max_chars))
            continue
        candidate = f"{current} {sentence}".strip()
        if current and len(candidate) > max_chars:
            chunks.append(
                VoiceoverChunk(kind=VoiceoverChunkKind.SPEECH, text=current)
            )
            current = sentence
        else:
            current = candidate
    if current:
        chunks.append(VoiceoverChunk(kind=VoiceoverChunkKind.SPEECH, text=current))
    return chunks


def _split_long_sentence(text: str, *, max_chars: int) -> list[VoiceoverChunk]:
    words = text.split()
    chunks: list[VoiceoverChunk] = []
    current = ""
    for word in words:
        candidate = f"{current} {word}".strip()
        if current and len(candidate) > max_chars:
            chunks.append(
                VoiceoverChunk(kind=VoiceoverChunkKind.SPEECH, text=current)
            )
            current = word
        else:
            current = candidate
    if current:
        chunks.append(VoiceoverChunk(kind=VoiceoverChunkKind.SPEECH, text=current))
    return chunks


def _coalesce_pauses(chunks: list[VoiceoverChunk]) -> list[VoiceoverChunk]:
    coalesced: list[VoiceoverChunk] = []
    for chunk in chunks:
        if (
            coalesced
            and chunk.kind != VoiceoverChunkKind.SPEECH
            and coalesced[-1].kind != VoiceoverChunkKind.SPEECH
        ):
            previous = coalesced[-1]
            coalesced[-1] = VoiceoverChunk(
                kind=VoiceoverChunkKind.LONG_PAUSE
                if (
                    previous.kind == VoiceoverChunkKind.LONG_PAUSE
                    or chunk.kind == VoiceoverChunkKind.LONG_PAUSE
                )
                else VoiceoverChunkKind.SHORT_PAUSE,
                pause_ms=max(previous.pause_ms, chunk.pause_ms),
            )
        else:
            coalesced.append(chunk)
    return coalesced
