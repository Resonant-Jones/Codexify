"""Mutation check: the attribution tests bite.

A test that passes with and without the fix proves nothing. This
harness applies each mutation to the real source in turn and asserts
that the test which names it fails.

It restores every file it touches from a byte-verified backup, whether
the mutation was caught or not, so the working tree is left as it was
found.

Usage:

    DATABASE_URL=postgresql://... \\
    python scripts/proofs/mutate_music_attribution_tests.py

Exit codes:

    0  every mutation was caught
    3  a mutation was not caught, or a mutation could not be applied
    2  a precondition failed (no database, no pytest)
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]

ROUTE = REPO_ROOT / "guardian/routes/music_projects.py"
PGDB = REPO_ROOT / "guardian/core/pgdb.py"

TEST_MODULE = "tests/routes/test_music_projects.py"

# (label, file, original, replacement, the test that must fail)
MUTATIONS: list[tuple[str, Path, str, str, str]] = [
    (
        "the host never records the attribution",
        ROUTE,
        """    output = body.get("output") or {}
    # A job handle is minted here, and this is the one place the host
    # knows what it belongs to. Recording it now is what lets the
    # attribution survive an engine that does not echo the context back.
    _record_job_attribution(output, context)
    return output""",
        """    output = body.get("output") or {}
    return output""",
        f"{TEST_MODULE}::test_the_host_records_which_project_a_job_belongs_to",
    ),
    (
        "the poll reads only the context the service echoed",
        ROUTE,
        """    job_id = (result or {}).get("job_id")
    record = _host_job_record(job_id)
    if record is not None:""",
        """    job_id = (result or {}).get("job_id")
    record = None
    if record is not None:""",
        f"{TEST_MODULE}::test_a_service_that_echoes_nothing_still_gets_its_files_attributed",
    ),
    (
        "the echoed context wins over the host's record",
        ROUTE,
        """    job_id = (result or {}).get("job_id")
    record = _host_job_record(job_id)
    if record is not None:""",
        """    job_id = (result or {}).get("job_id")
    record = None
    if record is not None:""",
        f"{TEST_MODULE}::test_the_hosts_own_record_wins_over_what_the_service_echoed",
    ),
    (
        "a later record moves the job",
        PGDB,
        """                    ON CONFLICT (job_id) DO NOTHING
                    RETURNING job_id, project_id, thread_id, created_at""",
        """                    ON CONFLICT (job_id) DO UPDATE SET
                        project_id = EXCLUDED.project_id,
                        thread_id = EXCLUDED.thread_id
                    RETURNING job_id, project_id, thread_id, created_at""",
        f"{TEST_MODULE}::test_a_job_is_not_moved_by_a_later_record",
    ),
    (
        "a refused record write fails the compose",
        ROUTE,
        """    try:
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
        )""",
        """    db.record_music_job(
        str(job_id),
        project_id=project_id,
        thread_id=_thread_id_from_context(context),
    )""",
        f"{TEST_MODULE}::test_a_record_that_cannot_be_written_does_not_cost_the_files",
    ),
]


def _environment() -> dict[str, str]:
    env = dict(os.environ)
    for name in ("DATABASE_URL", "GUARDIAN_DATABASE_URL", "TEST_DATABASE_URL"):
        value = env.get(name, "").strip()
        if value:
            env[name] = value
    return env


def main() -> int:
    database_url = (
        os.environ.get("TEST_DATABASE_URL")
        or os.environ.get("DATABASE_URL")
        or ""
    ).strip()
    if not database_url:
        print("FAIL: TEST_DATABASE_URL (or DATABASE_URL) is required")
        return 2

    backup = Path(tempfile.mkdtemp(prefix="attribution-mutation-"))
    for path in (ROUTE, PGDB):
        shutil.copy(path, backup / path.name)

    def restore() -> None:
        for path in (ROUTE, PGDB):
            shutil.copy(backup / path.name, path)

    failures: list[str] = []
    try:
        for label, path, original, replacement, test in MUTATIONS:
            text = path.read_text(encoding="utf-8")
            if original not in text:
                failures.append(f"could not apply the mutation: {label}")
                print(f"!! could not apply: {label}")
                continue

            path.write_text(text.replace(original, replacement, 1), encoding="utf-8")
            try:
                result = subprocess.run(
                    [sys.executable, "-m", "pytest", "-q", "--disable-warnings", test],
                    cwd=REPO_ROOT,
                    env=_environment(),
                    capture_output=True,
                    text=True,
                )
            finally:
                restore()

            caught = result.returncode != 0
            print(f"{label}: {'caught' if caught else 'NOT CAUGHT'}")
            if not caught:
                failures.append(f"the test did not bite: {label} -> {test}")
                print(result.stdout[-2000:])
    finally:
        restore()
        shutil.rmtree(backup, ignore_errors=True)

    print()
    if failures:
        print("FAIL")
        for line in failures:
            print(f"  - {line}")
        return 3

    print(f"PASS: every mutation was caught by the test that names it")
    return 0


if __name__ == "__main__":
    sys.exit(main())
