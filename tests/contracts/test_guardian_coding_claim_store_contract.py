"""Mainline persistence authority only; no worker, adapter, or dispatch proof.

Requires disposable PostgreSQL explicitly supplied as TEST_DATABASE_URL. Missing
PostgreSQL is a failure, never a skip. Only the uniquely named test database is
created/migrated/dropped; the supplied database's schema is never modified.
"""

from __future__ import annotations

import os
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
from threading import Barrier
from types import SimpleNamespace
from uuid import uuid4

import psycopg
from psycopg import sql
import pytest
import sqlalchemy as sa
from alembic import command
from alembic.config import Config
from sqlalchemy.engine import make_url
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker

from guardian.agents.store import AgentStore
from guardian.db.models import (
    AgentDeployment,
    AgentRun,
    AgentRunArtifact,
    ChatMessage,
    ChatThread,
    Project,
    User,
)

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture(scope="module")
def postgres():
    base_url = os.environ.get("TEST_DATABASE_URL")
    if not base_url:
        pytest.fail("TEST_DATABASE_URL must identify task-owned disposable PostgreSQL")
    base = make_url(base_url)
    assert base.get_backend_name() == "postgresql"
    name = f"codexify_claim_store_{uuid4().hex[:12]}"
    admin = base.set(drivername="postgresql", database="postgres")
    url = base.set(drivername="postgresql+psycopg", database=name)
    with psycopg.connect(
        admin.render_as_string(hide_password=False), autocommit=True
    ) as conn:
        conn.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(name)))
    engine = sa.create_engine(url, pool_size=10)
    try:
        config = Config(str(ROOT / "backend/alembic.ini"))
        config.set_main_option("script_location", str(ROOT / "guardian/db/migrations"))
        config.set_main_option(
            "sqlalchemy.url",
            url.render_as_string(hide_password=False).replace("%", "%%"),
        )
        with pytest.MonkeyPatch.context() as patch:
            patch.setenv("DATABASE_URL", url.render_as_string(hide_password=False))
            patch.setenv(
                "GUARDIAN_DATABASE_URL", url.render_as_string(hide_password=False)
            )
            command.upgrade(config, "head")
        yield engine
    finally:
        engine.dispose()
        with psycopg.connect(
            admin.render_as_string(hide_password=False), autocommit=True
        ) as conn:
            conn.execute(
                "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = %s",
                (name,),
            )
            conn.execute(sql.SQL("DROP DATABASE {}").format(sql.Identifier(name)))


@pytest.fixture
def case(postgres):
    db = SimpleNamespace(
        get_session=sessionmaker(bind=postgres, expire_on_commit=False)
    )
    suffix = uuid4().hex[:12]
    with db.get_session() as session:
        uid = f"claim-account-{suffix}"
        session.add(User(id=uid, username=uid, password_hash="synthetic"))
        session.flush()
        project = Project(user_id=uid, name="Claim store proof")
        session.add(project)
        session.flush()
        thread = ChatThread(user_id=uid, title="Claim source", project_id=project.id)
        session.add(thread)
        session.flush()
        message = ChatMessage(
            thread_id=thread.id,
            user_id=uid,
            role="user",
            content="Synthetic task",
            kind="chat",
        )
        session.add(message)
        session.flush()
        identity = {
            "user_id": uid,
            "thread_id": thread.id,
            "source_message_id": message.id,
            "attempt_id": f"attempt-{suffix}",
            "coding_task_id": f"task-{suffix}",
        }
        spec = dict(identity, execution_binding=dict(identity))
        deployment = AgentDeployment(
            deployment_id=f"deployment-{suffix}",
            flow_id="coding",
            thread_id=thread.id,
            spec_json=spec,
            spec_hash="synthetic",
        )
        session.add(deployment)
        session.flush()
        run = AgentRun(
            run_id=f"run-{suffix}",
            deployment_id=deployment.id,
            account_origin_user_id=uid,
            thread_id=thread.id,
            status="queued",
        )
        session.add(run)
        session.commit()
        args = dict(
            identity,
            run_id=run.run_id,
            deployment_id=deployment.deployment_id,
            worker_instance_id=f"worker-{suffix}",
            claim_id=f"claim-{suffix}",
        )
    return SimpleNamespace(
        db=db,
        store=AgentStore(db),
        args=args,
        run_pk=run.id,
        deployment_pk=deployment.id,
    )


def state(case):
    with case.db.get_session() as session:
        row = session.get(AgentRun, case.run_pk)
        return {
            column.name: getattr(row, column.name)
            for column in AgentRun.__table__.columns
        }


def accept(case, **overrides):
    return case.store.claim_run_for_acceptance(**(case.args | overrides))


def heartbeat(case, **overrides):
    return case.store.renew_coding_run_heartbeat(
        **(
            {
                key: case.args[key]
                for key in ("run_id", "worker_instance_id", "claim_id")
            }
            | overrides
        )
    )


def terminal(case, session, **overrides):
    return case.store.claim_coding_run_terminal(
        session=session,
        **(
            {
                key: case.args[key]
                for key in ("run_id", "worker_instance_id", "claim_id")
            }
            | {"status": "succeeded"}
            | overrides
        ),
    )


def test_acceptance_is_durable_and_initial_heartbeat_uses_database_clock(
    case, monkeypatch
):
    # A wildly wrong host clock cannot affect persisted execution timestamps.
    monkeypatch.setattr(
        "guardian.agents.store._utc_now",
        lambda: datetime(2000, 1, 1, tzinfo=timezone.utc),
    )
    with case.db.get_session() as session:
        before = session.scalar(sa.select(sa.func.clock_timestamp()))
    assert accept(case) == "accepted"
    row = state(case)
    with case.db.get_session() as session:
        after = session.scalar(sa.select(sa.func.clock_timestamp()))
    assert row["status"] == "running"
    assert row["coding_worker_instance_id"] == case.args["worker_instance_id"]
    assert row["coding_worker_claim_id"] == case.args["claim_id"]
    assert (
        before <= row["started_at"] <= row["coding_worker_last_heartbeat_at"] <= after
    )
    assert row["ended_at"] is None
    assert case.store.get_run(case.args["run_id"])["status"] == "running"


def test_duplicate_acceptance_changes_nothing(case):
    assert accept(case) == "accepted"
    before = state(case)
    assert accept(case) == "rejected"
    assert accept(case, worker_instance_id="another", claim_id="another") == "rejected"
    assert state(case) == before


def test_concurrent_competing_claims_have_exactly_one_durable_winner(case):
    barrier = Barrier(8)

    def compete(index):
        barrier.wait(timeout=10)
        return index, accept(
            case,
            worker_instance_id=f"worker-{index}",
            claim_id=f"claim-{index}-{uuid4().hex}",
        )

    with ThreadPoolExecutor(max_workers=8) as pool:
        outcomes = list(pool.map(compete, range(8)))
    winners = [index for index, result in outcomes if result == "accepted"]
    assert len(winners) == 1
    assert [result for _, result in outcomes].count("rejected") == 7
    assert state(case)["coding_worker_instance_id"] == f"worker-{winners[0]}"


def test_started_at_is_write_once_even_on_historical_queued_row(case):
    original = datetime(2020, 1, 1, tzinfo=timezone.utc)
    with case.db.get_session() as session:
        session.get(AgentRun, case.run_pk).started_at = original
        session.commit()
    assert accept(case) == "accepted"
    assert state(case)["started_at"] == original
    assert heartbeat(case) == "renewed"
    assert state(case)["started_at"] == original


@pytest.mark.parametrize(
    "field,value",
    [
        ("user_id", "another-account"),
        ("thread_id", -1),
        ("source_message_id", -1),
        ("attempt_id", "another-attempt"),
        ("coding_task_id", "another-task"),
        ("deployment_id", "missing"),
        ("run_id", "missing"),
        ("user_id", None),
        ("thread_id", None),
        ("source_message_id", None),
        ("attempt_id", None),
        ("coding_task_id", None),
        ("worker_instance_id", ""),
        ("claim_id", ""),
        ("claim_id", "x" * 65),
    ],
)
def test_acceptance_refuses_missing_or_mismatched_identity(case, field, value):
    before = state(case)
    assert accept(case, **{field: value}) == "rejected"
    assert state(case) == before


@pytest.mark.parametrize(
    "field",
    [
        "user_id",
        "source_thread_id",
        "source_message_id",
        "attempt_id",
        "coding_task_id",
    ],
)
def test_conflicting_persisted_binding_assertions_are_refused(case, field):
    with case.db.get_session() as session:
        dep = session.get(AgentDeployment, case.deployment_pk)
        spec = dict(dep.spec_json)
        spec["execution_binding"] = dict(
            spec["execution_binding"], **{field: "conflict"}
        )
        dep.spec_json = spec
        session.commit()
    assert accept(case) == "rejected"
    assert state(case)["status"] == "queued"


@pytest.mark.parametrize(
    "field,value",
    [
        ("account_origin_user_id", "other"),
        ("account_origin_user_id", None),
        ("thread_id", None),
    ],
)
def test_missing_or_cross_account_canonical_run_lineage_is_refused(case, field, value):
    with case.db.get_session() as session:
        setattr(session.get(AgentRun, case.run_pk), field, value)
        session.commit()
    assert accept(case) == "rejected"


@pytest.mark.parametrize(
    "status", ["running", "succeeded", "failed", "canceled", "escalated"]
)
def test_acceptance_requires_queued(case, status):
    case.store.update_run_status(run_id=case.args["run_id"], status=status)
    before = state(case)
    assert accept(case) == "rejected"
    assert state(case) == before


def test_claim_id_is_unique_across_runs(case):
    assert accept(case) == "accepted"
    with case.db.get_session() as session:
        row = session.get(AgentRun, case.run_pk)
        other = AgentRun(
            run_id=f"other-{uuid4().hex}",
            deployment_id=row.deployment_id,
            thread_id=row.thread_id,
            account_origin_user_id=row.account_origin_user_id,
            status="queued",
        )
        session.add(other)
        session.commit()
        other_id = other.run_id
    assert accept(case, run_id=other_id) == "rejected"


def test_heartbeat_updates_only_activity_using_database_clock(case, monkeypatch):
    assert accept(case) == "accepted"
    before = state(case)
    monkeypatch.setattr(
        "guardian.agents.store._utc_now",
        lambda: datetime(2000, 1, 1, tzinfo=timezone.utc),
    )
    assert heartbeat(case) == "renewed"
    after = state(case)
    assert after.pop("coding_worker_last_heartbeat_at") > before.pop(
        "coding_worker_last_heartbeat_at"
    )
    assert after == before


@pytest.mark.parametrize(
    "overrides",
    [
        {"worker_instance_id": "wrong"},
        {"claim_id": "wrong"},
        {"claim_id": ""},
        {"run_id": "missing"},
    ],
)
def test_heartbeat_refuses_wrong_or_missing_claim(case, overrides):
    assert accept(case) == "accepted"
    before = state(case)
    assert heartbeat(case, **overrides) == "not_eligible"
    assert state(case) == before


@pytest.mark.parametrize("status", ["succeeded", "failed", "canceled", "escalated"])
def test_terminal_and_escalated_runs_refuse_heartbeat_and_late_completion(case, status):
    assert accept(case) == "accepted"
    case.store.update_run_status(run_id=case.args["run_id"], status=status)
    before = state(case)
    assert heartbeat(case) == "not_eligible"
    with case.db.get_session() as session:
        expected = (
            "terminal_rejected"
            if status == "escalated"
            else "terminal_already_terminal"
        )
        assert terminal(case, session) == expected
        session.commit()
    assert state(case) == before


@pytest.mark.parametrize("status", ["queued", "running", "succeeded"])
def test_historical_null_ownership_rows_remain_readable_and_cannot_be_taken_over(
    case, status
):
    case.store.update_run_status(run_id=case.args["run_id"], status=status)
    assert case.store.get_run(case.args["run_id"])["status"] == status
    assert heartbeat(case) == "not_eligible"
    with case.db.get_session() as session:
        assert terminal(case, session) == "terminal_rejected"
    assert accept(case) == ("accepted" if status == "queued" else "rejected")


def test_terminal_decision_and_canonical_results_commit_together(case):
    assert accept(case) == "accepted"
    before = state(case)
    with case.db.get_session() as session:
        cached = session.get(AgentRun, case.run_pk)
        assert terminal(case, session) == "terminal_accepted"
        assert cached.status == "succeeded"
        # A separate transaction sees no premature terminal commit.
        assert state(case) == before
        session.add(
            AgentRunArtifact(
                run_id=case.run_pk,
                artifact_type="coding_result",
                content_json={
                    "coding_task_id": case.args["coding_task_id"],
                    "result_json": {"status": "success"},
                },
            )
        )
        session.add(
            ChatMessage(
                thread_id=case.args["thread_id"],
                user_id=case.args["user_id"],
                role="assistant",
                content="Bounded result",
                kind="coding_result",
            )
        )
        session.commit()
    after = state(case)
    assert after["status"] == "succeeded" and after["ended_at"] is not None
    for key in (
        "started_at",
        "coding_worker_instance_id",
        "coding_worker_claim_id",
        "coding_worker_last_heartbeat_at",
    ):
        assert after[key] == before[key]
    assert len(case.store.list_coding_results(run_id=case.args["run_id"])) == 1


def test_failed_result_write_rolls_back_terminal_message_and_artifact(case):
    assert accept(case) == "accepted"
    before = state(case)
    with pytest.raises(IntegrityError):
        with case.db.get_session() as session:
            assert terminal(case, session) == "terminal_accepted"
            session.add(
                ChatMessage(
                    thread_id=case.args["thread_id"],
                    user_id=case.args["user_id"],
                    role="assistant",
                    content="Must roll back",
                    kind="coding_result",
                )
            )
            session.add(
                AgentRunArtifact(
                    run_id=case.run_pk, artifact_type="coding_result", content_json={}
                )
            )
            session.flush()
            # A real canonical-result FK violation after successful writes.
            session.add(
                AgentRunArtifact(
                    run_id=-1, artifact_type="coding_result", content_json={}
                )
            )
            session.commit()
    assert state(case) == before
    assert case.store.list_coding_results(run_id=case.args["run_id"]) == []
    with case.db.get_session() as session:
        assert (
            session.query(ChatMessage)
            .filter_by(thread_id=case.args["thread_id"], kind="coding_result")
            .count()
            == 0
        )
        assert terminal(case, session) == "terminal_accepted"
        session.rollback()
    assert state(case) == before


@pytest.mark.parametrize(
    "overrides",
    [
        {"worker_instance_id": "wrong"},
        {"claim_id": "stale"},
        {"run_id": "missing"},
        {"status": "running"},
        {"status": "queued"},
        {"status": "escalated"},
        {"status": "nonsense"},
        {"status": ""},
    ],
)
def test_terminal_refuses_stale_claims_and_nonterminal_outcomes_without_results(
    case, overrides
):
    assert accept(case) == "accepted"
    before = state(case)
    with case.db.get_session() as session:
        assert terminal(case, session, **overrides) == "terminal_rejected"
        session.commit()
    assert state(case) == before
    assert case.store.list_coding_results(run_id=case.args["run_id"]) == []


@pytest.mark.parametrize(
    "field",
    [
        "user_id",
        "source_thread_id",
        "source_message_id",
        "attempt_id",
        "coding_task_id",
    ],
)
def test_terminal_revalidates_all_persisted_binding_assertions(case, field):
    assert accept(case) == "accepted"
    with case.db.get_session() as session:
        dep = session.get(AgentDeployment, case.deployment_pk)
        spec = dict(dep.spec_json)
        spec["execution_binding"] = dict(
            spec["execution_binding"], **{field: "conflict"}
        )
        dep.spec_json = spec
        session.commit()
    before = state(case)
    with case.db.get_session() as session:
        assert terminal(case, session) == "terminal_rejected"
        session.commit()
    assert state(case) == before


def test_terminal_refreshes_cached_run_after_external_escalation(case):
    assert accept(case) == "accepted"
    with case.db.get_session() as session:
        cached = session.get(AgentRun, case.run_pk)
        assert cached.status == "running"
        case.store.update_run_status(run_id=case.args["run_id"], status="escalated")
        assert terminal(case, session) == "terminal_rejected"
        session.commit()
    assert state(case)["status"] == "escalated"


def test_competing_terminal_transactions_create_only_one_result(case):
    assert accept(case) == "accepted"
    barrier = Barrier(2)

    def finish(status):
        with case.db.get_session() as session:
            barrier.wait(timeout=10)
            outcome = terminal(case, session, status=status)
            if outcome == "terminal_accepted":
                session.add(
                    AgentRunArtifact(
                        run_id=case.run_pk,
                        artifact_type="coding_result",
                        content_json={"result_json": {"status": status}},
                    )
                )
            session.commit()
            return status, outcome

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(finish, ["succeeded", "failed"]))
    assert sorted(outcome for _, outcome in results) == [
        "terminal_accepted",
        "terminal_already_terminal",
    ]
    assert state(case)["status"] == next(
        status for status, outcome in results if outcome == "terminal_accepted"
    )
    assert len(case.store.list_coding_results(run_id=case.args["run_id"])) == 1


def test_superseded_worker_claim_cannot_renew_or_finalize(case):
    assert accept(case) == "accepted"
    with case.db.get_session() as session:
        row = session.get(AgentRun, case.run_pk)
        row.coding_worker_instance_id = "replacement-worker"
        row.coding_worker_claim_id = "replacement-claim"
        session.commit()
    before = state(case)
    assert heartbeat(case) == "not_eligible"
    with case.db.get_session() as session:
        assert terminal(case, session) == "terminal_rejected"
        session.commit()
    assert state(case) == before


@pytest.mark.parametrize("spec", [None, [], {"execution_binding": "malformed"}])
def test_malformed_deployment_lineage_is_refused(case, spec):
    with case.db.get_session() as session:
        session.get(AgentDeployment, case.deployment_pk).spec_json = spec
        session.commit()
    assert accept(case) == "rejected"


def test_queued_row_with_existing_owner_cannot_be_reassigned(case):
    with case.db.get_session() as session:
        row = session.get(AgentRun, case.run_pk)
        row.coding_worker_instance_id = "historical-owner"
        row.coding_worker_claim_id = "historical-claim"
        session.commit()
    before = state(case)
    assert accept(case) == "rejected"
    assert state(case) == before


def test_persistence_absence_and_failure_never_authorize_execution(case):
    class Unreachable:
        def get_session(self):
            raise OSError("synthetic persistence outage")

    for db in (None, Unreachable()):
        store = AgentStore(db)
        assert store.claim_run_for_acceptance(**case.args) == "unavailable"
        assert (
            store.renew_coding_run_heartbeat(
                run_id="x", worker_instance_id="w", claim_id="c"
            )
            == "unavailable"
        )
        assert (
            store.claim_coding_run_terminal(
                session=None,
                run_id="x",
                worker_instance_id="w",
                claim_id="c",
                status="succeeded",
            )
            == "terminal_unavailable"
        )
    assert state(case)["status"] == "queued"


def test_non_postgresql_session_is_not_claim_authority(case):
    # No SQLite database is used: a dialect-only stub proves refusal before SQL.
    class OtherSession:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def get_bind(self):
            return SimpleNamespace(dialect=SimpleNamespace(name="sqlite"))

    store = AgentStore(SimpleNamespace(get_session=OtherSession))
    assert store.claim_run_for_acceptance(**case.args) == "unavailable"
    assert (
        store.renew_coding_run_heartbeat(
            run_id="x", worker_instance_id="w", claim_id="c"
        )
        == "unavailable"
    )
    assert (
        store.claim_coding_run_terminal(
            session=OtherSession(),
            run_id="x",
            worker_instance_id="w",
            claim_id="c",
            status="succeeded",
        )
        == "terminal_unavailable"
    )
