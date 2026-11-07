"""
Music Project Routes
~~~~~~~~~~~~~~~~~~~~~

A Music Project is an ordinary Codexify ``Project`` with musical state
attached to it. There is no parallel chat concept: threads and chats are
the existing ``ChatThread`` / ``ChatMessage`` rows, which already carry
a ``project_id`` foreign key.

This module is deliberately **thin**. It does two things:

1. Reads and writes the musical state of a Music Project.
2. Forwards the Producer's operations to the Agent-DAW service, which
   runs as its own container.

The split is not decorative. Codexify derives its model-callable tools
from the app's OpenAPI schema (``guardian/command_bus/manifest.py`` ->
``guardian/tools/derive.py``), so the model can only call a route that
exists *here*. That route has to exist in this process for the tool to
exist at all -- but the code that renders audio does not have to.

So this module owns the contract and the forwarding, and the service
owns the music. Codexify never imports ``agentdaw``: the dependency runs
in the other direction, over HTTP, on the canonical service-plugin
protocol (``POST {base_url}/invoke`` with the versioned envelope).

**Why the forwarding is asynchronous by default.** A live compose takes
around 107 seconds -- the Producer's LLM call is the long pole, and the
render itself is only about two seconds. Blocking a chat turn for that
long is a turn the Artist watches hang, so ``compose`` returns a job
handle and the caller polls ``GET /api/music/jobs/{job_id}``. The quick
operations -- preview, render, measure, anchor -- are synchronous.

The state endpoints here are thin on purpose too. The Producer owns the
music; this side owns the record of it. Everything that decides *what*
the music should be -- tempo, key, bars, the spec itself -- is derived
by the Producer and written back complete, never patched field by field,
because a revision replaces the whole state.

``music_projects.current_spec`` is therefore a whole-state *record* of
what the Producer produced, not an independent truth about the music.
It is written whole. When the Artist edits the ``.rpp`` in REAPER after
the handoff, the two disagree, and until that is reconciled the
Producer's specification is the authority on what the music is -- the
column records where it was at handoff, not where it is now.
"""

import logging
import os
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

import requests
from fastapi import APIRouter, Body, Depends, HTTPException, Query
from pydantic import BaseModel, ConfigDict, Field

from guardian.config.db_defaults import DEFAULT_PG_DSN

# Shared dependencies are imported defensively, the way guardian/routes/
# projects.py does it: guardian_api.py imports this module at module
# scope, so an ImportError here would stop the whole app from booting.
try:
    from guardian.core.dependencies import (
        RequestUserScope,
        chatlog_db,
        get_account_user_scope as get_request_user_scope,
    )
except ImportError:  # pragma: no cover - dependency shape guard
    chatlog_db = None
    RequestUserScope = object  # type: ignore[assignment,misc]

    def get_request_user_scope():  # type: ignore[misc]
        return None


logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/music", tags=["music"])

#: Where the Agent-DAW service lives. Matches the ``base_url`` in
#: ``plugins/agentdaw/manifest.json``; both point at the compose service
#: name, so the two cannot drift apart without the manifest changing too.
ENV_AGENTDAW_URL = "AGENTDAW_SERVICE_URL"
DEFAULT_AGENTDAW_URL = "http://agentdaw:8000"

#: The canonical service-plugin protocol version. It is checked, not
#: assumed: the service refuses an envelope it does not understand, and
#: this side refuses a response that does not carry ``ok``.
PROTOCOL_VERSION = "1.0"
PLUGIN_ID = "agentdaw"
CAPABILITY = "music"

#: The facade uses 10 seconds for a plugin invoke
#: (``INVOKE_TIMEOUT_SECONDS`` in ``guardian/core/plugins.py``). A compose
#: takes about 107, so the request that starts one returns immediately
#: with a job handle and the work continues on the service.
JOB_ACTIONS = {"compose"}


def _service_url() -> str:
    return (os.getenv(ENV_AGENTDAW_URL) or DEFAULT_AGENTDAW_URL).rstrip("/")


def _invoke(
    action: str,
    payload: Dict[str, Any],
    *,
    context: Optional[Dict[str, Any]] = None,
    timeout: int = 30,
) -> Dict[str, Any]:
    """Call one Agent-DAW operation through the canonical envelope.

    The response is the canonical one: ``ok`` plus either ``output`` or
    ``error``. A response that does not carry a boolean ``ok`` is a
    broken service, not a bad request, and it is reported as such.
    """
    envelope = {
        "protocol_version": PROTOCOL_VERSION,
        "plugin_id": PLUGIN_ID,
        "capability": CAPABILITY,
        "action": action,
        "input": payload,
        "context": context or {},
    }
    url = f"{_service_url()}/invoke"

    try:
        response = requests.post(url, json=envelope, timeout=timeout)
    except requests.RequestException as exc:
        logger.warning("[music_projects] agentdaw service unreachable: %s", exc)
        raise HTTPException(
            status_code=503,
            detail=f"the music service is unreachable: {exc}",
        )

    if response.status_code >= 400:
        logger.warning(
            "[music_projects] agentdaw service returned %s: %s",
            response.status_code,
            response.text[:300],
        )
        raise HTTPException(
            status_code=502,
            detail=f"the music service returned {response.status_code}",
        )

    try:
        body = response.json()
    except ValueError as exc:
        raise HTTPException(
            status_code=502,
            detail=f"the music service returned malformed JSON: {exc}",
        )

    if not isinstance(body, dict) or not isinstance(body.get("ok"), bool):
        raise HTTPException(
            status_code=502,
            detail="the music service returned a malformed response",
        )

    if body["ok"] is False:
        error = body.get("error") or {}
        raise HTTPException(
            status_code=502,
            detail=error.get("message") or "the music service reported an error",
        )

    output = body.get("output") or {}
    # A job handle is minted here, and this is the one place the host
    # knows what it belongs to. Recording it now is what lets the
    # attribution survive an engine that does not echo the context back.
    _record_job_attribution(output, context)
    return output


def _record_job_attribution(
    output: Dict[str, Any],
    context: Optional[Dict[str, Any]],
) -> None:
    """Keep the host's own copy of which project a job belongs to.

    The host sent the context, so it knows the answer already; keeping
    a copy means the attribution does not depend on the service echoing
    the context back. An engine that does not echo it used to produce
    files the host could not place, and the host reported success
    anyway -- files produced, none registered.

    The write is best effort. If it fails the files are still worth
    producing, so the failure is logged and swallowed: the Artist's
    music exists either way.
    """
    job_id = (output or {}).get("job_id")
    if not job_id:
        return

    context = context or {}
    raw_project_id = context.get("project_id")
    if not raw_project_id:
        return
    try:
        project_id = int(raw_project_id)
    except (TypeError, ValueError):
        logger.warning(
            "[music_projects] work carried a non-numeric project id; the "
            "job was not attributed"
        )
        return

    db = chatlog_db
    if db is None:
        logger.warning(
            "[music_projects] no database is configured; job %s was not "
            "attributed",
            job_id,
        )
        return

    try:
        db.record_music_job(
            str(job_id),
            project_id=project_id,
            thread_id=_thread_id_from_context(context),
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "[music_projects] could not attribute job %s to project %s: %s",
            job_id,
            project_id,
            exc,
        )


def _thread_id_from_context(context: Dict[str, Any]) -> Optional[int]:
    """The thread a job belongs to, or None.

    A thread that is not there is dropped rather than allowed to fail
    the registration; the project is what the row needs.
    """
    raw_thread_id = (context or {}).get("thread_id")
    if not raw_thread_id:
        return None
    try:
        return int(raw_thread_id)
    except (TypeError, ValueError):
        return None


# --------------------------------------------------------------------------
# Request models
#
# Module scope on purpose: this module uses postponed annotation
# evaluation, so FastAPI resolves the annotation strings against these
# module globals. A model defined inside a function cannot be resolved
# there, and FastAPI silently demotes the argument to a query parameter.
# The schema is the model's only documentation, so the field names are
# the Artist's vocabulary -- brief, feedback, query -- not params.
# --------------------------------------------------------------------------


class ComposeRequest(BaseModel):
    """The Artist's brief, in the Artist's words.

    Describe the music: mood, tempo, instrumentation, how it should move,
    how long it should be. Tempo, key, bar count and length stated here
    are treated as locked and will not be reinterpreted. Do not pass DSP
    values -- the engine owns those.
    """

    brief: str = Field(
        ...,
        description="The artist's description, in plain words. Not DSP parameters.",
    )
    project_id: int = Field(
        ...,
        description=(
            "The Music Project this session belongs to. The produced files "
            "are registered against it, so a session with nowhere to live "
            "is not a session."
        ),
    )
    thread_id: int | None = Field(
        default=None,
        description=(
            "The thread the work happens in, when there is one. The files "
            "are namespaced under it, so a thread's music stays findable."
        ),
    )
    library: str | None = Field(
        default=None, description="Path to the approved patch library JSON."
    )
    render: bool = Field(
        default=True, description="Also render stems, MIDI and the project."
    )
    sync: bool = Field(
        default=False,
        description=(
            "Wait for the result instead of returning a job handle. A compose "
            "takes about 107 seconds because the model's own call is the long "
            "pole, so the default is to return a job id and poll it."
        ),
    )


class ReviseRequest(BaseModel):
    """A correction to an existing session."""

    spec: Dict[str, Any] = Field(..., description="The existing session spec.")
    feedback: str = Field(
        ..., description="What the artist wants changed, in plain words."
    )
    library: str | None = None


class PreviewRequest(BaseModel):
    """A fast audition of one patch."""

    spec: Dict[str, Any] = Field(..., description="The session spec.")
    patch_id: str = Field(..., description="Which patch to audition.")


class RenderRequest(BaseModel):
    """A full render of a spec."""

    spec: Dict[str, Any] = Field(..., description="The session spec.")
    project_id: int = Field(
        ...,
        description="The Music Project the rendered files belong to.",
    )
    thread_id: int | None = Field(
        default=None,
        description="The thread the work happens in, when there is one.",
    )
    out_dir: str | None = None


class ApproveRequest(BaseModel):
    """Promote a session's patches into the approved library."""

    spec: Dict[str, Any] = Field(..., description="The session spec.")
    measurements: Dict[str, Dict[str, float]] | None = Field(
        default=None,
        description="Per-track measurements, keyed by track id.",
    )
    library: str | None = None


class MusicProjectState(BaseModel):
    """The musical state of a Music Project.

    ``current_spec`` is the complete session state. It is written whole,
    never merged: a revision is a new complete state, and a partial
    update here would silently resurrect values the Artist already
    changed.
    """

    bpm: Optional[float] = None
    musical_key: Optional[str] = None
    musical_mode: Optional[str] = None
    bars: Optional[int] = None
    time_signature: Optional[str] = None
    length_seconds: Optional[float] = None
    library_path: Optional[str] = None
    current_spec: Optional[Dict[str, Any]] = None

    model_config = ConfigDict(extra="ignore")


# --------------------------------------------------------------------------
# Producer operations -- forwarded to the Agent-DAW service
# --------------------------------------------------------------------------


def _music_context(
    project_id: int,
    thread_id: int | None,
    scope: Any,
) -> Dict[str, Any]:
    """What the work belongs to, in the envelope the service understands.

    The service cannot interpret any of this -- it does not know the
    host's data model -- but it carries it back on the job, which is how
    the host learns which project the finished files belong to.
    """
    context: Dict[str, Any] = {"project_id": str(project_id)}
    if thread_id is not None:
        context["thread_id"] = str(thread_id)
    user_id = getattr(scope, "user_id", None)
    if user_id:
        context["user_id"] = str(user_id)
    return context


@router.post(
    "/compose",
    summary="Produce a music session from an artist's description",
    description=(
        "Turn a description into a session: a spec, rendered stems, MIDI, a mix "
        "and a REAPER project, plus the measurements that were taken of them. "
        "Approved patches are retrieved from the library and revised rather "
        "than reinvented when one matches. Returns a job id; poll "
        "GET /api/music/jobs/{job_id} for the result."
    ),
)
def compose(
    req: ComposeRequest,
    request_user_scope: RequestUserScope = Depends(get_request_user_scope),
) -> Dict[str, Any]:
    payload: Dict[str, Any] = {
        "brief": req.brief,
        "library": req.library,
        "render": req.render,
    }
    if req.sync:
        payload["mode"] = "sync"
    else:
        payload["mode"] = "async"

    # A synchronous compose outlives the HTTP timeout below, so it gets
    # its own, generous one.
    timeout = 600 if req.sync else 30
    context = _music_context(req.project_id, req.thread_id, request_user_scope)
    output = _invoke("compose", payload, context=context, timeout=timeout)
    if req.sync:
        # A synchronous compose returns the files itself, so this is where
        # they are registered. The asynchronous one registers when the job
        # is polled.
        _register_artifacts_from(output, context, request_user_scope)
    return output


@router.post(
    "/revise",
    summary="Revise a session from the artist's correction",
    description=(
        "Apply a correction in plain words. Everything the artist did not "
        "mention stays as it was; the returned spec is a complete new state."
    ),
)
def revise(req: ReviseRequest) -> Dict[str, Any]:
    return _invoke(
        "revise",
        {"spec": req.spec, "feedback": req.feedback, "library": req.library},
    )


@router.post(
    "/preview",
    summary="Audition one patch quickly",
    description=(
        "Render one patch under the session's drum bed. Fast on purpose: this "
        "is the loop the artist approves a sound in. Returns measurements, "
        "not adjectives."
    ),
)
def preview(req: PreviewRequest) -> Dict[str, Any]:
    return _invoke("preview", {"spec": req.spec, "patch_id": req.patch_id})


@router.post(
    "/render",
    summary="Render a spec to stems, MIDI, a mix and a project",
)
def render(
    req: RenderRequest,
    request_user_scope: RequestUserScope = Depends(get_request_user_scope),
) -> Dict[str, Any]:
    context = _music_context(req.project_id, req.thread_id, request_user_scope)
    output = _invoke(
        "render",
        {"spec": req.spec, "out_dir": req.out_dir},
        context=context,
    )
    _register_artifacts_from(output, context, request_user_scope)
    return output


@router.get(
    "/anchors",
    summary="Find approved patches that match a request",
    description=(
        "Search the approved patch library. A miss is a legitimate answer and "
        "is reported as one, so the artist can be told that nothing matches "
        "instead of being handed a false recall."
    ),
)
def anchors(
    query: str = Query(..., description="What to look for, in plain words."),
    library: str | None = Query(default=None),
    limit: int = Query(default=5),
) -> Dict[str, Any]:
    return _invoke(
        "anchor",
        {"query": query, "library": library, "limit": limit},
    )


@router.post(
    "/approve",
    summary="Promote a session's patches into the approved library",
)
def approve(req: ApproveRequest) -> Dict[str, Any]:
    return _invoke(
        "approve",
        {
            "spec": req.spec,
            "measurements": req.measurements,
            "library": req.library,
        },
    )


@router.get(
    "/jobs/{job_id}",
    summary="Poll an asynchronous music job",
    description=(
        "Compose takes about 107 seconds, so it runs as a job. Poll this for "
        "the result. The status is one of running, succeeded or failed."
    ),
)
def job_status(
    job_id: str,
    request_user_scope: RequestUserScope = Depends(get_request_user_scope),
) -> Dict[str, Any]:
    result = _invoke("job_status", {"job_id": job_id})
    _register_finished_artifacts(result, request_user_scope)
    return result


def _register_finished_artifacts(
    result: Dict[str, Any],
    scope: Any,
) -> None:
    """Register the files a finished job produced."""
    if not isinstance(result, dict) or result.get("status") != "succeeded":
        return
    _register_artifacts_from(
        result.get("output") or {},
        _attribution_for(result),
        scope,
    )


def _host_job_record(job_id: Optional[str]) -> Optional[Dict[str, Any]]:
    """The host's own record of a job, or None.

    A database that cannot answer is treated as having no record rather
    than as an error: the fallback below still attributes the files, and
    the warning makes the missing record visible.
    """
    if not job_id:
        return None
    db = chatlog_db
    if db is None:
        return None
    try:
        return db.get_music_job(str(job_id))
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "[music_projects] could not read the record of job %s: %s",
            job_id,
            exc,
        )
        return None


def _attribution_for(result: Dict[str, Any]) -> Dict[str, Any]:
    """Which project and thread a finished job belongs to.

    The host's own record wins: it was written from the context the
    host sent, so it is the answer the host gave rather than one it
    read back. The context the service echoed is the fallback for a job
    the host never recorded, and it is logged when it is used, so a
    missing host record is visible instead of silent.
    """
    job_id = (result or {}).get("job_id")
    record = _host_job_record(job_id)
    if record is not None:
        context: Dict[str, Any] = {"project_id": str(record["project_id"])}
        if record.get("thread_id") is not None:
            context["thread_id"] = str(record["thread_id"])
        return context

    context = (result or {}).get("context") or {}
    if context.get("project_id"):
        logger.warning(
            "[music_projects] job %s was not recorded by the host; falling "
            "back to the context the service echoed",
            job_id,
        )
    return context


def _music_target_is_real(project_id: int, thread_id: Optional[int]) -> bool:
    """Whether the thread that would own the files actually exists.

    The project is the hard requirement -- an asset without one is not a
    row. The thread is attribution, and attribution that points at
    nothing should not cost the Artist their files. So a thread that is
    not there is dropped rather than allowed to fail the registration.
    """
    if thread_id is None:
        return True

    from guardian.db.models import ChatThread

    try:
        db = _media_db()
        with db.get_session() as session:
            return session.get(ChatThread, thread_id) is not None
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "[music_projects] could not check thread %s: %s", thread_id, exc
        )
        return False


def _register_artifacts_from(
    output: Dict[str, Any],
    context: Dict[str, Any],
    scope: Any,
) -> None:
    """Turn the produced files into the host's own asset rows.

    The service produced the files; the host owns how they are named and
    stored, so the registration happens here and not there. The context
    is the attribution the host resolved for the job -- its own record
    where there is one, the service's echo otherwise.

    A failure to register is logged and swallowed: the Artist's music
    exists either way, and a job that succeeded must not be reported as
    failed because a row could not be written.
    """
    artifacts = (output or {}).get("artifacts") or []
    if not artifacts:
        return

    raw_project_id = (context or {}).get("project_id")
    if not raw_project_id:
        logger.warning(
            "[music_projects] files were produced without a project; they "
            "will not be registered"
        )
        return

    try:
        project_id = int(raw_project_id)
    except (TypeError, ValueError):
        logger.warning("[music_projects] work carried a non-numeric project id")
        return

    thread_id = _thread_id_from_context(context or {})
    if thread_id is not None and not _music_target_is_real(project_id, thread_id):
        logger.warning(
            "[music_projects] thread %s is not there; registering the "
            "files against the project without it",
            thread_id,
        )
        thread_id = None

    user_id = getattr(scope, "user_id", None)
    try:
        registered = register_artifacts(
            artifacts,
            project_id=project_id,
            thread_id=thread_id,
            user_id=user_id,
        )
        logger.info(
            "[music_projects] registered %d artifact(s) against project %s",
            len(registered),
            project_id,
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning("[music_projects] failed to register artifacts: %s", exc)


# --------------------------------------------------------------------------
# Music Project state -- Codexify's own rows
# --------------------------------------------------------------------------


def _require_db():
    if chatlog_db is None:
        raise HTTPException(status_code=503, detail="database is not configured")
    return chatlog_db


def _serialise(row: Dict[str, Any]) -> Dict[str, Any]:
    """Make a database row safe to serialise as JSON.

    Timestamps come back as datetimes and the spec as a JSON string in
    some drivers; both need normalising before they can cross the wire.
    """
    payload = dict(row)
    for key in ("created_at", "updated_at"):
        value = payload.get(key)
        if value is not None and not isinstance(value, str):
            payload[key] = value.isoformat()
    spec = payload.get("current_spec")
    if isinstance(spec, str):
        import json

        try:
            payload["current_spec"] = json.loads(spec)
        except ValueError:
            payload["current_spec"] = None
    return payload


@router.get("/projects")
def list_music_projects(
    request_user_scope: RequestUserScope = Depends(get_request_user_scope),
):
    """Return every Music Project's musical state."""
    db = _require_db()
    try:
        rows = db.list_music_projects()
    except Exception as exc:
        logger.warning("[music_projects] failed to list music projects: %s", exc)
        raise HTTPException(status_code=500, detail="failed to list music projects")
    return [_serialise(row) for row in rows]


@router.get("/projects/{project_id}")
def get_music_project(
    project_id: int,
    request_user_scope: RequestUserScope = Depends(get_request_user_scope),
):
    """Return one Music Project's musical state.

    A project that has no musical state is not an error: it is an
    ordinary Project that has not been made into a Music Project yet.
    """
    db = _require_db()
    try:
        row = db.get_music_project(project_id)
    except Exception as exc:
        logger.warning(
            "[music_projects] failed to read music project %s: %s", project_id, exc
        )
        raise HTTPException(status_code=500, detail="failed to read music project")
    if row is None:
        raise HTTPException(status_code=404, detail="not a music project")
    return _serialise(row)


@router.put("/projects/{project_id}")
def put_music_project(
    project_id: int,
    body: MusicProjectState = Body(...),
    request_user_scope: RequestUserScope = Depends(get_request_user_scope),
):
    """Attach or replace a Music Project's musical state.

    The write is complete, not incremental: the values in ``body`` are
    the state, and anything omitted becomes null. That is what makes a
    revision a revision rather than an edit.
    """
    db = _require_db()
    try:
        row = db.upsert_music_project(
            project_id,
            bpm=body.bpm,
            musical_key=body.musical_key,
            musical_mode=body.musical_mode,
            bars=body.bars,
            time_signature=body.time_signature,
            length_seconds=body.length_seconds,
            library_path=body.library_path,
            current_spec=body.current_spec,
        )
    except Exception as exc:
        logger.warning(
            "[music_projects] failed to write music project %s: %s", project_id, exc
        )
        raise HTTPException(status_code=500, detail="failed to write music project")
    return _serialise(row)


@router.delete("/projects/{project_id}")
def delete_music_project(
    project_id: int,
    request_user_scope: RequestUserScope = Depends(get_request_user_scope),
):
    """Detach the musical state. The Project itself is untouched."""
    db = _require_db()
    try:
        removed = db.delete_music_project(project_id)
    except Exception as exc:
        logger.warning(
            "[music_projects] failed to delete music project %s: %s", project_id, exc
        )
        raise HTTPException(status_code=500, detail="failed to delete music project")
    if not removed:
        raise HTTPException(status_code=404, detail="not a music project")
    return {"project_id": project_id, "deleted": True}


def _media_db():
    """Return a database handle that can open a SQLAlchemy session.

    Media assets are rows, not raw SQL, so they need a SQLAlchemy
    session. The chatlog facade used elsewhere in this module speaks
    raw SQL and does not necessarily provide one, so the media database
    is resolved the way guardian/routes/media.py resolves it.
    """
    from guardian.core.db import GuardianDB, load_guardian_db_from_env

    resolved = load_guardian_db_from_env()
    if resolved is not None and hasattr(resolved, "get_session"):
        return resolved
    db_url = os.getenv("DATABASE_URL") or DEFAULT_PG_DSN
    return GuardianDB(db_url)


def register_artifacts(
    artifacts: List[Dict[str, Any]],
    *,
    project_id: int,
    thread_id: Optional[int] = None,
    user_id: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Register produced files as MediaAsset rows.

    The identity fields -- ``deterministic_id``, ``normalized_slug``,
    ``system_name``, ``storage_prefix`` -- are computed by Codexify's own
    ``media_identity`` service, not by the Producer. Agent-DAW knows what
    a file *is*; the host owns the rules for naming and storing it, and
    duplicating those rules would let them drift.

    Three things this has to get right, because each of them fails
    silently:

    - **The row survives.** The session is a plain SQLAlchemy Session:
      closing it rolls back anything uncommitted, so the row has to be
      committed here or it never existed.
    - **The identity is stable.** The host reads the bytes, so it hashes
      them itself. Trusting the Producer's hash would let a wrong hash
      become the row's identity, and two registrations of the same file
      would then become two rows.
    - **Registration is idempotent.** A job can be polled more than
      once. The second poll must reuse the row the first one wrote, not
      collide with it.

    One artifact that cannot be registered does not cost the Artist the
    others, so each is registered on its own.

    Returns one row per registered artifact, with the asset id.
    """
    from guardian.db.models import MediaAsset
    from guardian.services.media_identity import (
        compute_content_hash,
        compute_identity,
        find_existing_asset,
        utcnow,
    )

    if not artifacts:
        return []

    db = _media_db()
    registered: List[Dict[str, Any]] = []

    for artifact in artifacts:
        path = Path(str(artifact.get("path") or ""))
        if not path.exists():
            logger.warning("[music_projects] artifact is missing on disk: %s", path)
            continue

        media_kind = str(artifact.get("media_kind") or "other")
        if media_kind not in {"document", "image", "audio", "video", "other"}:
            media_kind = "other"
        provenance = str(artifact.get("provenance") or "generated")

        file_data = path.read_bytes()
        # The host owns the identity, so the host hashes the bytes it just
        # read. The Producer's hash is a claim about them; if it disagrees
        # with the bytes in front of us, the bytes win.
        content_hash = compute_content_hash(file_data)
        reported_hash = artifact.get("content_hash")
        if reported_hash and reported_hash != content_hash:
            logger.warning(
                "[music_projects] %s reported hash %s but hashes to %s; "
                "the host's own hash is the identity",
                path.name,
                str(reported_hash)[:12],
                content_hash[:12],
            )

        identity = compute_identity(
            file_data=file_data,
            media_kind=media_kind,
            provenance=provenance,
            human_label=path.stem,
            original_filename=path.name,
            mime_type=artifact.get("mime_type"),
            first_seen_at=utcnow(),
            content_hash=content_hash,
        )

        try:
            with db.get_session() as session:
                existing = find_existing_asset(
                    session,
                    project_id=project_id,
                    media_kind=media_kind,
                    provenance=provenance,
                    content_hash=content_hash,
                )
                if existing is not None:
                    # The same bytes are already this project's asset of
                    # this kind. The identity is the same fact, so this is
                    # the same row -- not a second one.
                    registered.append(
                        {
                            "asset_id": existing.id,
                            "role": artifact.get("role"),
                            "media_kind": media_kind,
                            "mime_type": artifact.get("mime_type"),
                            "bytes": artifact.get("bytes"),
                            "content_hash": content_hash,
                            "deterministic_id": existing.deterministic_id,
                            "system_name": existing.system_name,
                            "storage_prefix": existing.storage_prefix,
                        }
                    )
                    continue

                asset = MediaAsset(
                    id=str(uuid.uuid4()),
                    project_id=project_id,
                    thread_id=thread_id,
                    user_id=user_id,
                    media_kind=media_kind,
                    provenance=provenance,
                    source_tag="agentdaw",
                    content_hash=content_hash,
                    deterministic_id=identity.deterministic_id,
                    normalized_slug=identity.normalized_slug,
                    system_name=identity.system_name,
                    storage_prefix=identity.storage_prefix,
                    src_url=path.as_uri(),
                    mime_type=artifact.get("mime_type"),
                    filesize=artifact.get("bytes"),
                    # The column is NOT NULL with a flush-time default. Writing it
                    # explicitly means the row is complete the moment it is
                    # constructed, rather than depending on when the session
                    # happens to flush it.
                    import_lineage=[],
                )

                session.add(asset)
                session.flush()
                # Read the id while the session still holds the instance.
                # Committing expires the instance's attributes, and a
                # closed session cannot refresh them -- so reading it
                # afterwards raises instead of returning the id.
                asset_id = asset.id
                # The flush alone would let this function report a
                # registration that did not happen.
                session.commit()

                registered.append(
                    {
                        "asset_id": asset_id,
                        "role": artifact.get("role"),
                        "media_kind": media_kind,
                        "mime_type": artifact.get("mime_type"),
                        "bytes": artifact.get("bytes"),
                        "content_hash": content_hash,
                        "deterministic_id": identity.deterministic_id,
                        "system_name": identity.system_name,
                        "storage_prefix": identity.storage_prefix,
                    }
                )
        except Exception as exc:  # noqa: BLE001
            # The Artist's music exists whether or not a row was written,
            # and one file that will not register does not cost the
            # Artist the rest of the session.
            logger.warning(
                "[music_projects] could not register %s: %s",
                path.name,
                exc,
            )

    return registered
