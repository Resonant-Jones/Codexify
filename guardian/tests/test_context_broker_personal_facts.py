from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from guardian.context.broker import ContextBroker


def _fact(
    *,
    fact_id: int,
    key: str,
    value: str,
    status: str = "verified",
    is_active: bool = True,
) -> dict[str, object]:
    return {
        "id": fact_id,
        "user_id": "user-1",
        "key": key,
        "value": value,
        "status": status,
        "confidence": 0.9,
        "is_active": is_active,
    }


@pytest.fixture
def chatlog_db() -> AsyncMock:
    mock = AsyncMock()
    mock.last_messages = MagicMock(
        return_value=[{"id": 1, "role": "user", "content": "hello"}]
    )
    mock.get_chat_thread = MagicMock(
        return_value={"id": 1, "user_id": "user-1", "project_id": 11}
    )
    mock.get_connector_config = MagicMock(return_value=None)
    mock.list_facts = MagicMock(return_value=[])
    return mock


@pytest.fixture
def vector_store() -> MagicMock:
    mock = MagicMock()
    mock.search.return_value = []
    return mock


@pytest.fixture
def broker(chatlog_db: AsyncMock, vector_store: MagicMock) -> ContextBroker:
    return ContextBroker(
        chatlog_db=chatlog_db,
        vector_store=vector_store,
        memory_store=None,
        sensors=None,
    )


@pytest.mark.asyncio
@pytest.mark.parametrize("depth_mode", ["normal", "deep", "diagnostic"])
async def test_verified_personal_facts_are_included_in_non_conversation_context(
    broker: ContextBroker,
    chatlog_db: AsyncMock,
    depth_mode: str,
) -> None:
    verified_fact = _fact(
        fact_id=1,
        key="location",
        value="NYC",
    )
    chatlog_db.list_facts.return_value = [verified_fact]

    context, trace = await broker.assemble(
        thread_id=1,
        query="hello",
        depth_mode=depth_mode,
        user_id="user-1",
    )

    assert context["personal_facts"] == [verified_fact]
    assert [fact["id"] for fact in context["verified_personal_facts"]] == [1]
    assert trace["personal_facts_context"]["status"] == "contributed"
    assert trace["personal_facts_context"]["count"] == 1
    assert trace["personal_facts_context"]["included_ids"] == [1]
    chatlog_db.list_facts.assert_called_once_with(
        "user-1",
        status="verified",
        active_only=True,
        limit=12,
    )


@pytest.mark.asyncio
@pytest.mark.parametrize("depth_mode", ["normal", "shallow"])
async def test_verified_personal_facts_are_included_in_light_depths(
    broker: ContextBroker,
    chatlog_db: AsyncMock,
    depth_mode: str,
) -> None:
    chatlog_db.list_facts.return_value = [
        _fact(fact_id=1, key="location", value="NYC")
    ]

    context, trace = await broker.assemble(
        thread_id=1,
        query="hello",
        depth_mode=depth_mode,
        user_id="user-1",
    )

    assert context["personal_facts"] == [
        _fact(fact_id=1, key="location", value="NYC")
    ]
    assert [fact["id"] for fact in context["verified_personal_facts"]] == [1]
    assert trace["personal_facts_context"]["status"] == "contributed"
    assert trace["personal_facts_context"]["count"] == 1
    chatlog_db.list_facts.assert_called_once_with(
        "user-1",
        status="verified",
        active_only=True,
        limit=12,
    )


@pytest.mark.asyncio
async def test_non_verified_personal_facts_are_filtered_out(
    broker: ContextBroker,
    chatlog_db: AsyncMock,
) -> None:
    verified_fact = _fact(
        fact_id=1,
        key="location",
        value="NYC",
    )
    candidate_fact = _fact(
        fact_id=2,
        key="location",
        value="candidate-town",
        status="candidate",
    )
    disputed_fact = _fact(
        fact_id=3,
        key="occupation",
        value="disputed-role",
        status="disputed",
    )
    inactive_fact = _fact(
        fact_id=4,
        key="timezone",
        value="retired-zone",
        is_active=False,
    )
    chatlog_db.list_facts.return_value = [
        candidate_fact,
        disputed_fact,
        inactive_fact,
        verified_fact,
    ]

    context, trace = await broker.assemble(
        thread_id=1,
        query="hello",
        depth_mode="deep",
        user_id="user-1",
    )

    assert context["personal_facts"] == [verified_fact]
    assert trace["personal_facts_context"]["retrieved_count"] == 4
    assert trace["personal_facts_context"]["count"] == 1
    assert all(
        fact["status"] == "verified" and fact["is_active"] is True
        for fact in context["personal_facts"]
    )


@pytest.mark.asyncio
async def test_broker_assembly_fails_soft_when_no_personal_facts_exist(
    broker: ContextBroker,
    chatlog_db: AsyncMock,
) -> None:
    chatlog_db.list_facts.return_value = []

    context, trace = await broker.assemble(
        thread_id=1,
        query="hello",
        depth_mode="deep",
        user_id="user-1",
    )

    assert "personal_facts" not in context
    assert context["messages"] == [
        {"id": 1, "role": "user", "content": "hello"}
    ]
    assert trace["personal_facts_context"]["status"] == "attempted_no_hits"
    assert trace["personal_facts_context"]["reason"] == "no_verified_facts"
    assert trace["personal_facts_context"]["count"] == 0
