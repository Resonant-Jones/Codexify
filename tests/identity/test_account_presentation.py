"""Account/workspace appearance ownership, explicit writes and bounded images."""

from io import BytesIO
from uuid import uuid4

import pytest
from PIL import Image
from sqlalchemy import func, select

from guardian.db.models import UserPresentation
from guardian.presentation_tokens import MAX_WALLPAPER_BYTES, PRESENTATION_DEFAULTS
from tests.identity import test_scout_greeting_name as greeting
from tests.identity import test_scout_profile as profile_tests
from tests.identity.test_scout_profile import FIRST, SECOND

profile = profile_tests.profile
writer = greeting.writer
PATH = "/api/auth/scout/profile/presentation"
A, B = str(uuid4()), str(uuid4())


@pytest.fixture
def appearance(writer):
    UserPresentation.__table__.create(writer.engine)
    return writer


def read(app, workspace=A, owner=FIRST, query=""):
    return app.client.get(
        PATH + "?workspace_id=" + workspace + query, headers=app.headers(owner)
    )


def save(app, body, workspace=A, owner=FIRST):
    return app.client.patch(
        PATH, json={"workspace_id": workspace, **body}, headers=app.headers(owner)
    )


def image(color="red"):
    out = BytesIO()
    Image.new("RGB", (2, 2), color).save(out, format="PNG")
    return out.getvalue()


def upload(app, data, workspace=A, owner=FIRST):
    return app.client.put(
        PATH + "/wallpaper?workspace_id=" + workspace,
        content=data,
        headers=app.headers(owner),
    )


def test_get_defaults_does_not_create_or_write(appearance):
    for _ in range(2):
        r = read(appearance)
        assert r.status_code == 200
        assert r.json()["settings"] == PRESENTATION_DEFAULTS
        assert r.json()["wallpaper_url"] is None
        assert r.json()["workspace_unique"] is False
        assert r.headers["Cache-Control"] == "no-store"
    with appearance.factory() as session:
        assert session.scalar(select(func.count()).select_from(UserPresentation)) == 0


def test_account_preferences_follow_workspaces_and_owner_inputs_are_ignored(appearance):
    assert (
        save(
            appearance, {"settings": {"theme_mode": "dark", "surface_depth": 70}}
        ).status_code
        == 200
    )
    r = read(appearance, B, query="&user_id=foreign-fixture&account_id=foreign-fixture")
    assert r.json()["settings"]["theme_mode"] == "dark"
    assert r.json()["settings"]["surface_depth"] == 70
    assert read(appearance, owner=SECOND).json()["settings"] == PRESENTATION_DEFAULTS
    assert save(appearance, {"settings": {"base_color": "#123456"}}).status_code == 200
    assert read(appearance).json()["settings"]["theme_mode"] == "dark"


def test_unique_workspace_is_explicit_and_never_promoted_to_account(appearance):
    save(appearance, {"settings": {"theme_mode": "dark"}})
    assert (
        save(appearance, {"workspace_unique": True}).json()["workspace_unique"] is True
    )
    assert (
        save(appearance, {"settings": {"theme_mode": "light"}}).json()["settings"][
            "theme_mode"
        ]
        == "light"
    )
    assert read(appearance, B).json()["settings"]["theme_mode"] == "dark"
    assert read(appearance, owner=SECOND).json()["workspace_unique"] is False
    assert (
        save(appearance, {"workspace_unique": False}).json()["settings"]["theme_mode"]
        == "dark"
    )
    assert (
        save(appearance, {"workspace_unique": True}).json()["settings"]["theme_mode"]
        == "light"
    )


@pytest.mark.parametrize(
    "body",
    [
        {},
        {"settings": {}},
        {"settings": {"theme_mode": "unknown"}},
        {"settings": {"theme_mode": None}},
        {"settings": {"surface_depth": True}},
        {"settings": {"background_depth": "0.5"}},
        {"settings": {"background_fade": 2}},
        {"settings": {"base_color": "url(javascript:example)"}},
        {"settings": {"provider_key": "never-echo-this"}},
        {"settings": {"bio": "never-echo-this"}},
        {"settings": {"greeting_name": "never-echo-this"}},
        {"workspace_unique": "true"},
        {"clear_wallpaper": False},
        {"clear_wallpaper": 1},
        {"workspace_unique": True, "settings": {"theme_mode": "dark"}},
        {"user_id": SECOND, "settings": {"theme_mode": "dark"}},
    ],
)
def test_strict_allowlist_rejects_invalid_or_sensitive_fields(appearance, body):
    r = save(appearance, body)
    assert r.status_code == 400
    assert "never-echo-this" not in r.text
    with appearance.factory() as session:
        assert session.scalar(select(func.count()).select_from(UserPresentation)) == 0


def test_wallpaper_uses_account_ownership_and_remains_private(appearance):
    data = image()
    r = upload(appearance, data)
    assert r.status_code == 200
    url = r.json()["wallpaper_url"]
    assert url.startswith(PATH + "/wallpaper?workspace_id=")
    for workspace in (A, B):
        got = appearance.client.get(
            PATH + "/wallpaper?workspace_id=" + workspace, headers=appearance.headers()
        )
        assert got.status_code == 200 and got.content == data
        assert got.headers["content-type"] == "image/png"
        assert got.headers["cache-control"] == "no-store"
        assert got.headers["x-content-type-options"] == "nosniff"
    assert (
        appearance.client.get(url, headers=appearance.headers(SECOND)).status_code
        == 404
    )
    assert appearance.client.get(url).status_code == 401
    assert save(appearance, {"clear_wallpaper": True}).json()["wallpaper_url"] is None


def test_workspace_wallpaper_snapshot_is_independent(appearance):
    first, second = image(), image("blue")
    upload(appearance, first)
    save(appearance, {"workspace_unique": True})
    upload(appearance, second, B)
    assert (
        appearance.client.get(
            PATH + "/wallpaper?workspace_id=" + A, headers=appearance.headers()
        ).content
        == first
    )
    assert (
        appearance.client.get(
            PATH + "/wallpaper?workspace_id=" + B, headers=appearance.headers()
        ).content
        == second
    )


@pytest.mark.parametrize(
    "data,status",
    [(b"<svg></svg>", 400), (b"", 413), (b"x" * (MAX_WALLPAPER_BYTES + 1), 413)],
)
def test_invalid_or_oversize_images_do_not_create_rows(appearance, data, status):
    assert upload(appearance, data).status_code == status
    with appearance.factory() as session:
        assert session.scalar(select(func.count()).select_from(UserPresentation)) == 0


def test_unrecognized_stored_keys_are_not_projected(appearance):
    with appearance.factory.begin() as session:
        session.add(
            UserPresentation(
                user_id=FIRST,
                workspace_id="account",
                is_unique=False,
                settings={"bio": "never-echo-this", "theme_mode": "dark"},
            )
        )
    response = read(appearance)
    assert response.status_code == 200
    assert "never-echo-this" not in response.text
    assert set(response.json()["settings"]) == set(PRESENTATION_DEFAULTS)


@pytest.mark.parametrize(
    "failure", ["missing", "revoked", "session-mismatch", "operator", "ingress"]
)
@pytest.mark.parametrize("method", ["GET", "PATCH", "PUT"])
def test_auth_failures_never_open_database(appearance, monkeypatch, failure, method):
    from guardian.core import auth
    from guardian.core import scout_account_transport
    from guardian.routes import scout_auth
    from fastapi import HTTPException

    headers = appearance.headers(
        purpose=(
            auth.OPERATOR_SESSION_PURPOSE
            if failure == "operator"
            else auth.ACCOUNT_SESSION_PURPOSE
        )
    )
    token = headers["X-Guardian-Account-Session"]
    if failure == "missing":
        headers.pop("X-Guardian-Account-Session")
    elif failure == "revoked":
        appearance.store.revoke(token)
    elif failure == "session-mismatch":
        appearance.store.store(token, SECOND, 300)
    elif failure == "ingress":

        def reject(_):
            raise HTTPException(status_code=403)

        monkeypatch.setattr(scout_auth, "verify_access_assertion", reject)
        monkeypatch.setattr(scout_account_transport, "verify_access_assertion", reject)
    appearance.opened.reset_mock()
    response = appearance.client.request(
        method,
        PATH + ("/wallpaper" if method == "PUT" else "") + "?workspace_id=" + A,
        headers=headers,
        **(
            {"json": {"workspace_id": A, "settings": {"theme_mode": "dark"}}}
            if method == "PATCH"
            else {}
        ),
    )
    assert response.status_code in (400, 401, 403)
    appearance.opened.assert_not_called()


def test_uses_canonical_account_distinct_from_session_subject(appearance):
    from guardian.core import dependencies
    from guardian.db.models import User

    with appearance.factory.begin() as session:
        session.add(
            User(
                id="canonical-owner",
                username="canonical",
                password_hash="fixture",
                role="guest",
            )
        )
    scope = dependencies.RequestUserScope(
        user_id="legacy",
        subject_id=FIRST,
        account_id="canonical-owner",
        multi_user_enabled=True,
    )
    appearance.app.dependency_overrides[dependencies.get_account_user_scope] = (
        lambda: scope
    )
    assert save(appearance, {"settings": {"theme_mode": "dark"}}).status_code == 200
    with appearance.factory() as session:
        assert session.get(UserPresentation, ("canonical-owner", "account")) is not None
        assert session.get(UserPresentation, (FIRST, "account")) is None


def test_workspace_limit_and_repeated_toggles_are_bounded(appearance):
    from guardian.presentation_tokens import MAX_PRESENTATION_WORKSPACES

    for _ in range(MAX_PRESENTATION_WORKSPACES):
        assert (
            save(appearance, {"workspace_unique": True}, str(uuid4())).status_code
            == 200
        )
    assert save(appearance, {"workspace_unique": True}).status_code == 409
    with appearance.factory() as session:
        assert (
            session.scalar(select(func.count()).select_from(UserPresentation))
            == MAX_PRESENTATION_WORKSPACES
        )


def test_exact_native_route_admission():
    from guardian.core.scout_account_transport import account_route

    for path, allowed in (
        (PATH, {"GET", "PATCH"}),
        (PATH + "/wallpaper", {"GET", "PUT"}),
    ):
        for method in ("GET", "PATCH", "PUT", "POST", "DELETE", "HEAD", "OPTIONS"):
            assert account_route(path, method) is (method in allowed)
        assert not account_route(path + "/foreign", "GET")
