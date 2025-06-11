import os
import tempfile
import shutil
import pytest

from guardian.core.db import GuardianDB

@pytest.fixture
def temp_db_path():
    temp_dir = tempfile.mkdtemp()
    db_path = os.path.join(temp_dir, "test_guardian_chat.db")
    yield db_path
    shutil.rmtree(temp_dir)

def test_chat_log_persistence(temp_db_path):
    db = GuardianDB(db_path=temp_db_path)
    session_id = "pytest-session"
    user_id = "test-user"

    # Simulate adding chat messages
    messages = [
        ("user", "Hello, Axis!"),
        ("assistant", "Welcome, Resonant. How can I help?"),
        ("user", "What’s the weather on Mars?"),
        ("assistant", "Dusty, as usual.")
    ]

    for role, message in messages:
        db.add_chat_log(
            session_id=session_id,
            user_id=user_id,
            role=role,
            message=message,
            response=None,
            backend="test-backend"
        )

    # Retrieve history and assert correct
    history = db.get_chat_history(session_id=session_id, user_id=user_id, limit=10)
    assert len(history) == 4
    assert history[0]['message'] == "Dusty, as usual."
    assert history[0]['role'] == "assistant"
    assert history[1]['message'] == "What’s the weather on Mars?"
    assert history[1]['role'] == "user"
    assert history[2]['message'] == "Welcome, Resonant. How can I help?"
    assert history[2]['role'] == "assistant"
    assert history[3]['message'] == "Hello, Axis!"
    assert history[3]['role'] == "user"

def test_chat_history_order(temp_db_path):
    db = GuardianDB(db_path=temp_db_path)
    session_id = "pytest-session"
    user_id = "test-user"
    messages = [
        ("user", "One"),
        ("assistant", "Two"),
        ("user", "Three"),
        ("assistant", "Four"),
    ]
    for role, message in messages:
        db.add_chat_log(
            session_id=session_id,
            user_id=user_id,
            role=role,
            message=message,
            response=None,
            backend="test-backend"
        )
    history = db.get_chat_history(session_id=session_id, user_id=user_id, limit=10)
    assert [m['message'] for m in history] == ["Four", "Three", "Two", "One"]

# Optional: if you have a summary method, test it too!
# def test_chat_summary(temp_db_path):
#     db = GuardianDB(db_path=temp_db_path)
#     session_id = "pytest-session"
#     user_id = "test-user"
#     # Add enough messages...
#     for i in range(10):
#         db.add_chat_log(
#             session_id=session_id,
#             user_id=user_id,
#             role="user" if i % 2 == 0 else "assistant",
#             message=f"msg {i}",
#             response=None,
#             backend="test-backend"
#         )
#     summary = db.summarize_chat(session_id=session_id)
#     assert isinstance(summary, str)
#     assert "summary" in summary.lower()
