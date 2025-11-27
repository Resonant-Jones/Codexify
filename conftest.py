"""
Test bootstrap: seed env and harmonize imports.
"""

import os
import sys
from pathlib import Path

# Ensure legacy `memoryos.*` imports resolve to in-repo `guardian.memoryos.*`
try:
    import guardian.memoryos as _gm

    sys.modules.setdefault("memoryos", _gm)
except Exception:
    pass

# Ensure the repository root takes precedence over any installed packages
ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

"""
pytest bootstrap (quiet by default)
- Seeds dummy env so import-time Settings() validation can't crash collection.
- To debug loading order, run with: PYTEST_VERBOSE_BOOT=1 pytest -s
"""

# ---- Quiet banner (opt-in) ----
if os.getenv("PYTEST_VERBOSE_BOOT") == "1":
    print(">>> conftest.py:", __file__)
    print(">>> sys.path[0]:", sys.path[0])

# ---- Env seeding for tests/CI ----
os.environ.setdefault("GUARDIAN_ALLOW_DUMMY_SETTINGS", "1")
os.environ.setdefault("GENAI_API_KEY", "dummy")
os.environ.setdefault("NOTION_API_KEY", "dummy")
os.environ.setdefault("ANTHROPIC_API_KEY", "dummy")
os.environ.setdefault("OPENAI_API_KEY", "dummy")
os.environ.setdefault("GEMINI_API_KEY", "dummy")
os.environ.setdefault("GOOGLE_API_KEY", "dummy")

# ---- Simple secret masker for test logs ----
import logging


class _MaskSecrets(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        msg = str(record.getMessage())
        # Replace long token-like strings; keep messages readable
        record.msg = msg.replace(
            os.environ.get("OPENAI_API_KEY", "dummy"), "***"
        )
        for k in (
            "GENAI_API_KEY",
            "NOTION_API_KEY",
            "ANTHROPIC_API_KEY",
            "GEMINI_API_KEY",
            "GOOGLE_API_KEY",
        ):
            v = os.environ.get(k)
            if v and len(v) > 6:
                record.msg = record.msg.replace(v, "***")
        return True


logging.getLogger().addFilter(_MaskSecrets())
