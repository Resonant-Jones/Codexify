"""Read-only display-name projection over the existing account boundary."""

from types import SimpleNamespace

import fakeredis
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from guardian.core import auth, dependencies, scout_account_transport, session_store
from guardian.routes import scout_auth

PATH = "/api/auth/scout/profile"
FIRST = "first@example.invalid"
SECOND = "second@example.invalid"
ROWS = {
    FIRST: "  Chosen Name  ",
    SECOND: "Other Name",
    "null@example.invalid": None,
    "empty@example.invalid": "",
    "blank@example.invalid": " \t\n ",
    "account-one": "Canonical One",
    "account-two": "Canonical Two",
}
GREETINGS = {
    FIRST: "  Resonant  ",
    SECOND: "Other Greeting",
    "account-one": "Canonical Greeting One",
    "account-two": "Canonical Greeting Two",
}


class ReadOnlySession(Session):
    def forbidden_write(self, *args, **kwargs):
        pytest.fail("Profile reads must not write, flush, or commit")

    add = add_all = delete = merge = flush = commit = forbidden_write


class ProfileDb:
    """Only projection columns exist; SQLite also forbids SQL writes."""

    def __init__(self):
        self.engine = create_engine(
            "sqlite+pysqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        with self.engine.begin() as connection:
            connection.exec_driver_sql(
                "CREATE TABLE user_profiles (user_id TEXT PRIMARY KEY, display_name TEXT, greeting_name TEXT)"
            )
            connection.execute(
                text("INSERT INTO user_profiles VALUES (:owner, :name, :greeting)"),
                [
                    {"owner": owner, "name": name, "greeting": GREETINGS.get(owner)}
                    for owner, name in ROWS.items()
                ],
            )
        with self.engine.connect() as connection:
            connection.exec_driver_sql("PRAGMA query_only = ON")
        self.statements = []
        self.sessions = []
        self.factory = sessionmaker(
            self.engine, class_=ReadOnlySession, autoflush=False
        )
        event.listen(self.engine, "before_cursor_execute", self.observe_sql)

    def observe_sql(self, connection, cursor, statement, parameters, context, many):
        assert statement.lstrip().upper().startswith("SELECT ")
        self.statements.append((statement, parameters))

    def get_session(self):
        session = self.factory()
        self.sessions.append(session)
        return session


@pytest.fixture
def profile(monkeypatch):
    monkeypatch.setenv("GUARDIAN_EXPOSURE_MODE", "private_preview")
    monkeypatch.setenv("GUARDIAN_AUTH_MODE", "remote")
    monkeypatch.setenv("CODEXIFY_MULTI_USER_ENABLED", "true")
    monkeypatch.setenv("GUARDIAN_SESSION_SECRET", "synthetic-profile-session-fixture")
    approved = [FIRST, SECOND, "missing@example.invalid", *ROWS]
    monkeypatch.setenv("CODEXIFY_PREVIEW_APPROVED_EMAILS", ",".join(approved))
    monkeypatch.delenv("CODEXIFY_PREVIEW_ADMIN_EMAILS", raising=False)
    monkeypatch.setattr(
        scout_account_transport, "verify_access_assertion", lambda _: None
    )
    monkeypatch.setattr(scout_auth, "verify_access_assertion", lambda _: None)
    store = session_store.SessionStore(fakeredis.FakeRedis())
    monkeypatch.setattr(session_store, "_SESSION_STORE", store)
    db = ProfileDb()
    monkeypatch.setattr(scout_auth, "load_guardian_db_from_env", lambda: db)
    app = FastAPI()
    app.include_router(scout_auth.router)
    app.add_middleware(scout_account_transport.ScoutAccountTransportMiddleware)
    client = TestClient(app, base_url="https://preview.codexify.space")
    client.headers.pop("X-API-Key", None)

    def headers(subject=FIRST, *, purpose=auth.ACCOUNT_SESSION_PURPOSE):
        token, _ = auth.issue_session_token(subject=subject, purpose=purpose)
        store.store(token, subject, 300)
        return {
            "X-Guardian-Account-Session": token,
            "CF-Access-Jwt-Assertion": "synthetic-access-assertion",
        }

    yield SimpleNamespace(client=client, app=app, db=db, store=store, headers=headers)
    client.close()
    db.engine.dispose()


@pytest.mark.parametrize("forwarded", [False, True])
def test_current_account_isolation_and_ignored_client_owner_inputs(profile, forwarded):
    for subject, expected in [(FIRST, "Resonant"), (SECOND, "Other Greeting")]:
        headers = profile.headers(subject)
        headers.update({"X-User-Id": SECOND, "X-Account-Id": SECOND})
        if forwarded:
            headers["Authorization"] = "Bearer oauth:synthetic-ingress"
        response = profile.client.request(
            "GET",
            PATH + "?user_id=" + SECOND + "&account_id=" + SECOND,
            headers=headers,
            json={"user_id": SECOND, "account_id": SECOND, "display_name": "Injected"},
        )
        assert response.status_code == 200
        assert response.json() == {"greeting_name": expected}
        assert response.headers["Cache-Control"] == "no-store"
        assert response.headers["Referrer-Policy"] == "no-referrer"
        assert profile.db.statements[-1][1] == (subject,)
        assert not profile.db.sessions[-1].identity_map
    assert len(profile.db.statements) == 2


@pytest.mark.parametrize(
    "subject",
    [
        "missing@example.invalid",
        "null@example.invalid",
        "empty@example.invalid",
        "blank@example.invalid",
    ],
)
def test_missing_and_blank_profile_returns_null_without_creating_rows(profile, subject):
    headers = profile.headers(subject)
    for _ in range(2):
        response = profile.client.get(PATH, headers=headers)
        assert response.status_code == 200
        assert response.json() == {"greeting_name": None}
    assert len(profile.db.statements) == 2
    # No username/social columns exist, and query_only rejects any lazy INSERT.
    with profile.db.engine.connect() as connection:
        assert (
            dict(
                connection.execute(
                    text("SELECT user_id, display_name FROM user_profiles")
                ).all()
            )
            == ROWS
        )


def test_projection_uses_canonical_scope_account_when_distinct_from_subject(profile):
    # Preview currently resolves its canonical account to the stored subject.
    # At this trusted seam, prove the projection also respects distinct IDs;
    # signed-purpose and stored-subject validation remain real.
    for subject, account, expected in [
        (FIRST, "account-one", "Canonical Greeting One"),
        (SECOND, "account-two", "Canonical Greeting Two"),
    ]:
        scope = dependencies.RequestUserScope(
            user_id="legacy-user",
            subject_id=subject,
            account_id=account,
            multi_user_enabled=True,
        )
        profile.app.dependency_overrides[dependencies.get_account_user_scope] = (
            lambda: scope
        )
        response = profile.client.get(
            PATH + "?account_id=account-two",
            headers={**profile.headers(subject), "X-User-Id": SECOND},
        )
        assert response.status_code == 200, response.text
        assert response.json() == {"greeting_name": expected}
        assert profile.db.statements[-1][1] == (account,)


@pytest.mark.parametrize("stored_subject", [None, SECOND])
def test_route_rechecks_stored_session_even_with_resolved_scope(
    profile, stored_subject
):
    headers = profile.headers()
    token = headers.pop("X-Guardian-Account-Session")
    if stored_subject is None:
        profile.store.revoke(token)
    else:
        profile.store.store(token, stored_subject, 300)
    profile.app.dependency_overrides[dependencies.get_account_user_scope] = (
        lambda: dependencies.RequestUserScope(
            account_id="account-one", subject_id=FIRST
        )
    )
    headers["Authorization"] = "Bearer " + token
    assert profile.client.get(PATH, headers=headers).status_code == 401
    assert not profile.db.sessions


@pytest.mark.parametrize(
    "failure",
    ["missing", "invalid", "revoked", "session-mismatch", "operator", "guest"],
)
def test_invalid_account_never_opens_profile_database(profile, failure):
    headers = profile.headers(
        purpose=(
            auth.OPERATOR_SESSION_PURPOSE
            if failure == "operator"
            else auth.ACCOUNT_SESSION_PURPOSE
        )
    )
    token = headers["X-Guardian-Account-Session"]
    if failure == "missing":
        headers.pop("X-Guardian-Account-Session")
    elif failure == "invalid":
        headers["X-Guardian-Account-Session"] = "synthetic-invalid-session"
    elif failure == "revoked":
        profile.store.revoke(token)
    elif failure == "session-mismatch":
        profile.store.store(token, SECOND, 300)
    elif failure == "guest":
        headers = profile.headers(
            subject="hosted_room_guest_session", purpose="hosted_room_guest_session"
        )
    response = profile.client.get(PATH, headers=headers)
    assert response.status_code == 401
    assert not profile.db.sessions


@pytest.mark.parametrize(
    "scope",
    [
        dependencies.RequestUserScope(account_id="account-two", subject_id=SECOND),
        dependencies.RequestUserScope(account_id=None, subject_id=FIRST),
        dependencies.RequestUserScope(account_id="account-one", subject_id=None),
    ],
)
def test_scope_must_match_signed_stored_subject(profile, scope):
    profile.app.dependency_overrides[dependencies.get_account_user_scope] = (
        lambda: scope
    )
    response = profile.client.get(PATH, headers=profile.headers())
    assert response.status_code == 401
    assert not profile.db.sessions


@pytest.mark.parametrize(
    "failure",
    [
        "missing-access",
        "invalid-access",
        "wrong-host",
        "local-mode",
        "mixed-key",
        "mixed-cookie",
        "duplicate-access",
        "duplicate-account",
    ],
)
def test_hosted_profile_requires_qualified_ingress(profile, monkeypatch, failure):
    headers = profile.headers()
    if failure == "missing-access":
        headers.pop("CF-Access-Jwt-Assertion")
    elif failure == "invalid-access":

        def reject(_):
            raise ValueError("synthetic-invalid-assertion")

        monkeypatch.setattr(scout_account_transport, "verify_access_assertion", reject)
    elif failure == "wrong-host":
        headers["Host"] = "other.example.invalid"
    elif failure == "local-mode":
        monkeypatch.setenv("GUARDIAN_EXPOSURE_MODE", "local_safe")
    elif failure == "mixed-key":
        headers["X-API-Key"] = "synthetic-operator-key"
    elif failure == "mixed-cookie":
        headers["Cookie"] = "gc_session=synthetic-conflicting-cookie"
    elif failure.startswith("duplicate"):
        key = (
            "CF-Access-Jwt-Assertion"
            if failure == "duplicate-access"
            else "X-Guardian-Account-Session"
        )
        headers = [*headers.items(), (key, headers[key])]
    assert profile.client.get(PATH, headers=headers).status_code == 400
    assert not profile.db.sessions


@pytest.mark.parametrize("method", ["HEAD", "POST", "PUT", "DELETE", "OPTIONS"])
def test_profile_transport_rejects_other_methods(profile, method):
    assert not scout_account_transport.account_route(PATH, method)
    assert (
        profile.client.request(method, PATH, headers=profile.headers()).status_code
        == 400
    )
    assert not profile.db.sessions


@pytest.mark.parametrize(
    "path", [PATH + "/", PATH + "/other", PATH + "-extra", "/api/user/profile"]
)
def test_profile_transport_does_not_admit_related_paths(profile, path):
    assert not scout_account_transport.account_route(path, "GET")
    assert profile.client.get(path, headers=profile.headers()).status_code == 400
    assert not profile.db.sessions


def test_profile_database_unavailable_is_bounded(profile, monkeypatch):
    monkeypatch.setattr(scout_auth, "load_guardian_db_from_env", lambda: None)
    response = profile.client.get(PATH, headers=profile.headers())
    assert response.status_code == 503
    assert response.json() == {"detail": "Profile unavailable"}
    assert response.headers["Cache-Control"] == "no-store"
    assert response.headers["Referrer-Policy"] == "no-referrer"
