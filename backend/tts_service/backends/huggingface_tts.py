"""Hugging Face TTS backend implementation."""

import io
import logging
import platform
from functools import lru_cache
from typing import Optional

import numpy as np
import soundfile as sf
import torch
from transformers import pipeline

from .base import TTSBackend

logger = logging.getLogger(__name__)


def _detect_device() -> str:
    """Detect the best available device for inference."""
    if torch.cuda.is_available():
        return "cuda"
    elif hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
        # Apple Silicon MPS
        if platform.system() == "Darwin" and platform.processor() == "arm":
            return "mps"
    return "cpu"


@lru_cache(maxsize=4)
def _get_pipeline(model_id: str):
    """
    Get or create a cached TTS pipeline for the given model.

    Args:
        model_id: Hugging Face model identifier

    Returns:
        Cached transformers pipeline
    """
    device = _detect_device()
    logger.info(f"Loading TTS model {model_id} on device: {device}")

    try:
        pipe = pipeline(
            "text-to-speech",
            model=model_id,
            device=device,
        )
        logger.info(f"Successfully loaded {model_id}")
        return pipe
    except Exception as e:
        logger.error(f"Failed to load model {model_id}: {e}")
        raise


class HuggingFaceTTSBackend(TTSBackend):
    """TTS backend using Hugging Face transformers."""

    def __init__(self, model_id: str):
        """
        Initialize the Hugging Face TTS backend.

        Args:
            model_id: Hugging Face model identifier
        """
        self.model_id = model_id
        self._pipeline = None

    @property
    def pipeline(self):
        """Lazy-load the pipeline on first use."""
        if self._pipeline is None:
            self._pipeline = _get_pipeline(self.model_id)
        return self._pipeline

    def synthesize(
        self,
        text: str,
        *,
        voice: Optional[str] = None,
        speed: Optional[float] = None,
    ) -> tuple[bytes, int]:
        """
        Synthesize speech from text using Hugging Face models.

        Args:
            text: The text to synthesize
            voice: Optional voice identifier (model-specific)
            speed: Optional speed modifier (not implemented for HF models)

        Returns:
            tuple of (wav_bytes, sampling_rate)
        """
        logger.info(f"Synthesizing text: {text[:50]}...")

        # Generate audio
        result = self.pipeline(text)

        # Extract audio and sampling rate
        # Result format: {"audio": ndarray, "sampling_rate": int}
        audio = result["audio"]
        sampling_rate = result["sampling_rate"]

        # Normalize to float32
        if audio.dtype != np.float32:
            audio = audio.astype(np.float32)

        # Ensure audio is in the correct range [-1, 1]
        if audio.max() > 1.0 or audio.min() < -1.0:
            audio = np.clip(audio, -1.0, 1.0)

        # Encode to WAV in memory
        buffer = io.BytesIO()
        sf.write(buffer, audio, sampling_rate, format="WAV", subtype="PCM_16")
        wav_bytes = buffer.getvalue()

        logger.info(f"Generated {len(wav_bytes)} bytes at {sampling_rate} Hz")

        return wav_bytes, sampling_rate
