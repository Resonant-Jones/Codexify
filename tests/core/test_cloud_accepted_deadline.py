"""Loopback HTTP bounds for every non-local accepted provider dispatch."""
from datetime import datetime, timedelta, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import threading
import time

import pytest

from guardian.core import ai_router
from guardian.core.config import Settings
from guardian.tasks.chat_deadline import (
    AcceptedChatTaskDeadlineExceeded, build_accepted_chat_task_deadline,
)

PROVIDERS = ["groq", "openai", "deepseek", "alibaba", "minimax"]


@pytest.fixture
def cloud_endpoint(monkeypatch):
    state = {"mode": "headers", "calls": 0, "closed": threading.Event()}

    class Handler(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"

        def log_message(self, *args):
            pass

        def do_POST(self):
            self.close_connection = True
            self.rfile.read(int(self.headers["Content-Length"]))
            state["calls"] += 1
            self.connection.settimeout(2)
            try:
                if state["mode"] == "headers":
                    if self.connection.recv(1) == b"":
                        state["closed"].set()
                elif state["mode"] == "success":
                    data = (
                        {"content": [{"type": "text", "text": "fixture reply"}]}
                        if self.path.endswith("/messages") else
                        {"choices": [{"message": {"content": "fixture reply"}}]}
                    )
                    payload = json.dumps(data).encode()
                    self.send_response(200)
                    self.send_header("Content-Type", "application/json")
                    self.send_header("Content-Length", str(len(payload)))
                    self.end_headers()
                    self.wfile.write(payload)
                    self.wfile.flush()
                else:
                    self.send_response(200)
                    self.send_header("Content-Length", "1000")
                    self.end_headers()
                    for _ in range(1000):
                        self.wfile.write(b" ")
                        self.wfile.flush()
                        time.sleep(.02)
            except (BrokenPipeError, ConnectionResetError):
                state["closed"].set()

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base = f"http://127.0.0.1:{server.server_port}"
    settings = Settings(_env_file=None, ALLOW_CLOUD_PROVIDERS=True, CODEXIFY_LOCAL_ONLY_MODE=False,
        GROQ_API_KEY="fixture", GROQ_BASE_URL=base,
        OPENAI_API_KEY="fixture", OPENAI_BASE_URL=base,
        DEEPSEEK_API_KEY="fixture", DEEPSEEK_BASE_URL=base,
        ALIBABA_API_KEY="fixture", ALIBABA_API_BASE=base,
        MINIMAX_API_KEY="fixture", MINIMAX_API_BASE=base)
    monkeypatch.setattr(ai_router, "assert_egress_allowed", lambda *args, **kwargs: None)
    monkeypatch.setattr(ai_router, "provider_routing_requires_discovered_inventory", lambda _: False)
    try:
        yield state, settings
    finally:
        server.shutdown()
        server.server_close()
        thread.join(2)


@pytest.mark.parametrize("provider", PROVIDERS)
@pytest.mark.parametrize("mode", ["headers", "body"])
def test_cloud_dispatch_cannot_outlive_accepted_work(cloud_endpoint, provider, mode):
    state, settings = cloud_endpoint
    state["mode"] = mode
    deadline = build_accepted_chat_task_deadline(
        datetime.now(timezone.utc) - timedelta(seconds=719.7),
    )
    started = time.monotonic()
    with pytest.raises(AcceptedChatTaskDeadlineExceeded):
        ai_router.chat_with_ai([{"role": "user", "content": "fixture"}],
            provider=provider, model="fixture-model", settings=settings, accepted_deadline=deadline)
    assert time.monotonic() - started < 1.5
    assert state["calls"] == 1
    assert state["closed"].wait(.75)
    assert not any(t.name == "accepted-chat-http" for t in threading.enumerate())


@pytest.mark.parametrize("provider", PROVIDERS)
def test_expired_cloud_dispatch_performs_no_http(cloud_endpoint, provider):
    state, settings = cloud_endpoint
    deadline = build_accepted_chat_task_deadline(
        datetime.now(timezone.utc) - timedelta(seconds=721),
    )
    with pytest.raises(AcceptedChatTaskDeadlineExceeded):
        ai_router.chat_with_ai([{"role": "user", "content": "fixture"}],
            provider=provider, model="fixture-model", settings=settings, accepted_deadline=deadline)
    assert state["calls"] == 0


@pytest.mark.parametrize("provider", PROVIDERS)
def test_cloud_success_preserves_provider_parsing(cloud_endpoint, provider):
    state, settings = cloud_endpoint
    state["mode"] = "success"
    deadline = build_accepted_chat_task_deadline(datetime.now(timezone.utc))
    result = ai_router.chat_with_ai(
        [{"role": "user", "content": "fixture"}], provider=provider,
        model="fixture-model", settings=settings, accepted_deadline=deadline,
    )
    assert ai_router.normalize_completion_output(result).text == "fixture reply"
    assert state["calls"] == 1
    assert not any(t.name == "accepted-chat-http" for t in threading.enumerate())
