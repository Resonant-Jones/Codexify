"""Tests for the Music Project routes and the Agent-DAW service seam.

These are written to discriminate. The route's whole job is to be
*callable by the model*, and Codexify derives that callability from the
OpenAPI schema rather than from a tool registry -- so a route that
silently loses its request body still appears in the schema looking
plausible, and every call 422s. Asserting on the schema catches that
class of bug directly.

The other thing worth catching is a drift between the three places the
same contract is written down: the route's forwarding, the plugin
manifest, and the service that answers. If they disagree, the host
advertises a capability and then refuses it.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient


# --------------------------------------------------------------------------
# The OpenAPI contract -- this is what the model actually reads
# --------------------------------------------------------------------------


@pytest.fixture(scope="module")
def music_schema():
    from guardian.routes.music_projects import router

    app = FastAPI()
    app.include_router(router)
    return app.openapi()


def test_every_post_route_has_a_request_body(music_schema):
    """A route whose body was demoted to query parameters 422s on every call.

    That is not hypothetical: it is what happens when a FastAPI request
    model is defined inside a function under postponed annotation
    evaluation. The route still shows up in the schema, so only an
    assertion on the schema catches it.
    """
    components = music_schema.get("components", {}).get("schemas", {})

    def resolve(body):
        ref = body.get("$ref")
        if not ref:
            return body
        return components.get(ref.rsplit("/", 1)[-1], body)

    posts = 0
    for path, methods in music_schema["paths"].items():
        for method, operation in methods.items():
            if method != "post":
                continue
            posts += 1
            assert "requestBody" in operation, f"POST {path} has no request body"
            body = resolve(
                operation["requestBody"]["content"]["application/json"]["schema"]
            )
            assert body.get("type") == "object", f"POST {path} body is not an object"
            assert body.get("properties"), f"POST {path} body has no fields"

            for parameter in operation.get("parameters", []):
                assert parameter["in"] != "query", (
                    f"POST {path} exposes {parameter['name']} as a query "
                    "parameter; the request body was lost"
                )

    assert posts >= 5, "the producer's operations should all be exposed"


def test_the_schema_describes_the_artists_vocabulary(music_schema):
    """The schema is the model's only documentation, so the names matter."""
    compose = music_schema["paths"]["/api/music/compose"]["post"]
    components = music_schema.get("components", {}).get("schemas", {})
    body = compose["requestBody"]["content"]["application/json"]["schema"]
    name = body.get("$ref", "").rsplit("/", 1)[-1]
    properties = components.get(name, body).get("properties", {})

    assert "brief" in properties, "the request body is called 'brief'"
    assert "params" not in properties


def test_the_job_endpoint_is_exposed(music_schema):
    """Compose is a job; the model needs somewhere to poll it."""
    assert "/api/music/jobs/{job_id}" in music_schema["paths"]


# --------------------------------------------------------------------------
# The supported profile -- without this the routes are quarantined
# --------------------------------------------------------------------------


def test_the_route_label_is_in_a_supported_profile():
    """An unlisted label is quarantined, so the route would never mount.

    ``SupportedProfileManifest.route_status`` returns "quarantined" for
    any label it does not know. So the label has to be declared in a
    profile somewhere, or the Producer is silently uncallable.
    """
    from guardian.core.supported_profile import load_supported_profile

    profiles_dir = Path("config/supported_profiles")
    profiles = sorted(profiles_dir.glob("*.yaml"))
    assert profiles, f"no supported profiles found under {profiles_dir}"

    enabling = []
    for profile in profiles:
        manifest = load_supported_profile(profile.stem)
        if manifest.route_status("music_projects") == "enabled":
            enabling.append(profile.stem)

    assert enabling, (
        "no supported profile enables music_projects, so the Producer's "
        "routes would be quarantined and the model could not call them"
    )


def test_the_default_profile_is_not_modified():
    """The default profile is a release promise, and it is byte-frozen.

    A new capability gets its own profile rather than a change to the
    default one. If this test fails, the right answer is a new profile
    file -- not an edit to the default.
    """
    import subprocess

    default = Path("config/supported_profiles/v1-local-core-web-mcp.yaml")
    expected = subprocess.check_output(
        ["git", "show", f"HEAD:{default.as_posix()}"],
    )
    assert default.read_bytes() == expected


def test_other_profiles_leave_the_music_routes_quarantined():
    """Absent where it was not asked for, rather than broken.

    Same invariant the Hosted Room route families hold: only the
    profiles that are meant to expose them enable them.
    """
    from guardian.core.supported_profile import load_supported_profile

    music_profiles = {"v1-music-producer"}
    profiles_dir = Path("config/supported_profiles")

    for profile_path in sorted(profiles_dir.glob("*.yaml")):
        manifest = load_supported_profile(profile_path.stem)
        if manifest.name in music_profiles:
            assert manifest.route_status("music_projects") == "enabled"
            continue
        assert manifest.route_status("music_projects") == "quarantined", (
            f"{manifest.name} enables music_projects; only the music profile "
            "may"
        )


# --------------------------------------------------------------------------
# The forwarding -- the canonical service-plugin envelope
# --------------------------------------------------------------------------


class _FakeResponse:
    def __init__(self, payload, status_code=200):
        self._payload = payload
        self.status_code = status_code
        self.text = json.dumps(payload)

    def json(self):
        return self._payload


@pytest.fixture
def database_url():
    """A disposable PostgreSQL, migrated to head.

    The registration path only misbehaves against a real database, so the
    proofs that guard it need one.
    """
    yield from _disposable_database()


@pytest.fixture
def music_client():
    """A client for the music router on its own.

    The shared ``test_client`` fixture builds the whole guardian app, and
    that app mounts its routers at import time from whichever supported
    profile is active. A route test riding on it therefore inherits
    whatever profile the module before it left behind -- and since
    ``music_projects`` is quarantined outside the music profile, the route
    can be absent from an app that is supposed to have it. Mounting the
    router here keeps these tests about the route itself, and makes them
    independent of test order.
    """
    from guardian.routes.music_projects import router

    app = FastAPI()
    app.include_router(router)
    with TestClient(app) as client:
        yield client


@pytest.fixture
def captured_calls(monkeypatch):
    """Capture what the route sends to the service."""
    from guardian.routes import music_projects

    calls = []

    def _post(url, json=None, timeout=None, **_kwargs):
        calls.append({"url": url, "envelope": json, "timeout": timeout})
        return _FakeResponse({"ok": True, "output": {"ok": True}, "error": None})

    monkeypatch.setattr(music_projects.requests, "post", _post)
    return calls


def test_compose_sends_the_canonical_envelope(captured_calls, music_client):
    from guardian.routes import music_projects

    response = music_client.post("/api/music/compose", json={"brief": "a warm pad", "project_id": 1})

    assert response.status_code == 200, response.text
    assert len(captured_calls) == 1

    envelope = captured_calls[0]["envelope"]
    assert envelope["protocol_version"] == "1.0"
    assert envelope["plugin_id"] == "agentdaw"
    assert envelope["capability"] == "music"
    assert envelope["action"] == "compose"
    assert envelope["input"]["brief"] == "a warm pad"


def test_compose_is_asynchronous_by_default(captured_calls, music_client):
    """A compose takes about 107 seconds; blocking on it hangs the turn."""
    from guardian.routes import music_projects

    music_client.post("/api/music/compose", json={"brief": "a warm pad", "project_id": 1})

    envelope = captured_calls[0]["envelope"]
    assert envelope["input"]["mode"] == "async"


def test_compose_can_be_forced_synchronous(captured_calls, music_client):
    from guardian.routes import music_projects

    music_client.post(
        "/api/music/compose", json={"brief": "a warm pad", "sync": True, "project_id": 1}
    )

    envelope = captured_calls[0]["envelope"]
    assert envelope["input"]["mode"] == "sync"
    assert captured_calls[0]["timeout"] and captured_calls[0]["timeout"] > 60


def test_an_unreachable_service_is_a_503_not_a_500(monkeypatch, music_client):
    """The service being down is an availability problem, not a bug."""
    import requests

    from guardian.routes import music_projects

    def _boom(*_args, **_kwargs):
        raise requests.ConnectionError("connection refused")

    monkeypatch.setattr(music_projects.requests, "post", _boom)

    response = music_client.post("/api/music/compose", json={"brief": "a warm pad", "project_id": 1})

    assert response.status_code == 503
    assert "unreachable" in response.json()["detail"].lower()


def test_a_malformed_service_response_is_rejected(monkeypatch, music_client):
    """A response without a boolean 'ok' is a broken service."""
    from guardian.routes import music_projects

    monkeypatch.setattr(
        music_projects.requests,
        "post",
        lambda *_a, **_k: _FakeResponse({"output": {"ok": True}}),
    )

    response = music_client.post("/api/music/compose", json={"brief": "a warm pad", "project_id": 1})

    assert response.status_code == 502


def test_a_service_error_is_surfaced(monkeypatch, music_client):
    from guardian.routes import music_projects

    monkeypatch.setattr(
        music_projects.requests,
        "post",
        lambda *_a, **_k: _FakeResponse(
            {
                "ok": False,
                "output": None,
                "error": {"code": "not_found", "message": "no such patch", "retryable": False},
            }
        ),
    )

    response = music_client.post("/api/music/compose", json={"brief": "a warm pad", "project_id": 1})

    assert response.status_code == 502
    assert "no such patch" in response.json()["detail"]


# --------------------------------------------------------------------------
# The work belongs to a project
# --------------------------------------------------------------------------


def test_the_envelope_carries_the_project_and_thread(captured_calls, music_client):
    """The service cannot know what it produced belongs to.

    It is told, in the envelope, and it carries the answer back on the
    job so the host can attribute the files to the project and thread
    that asked for them.
    """
    music_client.post(
        "/api/music/compose",
        json={"brief": "a warm pad", "project_id": 17, "thread_id": 42},
    )

    context = captured_calls[0]["envelope"]["context"]
    assert context["project_id"] == "17"
    assert context["thread_id"] == "42"


def test_a_compose_without_a_project_is_refused(music_client):
    """A session with nowhere to live is not a session.

    The produced files are registered against a project, so a compose
    that names none would produce files the host cannot attribute.
    """
    response = music_client.post("/api/music/compose", json={"brief": "a warm pad"})

    assert response.status_code == 422


def _disposable_database():
    """A real PostgreSQL, migrated to head, for the duration of a test.

    The registration path only misbehaves against a real database: a fake
    session has no expiry, no commit semantics, and no unique constraint,
    so it cannot catch a row that never landed or a second write that
    collided with the first. These tests therefore need the real thing.
    """
    import os
    import uuid

    import psycopg
    from psycopg import sql

    admin = os.environ.get("TEST_DATABASE_URL", "").strip()
    if not admin:
        pytest.skip("a disposable PostgreSQL is required for this proof")

    name = "music_assets_" + uuid.uuid4().hex
    with psycopg.connect(admin, autocommit=True) as conn:
        conn.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(name)))
    info = psycopg.conninfo.conninfo_to_dict(admin)
    info["dbname"] = name

    from sqlalchemy.engine import URL

    migration_url = URL.create(
        "postgresql+psycopg",
        username=info.get("user"),
        password=info.get("password"),
        host=info.get("host"),
        port=int(info.get("port", 5432)),
        database=name,
    ).render_as_string(hide_password=False)

    try:
        from guardian.core.pgdb import PgDB
        from tests.services.test_memory_vault_read_projection import _migrate_to_head

        _migrate_to_head(migration_url)

        yield migration_url.replace("postgresql+psycopg://", "postgresql://", 1)
    finally:
        with psycopg.connect(admin, autocommit=True) as conn:
            conn.execute(
                sql.SQL("DROP DATABASE {} WITH (FORCE)").format(sql.Identifier(name))
            )


def _write_artifacts(tmp_path, count=3):
    """Distinct files, as a render would leave them."""
    artifacts = []
    for index in range(count):
        path = tmp_path / f"stem-{index}.wav"
        path.write_bytes(f"RIFF....WAVEfmt {index}".encode())
        artifacts.append(
            {
                "path": str(path),
                "media_kind": "audio",
                "mime_type": "audio/wav",
                "provenance": "generated",
                "bytes": path.stat().st_size,
                "content_hash": None,
            }
        )
    return artifacts


def test_a_registration_that_does_not_commit_is_not_a_registration(
    database_url, tmp_path, monkeypatch
):
    """The row has to survive the session closing.

    ``get_session()`` hands back a plain SQLAlchemy ``Session``, and
    closing one rolls back anything uncommitted. A registration that
    flushes but never commits reports success and leaves nothing behind
    -- which is the worst shape a bug can have: it looks like it worked.

    Run against a real database, because that is the only place the
    difference between a flushed row and a committed one exists.
    """
    from guardian.core.db import GuardianDB
    from guardian.core.pgdb import PgDB
    from guardian.routes import music_projects

    db = GuardianDB(database_url)
    monkeypatch.setattr(music_projects, "_media_db", lambda: db)

    project_id = PgDB(database_url).create_project("music assets", "proof")

    registered = music_projects.register_artifacts(
        _write_artifacts(tmp_path, 1),
        project_id=project_id,
        user_id="local",
    )

    assert len(registered) == 1
    assert registered[0]["asset_id"], "the registration reported no asset id"

    with PgDB(database_url)._connect() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id FROM media_assets WHERE project_id = %s", (project_id,)
            )
            rows = cur.fetchall()
    assert len(rows) == 1, "the row did not survive the session closing"
    assert str(rows[0]["id"]) == registered[0]["asset_id"]


def test_every_produced_file_is_registered_not_just_the_first(
    database_url, tmp_path, monkeypatch
):
    """One registration must not cost the Artist the rest of the session.

    A render produces a set of files -- stems, sequences, a mix, a project.
    If the first one raises, the ones after it must still be registered:
    the files exist whether or not a row was written, and losing them is
    the failure the Artist cannot see.
    """
    from guardian.core.db import GuardianDB
    from guardian.core.pgdb import PgDB
    from guardian.routes import music_projects

    db = GuardianDB(database_url)
    monkeypatch.setattr(music_projects, "_media_db", lambda: db)

    project_id = PgDB(database_url).create_project("music assets", "proof")

    artifacts = _write_artifacts(tmp_path, 3)
    registered = music_projects.register_artifacts(
        artifacts,
        project_id=project_id,
        user_id="local",
    )

    assert len(registered) == 3, [r["asset_id"] for r in registered]
    assert len({r["asset_id"] for r in registered}) == 3

    with PgDB(database_url)._connect() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id FROM media_assets WHERE project_id = %s", (project_id,)
            )
            rows = cur.fetchall()
    assert len(rows) == 3


def test_registering_the_same_file_twice_is_one_row(
    database_url, tmp_path, monkeypatch
):
    """Polling a finished job twice must not fail the second time.

    The job endpoint is polled, and every poll of a finished job asks for
    the files again. The second registration meets the first one's row,
    and the identity it owns is the same fact -- so it reuses that row
    rather than colliding with it and taking the rest of the session
    down with it.
    """
    from guardian.core.db import GuardianDB
    from guardian.core.pgdb import PgDB
    from guardian.routes import music_projects

    db = GuardianDB(database_url)
    monkeypatch.setattr(music_projects, "_media_db", lambda: db)

    project_id = PgDB(database_url).create_project("music assets", "proof")
    artifacts = _write_artifacts(tmp_path, 2)

    first = music_projects.register_artifacts(
        artifacts, project_id=project_id, user_id="local"
    )
    second = music_projects.register_artifacts(
        artifacts, project_id=project_id, user_id="local"
    )

    assert len(first) == 2
    assert len(second) == 2, "the second registration lost the files"
    assert [r["asset_id"] for r in first] == [r["asset_id"] for r in second]

    with PgDB(database_url)._connect() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id FROM media_assets WHERE project_id = %s", (project_id,)
            )
            rows = cur.fetchall()
    assert len(rows) == 2, "the second registration wrote a duplicate row"


def test_the_host_hashes_the_bytes_rather_than_trusting_the_producer(
    database_url, tmp_path, monkeypatch
):
    """Identity is the host's, so the hash is the host's.

    The Producer reports a hash for each file it produced. If the host
    takes that claim as the identity, a wrong hash becomes the row's
    identity -- and two registrations of the same bytes become two rows.
    The host already holds the bytes, so it hashes them itself.
    """
    from guardian.core.db import GuardianDB
    from guardian.core.pgdb import PgDB
    from guardian.routes import music_projects

    db = GuardianDB(database_url)
    monkeypatch.setattr(music_projects, "_media_db", lambda: db)

    project_id = PgDB(database_url).create_project("music assets", "proof")

    artifacts = _write_artifacts(tmp_path, 1)
    artifacts[0]["content_hash"] = "0" * 64

    registered = music_projects.register_artifacts(
        artifacts, project_id=project_id, user_id="local",
    )

    assert len(registered) == 1
    assert registered[0]["content_hash"] != "0" * 64, (
        "the host took the producer's hash as the identity"
    )

    import hashlib

    expected = hashlib.sha256((tmp_path / "stem-0.wav").read_bytes()).hexdigest()
    assert registered[0]["content_hash"] == expected


def test_artifacts_are_registered_against_a_project_with_no_thread(
    database_url, tmp_path, monkeypatch
):
    """Custody belongs to the Project; the Thread is only provenance.

    ADR-108 requires this assertion to be proven against a real
    database: the files are registered even when the originating thread
    cannot be resolved, because the Project is the durable home and the
    Thread is the attribution. A missing thread must not cost the
    Artist their files -- and the row must not claim a thread that does
    not exist.

    This goes through the real resolution path rather than around it:
    the thread id below is not in the database, and the registration has
    to notice that and carry on without it.
    """
    from types import SimpleNamespace

    from guardian.core.db import GuardianDB
    from guardian.core.pgdb import PgDB
    from guardian.routes import music_projects

    db = GuardianDB(database_url)
    monkeypatch.setattr(music_projects, "_media_db", lambda: db)

    project_id = PgDB(database_url).create_project("music custody", "proof")
    missing_thread_id = 987654

    artifacts = _write_artifacts(tmp_path, 2)
    music_projects._register_artifacts_from(
        {"artifacts": artifacts},
        {"project_id": str(project_id), "thread_id": str(missing_thread_id)},
        SimpleNamespace(user_id="local"),
    )

    with PgDB(database_url)._connect() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, project_id, thread_id FROM media_assets "
                "WHERE project_id = %s",
                (project_id,),
            )
            rows = cur.fetchall()

    assert len(rows) == 2, "the files were lost over a missing thread"
    for row in rows:
        assert row["project_id"] == project_id
        assert row["thread_id"] is None, (
            "the row claims a thread that does not exist"
        )


def test_a_finished_job_registers_its_files(monkeypatch, music_client):
    """The service made the files; the host decides what they are called.

    So the host registers them itself, against the project the job was
    started for.
    """
    from guardian.routes import music_projects

    registered = {}

    def _register(artifacts, *, project_id, thread_id=None, user_id=None):
        registered["artifacts"] = artifacts
        registered["project_id"] = project_id
        registered["thread_id"] = thread_id
        return [{"id": "asset-1"}]

    monkeypatch.setattr(music_projects, "register_artifacts", _register)
    monkeypatch.setattr(
        music_projects, "_music_target_is_real", lambda *_a, **_k: True
    )

    monkeypatch.setattr(
        music_projects.requests,
        "post",
        lambda *_a, **_k: _FakeResponse(
            {
                "ok": True,
                "output": {
                    "job_id": "job-1",
                    "status": "succeeded",
                    "context": {"project_id": "17", "thread_id": "42"},
                    "output": {"artifacts": [{"path": "/out/mix.wav"}]},
                },
                "error": None,
            }
        ),
    )

    response = music_client.get("/api/music/jobs/job-1")

    assert response.status_code == 200
    assert registered["project_id"] == 17
    assert registered["thread_id"] == 42
    assert registered["artifacts"] == [{"path": "/out/mix.wav"}]


def test_a_thread_that_is_not_there_does_not_cost_the_files(monkeypatch, music_client):
    """Attribution that points at nothing is dropped, not failed.

    The project is what the row needs. A thread that is not there cannot
    be attributed to, and losing the files over it would be the wrong
    trade.
    """
    from guardian.routes import music_projects

    registered = {}

    def _register(artifacts, *, project_id, thread_id=None, user_id=None):
        registered["project_id"] = project_id
        registered["thread_id"] = thread_id
        return [{"id": "asset-1"}]

    monkeypatch.setattr(music_projects, "register_artifacts", _register)
    monkeypatch.setattr(
        music_projects, "_music_target_is_real", lambda *_a, **_k: False
    )

    monkeypatch.setattr(
        music_projects.requests,
        "post",
        lambda *_a, **_k: _FakeResponse(
            {
                "ok": True,
                "output": {
                    "job_id": "job-3",
                    "status": "succeeded",
                    "context": {"project_id": "17", "thread_id": "999"},
                    "output": {"artifacts": [{"path": "/out/mix.wav"}]},
                },
                "error": None,
            }
        ),
    )

    response = music_client.get("/api/music/jobs/job-3")

    assert response.status_code == 200
    assert registered["project_id"] == 17
    assert registered["thread_id"] is None


def test_a_failed_registration_does_not_fail_the_job(monkeypatch, music_client):
    """The Artist's music exists whether or not a row was written."""
    from guardian.routes import music_projects

    def _boom(*_a, **_k):
        raise RuntimeError("the media table is unhappy")

    monkeypatch.setattr(music_projects, "register_artifacts", _boom)

    monkeypatch.setattr(
        music_projects.requests,
        "post",
        lambda *_a, **_k: _FakeResponse(
            {
                "ok": True,
                "output": {
                    "job_id": "job-2",
                    "status": "succeeded",
                    "context": {"project_id": "17"},
                    "output": {"artifacts": [{"path": "/out/mix.wav"}]},
                },
                "error": None,
            }
        ),
    )

    response = music_client.get("/api/music/jobs/job-2")

    assert response.status_code == 200
    assert response.json()["status"] == "succeeded"


# --------------------------------------------------------------------------
# The host's own record of the job
#
# The route used to read the project and thread out of the context the
# service echoed back on a finished job. That made the host's attribution
# depend on the engine's age: an engine that predates the echo hands back
# files the host cannot place, and the host reports success anyway --
# files produced, none registered. That is the same shape as the three
# defects PR #1003 fixed, one layer up.
#
# So the host keeps its own copy of the attribution, written when the job
# handle is minted. The proofs below are against a real database, because
# a row that never landed is invisible to a fake.
# --------------------------------------------------------------------------


def _service_that_answers(compose_output, job_output):
    """A service that answers compose and job_status differently."""

    def _post(url, json=None, timeout=None, **_kwargs):
        action = (json or {}).get("action")
        payload = compose_output if action == "compose" else job_output
        return _FakeResponse({"ok": True, "output": payload, "error": None})

    return _post


def _with_a_real_database(database_url, monkeypatch):
    """Point the route at a real database, and return its project id."""
    from guardian.core.db import GuardianDB
    from guardian.core.pgdb import PgDB
    from guardian.routes import music_projects

    monkeypatch.setattr(music_projects, "_media_db", lambda: GuardianDB(database_url))
    monkeypatch.setattr(music_projects, "chatlog_db", PgDB(database_url))
    return PgDB(database_url).create_project("music jobs", "proof")


def test_the_host_records_which_project_a_job_belongs_to(
    database_url, tmp_path, monkeypatch, music_client
):
    """The host sent the context, so it should keep its own copy of it.

    The row is written when the job handle is minted, which is the one
    moment the host knows what the work belongs to.
    """
    from guardian.core.pgdb import PgDB
    from guardian.routes import music_projects

    project_id = _with_a_real_database(database_url, monkeypatch)

    monkeypatch.setattr(
        music_projects.requests,
        "post",
        _service_that_answers(
            {"job_id": "job-1", "status": "running"},
            {"job_id": "job-1", "status": "succeeded"},
        ),
    )

    response = music_client.post(
        "/api/music/compose", json={"brief": "a warm pad", "project_id": project_id}
    )
    assert response.status_code == 200, response.text

    with PgDB(database_url)._connect() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT job_id, project_id, thread_id FROM music_jobs "
                "WHERE job_id = %s",
                ("job-1",),
            )
            rows = cur.fetchall()

    assert len(rows) == 1, "the host did not record the job"
    assert rows[0]["project_id"] == project_id
    assert rows[0]["thread_id"] is None


def test_a_service_that_echoes_nothing_still_gets_its_files_attributed(
    database_url, tmp_path, monkeypatch, music_client
):
    """The whole point: attribution must not depend on the engine's age.

    An engine that does not echo the context back -- one predating the
    echo -- returns a finished job with no context on it. Before this
    change the host had nothing to attribute the files to, produced them
    anyway, and reported success. With the host's own record, the files
    are attributed whether or not the service remembers anything.
    """
    from guardian.core.pgdb import PgDB
    from guardian.routes import music_projects

    project_id = _with_a_real_database(database_url, monkeypatch)

    monkeypatch.setattr(
        music_projects.requests,
        "post",
        _service_that_answers(
            {"job_id": "job-2", "status": "running"},
            # No "context" key at all: this is what an engine that does
            # not echo the context looks like from here.
            {
                "job_id": "job-2",
                "status": "succeeded",
                "output": {"artifacts": _write_artifacts(tmp_path, 1)},
            },
        ),
    )

    started = music_client.post(
        "/api/music/compose", json={"brief": "a warm pad", "project_id": project_id}
    )
    assert started.status_code == 200, started.text

    finished = music_client.get("/api/music/jobs/job-2")
    assert finished.status_code == 200, finished.text

    with PgDB(database_url)._connect() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, project_id FROM media_assets WHERE project_id = %s",
                (project_id,),
            )
            rows = cur.fetchall()

    assert len(rows) == 1, (
        "the files were produced but not attributed: the host cannot "
        "register what it cannot place"
    )
    assert rows[0]["project_id"] == project_id


def test_the_hosts_own_record_wins_over_what_the_service_echoed(
    database_url, tmp_path, monkeypatch, music_client
):
    """The host's record is what the host decided, not what it read back.

    If the two disagree, the host's answer is the one it gave.
    """
    from guardian.core.pgdb import PgDB
    from guardian.routes import music_projects

    project_id = _with_a_real_database(database_url, monkeypatch)

    monkeypatch.setattr(
        music_projects.requests,
        "post",
        _service_that_answers(
            {"job_id": "job-3", "status": "running"},
            {
                "job_id": "job-3",
                "status": "succeeded",
                # The service remembers a different project.
                "context": {"project_id": "999999"},
                "output": {"artifacts": _write_artifacts(tmp_path, 1)},
            },
        ),
    )

    music_client.post(
        "/api/music/compose", json={"brief": "a warm pad", "project_id": project_id}
    )
    finished = music_client.get("/api/music/jobs/job-3")
    assert finished.status_code == 200, finished.text

    with PgDB(database_url)._connect() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT id, project_id FROM media_assets")
            rows = cur.fetchall()

    assert len(rows) == 1, "the files were lost"
    assert rows[0]["project_id"] == project_id, (
        "the echoed context overrode the host's own record"
    )


def test_a_job_is_not_moved_by_a_later_record(
    database_url, monkeypatch, music_client
):
    """The first write wins.

    A job belongs to one project. If a second write could move it, then
    whichever write happened last would decide, and the attribution
    would depend on the order of unrelated requests.
    """
    from guardian.core.pgdb import PgDB
    from guardian.routes import music_projects

    project_id = _with_a_real_database(database_url, monkeypatch)

    monkeypatch.setattr(
        music_projects.requests,
        "post",
        _service_that_answers(
            {"job_id": "job-4", "status": "running"},
            {"job_id": "job-4", "status": "succeeded"},
        ),
    )

    music_client.post(
        "/api/music/compose", json={"brief": "a warm pad", "project_id": project_id}
    )

    pgdb = PgDB(database_url)
    pgdb.record_music_job("job-4", project_id=project_id + 100000, thread_id=None)

    row = pgdb.get_music_job("job-4")
    assert row is not None
    assert row["project_id"] == project_id, "a later record moved the job"


def test_a_record_that_cannot_be_written_does_not_cost_the_files(
    database_url, tmp_path, monkeypatch, music_client
):
    """The Artist's music exists whether or not a row was written.

    A database that refuses the attribution write must not fail the
    compose. The fallback still attributes the files, so the job
    succeeds and the files are registered.
    """
    from guardian.core.pgdb import PgDB
    from guardian.routes import music_projects

    project_id = _with_a_real_database(database_url, monkeypatch)

    class _DatabaseThatCannotRecord:
        """A database whose attribution writes always fail."""

        def __init__(self, inner):
            self._inner = inner

        def record_music_job(self, *_args, **_kwargs):
            raise RuntimeError("the music_jobs table is unhappy")

        def get_music_job(self, *args, **kwargs):
            return self._inner.get_music_job(*args, **kwargs)

    monkeypatch.setattr(
        music_projects, "chatlog_db", _DatabaseThatCannotRecord(music_projects.chatlog_db)
    )

    monkeypatch.setattr(
        music_projects.requests,
        "post",
        _service_that_answers(
            {"job_id": "job-5", "status": "running"},
            {
                "job_id": "job-5",
                "status": "succeeded",
                "context": {"project_id": str(project_id)},
                "output": {"artifacts": _write_artifacts(tmp_path, 1)},
            },
        ),
    )

    started = music_client.post(
        "/api/music/compose", json={"brief": "a warm pad", "project_id": project_id}
    )
    assert started.status_code == 200, started.text

    finished = music_client.get("/api/music/jobs/job-5")
    assert finished.status_code == 200, finished.text

    with PgDB(database_url)._connect() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, project_id FROM media_assets WHERE project_id = %s",
                (project_id,),
            )
            rows = cur.fetchall()

    assert len(rows) == 1, "a refused record cost the Artist the files"


def test_the_job_model_and_the_migration_agree():
    """Two statements of one schema; when they drift, only the column
    nobody exercised notices."""
    import re

    from sqlalchemy.dialects import postgresql
    from sqlalchemy.schema import CreateTable

    from guardian.db.models import MusicJob

    model_ddl = str(
        CreateTable(MusicJob.__table__).compile(dialect=postgresql.dialect())
    )

    revisions = Path("guardian/db/migrations/versions")
    candidates = [
        path
        for path in revisions.glob("*.py")
        if "music_jobs" in path.read_text(encoding="utf-8")
    ]
    assert candidates, "no migration creates the music_jobs table"
    migration_text = candidates[0].read_text(encoding="utf-8")

    for column in MusicJob.__table__.columns:
        assert column.name in migration_text, (
            f"{column.name} is in the model but not in the migration"
        )

    assert "chat_threads" in model_ddl, "the thread reference is not in the model"


# --------------------------------------------------------------------------
# The whole-state write
#
# `current_spec` is a record of what the Producer produced, written whole.
# A partial write that merged would silently resurrect values the Artist
# already changed -- so it has to clear them, and that has to be proven
# against a real database rather than asserted about a mock.
# --------------------------------------------------------------------------


def test_a_whole_state_write_replaces_and_a_partial_one_clears():
    """A revision replaces the state; it does not merge into it.

    Writing the full state, then writing only part of it, must leave the
    omitted columns null. A merge would resurrect values the Artist had
    already changed -- and the write would still look like it worked.
    """
    import os
    import uuid

    import psycopg
    from psycopg import sql

    admin = os.environ.get("TEST_DATABASE_URL", "").strip()
    if not admin:
        pytest.skip("a disposable PostgreSQL is required for this proof")

    name = "music_state_" + uuid.uuid4().hex
    with psycopg.connect(admin, autocommit=True) as conn:
        conn.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(name)))
    info = psycopg.conninfo.conninfo_to_dict(admin)
    info["dbname"] = name

    from sqlalchemy.engine import URL

    migration_url = URL.create(
        "postgresql+psycopg",
        username=info.get("user"),
        password=info.get("password"),
        host=info.get("host"),
        port=int(info.get("port", 5432)),
        database=name,
    ).render_as_string(hide_password=False)

    try:
        from guardian.core.pgdb import PgDB
        from tests.services.test_memory_vault_read_projection import _migrate_to_head

        _migrate_to_head(migration_url)

        db = PgDB(migration_url.replace("postgresql+psycopg://", "postgresql://", 1))

        project_id = db.create_project("music state proof", "proof")
        db.upsert_music_project(
            project_id,
            bpm=120.0,
            musical_key="C minor",
            bars=8,
            current_spec={"title": "first"},
        )

        full = db.get_music_project(project_id)
        assert full["bpm"] == 120.0
        assert full["musical_key"] == "C minor"
        assert full["current_spec"] == {"title": "first"}

        # A partial write is a new complete state, not a patch.
        db.upsert_music_project(project_id, bpm=90.0)
        partial = db.get_music_project(project_id)
        assert partial["bpm"] == 90.0
        assert partial["musical_key"] is None, "a partial write merged instead of replacing"
        assert partial["bars"] is None
        assert partial["current_spec"] is None
    finally:
        with psycopg.connect(admin, autocommit=True) as conn:
            conn.execute(
                sql.SQL("DROP DATABASE {} WITH (FORCE)").format(sql.Identifier(name))
            )


# --------------------------------------------------------------------------
# The model and the migration describe the same table
# --------------------------------------------------------------------------


def test_the_model_and_the_migration_agree():
    """Two statements of one schema; when they drift, the database and the
    application disagree, and only the column nobody exercised notices."""
    import re

    from sqlalchemy.dialects import postgresql
    from sqlalchemy.schema import CreateTable

    from guardian.db.models import MusicProject

    model_ddl = str(CreateTable(MusicProject.__table__).compile(dialect=postgresql.dialect()))

    revisions = Path("guardian/db/migrations/versions")
    candidates = [
        path
        for path in revisions.glob("*.py")
        if "music_projects" in path.read_text(encoding="utf-8")
    ]
    assert candidates, "no migration creates the music_projects table"
    migration_text = candidates[0].read_text(encoding="utf-8")

    for column in MusicProject.__table__.columns:
        assert column.name in migration_text, (
            f"{column.name} is in the model but not in the migration"
        )


def test_the_migration_leaves_a_single_alembic_head():
    """A second head is how a migration chain quietly forks."""
    import subprocess
    import sys

    result = subprocess.run(
        [sys.executable, "-m", "alembic", "-c", "backend/alembic.ini", "heads"],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        pytest.skip(f"alembic is not runnable here: {result.stderr[-300:]}")

    heads = [
        line.strip()
        for line in result.stdout.splitlines()
        if "(head)" in line
    ]
    assert len(heads) == 1, f"expected one head, got: {heads}"


# --------------------------------------------------------------------------
# The manifest and the service
# --------------------------------------------------------------------------


def test_the_plugin_manifest_is_valid_and_matches_the_service():
    """The manifest advertises the capabilities; the service answers them.

    If they drift, the host tells the model a capability exists and then
    refuses it when the model reaches for it.
    """
    from guardian.plugins.plugin_manifest import PluginManifest

    manifest_path = Path("plugins/agentdaw/manifest.json")
    assert manifest_path.exists(), "the Agent-DAW plugin manifest should ship"

    manifest = PluginManifest.model_validate(
        json.loads(manifest_path.read_text(encoding="utf-8"))
    )

    assert manifest.id == "agentdaw"
    assert manifest.base_url.startswith(("http://", "https://"))

    declared = manifest.operations()
    assert ("music", "compose") in declared
    assert ("music", "preview") in declared


def test_the_manifest_base_url_matches_the_route_default():
    """One URL, written down once, or the host calls somewhere else."""
    from guardian.routes import music_projects

    manifest = json.loads(
        Path("plugins/agentdaw/manifest.json").read_text(encoding="utf-8")
    )
    assert manifest["base_url"] == music_projects.DEFAULT_AGENTDAW_URL


# --------------------------------------------------------------------------
# The profile is the gate
# --------------------------------------------------------------------------


def _mounted_paths(app) -> set[str]:
    import fastapi.routing as fastapi_routing

    iter_contexts = getattr(fastapi_routing, "iter_route_contexts", None)
    routes = iter_contexts(app.routes) if iter_contexts else app.routes
    return {
        getattr(route, "path", None)
        for route in routes
        if isinstance(getattr(route, "path", None), str)
    }


def test_the_music_profile_mounts_the_route_and_the_default_does_not(
    monkeypatch, tmp_path
):
    """Absent, not broken.

    The default profile is byte-frozen, so the Producer lives in a profile
    of its own. This asserts the gate actually gates: under the music
    profile the route is mounted, and under the default profile it is not
    mounted at all -- so the Artist sees no music surface rather than a
    broken one.
    """
    import importlib
    import os

    import guardian.guardian_api as guardian_api

    original = os.environ.get("CODEXIFY_SUPPORTED_PROFILE")

    monkeypatch.setenv("GUARDIAN_API_KEY", "test-api-key")
    monkeypatch.setenv("ENABLE_CONNECTOR_WORKER", "0")
    monkeypatch.setenv("STORAGE_BASE_PATH", str(tmp_path / "media"))

    try:
        monkeypatch.setenv("CODEXIFY_SUPPORTED_PROFILE", "v1-music-producer")
        music_app = importlib.reload(guardian_api).app
        assert "/api/music/compose" in _mounted_paths(music_app)

        monkeypatch.setenv("CODEXIFY_SUPPORTED_PROFILE", "v1-local-core-web-mcp")
        default_app = importlib.reload(guardian_api).app
        assert "/api/music/compose" not in _mounted_paths(default_app)
    finally:
        if original is None:
            os.environ.pop("CODEXIFY_SUPPORTED_PROFILE", None)
        else:
            os.environ["CODEXIFY_SUPPORTED_PROFILE"] = original
        importlib.reload(guardian_api)
