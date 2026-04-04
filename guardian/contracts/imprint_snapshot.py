from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Mapping


def _canonicalize(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {
            str(key): _canonicalize(value[key])
            for key in sorted(value.keys(), key=lambda item: str(item))
        }
    if isinstance(value, (list, tuple)):
        return [_canonicalize(item) for item in value]
    if isinstance(value, set):
        canonical_items = [_canonicalize(item) for item in value]
        return sorted(
            canonical_items,
            key=lambda item: json.dumps(
                item, sort_keys=True, separators=(",", ":"), ensure_ascii=False
            ),
        )
    if isinstance(value, datetime):
        return value.isoformat()
    return value


@dataclass(frozen=True, slots=True)
class ImprintSignalSnapshot:
    """Canonical backend input for deterministic imprint proposal generation."""

    snapshot_version: int
    builder_version: str
    user_id: str
    project_id: int | None
    scope_kind: str
    requested_depth: str
    project_identity_depth: str
    settings: dict[str, Any]
    folded_state: dict[str, Any]
    effective_state: dict[str, Any]
    snapshot_hash: str = field(init=False)

    def __post_init__(self) -> None:
        object.__setattr__(self, "snapshot_hash", self._compute_hash())

    def canonical_payload(self) -> dict[str, Any]:
        return _canonicalize(
            {
                "snapshot_version": self.snapshot_version,
                "builder_version": self.builder_version,
                "user_id": self.user_id,
                "project_id": self.project_id,
                "scope_kind": self.scope_kind,
                "requested_depth": self.requested_depth,
                "project_identity_depth": self.project_identity_depth,
                "settings": self.settings,
                "folded_state": self.folded_state,
                "effective_state": self.effective_state,
            }
        )

    def canonical_json(self) -> str:
        return json.dumps(
            self.canonical_payload(),
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        )

    def _compute_hash(self) -> str:
        return hashlib.sha256(self.canonical_json().encode("utf-8")).hexdigest()

    def to_dict(self) -> dict[str, Any]:
        payload = self.canonical_payload()
        payload["snapshot_hash"] = self.snapshot_hash
        return payload


__all__ = ["ImprintSignalSnapshot"]
