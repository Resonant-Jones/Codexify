Preflight: git status --porcelain -uall must be empty

If preflight is not empty, STOP and run exactly:
- git status --porcelain -uall
- git stash push -u -m "preflight-TASK-2026-02-16-002"
- git status --porcelain -uall

# TASK-2026-02-16-002  Admin auth boundary and cookie hardening
- Risk: HIGH
- Findings: FINDING-2026-02-16-009
- Allowed files:
  - guardian/routes/admin.py
  - tests/routes/test_admin.py
  - .env.template
  - README.md
- Dependencies/Prereqs:
  - command -v rg
  - command -v pytest
  - test -n "${GUARDIAN_API_KEY:-}"
- Command checklist:
  1. rg -n "DEBUG_MODE|secure=False|GUARDIAN_ADMIN_TOKEN" guardian/routes/admin.py .env.template README.md
  2. Constrain/remove unconditional DEBUG admin bypass (explicit local opt-in only).
  3. Make cookie security flags environment-aware with secure defaults.
  4. Set docs/template default to DEBUG=false.
  5. pytest -q tests/routes/test_admin.py
- Scope guard:
  - git diff --name-only
  - If any changed file is outside Allowed files, STOP and run exactly:
    - git restore --staged --worktree -- .
    - git clean -fd
    - git status --porcelain -uall
- Expected outputs:
  - No ambient DEBUG admin bypass.
  - No hardcoded secure=False cookie.
  - tests/routes/test_admin.py exits 0.
- Rollback / cleanup commands:
  - git restore --staged --worktree -- guardian/routes/admin.py tests/routes/test_admin.py .env.template README.md
  - git status --porcelain -uall

## Runner Receipt (Start)

- Campaign: CAMPAIGN_2026_02_16_SECURITY_MVP_FOLLOWUP_EXECUTION

- Task ID: TASK-2026-02-16-002

- Head before: 0a2c08d3dbf5e9a7080e86865cb18a1d441d87aa


## Completion Summary (Runner)

- Status: failed

- Summary: (runner error)

- Head before: 0a2c08d3dbf5e9a7080e86865cb18a1d441d87aa

- Implementation commit hash: (none)

- Receipt update commit hash: (pending)

- Notes: codex exec failed
STDERR:
OpenAI Codex v0.101.0 (research preview)
--------
workdir: /Users/resonant_jones/Keep/Resonant_Constructs/Codexify
model: gpt-5.3-codex
provider: openai
approval: never
sandbox: workspace-write [workdir, /tmp, $TMPDIR]
reasoning effort: xhigh
reasoning summaries: auto
session id: 019c6535-a2ff-7643-aa25-6c9a626f77f7
--------
user
Preflight: git status --porcelain -uall must be empty
If dirty, STOP and run: git status --porcelain -uall && git stash push -u -m "preflight-TASK-2026-02-16-002" && git status --porcelain -uall
Implement TASK-2026-02-16-002: Admin auth boundary and cookie hardening.
Allowed files only:
- guardian/routes/admin.py
- tests/routes/test_admin.py
- .env.template
- README.md
Run required validations:
- pytest -q tests/routes/test_admin.py
- rg -n "DEBUG=true|secure=False|GUARDIAN_ADMIN_TOKEN" guardian/routes/admin.py .env.template README.md
Scope guard: git diff --name-only; if any out-of-scope file appears, run git restore --staged --worktree -- . && git clean -fd && git status --porcelain -uall, then STOP.
mcp: playwright starting
2026-02-16T06:48:59.961154Z ERROR codex_core::rollout::list: state db missing rollout path for thread 019c631d-6c3e-7c20-922f-e404437b953a
mcp: playwright ready
mcp startup: ready: playwright

thinking
**Acknowledging user request and planning**
codex
{"status":"success","summary":"Running the preflight sequence first: I’ll check `git status --porcelain -uall`, and if the tree is dirty I’ll stash exactly as specified before making any edits.","tests_ran":[],"commit_hash":"","implementation_commit_hash":"","receipt_update_commit_hash":"","notes":""}

thinking
**Clarifying response format choice**
exec
/bin/zsh -lc 'git status --porcelain -uall' in /Users/resonant_jones/Keep/Resonant_Constructs/Codexify succeeded in 53ms:


thinking
**Planning code inspection**
codex
{"status":"success","summary":"Preflight check is clean, so I’m proceeding to inspect `guardian/routes/admin.py`, its tests, and docs/env entries to implement the auth boundary and cookie hardening within the allowed files.","tests_ran":[],"commit_hash":"","implementation_commit_hash":"","receipt_update_commit_hash":"","notes":""}

thinking
**Planning parallel file reads**
exec
/bin/zsh -lc "sed -n '1,260p' .env.template" in /Users/resonant_jones/Keep/Resonant_Constructs/Codexifyexec
/bin/zsh -lc "sed -n '1,260p' guardian/routes/admin.py" in /Users/resonant_jones/Keep/Resonant_Constructs/Codexifyexec
/bin/zsh -lc "sed -n '1,320p' tests/routes/test_admin.py" in /Users/resonant_jones/Keep/Resonant_Constructs/Codexify succeeded in 51ms:
# .env.template / .env.example
# Local-only environment configuration. Copy to .env and edit.
# Never commit your real .env. Templates are the source of truth.
#
# Security hygiene:
# - .env is ignored via .gitignore: keep it local-only.
# - Rotate GUARDIAN_API_KEY regularly; prefer short-lived tokens.
# - Never ship VITE_GUARDIAN_API_KEY in any hosted/public build.

# --- Core runtime ---
ENV=development
LOG_LEVEL=INFO
DEBUG=true
PORT=8000

# --- Auth boundary ---
# local  -> static X-API-Key auth is allowed (localhost/dev only)
# remote -> static API keys are rejected; session/JWT is required
GUARDIAN_AUTH_MODE=local
# Backend auth secret. Use a long random value and rotate frequently.
 succeeded in 51ms:
"""
Admin Routes
~~~~~~~~~~~~

Diagnostic and administrative endpoints including health checks,
session token management, and configuration debugging.

Admin-protected endpoints require:
- X-Admin-Token header matching GUARDIAN_ADMIN_TOKEN, OR
- DEBUG=true environment variable (development only)
"""

import logging
import os
import secrets
from typing import Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Response
from pydantic import BaseModel

 succeeded in 51ms:
"""
Test suite for admin-protected endpoints.

Tests authentication, authorization, and access control for admin routes.
"""

from __future__ import annotations

import os
from typing import Any, Dict
from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException


class TestRequireAdminFunction:
    """Test the require_admin dependency function directly."""

    def test_require_admin_with_valid_admin_token(self, monkeypatch):

thinking
**Planning deeper test and README review**
codex
{"status":"success","summary":"I’ve loaded the current admin route and tests. Next I’m scanning the rest of `tests/routes/test_admin.py` and `README.md` to map current behavior and update docs/env consistently.","tests_ran":[],"commit_hash":"","implementation_commit_hash":"","receipt_update_commit_hash":"","notes":""}

thinking
**Switching commentary to plain text**
exec
/bin/zsh -lc "sed -n '320,720p' tests/routes/test_admin.py" in /Users/resonant_jones/Keep/Resonant_Constructs/Codexifyexec
/bin/zsh -lc 'rg -n "admin|GUARDIAN_ADMIN_TOKEN|session/cookie|DEBUG" README.md' in /Users/resonant_jones/Keep/Resonant_Constructs/Codexifyexec
/bin/zsh -lc "sed -n '1,320p' README.md" in /Users/resonant_jones/Keep/Resonant_Constructs/Codexify succeeded in 53ms:
        # Find the /authz/debug route
        authz_route = None
        for route in admin_module.router.routes:
            if route.path == "/authz/debug":
                authz_route = route
                break

        assert authz_route is not None, "/authz/debug route not found"

        # Check that it has dependencies
        assert hasattr(authz_route, "dependant")
        assert authz_route.dependant is not None


class TestPublicEndpointsRemainAccessible:
    """Verify public endpoints don't require admin access."""

    def test_ping_endpoint_is_public(self):
        """Verify /ping endpoint doesn't require admin."""
        from guardian.routes import admin as admin_module
 exited 1 in 52ms:

 succeeded in 51ms:
# Codexify

Codexify is a local-first chat + knowledge workspace built around a FastAPI backend (Guardian) and a React UI. It provides thread-based chat, memory silos, document autosave and sharing, media uploads, vector search, and optional workers for background tasks. Docker Compose is the primary, supported way to run the full stack.

### TL;DR — Start Here

If you want to **run Codexify locally** with the least friction:

* Use **Docker Compose**
* Copy `.env.template → .env`
* `.env` is local-only; never commit it (templates are the source of truth)
* Set `GUARDIAN_API_KEY`, `NEO4J_PASS`, and your local LLM settings
* Run: `docker compose up --build`
* Open:

  * UI: [http://localhost:5173](http://localhost:5173)
  * API docs: [http://localhost:8888/docs](http://localhost:8888/docs)

If you want to **contribute code**, start with:


thinking
**Inspecting admin module continuation**
exec
/bin/zsh -lc "sed -n '260,620p' guardian/routes/admin.py" in /Users/resonant_jones/Keep/Resonant_Constructs/Codexify succeeded in 53ms:


@router.get(
    "/debug/config",
    tags=["Diag"],
    summary="Return masked config for debugging (admin-only)",
)
def debug_config(access_method: str = Depends(require_admin)):
    """
    Return a small, masked snapshot of runtime config useful for local debugging.
    This endpoint requires admin privileges (X-Admin-Token header or DEBUG=true).
    """
    env = os.getenv("GUARDIAN_ENV", "development")
    api_key = (os.getenv("GUARDIAN_API_KEY") or "").strip()
    masked_key = (
        (api_key[:4] + "…" + api_key[-4:])
        if api_key and len(api_key) > 8
        else api_key
    )
    db_target = PG_DSN

thinking
**Searching for task details**
codex
{"status":"success","summary":"I confirmed `admin.py` scope and endpoint set. I’m now locating any task-specific references in the repo to align the exact intended behavior for the admin boundary and cookie security defaults.","tests_ran":[],"commit_hash":"","implementation_commit_hash":"","receipt_update_commit_hash":"","notes":""}

thinking
**Confirming JSON usage**
exec
/bin/zsh -lc 'rg -n "TASK-2026-02-16-002|admin auth boundary|cookie hardening|GUARDIAN_ADMIN_TOKEN|/auth/session/cookie|require_admin|DEBUG mode" .' in /Users/resonant_jones/Keep/Resonant_Constructs/Codexify succeeded in 50ms:
./API_AUDIT_REPORT.md:132:| 12 | POST | `/auth/session/cookie` | `admin.py:198` |
./API_AUDIT_REPORT.md:497:- Endpoint(s): `POST /auth/session/cookie`
./guardian/ws/methods.py:65:    expected = (os.getenv("GUARDIAN_ADMIN_TOKEN") or "").strip()
./guardian/routes/admin.py:9:- X-Admin-Token header matching GUARDIAN_ADMIN_TOKEN, OR
./guardian/routes/admin.py:54:ADMIN_TOKEN = os.getenv("GUARDIAN_ADMIN_TOKEN")
./guardian/routes/admin.py:58:def require_admin(
./guardian/routes/admin.py:66:    1. X-Admin-Token header matches GUARDIAN_ADMIN_TOKEN environment variable
./guardian/routes/admin.py:93:    # Method 2: Check DEBUG mode (development only)
./guardian/routes/admin.py:96:            "[admin] Admin access granted via DEBUG mode (api_key=%s)",
./guardian/routes/admin.py:121:            "Provide X-Admin-Token header or enable DEBUG mode.",
./guardian/routes/admin.py:199:    "/auth/session/cookie",
./guardian/routes/admin.py:251:    access_method: str = Depends(require_admin),
./guardian/routes/admin.py:267:def debug_config(access_method: str = Depends(require_admin)):
./tests/routes/test_admin.py:18:    """Test the require_admin dependency function directly."""
./tests/routes/test_admin.py:20:    def test_require_admin_with_valid_admin_token(self, monkeypatch):
./tests/routes/test_admin.py:22:        monkeypatch.setenv("GUARDIAN_ADMIN_TOKEN", "test-admin-secret")
./tests/routes/test_admin.py:32:        # Call require_admin with valid token
./tests/routes/test_admin.py:33:        result = admin_module.require_admin(
./tests/routes/test_admin.py:39:    def test_require_admin_with_invalid_admin_token(self, monkeypatch):
./tests/routes/test_admin.py:41:        monkeypatch.setenv("GUARDIAN_ADMIN_TOKEN", "test-admin-secret")

thinking
**Reviewing docs task requirements**
exec
/bin/zsh -lc "sed -n '1,260p' docs/work/tasks/2026/02/TASK_2026_02_16_002_admin_auth_debug_cookie_hardening.md" in /Users/resonant_jones/Keep/Resonant_Constructs/Codexify succeeded in 50ms:
Preflight: git status --porcelain -uall must be empty

If preflight is not empty, STOP and run exactly:
- git status --porcelain -uall
- git stash push -u -m "preflight-TASK-2026-02-16-002"
- git status --porcelain -uall

# TASK-2026-02-16-002  Admin auth boundary and cookie hardening
- Risk: HIGH
- Findings: FINDING-2026-02-16-009
- Allowed files:
  - guardian/routes/admin.py
  - tests/routes/test_admin.py
  - .env.template
  - README.md
- Dependencies/Prereqs:
  - command -v rg
  - command -v pytest
  - test -n "${GUARDIAN_API_KEY:-}"
- Command checklist:

thinking
**Searching auth config patterns**
codex
{"status":"success","summary":"I found the task spec in `docs/work/tasks/2026/02/TASK_2026_02_16_002_admin_auth_debug_cookie_hardening.md`; it confirms explicit goals: remove ambient DEBUG bypass, harden cookie flags, and switch template/docs default to `DEBUG=false`. I’m now aligning implementation with existing auth-mode env conventions in the repo.","tests_ran":[],"commit_hash":"","implementation_commit_hash":"","receipt_update_commit_hash":"","notes":""}

thinking
**Running parallel codebase search**
exec
/bin/zsh -lc 'rg -n "DEBUG=true|DEBUG=false|GUARDIAN_ADMIN_TOKEN|admin token|auth/session/cookie" README.md .env.template' in /Users/resonant_jones/Keep/Resonant_Constructs/Codexifyexec
/bin/zsh -lc "rg -n \"set_cookie\\(|samesite|httponly|secure=\" guardian -g'*.py'" in /Users/resonant_jones/Keep/Resonant_Constructs/Codexifyexec
/bin/zsh -lc "rg -n \"GUARDIAN_AUTH_MODE|GUARDIAN_DEV_MODE|DEBUG|ADMIN|LOCAL_ONLY|AUTH_MODE\" guardian -g'*.py'" in /Users/resonant_jones/Keep/Resonant_Constructs/Codexify succeeded in 53ms:
.env.template:13:DEBUG=true
 succeeded in 51ms:
guardian/routes/admin.py:228:    # NOTE: set secure=True when serving over HTTPS
guardian/routes/admin.py:229:    response.set_cookie(
guardian/routes/admin.py:233:        httponly=True,
guardian/routes/admin.py:234:        samesite="Lax",
guardian/routes/admin.py:235:        secure=False,
 succeeded in 51ms:
guardian/ws/methods.py:65:    expected = (os.getenv("GUARDIAN_ADMIN_TOKEN") or "").strip()
guardian/routes/admin.py:9:- X-Admin-Token header matching GUARDIAN_ADMIN_TOKEN, OR
guardian/routes/admin.py:10:- DEBUG=true environment variable (development only)
guardian/routes/admin.py:54:ADMIN_TOKEN = os.getenv("GUARDIAN_ADMIN_TOKEN")
guardian/routes/admin.py:55:DEBUG_MODE = os.getenv("DEBUG", "false").lower() in ("true", "1", "yes")
guardian/routes/admin.py:66:    1. X-Admin-Token header matches GUARDIAN_ADMIN_TOKEN environment variable
guardian/routes/admin.py:67:    2. DEBUG=true environment variable is set (development only)
guardian/routes/admin.py:85:    if x_admin_token and ADMIN_TOKEN:
guardian/routes/admin.py:86:        if secrets.compare_digest(x_admin_token, ADMIN_TOKEN):
guardian/routes/admin.py:93:    # Method 2: Check DEBUG mode (development only)
guardian/routes/admin.py:94:    if DEBUG_MODE:
guardian/routes/admin.py:96:            "[admin] Admin access granted via DEBUG mode (api_key=%s)",
guardian/routes/admin.py:112:        DEBUG_MODE,
guardian/routes/admin.py:121:            "Provide X-Admin-Token header or enable DEBUG mode.",
guardian/routes/admin.py:122:            "required": "X-Admin-Token header or DEBUG=true environment",
guardian/routes/admin.py:255:    This endpoint requires admin privileges (X-Admin-Token header or DEBUG=true).
guardian/routes/admin.py:270:    This endpoint requires admin privileges (X-Admin-Token header or DEBUG=true).
guardian/routes/devtools.py:36:    if not settings.GUARDIAN_DEV_MODE:
guardian/core/dependencies.py:158:    raw = (os.getenv("GUARDIAN_AUTH_MODE") or "local").strip().lower()
guardian/core/dependencies.py:164:        "Unknown GUARDIAN_AUTH_MODE=%r; defaulting to remote mode for safety",

thinking
**Inspecting auth mode function**
exec
/bin/zsh -lc "sed -n '120,240p' guardian/core/dependencies.py" in /Users/resonant_jones/Keep/Resonant_Constructs/Codexify succeeded in 53ms:
_origins_env = os.getenv("GUARDIAN_ALLOWED_ORIGINS", "http://localhost:5173")
allowed_origins = [o.strip() for o in _origins_env.split(",") if o.strip()]


# =========================
# Authentication
# =========================


def _exposure_mode() -> str:
    """
    Resolve endpoint exposure mode.

    - local_safe: default development boundary.
    - public_allowlist: externally exposed boundary.
    """
    raw = (os.getenv("GUARDIAN_EXPOSURE_MODE") or "local_safe").strip().lower()
    if raw in {"", "local_safe", "local"}:
        return "local_safe"
    if raw in {"public_allowlist"}:

thinking
**Assessing environment boolean parsing**
exec
/bin/zsh -lc "sed -n '1,180p' guardian/ws/methods.py" in /Users/resonant_jones/Keep/Resonant_Constructs/Codexify succeeded in 52ms:
"""RPC method registry and initial websocket RPC methods."""

from __future__ import annotations

import inspect
import os
from dataclasses import dataclass
from typing import Any, Awaitable, Callable

from fastapi import HTTPException

from guardian.ws.manager import WSConnectionManager

RPCHandler = Callable[[dict[str, Any], dict[str, Any]], Any]


@dataclass(frozen=True)
class RPCMethodSpec:
    """RPC method metadata and handler."""


thinking
**Searching DEBUG mentions**
exec
/bin/zsh -lc "rg -n \"\\bDEBUG\\b|GUARDIAN_ADMIN_TOKEN|auth/session/cookie|X-Admin-Token|admin-only|Admin\" README.md" in /Users/resonant_jones/Keep/Resonant_Constructs/Codexify exited 1 in 53ms:


thinking
**Clarifying debug bypass and cookie security changes**
exec
/bin/zsh -lc "sed -n '1,220p' guardian/routes/devtools.py" in /Users/resonant_jones/Keep/Resonant_Constructs/Codexify succeeded in 52ms:
"""
Devtools Routes
~~~~~~~~~~~~~~~

Development and debugging endpoints for inspecting system state.
These endpoints are intended for local development and debugging only.
"""

import json
import logging
import os
from typing import Optional

import psycopg
from fastapi import APIRouter, Depends, HTTPException

from guardian.agent_task_queue import (
    enqueue_agent_task,
    get_task_status,
    inject_result_to_thread,

thinking
**Inspecting dev mode usage**
exec
/bin/zsh -lc "sed -n '110,220p' guardian/core/config.py" in /Users/resonant_jones/Keep/Resonant_Constructs/Codexify succeeded in 53ms:
        default=0.5,
        description="Base delay for exponential backoff retries (seconds).",
    )
    PROVIDER_RETRY_MAX_SECONDS: float = Field(
        default=8.0,
        description="Maximum delay between retries (seconds).",
    )
    PROVIDER_RETRY_JITTER_SECONDS: float = Field(
        default=0.2,
        description="Random jitter added to retry sleep to avoid thundering herd (seconds).",
    )
    LLM_REQUEST_TIMEOUT_SECONDS: int = Field(
        default=60,
        description="Timeout for individual LLM completion requests (seconds).",
    )
    EMBEDDING_REQUEST_TIMEOUT_SECONDS: int = Field(
        default=30,
        description="Timeout for individual embedding requests (seconds).",
    )
    PROMPT_DIR_PATH: str | None = Field(

thinking
**Planning debug bypass feature**
exec
/bin/zsh -lc 'rg -n "auth/session/cookie|gc_session|set_cookie|secure=|samesite" tests' in /Users/resonant_jones/Keep/Resonant_Constructs/Codexify succeeded in 53ms:
tests/core/test_auth_boundary.py:18:        gc_session=None,
tests/core/test_auth_boundary.py:35:            gc_session=None,
tests/core/test_auth_boundary.py:50:        gc_session=None,
tests/core/test_auth_boundary.py:66:            gc_session=None,
tests/core/test_auth_boundary.py:83:            gc_session=None,
tests/core/test_auth_boundary.py:104:        gc_session=None,
tests/core/test_auth_boundary.py:123:        gc_session=session_token,
tests/core/test_auth_boundary.py:146:        gc_session=None,
tests/core/test_auth_boundary.py:167:        gc_session=None,

thinking
**Reviewing auth boundary tests**
exec
/bin/zsh -lc "sed -n '1,280p' tests/core/test_auth_boundary.py" in /Users/resonant_jones/Keep/Resonant_Constructs/Codexify succeeded in 52ms:
import time

import pytest
from fastapi import HTTPException

from guardian.core.auth import issue_session_token
from guardian.core.dependencies import verify_api_key


def test_local_mode_accepts_static_api_key(monkeypatch):
    monkeypatch.setenv("GUARDIAN_AUTH_MODE", "local")
    monkeypatch.setenv("GUARDIAN_EXPOSURE_MODE", "local_safe")
    monkeypatch.setenv("GUARDIAN_API_KEY", "local-test-key")

    token = verify_api_key(
        x_api_key="local-test-key",
        authorization=None,
        gc_session=None,
    )


thinking
**Aligning admin bypass with exposure and auth mode**
exec
/bin/zsh -lc "rg -n \"FINDING-2026-02-16-009|admin auth|debug bypass|secure=False|cookie hardening\" API_AUDIT_REPORT.md docs -g'*.md'" in /Users/resonant_jones/Keep/Resonant_Constructs/Codexify succeeded in 52ms:
API_AUDIT_REPORT.md:2428:- Audit and restrict `/debug/config`, `/authz/debug`, `/metrics` (disable in production or require admin auth)
docs/reference/operator/ops/doc-gen-validation.md:3:Deterministic procedure to prove `/api/documents/generate` persists drafts that immediately surface through `/api/threads/{thread_id}/documents`. Covers the INFO audit finding `FINDING-2026-02-16-009`.
docs/reference/product/Codexify-Master-Architecture-Report.md:402:| `admin.py` | `/admin` | (inferred) System ops | Requires admin auth |
docs/work/campaigns/2026/02/CAMPAIGN_2026_02_15_2026_02_16_COMPILED_AUDIT.md:20:- INFO: `FINDING-2026-02-16-009` (doc-gen loop closed; add deterministic validation artifact)
docs/archive/tasks/legacy/TASK_0091_23_45_678_9.md:1:# Task 009 — Tooling/Docs: Deterministic Doc-Gen Validation Artifact (FINDING-2026-02-16-009)
docs/archive/tasks/legacy/TASK_0091_23_45_678_9.md:17:- ID: `FINDING-2026-02-16-009`
docs/work/campaigns/2026/02/CAMPAIGN_2026_02_16_AUDIT_2026_02_16_SECURITY_MVP_FOLLOWUP.md:12:- Security: FINDING-2026-02-16-009, -010, -011
docs/work/tasks/2026/02/TASK_2026_02_16_002_admin_auth_debug_cookie_hardening.md:8:# TASK-2026-02-16-002  Admin auth boundary and cookie hardening
docs/work/tasks/2026/02/TASK_2026_02_16_002_admin_auth_debug_cookie_hardening.md:10:- Findings: FINDING-2026-02-16-009
docs/work/tasks/2026/02/TASK_2026_02_16_002_admin_auth_debug_cookie_hardening.md:21:  1. rg -n "DEBUG_MODE|secure=False|GUARDIAN_ADMIN_TOKEN" guardian/routes/admin.py .env.template README.md
docs/work/tasks/2026/02/TASK_2026_02_16_002_admin_auth_debug_cookie_hardening.md:34:  - No hardcoded secure=False cookie.

thinking
**Checking campaign document details**
exec
/bin/zsh -lc "sed -n '1,220p' docs/work/campaigns/2026/02/CAMPAIGN_2026_02_16_AUDIT_2026_02_16_SECURITY_MVP_FOLLOWUP.md" in /Users/resonant_jones/Keep/Resonant_Constructs/Codexify succeeded in 51ms:
# Campaign: AUDIT_2026_02_16 security-first closure

Source:
- audit_id: AUDIT_2026_02_16
- branch: campaign/2026-02-15/2026-02-16-compiled-audit
- commit: 1af5e5ec1f35e65a501ae33fa50f3f91142e4ded

Goal:
- Close RISK items first, then MVP core-loop closure gaps, then docs traceability drift.

Finding coverage:
- Security: FINDING-2026-02-16-009, -010, -011
- Core loop: FINDING-2026-02-16-001, -002, -003, -004, -005, -006, -007, -008
- Follow-up/docs: FINDING-2026-02-16-012, -013

Runner invariants:
- Every task starts with preflight clean-tree gate.
- Dirty tree or out-of-scope edits cause immediate STOP + exact cleanup commands.
- Decisions are explicit dedicated tasks (TASK-007, TASK-009).


thinking
**Planning audit search**
exec
/bin/zsh -lc 'rg -n "secure=False|DEBUG_MODE|X-Admin-Token|auth/session/cookie|admin bypass|ambient" API_AUDIT_REPORT.md' in /Users/resonant_jones/Keep/Resonant_Constructs/Codexify succeeded in 53ms:
132:| 12 | POST | `/auth/session/cookie` | `admin.py:198` |
497:- Endpoint(s): `POST /auth/session/cookie`

thinking
**Checking potential cookie security section**
exec
/bin/zsh -lc "sed -n '430,560p' API_AUDIT_REPORT.md" in /Users/resonant_jones/Keep/Resonant_Constructs/Codexify succeeded in 53ms:

---

### 8. Lightweight ping
- Endpoint(s): `GET /ping`
- What it is: Minimal liveness check returning a static response.
- Why it matters: Fastest possible check for load balancer health probes.
- Inputs needed:
  - None
  - Auth: unknown
- Output artifact:
  - Static JSON response (e.g., `{"status": "ok"}`)
- Risk / ambiguity notes:
  - Overlaps conceptually with `/health` and `/healthz`

---

### 9. Kubernetes-style health check
- Endpoint(s): `GET /healthz`
- What it is: Kubernetes-convention liveness/readiness probe endpoint.

thinking
**Searching for specific finding**
exec
/bin/zsh -lc "rg -n \"FINDING-2026-02-16-00[9-1][0-9]|FINDING-2026-02-16-009|admin bypass|cookie security\" docs API_AUDIT_REPORT.md -g'*.md'" in /Users/resonant_jones/Keep/Resonant_Constructs/Codexify exited 2 in 52ms:
rg: regex parse error:
    (?:FINDING-2026-02-16-00[9-1][0-9]|FINDING-2026-02-16-009|admin bypass|cookie security)
                             ^^^
error: invalid character class range, the start must be <= the end

thinking
**Simplifying regex to fix error**
exec
/bin/zsh -lc "rg -n \"FINDING-2026-02-16-009|FINDING-2026-02-16-010|FINDING-2026-02-16-011|admin bypass|cookie security\" docs API_AUDIT_REPORT.md -g'*.md'" in /Users/resonant_jones/Keep/Resonant_Constructs/Codexify succeeded in 53ms:
docs/work/tasks/2026/02/TASK_2026_02_16_001_sse_outbox_cleanup_api_alignment.md:10:- Findings: FINDING-2026-02-16-011
docs/reference/operator/ops/doc-gen-validation.md:3:Deterministic procedure to prove `/api/documents/generate` persists drafts that immediately surface through `/api/threads/{thread_id}/documents`. Covers the INFO audit finding `FINDING-2026-02-16-009`.
docs/work/tasks/2026/02/TASK_2026_02_16_003_identity_boundary_enforce_authenticated_ownership.md:10:- Findings: FINDING-2026-02-16-010
docs/archive/tasks/legacy/TASK_0091_23_45_678_9.md:1:# Task 009 — Tooling/Docs: Deterministic Doc-Gen Validation Artifact (FINDING-2026-02-16-009)
docs/archive/tasks/legacy/TASK_0091_23_45_678_9.md:17:- ID: `FINDING-2026-02-16-009`
docs/work/campaigns/2026/02/CAMPAIGN_2026_02_15_2026_02_16_COMPILED_AUDIT.md:20:- INFO: `FINDING-2026-02-16-009` (doc-gen loop closed; add deterministic validation artifact)
docs/work/tasks/2026/02/TASK_2026_02_16_002_admin_auth_debug_cookie_hardening.md:10:- Findings: FINDING-2026-02-16-009
docs/work/tasks/2026/02/TASK_2026_02_16_002_admin_auth_debug_cookie_hardening.md:22:  2. Constrain/remove unconditional DEBUG admin bypass (explicit local opt-in only).
docs/work/tasks/2026/02/TASK_2026_02_16_002_admin_auth_debug_cookie_hardening.md:23:  3. Make cookie security flags environment-aware with secure defaults.
docs/work/tasks/2026/02/TASK_2026_02_16_002_admin_auth_debug_cookie_hardening.md:33:  - No ambient DEBUG admin bypass.
docs/work/campaigns/2026/02/CAMPAIGN_2026_02_16_AUDIT_2026_02_16_SECURITY_MVP_FOLLOWUP.md:12:- Security: FINDING-2026-02-16-009, -010, -011

thinking
**Reviewing identity boundary task**
exec
/bin/zsh -lc "sed -n '1,240p' docs/work/tasks/2026/02/TASK_2026_02_16_003_identity_boundary_enforce_authenticated_ownership.md" in /Users/resonant_jones/Keep/Resonant_Constructs/Codexify succeeded in 53ms:
Preflight: git status --porcelain -uall must be empty

If preflight is not empty, STOP and run exactly:
- git status --porcelain -uall
- git stash push -u -m "preflight-TASK-2026-02-16-003"
- git status --porcelain -uall

# TASK-2026-02-16-003  Identity boundary enforcement on mutating routes
- Risk: HIGH
- Findings: FINDING-2026-02-16-010
- Allowed files:
  - guardian/core/dependencies.py
  - guardian/routes/migration.py
  - guardian/routes/media.py
  - guardian/routes/chat.py
  - tests/routes/test_migration_routes.py
  - tests/routes/test_media_routes.py
  - tests/routes/test_identity_boundary.py
- Dependencies/Prereqs:
  - command -v rg

thinking
**Planning scoped patch and tests**
exec
/bin/zsh -lc "rg -n \"issue_session_token|set_cookie|monkeypatch.setenv\\(\" tests/routes -g'test_*.py'" in /Users/resonant_jones/Keep/Resonant_Constructs/Codexify succeeded in 51ms:
tests/routes/test_connectors.py:23:from guardian.core.auth import issue_session_token
tests/routes/test_connectors.py:455:    monkeypatch.setenv("GUARDIAN_EXPOSURE_MODE", exposure_mode)
tests/routes/test_connectors.py:456:    monkeypatch.setenv("GUARDIAN_AUTH_MODE", auth_mode)
tests/routes/test_connectors.py:457:    monkeypatch.setenv("GUARDIAN_API_KEY", api_key)
tests/routes/test_connectors.py:459:        monkeypatch.setenv("GUARDIAN_SESSION_SECRET", session_secret)
tests/routes/test_connectors.py:511:        session_token, _expires = issue_session_token(
tests/routes/test_cron_routes.py:45:    monkeypatch.setenv("GUARDIAN_API_KEY", _API_KEY)
tests/routes/test_cron_routes.py:160:    monkeypatch.setenv("CRON_WEBHOOK_ALLOWLIST", "api.example.com")
tests/routes/test_personal_facts_routes.py:54:    monkeypatch.setenv("STORAGE_BASE_PATH", str(tmp_path / "media"))
tests/routes/test_thread_documents.py:22:from guardian.core.auth import issue_session_token
tests/routes/test_thread_documents.py:496:    monkeypatch.setenv("GUARDIAN_EXPOSURE_MODE", exposure_mode)
tests/routes/test_thread_documents.py:497:    monkeypatch.setenv("GUARDIAN_AUTH_MODE", auth_mode)
tests/routes/test_thread_documents.py:498:    monkeypatch.setenv("GUARDIAN_API_KEY", api_key)
tests/routes/test_thread_documents.py:500:        monkeypatch.setenv("GUARDIAN_SESSION_SECRET", session_secret)
tests/routes/test_thread_documents.py:569:        session_token, _expires = issue_session_token(
tests/routes/test_chat_routes.py:15:    monkeypatch.setenv("GROQ_API_KEY", "test-groq-key")
tests/routes/test_chat_routes.py:16:    monkeypatch.setenv("LLM_PROVIDER", "groq")
tests/routes/test_share_links.py:598:    monkeypatch.setenv("GUARDIAN_API_KEY", _API_KEY)
tests/routes/test_admin.py:22:        monkeypatch.setenv("GUARDIAN_ADMIN_TOKEN", "test-admin-secret")
tests/routes/test_admin.py:23:        monkeypatch.setenv("DEBUG", "false")

thinking
**Designing environment-aware admin and cookie security**
codex
{"status":"success","summary":"I’ve locked the implementation approach: admin bypass will require explicit local dev opt-in (not just `DEBUG`), and session cookies will default secure with local-only opt-out tied to dev mode. I’m about to patch `admin.py` and then update tests/docs/env accordingly.","tests_ran":[],"commit_hash":"","implementation_commit_hash":"","receipt_update_commit_hash":"","notes":""}

thinking
**Testing cookie header formatting**
exec
/bin/zsh -lc "python - <<'PY'
from fastapi import Response
r = Response()
r.set_cookie('gc_session','abc',max_age=60,httponly=True,samesite='Lax',secure=True)
print(r.headers['set-cookie'])
r2 = Response()
r2.set_cookie('gc_session','abc',max_age=60,httponly=True,samesite='Lax',secure=False)
print(r2.headers['set-cookie'])
PY" in /Users/resonant_jones/Keep/Resonant_Constructs/Codexify succeeded in 345ms:
gc_session=abc; HttpOnly; Max-Age=60; Path=/; SameSite=Lax; Secure
gc_session=abc; HttpOnly; Max-Age=60; Path=/; SameSite=Lax

thinking
**Planning targeted admin.py patch**
file update
M /Users/resonant_jones/Keep/Resonant_Constructs/Codexify/guardian/routes/admin.py
@@ -8,4 +8,4 @@
 Admin-protected endpoints require:
-- X-Admin-Token header matching GUARDIAN_ADMIN_TOKEN, OR
-- DEBUG=true environment variable (development only)
+- X-Admin-Token header matching GUARDIAN_ADMIN_TOKEN
+- Optional local debug bypass with explicit dev-mode opt-in
 """
@@ -52,5 +52,48 @@
 
-# Admin token from environment (optional, for stricter access control)
-ADMIN_TOKEN = os.getenv("GUARDIAN_ADMIN_TOKEN")
-DEBUG_MODE = os.getenv("DEBUG", "false").lower() in ("true", "1", "yes")
+TRUE_VALUES = {"true", "1", "yes", "on"}
+LOCAL_AUTH_MODES = {"", "local", "localhost", "loopback"}
+REMOTE_AUTH_MODES = {"remote", "cloud", "hosted", "public", "prod", "production"}
+
+
+def _env_bool(name: str, default: bool = False) -> bool:
+    raw = os.getenv(name)
+    if raw is None:
+        return default
+    return raw.strip().lower() in TRUE_VALUES
+
+
+def _is_local_auth_boundary() -> bool:
+    exposure_mode = (
+        (os.getenv("GUARDIAN_EXPOSURE_MODE") or "local_safe").strip().lower()
+    )
+    if exposure_mode == "public_allowlist":
+        return False
+
+    auth_mode = (os.getenv("GUARDIAN_AUTH_MODE") or "local").strip().lower()
+    if auth_mode in REMOTE_AUTH_MODES:
+        return False
+    if auth_mode in LOCAL_AUTH_MODES:
+        return True
+
+    logger.warning(
+        "[admin] Unknown GUARDIAN_AUTH_MODE=%r; treating as remote for safety",
+        auth_mode,
+    )
+    return False
+
+
+def _debug_admin_bypass_enabled() -> bool:
+    return (
+        _env_bool("DEBUG", default=False)
+        and _env_bool("GUARDIAN_DEV_MODE", default=False)
+        and _is_local_auth_boundary()
+    )
+
+
+def _session_cookie_secure_flag() -> bool:
+    # Secure by default. Local HTTP cookies are only allowed with explicit
+    # dev mode opt-in inside the local auth boundary.
+    if _is_local_auth_boundary() and _env_bool("GUARDIAN_DEV_MODE", default=False):
+        return False
+    return True
 
@@ -66,3 +109,4 @@
     1. X-Admin-Token header matches GUARDIAN_ADMIN_TOKEN environment variable
-    2. DEBUG=true environment variable is set (development only)
+    2. Local debug bypass is explicitly enabled via env:
+       DEBUG + GUARDIAN_DEV_MODE in local auth boundary
     3. Future: User role verification (when RBAC is fully implemented)
@@ -74,3 +118,3 @@
     Returns:
-        str: Access method used ("admin_token", "debug_mode")
+        str: Access method used ("admin_token", "debug_local_opt_in")
 
@@ -83,5 +127,10 @@
     """
-    # Method 1: Check X-Admin-Token header
-    if x_admin_token and ADMIN_TOKEN:
-        if secrets.compare_digest(x_admin_token, ADMIN_TOKEN):
+    admin_token = (os.getenv("GUARDIAN_ADMIN_TOKEN") or "").strip()
+    debug_mode = _env_bool("DEBUG", default=False)
+    dev_mode = _env_bool("GUARDIAN_DEV_MODE", default=False)
+    local_auth_boundary = _is_local_auth_boundary()
+
+    # Method 1: Check X-Admin-Token header.
+    if x_admin_token and admin_token:
+        if secrets.compare_digest(x_admin_token, admin_token):
             logger.info(
@@ -92,6 +141,6 @@
 
-    # Method 2: Check DEBUG mode (development only)
-    if DEBUG_MODE:
+    # Method 2: Explicit local debug bypass only.
+    if _debug_admin_bypass_enabled():
         logger.info(
-            "[admin] Admin access granted via DEBUG mode (api_key=%s)",
+            "[admin] Admin access granted via local debug opt-in (api_key=%s)",
             x_api_key[:8] + "..."
@@ -100,3 +149,3 @@
         )
-        return "debug_mode"
+        return "debug_local_opt_in"
 
@@ -108,6 +157,10 @@
     logger.warning(
-        "[admin] Admin access DENIED - missing admin token or debug mode "
-        "(admin_token_provided=%s, debug_mode=%s, api_key=%s)",
+        "[admin] Admin access DENIED "
+        "(admin_token_configured=%s, admin_token_provided=%s, debug_mode=%s, "
+        "dev_mode=%s, local_boundary=%s, api_key=%s)",
+        bool(admin_token),
         bool(x_admin_token),
-        DEBUG_MODE,
+        debug_mode,
+        dev_mode,
+        local_auth_boundary,
         x_api_key[:8] + "..." if x_api_key and len(x_api_key) > 8 else "none",
@@ -120,4 +173,5 @@
             "message": "This endpoint requires admin privileges. "
-            "Provide X-Admin-Token header or enable DEBUG mode.",
-            "required": "X-Admin-Token header or DEBUG=true environment",
+            "Provide X-Admin-Token or enable local debug opt-in "
+            "(DEBUG + GUARDIAN_DEV_MODE in local auth mode).",
+            "required": "X-Admin-Token header (preferred) or explicit local debug opt-in",
         },
@@ -227,3 +281,3 @@
     max_age = body.ttl_seconds or 24 * 3600
-    # NOTE: set secure=True when serving over HTTPS
+    secure_cookie = _session_cookie_secure_flag()
     response.set_cookie(
@@ -234,3 +288,3 @@
         samesite="Lax",
-        secure=False,
+        secure=secure_cookie,
     )
@@ -254,3 +308,3 @@
     """Return the masked API key received via X-API-Key, masked for safety.
-    This endpoint requires admin privileges (X-Admin-Token header or DEBUG=true).
+    This endpoint requires admin privileges.
     """
@@ -269,3 +323,3 @@
     Return a small, masked snapshot of runtime config useful for local debugging.
-    This endpoint requires admin privileges (X-Admin-Token header or DEBUG=true).
+    This endpoint requires admin privileges.
     """
apply_patch(auto_approved=true) exited 0 in 35ms:
Success. Updated the following files:
M /Users/resonant_jones/Keep/Resonant_Constructs/Codexify/guardian/routes/admin.py
file update:
diff --git a/guardian/routes/admin.py b/guardian/routes/admin.py
index 8e378ea1fc8d11f1457da8bba99c1a7be7b87993..440af8580fd8b93455729bf8e01f5ad4a8b19c7f
--- a/guardian/routes/admin.py
+++ b/guardian/routes/admin.py
@@ -6,8 +6,8 @@
 session token management, and configuration debugging.
 
 Admin-protected endpoints require:
-- X-Admin-Token header matching GUARDIAN_ADMIN_TOKEN, OR
-- DEBUG=true environment variable (development only)
+- X-Admin-Token header matching GUARDIAN_ADMIN_TOKEN
+- Optional local debug bypass with explicit dev-mode opt-in
 """
 
 import logging
@@ -50,9 +50,52 @@
     ttl_seconds: int | None = None
 
 
-# Admin token from environment (optional, for stricter access control)
-ADMIN_TOKEN = os.getenv("GUARDIAN_ADMIN_TOKEN")
-DEBUG_MODE = os.getenv("DEBUG", "false").lower() in ("true", "1", "yes")
+TRUE_VALUES = {"true", "1", "yes", "on"}
+LOCAL_AUTH_MODES = {"", "local", "localhost", "loopback"}
+REMOTE_AUTH_MODES = {"remote", "cloud", "hosted", "public", "prod", "production"}
+
+
+def _env_bool(name: str, default: bool = False) -> bool:
+    raw = os.getenv(name)
+    if raw is None:
+        return default
+    return raw.strip().lower() in TRUE_VALUES
+
+
+def _is_local_auth_boundary() -> bool:
+    exposure_mode = (
+        (os.getenv("GUARDIAN_EXPOSURE_MODE") or "local_safe").strip().lower()
+    )
+    if exposure_mode == "public_allowlist":
+        return False
+
+    auth_mode = (os.getenv("GUARDIAN_AUTH_MODE") or "local").strip().lower()
+    if auth_mode in REMOTE_AUTH_MODES:
+        return False
+    if auth_mode in LOCAL_AUTH_MODES:
+        return True
+
+    logger.warning(
+        "[admin] Unknown GUARDIAN_AUTH_MODE=%r; treating as remote for safety",
+        auth_mode,
+    )
+    return False
+
+
+def _debug_admin_bypass_enabled() -> bool:
+    return (
+        _env_bool("DEBUG", default=False)
+        and _env_bool("GUARDIAN_DEV_MODE", default=False)
+        and _is_local_auth_boundary()
+    )
+
+
+def _session_cookie_secure_flag() -> bool:
+    # Secure by default. Local HTTP cookies are only allowed with explicit
+    # dev mode opt-in inside the local auth boundary.
+    if _is_local_auth_boundary() and _env_bool("GUARDIAN_DEV_MODE", default=False):
+        return False
+    return True
 
 
 def require_admin(
@@ -64,7 +107,8 @@
 
     Access is granted if ANY of the following conditions are met:
     1. X-Admin-Token header matches GUARDIAN_ADMIN_TOKEN environment variable
-    2. DEBUG=true environment variable is set (development only)
+    2. Local debug bypass is explicitly enabled via env:
+       DEBUG + GUARDIAN_DEV_MODE in local auth boundary
     3. Future: User role verification (when RBAC is fully implemented)
 
     Args:
@@ -72,7 +116,7 @@
         x_api_key: Regular API key (for context/logging)
 
     Returns:
-        str: Access method used ("admin_token", "debug_mode")
+        str: Access method used ("admin_token", "debug_local_opt_in")
 
     Raises:
         HTTPException: 403 if access is denied
@@ -81,24 +125,29 @@
         - Info: Successful admin access with method used
         - Warning: Failed admin access attempts
     """
-    # Method 1: Check X-Admin-Token header
-    if x_admin_token and ADMIN_TOKEN:
-        if secrets.compare_digest(x_admin_token, ADMIN_TOKEN):
+    admin_token = (os.getenv("GUARDIAN_ADMIN_TOKEN") or "").strip()
+    debug_mode = _env_bool("DEBUG", default=False)
+    dev_mode = _env_bool("GUARDIAN_DEV_MODE", default=False)
+    local_auth_boundary = _is_local_auth_boundary()
+
+    # Method 1: Check X-Admin-Token header.
+    if x_admin_token and admin_token:
+        if secrets.compare_digest(x_admin_token, admin_token):
             logger.info(
                 "[admin] Admin access granted via X-Admin-Token (token=%s...)",
                 x_admin_token[:8] if len(x_admin_token) > 8 else "short",
             )
             return "admin_token"
 
-    # Method 2: Check DEBUG mode (development only)
-    if DEBUG_MODE:
+    # Method 2: Explicit local debug bypass only.
+    if _debug_admin_bypass_enabled():
         logger.info(
-            "[admin] Admin access granted via DEBUG mode (api_key=%s)",
+            "[admin] Admin access granted via local debug opt-in (api_key=%s)",
             x_api_key[:8] + "..."
             if x_api_key and len(x_api_key) > 8
             else "none",
         )
-        return "debug_mode"
+        return "debug_local_opt_in"
 
     # Method 3: Future - User role verification
     # if user_role == "admin":
@@ -106,10 +155,14 @@
 
     # Access denied - log the attempt
     logger.warning(
-        "[admin] Admin access DENIED - missing admin token or debug mode "
-        "(admin_token_provided=%s, debug_mode=%s, api_key=%s)",
+        "[admin] Admin access DENIED "
+        "(admin_token_configured=%s, admin_token_provided=%s, debug_mode=%s, "
+        "dev_mode=%s, local_boundary=%s, api_key=%s)",
+        bool(admin_token),
         bool(x_admin_token),
-        DEBUG_MODE,
+        debug_mode,
+        dev_mode,
+        local_auth_boundary,
         x_api_key[:8] + "..." if x_api_key and len(x_api_key) > 8 else "none",
     )
 
@@ -118,8 +171,9 @@
         detail={
             "error": "Admin access required",
             "message": "This endpoint requires admin privileges. "
-            "Provide X-Admin-Token header or enable DEBUG mode.",
-            "required": "X-Admin-Token header or DEBUG=true environment",
+            "Provide X-Admin-Token or enable local debug opt-in "
+            "(DEBUG + GUARDIAN_DEV_MODE in local auth mode).",
+            "required": "X-Admin-Token header (preferred) or explicit local debug opt-in",
         },
     )
 
@@ -225,14 +279,14 @@
         subject="web", ttl_seconds=body.ttl_seconds or 24 * 3600
     )
     max_age = body.ttl_seconds or 24 * 3600
-    # NOTE: set secure=True when serving over HTTPS
+    secure_cookie = _session_cookie_secure_flag()
     response.set_cookie(
         "gc_session",
         token,
         max_age=max_age,
         httponly=True,
         samesite="Lax",
-        secure=False,
+        secure=secure_cookie,
     )
     return {"ok": True, "expires": exp}
 
@@ -252,7 +306,7 @@
     x_api_key: Optional[str] = Header(None, alias="X-API-Key"),
 ):
     """Return the masked API key received via X-API-Key, masked for safety.
-    This endpoint requires admin privileges (X-Admin-Token header or DEBUG=true).
+    This endpoint requires admin privileges.
     """
     key = x_api_key or ""
     masked = (key[:4] + "…" + key[-4:]) if len(key) > 8 else key
@@ -267,7 +321,7 @@
 def debug_config(access_method: str = Depends(require_admin)):
     """
     Return a small, masked snapshot of runtime config useful for local debugging.
-    This endpoint requires admin privileges (X-Admin-Token header or DEBUG=true).
+    This endpoint requires admin privileges.
     """
     env = os.getenv("GUARDIAN_ENV", "development")
     api_key = (os.getenv("GUARDIAN_API_KEY") or "").strip()

file update:
diff --git a/guardian/routes/admin.py b/guardian/routes/admin.py
index 8e378ea1fc8d11f1457da8bba99c1a7be7b87993..440af8580fd8b93455729bf8e01f5ad4a8b19c7f
--- a/guardian/routes/admin.py
+++ b/guardian/routes/admin.py
@@ -6,8 +6,8 @@
 session token management, and configuration debugging.
 
 Admin-protected endpoints require:
-- X-Admin-Token header matching GUARDIAN_ADMIN_TOKEN, OR
-- DEBUG=true environment variable (development only)
+- X-Admin-Token header matching GUARDIAN_ADMIN_TOKEN
+- Optional local debug bypass with explicit dev-mode opt-in
 """
 
 import logging
@@ -50,9 +50,52 @@
     ttl_seconds: int | None = None
 
 
-# Admin token from environment (optional, for stricter access control)
-ADMIN_TOKEN = os.getenv("GUARDIAN_ADMIN_TOKEN")
-DEBUG_MODE = os.getenv("DEBUG", "false").lower() in ("true", "1", "yes")
+TRUE_VALUES = {"true", "1", "yes", "on"}
+LOCAL_AUTH_MODES = {"", "local", "localhost", "loopback"}
+REMOTE_AUTH_MODES = {"remote", "cloud", "hosted", "public", "prod", "production"}
+
+
+def _env_bool(name: str, default: bool = False) -> bool:
+    raw = os.getenv(name)
+    if raw is None:
+        return default
+    return raw.strip().lower() in TRUE_VALUES
+
+
+def _is_local_auth_boundary() -> bool:
+    exposure_mode = (
+        (os.getenv("GUARDIAN_EXPOSURE_MODE") or "local_safe").strip().lower()
+    )
+    if exposure_mode == "public_allowlist":
+        return False
+
+    auth_mode = (os.getenv("GUARDIAN_AUTH_MODE") or "local").strip().lower()
+    if auth_mode in REMOTE_AUTH_MODES:
+        return False
+    if auth_mode in LOCAL_AUTH_MODES:
+        return True
+
+    logger.warning(
+        "[admin] Unknown GUARDIAN_AUTH_MODE=%r; treating as remote for safety",
+        auth_mode,
+    )
+    return False
+
+
+def _debug_admin_bypass_enabled() -> bool:
+    return (
+        _env_bool("DEBUG", default=False)
+        and _env_bool("GUARDIAN_DEV_MODE", default=False)
+        and _is_local_auth_boundary()
+    )
+
+
+def _session_cookie_secure_flag() -> bool:
+    # Secure by default. Local HTTP cookies are only allowed with explicit
+    # dev mode opt-in inside the local auth boundary.
+    if _is_local_auth_boundary() and _env_bool("GUARDIAN_DEV_MODE", default=False):
+        return False
+    return True
 
 
 def require_admin(
@@ -64,7 +107,8 @@
 
     Access is granted if ANY of the following conditions are met:
     1. X-Admin-Token header matches GUARDIAN_ADMIN_TOKEN environment variable
-    2. DEBUG=true environment variable is set (development only)
+    2. Local debug bypass is explicitly enabled via env:
+       DEBUG + GUARDIAN_DEV_MODE in local auth boundary
     3. Future: User role verification (when RBAC is fully implemented)
 
     Args:
@@ -72,7 +116,7 @@
         x_api_key: Regular API key (for context/logging)
 
     Returns:
-        str: Access method used ("admin_token", "debug_mode")
+        str: Access method used ("admin_token", "debug_local_opt_in")
 
     Raises:
         HTTPException: 403 if access is denied
@@ -81,24 +125,29 @@
         - Info: Successful admin access with method used
         - Warning: Failed admin access attempts
     """
-    # Method 1: Check X-Admin-Token header
-    if x_admin_token and ADMIN_TOKEN:
-        if secrets.compare_digest(x_admin_token, ADMIN_TOKEN):
+    admin_token = (os.getenv("GUARDIAN_ADMIN_TOKEN") or "").strip()
+    debug_mode = _env_bool("DEBUG", default=False)
+    dev_mode = _env_bool("GUARDIAN_DEV_MODE", default=False)
+    local_auth_boundary = _is_local_auth_boundary()
+
+    # Method 1: Check X-Admin-Token header.
+    if x_admin_token and admin_token:
+        if secrets.compare_digest(x_admin_token, admin_token):
             logger.info(
                 "[admin] Admin access granted via X-Admin-Token (token=%s...)",
                 x_admin_token[:8] if len(x_admin_token) > 8 else "short",
             )
             return "admin_token"
 
-    # Method 2: Check DEBUG mode (development only)
-    if DEBUG_MODE:
+    # Method 2: Explicit local debug bypass only.
+    if _debug_admin_bypass_enabled():
         logger.info(
-            "[admin] Admin access granted via DEBUG mode (api_key=%s)",
+            "[admin] Admin access granted via local debug opt-in (api_key=%s)",
             x_api_key[:8] + "..."
             if x_api_key and len(x_api_key) > 8
             else "none",
         )
-        return "debug_mode"
+        return "debug_local_opt_in"
 
     # Method 3: Future - User role verification
     # if user_role == "admin":
@@ -106,10 +155,14 @@
 
     # Access denied - log the attempt
     logger.warning(
-        "[admin] Admin access DENIED - missing admin token or debug mode "
-        "(admin_token_provided=%s, debug_mode=%s, api_key=%s)",
+        "[admin] Admin access DENIED "
+        "(admin_token_configured=%s, admin_token_provided=%s, debug_mode=%s, "
+        "dev_mode=%s, local_boundary=%s, api_key=%s)",
+        bool(admin_token),
         bool(x_admin_token),
-        DEBUG_MODE,
+        debug_mode,
+        dev_mode,
+        local_auth_boundary,
         x_api_key[:8] + "..." if x_api_key and len(x_api_key) > 8 else "none",
     )
 
@@ -118,8 +171,9 @@
         detail={
             "error": "Admin access required",
             "message": "This endpoint requires admin privileges. "
-            "Provide X-Admin-Token header or enable DEBUG mode.",
-            "required": "X-Admin-Token header or DEBUG=true environment",
+            "Provide X-Admin-Token or enable local debug opt-in "
+            "(DEBUG + GUARDIAN_DEV_MODE in local auth mode).",
+            "required": "X-Admin-Token header (preferred) or explicit local debug opt-in",
         },
     )
 
@@ -225,14 +279,14 @@
         subject="web", ttl_seconds=body.ttl_seconds or 24 * 3600
     )
     max_age = body.ttl_seconds or 24 * 3600
-    # NOTE: set secure=True when serving over HTTPS
+    secure_cookie = _session_cookie_secure_flag()
     response.set_cookie(
         "gc_session",
         token,
         max_age=max_age,
         httponly=True,
         samesite="Lax",
-        secure=False,
+        secure=secure_cookie,
     )
     return {"ok": True, "expires": exp}
 
@@ -252,7 +306,7 @@
     x_api_key: Optional[str] = Header(None, alias="X-API-Key"),
 ):
     """Return the masked API key received via X-API-Key, masked for safety.
-    This endpoint requires admin privileges (X-Admin-Token header or DEBUG=true).
+    This endpoint requires admin privileges.
     """
     key = x_api_key or ""
     masked = (key[:4] + "…" + key[-4:]) if len(key) > 8 else key
@@ -267,7 +321,7 @@
 def debug_config(access_method: str = Depends(require_admin)):
     """
     Return a small, masked snapshot of runtime config useful for local debugging.
-    This endpoint requires admin privileges (X-Admin-Token header or DEBUG=true).
+    This endpoint requires admin privileges.
     """
     env = os.getenv("GUARDIAN_ENV", "development")
     api_key = (os.getenv("GUARDIAN_API_KEY") or "").strip()

ERROR: You've hit your usage limit. To get more access now, send a request to your admin or try again at 2:31 AM.
Warning: no last agent message; wrote empty content to /var/folders/kj/mnb6b7ds2sq__bjhmglf5xyh0000gn/T/tmpmu971pnh/task_result.json
tokens used
78,035
