"""Private trusted entry point; never mounted as a route or enabled in chat."""

import asyncio
from contextlib import contextmanager

from fastapi import HTTPException

from sqlalchemy import text

from guardian.command_bus.accepted_knowledge_read import (
    prepare_accepted_knowledge_read,
    AcceptedKnowledgeReadUnavailable,
)
from guardian.command_bus.accepted_knowledge_transport import _authority, ORIGINS
from guardian.command_bus.contracts import ActorSpec, InvokeRequest
from guardian.command_bus.invoke import execute_invoke
from guardian.command_bus.store import CommandBusStore


class _BoundedDB:
    """Use existing canonical sessions with transaction-local database limits.

    No new engine/credential/authority store. Timeout settings expire with each
    transaction and never change the database/service configuration.
    """

    def __init__(self, db):
        self._db = db

    @contextmanager
    def _session(self, name):
        with getattr(self._db, name)() as session:
            if session.get_bind().dialect.name != "postgresql":
                raise AcceptedKnowledgeReadUnavailable(
                    "accepted_knowledge_storage_unavailable"
                )
            session.execute(text("SET LOCAL statement_timeout = '1000ms'"))
            session.execute(text("SET LOCAL lock_timeout = '1000ms'"))
            yield session

    def get_session(self):
        return self._session("get_session")

    def _sa_session(self):
        return self._session("_sa_session")


async def execute_accepted_knowledge_read(*, db, task, payload: InvokeRequest, app):
    """Resolve account server-side and retain Command Bus policy/persistence.

    The trusted caller supplies an explicit server-resolved permission profile
    and external rules. Missing/denied grants stay blocked; OAuth is insufficient.
    No caller subject, headers, lineage, idempotency identity or URL is trusted.
    """
    scoped_db = _BoundedDB(db)
    payload = payload.model_copy(deep=True)
    fence = await _authority(
        lambda: prepare_accepted_knowledge_read(
            scoped_db, task, command_id=payload.command_id, arguments=payload.arguments
        )
    )
    lineage = await _authority(fence.lineage)
    payload = _canonical_payload(payload, lineage).model_copy(
        update={
            "arguments": await _authority(fence.arguments),
            "idempotency_key": await _authority(fence.idempotency_key),
        }
    )
    try:
        return await execute_invoke(
            payload=payload,
            auth_subject=lineage["account_id"],
            inbound_headers={},
            store=CommandBusStore(scoped_db),
            app=app,
            execution_lane="tools",
            allow_write_execution=False,
            confirmation_granted=False,
            _accepted_knowledge=fence,
        )
    except (asyncio.CancelledError, HTTPException):
        raise
    except Exception:
        raise AcceptedKnowledgeReadUnavailable(
            "accepted_knowledge_read_unavailable"
        ) from None


def _canonical_payload(payload, lineage):
    """Bind actual request metadata; never manufacture permission grants."""
    profile = payload.permission_profile
    if profile is not None:
        # Declared grants remain unchanged; actual request metadata is canonical.
        profile = profile.model_copy(
            update={
                "request_task_id": lineage["backend_task_id"],
                "request_thread_id": str(lineage["thread_id"]),
                "request_project_id": None,
                "request_command_class": "connector",
                "uses_network": True,
                "uses_connector": True,
                "uses_shell": False,
                "requested_write_paths": (),
            }
        )
    provider = lineage["provider"]
    return payload.model_copy(
        update={
            "actor": ActorSpec(
                kind="agent",
                id="guardian-accepted-knowledge",
                delegated_by=lineage["account_id"],
            ),
            "provenance_json": {"accepted_knowledge": lineage},
            "permission_profile": profile,
            "external_transport": "https",
            "external_target_url": ORIGINS[provider],
            "external_connector_name": provider,
            "external_command_namespace": provider,
            "external_command_name": payload.command_id.split("_", 1)[1],
            "external_thread_id": str(lineage["thread_id"]),
            "external_project_id": None,
            "work_order_id": None,
        }
    )
