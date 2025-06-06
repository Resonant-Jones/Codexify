# tests/test_guardian_db.py

import os
import pytest
from guardian.core.db import GuardianDB

TEST_DB_PATH = "test_guardian.db"

@pytest.fixture
def db():
    # Setup: create a fresh DB file
    db = GuardianDB(TEST_DB_PATH)
    db.init_db()
    yield db
    # Teardown: remove the test db file
    if os.path.exists(TEST_DB_PATH):
        os.remove(TEST_DB_PATH)

def test_insert_and_history(db):
    db.insert_log(user_id="test", command="echo test", tag="unit", agent="pytest", timestamp="2025-01-01T00:00:00")
    history = db.get_history(limit=1, user_id="test")
    assert history, "No history found after insert"
    assert history[0][2] == "echo test"