from __future__ import annotations
import os
from pathlib import Path
from typing import Optional, Tuple

SCOPES = ["https://www.googleapis.com/auth/drive.file"]


def _default_token_path() -> Path:
    # repo_root = guardian/integrations/ -> parents[2]
    return Path(__file__).resolve().parents[2] / "secrets" / "token.json"


def _resolve_paths() -> Tuple[Optional[Path], Path]:
    creds_path = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
    token_env = os.environ.get("GDRIVE_OAUTH_TOKEN")
    token_path = Path(token_env) if token_env else _default_token_path()
    token_path.parent.mkdir(parents=True, exist_ok=True)
    return (Path(creds_path) if creds_path else None, token_path)


def ensure_oauth_credentials() -> str:
    """
    Ensures an OAuth token exists at the resolved token path.
    - If token.json already exists and is valid, returns its path.
    - If legacy token.pickle exists next to it, migrates content to token.json.
    - Otherwise runs the Installed App flow using GOOGLE_APPLICATION_CREDENTIALS.
    Returns the token file path as string.
    """
    # Lazy imports (optional deps)
    import json
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow

    creds_path, token_path = _resolve_paths()

    # Migrate legacy token.pickle → token.json if present
    legacy_pickle = token_path.with_suffix(".pickle")
    if legacy_pickle.exists() and not token_path.exists():
        try:
            import pickle

            with legacy_pickle.open("rb") as f:
                old = pickle.load(f)
            data = {
                "token": getattr(old, "token", None),
                "refresh_token": getattr(old, "refresh_token", None),
                "token_uri": getattr(old, "token_uri", "https://oauth2.googleapis.com/token"),
                "client_id": getattr(old, "client_id", None),
                "client_secret": getattr(old, "client_secret", None),
                "scopes": getattr(old, "scopes", SCOPES),
            }
            token_path.write_text(json.dumps(data))
        except Exception:
            # ignore migration errors; we'll just run flow below
            pass

    creds = None
    if token_path.exists():
        try:
            creds = Credentials.from_authorized_user_file(str(token_path), SCOPES)
        except Exception:
            creds = None
    if creds and creds.expired and getattr(creds, "refresh_token", None):
        try:
            creds.refresh(Request())
            token_path.write_text(creds.to_json())
            os.environ["GDRIVE_OAUTH_TOKEN"] = str(token_path)
            return str(token_path)
        except Exception:
            creds = None
    if not creds:
        if not creds_path or not Path(creds_path).exists():
            raise RuntimeError(
                "OAuth client secret missing. Set GOOGLE_APPLICATION_CREDENTIALS to your client_secret JSON."
            )
        flow = InstalledAppFlow.from_client_secrets_file(str(creds_path), SCOPES)
        # local server flow opens browser
        creds = flow.run_local_server(port=0)
        token_path.write_text(creds.to_json())
    # Ensure env is set so downstream libs can see it
    os.environ["GDRIVE_OAUTH_TOKEN"] = str(token_path)
    return str(token_path)

