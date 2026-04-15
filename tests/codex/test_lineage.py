from __future__ import annotations

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from guardian.codex.lineage import (
    CodexLineageRef,
    _set_session_factory,
    ensure_lineage_exists,
    normalize_front_matter,
    parse_lineage,
    reset_session_factory,
)


@pytest.fixture(autouse=True)
def _reset_lineage_state():
    reset_session_factory()
    yield
    reset_session_factory()


def _seed_lineage_db(
    db_path: str,
    *,
    thread_id: int,
    message_id: int | None = None,
) -> None:
    engine = create_engine(
        f"sqlite:///{db_path}",
        future=True,
        connect_args={"check_same_thread": False},
    )
    Session = sessionmaker(
        bind=engine, autoflush=False, autocommit=False, future=True
    )
    with Session() as session:
        session.execute(
            text("CREATE TABLE chat_threads (id INTEGER PRIMARY KEY)")
        )
        session.execute(
            text(
                """
                CREATE TABLE chat_messages (
                    id INTEGER PRIMARY KEY,
                    thread_id INTEGER NOT NULL
                )
                """
            )
        )
        session.execute(
            text("INSERT INTO chat_threads (id) VALUES (:thread_id)"),
            {"thread_id": thread_id},
        )
        if message_id is not None:
            session.execute(
                text(
                    "INSERT INTO chat_messages (id, thread_id) VALUES (:message_id, :thread_id)"
                ),
                {"message_id": message_id, "thread_id": thread_id},
            )
        session.commit()
    _set_session_factory(Session)


def test_parse_lineage_accepts_thread_only_lineage():
    lineage = parse_lineage(
        {
            "source_thread_id": "11",
            "source_message_id": None,
        }
    )

    assert lineage == CodexLineageRef(11, None)


def test_ensure_lineage_exists_accepts_thread_only_lineage(tmp_path):
    _seed_lineage_db(str(tmp_path / "lineage.db"), thread_id=11)

    ensure_lineage_exists(CodexLineageRef(11, None))


def test_ensure_lineage_exists_accepts_thread_and_message_lineage(
    tmp_path,
):
    _seed_lineage_db(str(tmp_path / "lineage.db"), thread_id=11, message_id=22)

    ensure_lineage_exists(CodexLineageRef(11, 22))


def test_parse_lineage_rejects_message_only_lineage():
    with pytest.raises(ValueError, match="source_thread_id is required"):
        parse_lineage({"source_message_id": 22})


def test_normalize_front_matter_preserves_null_message_lineage_and_metadata(
    tmp_path,
):
    _seed_lineage_db(str(tmp_path / "lineage.db"), thread_id=11)
    metadata = {
        "artifactKind": "retrieval_posture_diff_note",
        "pinned_posture": {
            "source_mode": "conversation",
            "boundary_label": "active_conversation_only",
            "retrieval_override_mode": "conversation",
            "widen_reason": "none",
            "conversation_only": True,
        },
    }

    normalized, lineage = normalize_front_matter(
        {
            "thread_id": 11,
            "source_message_id": None,
            "metadata": metadata,
        }
    )

    assert lineage == CodexLineageRef(11, None)
    assert normalized["source_thread_id"] == 11
    assert normalized["source_message_id"] is None
    assert normalized["thread_id"] == 11
    assert normalized["message_id"] is None
    assert normalized["metadata"] == metadata
