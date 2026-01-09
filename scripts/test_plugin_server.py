#!/usr/bin/env python
"""
Test Plugin Server
~~~~~~~~~~~~~~~~~~

A mock plugin server for testing the agent task worker's plugin routing.
Simulates a Codex-style plugin that echoes back prompts.

Usage:
    uvicorn scripts.test_plugin_server:app --port 8081
    # or
    python scripts/test_plugin_server.py
"""

import logging
from datetime import datetime

from fastapi import FastAPI, Request

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Test Plugin Server", version="1.0.0")


@app.post("/rpc")
async def rpc(request: Request):
    """
    RPC endpoint that simulates plugin behavior.

    Expects:
        {
            "action": "generate",
            "payload": {
                "prompt": "...",
                "thread_id": "..."
            }
        }

    Returns:
        {"result": "..."}
    """
    body = await request.json()
    action = body.get("action", "unknown")
    payload = body.get("payload", {})
    prompt = payload.get("prompt", "")
    thread_id = payload.get("thread_id", "unknown")

    logger.info(
        "📨 Received RPC: action=%s thread=%s prompt=%s",
        action,
        thread_id,
        prompt[:50] + "..." if len(prompt) > 50 else prompt,
    )

    # Simulate processing
    timestamp = datetime.now().isoformat()
    result = f"[Codex Plugin @ {timestamp}] Processed: {prompt}"

    logger.info("📤 Returning result (%d chars)", len(result))
    return {"result": result}


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "ok", "plugin": "codex-test"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8081)
