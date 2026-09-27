"""Strict bounded result contract for one Guardian-authorized live Evaluator.

Only the allowlisted verdict, short summary, and criterion judgments cross the
Pi result-return boundary. Raw assistant text, reasoning, tool arguments, and
provider payloads remain outside Guardian/Campaign artifacts.
"""

from __future__ import annotations

import re
from typing import Any, Mapping

from .tokens import PI_AUTHORIZED_EVALUATOR_RESULT_CONTRACT

_VERDICTS = frozenset({"passed", "passed_with_advisories", "repair_required", "blocked"})
_CRITERION_VERDICTS = frozenset({"pass", "fail", "advisory"})
_SAFE_REF = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/#-]{0,127}$")
_CREDENTIAL_SHAPE = re.compile(
    r"\bsk-[A-Za-z0-9_-]{16,}|Bearer\s+\S{8,}|"
    r"-----BEGIN [A-Z ]*PRIVATE KEY-----|"
    r"(?:api[_-]?key|password|secret)\s*[:=]\s*\S{8,}",
    re.IGNORECASE,
)


def _bounded_text(value: Any, maximum: int) -> bool:
    return (
        isinstance(value, str)
        and 0 < len(value) <= maximum
        and bool(value.strip())
        and _CREDENTIAL_SHAPE.search(value) is None
    )


def validate_evaluator_result(value: Any) -> dict[str, Any]:
    """Return a content-minimized copy or raise a credential-safe error."""
    invalid = ValueError("invalid bounded evaluator result")
    if not isinstance(value, Mapping) or set(value) != {
        "verdict", "summary", "structured_acceptance_results"
    }:
        raise invalid
    if value["verdict"] not in _VERDICTS or not _bounded_text(value["summary"], 500):
        raise invalid
    items = value["structured_acceptance_results"]
    if not isinstance(items, list) or not 1 <= len(items) <= 16:
        raise invalid
    seen: set[str] = set()
    results: list[dict[str, Any]] = []
    for item in items:
        if not isinstance(item, Mapping) or set(item) != {
            "criterion_id", "verdict", "evidence_refs", "basis"
        }:
            raise invalid
        cid, verdict, refs, basis = (
            item["criterion_id"], item["verdict"], item["evidence_refs"], item["basis"]
        )
        if (
            not isinstance(cid, str)
            or _SAFE_REF.fullmatch(cid) is None
            or cid in seen
            or verdict not in _CRITERION_VERDICTS
            or not isinstance(refs, list)
            or not 1 <= len(refs) <= 8
            or any(not isinstance(ref, str) or _SAFE_REF.fullmatch(ref) is None for ref in refs)
            or not _bounded_text(basis, 500)
        ):
            raise invalid
        seen.add(cid)
        results.append({
            "criterion_id": cid,
            "verdict": verdict,
            "evidence_refs": list(refs),
            "basis": basis,
        })
    criterion_verdicts = {item["verdict"] for item in results}
    if (
        (value["verdict"] == "passed" and criterion_verdicts != {"pass"})
        or (value["verdict"] == "passed_with_advisories"
            and ("fail" in criterion_verdicts or "advisory" not in criterion_verdicts))
        or (value["verdict"] == "repair_required" and "fail" not in criterion_verdicts)
    ):
        raise invalid
    return {
        "verdict": value["verdict"],
        "summary": value["summary"],
        "structured_acceptance_results": results,
    }


__all__ = ["PI_AUTHORIZED_EVALUATOR_RESULT_CONTRACT", "validate_evaluator_result"]
