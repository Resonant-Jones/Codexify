"""Typed participant boundary for canonical chat queue acceptance.

Participants coordinate bounded, feature-specific ephemeral state around the
existing acceptance transaction. They never own the turn lock, queue, task
events, worker execution, or transcript persistence.
"""

from __future__ import annotations

from typing import Protocol

from guardian.tasks.types import ChatCompletionTask


class ChatAcceptanceParticipant(Protocol):
    """Optional lifecycle participant in one chat acceptance attempt.

    ``prepare`` runs after the canonical turn lock is held and before task
    serialization/enqueue. A successful return means the participant prepared
    state that must be rolled back if queue acceptance subsequently fails.
    Implementations must make a failed ``prepare`` atomic or clean up any
    partial state themselves.

    ``rollback`` is pre-acceptance cleanup only. ``commit`` runs after queue
    acceptance and must be monotonic/idempotent because accepted work cannot be
    withdrawn or automatically re-enqueued by this lifecycle. Implementations
    must not mutate task/request/user/thread identity, provider selection,
    retrieval policy, or the accepted task after enqueue.
    """

    def prepare(self, task: ChatCompletionTask, /) -> None:
        """Prepare bounded state and optionally mutate the in-memory task."""

    def rollback(self, /) -> None:
        """Idempotently release prepared state after enqueue did not occur."""

    def commit(self, /) -> None:
        """Commit prepared state after irreversible queue acceptance."""
