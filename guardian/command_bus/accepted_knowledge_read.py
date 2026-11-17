"""ADR-112 revalidation fence, not an execution owner or public capability.

The private Command Bus adapter consumes it before replay, each request and
result publication. It is deliberately not wired to chat or HTTP admission.
No provider refresh, ambient credential fallback or network call occurs here.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
import hashlib
import math
import time
from typing import Any

from guardian.command_bus.contracts import InvokeArguments
from guardian.command_bus.redaction_policy import canonical_json, compute_args_hash
from guardian.connections import chat_pilot, knowledge_oauth, oauth_store
from guardian.connections.github.service import normalize_repository
from guardian.core.chat_account_custody import (
    AcceptedChatAccountBinding,
    ChatAccountAcceptancePending,
    resolve_accepted_chat_account,
)
from guardian.tasks.chat_deadline import accepted_chat_deadline_for_task


class AcceptedKnowledgeReadUnavailable(ValueError):
    """Bounded internal refusal; never includes credentials or caller data."""


def _deny() -> None:
    raise AcceptedKnowledgeReadUnavailable(
        "accepted_knowledge_read_unavailable"
    ) from None


@dataclass(frozen=True)
class _TaskEvidence:
    request_id: str
    task_id: str
    thread_id: int
    turn_id: str
    user_id: str
    origin: str
    hosted_room_invocation: Any = field(repr=False)
    accepted_at: str | None = None
    work_deadline_at: str | None = None
    terminal_deadline_at: str | None = None


def _canonical_arguments(command_id: str, arguments: InvokeArguments) -> str | None:
    """Reject headers, bodies, extra arguments and noncanonical command forms."""
    if command_id not in chat_pilot.COMMANDS or not isinstance(
        arguments, InvokeArguments
    ):
        _deny()
    if command_id.endswith("_search"):
        raw = arguments.query
    elif command_id == "op::notion_content_read":
        raw = arguments.path_params
    else:
        path = arguments.path_params
        raw = {
            "repository": f"{path.get('owner', '')}/{path.get('repo', '')}",
            "number": path.get("number"),
        }
    if chat_pilot.hydrate_arguments(command_id, raw) != arguments:
        _deny()
    if command_id.startswith("op::github_"):
        repository = normalize_repository(raw["repository"])
        if command_id.endswith("_search") and any(
            c in raw["query"] for c in ':"\\\n\r'
        ):
            _deny()
        return repository
    return None


@dataclass(frozen=True, repr=False)
class AcceptedKnowledgeRead:
    """An immutable comparison target, never cached continuing authority.

    All public methods reread canonical ownership and current connection state.
    The database/task references cannot be supplied through InvokeRequest.
    Current generation is pinned for this attempt, so refresh/reselection and
    reconnect invalidate it as well as disconnect. A retry must prepare anew.
    """

    _db: Any = field(repr=False)
    _task: _TaskEvidence = field(repr=False)
    _binding: AcceptedChatAccountBinding
    _grant: oauth_store.ReadGrant
    _repository: str | None
    _monotonic_deadline: float
    _arguments_json: str = field(repr=False)

    def revalidate(self) -> AcceptedChatAccountBinding:
        try:
            if (
                not knowledge_oauth.enabled()
                or time.monotonic() >= self._monotonic_deadline
            ):
                _deny()
            binding = resolve_accepted_chat_account(
                self._db,
                self._task,
                command_id=self._binding.command_id,
                args_hash=self._binding.args_hash,
            )
            grant = oauth_store.read_grant(
                self._db, binding.account_id, self._grant.provider
            )
            if binding != self._binding or grant is None or grant != self._grant:
                _deny()
            if grant.expires_at is not None and (
                not math.isfinite(grant.expires_at) or grant.expires_at <= time.time()
            ):
                _deny()
            if self._repository is not None and self._repository not in {
                normalize_repository(value) for value in grant.repositories
            }:
                _deny()
            # Database reads must not turn a formerly live deadline into permission.
            deadline = accepted_chat_deadline_for_task(self._task)
            if (
                deadline is None
                or datetime.now(timezone.utc) >= deadline.work_deadline_at
                or time.monotonic() >= self._monotonic_deadline
            ):
                _deny()
            return binding
        except ChatAccountAcceptancePending:
            raise
        except Exception:
            _deny()

    def lineage(self) -> dict[str, str | int]:
        """Server-derived provenance for existing Command Bus events, no secrets."""
        binding = self.revalidate()
        return {
            "account_id": binding.account_id,
            "request_id": binding.request_id,
            "backend_task_id": binding.backend_task_id,
            "thread_id": binding.thread_id,
            "turn_id": binding.turn_id,
            "tool_turn_id": binding.tool_turn_id,
            "command_id": binding.command_id,
            "args_hash": binding.args_hash,
            "connection_generation": self._grant.generation,
            "provider": self._grant.provider,
        }

    def arguments(self) -> InvokeArguments:
        """Detached exact arguments for the bounded adapter, never caller aliases."""
        self.revalidate()
        return InvokeArguments.model_validate_json(self._arguments_json)

    def remaining_seconds(self) -> float:
        """Upper bound for a cancellable transport timer, not a timer itself."""
        self.revalidate()
        deadline = accepted_chat_deadline_for_task(self._task)
        remaining = min(
            self._monotonic_deadline - time.monotonic(),
            (deadline.work_deadline_at - datetime.now(timezone.utc)).total_seconds(),
        )
        if self._grant.expires_at is not None:
            remaining = min(remaining, self._grant.expires_at - time.time())
        if remaining <= 0:
            _deny()
        return remaining

    def idempotency_key(self) -> str:
        # Generation participates so a newly authorized connection cannot replay
        # evidence fetched using a superseded connection or resource selection.
        digest = hashlib.sha256(canonical_json(self.lineage()).encode()).hexdigest()
        return f"accepted-knowledge:{digest}"

    def validate_replay(self, run: dict[str, Any]) -> None:
        """Call before returning either ordinary or conflict-race replay results."""
        binding = self.revalidate()
        if (
            run.get("auth_subject") != binding.account_id
            or run.get("command_id") != binding.command_id
            or run.get("args_hash") != binding.args_hash
            or run.get("idempotency_key") != self.idempotency_key()
        ):
            _deny()
        self.revalidate()

    def credential_for_io(self) -> oauth_store.CredentialSnapshot:
        """Just-in-time credential only; no refresh/network/legacy fallback.

        A change after the final read can race an already-started request. The
        transport must cancel when observed and revalidate before publishing
        results; this function is not a lock across network I/O.
        """
        try:
            binding = self.revalidate()
            snapshot = oauth_store.credential(
                self._db, binding.account_id, self._grant.provider
            )
            if snapshot is None or (
                snapshot.user_id != binding.account_id
                or snapshot.provider != self._grant.provider
                or snapshot.generation != self._grant.generation
                or tuple(snapshot.repositories) != self._grant.repositories
                or snapshot.expires_at != self._grant.expires_at
                or not snapshot.access_token
            ):
                _deny()
            self.revalidate()
            return snapshot
        except ChatAccountAcceptancePending:
            raise
        except Exception:
            _deny()


def prepare_accepted_knowledge_read(
    db: Any,
    task: Any,
    *,
    command_id: str,
    arguments: InvokeArguments,
) -> AcceptedKnowledgeRead:
    """Prepare from canonical acceptance; task account fields are comparisons."""
    try:
        arguments = arguments.model_copy(deep=True)
        repository = _canonical_arguments(command_id, arguments)
        evidence = _TaskEvidence(
            **{
                name: getattr(task, name, None)
                for name in _TaskEvidence.__dataclass_fields__
            }
        )
        args_hash = compute_args_hash(
            arguments.model_dump(mode="json", exclude_none=False)
        )
        binding = resolve_accepted_chat_account(
            db, evidence, command_id=command_id, args_hash=args_hash
        )
        if not knowledge_oauth.enabled():
            _deny()
        grant = oauth_store.read_grant(
            db, binding.account_id, chat_pilot.COMMANDS[command_id][0]
        )
        deadline = accepted_chat_deadline_for_task(evidence)
        if grant is None or deadline is None:
            _deny()
        remaining = (
            deadline.work_deadline_at - datetime.now(timezone.utc)
        ).total_seconds()
        fence = AcceptedKnowledgeRead(
            db,
            evidence,
            binding,
            grant,
            repository,
            time.monotonic() + remaining,
            canonical_json(arguments.model_dump(mode="json", exclude_none=False)),
        )
        fence.revalidate()
        return fence
    except ChatAccountAcceptancePending:
        raise
    except Exception:
        _deny()
