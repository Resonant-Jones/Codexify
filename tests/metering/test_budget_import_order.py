"""Quarantine helpers must not silently remove optional TTS providers at import."""

import os
from pathlib import Path
import subprocess
import sys

import pytest


@pytest.mark.parametrize(
    "first",
    [
        "guardian.metering.runtime",
        "guardian.db.models",
        "guardian.tts.providers.deepgram_provider",
    ],
)
def test_budget_import_does_not_break_tts_registration(first):
    # Fresh interpreter is essential: optional-provider imports swallow errors,
    # and testing only an already-imported module misses the circular dependency.
    code = f"""
import socket

def deny(*args, **kwargs):
    raise AssertionError("No network permitted in import-order regression")

socket.socket.connect = deny
socket.socket.connect_ex = deny
socket.socket.sendto = deny
socket.getaddrinfo = deny
import importlib
importlib.import_module({first!r})
from guardian.tts.providers import PROVIDERS
from guardian.tts.providers.deepgram_provider import DeepgramProvider
assert PROVIDERS.get("deepgram") is DeepgramProvider, list(PROVIDERS)
from guardian.metering.runtime import deny_unqualified_spend
deny_unqualified_spend()
"""
    env = dict(os.environ)
    env.pop("CODEXIFY_BOUNDED_OPENAI_BUDGET_JSON", None)
    result = subprocess.run(
        [sys.executable, "-c", code],
        cwd=Path(__file__).resolve().parents[2],
        env=env,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0, result.stderr
