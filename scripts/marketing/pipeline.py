from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

STATUS_IMPLEMENTED = "implemented"
STATUS_VERIFIED = "verified"
STATUS_LIVE_PROVEN = "live-proven"

ALLOWED_STATUSES = [STATUS_IMPLEMENTED, STATUS_VERIFIED, STATUS_LIVE_PROVEN]

CANDIDATE_MARKETABLE_CLAIM = "marketable_claim"
CANDIDATE_INTERNAL_EVIDENCE = "internal_evidence"
CANDIDATE_RISK_OR_BLOCKER = "risk_or_blocker"
CANDIDATE_TASK_INSTRUCTION = "task_instruction"
CANDIDATE_METADATA_REFERENCE = "metadata_reference"

PRESENTATION_PUBLIC_COPY_SEED = "public_copy_seed"
PRESENTATION_SUPPORTING_EVIDENCE = "supporting_evidence"
PRESENTATION_INTERNAL_ANCHOR = "internal_anchor"
PRESENTATION_RISK_NOTE = "risk_note"
PRESENTATION_METADATA_REFERENCE = "metadata_reference"

ALLOWED_PRESENTATION_ROLES = [
    PRESENTATION_PUBLIC_COPY_SEED,
    PRESENTATION_SUPPORTING_EVIDENCE,
    PRESENTATION_INTERNAL_ANCHOR,
    PRESENTATION_RISK_NOTE,
    PRESENTATION_METADATA_REFERENCE,
]

ALLOWED_CANDIDATE_CLASSES = [
    CANDIDATE_MARKETABLE_CLAIM,
    CANDIDATE_INTERNAL_EVIDENCE,
    CANDIDATE_RISK_OR_BLOCKER,
    CANDIDATE_TASK_INSTRUCTION,
    CANDIDATE_METADATA_REFERENCE,
]

EVIDENCE_LEDGER_SCHEMA_VERSION = "marketing_evidence_ledger.v2"

LIVE_PROVEN_MARKERS = [
    "live proof",
    "live-proven",
    "re-proven",
    "runtime proof",
    "supported path proof",
    "compose-local proof",
]

VERIFIED_MARKERS = [
    "verified",
    "validation",
    "validated",
    "test",
    "tests",
    "passed",
    "audit",
    "regression coverage",
]

CLAIM_KEYWORDS = [
    "claim",
    "evidence",
    "implemented",
    "local",
    "runtime",
    "boundary",
    "identity",
    "proof",
    "verified",
    "audit",
    "policy",
    "supported",
    "compose",
    "release",
    "governance",
    "queue",
    "contract",
    "adr",
    "depends on",
    "stability",
    "task",
    "failed",
    "blocked",
    "artifact",
    "missing",
]

DEFAULT_CHANNELS = ["website", "social", "community"]

AUDIENCE_LABELS = {
    "local-first-builders": "Local-First AI Builders",
}

DRAFT_SAFE_PUBLIC_PLACEHOLDER = (
    "No copy-ready public claims were available for this campaign. "
    "Review evidence ledger before publication."
)

STATUS_RANK = {
    STATUS_IMPLEMENTED: 0,
    STATUS_VERIFIED: 1,
    STATUS_LIVE_PROVEN: 2,
}

CANDIDATE_CLASS_RANK = {
    CANDIDATE_MARKETABLE_CLAIM: 0,
    CANDIDATE_INTERNAL_EVIDENCE: 1,
    CANDIDATE_METADATA_REFERENCE: 2,
    CANDIDATE_TASK_INSTRUCTION: 3,
    CANDIDATE_RISK_OR_BLOCKER: 4,
}

RISK_OR_BLOCKER_MARKERS = [
    "not release-ready",
    "release-ready for this path: no",
    "failed before",
    "migrator failed",
    "task.failed",
    "blocked",
    "missing revision",
    "restore the missing",
    "re-run the live compose proof",
    "not yet runtime-owned",
    "worker runtime artifact",
    "failed proof",
    "failed run",
    "missing runtime artifact",
]

TASK_INSTRUCTION_PREFIXES = [
    "re-run",
    "rerun",
    "run the",
    "restore the",
    "follow up",
    "investigate",
    "todo:",
    "action:",
]

INTERNAL_EVIDENCE_MARKERS = [
    "runbook",
    "internal",
    "operator note",
    "triage",
    "debug",
    "event emitted",
    "events are emitted",
]

RELEASE_READINESS_MARKERS = [
    "not release-ready",
    "release-ready for this path: no",
    "not yet runtime-owned",
]

FAILED_PROOF_MARKERS = [
    "failed proof",
    "failed before",
    "migrator failed",
    "failed run",
]

BLOCKED_RUN_MARKERS = [
    "blocked",
    "re-run",
    "rerun",
]

MISSING_RUNTIME_ARTIFACT_MARKERS = [
    "missing revision",
    "restore the missing",
    "worker runtime artifact",
    "missing runtime artifact",
]

IMPLEMENTATION_BREADCRUMB_PATTERNS = [
    re.compile(r"^\s*\d+\.\s+", re.IGNORECASE),
    re.compile(r"\b[0-9a-f]{7,12}\b", re.IGNORECASE),
    re.compile(r"\bTASK-\d{4}-[A-Za-z0-9._-]+", re.IGNORECASE),
    re.compile(r"\bdocs/architecture/[A-Za-z0-9._\-/]*", re.IGNORECASE),
    re.compile(r"\bguardian/queue/[A-Za-z0-9._\-/]*", re.IGNORECASE),
    re.compile(r"/app/[A-Za-z0-9._\-/]*", re.IGNORECASE),
    re.compile(r"\bcodexify:queue:[A-Za-z0-9:_-]+", re.IGNORECASE),
    re.compile(r"\bexisting queue:", re.IGNORECASE),
    re.compile(r"\bguardian queue infrastructure\b", re.IGNORECASE),
    re.compile(r"\bcoding-task envelope schema\b", re.IGNORECASE),
    re.compile(r"\bDepends on:\s*ADR-\d+\b", re.IGNORECASE),
    re.compile(r"\bPer\s+ADR-\d+\s+contract:\s*$", re.IGNORECASE),
]


@dataclass(frozen=True)
class SourceDocument:
    relative_path: str
    precedence: int
    content: str


@dataclass
class Claim:
    claim: str
    proof_tier: str
    evidence_paths: list[str]
    status: str
    channel: str
    approval_state: str
    candidate_class: str = CANDIDATE_MARKETABLE_CLAIM
    presentation_role: str = PRESENTATION_PUBLIC_COPY_SEED
    copy_ready: bool = True

    def as_dict(self) -> dict[str, Any]:
        return {
            "claim": self.claim,
            "proof_tier": self.proof_tier,
            "evidence_paths": self.evidence_paths,
            "status": self.status,
            "channel": self.channel,
            "approval_state": self.approval_state,
            "candidate_class": self.candidate_class,
            "presentation_role": self.presentation_role,
            "copy_ready": self.copy_ready,
        }


@dataclass(frozen=True)
class SkillContract:
    banned_phrases: list[str]
    risk_flags: list[str]


def _repo_relative(path: Path, root: Path) -> str:
    return path.relative_to(root).as_posix()


def _document_precedence(relative_path: str) -> int:
    if relative_path.startswith("docs/Campaign/"):
        return 0
    if relative_path == "docs/architecture/00-current-state.md":
        return 1
    if relative_path.startswith("docs/beta/"):
        return 1
    if relative_path.startswith("docs/release/"):
        return 1
    if relative_path.startswith("docs/DEV_LOG/"):
        return 2
    return 3


def collect_source_documents(source_root: Path) -> list[SourceDocument]:
    paths: list[Path] = []

    paths.extend(sorted((source_root / "docs" / "Campaign").glob("**/*.md")))

    current_state = (
        source_root / "docs" / "architecture" / "00-current-state.md"
    )
    if current_state.exists():
        paths.append(current_state)

    paths.extend(sorted((source_root / "docs" / "beta").glob("**/*.md")))
    paths.extend(sorted((source_root / "docs" / "release").glob("**/*.md")))
    paths.extend(sorted((source_root / "docs" / "DEV_LOG").glob("**/*.md")))

    documents: list[SourceDocument] = []
    for path in paths:
        if not path.exists() or not path.is_file():
            continue
        relative_path = _repo_relative(path, source_root)
        documents.append(
            SourceDocument(
                relative_path=relative_path,
                precedence=_document_precedence(relative_path),
                content=path.read_text(encoding="utf-8", errors="replace"),
            )
        )
    return documents


def _normalize_claim_key(text: str) -> str:
    lowered = text.lower()
    cleaned = re.sub(r"[^a-z0-9\s]", " ", lowered)
    squashed = re.sub(r"\s+", " ", cleaned).strip()
    return squashed


def _line_looks_claimworthy(line: str) -> bool:
    if len(line) < 18 or len(line) > 240:
        return False
    if line.startswith(("#", "```", "|", "import ", "from ")):
        return False

    if (
        _looks_like_risk_or_blocker(line)
        or _looks_like_task_instruction(line)
        or _looks_like_metadata_reference(line)
    ):
        return True

    lowered = line.lower()
    return any(keyword in lowered for keyword in CLAIM_KEYWORDS)


def classify_claim_status(text: str) -> str:
    lowered = text.lower()
    if any(marker in lowered for marker in LIVE_PROVEN_MARKERS):
        return STATUS_LIVE_PROVEN
    if any(marker in lowered for marker in VERIFIED_MARKERS):
        return STATUS_VERIFIED
    return STATUS_IMPLEMENTED


def _looks_like_metadata_reference(line: str) -> bool:
    lowered = line.lower()
    if lowered.startswith(
        (
            "proof artifact:",
            "artifact:",
            "evidence path:",
            "source:",
            "path:",
            "metadata:",
            "reference:",
        )
    ):
        return True
    return bool(
        re.search(r"\bdocs/[A-Za-z0-9._\-/]+\b", line)
        and lowered.startswith(("proof artifact", "artifact", "source", "path"))
    )


def _looks_like_task_instruction(line: str) -> bool:
    lowered = line.lower()
    if any(lowered.startswith(prefix) for prefix in TASK_INSTRUCTION_PREFIXES):
        return True
    return "re-run the live compose proof" in lowered


def _looks_like_risk_or_blocker(line: str) -> bool:
    lowered = line.lower()
    return any(marker in lowered for marker in RISK_OR_BLOCKER_MARKERS)


def _looks_like_internal_evidence(line: str) -> bool:
    lowered = line.lower()
    return any(marker in lowered for marker in INTERNAL_EVIDENCE_MARKERS)


def classify_claim_candidate(text: str) -> str:
    if _looks_like_risk_or_blocker(text):
        return CANDIDATE_RISK_OR_BLOCKER
    if _looks_like_task_instruction(text):
        return CANDIDATE_TASK_INSTRUCTION
    if _looks_like_metadata_reference(text):
        return CANDIDATE_METADATA_REFERENCE
    if _looks_like_internal_evidence(text):
        return CANDIDATE_INTERNAL_EVIDENCE
    return CANDIDATE_MARKETABLE_CLAIM


def _looks_like_implementation_breadcrumb(text: str) -> bool:
    return any(
        pattern.search(text) for pattern in IMPLEMENTATION_BREADCRUMB_PATTERNS
    )


def _looks_like_internal_anchor(text: str) -> bool:
    lowered = text.lower().strip()
    return (
        lowered.startswith(("depends on:", "per adr-"))
        or "adr-" in lowered
        or lowered.endswith(":")
    )


def assign_presentation_role(claim: Claim) -> None:
    if claim.candidate_class == CANDIDATE_RISK_OR_BLOCKER:
        claim.presentation_role = PRESENTATION_RISK_NOTE
        claim.copy_ready = False
        return

    if claim.candidate_class == CANDIDATE_METADATA_REFERENCE:
        claim.presentation_role = PRESENTATION_METADATA_REFERENCE
        claim.copy_ready = False
        return

    if claim.candidate_class in {
        CANDIDATE_TASK_INSTRUCTION,
        CANDIDATE_INTERNAL_EVIDENCE,
    }:
        claim.presentation_role = PRESENTATION_INTERNAL_ANCHOR
        claim.copy_ready = False
        return

    if _looks_like_internal_anchor(claim.claim):
        claim.presentation_role = PRESENTATION_INTERNAL_ANCHOR
        claim.copy_ready = False
        return

    if _looks_like_implementation_breadcrumb(claim.claim):
        claim.presentation_role = PRESENTATION_SUPPORTING_EVIDENCE
        claim.copy_ready = False
        return

    claim.presentation_role = PRESENTATION_PUBLIC_COPY_SEED
    claim.copy_ready = True


def assign_presentation_roles(claims: list[Claim]) -> list[Claim]:
    for claim in claims:
        assign_presentation_role(claim)
    return claims


def extract_claim_candidates(documents: list[SourceDocument]) -> list[Claim]:
    candidates: list[Claim] = []
    for doc in documents:
        for raw_line in doc.content.splitlines():
            line = raw_line.strip()
            if line.startswith(("- ", "* ")):
                line = line[2:].strip()
            line = re.sub(r"`", "", line)
            line = re.sub(r"\s+", " ", line).strip()
            if not _line_looks_claimworthy(line):
                continue
            status = classify_claim_status(line)
            candidate_class = classify_claim_candidate(line)
            candidates.append(
                Claim(
                    claim=line,
                    proof_tier=status,
                    evidence_paths=[doc.relative_path],
                    status=status,
                    channel="core",
                    approval_state="draft",
                    candidate_class=candidate_class,
                )
            )
    return candidates


def merge_claims_by_precedence(candidates: list[Claim]) -> list[Claim]:
    merged: dict[str, tuple[int, Claim]] = {}

    for candidate in candidates:
        evidence = candidate.evidence_paths[0]
        precedence = _document_precedence(evidence)
        key = _normalize_claim_key(candidate.claim)
        if not key:
            continue

        current = merged.get(key)
        if current is None:
            merged[key] = (precedence, candidate)
            continue

        current_precedence, current_claim = current
        if precedence < current_precedence:
            merged[key] = (precedence, candidate)
            continue

        if precedence == current_precedence:
            new_class_rank = CANDIDATE_CLASS_RANK.get(
                candidate.candidate_class, 0
            )
            old_class_rank = CANDIDATE_CLASS_RANK.get(
                current_claim.candidate_class, 0
            )
            if new_class_rank > old_class_rank:
                merged[key] = (precedence, candidate)
                continue
            new_rank = STATUS_RANK.get(candidate.status, 0)
            old_rank = STATUS_RANK.get(current_claim.status, 0)
            if new_rank > old_rank:
                merged[key] = (precedence, candidate)

    claims = [value[1] for value in merged.values()]
    claims.sort(
        key=lambda item: (
            _document_precedence(item.evidence_paths[0]),
            item.evidence_paths[0],
            item.claim.lower(),
        )
    )
    return claims


def enforce_no_evidence_no_claim(
    claims: list[Claim], source_root: Path
) -> None:
    for claim in claims:
        if claim.status not in ALLOWED_STATUSES:
            raise ValueError(f"Unsupported claim status: {claim.status}")
        if claim.proof_tier not in ALLOWED_STATUSES:
            raise ValueError(
                f"Unsupported claim proof tier: {claim.proof_tier}"
            )
        if claim.approval_state != "draft":
            raise ValueError(
                "All claims must remain in draft approval state in v1"
            )
        if claim.candidate_class not in ALLOWED_CANDIDATE_CLASSES:
            raise ValueError(
                f"Unsupported claim candidate class: {claim.candidate_class}"
            )
        if not claim.evidence_paths:
            raise ValueError(f"Claim has no evidence: {claim.claim}")
        for rel_path in claim.evidence_paths:
            abs_path = source_root / rel_path
            if not abs_path.exists():
                raise ValueError(f"Evidence path does not exist: {rel_path}")


def detect_risk_flags(text: str) -> list[str]:
    lowered = text.lower()
    flags: list[str] = []

    if any(
        phrase in lowered
        for phrase in ["guaranteed", "zero risk", "fully autonomous"]
    ):
        flags.append("overclaim_risk")

    if "public launch ready" in lowered:
        flags.append("unsupported_readiness_risk")

    if "desktop" in lowered and "docker" in lowered and "same path" in lowered:
        flags.append("path_collapsing_risk")

    return flags


def detect_candidate_risk_flags(claims: list[Claim]) -> list[str]:
    flags: set[str] = set()
    for claim in claims:
        flags.update(_risk_flags_for_claim(claim))
    return sorted(flags)


def _risk_flags_for_claim(claim: Claim) -> list[str]:
    if claim.candidate_class != CANDIDATE_RISK_OR_BLOCKER:
        return []

    lowered = claim.claim.lower()
    flags: set[str] = set()
    if any(marker in lowered for marker in RELEASE_READINESS_MARKERS):
        flags.add("unsupported_readiness_risk")
    if any(marker in lowered for marker in FAILED_PROOF_MARKERS):
        flags.add("failed_proof_risk")
    if any(marker in lowered for marker in BLOCKED_RUN_MARKERS):
        flags.add("blocked_run_risk")
    if any(marker in lowered for marker in MISSING_RUNTIME_ARTIFACT_MARKERS):
        flags.add("missing_runtime_artifact_risk")
    if "task.failed" in lowered:
        flags.add("task_failure_risk")
    return sorted(flags)


def enforce_banned_phrasing(text: str, banned_phrases: list[str]) -> None:
    lowered = text.lower()
    for phrase in banned_phrases:
        if phrase.lower() in lowered:
            raise ValueError(f"Banned phrase detected: {phrase}")


def _read_file(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def load_skill_contract(source_root: Path) -> SkillContract:
    contract_path = (
        source_root / "guardian" / "skills" / "marketing" / "contract.json"
    )
    payload = json.loads(_read_file(contract_path))
    return SkillContract(
        banned_phrases=[
            str(item) for item in payload.get("banned_phrases", [])
        ],
        risk_flags=[str(item) for item in payload.get("risk_flags", [])],
    )


def _load_template(source_root: Path, name: str) -> str:
    template_path = (
        source_root / "guardian" / "skills" / "marketing" / "templates" / name
    )
    return _read_file(template_path)


def _claims_bullets(claims: list[Claim], with_evidence: bool = True) -> str:
    lines = []
    for claim in claims:
        if with_evidence:
            lines.append(
                f"- [{claim.proof_tier}] {claim.claim} (`{claim.evidence_paths[0]}`)"
            )
        else:
            lines.append(f"- [{claim.proof_tier}] {claim.claim}")
    return "\n".join(lines)


def _copy_ready_claims(claims: list[Claim]) -> list[Claim]:
    return [claim for claim in claims if claim.copy_ready]


def _public_copy_text(claim: Claim) -> str:
    public_message = getattr(claim, "public_message", None)
    if isinstance(public_message, str) and public_message.strip():
        return public_message.strip()
    return claim.claim


def _public_copy_claims(claims: list[Claim]) -> list[Claim]:
    return [
        claim
        for claim in claims
        if claim.presentation_role == PRESENTATION_PUBLIC_COPY_SEED
        and claim.copy_ready
    ]



def _supporting_evidence_claims(claims: list[Claim]) -> list[Claim]:
    return [
        claim
        for claim in claims
        if claim.presentation_role
        in {PRESENTATION_SUPPORTING_EVIDENCE, PRESENTATION_INTERNAL_ANCHOR}
    ]


def _supporting_evidence_bullets(claims: list[Claim]) -> str:
    supporting = _supporting_evidence_claims(claims)
    if not supporting:
        return "- none"
    counts = {
        PRESENTATION_SUPPORTING_EVIDENCE: 0,
        PRESENTATION_INTERNAL_ANCHOR: 0,
    }
    for claim in supporting:
        counts[claim.presentation_role] += 1
    return "\n".join(
        f"- {role}: {count} preserved in evidence-ledger.json"
        for role, count in counts.items()
        if count
    )


def _public_copy_bullets(claims: list[Claim]) -> str:
    if not claims:
        return f"- {DRAFT_SAFE_PUBLIC_PLACEHOLDER}"
    lines = []
    for claim in claims:
        lines.append(f"- [{claim.proof_tier}] {_public_copy_text(claim)}")
    return "\n".join(lines)


def _public_copy_sentence(claims: list[Claim]) -> str:
    if not claims:
        return DRAFT_SAFE_PUBLIC_PLACEHOLDER
    return _public_copy_text(claims[0])


def _draft_warning(public_copy_claims: list[Claim]) -> str:
    if public_copy_claims:
        return "- none"
    return f"- {DRAFT_SAFE_PUBLIC_PLACEHOLDER}"


def _claims_bullets_for_review(claims: list[Claim]) -> str:
    if not claims:
        return "- none"
    lines = []
    for claim in claims:
        lines.append(
            f"- [{claim.candidate_class}] [{claim.proof_tier}] {claim.claim} (`{claim.evidence_paths[0]}`)"
        )
    return "\n".join(lines)


def _risk_flags_bullets(flags: list[str]) -> str:
    if not flags:
        return "- none"
    return "\n".join(f"- {flag}" for flag in sorted(set(flags)))


def _serialize_claim_entry(claim: Claim) -> dict[str, Any]:
    payload = claim.as_dict()
    payload["channel_eligible"] = bool(
        claim.candidate_class == CANDIDATE_MARKETABLE_CLAIM
        and claim.presentation_role
        in {PRESENTATION_PUBLIC_COPY_SEED, PRESENTATION_SUPPORTING_EVIDENCE}
    )
    payload["risk_flags"] = list(_risk_flags_for_claim(claim))
    return payload


def _build_claim_summary(
    claims: list[dict[str, Any]],
) -> dict[str, int]:
    return {
        "total": len(claims),
        "marketable_claim": len(
            [
                claim
                for claim in claims
                if claim.get("candidate_class") == CANDIDATE_MARKETABLE_CLAIM
            ]
        ),
        "internal_evidence": len(
            [
                claim
                for claim in claims
                if claim.get("candidate_class") == CANDIDATE_INTERNAL_EVIDENCE
            ]
        ),
        "risk_or_blocker": len(
            [
                claim
                for claim in claims
                if claim.get("candidate_class") == CANDIDATE_RISK_OR_BLOCKER
            ]
        ),
        "task_instruction": len(
            [
                claim
                for claim in claims
                if claim.get("candidate_class") == CANDIDATE_TASK_INSTRUCTION
            ]
        ),
        "metadata_reference": len(
            [
                claim
                for claim in claims
                if claim.get("candidate_class") == CANDIDATE_METADATA_REFERENCE
            ]
        ),
    }


def _split_by_marketing_eligibility(
    claims: list[Claim],
) -> tuple[list[Claim], list[Claim]]:
    marketable: list[Claim] = []
    non_marketable: list[Claim] = []
    for claim in claims:
        if claim.candidate_class == CANDIDATE_MARKETABLE_CLAIM:
            marketable.append(claim)
        else:
            non_marketable.append(claim)
    return marketable, non_marketable


def _non_marketable_by_class(claims: list[Claim]) -> dict[str, list[Claim]]:
    grouped: dict[str, list[Claim]] = {
        CANDIDATE_RISK_OR_BLOCKER: [],
        CANDIDATE_TASK_INSTRUCTION: [],
        CANDIDATE_METADATA_REFERENCE: [],
        CANDIDATE_INTERNAL_EVIDENCE: [],
    }
    for claim in claims:
        grouped.setdefault(claim.candidate_class, []).append(claim)
    return grouped


def _render_review_notes(
    campaign_id: str, non_marketable_claims: list[Claim], risk_flags: list[str]
) -> str:
    grouped = _non_marketable_by_class(non_marketable_claims)
    parts = [
        f"# Review Notes: {campaign_id}",
        "",
        "This file is internal review material. Do not use in external-facing copy.",
        "",
        "## Governance",
        "- approval_state: `draft`",
        "- review_scope: `internal-only`",
        "",
        "## Risk Flags",
        _risk_flags_bullets(risk_flags),
        "",
        "## Risk or Blocker Evidence",
        _claims_bullets_for_review(grouped[CANDIDATE_RISK_OR_BLOCKER]),
        "",
        "## Task Instruction Evidence",
        _claims_bullets_for_review(grouped[CANDIDATE_TASK_INSTRUCTION]),
        "",
        "## Metadata Reference Evidence",
        _claims_bullets_for_review(grouped[CANDIDATE_METADATA_REFERENCE]),
        "",
        "## Internal Evidence",
        _claims_bullets_for_review(grouped[CANDIDATE_INTERNAL_EVIDENCE]),
    ]
    return "\n".join(parts) + "\n"


def _sanitize_campaign_id(campaign_id: str) -> str:
    normalized = re.sub(r"[^A-Za-z0-9._-]+", "-", campaign_id.strip())
    return normalized.strip("-") or "campaign"


def _channel_hook(channel: str) -> str:
    if channel == "website":
        return "Infrastructure truth for local-first operators"
    if channel == "social":
        return "Proof-backed updates for builders who distrust hype"
    if channel == "community":
        return "Operational transparency and practical build lessons"
    return "Evidence-backed product signal"


def _channel_message(channel: str, core_claims: list[Claim]) -> str:
    top = core_claims[:2]
    if channel == "website":
        return (
            "Codexify presents local-first AI operations as a contract, not a slogan. "
            f"Current evidence emphasizes {top[0].proof_tier if top else 'implemented'} seams with explicit boundaries."
        )
    if channel == "social":
        return "Codexify update: structural reliability work is being tracked with explicit proof tiers and source-linked claims."
    if channel == "community":
        return "This cycle focused on operator trust: visible boundaries, bounded claims, and evidence-led progress artifacts."
    return "Evidence-linked marketing draft generated from canonical project truth."


def _status_to_phrase(status: str) -> str:
    if status == STATUS_LIVE_PROVEN:
        return "live-proven"
    if status == STATUS_VERIFIED:
        return "verified"
    return "implemented"


def _generated_at_or_now(generated_at: str | None) -> str:
    if generated_at:
        return generated_at
    return datetime.now(timezone.utc).isoformat()


def _write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


def generate_marketing_artifacts(
    source_root: Path,
    campaign_id: str,
    audience: str,
    channels: list[str],
    mode: str,
    output_root: Path | None = None,
    max_claims: int = 24,
    generated_at: str | None = None,
    write_output: bool = True,
) -> dict[str, Any]:
    if mode != "draft":
        raise ValueError("V1 only supports mode='draft'")

    contract = load_skill_contract(source_root)
    documents = collect_source_documents(source_root)
    candidates = extract_claim_candidates(documents)
    merged = merge_claims_by_precedence(candidates)
    selected_claims = merged[:max_claims]
    assign_presentation_roles(selected_claims)

    if not selected_claims:
        raise ValueError("No claim candidates found in canonical sources")

    enforce_no_evidence_no_claim(selected_claims, source_root)
    marketable_claims, non_marketable_claims = _split_by_marketing_eligibility(
        selected_claims
    )
    if not marketable_claims:
        raise ValueError(
            "No marketable claims remained after claim suitability classification"
        )

    generated = _generated_at_or_now(generated_at)
    channel_list = [item.strip() for item in channels if item.strip()]
    if not channel_list:
        channel_list = list(DEFAULT_CHANNELS)

    audience_label = AUDIENCE_LABELS.get(audience, audience)
    canonical_claims = [
        _serialize_claim_entry(claim) for claim in selected_claims
    ]
    for claim in canonical_claims:
        if claim.get("candidate_class") is None:
            raise ValueError("ledger v2 requires non-null candidate_class")
        if claim.get("channel_eligible") is None:
            raise ValueError("ledger v2 requires non-null channel_eligible")
        if claim.get("risk_flags") is None:
            raise ValueError("ledger v2 requires non-null risk_flags")
        if claim.get("presentation_role") is None:
            raise ValueError("ledger v2 requires non-null presentation_role")
        if claim.get("copy_ready") is None:
            raise ValueError("ledger v2 requires non-null copy_ready")
        if not isinstance(claim.get("channel_eligible"), bool):
            raise ValueError("ledger v2 requires boolean channel_eligible")
        if not isinstance(claim.get("risk_flags"), list):
            raise ValueError("ledger v2 requires list risk_flags")
        if not isinstance(claim.get("copy_ready"), bool):
            raise ValueError("ledger v2 requires boolean copy_ready")
        if claim.get("presentation_role") not in ALLOWED_PRESENTATION_ROLES:
            raise ValueError(
                f"Unsupported presentation role: {claim.get('presentation_role')}"
            )
    marketable_claim_dicts = [
        claim for claim in canonical_claims if claim["channel_eligible"]
    ]
    non_marketable_claim_dicts = [
        claim for claim in canonical_claims if not claim["channel_eligible"]
    ]

    out_root = output_root or (source_root / "docs" / "Marketing" / "generated")
    campaign_dir = out_root / _sanitize_campaign_id(campaign_id)
    if write_output:
        campaign_dir.mkdir(parents=True, exist_ok=True)

    positioning = (
        "Codexify is local-first AI operations infrastructure with explicit boundaries, "
        "evidence-linked claims, and human-governed release posture."
    )
    core_narrative = (
        "This draft campaign translates real campaign receipts and architecture truth into public-facing messaging "
        "for builders who prioritize reliability over hype."
    )

    core_template = _load_template(source_root, "core-brief.md")
    copy_ready_claims = _copy_ready_claims(marketable_claims)
    public_copy_claims = _public_copy_claims(marketable_claims)
    claims_bullets = (
        _claims_bullets(copy_ready_claims)
        if copy_ready_claims
        else f"- {DRAFT_SAFE_PUBLIC_PLACEHOLDER}"
    )
    supporting_evidence_claims = _supporting_evidence_claims(marketable_claims)
    public_copy_claims_bullets = _public_copy_bullets(public_copy_claims)
    supporting_evidence_bullets = _supporting_evidence_bullets(
        supporting_evidence_claims
    )
    draft_warning = _draft_warning(public_copy_claims)

    assembled_channel_text: list[str] = []
    rendered_channels: dict[str, str] = {}
    channel_template = _load_template(source_root, "channel-variant.md")
    for channel in sorted(set(channel_list)):
        channel_claims = public_copy_claims[:4]
        rendered = channel_template.format(
            channel=channel,
            hook=_channel_hook(channel),
            message=_channel_message(channel, channel_claims),
            public_copy_claims_bullets=_public_copy_bullets(channel_claims),
            draft_warning=draft_warning,
        )
        enforce_banned_phrasing(rendered, contract.banned_phrases)
        rendered_channels[channel] = rendered
        assembled_channel_text.append(rendered)

    ad_template = _load_template(source_root, "ad-copy.md")
    ad_claims = public_copy_claims[:3]
    ad_rendered = ad_template.format(
        campaign_id=campaign_id,
        ad_headline_1="Build AI operations on evidence, not assumptions",
        ad_body_1=_public_copy_sentence(ad_claims[:1])
        if ad_claims
        else DRAFT_SAFE_PUBLIC_PLACEHOLDER,
        ad_tier_1=ad_claims[0].proof_tier if ad_claims else STATUS_IMPLEMENTED,
        ad_headline_2="Local-first control with explicit policy surfaces",
        ad_body_2=_public_copy_sentence(ad_claims[1:2])
        if len(ad_claims) > 1
        else DRAFT_SAFE_PUBLIC_PLACEHOLDER,
        ad_tier_2=ad_claims[1].proof_tier
        if len(ad_claims) > 1
        else STATUS_IMPLEMENTED,
        ad_headline_3="Marketing copy that can be audited",
        ad_body_3=_public_copy_sentence(ad_claims[2:3])
        if len(ad_claims) > 2
        else DRAFT_SAFE_PUBLIC_PLACEHOLDER,
        ad_tier_3=ad_claims[2].proof_tier
        if len(ad_claims) > 2
        else STATUS_IMPLEMENTED,
        draft_warning=draft_warning,
    )
    enforce_banned_phrasing(ad_rendered, contract.banned_phrases)

    infographic_template = _load_template(source_root, "infographic.md")
    data_points = public_copy_claims[:6]
    data_points_bullets = _public_copy_bullets(data_points)
    infographic_rendered = infographic_template.format(
        campaign_id=campaign_id,
        infographic_purpose=(
            "Show how Codexify maps campaign receipts, runtime truth, and operator governance into a coherent reliability narrative."
        ),
        audience_label=audience_label,
        data_points_bullets=data_points_bullets,
        visual_arc=(
            "Problem ambiguity -> boundary contracts -> evidence-linked claims -> operator confidence"
        ),
        prompt_a=(
            "Create a technical infographic for Local-First AI Builders. Show a left-to-right flow: campaign receipts, current-state truth, dev-log context, and draft marketing outputs. Use restrained engineering visuals and explicit proof-tier labels."
        ),
        prompt_b=(
            "Design an operator-facing infographic that emphasizes local-first reliability, identity boundaries, and failure visibility. Include badges for implemented, verified, and live-proven claims. Avoid hype language."
        ),
        draft_warning=draft_warning,
    )
    enforce_banned_phrasing(infographic_rendered, contract.banned_phrases)

    core_rendered = core_template.format(
        campaign_id=campaign_id,
        audience_label=audience_label,
        positioning=positioning,
        core_narrative=core_narrative,
        claims_bullets=claims_bullets,
        public_copy_claims_bullets=public_copy_claims_bullets,
        supporting_evidence_bullets=supporting_evidence_bullets,
        risk_flags_bullets="- pending-evaluation",
    )

    combined_text = "\n\n".join(
        [
            core_rendered,
            ad_rendered,
            infographic_rendered,
            *assembled_channel_text,
        ]
    )
    flags = detect_risk_flags(combined_text)
    suitability_flags = detect_candidate_risk_flags(non_marketable_claims)
    filtered_flags = sorted({*flags, *suitability_flags})

    final_core_rendered = core_template.format(
        campaign_id=campaign_id,
        audience_label=audience_label,
        positioning=positioning,
        core_narrative=core_narrative,
        claims_bullets=claims_bullets,
        public_copy_claims_bullets=public_copy_claims_bullets,
        supporting_evidence_bullets=supporting_evidence_bullets,
        risk_flags_bullets=_risk_flags_bullets(filtered_flags),
    )
    enforce_banned_phrasing(final_core_rendered, contract.banned_phrases)
    review_notes = _render_review_notes(
        campaign_id=campaign_id,
        non_marketable_claims=non_marketable_claims,
        risk_flags=filtered_flags,
    )

    evidence_payload = {
        "schema_version": EVIDENCE_LEDGER_SCHEMA_VERSION,
        "campaign_id": campaign_id,
        "audience": audience,
        "mode": mode,
        "approval_state": "draft",
        "generated_at": generated,
        "claims": canonical_claims,
        "marketable_claims": marketable_claim_dicts,
        "non_marketable_claims": non_marketable_claim_dicts,
        "claim_summary": _build_claim_summary(canonical_claims),
        "risk_flags": filtered_flags,
    }

    run_metadata = {
        "campaign_id": campaign_id,
        "audience": audience,
        "channels": sorted(set(channel_list)),
        "mode": mode,
        "approval_state": "draft",
        "generated_at": generated,
        "claim_count": len(canonical_claims),
        "marketable_claim_count": len(marketable_claim_dicts),
        "non_marketable_claim_count": len(non_marketable_claim_dicts),
        "output_dir": _repo_relative(campaign_dir, source_root)
        if out_root.is_relative_to(source_root)
        else _sanitize_campaign_id(campaign_id),
    }
    if write_output:
        _write_text(campaign_dir / "core-brief.md", final_core_rendered)
        for channel, rendered in rendered_channels.items():
            _write_text(campaign_dir / f"channel-{channel}.md", rendered)
        _write_text(campaign_dir / "ad-copy.md", ad_rendered)
        _write_text(campaign_dir / "infographic-spec.md", infographic_rendered)
        _write_text(campaign_dir / "review-notes.md", review_notes)
        _write_json(campaign_dir / "evidence-ledger.json", evidence_payload)
        _write_json(campaign_dir / "run-metadata.json", run_metadata)

        history_path = (
            source_root
            / "docs"
            / "Marketing"
            / "generated"
            / "history"
            / "run-history.jsonl"
        )
        history_path.parent.mkdir(parents=True, exist_ok=True)
        with history_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(run_metadata, sort_keys=True) + "\n")

    return {
        "campaign_dir": str(campaign_dir),
        "evidence_ledger": str(campaign_dir / "evidence-ledger.json"),
        "claim_count": len(canonical_claims),
        "marketable_claim_count": len(marketable_claim_dicts),
        "channels": sorted(set(channel_list)),
        "risk_flags": filtered_flags,
    }
