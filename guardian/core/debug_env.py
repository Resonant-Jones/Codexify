import os
import sys
from pathlib import Path

from dotenv import load_dotenv

# Add project root to path
root = Path(__file__).resolve().parents[2]
sys.path.append(str(root))

print(f"Project root: {root}")

# Try loading .env manually using the same logic as dependencies.py
env_path = root / ".env"
print(f"Checking for .env at: {env_path}")
if env_path.exists():
    print(".env file exists")
    load_dotenv(env_path)
else:
    print(".env file NOT found")

# Check if key is present in os.environ
key = os.getenv("GROQ_API_KEY")
if key:
    print(f"GROQ_API_KEY found: {key[:4]}...{key[-4:]}")
else:
    print("GROQ_API_KEY NOT found in os.environ")

# Try importing config to see what pydantic sees
try:
    from guardian.core.config import get_settings

    settings = get_settings()
    print(
        f"Settings.GROQ_API_KEY: {settings.GROQ_API_KEY[:4] if settings.GROQ_API_KEY else 'None'}..."
    )
except Exception as e:
    print(f"Failed to load settings: {e}")
