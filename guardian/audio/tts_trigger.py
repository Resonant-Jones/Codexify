"""
TTS Trigger
~~~~~~~~~~~

Discovery-aware trigger for local TTS plugins (if available).
"""

import os

import requests

# Known TTS plugins: "chatterbox", "lfm25", etc.
DEFAULT_TTS_PLUGIN = os.environ.get("TTS_PLUGIN_ID", "chatterbox")
# TODO: Replace hardcoded TTS_PLUGIN_ENDPOINTS with plugin manifest lookup
TTS_PLUGIN_ENDPOINTS = {
    "chatterbox": "http://localhost:7101/speak",
    "lfm25": "http://localhost:7200/voice",
}


def trigger_tts_if_available(text: str, metadata: dict = {}) -> bool:
    plugin_id = DEFAULT_TTS_PLUGIN
    endpoint = TTS_PLUGIN_ENDPOINTS.get(plugin_id)

    if not endpoint:
        print(f"[TTS] No endpoint defined for plugin {plugin_id}")
        return False

    try:
        response = requests.post(
            endpoint, json={"text": text, "metadata": metadata}, timeout=8
        )
        return response.status_code == 200
    except Exception as e:
        print(f"[TTS] Error calling TTS plugin: {e}")
        return False
