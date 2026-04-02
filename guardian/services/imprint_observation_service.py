"""
Append-only imprint observation storage.

Observations are durable evidence, not proposal input. They are folded through
the materialization service before influencing any canonical snapshot.
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from datetime import datetime, timezone
from typing import Any

from fastapi import HTTPException
from sqlalchemy import create_engine, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker

from guardian.core.dependencies import get_database_dsn
from guardian.db.models import ImprintObservation

_SessionFactory: sessionmaker | None = None


def _get_session_factory() -> sessionmaker:
    global _SessionFactory
    if _SessionFactory is not None:
        return _SessionFactory

    dsn = get_database_dsn()
    if not dsn:
        raise RuntimeError(
            "Database DSN not configured; cannot access imprint observations."
        )

    engine = create_engine(dsn, future=True)
    _SessionFactory = sessionmaker(
        bind=engine, autoflush=False, autocommit=False, future=True
    )
    return _SessionFactory


def _set_session_factory(factory: sessionmaker) -> None:
    global _SessionFactory
    _SessionFactory = factory


def _normalize_user_id(user_id: str) -> str:
    resolved = str(user_id or "").strip()
    if not resolved:
        raise HTTPException(
            status_code=403, detail="current user could not be resolved"
        )
    return resolved


def _normalize_project_id(project_id: Any) -> int | None:
    if project_id in {None, ""}:
        return None
    try:
        return int(project_id)
    except (TypeError, ValueError) as exc:
        raise HTTPException(
            status_code=400, detail="project_id must be an integer"
        ) from exc


def _normalize_schema_version(schema_version: Any) -> int:
    try:
        resolved = int(schema_version)
    except (TypeError, ValueError) as exc:
        raise HTTPException(
            status_code=400, detail="schema_version must be an integer"
        ) from exc
    if resolved < 1:
        raise HTTPException(
            status_code=400, detail="schema_version must be positive"
        )
    return resolved


def _normalize_idempotency_key(idempotency_key: str) -> str:
    resolved = str(idempotency_key or "").strip()
    if not resolved:
        raise HTTPException(
            status_code=400, detail="idempotency_key is required"
        )
    return resolved


def _normalize_signal_type(signal_type: str) -> str:
    resolved = str(signal_type or "").strip().lower()
    resolved = re.sub(r"[^a-z0-9]+", "_", resolved).strip("_")
    if not resolved:
        raise HTTPException(status_code=400, detail="signal_type is required")
    return resolved


def _normalize_mapping(value: Any) -> dict[str, Any]:
    if isinstance(value, Mapping):
        return dict(value)
    if value is None:
        return {}
    return {"value": value}


def _serialize_observation(row: ImprintObservation) -> ImprintObservation:
    return row


def append_observation(
    user_id: str,
    project_id: int | None,
    *,
    schema_version: int = 1,
    provenance: Mapping[str, Any] | None = None,
    idempotency_key: str,
    signal_type: str,
    signal_payload: Mapping[str, Any] | None = None,
) -> ImprintObservation:
    """
    Append a durable imprint observation.

    Duplicate idempotency keys resolve to the already-persisted semantic row.
    """
    resolved_user = _normalize_user_id(user_id)
    resolved_project = _normalize_project_id(project_id)
    resolved_schema_version = _normalize_schema_version(schema_version)
    resolved_key = _normalize_idempotency_key(idempotency_key)
    resolved_signal_type = _normalize_signal_type(signal_type)
    resolved_provenance = _normalize_mapping(provenance)
    resolved_signal_payload = _normalize_mapping(signal_payload)

    Session = _get_session_factory()
    now = datetime.now(timezone.utc)
    with Session() as session:
        existing = session.scalars(
            select(ImprintObservation).where(
                ImprintObservation.idempotency_key == resolved_key
            )
        ).first()
        if existing is not None:
            return _serialize_observation(existing)

        row = ImprintObservation(
            user_id=resolved_user,
            project_id=resolved_project,
            schema_version=resolved_schema_version,
            provenance=resolved_provenance,
            idempotency_key=resolved_key,
            signal_type=resolved_signal_type,
            signal_payload=resolved_signal_payload,
            created_at=now,
            updated_at=now,
        )
        session.add(row)
        try:
            session.commit()
        except IntegrityError:
            session.rollback()
            existing = session.scalars(
                select(ImprintObservation).where(
                    ImprintObservation.idempotency_key == resolved_key
                )
            ).first()
            if existing is not None:
                return _serialize_observation(existing)
            raise
        session.refresh(row)
        return _serialize_observation(row)


def get_observation_by_idempotency_key(
    idempotency_key: str,
) -> ImprintObservation | None:
    resolved_key = _normalize_idempotency_key(idempotency_key)
    Session = _get_session_factory()
    with Session() as session:
        return session.scalars(
            select(ImprintObservation).where(
                ImprintObservation.idempotency_key == resolved_key
            )
        ).first()


def list_observations_for_scope(
    user_id: str,
    project_id: int | None,
) -> list[ImprintObservation]:
    resolved_user = _normalize_user_id(user_id)
    resolved_project = _normalize_project_id(project_id)
    Session = _get_session_factory()
    with Session() as session:
        stmt = (
            select(ImprintObservation)
            .where(
                ImprintObservation.user_id == resolved_user,
                (
                    ImprintObservation.project_id.is_(None)
                    if resolved_project is None
                    else ImprintObservation.project_id == resolved_project
                ),
            )
            .order_by(
                ImprintObservation.created_at.asc(),
                ImprintObservation.id.asc(),
            )
        )
        return list(session.scalars(stmt))


__all__ = [
    "append_observation",
    "get_observation_by_idempotency_key",
    "list_observations_for_scope",
    "_set_session_factory",
]
