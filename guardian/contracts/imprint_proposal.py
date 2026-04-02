from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from typing import Any

from guardian.contracts.imprint_snapshot import _canonicalize


@dataclass(frozen=True, slots=True)
class ImprintProposal:
    """Deterministic backend proposal derived from a canonical snapshot."""

    proposal_version: int
    generator_version: str
    snapshot_version: int
    snapshot_hash: str
    user_id: str
    project_id: int | None
    scope_kind: str
    proposal_name: str
    preferred_name: str
    persona_draft: str
    prompt_metadata: dict[str, Any]
    proposal_hash: str = field(init=False)

    def __post_init__(self) -> None:
        object.__setattr__(self, "proposal_hash", self._compute_hash())

    def canonical_payload(self) -> dict[str, Any]:
        return _canonicalize(
            {
                "proposal_version": self.proposal_version,
                "generator_version": self.generator_version,
                "snapshot_version": self.snapshot_version,
                "snapshot_hash": self.snapshot_hash,
                "user_id": self.user_id,
                "project_id": self.project_id,
                "scope_kind": self.scope_kind,
                "proposal_name": self.proposal_name,
                "preferred_name": self.preferred_name,
                "persona_draft": self.persona_draft,
                "prompt_metadata": self.prompt_metadata,
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
        payload["proposal_hash"] = self.proposal_hash
        return payload


__all__ = ["ImprintProposal"]
