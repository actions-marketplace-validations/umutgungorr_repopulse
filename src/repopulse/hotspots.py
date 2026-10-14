"""Code churn and architectural hotspot risk analyzer."""

from __future__ import annotations

import math
from collections import Counter
from collections.abc import Iterable
from typing import Any

from repopulse.models import CommitInfo, Hotspot


def analyze_hotspots(commits: Iterable[CommitInfo], top_n: int = 15) -> list[Hotspot]:
    """
    Identifies high-risk architectural hotspots by combining
    change frequency (churn) and code volume (net lines added/deleted).

    Hotspot formula: log(1 + churn) * sqrt(max(5, added - deleted))
    """
    file_churn: Counter[str] = Counter()
    file_added: Counter[str] = Counter()
    file_deleted: Counter[str] = Counter()

    for c in commits:
        for f in c.files:
            file_churn[f.path] += 1
            file_added[f.path] += f.added
            file_deleted[f.path] += f.deleted

    hotspots: list[Hotspot] = []
    for path, churn in file_churn.items():
        added = file_added[path]
        deleted = file_deleted[path]
        net_size = max(5, added - deleted)

        # Hotspot score: log(churn + 1) * sqrt(net_size)
        score = math.log1p(churn) * math.sqrt(net_size)

        # Risk classification
        if churn >= 10 and score >= 25.0:
            risk = "CRITICAL"
        elif churn >= 6 or score >= 15.0:
            risk = "HIGH"
        elif churn >= 3 or score >= 8.0:
            risk = "MEDIUM"
        else:
            risk = "LOW"

        hotspots.append(
            Hotspot(
                path=path,
                churn_count=churn,
                lines_added=added,
                lines_deleted=deleted,
                estimated_size=net_size,
                hotspot_score=score,
                risk_level=risk,
            )
        )

    hotspots.sort(key=lambda x: (-x.hotspot_score, -x.churn_count, x.path))
    return hotspots[:top_n]


def summarize_hotspots(hotspots: list[Hotspot]) -> dict[str, Any]:
    """Computes summary metrics for architectural hotspots."""
    critical_count = sum(1 for h in hotspots if h.risk_level == "CRITICAL")
    high_count = sum(1 for h in hotspots if h.risk_level == "HIGH")
    medium_count = sum(1 for h in hotspots if h.risk_level == "MEDIUM")
    low_count = sum(1 for h in hotspots if h.risk_level == "LOW")

    return {
        "total_hotspots": len(hotspots),
        "critical_count": critical_count,
        "high_count": high_count,
        "medium_count": medium_count,
        "low_count": low_count,
        "highest_risk_file": hotspots[0].path if hotspots else None,
    }
