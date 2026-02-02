"""
TTS Trigger
~~~~~~~~~~~

Discovery-aware trigger for local TTS plugins (if available).
"""

from typing import Optional

import requests

from guardian.plugins.plugin_loader import load_all_manifests


def get_tts_plugin_endpoint() -> Optional[str]:
    for plugin in load_all_manifests():
        if "tts" in (plugin.capabilities or []):
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
