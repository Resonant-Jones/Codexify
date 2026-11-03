"""Append-only, account-bound inference usage, independent of billing authority.

Only provider-reported units are treated as observed. A missing or malformed
usage block creates an explicit unavailable/partial record with NULL costs.
Configured rate quotes are snapshots, not claims about provider invoices.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from typing import Any, Mapping

from sqlalchemy import case, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from guardian.db.models import ChatThread, InferenceUsageEvent, User
from guardian.metering.tokens import InferenceCostSource, InferenceUsageSource

logger = logging.getLogger(__name__)
_MILLION = Decimal("1000000")
_COST_QUANTUM = Decimal("0.000000001")
_PRICE_CONFIG_ENV = "CODEXIFY_METERING_PRICE_SNAPSHOTS_JSON"


@dataclass(frozen=True)
class ProviderTokenUsage:
    input_tokens: int | None
    output_tokens: int | None
    cached_input_tokens: int | None
    total_tokens: int | None
    source: InferenceUsageSource
    provider_request_id: str | None = None


def _count(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value if value >= 0 else None
    if isinstance(value, str) and value.isascii() and value.isdecimal():
        return int(value)
    return None


def _first_count(source: Mapping[str, Any], *names: str) -> int | None:
    for name in names:
        if name in source:
            return _count(source[name])
    return None


def extract_provider_usage(output: Any) -> ProviderTokenUsage:
    """Parse only the provider's usage envelope, never generated text."""
    raw = getattr(output, "raw_payload", None)
    if raw is None and isinstance(output, Mapping):
        raw = output
    payload = raw if isinstance(raw, Mapping) else {}
    usage = payload.get("usage")
    usage = usage if isinstance(usage, Mapping) else {}
    details = usage.get("prompt_tokens_details")
    details = details if isinstance(details, Mapping) else {}

    input_tokens = _first_count(usage, "prompt_tokens", "input_tokens")
    output_tokens = _first_count(usage, "completion_tokens", "output_tokens")
    cached = _first_count(usage, "prompt_cache_hit_tokens", "cached_input_tokens")
    if cached is None:
        cached = _first_count(details, "cached_tokens")
    total = _first_count(usage, "total_tokens")
    if input_tokens is not None and output_tokens is not None:
        source = InferenceUsageSource.PROVIDER_REPORTED
    elif any(value is not None for value in (input_tokens, output_tokens, cached, total)):
        source = InferenceUsageSource.PARTIAL
    else:
        source = InferenceUsageSource.UNAVAILABLE
    provider_request_id = payload.get("id")
    if not isinstance(provider_request_id, str) or not 0 < len(provider_request_id) <= 128:
        provider_request_id = None
    return ProviderTokenUsage(
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        cached_input_tokens=cached,
        total_tokens=total,
        source=source,
        provider_request_id=provider_request_id,
    )


def _nonnegative_decimal(value: Any) -> Decimal | None:
    try:
        parsed = Decimal(str(value))
    except (TypeError, InvalidOperation, ValueError):
        return None
    if not parsed.is_finite() or parsed < 0:
        return None
    return parsed


def _configured_prices() -> Mapping[str, Any]:
    raw = os.getenv(_PRICE_CONFIG_ENV, "").strip()
    if not raw:
        return {}
    try:
        configured = json.loads(raw)
    except (TypeError, ValueError):
        logger.warning("[inference-metering] invalid_price_config")
        return {}
    if not isinstance(configured, dict):
        logger.warning("[inference-metering] invalid_price_config_shape")
        return {}
    return configured


def estimate_cost(
    *,
    usage: ProviderTokenUsage,
    provider: str,
    model: str,
    price_book: Mapping[str, Any] | None = None,
) -> tuple[Decimal | None, dict[str, str]]:
    """Quote USD using an explicit versioned rate snapshot; never guess rates."""
    if usage.source is not InferenceUsageSource.PROVIDER_REPORTED:
        return None, {}
    if price_book is None:
        price_book = _configured_prices()
    quote = price_book.get(f"{provider}:{model}")
    if not isinstance(quote, Mapping):
        return None, {}
    version = quote.get("version")
    if not isinstance(version, str) or not version.strip() or len(version) > 128:
        return None, {}
    input_rate = _nonnegative_decimal(quote.get("input_usd_per_million"))
    output_rate = _nonnegative_decimal(quote.get("output_usd_per_million"))
    if input_rate is None or output_rate is None:
        return None, {}
    cached = usage.cached_input_tokens
    if cached is not None and cached > (usage.input_tokens or 0):
        return None, {}
    cached_rate: Decimal | None = None
    if cached:
        cached_rate = _nonnegative_decimal(quote.get("cached_input_usd_per_million"))
        if cached_rate is None:
            return None, {}
    input_tokens = usage.input_tokens or 0
    output_tokens = usage.output_tokens or 0
    ordinary_input = input_tokens - (cached or 0)
    total_cost = (
        Decimal(ordinary_input) * input_rate
        + Decimal(output_tokens) * output_rate
        + Decimal(cached or 0) * (cached_rate or Decimal("0"))
    ) / _MILLION
    snapshot = {
        "version": version.strip(),
        "input_usd_per_million": str(input_rate),
        "output_usd_per_million": str(output_rate),
    }
    if cached_rate is not None:
        snapshot["cached_input_usd_per_million"] = str(cached_rate)
    return total_cost.quantize(_COST_QUANTUM, rounding=ROUND_HALF_UP), snapshot


def _event_hash(
    *,
    account_id: str,
    thread_id: int,
    request_id: str,
    provider_attempt_id: str,
    provider: str,
    model: str,
    usage: ProviderTokenUsage,
) -> str:
    payload = {
        "account_id": account_id,
        "thread_id": thread_id,
        "request_id": request_id,
        "provider_attempt_id": provider_attempt_id,
        "provider": provider,
        "model": model,
        "input_tokens": usage.input_tokens,
        "output_tokens": usage.output_tokens,
        "cached_input_tokens": usage.cached_input_tokens,
        "total_tokens": usage.total_tokens,
        "usage_source": usage.source.value,
        "provider_request_id": usage.provider_request_id,
    }
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def record_inference_attempt(
    session: Session,
    *,
    account_id: str,
    thread_id: int,
    request_id: str,
    provider_attempt_id: str,
    provider: str,
    model: str,
    output: Any,
    price_book: Mapping[str, Any] | None = None,
) -> InferenceUsageEvent:
    """Insert once per real provider attempt; never update or overwrite.

    The thread's persisted owner, not a caller-supplied account header, is the
    authority. A repeated attempt with different units fails as a collision.
    The caller controls the transaction; DB failures must not alter inference.
    """
    if not account_id or not request_id or not provider_attempt_id or not provider or not model:
        raise ValueError("inference_metering_identity_missing")
    thread = session.get(ChatThread, int(thread_id))
    if (
        thread is None
        or thread.user_id != account_id
        or session.get(User, account_id) is None
    ):
        raise PermissionError("inference_metering_account_thread_mismatch")

    usage = extract_provider_usage(output)
    estimated_cost, price_snapshot = estimate_cost(
        usage=usage, provider=provider, model=model, price_book=price_book
    )
    payload_hash = _event_hash(
        account_id=account_id,
        thread_id=int(thread_id),
        request_id=request_id,
        provider_attempt_id=provider_attempt_id,
        provider=provider,
        model=model,
        usage=usage,
    )
    criteria = (
        InferenceUsageEvent.account_id == account_id,
        InferenceUsageEvent.provider_attempt_id == provider_attempt_id,
    )
    existing = session.scalar(select(InferenceUsageEvent).where(*criteria))
    if existing is not None:
        if existing.payload_hash != payload_hash:
            raise ValueError("inference_metering_idempotency_conflict")
        return existing

    event = InferenceUsageEvent(
        account_id=account_id,
        thread_id=int(thread_id),
        request_id=request_id,
        provider_attempt_id=provider_attempt_id,
        provider=provider,
        model=model,
        provider_request_id=usage.provider_request_id,
        input_tokens=usage.input_tokens,
        output_tokens=usage.output_tokens,
        cached_input_tokens=usage.cached_input_tokens,
        total_tokens=usage.total_tokens,
        usage_source=usage.source.value,
        estimated_cost_usd=estimated_cost,
        cost_source=(
            InferenceCostSource.RATE_SNAPSHOT_ESTIMATE.value
            if estimated_cost is not None
            else InferenceCostSource.UNAVAILABLE.value
        ),
        price_snapshot=price_snapshot,
        payload_hash=payload_hash,
    )
    try:
        # A SAVEPOINT preserves the enclosing chat transaction on a collision.
        with session.begin_nested():
            session.add(event)
            session.flush()
    except IntegrityError:
        existing = session.scalar(select(InferenceUsageEvent).where(*criteria))
        if existing is None:
            raise
        if existing.payload_hash != payload_hash:
            raise ValueError("inference_metering_idempotency_conflict") from None
        return existing
    return event


def account_inference_totals(
    session: Session,
    *,
    account_id: str | None = None,
    limit: int = 100,
) -> list[dict[str, Any]]:
    """Content-free administrator aggregation; NULL costs stay visible as gaps."""
    event = InferenceUsageEvent
    query = select(
        event.account_id.label("account_id"),
        func.count(event.id).label("attempts"),
        func.coalesce(func.sum(event.input_tokens), 0).label("input_tokens"),
        func.coalesce(func.sum(event.output_tokens), 0).label("output_tokens"),
        func.coalesce(func.sum(event.estimated_cost_usd), 0).label("estimated_cost_usd"),
        func.sum(case((event.usage_source != InferenceUsageSource.PROVIDER_REPORTED.value, 1), else_=0)).label("unknown_or_partial_usage_attempts"),
        func.sum(case((event.cost_source == InferenceCostSource.UNAVAILABLE.value, 1), else_=0)).label("unpriced_attempts"),
    )
    if account_id is not None:
        query = query.where(event.account_id == account_id)
    query = query.group_by(event.account_id).order_by(event.account_id).limit(min(max(limit, 1), 100))
    rows = session.execute(query).all()
    return [
        {
            "account_id": row.account_id,
            "attempts": int(row.attempts),
            "provider_reported_input_tokens": int(row.input_tokens),
            "provider_reported_output_tokens": int(row.output_tokens),
            "estimated_cost_usd": str(row.estimated_cost_usd),
            "unknown_or_partial_usage_attempts": int(row.unknown_or_partial_usage_attempts),
            "unpriced_attempts": int(row.unpriced_attempts),
            "cost_is_complete": int(row.unpriced_attempts) == 0,
        }
        for row in rows
    ]
