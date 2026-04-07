"""Risk scoring utilities for audit infrastructure."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class RiskEntry:
    """Single risk entry in the risk matrix."""

    # Required fields (from baseline)
    id: str
    area: str
    failure_mode: str
    impact: int
    likelihood: int
    detectability: int
    recoverability: int
    owner: str
    status: str
    current_controls: list[str]
    next_control: str
    last_reviewed: str
    review_interval_days: int
    evidence: list[str]

    # Calculated fields (generated)
    score: int = field(default=0)
    band: str = field(default="")
    days_since_review: int = field(default=0)
    is_stale: bool = field(default=False)

    def __post_init__(self) -> None:
        """Calculate score and band after initialization."""
        self.score = calculate_score(
            self.impact,
            self.likelihood,
            self.detectability,
            self.recoverability,
        )
        self.band = score_to_band(self.score)
        self.days_since_review = calculate_days_since_review(self.last_reviewed)
        self.is_stale = self.days_since_review > self.review_interval_days

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "id": self.id,
            "area": self.area,
            "failure_mode": self.failure_mode,
            "impact": self.impact,
            "likelihood": self.likelihood,
            "detectability": self.detectability,
            "recoverability": self.recoverability,
            "score": self.score,
            "band": self.band,
            "owner": self.owner,
            "status": self.status,
            "current_controls": self.current_controls,
            "next_control": self.next_control,
            "last_reviewed": self.last_reviewed,
            "review_interval_days": self.review_interval_days,
            "days_since_review": self.days_since_review,
            "is_stale": self.is_stale,
            "evidence": self.evidence,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> RiskEntry:
        """Create RiskEntry from dictionary (baseline format)."""
        # Extract only the fields that belong in the baseline
        return cls(
            id=data["id"],
            area=data["area"],
            failure_mode=data["failure_mode"],
            impact=data["impact"],
            likelihood=data["likelihood"],
            detectability=data["detectability"],
            recoverability=data["recoverability"],
            owner=data["owner"],
            status=data["status"],
            current_controls=data["current_controls"],
            next_control=data["next_control"],
            last_reviewed=data["last_reviewed"],
            review_interval_days=data["review_interval_days"],
            evidence=data["evidence"],
        )


def calculate_score(
    impact: int, likelihood: int, detectability: int, recoverability: int
) -> int:
    """Calculate risk score: Impact × Likelihood × Detectability × Recoverability."""
    return impact * likelihood * detectability * recoverability


def score_to_band(score: int) -> str:
    """Convert score to risk band."""
    if score <= 20:
        return "Low"
    elif score <= 60:
        return "Moderate"
    elif score <= 120:
        return "High"
    else:
        return "Critical"


def calculate_days_since_review(last_reviewed: str) -> int:
    """Calculate days since last review."""
    try:
        reviewed_date = datetime.strptime(last_reviewed, "%Y-%m-%d")
        return (datetime.now() - reviewed_date).days
    except ValueError:
        return 0


def calculate_risk_summary(risks: list[RiskEntry]) -> dict[str, Any]:
    """Calculate summary statistics for a list of risks."""
    total = len(risks)
    by_band: dict[str, int] = {
        "Low": 0,
        "Moderate": 0,
        "High": 0,
        "Critical": 0,
    }
    by_owner: dict[str, int] = {}
    missing_owners: list[str] = []
    stale_entries: list[str] = []
    highest_risks: list[str] = []

    # Sort by score descending for highest risks
    sorted_by_score = sorted(risks, key=lambda r: r.score, reverse=True)

    for risk in risks:
        by_band[risk.band] = by_band.get(risk.band, 0) + 1
        by_owner[risk.owner] = by_owner.get(risk.owner, 0) + 1

        if not risk.owner or risk.owner == "TBD":
            missing_owners.append(risk.id)

        if risk.is_stale:
            stale_entries.append(risk.id)

    # Top 5 highest risks
    highest_risks = [r.id for r in sorted_by_score[:5]]

    return {
        "total": total,
        "by_band": by_band,
        "by_owner": by_owner,
        "missing_owners": missing_owners,
        "stale_entries": stale_entries,
        "highest_risks": highest_risks,
        "newly_worsened": [],  # Populated by delta calculation
    }


def calculate_delta(
    current: list[RiskEntry], previous: list[RiskEntry]
) -> dict[str, Any]:
    """Calculate delta between two risk snapshots."""
    current_by_id = {r.id: r for r in current}
    previous_by_id = {r.id: r for r in previous}

    score_changes: list[dict[str, Any]] = []
    new_risks: list[str] = []
    removed_risks: list[str] = []
    band_changes: list[dict[str, Any]] = []

    # Find new and changed risks
    for risk_id, current_risk in current_by_id.items():
        if risk_id not in previous_by_id:
            new_risks.append(risk_id)
        else:
            prev_risk = previous_by_id[risk_id]
            if current_risk.score != prev_risk.score:
                score_changes.append(
                    {
                        "id": risk_id,
                        "old": prev_risk.score,
                        "new": current_risk.score,
                        "delta": current_risk.score - prev_risk.score,
                    }
                )
            if current_risk.band != prev_risk.band:
                band_changes.append(
                    {
                        "id": risk_id,
                        "old": prev_risk.band,
                        "new": current_risk.band,
                    }
                )

    # Find removed risks
    for risk_id in previous_by_id:
        if risk_id not in current_by_id:
            removed_risks.append(risk_id)

    return {
        "score_changes": score_changes,
        "new_risks": new_risks,
        "removed_risks": removed_risks,
        "band_changes": band_changes,
    }
