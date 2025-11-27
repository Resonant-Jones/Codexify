from __future__ import annotations

import json
import os
from pathlib import Path

from google.oauth2.credentials import Credentials as OAuthCredentials
from google.oauth2.service_account import Credentials as SACredentials
from googleapiclient.discovery import build

SCOPES = ["https://www.googleapis.com/auth/drive.file"]


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def resolve_token_path() -> Path:
    p = os.environ.get("GDRIVE_OAUTH_TOKEN")
    if p:
        return Path(p)
    return _repo_root() / "secrets" / "token.json"


def is_service_account(creds_path: Path) -> bool:
    try:
        data = json.loads(creds_path.read_text())
        return isinstance(data, dict) and data.get("type") == "service_account"
    except Exception:
        return False


def build_drive_service(logger=None):
    """
    Build a Drive v3 client using either Service Account JSON (GOOGLE_APPLICATION_CREDENTIALS)
    or OAuth token.json (GDRIVE_OAUTH_TOKEN or secrets/token.json).
    """
    creds_json = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
    token_json = resolve_token_path()

    if creds_json:
        cpath = Path(creds_json)
        if cpath.exists() and is_service_account(cpath):
            if logger:
                logger.info(
                    "Drive auth: using Service Account at %s", str(cpath)
                )
            creds = SACredentials.from_service_account_file(
                str(cpath), scopes=SCOPES
            )
            return build(
                "drive", "v3", credentials=creds, cache_discovery=False
            )
        # Else: OAuth path — token.json must exist
        if token_json.exists():
            if logger:
                logger.info(
                    "Drive auth: using OAuth token at %s (client at %s)",
                    str(token_json),
                    str(cpath),
                )
            creds = OAuthCredentials.from_authorized_user_file(
                str(token_json), SCOPES
            )
            return build(
                "drive", "v3", credentials=creds, cache_discovery=False
            )
        raise RuntimeError(
            "OAuth token not found at %s. Run /codexify/oauth-begin first."
            % str(token_json)
        )

    # No GOOGLE_APPLICATION_CREDENTIALS => rely on token.json only
    if token_json.exists():
        if logger:
            logger.info(
                "Drive auth: using OAuth token at %s (no client secret provided)",
                str(token_json),
            )
        creds = OAuthCredentials.from_authorized_user_file(
            str(token_json), SCOPES
        )
        return build("drive", "v3", credentials=creds, cache_discovery=False)
    raise RuntimeError(
        "No Drive credentials. Set GOOGLE_APPLICATION_CREDENTIALS or provide token.json at %s"
        % str(token_json)
    )
