from fastapi import Depends, Header, HTTPException, status
from .settings import settings  # however you load env

def require_ui_key(
    x_guardian_key: str = Header(default="", alias="X-Guardian-Key")
):
    if x_guardian_key != settings.PUBLIC_UI_KEY:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)