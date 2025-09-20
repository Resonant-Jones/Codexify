"""
Guardian TTS Package
-----------------
Text-to-speech synthesis package with pluggable provider support.
"""

from .tts_manager import TTSManager
from .tts_service import TTSError, TTSProvider

__all__ = ["TTSProvider", "TTSManager", "TTSError"]
