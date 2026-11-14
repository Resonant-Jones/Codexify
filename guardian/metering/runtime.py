"""Opt-in, single-attempt OpenAI text-chat budget integration.

No implicit budgets, prices, activation, paid retries or user-supplied authority.
This protects only this bounded chat route, not every possible API consumer.
"""

from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass
from hashlib import sha256
import json
import logging
import math
import os
from types import SimpleNamespace

from fastapi import HTTPException

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from guardian.metering.budget import BudgetLedger

ENV = "CODEXIFY_BOUNDED_OPENAI_BUDGET_JSON"
# Deliberately pinned, narrow capability contract, not a general model catalog.
# https://developers.openai.com/api/docs/models/gpt-4o (checked 2026-11-14)
MODEL = "gpt-4o-2024-08-06"
CONTEXT_TOKENS = 128_000
MAX_OUTPUT = 16_384
ENDPOINT = "https://api.openai.com/v1/chat/completions"
logger = logging.getLogger(__name__)
_CONTEXT = ContextVar("bounded_inference_budget", default=None)


def _deny():
    return HTTPException(
        status_code=503,
        detail="Managed inference budget is unavailable or this request is outside its qualified scope. Account data remains accessible.",
    )


def configuration():
    raw = os.getenv(ENV)
    if raw is None or not raw.strip():
        return None
    try:
        config = json.loads(raw)
        required = {
            "mode",
            "payer_scope",
            "monthly_window",
            "funding_window",
            "max_output_tokens",
            "quote",
        }
        if (
            not isinstance(config, dict)
            or not required <= set(config)
            or set(config) - required - {"account_allowances"}
        ):
            raise ValueError()
        allowances = config.get("account_allowances", {})
        if not isinstance(allowances, dict) or any(
            not isinstance(account, str)
            or not 0 < len(account) <= 255
            or type(amount) is not int
            or not 1 <= amount <= 10**15
            for account, amount in allowances.items()
        ):
            raise ValueError()
        if config["mode"] != "enforce":
            raise ValueError()
        for key in ("payer_scope", "monthly_window", "funding_window"):
            if not isinstance(config[key], str) or not 0 < len(config[key]) <= 128:
                raise ValueError()
        if (
            type(config["max_output_tokens"]) is not int
            or not 1 <= config["max_output_tokens"] <= MAX_OUTPUT
        ):
            raise ValueError()
        if not isinstance(config["quote"], dict):
            raise ValueError()
        return config
    except (TypeError, ValueError, KeyError):
        raise _deny() from None


@dataclass(frozen=True)
class _Context:
    config: dict
    ledger: BudgetLedger
    account_id: str
    request_id: str
    thread_id: int
    task_id: str


@contextmanager
def accepted_budget_context(task, provider, db):
    if provider == "local":
        yield
        return
    config = configuration()
    if config is None:
        yield
        return
    if (
        provider != "openai"
        or not callable(getattr(db, "_sa_session", None))
        or getattr(task, "tools", None)
    ):
        raise _deny()
    # These are candidate IDs, not authority. BudgetLedger revalidates them
    # against the canonical accepted-account binding before reserving/claiming.
    account = getattr(task, "user_id", None)
    request = getattr(task, "request_id", None)
    thread_id = getattr(task, "thread_id", None)
    task_id = getattr(task, "task_id", None)
    if (
        not isinstance(account, str)
        or not isinstance(request, str)
        or type(thread_id) is not int
        or thread_id < 1
        or not isinstance(task_id, str)
        or not task_id
    ):
        raise _deny()
    # Import only for an admitted DB-backed request. Importing the ledger at
    # module load cycles through DB models -> TTS -> provider quarantine guards.
    from guardian.metering.budget import BudgetLedger

    token = _CONTEXT.set(
        _Context(
            config,
            BudgetLedger(SimpleNamespace(begin=db._sa_session)),
            account,
            request,
            thread_id,
            task_id,
        )
    )
    try:
        yield
    finally:
        _CONTEXT.reset(token)


def deny_unqualified_spend():
    """Fence legacy paid adapters while bounded mode is configured.

    An accepted chat context cannot authorize a second SDK call. These routes
    lack qualified reservations and must not inherit the chat call's authority.
    Malformed configuration also denies. Unconfigured installations are unchanged.
    """
    if configuration() is not None:
        raise _deny()


def require_context(provider):
    if provider != "local" and configuration() is not None:
        if provider != "openai" or _CONTEXT.get() is None:
            raise _deny()


def guarded_http(url, payload, send):
    """Reserve/claim at the final wire payload, settle raw usage before parsing.

    send receives the validated, output-bounded payload. It must not redirect or
    retry. Any exception after claim remains held. One accepted request can
    claim only one attempt, even across redelivery and process restart.
    """
    context = _CONTEXT.get()
    if context is None:
        # This choke point is used by cloud adapters only. No provider alias,
        # custom URL or direct adapter call can bypass accepted admission.
        if configuration() is not None:
            raise _deny()
        return send(payload, False)
    if url != ENDPOINT or not isinstance(payload, dict):
        raise _deny()
    if set(payload) - {"model", "messages", "temperature", "max_tokens"}:
        raise _deny()
    if payload.get("model") != MODEL:
        # This is the actual normalized dispatch model, never Composer's label.
        raise _deny()
    messages = payload.get("messages")
    if not isinstance(messages, list) or not messages:
        raise _deny()
    for message in messages:
        if not isinstance(message, dict) or set(message) != {"role", "content"}:
            raise _deny()
        if message["role"] not in {"system", "user", "assistant"} or not isinstance(
            message["content"], str
        ):
            raise _deny()
    bound = context.config["max_output_tokens"]
    if "max_tokens" in payload:
        value = payload["max_tokens"]
        if type(value) is not int or not 1 <= value <= bound:
            raise _deny()
        bound = value
    temperature = payload.get("temperature", 0.7)
    if (
        type(temperature) not in (int, float)
        or not math.isfinite(temperature)
        or not 0 <= temperature <= 2
    ):
        raise _deny()
    wire = dict(payload, max_tokens=bound)
    # Bound admission work and reject local serialization failures before claim.
    # This is a size guard, not an asserted tokenizer-equivalence calculation.
    if (
        len(messages) > 1000
        or len(json.dumps(wire, ensure_ascii=False, allow_nan=False).encode("utf-8"))
        > 128_000
    ):
        raise _deny()
    # Reserve the full documented context ceiling; no guessed tokenizer count.
    # An over-context request can be rejected upstream but never under-reserved.
    attempt = (
        "bounded-openai-"
        + sha256(f"{context.account_id}\0{context.request_id}".encode()).hexdigest()
    )
    try:
        context.ledger.reserve(
            attempt_id=attempt,
            account_id=context.account_id,
            request_id=context.request_id,
            payer_scope=context.config["payer_scope"],
            provider="openai",
            model=MODEL,
            budget_ids=[
                context.config["monthly_window"],
                context.config["funding_window"],
            ],
            input_ceiling=CONTEXT_TOKENS,
            output_ceiling=bound,
            quote=context.config["quote"],
            expected_thread_id=context.thread_id,
            expected_task_id=context.task_id,
            dispatch_digest=sha256(
                json.dumps(
                    wire, sort_keys=True, ensure_ascii=False, allow_nan=False
                ).encode("utf-8")
            ).hexdigest(),
        )
        if not context.ledger.claim(attempt_id=attempt, account_id=context.account_id):
            raise _deny()
    except HTTPException:
        raise
    except Exception:
        # Do not log budget configuration, credentials or private identifiers.
        logger.warning("Managed inference admission unavailable")
        raise _deny() from None
    response = send(wire, True)
    # Capture even if the adapter subsequently discards usage/returns only text.
    # A non-2xx or unparsable response remains ambiguous, never a free refund.
    try:
        if 200 <= response.status_code < 300:
            context.ledger.settle(
                attempt_id=attempt,
                account_id=context.account_id,
                output=response.json(),
            )
    except Exception:
        # Transaction failure keeps the durable hold; don't repeat paid work.
        logger.warning("Managed inference settlement pending reconciliation")
    return response
