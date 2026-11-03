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
