# tests/test_auth.py
import os
import pytest
from fastapi.testclient import TestClient

# make sure this matches how you import your app
from guardian.guardian_api import app  

# pick up the same key your server uses
VALID_KEY = os.getenv("GUARDIAN_API_KEY", "invalid-by-default")

client = TestClient(app)

@pytest.mark.parametrize("path,method", [
    ("/chat", "post"),
    ("/chat/stream", "get"),
])
def test_requires_api_key(path, method):
    # 1) no header -> 401
    r = getattr(client, method)(path, json={"prompt": "hello"})
    assert r.status_code == 401, f"Unauthenticated {method.upper()} {path} should be 401"

    # 2) wrong key -> 401
    r = getattr(client, method)(
        path,
        headers={"X-API-Key": "wrong"},
        json={"prompt": "hello"}
    )
    assert r.status_code == 401, f"Bad-key {method.upper()} {path} should be 401"

    # 3) correct key -> not 401 (200/stream)
    if method == "post":
        r = client.post(
            path,
            headers={"X-API-Key": VALID_KEY},
            json={"prompt": "hello", "provider":"groq","model":"moonshotai/kimi-k2-instruct-0905"}
        )
        assert r.status_code == 200, f"Authenticated POST {path} should be 200, got {r.status_code}"
        data = r.json()
        assert "reply" in data
    else:
        # stream endpoint: we expect a streaming response
        r = client.get(
            path + "?prompt=hello&provider=groq&model=moonshotai%2Fkimi-k2-instruct-0905",
            headers={"X-API-Key": VALID_KEY},
            stream=True
        )
        assert r.status_code == 200, f"Authenticated GET {path} should be 200, got {r.status_code}"
        # read a few chunks to ensure it isn’t failing immediately
        chunks = list(r.iter_lines(chunk_size=1, decode_unicode=True))
        assert any(chunks), "Stream should yield at least one token"