"""Inactive, internal voice reservation core; no policy issuer or dispatch API.

Trusted server callers supply policy/credential references, quotes and final wire
digests. These values are not grants. Exactly one dispatch may be claimed per
reservation; a multi-chunk synthesis needs independently reserved child attempts.
Nothing here reads configuration, seeds funding, authorizes a provider or sends
audio. Runtime qualification and the existing quarantine remain independent.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from hashlib import sha256
import json
from urllib.parse import urlsplit

from sqlalchemy import select

from guardian.core.project_ownership import classify_project_ownership
from guardian.core.preview_access import is_private_preview, role_for_preview_email
from guardian.db.models import (
    ChatMessage,
    ChatThread,
    InferenceBudgetWindow,
    Project,
    User,
    VoiceBudgetAllocation,
    VoiceBudgetDispatch,
    VoiceBudgetReservation,
)
from guardian.metering.tokens import (
    InferenceBudgetState,
    VoiceBillingUnit,
    VoiceBudgetService,
    VoicePayerKind,
)

MAX_UNITS = 10**15


def _now():
    return datetime.now(timezone.utc)


def _integer(value, minimum=0, maximum=MAX_UNITS):
    if type(value) is not int or not minimum <= value <= maximum:
        raise ValueError("invalid_voice_budget_integer")


def _identifier(value, maximum=128):
    if (
        type(value) is not str
        or not 0 < len(value) <= maximum
        or any(c.isspace() or ord(c) < 32 or ord(c) == 127 for c in value)
    ):
        raise ValueError("invalid_voice_budget_identifier")


def _digest(value):
    if (
        type(value) is not str
        or len(value) != 64
        or any(c not in "0123456789abcdef" for c in value)
    ):
        raise ValueError("invalid_voice_budget_digest")


def _date(value):
    if (
        not isinstance(value, datetime)
        or value.tzinfo is None
        or value.utcoffset() is None
    ):
        raise ValueError("voice_budget_aware_time_required")


def _hash(value):
    return sha256(
        json.dumps(
            value, sort_keys=True, separators=(",", ":"), allow_nan=False
        ).encode()
    ).hexdigest()


def assistant_content_hash(content: str) -> str:
    """Bind the exact stripped historical assistant text, without retaining it."""
    if type(content) is not str or not content.strip():
        raise ValueError("voice_budget_assistant_content_required")
    return sha256(content.strip().encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class VoicePayerDescriptor:
    """Trusted route; not proof that a key or funding is account-owned.

    The future production resolver must map each opaque payer_scope to its
    canonical route, credential and distinct windows. This core does not look up
    keys, infer ownership, select fallback payers or issue a funding policy.
    """

    kind: VoicePayerKind
    payer_scope: str
    credential_ref: str
    owner_account_id: str | None = None

    def __post_init__(self):
        if type(self.kind) is not VoicePayerKind:
            raise ValueError("typed_voice_payer_required")
        _identifier(self.payer_scope)
        _identifier(self.credential_ref)
        if self.kind == VoicePayerKind.ACCOUNT_OWNED:
            _identifier(self.owner_account_id, 255)
        elif self.owner_account_id is not None:
            raise ValueError("voice_sponsor_cannot_claim_account_ownership")


@dataclass(frozen=True)
class VoiceBudgetBinding:
    account_id: str
    thread_id: int
    project_id: int | None
    settings_digest: str
    payer: VoicePayerDescriptor
    policy_digest: str
    endpoint: str
    model: str
    session_id: str | None = None
    message_id: int | None = None
    content_hash: str | None = None
    mip_opt_out: bool = True

    def __post_init__(self):
        _identifier(self.account_id, 255)
        _integer(self.thread_id, 1, 2**31 - 1)
        if self.project_id is not None:
            _integer(self.project_id, 1, 2**31 - 1)
        for value in (self.settings_digest, self.policy_digest):
            _digest(value)
        _identifier(self.model)
        if type(self.payer) is not VoicePayerDescriptor:
            raise ValueError("typed_voice_payer_required")
        if (
            self.payer.kind == VoicePayerKind.ACCOUNT_OWNED
            and self.payer.owner_account_id != self.account_id
        ):
            raise PermissionError("voice_payer_account_mismatch")
        if self.mip_opt_out is not True:
            raise ValueError("voice_budget_opt_out_required")
        if type(self.endpoint) is not str:
            raise ValueError("invalid_voice_budget_endpoint")
        parsed = urlsplit(self.endpoint)
        if (
            parsed.username
            or parsed.password
            or parsed.query
            or parsed.fragment
            or parsed.port
        ):
            raise ValueError("invalid_voice_budget_endpoint")
        if self.session_id is not None:
            _identifier(self.session_id)
            if self.message_id is not None or self.content_hash is not None:
                raise ValueError("invalid_voice_budget_source")
            allowed = {"wss://agent.deepgram.com/v1/agent/converse"}
        else:
            _integer(self.message_id, 1, 2**63 - 1)
            _digest(self.content_hash)
            allowed = {
                f"https://api.deepgram.com/v{version}/speak" for version in (1, 2)
            }
        if self.endpoint not in allowed:
            raise ValueError("invalid_voice_budget_endpoint")

    @property
    def service(self) -> VoiceBudgetService:
        return (
            VoiceBudgetService.AGENT
            if self.session_id is not None
            else VoiceBudgetService.SPEAK
        )


@dataclass(frozen=True)
class VoicePriceQuote:
    """Explicit integer nanodollar arithmetic, never a real-price assertion.

    Quantity is rounded UP to quantity_increment, then raised to minimum_quantity.
    unit_price_units is USD nanounits per unit_size of the stated voice dimension.
    All applicable charges must be covered by trusted caller evidence; this core
    cannot establish account eligibility or a provider's billable-close behavior.
    """

    version: str
    source: str
    effective_at: datetime
    expires_at: datetime
    unit_contract: VoiceBillingUnit
    unit_size: int
    unit_price_units: int
    quantity_increment: int = 1
    minimum_quantity: int = 0
    fixed_units: int = 0

    def __post_init__(self):
        _identifier(self.version)
        _identifier(self.source, 512)
        if type(self.unit_contract) is not VoiceBillingUnit:
            raise ValueError("unsupported_voice_billing_units")
        for value in (self.effective_at, self.expires_at):
            _date(value)
        if self.expires_at <= self.effective_at:
            raise ValueError("invalid_voice_quote_interval")
        for value in (self.unit_size, self.unit_price_units, self.quantity_increment):
            _integer(value, 1)
        for value in (self.minimum_quantity, self.fixed_units):
            _integer(value)

    def price(self, quantity: int) -> int:
        _integer(quantity, 0, 10**12)
        increment = self.quantity_increment
        billed = max(
            self.minimum_quantity, ((quantity + increment - 1) // increment) * increment
        )
        amount = (
            self.fixed_units
            + (billed * self.unit_price_units + self.unit_size - 1) // self.unit_size
        )
        _integer(amount)
        return amount

    def snapshot(self) -> dict:
        return asdict(self) | {
            "effective_at": self.effective_at.isoformat(),
            "expires_at": self.expires_at.isoformat(),
            "unit_contract": self.unit_contract.value,
        }

    @classmethod
    def from_snapshot(cls, value: dict):
        value = dict(value)
        for key in ("effective_at", "expires_at"):
            value[key] = datetime.fromisoformat(value[key])
        value["unit_contract"] = VoiceBillingUnit(value["unit_contract"])
        return cls(**value)


class VoiceBudgetLedger:
    """Internal PostgreSQL transactions; committed claim precedes any I/O.

    No authentication, current policy resolver, issuance or activation is added.
    Caller authority is exactly the trusted-server boundary of BudgetLedger.
    Settlement/release do not require surviving account rows: deletion must not
    erase an already claimed financial liability or prevent its reconciliation.
    """

    def __init__(self, sessions):
        self.sessions = sessions

    @staticmethod
    def _postgres(session):
        if session.get_bind().dialect.name != "postgresql":
            raise RuntimeError("voice_budget_requires_postgresql")

    @staticmethod
    def _custody(session, binding):
        thread = session.scalar(
            select(ChatThread)
            .where(ChatThread.id == binding.thread_id)
            .with_for_update()
        )
        user = session.scalar(
            select(User).where(User.id == binding.account_id).with_for_update()
        )
        if (
            thread is None
            or user is None
            or thread.user_id != binding.account_id
            or thread.project_id != binding.project_id
            or thread.archived_at is not None
        ):
            raise PermissionError("voice_budget_custody_mismatch")
        if binding.project_id is not None:
            project = session.scalar(
                select(Project)
                .where(Project.id == binding.project_id)
                .with_for_update()
            )
            ownership = classify_project_ownership(project)
            if (
                project is None
                or ownership.canonical_owner_id != binding.account_id
                or ownership.has_authority_conflict
                or project.archived_at is not None
            ):
                raise PermissionError("voice_budget_project_custody_mismatch")
        if (
            is_private_preview()
            and role_for_preview_email(user.email or user.id) is None
        ):
            raise PermissionError("voice_budget_preview_ineligible")
        if binding.message_id is not None:
            message = session.scalar(
                select(ChatMessage)
                .where(ChatMessage.id == binding.message_id)
                .with_for_update()
            )
            if (
                message is None
                or message.thread_id != binding.thread_id
                or message.user_id != binding.account_id
                or message.role != "assistant"
                or assistant_content_hash(message.content) != binding.content_hash
            ):
                raise PermissionError("voice_budget_message_custody_mismatch")

    @staticmethod
    def _windows(session, ids):
        return list(
            session.scalars(
                select(InferenceBudgetWindow)
                .where(InferenceBudgetWindow.id.in_(ids))
                .order_by(InferenceBudgetWindow.id)
                .with_for_update()
            )
        )

    @staticmethod
    def _active(windows, payer, now, additional=0):
        if len(windows) != 2 or {w.kind for w in windows} != {"monthly", "funding"}:
            raise ValueError("monthly_and_funding_budgets_required")
        for window in windows:
            if window.payer_scope != payer or window.provider != (
                "deepgram" if window.kind == "funding" else "*"
            ):
                raise PermissionError("voice_budget_scope_mismatch")
            if not window.enabled or not window.starts_at <= now < window.ends_at:
                raise PermissionError("voice_budget_window_inactive")
            if window.spent_units + window.held_units + additional > window.limit_units:
                raise PermissionError("voice_budget_exhausted")

    def reserve(
        self,
        *,
        attempt_id,
        binding,
        payer_scope,
        budget_ids,
        quantity_ceiling,
        quote,
        dispatch_digest,
    ):
        for value in (attempt_id, payer_scope):
            _identifier(value)
        if (
            type(binding) is not VoiceBudgetBinding
            or type(quote) is not VoicePriceQuote
        ):
            raise ValueError("typed_voice_binding_and_quote_required")
        if payer_scope != binding.payer.payer_scope:
            raise PermissionError("voice_payer_scope_mismatch")
        _digest(dispatch_digest)
        _integer(quantity_ceiling, 1, 10**12)
        expected_unit = (
            VoiceBillingUnit.CONNECTION_MS
            if binding.session_id is not None
            else VoiceBillingUnit.SYNTHESIS_CHARACTERS
        )
        if quote.unit_contract != expected_unit:
            raise ValueError("voice_billing_source_mismatch")
        if not isinstance(budget_ids, (list, tuple)) or len(budget_ids) != 2:
            raise ValueError("monthly_and_funding_budgets_required")
        for value in budget_ids:
            _identifier(value)
        if len(set(budget_ids)) != 2:
            raise ValueError("monthly_and_funding_budgets_required")
        snapshot, saved_binding = quote.snapshot(), asdict(binding)
        upper = quote.price(quantity_ceiling)
        _integer(upper, 1)
        digest = _hash(
            dict(
                binding=saved_binding,
                quote=snapshot,
                payer=payer_scope,
                budgets=sorted(budget_ids),
                quantity=quantity_ceiling,
                dispatch=dispatch_digest,
            )
        )
        with self.sessions.begin() as session:
            self._postgres(session)
            self._custody(session, binding)
            windows = self._windows(session, budget_ids)
            now = _now()
            if not quote.effective_at <= now < quote.expires_at:
                raise PermissionError("voice_budget_quote_inactive")
            self._active(windows, payer_scope, now)
            previous = session.get(VoiceBudgetReservation, attempt_id)
            if previous is not None:
                if previous.payload_hash != digest:
                    raise ValueError("voice_budget_idempotency_conflict")
                return previous.reserved_units
            self._active(windows, payer_scope, now, upper)
            session.add(
                VoiceBudgetReservation(
                    id=attempt_id,
                    account_id=binding.account_id,
                    thread_id=binding.thread_id,
                    binding_snapshot=saved_binding,
                    payer_scope=payer_scope,
                    provider="deepgram",
                    budget_ids=sorted(budget_ids),
                    unit_contract=quote.unit_contract.value,
                    quantity_ceiling=quantity_ceiling,
                    reserved_units=upper,
                    state=InferenceBudgetState.RESERVED.value,
                    price_snapshot=snapshot,
                    payload_hash=digest,
                    dispatch_digest=dispatch_digest,
                )
            )
            session.flush()
            for window in windows:
                window.held_units += upper
                session.add(
                    VoiceBudgetAllocation(attempt_id=attempt_id, window_id=window.id)
                )
        return upper

    def _locked(self, session, attempt_id, account_id):
        self._postgres(session)
        _identifier(attempt_id)
        _identifier(account_id, 255)
        row = session.scalar(
            select(VoiceBudgetReservation)
            .where(VoiceBudgetReservation.id == attempt_id)
            .with_for_update()
        )
        if row is None or row.account_id != account_id:
            raise PermissionError("voice_budget_not_owned")
        return row

    def _allocated_windows(self, session, row):
        ids = list(
            session.scalars(
                select(VoiceBudgetAllocation.window_id).where(
                    VoiceBudgetAllocation.attempt_id == row.id
                )
            )
        )
        if len(ids) != 2 or sorted(ids) != row.budget_ids:
            raise ValueError("voice_budget_allocation_missing")
        windows = self._windows(session, ids)
        if len(windows) != 2:
            raise ValueError("voice_budget_allocation_missing")
        if any(window.held_units < row.reserved_units for window in windows):
            raise ValueError("voice_budget_hold_inconsistent")
        return windows

    def claim(self, *, attempt_id, binding, dispatch_digest) -> bool:
        if type(binding) is not VoiceBudgetBinding:
            raise ValueError("typed_voice_binding_required")
        _digest(dispatch_digest)
        with self.sessions.begin() as session:
            row = self._locked(session, attempt_id, binding.account_id)
            if (
                row.binding_snapshot != asdict(binding)
                or row.dispatch_digest != dispatch_digest
            ):
                raise PermissionError("voice_budget_dispatch_mismatch")
            if row.state != InferenceBudgetState.RESERVED.value:
                return False
            self._custody(session, binding)
            windows = self._allocated_windows(session, row)
            now = _now()
            quote = VoicePriceQuote.from_snapshot(row.price_snapshot)
            if not quote.effective_at <= now < quote.expires_at:
                raise PermissionError("voice_budget_quote_inactive")
            self._active(windows, row.payer_scope, now)
            session.add(
                VoiceBudgetDispatch(attempt_id=row.id, dispatch_digest=dispatch_digest)
            )
            row.state = InferenceBudgetState.DISPATCHED.value
        return True

    def release_unclaimed(self, *, attempt_id, account_id) -> bool:
        with self.sessions.begin() as session:
            row = self._locked(session, attempt_id, account_id)
            if (
                row.state != InferenceBudgetState.RESERVED.value
                or session.get(VoiceBudgetDispatch, attempt_id) is not None
            ):
                return False
            for window in self._allocated_windows(session, row):
                window.held_units -= row.reserved_units
            row.state = InferenceBudgetState.RELEASED.value
        return True

    def settle(
        self,
        *,
        attempt_id,
        account_id,
        observed_quantity,
        provider_request_id,
        reported_model,
    ) -> bool:
        """Trusted complete receipt only; no inference from timeout or cancellation.

        This estimates the saved tariff, not an invoice or a refund authority.
        Missing/unrecognized units or model identity retain the entire hold.
        """
        with self.sessions.begin() as session:
            row = self._locked(session, attempt_id, account_id)
            if (
                observed_quantity is None
                or provider_request_id is None
                or reported_model is None
            ):
                return False
            _integer(observed_quantity, 0, 10**12)
            _identifier(provider_request_id)
            if reported_model != row.binding_snapshot["model"]:
                return False
            receipt = dict(
                quantity=observed_quantity,
                provider_request_id=provider_request_id,
                reported_model=reported_model,
                dispatch_digest=row.dispatch_digest,
            )
            digest = _hash(receipt)
            if row.state == InferenceBudgetState.SETTLED.value:
                if row.settlement_hash != digest:
                    raise ValueError("voice_budget_settlement_conflict")
                return True
            if (
                row.state != InferenceBudgetState.DISPATCHED.value
                or session.get(VoiceBudgetDispatch, attempt_id) is None
            ):
                raise ValueError("voice_budget_not_dispatched")
            units = VoicePriceQuote.from_snapshot(row.price_snapshot).price(
                observed_quantity
            )
            for window in self._allocated_windows(session, row):
                window.held_units -= row.reserved_units
                window.spent_units += units
            row.settled_units, row.settlement_usage, row.settlement_hash = (
                units,
                receipt,
                digest,
            )
            row.state = InferenceBudgetState.SETTLED.value
        return True
