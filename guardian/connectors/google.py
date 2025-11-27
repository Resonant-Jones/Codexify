import os
import time
from urllib.parse import urlencode

import requests
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse

from guardian.auth import get_current_user  # your user dependency
from guardian.crypto import decrypt_str, encrypt_str  # helpers (see below)
from guardian.db import save_oauth_tokens  # implement per your DB layer

router = APIRouter(prefix="/connect/google", tags=["connectors"])

GOOGLE_CLIENT_ID = os.environ["GOOGLE_OAUTH_CLIENT_ID"]
GOOGLE_CLIENT_SECRET = os.environ["GOOGLE_OAUTH_CLIENT_SECRET"]
REDIRECT_URI = os.environ.get(
    "GOOGLE_OAUTH_REDIRECT", "http://localhost:8000/connect/google/callback"
)

SCOPES = [
    "https://www.googleapis.com/auth/drive.readonly",
    "openid",
    "email",
    "profile",
]


@router.get("/start")
def start_connect(user=Depends(get_current_user)):
    state = f"{user['id']}:{int(time.time())}"  # you should sign this state
    params = {
        "client_id": GOOGLE_CLIENT_ID,
        "response_type": "code",
        "scope": " ".join(SCOPES),
        "access_type": "offline",  # important => refresh_token returned
        "prompt": "consent",  # ensure refresh_token on repeated auth
        "redirect_uri": REDIRECT_URI,
        "state": state,
    }
    url = "https://accounts.google.com/o/oauth2/v2/auth?" + urlencode(params)
    return RedirectResponse(url)


@router.get("/callback")
def callback(code: str = None, state: str = None, request: Request = None):
    # validate `state` (signature/CSRF) in prod
    if not code:
        raise HTTPException(400, "Missing code")
    token_url = "https://oauth2.googleapis.com/token"
    data = {
        "code": code,
        "client_id": GOOGLE_CLIENT_ID,
        "client_secret": GOOGLE_CLIENT_SECRET,
        "redirect_uri": REDIRECT_URI,
        "grant_type": "authorization_code",
    }
    r = requests.post(token_url, data=data, timeout=10)
    r.raise_for_status()
    token_data = r.json()
    # token_data contains access_token, expires_in, refresh_token (maybe), scope, id_token etc.

    # Identify user from state (or require a session cookie). Here we assume state encodes user_id.
    user_id = state.split(":")[0]

    expires_at = None
    if "expires_in" in token_data:
        expires_at = int(time.time()) + int(
            token_data["expires_in"]
        )  # store as epoch or ISO

    save_oauth_tokens(
        user_id=user_id,
        provider="google-drive",
        provider_account_id=None,
        access_token=encrypt_str(token_data["access_token"]),
        refresh_token=encrypt_str(token_data.get("refresh_token")),
        scope=token_data.get("scope", ""),
        expires_at=str(expires_at),
    )

    # redirect back to UI with success
    return RedirectResponse("/?connected=google-drive")


def refresh_google_token(row):
    refresh_token = decrypt_str(row["refresh_token"])
    token_url = "https://oauth2.googleapis.com/token"
    data = {
        "client_id": GOOGLE_CLIENT_ID,
        "client_secret": GOOGLE_CLIENT_SECRET,
        "grant_type": "refresh_token",
        "refresh_token": refresh_token,
    }
    r = requests.post(token_url, data=data, timeout=10)
    r.raise_for_status()
    token_data = r.json()
    # update DB: new access_token, possibly new refresh_token, new expires_at
    update_oauth_tokens(
        row["id"],
        access_token=encrypt_str(token_data["access_token"]),
        refresh_token=encrypt_str(
            token_data.get("refresh_token") or refresh_token
        ),
        expires_at=str(
            int(time.time()) + int(token_data.get("expires_in", 3600))
        ),
    )
