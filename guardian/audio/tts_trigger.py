"""
TTS Trigger
~~~~~~~~~~~

Discovery-aware trigger for local TTS plugins (if available).
"""

from typing import Optional

import requests

from guardian.core.plugins import get_plugin_manifest_by_capability


def get_tts_plugin_endpoint() -> Optional[str]:
    plugin = get_plugin_manifest_by_capability("tts")
    if plugin:
        return plugin.entrypoint.rstrip("/") + "/speak"
    return None


def trigger_tts_if_available(
    text: str, metadata: Optional[dict] = None
) -> bool:
    metadata = metadata or {}
    endpoint = get_tts_plugin_endpoint()

    if not endpoint:
        print("[TTS] No TTS plugin discovered in manifest.")
        return False

    try:
        response = requests.post(
            endpoint, json={"text": text, "metadata": metadata}, timeout=8
        )
        return response.status_code == 200
    except Exception as e:
        print(f"[TTS] Error calling TTS plugin: {e}")
        return False
