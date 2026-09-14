"""ADR-087 accepted chat deadline authority; no execution enforcement."""

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Mapping

ACCEPTED_CHAT_TASK_WORK_BUDGET_SECONDS = 720
ACCEPTED_CHAT_TASK_TERMINAL_BUDGET_SECONDS = 60
ACCEPTED_CHAT_TASK_TOTAL_BUDGET_SECONDS = (
    ACCEPTED_CHAT_TASK_WORK_BUDGET_SECONDS + ACCEPTED_CHAT_TASK_TERMINAL_BUDGET_SECONDS
)
TURN_LOCK_SAFETY_MARGIN_SECONDS = 60
ACCEPTED_CHAT_TASK_TURN_LOCK_LEASE_SECONDS = (
    ACCEPTED_CHAT_TASK_TOTAL_BUDGET_SECONDS + TURN_LOCK_SAFETY_MARGIN_SECONDS
)
DEADLINE_FIELDS = ("accepted_at", "work_deadline_at", "terminal_deadline_at")


def _utc(instant: datetime) -> datetime:
    if not isinstance(instant, datetime) or instant.utcoffset() is None:
        raise ValueError("accepted chat deadline requires aware timestamps")
    return instant.astimezone(timezone.utc)


@dataclass(frozen=True)
class AcceptedChatTaskDeadline:
    accepted_at: datetime
    work_deadline_at: datetime
    terminal_deadline_at: datetime

    def __post_init__(self) -> None:
        for name in DEADLINE_FIELDS:
            object.__setattr__(self, name, _utc(getattr(self, name)))
        if (
            self.work_deadline_at - self.accepted_at
            != timedelta(seconds=ACCEPTED_CHAT_TASK_WORK_BUDGET_SECONDS)
            or self.terminal_deadline_at - self.accepted_at
            != timedelta(seconds=ACCEPTED_CHAT_TASK_TOTAL_BUDGET_SECONDS)
            or self.terminal_deadline_at - self.work_deadline_at
            != timedelta(seconds=ACCEPTED_CHAT_TASK_TERMINAL_BUDGET_SECONDS)
        ):
            raise ValueError("accepted chat deadline intervals are invalid")

    def to_dict(self) -> dict[str, str]:
        return {name: getattr(self, name).isoformat() for name in DEADLINE_FIELDS}


def build_accepted_chat_task_deadline(now: datetime) -> AcceptedChatTaskDeadline:
    accepted = _utc(now)
    return AcceptedChatTaskDeadline(
        accepted,
        accepted + timedelta(seconds=ACCEPTED_CHAT_TASK_WORK_BUDGET_SECONDS),
        accepted + timedelta(seconds=ACCEPTED_CHAT_TASK_TOTAL_BUDGET_SECONDS),
    )


def parse_accepted_chat_task_deadline(
    payload: Mapping[str, Any],
) -> AcceptedChatTaskDeadline | None:
    """Validate without repairing input; absent keys alone denote legacy data."""
    present = [name in payload for name in DEADLINE_FIELDS]
    if not any(present):
        return None
    if not all(present):
        raise ValueError("accepted chat deadline snapshot is incomplete")
    try:
        values = [payload[name] for name in DEADLINE_FIELDS]
        if any(not isinstance(value, str) for value in values):
            raise ValueError
        return AcceptedChatTaskDeadline(
            *(datetime.fromisoformat(value) for value in values)
        )
    except (TypeError, ValueError, OverflowError):
        raise ValueError("accepted chat deadline snapshot is invalid") from None
