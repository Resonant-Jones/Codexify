"""Hugging Face TTS backend implementation."""

import io
import logging
import os
from functools import lru_cache
from typing import Optional

import numpy as np
import soundfile as sf
import torch

try:
    from transformers import pipeline as hf_pipeline
except Exception as exc:  # pragma: no cover
    hf_pipeline = None  # type: ignore[assignment]
    _PIPELINE_IMPORT_ERROR = exc
else:
    _PIPELINE_IMPORT_ERROR = None

# Optional: Qwen3-TTS native runtime (preferred for Qwen/Qwen3-TTS models)
try:
    from qwen_tts import Qwen3TTSModel  # type: ignore
except Exception:  # pragma: no cover
    Qwen3TTSModel = None  # type: ignore

from .base import TTSBackend

logger = logging.getLogger(__name__)


def _detect_device() -> str:
    """Detect the best available device for inference."""
    if torch.cuda.is_available():
        return "cuda"
    if hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
        return "mps"
    return "cpu"


def _qwen_device_map_and_dtype(device: str):
    # qwen-tts examples use device_map like "cuda:0".
    if device == "cuda":
        return "cuda:0", torch.bfloat16
    if device == "mps":
        # MPS generally prefers fp16/bf16, but be conservative if bf16 is unsupported.
        return "mps", torch.float16
    return "cpu", torch.float32


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
    offline = (
        os.environ.get("HF_HUB_OFFLINE") == "1"
        or os.environ.get("TRANSFORMERS_OFFLINE") == "1"
    )

    # Qwen3-TTS models ship a custom architecture (`qwen3_tts`).
    # In practice, `transformers.pipeline(..., trust_remote_code=True)` can still fail to
    # register that architecture depending on the transformers version. Prefer qwen-tts.
    if model_id.startswith("Qwen/Qwen3-TTS"):
        if Qwen3TTSModel is None:
            raise RuntimeError(
                "qwen-tts is required for Qwen3-TTS models but is not installed in this runtime"
            )
        device_map, dtype = _qwen_device_map_and_dtype(device)
        logger.info(
            f"Using qwen-tts runtime for {model_id} (device_map={device_map}, dtype={dtype})"
        )
        load_kwargs = {
            "device_map": device_map,
            "dtype": dtype,
            "low_cpu_mem_usage": True,
            "local_files_only": offline,
        }
        try:
            return Qwen3TTSModel.from_pretrained(
                model_id,
                **load_kwargs,
            )
        except TypeError as exc:
            logger.warning(
                "qwen-tts runtime rejected low-memory preload kwargs for %s; retrying with compatibility fallback: %s",
                model_id,
                exc,
            )
            load_kwargs.pop("low_cpu_mem_usage", None)
            load_kwargs.pop("local_files_only", None)
            return Qwen3TTSModel.from_pretrained(
                model_id,
                **load_kwargs,
            )

    # Non-Qwen models: use transformers pipeline.
    if hf_pipeline is None:
        raise RuntimeError(
            "transformers.pipeline is unavailable in this runtime."
        ) from _PIPELINE_IMPORT_ERROR

    try:
        pipe = hf_pipeline(
            "text-to-speech",
            model=model_id,
            device=device,
            model_kwargs={"local_files_only": offline},
        )
        logger.info(f"Successfully loaded {model_id}")
        return pipe
    except Exception as e:
        logger.error(f"Failed to load model {model_id}: {e}")
        raise


class HuggingFaceTTSBackend(TTSBackend):
    """TTS backend using Hugging Face transformers."""

    def __init__(self, model_id: str, *, mode: str = "custom_voice"):
        """
        Initialize the Hugging Face TTS backend.

        Args:
            model_id: Hugging Face model identifier
            mode: Synthesis mode - "custom_voice" or "voice_clone"
        """
        self.model_id = model_id
        self.mode = mode
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
        ref_audio: Optional[str] = None,
        ref_text: Optional[str] = None,
    ) -> tuple[bytes, int]:
        """
        Synthesize speech from text using Hugging Face models.

        Args:
            text: The text to synthesize
            voice: Optional voice identifier (model-specific)
            speed: Optional speed modifier (not yet supported)
            ref_audio: Path to reference audio (required for voice_clone mode)
            ref_text: Transcript of reference audio (for voice_clone mode)

        Returns:
            tuple of (wav_bytes, sampling_rate)
        """
        if speed is not None and speed != 1.0:
            logger.warning(
                "speed parameter is not yet supported for HF TTS; "
                "ignoring speed=%.2f",
                speed,
            )

        logger.info(f"Synthesizing text: {text[:50]}...")

        # Branch 1: Qwen3-TTS CustomVoice models
        if hasattr(self.pipeline, "generate_custom_voice"):
            speaker = (
                voice or os.environ.get("QWEN_TTS_DEFAULT_SPEAKER") or "Ryan"
            )
            wavs, sampling_rate = self.pipeline.generate_custom_voice(
                text=text,
                speaker=speaker,
                language="Auto",
            )
            audio = wavs[0]

        # Branch 2: Qwen3-TTS Base models (voice cloning)
        elif hasattr(self.pipeline, "generate_voice_clone"):
            if not ref_audio:
                raise ValueError(
                    f"Provider uses Base model '{self.model_id}' which "
                    "requires 'ref_audio' and 'ref_text' for voice cloning. "
                    "Use a CustomVoice provider for simple text-to-speech."
                )
            wavs, sampling_rate = self.pipeline.generate_voice_clone(
                text=text,
                ref_audio=ref_audio,
                ref_text=ref_text or "",
                language="Auto",
            )
            audio = wavs[0]

        # Branch 3: Generic transformers pipeline (non-Qwen models)
        else:
            result = self.pipeline(text)
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
