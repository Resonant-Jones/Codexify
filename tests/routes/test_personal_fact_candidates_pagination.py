"""Real-PostgreSQL proof for the account-scoped Personal Fact candidate listing.

The candidate endpoint used to fetch at most 200 rows and then slice the
window in Python, so candidates beyond the first page were unreachable and
``total`` described the fetch window rather than the real population. These
tests drive the real router against a real migrated PostgreSQL database and
assert the contract that the endpoint now owes its callers.

The database is disposable: it is created from ``TEST_DATABASE_URL``, migrated
to head, and dropped again. No ambient runtime database is ever used.
"""

from __future__ import annotations

import os
import uuid
from typing import Any, Iterator

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from guardian.core.pgdb import PgDB
from tests.services.test_memory_vault_read_projection import (
    _admin_url,
    _create_disposable_database,
    _drop_database,
    _migrate_to_head,
)

ACCOUNT_A = "pfp01-account-a"
ACCOUNT_B = "pfp01-account-b"
API_KEY = "pfp01-test-api-key"

CANDIDATE_COUNT_A = 253
CANDIDATE_COUNT_B = 3
ARCHIVED_COUNT_A = 5
ARCHIVED_COUNT_B = 3

THREAD_ID = 4242
OTHER_THREAD_ID = 9999
THREAD_FACT_COUNT = 7


@pytest.fixture(scope="module")
def database_url() -> Iterator[str]:
    admin = _admin_url()
    name = f"pfp01_{uuid.uuid4().hex[:10]}"
    url = _create_disposable_database(admin, name)
    try:
        _migrate_to_head(url)
        yield url
    finally:
        _drop_database(admin, name)


@pytest.fixture(scope="module")
def seeded(database_url: str) -> dict[str, Any]:
    """Seed synthetic candidates and evidence for two account principals."""
    db = PgDB(database_url)
    a_ids: list[int] = []
    b_ids: list[int] = []

    for index in range(CANDIDATE_COUNT_A):
        a_ids.append(
            db.create_fact(
                ACCOUNT_A,
                f"probe_key_{index}",
                f"synthetic-value-{index}",
                status="candidate",
                confidence=0.5,
            )
        )
    for index in range(CANDIDATE_COUNT_B):
        b_ids.append(
            db.create_fact(
                ACCOUNT_B,
                f"probe_key_b{index}",
                f"synthetic-value-b{index}",
                status="candidate",
                confidence=0.5,
            )
        )

    # Pin every candidate to one timestamp so the ordering assertion has to be
    # satisfied by the secondary key rather than by insertion luck.
    from sqlalchemy import text

    with db._sa_session() as session:
        session.execute(
            text(
                "UPDATE personal_facts SET updated_at = CAST(:ts AS timestamptz) "
                "WHERE user_id IN (:a, :b)"
            ).bindparams(
                ts="2026-01-01T00:00:00+00:00", a=ACCOUNT_A, b=ACCOUNT_B
            )
        )
        session.commit()

    # Archived records. The normal archive path (guardian/core/db.py
    # deactivate_fact) sets status="archived" *and* is_active=False, so the
    # archived population is invisible to an active-only listing. These rows
    # are created outside the 253-candidate population so the candidate
    # regression is unaffected.
    archived_a_ids: list[int] = []
    archived_b_ids: list[int] = []
    for index in range(ARCHIVED_COUNT_A):
        archived_a_ids.append(
            db.create_fact(
                ACCOUNT_A,
                f"archived_key_{index}",
                f"synthetic-archived-value-{index}",
                status="candidate",
                confidence=0.5,
            )
        )
    for index in range(ARCHIVED_COUNT_B):
        archived_b_ids.append(
            db.create_fact(
                ACCOUNT_B,
                f"archived_key_b{index}",
                f"synthetic-archived-value-b{index}",
                status="candidate",
                confidence=0.5,
            )
        )

    from guardian.db.models import PersonalFact

    with db._sa_session() as session:
        for fact_id in archived_a_ids + archived_b_ids:
            fact = session.query(PersonalFact).filter_by(id=fact_id).first()
            fact.status = "archived"
            fact.is_active = False
            session.add(fact)
        session.commit()

    # Thread-scoped evidence on one archived fact of account A, so the
    # archived thread read can prove evidence attachment still works.
    db.add_fact_evidence(
        archived_a_ids[0],
        source_message_id=None,
        excerpt="synthetic excerpt",
        modality="text",
        confidence=0.5,
        source_type="user_stated",
        evidence_meta={"thread_id": THREAD_ID, "source": "chat"},
    )

    # Thread-scoped evidence for a subset of account A's candidates. One fact
    # receives two matching evidence rows to prove the filter cannot
    # duplicate a fact.
    for fact_id in a_ids[:THREAD_FACT_COUNT]:
        db.add_fact_evidence(
            fact_id,
            source_message_id=None,
            excerpt="synthetic excerpt",
            modality="text",
            confidence=0.5,
            source_type="user_stated",
            evidence_meta={"thread_id": THREAD_ID, "source": "chat"},
        )
    db.add_fact_evidence(
        a_ids[0],
        source_message_id=None,
        excerpt="synthetic excerpt",
        modality="text",
        confidence=0.5,
        source_type="user_stated",
        evidence_meta={"thread_id": THREAD_ID, "source": "chat", "second": True},
    )
    # One candidate is linked to a different thread and must not be included.
    db.add_fact_evidence(
        a_ids[-1],
        source_message_id=None,
        excerpt="synthetic excerpt",
        modality="text",
        confidence=0.5,
        source_type="user_stated",
        evidence_meta={"thread_id": OTHER_THREAD_ID, "source": "chat"},
    )

    return {
        "a_ids": a_ids,
        "b_ids": b_ids,
        "archived_a_ids": archived_a_ids,
        "archived_b_ids": archived_b_ids,
        "db": db,
    }


@pytest.fixture
def candidates_client(
    seeded: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> Iterator[TestClient]:
    """A client bound to the real router, the real database, and a test key."""
    from guardian.core import dependencies
    from guardian.routes import personal_facts

    monkeypatch.setattr(personal_facts, "chatlog_db", seeded["db"], raising=False)

    class _SettingsStub:
        GUARDIAN_API_KEY = API_KEY
        GUARDIAN_API_KEYS = ""

    monkeypatch.setattr(
        dependencies, "get_settings", lambda: _SettingsStub(), raising=False
    )
    monkeypatch.setenv("GUARDIAN_AUTH_MODE", "local")
    monkeypatch.setenv("GUARDIAN_EXPOSURE_MODE", "local_safe")
    monkeypatch.setenv("CODEXIFY_MULTI_USER_ENABLED", "false")

    app = FastAPI()
    app.include_router(personal_facts.router)
    app.include_router(personal_facts.router, prefix="/api")
    app.dependency_overrides[personal_facts.get_current_user] = lambda: ACCOUNT_A
    with TestClient(app) as client:
        client.headers.update({"X-API-Key": API_KEY})
        yield client


def _as(client: TestClient, account: str) -> TestClient:
    """Rebind the resolved account principal for the next request."""
    from guardian.routes import personal_facts

    client.app.dependency_overrides[personal_facts.get_current_user] = (
        lambda: account
    )
    return client


# ── Reachability ────────────────────────────────────────────────────────────


def test_candidates_route_returns_200(candidates_client: TestClient) -> None:
    """The literal /candidates route must not be shadowed by /{fact_id}."""
    response = candidates_client.get("/personal-facts/candidates")
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["ok"] is True
    # The default page size is 50; total describes the whole population.
    assert body["total"] == CANDIDATE_COUNT_A
    assert body["limit"] == 50
    assert body["offset"] == 0
    assert len(body["facts"]) == 50


def test_api_alias_behaves_consistently(candidates_client: TestClient) -> None:
    plain = candidates_client.get("/personal-facts/candidates")
    aliased = candidates_client.get("/api/personal-facts/candidates")
    assert plain.status_code == 200
    assert aliased.status_code == 200
    assert plain.json() == aliased.json()


def test_numeric_fact_id_route_still_works(
    candidates_client: TestClient, seeded: dict[str, Any]
) -> None:
    fact_id = seeded["a_ids"][0]
    response = candidates_client.get(f"/personal-facts/{fact_id}")
    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is True
    assert body["fact"]["id"] == fact_id


def test_debug_recent_route_still_works(candidates_client: TestClient) -> None:
    response = candidates_client.get("/personal-facts/candidates/debug/recent?limit=5")
    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is True
    assert len(body["facts"]) == 5


# ── Pagination truthfulness ─────────────────────────────────────────────────


def test_first_page_returns_200_records_and_full_total(
    candidates_client: TestClient,
) -> None:
    response = candidates_client.get(
        "/personal-facts/candidates?offset=0&limit=200"
    )
    assert response.status_code == 200
    body = response.json()
    assert len(body["facts"]) == 200
    assert body["total"] == CANDIDATE_COUNT_A
    assert body["limit"] == 200
    assert body["offset"] == 0


def test_second_page_returns_the_remaining_records(
    candidates_client: TestClient,
) -> None:
    response = candidates_client.get(
        "/personal-facts/candidates?offset=200&limit=200"
    )
    assert response.status_code == 200
    body = response.json()
    assert len(body["facts"]) == 53
    assert body["total"] == CANDIDATE_COUNT_A
    assert body["offset"] == 200


def test_pages_partition_the_candidate_set_exactly_once(
    candidates_client: TestClient,
) -> None:
    first = candidates_client.get(
        "/personal-facts/candidates?offset=0&limit=200"
    ).json()
    second = candidates_client.get(
        "/personal-facts/candidates?offset=200&limit=200"
    ).json()
    first_ids = [fact["id"] for fact in first["facts"]]
    second_ids = [fact["id"] for fact in second["facts"]]
    assert len(set(first_ids)) == len(first_ids)
    assert len(set(second_ids)) == len(second_ids)
    assert not set(first_ids) & set(second_ids)
    assert len(first_ids) + len(second_ids) == CANDIDATE_COUNT_A


def test_offset_past_the_end_returns_an_empty_page(
    candidates_client: TestClient,
) -> None:
    response = candidates_client.get(
        "/personal-facts/candidates?offset=253&limit=50"
    )
    assert response.status_code == 200
    body = response.json()
    assert body["facts"] == []
    assert body["total"] == CANDIDATE_COUNT_A


def test_total_is_independent_of_the_page_size(
    candidates_client: TestClient,
) -> None:
    small = candidates_client.get(
        "/personal-facts/candidates?offset=0&limit=1"
    ).json()
    large = candidates_client.get(
        "/personal-facts/candidates?offset=0&limit=200"
    ).json()
    assert small["total"] == large["total"] == CANDIDATE_COUNT_A
    assert len(small["facts"]) == 1


def test_limit_is_capped_at_200(candidates_client: TestClient) -> None:
    response = candidates_client.get("/personal-facts/candidates?limit=5000")
    assert response.status_code == 200
    body = response.json()
    assert body["limit"] == 200
    assert len(body["facts"]) == 200


def test_negative_offset_is_rejected(candidates_client: TestClient) -> None:
    response = candidates_client.get("/personal-facts/candidates?offset=-1")
    assert response.status_code == 422
    assert "offset" in response.text


# ── Deterministic ordering ──────────────────────────────────────────────────


def test_ordering_is_deterministic_for_an_unchanged_dataset(
    candidates_client: TestClient,
) -> None:
    first = candidates_client.get(
        "/personal-facts/candidates?offset=0&limit=200"
    ).json()
    second = candidates_client.get(
        "/personal-facts/candidates?offset=0&limit=200"
    ).json()
    assert [f["id"] for f in first["facts"]] == [f["id"] for f in second["facts"]]


def test_ordering_uses_updated_at_then_id_descending(
    candidates_client: TestClient, seeded: dict[str, Any]
) -> None:
    """Every seeded row shares one timestamp, so id DESC must decide."""
    body = candidates_client.get(
        "/personal-facts/candidates?offset=0&limit=200"
    ).json()
    ids = [fact["id"] for fact in body["facts"]]
    assert ids == sorted(ids, reverse=True)
    assert ids[0] == max(seeded["a_ids"])


# ── Thread-scoped filtering ─────────────────────────────────────────────────


def test_thread_filter_narrows_page_and_total(
    candidates_client: TestClient,
) -> None:
    response = candidates_client.get(
        f"/personal-facts/candidates?thread_id={THREAD_ID}&limit=200"
    )
    assert response.status_code == 200
    body = response.json()
    assert body["total"] == THREAD_FACT_COUNT
    assert len(body["facts"]) == THREAD_FACT_COUNT


def test_thread_filter_does_not_duplicate_facts(
    candidates_client: TestClient,
) -> None:
    body = candidates_client.get(
        f"/personal-facts/candidates?thread_id={THREAD_ID}&limit=200"
    ).json()
    ids = [fact["id"] for fact in body["facts"]]
    assert len(ids) == len(set(ids))


def test_thread_filter_attaches_matching_evidence(
    candidates_client: TestClient,
) -> None:
    body = candidates_client.get(
        f"/personal-facts/candidates?thread_id={THREAD_ID}&limit=200"
    ).json()
    for fact in body["facts"]:
        evidence = fact.get("_evidence")
        assert evidence is not None
        assert int(evidence["evidence_meta"]["thread_id"]) == THREAD_ID


def test_thread_filter_excludes_other_threads(
    candidates_client: TestClient,
) -> None:
    body = candidates_client.get(
        f"/personal-facts/candidates?thread_id={OTHER_THREAD_ID}&limit=200"
    ).json()
    assert body["total"] == 1


def test_thread_filter_pagination_is_truthful(
    candidates_client: TestClient,
) -> None:
    first = candidates_client.get(
        f"/personal-facts/candidates?thread_id={THREAD_ID}&offset=0&limit=3"
    ).json()
    second = candidates_client.get(
        f"/personal-facts/candidates?thread_id={THREAD_ID}&offset=3&limit=10"
    ).json()
    assert len(first["facts"]) == 3
    # The tail of the thread-scoped population must be reachable.
    assert len(second["facts"]) == THREAD_FACT_COUNT - 3
    assert first["total"] == second["total"] == THREAD_FACT_COUNT
    first_ids = {fact["id"] for fact in first["facts"]}
    second_ids = {fact["id"] for fact in second["facts"]}
    assert not first_ids & second_ids


# ── Archived facts ───────────────────────────────────────────────────────────
#
# Archival sets status="archived" AND is_active=False, so an active-only
# listing made the route's advertised archived status unobservable. Reading an
# archived fact must not activate, approve, or promote it.


def test_archived_status_returns_inactive_archived_facts(
    candidates_client: TestClient, seeded: dict[str, Any]
) -> None:
    body = candidates_client.get(
        "/personal-facts/candidates?status=archived&limit=200"
    ).json()
    assert body["ok"] is True
    assert body["total"] == ARCHIVED_COUNT_A
    assert len(body["facts"]) == ARCHIVED_COUNT_A
    archived_ids = set(seeded["archived_a_ids"])
    assert {fact["id"] for fact in body["facts"]} == archived_ids


def test_archived_records_stay_inactive_and_unpromoted(
    candidates_client: TestClient,
) -> None:
    body = candidates_client.get(
        "/personal-facts/candidates?status=archived&limit=200"
    ).json()
    assert body["facts"]
    for fact in body["facts"]:
        assert fact["status"] == "archived"
        assert fact["is_active"] is False


def test_reading_archived_facts_does_not_activate_them(
    candidates_client: TestClient, seeded: dict[str, Any]
) -> None:
    """A read must not change activation, status, or promotion state."""
    candidates_client.get(
        "/personal-facts/candidates?status=archived&limit=200"
    )
    db = seeded["db"]
    rows = db.list_facts(
        ACCOUNT_A, status="archived", active_only=False, limit=200
    )
    assert len(rows) == ARCHIVED_COUNT_A
    for row in rows:
        assert row["status"] == "archived"
        assert row["is_active"] is False


def test_archived_total_counts_the_archived_population(
    candidates_client: TestClient,
) -> None:
    body = candidates_client.get(
        "/personal-facts/candidates?status=archived&limit=1"
    ).json()
    # total must describe the whole archived population, not the page.
    assert body["total"] == ARCHIVED_COUNT_A
    assert len(body["facts"]) == 1


def test_default_candidate_read_excludes_archived_records(
    candidates_client: TestClient, seeded: dict[str, Any]
) -> None:
    body = candidates_client.get("/personal-facts/candidates?limit=200").json()
    assert body["total"] == CANDIDATE_COUNT_A
    archived_ids = set(seeded["archived_a_ids"])
    assert not {fact["id"] for fact in body["facts"]} & archived_ids


def test_other_status_filters_remain_unchanged(
    candidates_client: TestClient, seeded: dict[str, Any]
) -> None:
    archived_ids = set(seeded["archived_a_ids"])
    for status in ("candidate", "verified", "disputed"):
        body = candidates_client.get(
            f"/personal-facts/candidates?status={status}&limit=200"
        ).json()
        assert not {fact["id"] for fact in body["facts"]} & archived_ids
    body = candidates_client.get("/personal-facts/candidates?limit=200").json()
    assert not {fact["id"] for fact in body["facts"]} & archived_ids


def test_archived_api_alias_matches(
    candidates_client: TestClient,
) -> None:
    plain = candidates_client.get(
        "/personal-facts/candidates?status=archived&limit=200"
    ).json()
    aliased = candidates_client.get(
        "/api/personal-facts/candidates?status=archived&limit=200"
    ).json()
    assert plain == aliased


def test_account_b_cannot_list_account_as_archive(
    candidates_client: TestClient, seeded: dict[str, Any]
) -> None:
    _as(candidates_client, ACCOUNT_B)
    body = candidates_client.get(
        "/personal-facts/candidates?status=archived&limit=200"
    ).json()
    assert body["total"] == ARCHIVED_COUNT_B
    assert {fact["user_id"] for fact in body["facts"]} == {ACCOUNT_B}
    assert not {fact["id"] for fact in body["facts"]} & set(
        seeded["archived_a_ids"]
    )


def test_account_b_cannot_count_account_as_archive(
    candidates_client: TestClient,
) -> None:
    _as(candidates_client, ACCOUNT_B)
    body = candidates_client.get(
        "/personal-facts/candidates?status=archived&limit=1"
    ).json()
    assert body["total"] == ARCHIVED_COUNT_B
    assert body["total"] != ARCHIVED_COUNT_A


def test_archived_thread_read_attaches_correct_evidence(
    candidates_client: TestClient, seeded: dict[str, Any]
) -> None:
    body = candidates_client.get(
        f"/personal-facts/candidates?status=archived&thread_id={THREAD_ID}"
        "&limit=200"
    ).json()
    assert body["total"] == 1
    assert len(body["facts"]) == 1
    fact = body["facts"][0]
    assert fact["id"] == seeded["archived_a_ids"][0]
    assert fact["is_active"] is False
    assert fact["_evidence"]["evidence_meta"]["thread_id"] == THREAD_ID


def test_archived_thread_read_omits_facts_without_matching_evidence(
    candidates_client: TestClient, seeded: dict[str, Any]
) -> None:
    body = candidates_client.get(
        f"/personal-facts/candidates?status=archived&thread_id={OTHER_THREAD_ID}"
        "&limit=200"
    ).json()
    assert body["total"] == 0
    assert body["facts"] == []


# ── Account isolation ───────────────────────────────────────────────────────


def test_account_b_cannot_read_account_a_candidates(
    candidates_client: TestClient, seeded: dict[str, Any]
) -> None:
    _as(candidates_client, ACCOUNT_B)
    body = candidates_client.get("/personal-facts/candidates?limit=200").json()
    assert body["total"] == CANDIDATE_COUNT_B
    assert len(body["facts"]) == CANDIDATE_COUNT_B
    assert {fact["user_id"] for fact in body["facts"]} == {ACCOUNT_B}
    assert not set(fact["id"] for fact in body["facts"]) & set(seeded["a_ids"])


def test_account_b_cannot_count_account_a_candidates(
    candidates_client: TestClient,
) -> None:
    _as(candidates_client, ACCOUNT_B)
    body = candidates_client.get("/personal-facts/candidates?limit=200").json()
    assert body["total"] == CANDIDATE_COUNT_B
    assert body["total"] != CANDIDATE_COUNT_A


def test_account_b_cannot_read_an_account_a_fact(
    candidates_client: TestClient, seeded: dict[str, Any]
) -> None:
    _as(candidates_client, ACCOUNT_B)
    response = candidates_client.get(f"/personal-facts/{seeded['a_ids'][0]}")
    assert response.status_code == 404


# ── Empty population ────────────────────────────────────────────────────────


def test_empty_dataset_reports_total_zero(
    database_url: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    from guardian.core import dependencies
    from guardian.routes import personal_facts

    db = PgDB(database_url)
    monkeypatch.setattr(personal_facts, "chatlog_db", db, raising=False)

    class _SettingsStub:
        GUARDIAN_API_KEY = API_KEY
        GUARDIAN_API_KEYS = ""

    monkeypatch.setattr(
        dependencies, "get_settings", lambda: _SettingsStub(), raising=False
    )
    monkeypatch.setenv("GUARDIAN_AUTH_MODE", "local")
    monkeypatch.setenv("GUARDIAN_EXPOSURE_MODE", "local_safe")
    monkeypatch.setenv("CODEXIFY_MULTI_USER_ENABLED", "false")

    app = FastAPI()
    app.include_router(personal_facts.router)
    app.dependency_overrides[personal_facts.get_current_user] = (
        lambda: "pfp01-empty-account"
    )
    with TestClient(app) as client:
        client.headers.update({"X-API-Key": API_KEY})
        body = client.get("/personal-facts/candidates").json()
    assert body["ok"] is True
    assert body["facts"] == []
    assert body["total"] == 0


# ── Authorization ───────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_unauthorized_principal_is_denied(
    database_url: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    """No API key must not reach the candidate listing.

    The repository's root conftest injects a default ``X-API-Key`` into every
    ``TestClient``, so the absence of a credential is proven with a raw ASGI
    request that carries no such header.
    """
    import httpx

    from guardian.routes import personal_facts

    db = PgDB(database_url)
    monkeypatch.setattr(personal_facts, "chatlog_db", db, raising=False)
    monkeypatch.setenv("GUARDIAN_AUTH_MODE", "local")
    monkeypatch.setenv("GUARDIAN_EXPOSURE_MODE", "local_safe")
    monkeypatch.setenv("CODEXIFY_MULTI_USER_ENABLED", "false")

    app = FastAPI()
    app.include_router(personal_facts.router)
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(
        transport=transport, base_url="http://testserver"
    ) as raw:
        response = await raw.get("/personal-facts/candidates")
    assert response.status_code in (401, 403), response.text


def test_wrong_api_key_is_denied(candidates_client: TestClient) -> None:
    response = candidates_client.get(
        "/personal-facts/candidates", headers={"X-API-Key": "not-the-key"}
    )
    assert response.status_code in (401, 403), response.text


def test_the_test_key_is_not_a_real_credential() -> None:
    """Guard against a real credential being pasted into this module."""
    assert API_KEY == "pfp01-test-api-key"
    assert os.environ.get("GUARDIAN_API_KEY") != API_KEY
