"""Internal atomic budget ledger for the opt-in bounded runtime.

Only a trusted, operator-owned execution service may use this ledger. Provider
calls must occur AFTER claim() commits. A false claim result must never dispatch.
Client/self-host reports cannot authorize or settle operator-funded inference.
"""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal, ROUND_CEILING
from hashlib import sha256
from collections.abc import Mapping
import json

from sqlalchemy import select

from guardian.db.models import (
    ChatCompletionAttempt,
    ChatThread,
    InferenceBudgetWindow,
    InferenceBudgetReservation,
    InferenceBudgetAllocation,
)
from guardian.metering.ledger import estimate_cost, extract_provider_usage
from guardian.metering.tokens import InferenceBudgetState

NANO = Decimal(1_000_000_000)
MAX_UNITS = 10**15


def _units(value: Decimal) -> int:
    if not value.is_finite() or value < 0:
        raise ValueError("invalid_cost")
    units = int((value * NANO).to_integral_value(rounding=ROUND_CEILING))
    if units > MAX_UNITS:
        raise ValueError("cost_out_of_range")
    return units


def _quote(quote: dict, provider: str, model: str) -> dict:
    """Require provenance and an explicit bounded token-only billing contract."""
    result = dict(quote)
    for field in ("version", "source", "effective_at"):
        if not isinstance(result.get(field), str) or not result[field].strip():
            raise ValueError("price_provenance_required")
    effective = datetime.fromisoformat(result["effective_at"].replace("Z", "+00:00"))
    if effective.tzinfo is None or effective > datetime.now(timezone.utc):
        raise ValueError("price_effective_time_invalid")
    if result.get("unit_contract") != "bounded_text_tokens_only":
        raise ValueError("unsupported_billing_units")
    for field in (
        "input_usd_per_million",
        "output_usd_per_million",
        "cached_input_usd_per_million",
    ):
        rate = Decimal(str(result[field]))
        _units(rate)
        result[field] = str(rate)
    result.update(provider=provider, model=model)
    return result


class BudgetLedger:
    """Each operation owns one transaction; database failures never admit spend.

    PostgreSQL row locks serialize multi-worker admission. Fixed windows never
    reset in place: old reservations remain against their original windows.
    All IDs and price books must come from trusted policy, NOT request payloads.
    No authentication, entitlement, policy activation, or provider dispatch API
    is provided here; those remain separately reviewed integration gates.
    """

    def __init__(self, sessions):
        self.sessions = sessions

    @staticmethod
    def _postgres(session):
        if session.get_bind().dialect.name != "postgresql":
            raise RuntimeError("budget_requires_postgresql")

    @staticmethod
    def _owner(session, account, request):
        binding = session.get(ChatCompletionAttempt, request)
        thread = session.get(ChatThread, binding.thread_id) if binding else None
        if (
            not binding
            or binding.accepted_account_id != account
            or not thread
            or thread.user_id != account
        ):
            raise PermissionError("budget_account_custody_mismatch")
        return binding.thread_id

    def reserve(
        self,
        *,
        attempt_id: str,
        account_id: str,
        request_id: str,
        payer_scope: str,
        provider: str,
        model: str,
        budget_ids: list[str],
        input_ceiling: int,
        output_ceiling: int,
        quote: dict,
        dispatch_digest: str | None = None,
        expected_thread_id: int | None = None,
        expected_task_id: str | None = None,
    ) -> int:
        """Reserve one bounded provider attempt against monthly AND funding pools."""
        for value in (attempt_id, account_id, request_id, payer_scope, provider, model):
            if not isinstance(value, str) or not value.strip() or len(value) > 128:
                raise ValueError("invalid_budget_identity")
        if len(budget_ids) != 2 or len(set(budget_ids)) != 2:
            raise ValueError("monthly_and_funding_budgets_required")
        for count in (input_ceiling, output_ceiling):
            if type(count) is not int or not 0 <= count <= 10**9:
                raise ValueError("invalid_token_ceiling")
        if dispatch_digest is not None and (
            not isinstance(dispatch_digest, str)
            or len(dispatch_digest) != 64
            or any(c not in "0123456789abcdef" for c in dispatch_digest)
        ):
            raise ValueError("invalid_dispatch_digest")
        snapshot = _quote(quote, provider, model)
        # Cache discounts are not assumed; a cache premium must also be bounded.
        input_rate = max(
            Decimal(snapshot["input_usd_per_million"]),
            Decimal(snapshot["cached_input_usd_per_million"]),
        )
        upper = _units(
            (
                input_ceiling * input_rate
                + output_ceiling * Decimal(snapshot["output_usd_per_million"])
            )
            / 1_000_000
        )
        if upper == 0:
            raise ValueError("paid_reservation_must_be_positive")
        payload = dict(
            account=account_id,
            request=request_id,
            payer=payer_scope,
            provider=provider,
            model=model,
            budgets=sorted(budget_ids),
            input=input_ceiling,
            output=output_ceiling,
            quote=snapshot,
            dispatch_digest=dispatch_digest,
        )
        digest = sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()
        with self.sessions.begin() as session:
            self._postgres(session)
            thread_id = self._owner(session, account_id, request_id)
            binding = session.get(ChatCompletionAttempt, request_id)
            if (expected_thread_id is not None and thread_id != expected_thread_id) or (
                expected_task_id is not None
                and binding.backend_task_id != expected_task_id
            ):
                raise PermissionError("budget_accepted_task_mismatch")
            # Same global lock order for every admission prevents pool deadlocks.
            windows = list(
                session.scalars(
                    select(InferenceBudgetWindow)
                    .where(InferenceBudgetWindow.id.in_(budget_ids))
                    .order_by(InferenceBudgetWindow.id)
                    .with_for_update()
                )
            )
            if len(windows) != 2 or {w.kind for w in windows} != {"monthly", "funding"}:
                raise ValueError("monthly_and_funding_budgets_required")
            previous = session.get(InferenceBudgetReservation, attempt_id)
            if previous:
                if previous.payload_hash != digest:
                    raise ValueError("budget_idempotency_conflict")
                return previous.reserved_units
            now = datetime.now(timezone.utc)
            for window in windows:
                if window.payer_scope != payer_scope or window.provider != (
                    provider if window.kind == "funding" else "*"
                ):
                    raise PermissionError("budget_scope_mismatch")
                if not window.enabled or not window.starts_at <= now < window.ends_at:
                    raise PermissionError("budget_window_inactive")
                if window.spent_units + window.held_units + upper > window.limit_units:
                    raise PermissionError("budget_exhausted")
            row = InferenceBudgetReservation(
                id=attempt_id,
                account_id=account_id,
                request_id=request_id,
                thread_id=thread_id,
                payer_scope=payer_scope,
                provider=provider,
                model=model,
                reserved_units=upper,
                state=InferenceBudgetState.RESERVED.value,
                input_ceiling=input_ceiling,
                output_ceiling=output_ceiling,
                price_snapshot=snapshot,
                payload_hash=digest,
            )
            session.add(row)
            session.flush()
            for window in windows:
                window.held_units += upper
                session.add(
                    InferenceBudgetAllocation(
                        attempt_id=attempt_id, window_id=window.id
                    )
                )
        return upper

    def _locked(self, session, attempt_id, account_id):
        self._postgres(session)
        row = session.scalar(
            select(InferenceBudgetReservation)
            .where(InferenceBudgetReservation.id == attempt_id)
            .with_for_update()
        )
        if not row or row.account_id != account_id:
            raise PermissionError("budget_reservation_not_owned")
        return row

    def _windows(self, session, row):
        ids = select(InferenceBudgetAllocation.window_id).where(
            InferenceBudgetAllocation.attempt_id == row.id
        )
        return list(
            session.scalars(
                select(InferenceBudgetWindow)
                .where(InferenceBudgetWindow.id.in_(ids))
                .order_by(InferenceBudgetWindow.id)
                .with_for_update()
            )
        )

    def claim(self, *, attempt_id, account_id) -> bool:
        """At-most-once dispatch permit; commit before any network request.

        Crash after commit is ambiguous: never reclaim or release automatically.
        The caller must dispatch the EXACT saved model and ceilings, and honor
        current trusted policy. This primitive alone does not prove enforcement.
        """
        with self.sessions.begin() as session:
            row = self._locked(session, attempt_id, account_id)
            if row.state != InferenceBudgetState.RESERVED.value:
                return False
            self._owner(session, account_id, row.request_id)
            now = datetime.now(timezone.utc)
            for window in self._windows(session, row):
                if not window.enabled or not window.starts_at <= now < window.ends_at:
                    raise PermissionError("budget_window_inactive")
                if window.spent_units + window.held_units > window.limit_units:
                    raise PermissionError("budget_exhausted")
            row.state = InferenceBudgetState.DISPATCHED.value
        return True

    def release_unclaimed(self, *, attempt_id, account_id) -> bool:
        """Release only while dispatch was never claimed. Timeout is not proof."""
        with self.sessions.begin() as session:
            row = self._locked(session, attempt_id, account_id)
            if row.state != InferenceBudgetState.RESERVED.value:
                return False
            for window in self._windows(session, row):
                window.held_units -= row.reserved_units
            row.state = InferenceBudgetState.RELEASED.value
        return True

    def settle(self, *, attempt_id, account_id, output) -> bool:
        """Trusted provider response only. Missing usage retains the entire hold.

        A measured overrun is recorded honestly and blocks subsequent admission;
        it cannot be erased to make an invalid upper-bound estimate look safe.
        """
        with self.sessions.begin() as session:
            row = self._locked(session, attempt_id, account_id)
            raw = getattr(output, "raw_payload", output)
            reported_model = raw.get("model") if isinstance(raw, Mapping) else None
            if reported_model is not None and reported_model != row.model:
                # Never settle a normalized/redirected model at the wrong price.
                # Aliases require an independently reviewed resolution contract.
                return False
            usage = extract_provider_usage(output)
            cost, _ = estimate_cost(
                usage=usage,
                provider=row.provider,
                model=row.model,
                price_book={f"{row.provider}:{row.model}": row.price_snapshot},
            )
            if row.state == InferenceBudgetState.SETTLED.value:
                digest = sha256(
                    json.dumps(usage.__dict__, sort_keys=True).encode()
                ).hexdigest()
                if row.settlement_hash != digest:
                    raise ValueError("budget_settlement_conflict")
                return True
            if row.state != InferenceBudgetState.DISPATCHED.value:
                raise ValueError("budget_not_dispatched")
            if cost is None:
                return False
            cached = usage.cached_input_tokens or 0
            snapshot = row.price_snapshot
            exact = (
                (usage.input_tokens - cached)
                * Decimal(snapshot["input_usd_per_million"])
                + cached * Decimal(snapshot["cached_input_usd_per_million"])
                + usage.output_tokens * Decimal(snapshot["output_usd_per_million"])
            ) / 1_000_000
            units = _units(exact)
            for window in self._windows(session, row):
                window.held_units -= row.reserved_units
                window.spent_units += units
            row.settled_units = units
            row.settlement_usage = usage.__dict__ | {"reported_model": reported_model}
            row.settlement_hash = sha256(
                json.dumps(usage.__dict__, sort_keys=True).encode()
            ).hexdigest()
            row.state = InferenceBudgetState.SETTLED.value
        return True


def soft_thresholds(
    *, observed_units: int, held_units: int, allowance_units: int
) -> dict:
    """Operator reconnaissance signal, not an entitlement or denial verdict."""
    if (
        any(
            type(v) is not int or v < 0
            for v in (observed_units, held_units, allowance_units)
        )
        or not allowance_units
    ):
        raise ValueError("invalid_soft_threshold")
    return {
        "reached_percent": [
            p for p in (50, 80, 100) if observed_units * 100 >= allowance_units * p
        ],
        "estimated_spend_units": observed_units,
        "unsettled_hold_units": held_units,
        "deny_inference": False,
    }


def budget_status(
    session,
    *,
    monthly_window: str,
    funding_window: str,
    account_id: str | None = None,
    limit: int = 100,
    account_allowances: dict[str, int] | None = None,
) -> dict:
    """Read-only operator status. Unsettled holds are never called zero spend."""
    from sqlalchemy import case, func

    windows = list(
        session.scalars(
            select(InferenceBudgetWindow).where(
                InferenceBudgetWindow.id.in_([monthly_window, funding_window])
            )
        )
    )
    query = (
        select(
            InferenceBudgetReservation.account_id,
            func.coalesce(func.sum(InferenceBudgetReservation.settled_units), 0),
            func.coalesce(
                func.sum(
                    case(
                        (
                            InferenceBudgetReservation.state.in_(
                                [
                                    InferenceBudgetState.RESERVED.value,
                                    InferenceBudgetState.DISPATCHED.value,
                                ]
                            ),
                            InferenceBudgetReservation.reserved_units,
                        ),
                        else_=0,
                    )
                ),
                0,
            ),
            func.sum(
                case(
                    (
                        InferenceBudgetReservation.state
                        == InferenceBudgetState.DISPATCHED.value,
                        1,
                    ),
                    else_=0,
                )
            ),
        )
        .join(
            InferenceBudgetAllocation,
            InferenceBudgetAllocation.attempt_id == InferenceBudgetReservation.id,
        )
        .where(InferenceBudgetAllocation.window_id == monthly_window)
    )
    if account_id is not None:
        query = query.where(InferenceBudgetReservation.account_id == account_id)
    accounts = []
    for account, spent, held, unresolved in session.execute(
        query.group_by(InferenceBudgetReservation.account_id)
        .order_by(InferenceBudgetReservation.account_id)
        .limit(min(max(limit, 1), 100))
    ):
        entry = dict(
            account_id=account,
            estimated_settled_units=int(spent),
            unsettled_hold_units=int(held),
            unresolved_dispatches=int(unresolved),
            soft_thresholds=None,
        )
        allowance = (account_allowances or {}).get(account)
        if allowance is not None:
            entry["soft_thresholds"] = soft_thresholds(
                observed_units=int(spent),
                held_units=int(held),
                allowance_units=allowance,
            )
        accounts.append(entry)
    return dict(
        scope="bounded_openai_text_chat",
        unit="USD_nanounits",
        cost_basis="versioned_rate_estimates_not_provider_invoice",
        windows=[
            dict(
                id=w.id,
                kind=w.kind,
                limit_units=w.limit_units,
                held_units=w.held_units,
                spent_units=w.spent_units,
                enabled=w.enabled,
            )
            for w in windows
        ],
        accounts=accounts,
        account_reads_restricted=False,
    )
