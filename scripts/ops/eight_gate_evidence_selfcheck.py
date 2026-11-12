#!/usr/bin/env python3
"""Self-checks for the eight-gate evidence harness.

These checks do not need a running stack. They verify the harness's own
behaviour: that every gate reads the surface the rubric names, that each gate
returns the verdict its rubric clause calls for under a known set of durable
observations, that credentials are never printed, and that the refusal cases
fail closed.

Run:

    /Volumes/Dev_SSD/Codexify-main/.venv/bin/python \\
        scripts/ops/eight_gate_evidence_selfcheck.py
"""

from __future__ import annotations

import ast
import datetime as dt
import json
import sys
import tempfile
import time
from pathlib import Path
from typing import Any, Mapping, Sequence

sys.path.insert(0, str(Path(__file__).resolve().parent))

import eight_gate_evidence as G  # noqa: E402
from eight_gate_runtime import (  # noqa: E402
    HttpResponse,
    Secret,
    BrowserDriver,
    HttpClient,
    parse_env_file,
)

FAILURES: list[str] = []
CHECKS = 0


def check(condition: Any, label: str) -> None:
    global CHECKS
    CHECKS += 1
    if not condition:
        FAILURES.append(label)
        print(f"  FAIL  {label}")
    else:
        print(f"  ok    {label}")


def eq(actual: Any, expected: Any, label: str) -> None:
    check(actual == expected, f"{label} (got {actual!r}, expected {expected!r})")


# ---------------------------------------------------------------------------
# Fakes
# ---------------------------------------------------------------------------


class FakePg:
    """A PostgreSQL reader that answers from a canned table map."""

    def __init__(self, tables: Mapping[str, Sequence[Mapping[str, Any]]] | None = None):
        self.tables = dict(tables or {})
        self.dsn = Secret("DATABASE_URL", "")

    def query(self, sql: str, params: Sequence[Any] = ()) -> list[dict[str, Any]]:
        for needle, rows in self.tables.items():
            if needle in sql:
                return [dict(row) for row in rows]
        return []

    def query_one(self, sql: str, params: Sequence[Any] = ()) -> dict[str, Any] | None:
        rows = self.query(sql, params)
        return rows[0] if rows else None


class FakeRedis:
    """A Redis reader that answers LLEN/GET/TTL from a script."""

    def __init__(
        self,
        depths: Mapping[str, int] | None = None,
        values: Mapping[str, str | None] | None = None,
        chat_sequence: Sequence[int] | None = None,
    ):
        self.depths = dict(depths or {})
        self.values = dict(values or {})
        self.chat_sequence = list(chat_sequence or [])
        self.index = 0

    def llen(self, key: str) -> int:
        if key == G.CHAT_COMPLETION_QUEUE and self.chat_sequence:
            value = (
                self.chat_sequence[self.index]
                if self.index < len(self.chat_sequence)
                else self.chat_sequence[-1]
            )
            self.index += 1
            return value
        return int(self.depths.get(key, 0))

    def get(self, key: str) -> str | None:
        return self.values.get(key)

    def ttl(self, key: str) -> int:
        return 45

    def ping(self) -> bool:
        return True


class FakeHttp:
    """An HTTP client that answers from a canned route map."""

    def __init__(self, responses: Mapping[str, HttpResponse] | None = None):
        self.responses = dict(responses or {})

    def post(self, path: str, **kwargs: Any) -> HttpResponse:
        if path.endswith("/threads"):
            return HttpResponse(status=200, body={"id": 1}, raw="{}")
        return self.responses.get(
            path,
            HttpResponse(
                status=200,
                body={"task_id": "t1", "request_id": "req1", "acceptance_status": "accepted"},
                raw="{}",
            ),
        )

    def get(self, path: str, **kwargs: Any) -> HttpResponse:
        return self.responses.get(path, HttpResponse(status=404, body=None, raw=""))


class FakePage:
    """A browser page that replays a canned DOM."""

    def __init__(self, messages: Sequence[str], authors: Sequence[str]):
        self.messages = list(messages)
        self.authors = list(authors)
        self.version = "141.0.7390.37"
        self.page = self
        self.reload_count = 0

    def goto(self, *args: Any, **kwargs: Any) -> None:
        pass

    def reload(self, *args: Any, **kwargs: Any) -> None:
        self.reload_count += 1

    def all_inner_texts(self, selector: str) -> list[str]:
        if "author" in selector:
            return list(self.authors)
        return list(self.messages)

    def viewport_info(self) -> dict[str, Any]:
        return {
            "viewport": {"width": 1440, "height": 900},
            "device_pixel_ratio": 1,
            "user_agent": "HeadlessChrome/141.0.7390.37",
        }

    def wait_for_timeout(self, _seconds: float) -> None:
        pass


class FakeBrowser:
    """A browser driver that replays a canned DOM."""

    def __init__(self, messages: Sequence[str] = (), authors: Sequence[str] = ()):
        self.messages = list(messages)
        self.authors = list(authors)

    def available(self) -> tuple[bool, str]:
        return True, "141.0.7390.37"

    def open(self, url: str, *, session_token: str | None = None) -> Any:
        outer = self

        class _Session:
            def __enter__(self) -> FakePage:
                return FakePage(outer.messages, outer.authors)

            def __exit__(self, *exc: Any) -> None:
                pass

        return _Session()


def make_harness(
    *,
    tables: Mapping[str, Sequence[Mapping[str, Any]]] | None = None,
    redis: FakeRedis | None = None,
    http: Any | None = None,
    browser: Any | None = None,
    env: Mapping[str, Secret] | None = None,
    settle_seconds: float = 2.0,
) -> G.Harness:
    options = G.build_parser().parse_args(
        [
            "--env-file",
            "unused",
            "--compose-project",
            "unused",
            "--out",
            "unused",
            "--gate1-settle-seconds",
            str(settle_seconds),
        ]
    )
    return G.Harness(
        env=dict(env or {}),
        compose_project="unused",
        base_url="http://127.0.0.1:1",
        frontend_url="http://127.0.0.1:1",
        postgres=FakePg(tables),
        redis=redis or FakeRedis(),
        http=http or FakeHttp(),
        browser=browser or FakeBrowser(),
        options=options,
    )


# ---------------------------------------------------------------------------
# Checks
# ---------------------------------------------------------------------------


def check_env_parsing() -> None:
    print("env parsing")
    with tempfile.TemporaryDirectory() as workspace:
        path = Path(workspace) / "sample.env"
        path.write_text(
            "# a comment\n"
            "PLAIN=value\n"
            "export EXPORTED=other\n"
            "QUOTED='quoted value'\n"
            "DOUBLE=\"double value\"\n"
            "EMPTY=\n"
            "UNSET=<not-provided>\n",
            encoding="utf-8",
        )
        values = parse_env_file(path)
        eq(values.get("PLAIN"), "value", "plain value")
        eq(values.get("EXPORTED"), "other", "exported value")
        eq(values.get("QUOTED"), "quoted value", "single-quoted value")
        eq(values.get("DOUBLE"), "double value", "double-quoted value")
        eq(values.get("EMPTY"), "", "empty value")
        check("UNSET" not in values, "an unset placeholder is not read as a value")


def check_secret_hygiene() -> None:
    print("credential hygiene")
    secret = Secret("GUARDIAN_API_KEY", "super-secret-value")
    check("super-secret-value" not in repr(secret), "repr does not leak the value")
    check("super-secret-value" not in str(secret), "str does not leak the value")
    check(secret.fingerprint().startswith("sha256:"), "a fingerprint identifies the key")
    check("super-secret-value" not in secret.fingerprint(), "the fingerprint omits the value")

    payload = {"token": "abc", "nested": {"api_key": "def", "keep": "visible"}}
    redacted = G.redact(payload)
    eq(redacted["token"], "<redacted>", "a token is redacted")
    eq(redacted["nested"]["api_key"], "<redacted>", "a nested api key is redacted")
    eq(redacted["nested"]["keep"], "visible", "a non-credential value survives")


def check_gate_names_and_order() -> None:
    print("gate set")
    eq(
        [name for name, _ in G.GATES],
        list(G.GATE_NAMES),
        "the harness covers the rubric's eight gates in rubric order",
    )
    eq(len(G.GATES), 8, "there are eight gates")


def check_queue_key_names() -> None:
    print("queue and heartbeat key names")
    for key in (
        "codexify:queue:chat-embed",
        "codexify:queue:coding-execution",
        "codexify:queue:document-embed",
        "codexify:queue:account-import",
    ):
        check(key in G.RUBRIC_QUEUE_KEYS, f"the rubric's queue {key} is observed")
    check(
        G.CHAT_COMPLETION_QUEUE == "codexify:queue:chat",
        "the chat completion queue is the one the completion route enqueues on",
    )
    eq(
        list(G.HEARTBEAT_KEYS),
        ["codexify:worker:chat:heartbeat", "codexify:worker:voice:heartbeat"],
        "the two heartbeat keys that exist are the two observed",
    )


def check_deadline_gate() -> None:
    print("deadline gate")
    now = dt.datetime.now(dt.timezone.utc)
    future = (now + dt.timedelta(seconds=300)).isoformat()
    past = (now - dt.timedelta(seconds=60)).isoformat()

    def attempt(request_id: str, deadline: str, terminal: str | None = None) -> dict:
        return G._normalize_attempt(
            {
                "request_id": request_id,
                "backend_task_id": "t",
                "thread_id": 1,
                "turn_id": "u",
                "accepted_at": now.isoformat(),
                "terminal_event_type": terminal,
                "terminal_outcome": None,
                "deadline_snapshot": {
                    "accepted_at": now.isoformat(),
                    "work_deadline_at": deadline,
                    "terminal_deadline_at": deadline,
                },
                "turn_lock_token": "token",
                "completed_message_id": None,
                "created_at": now.isoformat(),
            }
        )

    passed = G.gate_deadline(
        make_harness(
            tables={
                "chat_completion_attempts": [
                    attempt("r1", future),
                    attempt("r2", past, terminal="task.failed"),
                ]
            }
        )
    )
    eq(passed.verdict, G.VERDICT_PASS, "a snapshot plus a past-deadline terminal attempt is PASS")

    unproven = G.gate_deadline(
        make_harness(tables={"chat_completion_attempts": [attempt("r1", future)]})
    )
    eq(unproven.verdict, G.VERDICT_UNPROVEN, "a snapshot alone is UNPROVEN")
    check(
        any("terminal_deadline_at" in item for item in unproven.missing),
        "the UNPROVEN verdict names the missing past-deadline observation",
    )


def check_lock_gate() -> None:
    print("lock gate")
    absent = G.gate_lock(
        make_harness(tables={"uq_agent_runs_coding_worker_claim_id": []})
    )
    eq(absent.verdict, G.VERDICT_FAIL, "an absent unique constraint is FAIL")

    present = G.gate_lock(
        make_harness(
            tables={
                "uq_agent_runs_coding_worker_claim_id": [
                    {
                        "conname": "uq_agent_runs_coding_worker_claim_id",
                        "definition": "UNIQUE (coding_worker_claim_id)",
                        "contype": "u",
                    }
                ]
            }
        )
    )
    eq(present.verdict, G.VERDICT_UNPROVEN, "the constraint alone, with no run to claim, is UNPROVEN")
    eq(
        present.observed["unique_constraint"]["is_unique"],
        True,
        "the constraint is recorded as unique",
    )


def _parse_revision_source(tree: ast.AST) -> tuple[str | None, list[str]]:
    """Return the (revision, down_revisions) a migration module declares."""
    revision: str | None = None
    downs: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            targets = [t.id for t in node.targets if isinstance(t, ast.Name)]
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            targets = [node.target.id]
        else:
            continue
        if "revision" in targets:
            try:
                value = ast.literal_eval(node.value)
            except (ValueError, SyntaxError):
                value = None
            if isinstance(value, str):
                revision = value
        if "down_revision" in targets:
            try:
                value = ast.literal_eval(node.value)
            except (ValueError, SyntaxError):
                value = None
            if isinstance(value, str):
                downs = [value]
            elif isinstance(value, (list, tuple)):
                downs = [v for v in value if isinstance(v, str)]
    return revision, downs


def _head_from_graph(revisions: Mapping[str, Sequence[str]]) -> dict[str, Any]:
    """The single head of a revision graph, or none when there is not one.

    A revision is a head when no other revision descends from it. A graph
    with two heads has no single head, and that is reported as such rather
    than resolved by picking one.
    """
    children: set[str] = set()
    for downs in revisions.values():
        children.update(downs)
    heads = sorted(set(revisions) - children)
    return {
        "head": heads[0] if len(heads) == 1 else None,
        "heads": heads,
        "revisions": len(revisions),
    }


def _source_level_head(versions_dir: Path | None = None) -> dict[str, Any]:
    """Compute the checkout's single Alembic head from the migration source.

    This is deliberately independent of ``eight_gate_evidence``'s own
    ``_read_checkout_head``. Two independent reasons:

    * It must not take the harness's answer as the expected value. A harness
      that computed the wrong head would then agree with itself and the check
      would pass.
    * It must not pin a literal revision. A pinned revision goes stale at the
      next migration and turns the check into a false failure -- which is
      exactly what happened: the check reported 53/54 with a stale expected
      revision while the harness under test was reading the real head
      correctly.

    So the head is read here, straight from the migration files' own
    ``revision`` and ``down_revision`` declarations, with no Alembic and no
    ``alembic.ini``: the revision that no other revision descends from.

    ``versions_dir`` exists so a proof can point this at another graph.
    """
    versions = versions_dir or (
        Path(__file__).resolve().parents[2]
        / "guardian"
        / "db"
        / "migrations"
        / "versions"
    )
    revisions: dict[str, list[str]] = {}
    for path in sorted(versions.glob("*.py")):
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"))
        except (OSError, SyntaxError):
            continue
        revision, downs = _parse_revision_source(tree)
        if revision:
            revisions[revision] = downs
    return _head_from_graph(revisions)


def check_migration_gate() -> None:
    print("migration gate")
    mismatched = G.gate_migration_deployment(
        make_harness(tables={"alembic_version": [{"version_num": "not-the-head"}]})
    )
    eq(mismatched.verdict, G.VERDICT_FAIL, "a live revision that is not the checkout head is FAIL")

    expected = _source_level_head()
    head = expected.get("head")
    if not isinstance(head, str) or len(head) != 12:
        check(
            False,
            "the evaluated checkout's single head is computed from its source "
            f"(could not be computed from the migration source: {expected})",
        )
        return

    matched = G.gate_migration_deployment(
        make_harness(tables={"alembic_version": [{"version_num": head}]})
    )
    eq(
        matched.observed["live_alembic_version"]["row_count"],
        1,
        "the live revision is read directly out of PostgreSQL",
    )
    eq(
        matched.observed["evaluated_checkout_head"]["head"],
        head,
        "the evaluated checkout's single head is computed from its source",
    )
    eq(
        len(matched.observed["evaluated_checkout_head"]["heads"]),
        1,
        "the checkout has exactly one head",
    )
    refusals = matched.observed["refusal_cases"]
    eq(len(refusals), 3, "all three refusal cases are exercised")
    check(
        all(case["refused"] for case in refusals),
        "every refusal case fails closed",
    )
    check(
        all(not case["migration_applied"] for case in refusals),
        "no refusal case applied a migration",
    )


def check_graceful_stop_gate() -> None:
    print("graceful-stop gate")
    handler = G._read_coding_worker_handler()
    check(handler["present"], "the coding worker's shutdown handler is readable")
    check(handler["registers_sigterm"], "the shutdown handler registers SIGTERM")
    check(handler["registers_sigint"], "the shutdown handler registers SIGINT")

    idle = G.gate_graceful_stop(make_harness())
    eq(
        idle.verdict,
        G.VERDICT_UNPROVEN,
        "a worker stopped while idle is UNPROVEN, not a pass",
    )
    check(
        any("claim" in item for item in idle.missing),
        "the UNPROVEN verdict names the missing claimed run",
    )


def check_browser_gate() -> None:
    print("browser gate")
    unavailable = G.gate_browser(make_harness(browser=FakeBrowser()))
    eq(
        unavailable.verdict,
        G.VERDICT_UNPROVEN,
        "no authenticated account session leaves the browser gate UNPROVEN",
    )
    check(
        any("session" in item for item in unavailable.missing),
        "the UNPROVEN verdict names the missing account session",
    )

    projected = G.gate_browser(
        make_harness(
            tables={
                "FROM chat_messages": [
                    {
                        "thread_id": 7,
                        "title": "T",
                        "message_id": 1,
                        "role": "user",
                        "content": "MARKER-XYZ",
                    }
                ]
            },
            browser=FakeBrowser(["MARKER-XYZ"], ["Guardian"]),
            env={"EIGHT_GATE_SESSION_TOKEN": Secret("t", "token")},
        )
    )
    eq(projected.verdict, G.VERDICT_PASS, "a matching DOM is PASS")
    check(
        projected.observed["browser"]["version"],
        "the browser version is recorded",
    )
    check(
        "device_pixel_ratio" in projected.observed["browser"],
        "the device pixel ratio is recorded",
    )

    mismatched = G.gate_browser(
        make_harness(
            tables={
                "FROM chat_messages": [
                    {
                        "thread_id": 7,
                        "title": "T",
                        "message_id": 1,
                        "role": "user",
                        "content": "MARKER-XYZ",
                    }
                ]
            },
            browser=FakeBrowser(["SOMETHING-ELSE"], ["Guardian"]),
            env={"EIGHT_GATE_SESSION_TOKEN": Secret("t", "token")},
        )
    )
    eq(mismatched.verdict, G.VERDICT_FAIL, "a DOM that disagrees with the durable state is FAIL")


def check_import_recall_gate() -> None:
    print("import-recall gate")
    empty = G.gate_import_recall(make_harness())
    eq(empty.verdict, G.VERDICT_UNPROVEN, "no import job leaves the gate UNPROVEN")
    check(
        any("export" in item.lower() for item in empty.missing),
        "the UNPROVEN verdict names the missing real provider export",
    )

    job = {
        "id": "job-1",
        "user_id": "local",
        "source_system": "openai",
        "source_export_fingerprint": "f" * 64,
        "status": "completed",
        "total_file_count": 1,
        "total_byte_count": 10,
        "uploaded_file_count": 1,
        "uploaded_byte_count": 10,
        "imported_thread_count": 1,
        "imported_message_count": 2,
        "imported_media_count": 0,
        "failure_count": 0,
        "error_details": [],
        "checkpoint": {"conversation_ids": ["c1"]},
        "staged_manifest": [],
        "created_at": None,
        "completed_at": None,
    }
    thread = {
        "thread_id": 3,
        "user_id": "local",
        "project_id": 2,
        "origin_system": "openai",
        "title": "Imported",
        "message_count": 2,
    }
    populated = G.gate_import_recall(
        make_harness(
            tables={
                "openai_account_import_jobs": [job],
                "origin_system IN ('openai', 'anthropic')": [thread],
            }
        )
    )
    eq(
        populated.observed["materialisation_checkpoint"],
        {"conversation_ids": ["c1"]},
        "the durable materialisation checkpoint is observed",
    )
    eq(
        populated.verdict,
        G.VERDICT_UNPROVEN,
        "without the real export file the natural/synthetic classification is unevidenced",
    )


def check_scope_isolation_gate() -> None:
    print("scope-isolation gate")
    one_account = G.gate_scope_isolation(
        make_harness(
            env={"EIGHT_GATE_ACCOUNT_A_SESSION": Secret("t", "token-a")}
        )
    )
    eq(
        one_account.verdict,
        G.VERDICT_UNPROVEN,
        "one account leaves the gate UNPROVEN",
    )
    check(
        any("two" in item.lower() for item in one_account.missing),
        "the UNPROVEN verdict names the missing second account",
    )


def check_queue_worker_gate() -> None:
    print("queue/worker gate")
    now = dt.datetime.now(dt.timezone.utc).isoformat()
    attempt_row = {
        "request_id": "req1",
        "backend_task_id": "t1",
        "thread_id": 1,
        "turn_id": "u",
        "accepted_at": now,
        "terminal_event_type": None,
        "terminal_outcome": None,
        "deadline_snapshot": {"terminal_deadline_at": now},
        "turn_lock_token": "token",
        "completed_message_id": 7,
        "created_at": now,
    }
    heartbeat = json.dumps(
        {"worker": "chat", "status": "idle", "ts": int(time.time())}
    )
    passed = G.gate_queue_worker(
        make_harness(
            tables={"chat_completion_attempts": [attempt_row]},
            redis=FakeRedis(
                chat_sequence=[0, 3, 2, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
                values={"codexify:worker:chat:heartbeat": heartbeat},
            ),
        )
    )
    eq(passed.verdict, G.VERDICT_PASS, "a non-zero depth then zero, with a fresh heartbeat, is PASS")

    never = G.gate_queue_worker(
        make_harness(
            tables={"chat_completion_attempts": [attempt_row]},
            redis=FakeRedis(
                chat_sequence=[0] * 40,
                values={"codexify:worker:chat:heartbeat": heartbeat},
            ),
        )
    )
    eq(
        never.verdict,
        G.VERDICT_UNPROVEN,
        "a depth that was never observed non-zero is UNPROVEN, not a pass",
    )


def check_browser_binary() -> None:
    print("browser binary")
    available, detail = BrowserDriver().available()
    if available:
        check(bool(detail), "a real browser launches and reports its version")
    else:
        check(True, f"no browser is available here ({detail}); the gate reports UNPROVEN")


def main() -> int:
    print("eight-gate evidence harness self-check")
    print()
    check_env_parsing()
    print()
    check_secret_hygiene()
    print()
    check_gate_names_and_order()
    print()
    check_queue_key_names()
    print()
    check_queue_worker_gate()
    print()
    check_deadline_gate()
    print()
    check_graceful_stop_gate()
    print()
    check_lock_gate()
    print()
    check_migration_gate()
    print()
    check_browser_gate()
    print()
    check_import_recall_gate()
    print()
    check_scope_isolation_gate()
    print()
    check_browser_binary()
    print()
    print(f"{CHECKS - len(FAILURES)}/{CHECKS} checks passed")
    if FAILURES:
        for failure in FAILURES:
            print(f"  failed: {failure}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
