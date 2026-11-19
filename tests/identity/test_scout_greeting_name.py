"""Explicit account greeting choices never inherit account identifiers."""

from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from guardian.db.models import User, UserProfile
from guardian.routes import scout_auth
from tests.identity import test_scout_profile as profile_tests
from tests.identity.test_scout_profile import FIRST, PATH, ROWS, SECOND

profile = profile_tests.profile


@pytest.fixture
def writer(profile, monkeypatch):
    engine = create_engine(
        "sqlite+pysqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    User.__table__.create(engine)
    UserProfile.__table__.create(engine)
    factory = sessionmaker(engine, autoflush=False)
    with factory.begin() as session:
        for owner in (FIRST, SECOND, "missing@example.invalid"):
            session.add(
                User(
                    id=owner,
                    username=owner,
                    password_hash="synthetic-fixture",
                    role="guest",
                )
            )
        session.add_all(
            [
                UserProfile(
                    user_id=FIRST,
                    display_name=ROWS[FIRST],
                    username="identifier",
                    username_state="active",
                    avatar_url="https://example.invalid/avatar",
                    timezone="UTC",
                    accent_color="blue",
                ),
                UserProfile(
                    user_id=SECOND,
                    display_name=ROWS[SECOND],
                    greeting_name="Other Greeting",
                ),
            ]
        )
    opened = Mock(side_effect=factory)
    monkeypatch.setattr(
        scout_auth,
        "load_guardian_db_from_env",
        lambda: SimpleNamespace(get_session=opened),
    )
    yield SimpleNamespace(
        **vars(profile), engine=engine, factory=factory, opened=opened
    )
    engine.dispose()


def test_save_explicit_name_preserves_identifiers_and_other_account(writer):
    with writer.factory() as session:
        before = session.scalar(select(UserProfile).where(UserProfile.user_id == FIRST))
        unchanged = {
            column.name: getattr(before, column.name)
            for column in UserProfile.__table__.columns
            if column.name not in {"greeting_name", "updated_at"}
        }
    response = writer.client.patch(
        PATH + "?user_id=" + SECOND,
        headers={**writer.headers(), "X-User-Id": SECOND},
        json={"greeting_name": "  Resonant  "},
    )
    assert response.status_code == 200
    assert response.json() == {"greeting_name": "Resonant"}
    assert response.headers["Cache-Control"] == "no-store"
    assert response.headers["Referrer-Policy"] == "no-referrer"
    with writer.factory() as session:
        saved = session.scalar(select(UserProfile).where(UserProfile.user_id == FIRST))
        assert saved.greeting_name == "Resonant"
        assert {name: getattr(saved, name) for name in unchanged} == unchanged
        assert (
            session.scalar(
                select(UserProfile.greeting_name).where(UserProfile.user_id == SECOND)
            )
            == "Other Greeting"
        )


@pytest.mark.parametrize("value", [None, "", " \t\n "])
def test_explicit_clear_returns_neutral_even_with_display_and_username(writer, value):
    headers = writer.headers()
    assert (
        writer.client.patch(
            PATH, headers=headers, json={"greeting_name": "Chosen"}
        ).status_code
        == 200
    )
    response = writer.client.patch(PATH, headers=headers, json={"greeting_name": value})
    assert response.status_code == 200
    assert response.json() == {"greeting_name": None}
    assert writer.client.get(PATH, headers=headers).json()["greeting_name"] is None


def test_unset_name_never_uses_display_username_or_email(writer):
    response = writer.client.get(PATH, headers=writer.headers())
    assert response.json() == {"greeting_name": None}


def test_only_explicit_save_creates_missing_profile(writer):
    owner = "missing@example.invalid"
    headers = writer.headers(owner)
    for _ in range(2):
        assert writer.client.get(PATH, headers=headers).json() == {
            "greeting_name": None
        }
    with writer.factory() as session:
        assert (
            session.scalar(select(UserProfile).where(UserProfile.user_id == owner))
            is None
        )
    response = writer.client.patch(
        PATH, headers=headers, json={"greeting_name": "Chosen"}
    )
    assert response.status_code == 200
    assert response.json() == {"greeting_name": "Chosen"}
    with writer.factory() as session:
        assert (
            len(
                session.scalars(
                    select(UserProfile).where(UserProfile.user_id == owner)
                ).all()
            )
            == 1
        )


@pytest.mark.parametrize("name", ["星", "Dr. Rivera", "a" * 255])
def test_explicit_name_is_preserved_without_inference_or_truncation(writer, name):
    response = writer.client.patch(
        PATH, headers=writer.headers(), json={"greeting_name": name}
    )
    assert response.status_code == 200
    assert response.json()["greeting_name"] == name


@pytest.mark.parametrize(
    "body",
    [
        {},
        {"display_name": "Private"},
        {"greeting_name": "Private", "user_id": SECOND},
        {"greeting_name": "Private", "preferred_name": "Other"},
        {"bio": "Private"},
        {"greeting_name": 12},
        {"greeting_name": True},
        {"greeting_name": "a" * 256},
        {"greeting_name": "Private\nName"},
        {"greeting_name": "Private\x00Name"},
    ],
)
def test_invalid_input_cannot_open_database_or_echo_content(writer, body):
    response = writer.client.patch(PATH, headers=writer.headers(), json=body)
    assert response.status_code == 400
    assert response.json() == {"detail": "Invalid profile request"}
    writer.opened.assert_not_called()


@pytest.mark.parametrize(
    "case,status",
    [
        ("missing", 401),
        ("revoked", 401),
        ("mismatch", 401),
        ("access", 400),
        ("mixed", 400),
        ("host", 400),
    ],
)
def test_save_retains_account_and_ingress_boundaries(writer, case, status):
    headers = writer.headers()
    token = headers["X-Guardian-Account-Session"]
    if case == "missing":
        headers.pop("X-Guardian-Account-Session")
    elif case == "revoked":
        writer.store.revoke(token)
    elif case == "mismatch":
        writer.store.store(token, SECOND, 300)
    elif case == "access":
        headers.pop("CF-Access-Jwt-Assertion")
    elif case == "mixed":
        headers["X-API-Key"] = "synthetic-conflicting-key"
    elif case == "host":
        headers["Host"] = "other.example.invalid"
    assert (
        writer.client.patch(
            PATH, headers=headers, json={"greeting_name": "Chosen"}
        ).status_code
        == status
    )
    writer.opened.assert_not_called()


@pytest.mark.parametrize(
    "origin,expected",
    [
        (None, 403),
        ("https://other.example.invalid", 403),
        ("https://preview.codexify.space", 200),
    ],
)
def test_browser_cookie_save_uses_existing_same_origin_boundary(
    writer, origin, expected
):
    native = writer.headers()
    headers = {
        "CF-Access-Jwt-Assertion": native["CF-Access-Jwt-Assertion"],
        "Cookie": "gc_session=" + native["X-Guardian-Account-Session"],
    }
    if origin:
        headers["Origin"] = origin
    response = writer.client.patch(
        PATH, headers=headers, json={"greeting_name": "Chosen"}
    )
    assert response.status_code == expected
    if expected != 200:
        writer.opened.assert_not_called()


def test_save_requires_persisted_canonical_user(writer):
    response = writer.client.patch(
        PATH,
        headers=writer.headers("null@example.invalid"),
        json={"greeting_name": "Chosen"},
    )
    assert response.status_code == 404


def test_no_new_schema_is_an_explicit_unavailable_result(profile):
    from sqlalchemy import event

    # This is fixture schema setup, not a GET.
    event.remove(profile.db.engine, "before_cursor_execute", profile.db.observe_sql)
    with profile.db.engine.connect() as connection:
        connection.exec_driver_sql("PRAGMA query_only = OFF")
    with profile.db.engine.begin() as connection:
        connection.exec_driver_sql(
            "ALTER TABLE user_profiles DROP COLUMN greeting_name"
        )
        connection.exec_driver_sql("PRAGMA query_only = ON")
    response = profile.client.get(PATH, headers=profile.headers())
    assert response.status_code == 503
    assert response.json() == {"detail": "Profile unavailable"}
