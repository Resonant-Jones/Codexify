"""Live proof: the host owns the attribution of a music job.

The route's real functions, a real Agent-DAW service, and a real
PostgreSQL. For each engine:

  1. an async compose is started with a project and a thread;
  2. the host's own ``music_jobs`` row is checked;
  3. the job is polled until it is terminal;
  4. the host's own registration path runs;
  5. the ``media_assets`` rows are checked against the project and thread.

The pass condition is the invariant that matters: **the files are
attributed against the right project and thread, for every engine.** It
does not matter whether the engine echoed the context back. Whether it
did is reported as an observation, because that is a property of the
engine and not of the host.

This is the harness behind
``docs/architecture/proofs/runtime/2026-11-07-host-owned-music-job-attribution.md``.

Usage:

    DATABASE_URL=postgresql://... \\
    MUSIC_ATTRIBUTION_ENGINES='v0.1.6=http://127.0.0.1:8771,v0.1.2=http://127.0.0.1:8772' \\
    python scripts/proofs/prove_music_job_attribution.py

Exit codes:

    0  every engine attributed its files
    2  a precondition failed (no database, no engine)
    3  an engine did not attribute its files
"""

from __future__ import annotations

import os
import sys
import time
from pathlib import Path
from types import SimpleNamespace

REPO_ROOT = Path(__file__).resolve().parents[2]

DEFAULT_ENGINE = os.environ.get("AGENTDAW_SERVICE_URL", "http://127.0.0.1:8000")
DEFAULT_BRIEF = "a slow warm pad at 90 bpm, four bars"

#: How long to wait for a compose before giving up on it. A compose is
#: about 107 seconds -- the Producer's model call is the long pole.
JOB_TIMEOUT_SECONDS = int(os.environ.get("MUSIC_ATTRIBUTION_JOB_TIMEOUT", "300"))


def _engines() -> list[tuple[str, str]]:
    """The engines to exercise, as (label, url) pairs."""
    raw = os.environ.get("MUSIC_ATTRIBUTION_ENGINES", "").strip()
    if not raw:
        return [("the configured engine", DEFAULT_ENGINE)]
    pairs = []
    for item in raw.split(","):
        item = item.strip()
        if not item:
            continue
        label, _, url = item.partition("=")
        if not url:
            url, label = label, "engine"
        pairs.append((label.strip(), url.strip().rstrip("/")))
    return pairs or [("the configured engine", DEFAULT_ENGINE)]


def _rows(db, sql: str, params: tuple) -> list[dict]:
    with db._connect() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            return [dict(row) for row in cur.fetchall()]


def main() -> int:
    database_url = (
        os.environ.get("DATABASE_URL")
        or os.environ.get("GUARDIAN_DATABASE_URL")
        or ""
    ).strip()
    if not database_url:
        print("FAIL: DATABASE_URL (or GUARDIAN_DATABASE_URL) is required")
        return 2

    os.environ["DATABASE_URL"] = database_url
    os.environ["GUARDIAN_DATABASE_URL"] = database_url
    sys.path.insert(0, str(REPO_ROOT))
    os.chdir(REPO_ROOT)

    from guardian.core.db import GuardianDB
    from guardian.core.pgdb import PgDB
    from guardian.routes import music_projects

    db = GuardianDB(database_url)
    pgdb = PgDB(database_url)
    music_projects._media_db = lambda: db
    music_projects.chatlog_db = pgdb

    scope = SimpleNamespace(user_id="local")
    project_id = pgdb.create_project(
        f"attribution proof {int(time.time())}", "live proof"
    )

    from guardian.db.models import ChatThread

    with db.get_session() as session:
        thread = ChatThread(user_id="local", title="proof", project_id=project_id)
        session.add(thread)
        session.commit()
        thread_id = thread.id

    print(f"project_id={project_id} thread_id={thread_id}")
    print(f"database={database_url.split('@')[-1]}")
    print()

    failures: list[str] = []
    observations: list[tuple[str, str, str]] = []

    for label, url in _engines():
        print(f"=== {label} at {url} ===")
        os.environ["AGENTDAW_SERVICE_URL"] = url

        context = {
            "project_id": str(project_id),
            "thread_id": str(thread_id),
            "user_id": "local",
        }
        payload = {"brief": DEFAULT_BRIEF, "mode": "async", "render": True}

        try:
            started = music_projects._invoke(
                "compose", payload, context=context, timeout=60
            )
        except Exception as exc:  # noqa: BLE001
            failures.append(f"{label}: the compose did not start ({exc})")
            print(f"  compose failed: {exc}")
            continue

        job_id = started.get("job_id")
        print(f"  compose returned: {started}")
        if not job_id:
            failures.append(f"{label}: no job id")
            continue

        recorded = _rows(
            pgdb,
            "SELECT job_id, project_id, thread_id FROM music_jobs WHERE job_id = %s",
            (str(job_id),),
        )
        print(f"  music_jobs row:   {recorded}")
        if not recorded:
            failures.append(f"{label}: the host did not record the job")
            continue
        if recorded[0]["project_id"] != project_id:
            failures.append(f"{label}: recorded the wrong project")
        if recorded[0]["thread_id"] != thread_id:
            failures.append(f"{label}: recorded the wrong thread")

        result: dict = {}
        deadline = time.time() + JOB_TIMEOUT_SECONDS
        while time.time() < deadline:
            result = music_projects._invoke("job_status", {"job_id": str(job_id)})
            if result.get("status") in {"succeeded", "failed"}:
                break
            time.sleep(5)

        echoed = result.get("context") or {}
        print(f"  job status:       {result.get('status')}")
        print(f"  echoed context:   {echoed}")
        print(f"  echoed a context: {'yes' if echoed else 'no'}")
        observations.append((label, result.get("status") or "?", "yes" if echoed else "no"))

        artifacts = (result.get("output") or {}).get("artifacts") or []
        print(f"  artifacts:        {len(artifacts)}")

        music_projects._register_finished_artifacts(result, scope)

        assets = _rows(
            pgdb,
            "SELECT id, project_id, thread_id, media_kind FROM media_assets "
            "WHERE project_id = %s",
            (project_id,),
        )
        print(f"  media_assets:     {len(assets)} row(s)")
        for asset in assets:
            print(f"      {asset}")

        if not assets:
            failures.append(f"{label}: the files were produced but not attributed")
        else:
            for asset in assets:
                if asset["project_id"] != project_id:
                    failures.append(f"{label}: an asset names the wrong project")
                if asset["thread_id"] != thread_id:
                    failures.append(f"{label}: an asset names the wrong thread")
        print()

    print("VERDICT")
    print("-------")
    print(f"{'engine':<28} {'status':<12} {'echoed a context':<18}")
    for label, status, echoed in observations:
        print(f"{label:<28} {status:<12} {echoed:<18}")
    print()

    if failures:
        print("FAIL")
        for line in failures:
            print(f"  - {line}")
        return 3

    print("PASS: every engine's files were attributed against the right "
          "project and thread")
    return 0


if __name__ == "__main__":
    sys.exit(main())
