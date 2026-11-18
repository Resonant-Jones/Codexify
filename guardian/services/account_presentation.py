"""Account-owned appearance; reads do not create rows or inspect private bio."""

import hashlib
import warnings
from io import BytesIO

from fastapi import HTTPException
from PIL import Image, UnidentifiedImageError
from sqlalchemy import func, select

from guardian.db.models import User, UserPresentation
from guardian.presentation_tokens import (
    ACCOUNT_PRESENTATION_SCOPE,
    MAX_PRESENTATION_WORKSPACES,
    MAX_WALLPAPER_BYTES,
    MAX_WALLPAPER_PIXELS,
    PRESENTATION_DEFAULTS,
    WALLPAPER_FORMATS,
)

SAFE_HEADERS = {"Cache-Control": "no-store", "Referrer-Policy": "no-referrer"}


def deny(status, detail):
    raise HTTPException(status_code=status, detail=detail, headers=SAFE_HEADERS)


def rows(session, owner, workspace):
    return (
        session.get(UserPresentation, (owner, ACCOUNT_PRESENTATION_SCOPE)),
        session.get(UserPresentation, (owner, str(workspace))),
    )


def effective(account, workspace):
    return workspace if workspace is not None and workspace.is_unique else account


def payload(session, owner, workspace):
    account, local = rows(session, owner, workspace)
    row = effective(account, local)
    stored = row.settings if row else {}
    settings = {
        key: stored.get(key, default) for key, default in PRESENTATION_DEFAULTS.items()
    }
    version = (
        hashlib.sha256(row.wallpaper_data).hexdigest()
        if row is not None and row.wallpaper_data is not None
        else None
    )
    return {
        "workspace_id": str(workspace),
        "workspace_unique": bool(local is not None and local.is_unique),
        "settings": settings,
        "wallpaper_url": (
            "/api/auth/scout/profile/presentation/wallpaper"
            f"?workspace_id={workspace}&v={version}"
            if version
            else None
        ),
    }


def lock_owner(session, owner):
    if (
        session.scalar(select(User.id).where(User.id == owner).with_for_update())
        is None
    ):
        deny(404, "Account unavailable")


def writable(session, owner, workspace):
    account, local = rows(session, owner, workspace)
    row = effective(account, local)
    if row is None:
        row = UserPresentation(
            user_id=owner,
            workspace_id=ACCOUNT_PRESENTATION_SCOPE,
            settings={},
            is_unique=False,
        )
        session.add(row)
    return row


def save(
    session, owner, workspace, *, settings=None, unique=None, clear_wallpaper=False
):
    if settings is not None and not set(settings) <= PRESENTATION_DEFAULTS.keys():
        deny(400, "Invalid appearance field")
    lock_owner(session, owner)
    account, local = rows(session, owner, workspace)
    if unique is not None:
        if local is None and unique:
            count = session.scalar(
                select(func.count())
                .select_from(UserPresentation)
                .where(
                    UserPresentation.user_id == owner,
                    UserPresentation.workspace_id != ACCOUNT_PRESENTATION_SCOPE,
                )
            )
            if count >= MAX_PRESENTATION_WORKSPACES:
                deny(409, "Workspace appearance limit reached")
            local = UserPresentation(
                user_id=owner,
                workspace_id=str(workspace),
                is_unique=True,
                settings=dict(account.settings) if account else {},
                wallpaper_data=account.wallpaper_data if account else None,
                wallpaper_mime=account.wallpaper_mime if account else None,
            )
            session.add(local)
        elif local is not None:
            # Rejoining the account never promotes a workspace's choices.
            # Its last unique appearance remains available when selected again.
            local.is_unique = unique
    else:
        row = writable(session, owner, workspace)
        if settings is not None:
            row.settings = {**row.settings, **settings}
        if clear_wallpaper:
            row.wallpaper_data = row.wallpaper_mime = None
    session.flush()
    return payload(session, owner, workspace)


def validate_wallpaper(data):
    if not data or len(data) > MAX_WALLPAPER_BYTES:
        deny(413, "Wallpaper must be at most 5 MB")
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(BytesIO(data)) as image:
                mime = WALLPAPER_FORMATS.get(image.format)
                if (
                    not mime
                    or image.width * image.height > MAX_WALLPAPER_PIXELS
                    or getattr(image, "n_frames", 1) != 1
                ):
                    deny(
                        400,
                        "Choose a still PNG, JPEG or WebP image up to 16 megapixels",
                    )
                image.verify()
    except (
        UnidentifiedImageError,
        OSError,
        ValueError,
        Image.DecompressionBombError,
        Image.DecompressionBombWarning,
    ):
        deny(400, "Invalid wallpaper image")
    return mime


def upload(session, owner, workspace, data):
    mime = validate_wallpaper(data)
    lock_owner(session, owner)
    row = writable(session, owner, workspace)
    row.wallpaper_data, row.wallpaper_mime = data, mime
    session.flush()
    return payload(session, owner, workspace)


def wallpaper(session, owner, workspace):
    row = effective(*rows(session, owner, workspace))
    if row is None or row.wallpaper_data is None:
        deny(404, "Wallpaper unavailable")
    return row.wallpaper_data, row.wallpaper_mime
