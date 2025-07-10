"""
Guardian TTS Package
-----------------
Text-to-speech synthesis package with pluggable provider support.
"""

from .tts_service import TTSProvider, TTSError
from .tts_manager import TTSManager

__all__ = ["TTSProvider", "TTSManager", "TTSError"]
