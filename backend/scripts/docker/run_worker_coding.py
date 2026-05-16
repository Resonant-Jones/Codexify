from __future__ import annotations

import http.client
import http.server
import os
import signal
import subprocess
import sys
import threading
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from common import log, wait_for_tcp

_TARGET_HOST = os.getenv("OLLAMA_PROXY_TARGET_HOST", "host.docker.internal")
_TARGET_PORT = int(os.getenv("OLLAMA_PROXY_TARGET_PORT", "11434"))
_BIND_HOST = os.getenv("OLLAMA_PROXY_BIND_HOST", "127.0.0.1")
_BIND_PORT = int(os.getenv("OLLAMA_PROXY_BIND_PORT", "11434"))

_HOP_BY_HOP_HEADERS = {
    "connection",
    "content-length",
    "keep-alive",
    "proxy-authenticate",
    "proxy-authorization",
    "te",
    "trailers",
    "transfer-encoding",
    "upgrade",
}


class _OllamaProxyHandler(http.server.BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def _forward(self) -> None:
        content_length = int(self.headers.get("Content-Length") or 0)
        body = self.rfile.read(content_length) if content_length else None
        headers = {
            key: value
            for key, value in self.headers.items()
            if key.lower() not in {"host", *_HOP_BY_HOP_HEADERS}
        }
        conn = http.client.HTTPConnection(
            _TARGET_HOST,
            _TARGET_PORT,
            timeout=60,
        )
        try:
            conn.request(
                self.command,
                self.path,
                body=body,
                headers=headers,
            )
            resp = conn.getresponse()
            payload = resp.read()
            self.send_response(resp.status)
            for key, value in resp.getheaders():
                if key.lower() in _HOP_BY_HOP_HEADERS:
                    continue
                self.send_header(key, value)
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)
        finally:
            conn.close()

    do_GET = _forward
    do_POST = _forward
    do_PUT = _forward
    do_PATCH = _forward
    do_DELETE = _forward
    do_OPTIONS = _forward

    def log_message(self, format: str, *args: object) -> None:  # noqa: A003
        return


def _start_proxy() -> http.server.ThreadingHTTPServer:
    server = http.server.ThreadingHTTPServer(
        (_BIND_HOST, _BIND_PORT),
        _OllamaProxyHandler,
    )
    thread = threading.Thread(
        target=server.serve_forever,
        name="ollama-proxy",
        daemon=True,
    )
    thread.start()
    wait_for_tcp(_BIND_HOST, _BIND_PORT, timeout_s=10)
    return server


def main() -> int:
    server = _start_proxy()
    worker_cmd = [sys.executable, "-m", "guardian.workers.coding_worker"]
    log(
        "worker-coding",
        (
            "Launching coding worker with localhost Ollama bridge "
            f"{_BIND_HOST}:{_BIND_PORT} -> {_TARGET_HOST}:{_TARGET_PORT}"
        ),
    )

    worker = subprocess.Popen(worker_cmd, env=os.environ.copy())

    def _shutdown(_signum: int, _frame: object) -> None:
        if worker.poll() is None:
            worker.terminate()
        server.shutdown()

    signal.signal(signal.SIGTERM, _shutdown)
    signal.signal(signal.SIGINT, _shutdown)

    try:
        return worker.wait()
    finally:
        _shutdown(signal.SIGTERM, None)
        server.server_close()


if __name__ == "__main__":
    raise SystemExit(main())
