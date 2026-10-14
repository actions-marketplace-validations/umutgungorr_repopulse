"""Composite codebase health scoring engine for RepoPulse."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from repopulse.models import FileBusFactor, Hotspot, TemporalCoupling


@dataclass
class HealthScoreBreakdown:
    overall_score: int
    grade: str
    bus_factor_deduction: int
    hotspot_deduction: int
    coupling_deduction: int
    single_author_deduction: int
    verdict: str

    def to_dict(self) -> dict[str, object]:
        return {
            "overall_score": self.overall_score,
            "grade": self.grade,
            "bus_factor_deduction": self.bus_factor_deduction,
            "hotspot_deduction": self.hotspot_deduction,
            "coupling_deduction": self.coupling_deduction,
            "single_author_deduction": self.single_author_deduction,
            "verdict": self.verdict,
        }


def assign_grade(score: int) -> tuple[str, str]:
    """Returns letter grade and descriptive verdict for health score."""
    if score >= 90:
        return "A", "Healthy / Low Risk Codebase"
    elif score >= 80:
        return "B", "Stable / Minor Knowledge Silos"
    elif score >= 70:
        return "C", "Moderate Technical & Churn Debt"
    elif score >= 60:
        return "D", "Elevated Risk / Fragile Hotspots"
    else:
        return "F", "Critical Architecture & Bus-Factor Risk"


def compute_health_score(
    bus_risks: Sequence[FileBusFactor],
    hotspots: Sequence[Hotspot],
    couplings: Sequence[TemporalCoupling],
    total_commits: int,
    total_authors: int,
) -> HealthScoreBreakdown:
    """
    Computes an objective 0–100 codebase health score factoring in:
    1. Bus factor knowledge silos (-5 pts each, max 35)
    2. Hotspot churn density (-5 pts each for CRITICAL/HIGH, max 35)
    3. Temporal coupling debt (-3 pts each, max 20)
    4. Monopolistic single-author penalty (-10 if commits >= 10 and authors == 1)
    """
    score = 100

    critical_bus_count = sum(1 for b in bus_risks if b.is_at_risk)
    critical_hotspot_count = sum(1 for h in hotspots if h.risk_level in ("CRITICAL", "HIGH"))
    tight_coupling_count = len(couplings)

    bus_deduction = min(35, critical_bus_count * 5)
    hotspot_deduction = min(35, critical_hotspot_count * 5)
    coupling_deduction = min(20, tight_coupling_count * 3)

    single_author_deduction = 0
    if total_authors <= 1 and total_commits >= 10:
        single_author_deduction = 10

    score -= bus_deduction
    score -= hotspot_deduction
    score -= coupling_deduction
    score -= single_author_deduction

    overall_score = max(10, min(100, score))
    grade, verdict = assign_grade(overall_score)

    return HealthScoreBreakdown(
        overall_score=overall_score,
        grade=grade,
        bus_factor_deduction=bus_deduction,
        hotspot_deduction=hotspot_deduction,
        coupling_deduction=coupling_deduction,
        single_author_deduction=single_author_deduction,
        verdict=verdict,
    )
