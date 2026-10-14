"""Bus factor and knowledge concentration analyzer."""

from __future__ import annotations

from collections import Counter, defaultdict
from collections.abc import Iterable
from typing import Any

from repopulse.models import CommitInfo, FileBusFactor


def analyze_bus_factor(
    commits: Iterable[CommitInfo],
    min_revisions: int = 2,
    risk_threshold_pct: float = 75.0,
) -> list[FileBusFactor]:
    """
    Analyzes knowledge concentration per file based on commit authors.
    Files with >= risk_threshold_pct (default 75%) contribution from a single author
    and >= 3 revisions are flagged as high bus-factor risk.
    """
    file_authors: dict[str, Counter[str]] = defaultdict(Counter)
    file_revisions: Counter[str] = Counter()

    for c in commits:
        author = c.author_name or c.author_email or "Unknown"
        for path in {f.path for f in c.files}:
            file_authors[path][author] += 1
            file_revisions[path] += 1

    results: list[FileBusFactor] = []
    for path, authors in file_authors.items():
        total_revs = file_revisions[path]
        if total_revs < min_revisions:
            continue

        top_author, top_count = authors.most_common(1)[0]
        pct = (top_count / total_revs) * 100.0
        is_risk = pct >= risk_threshold_pct and total_revs >= 3

        results.append(
            FileBusFactor(
                path=path,
                total_revisions=total_revs,
                top_author=top_author,
                top_author_pct=pct,
                author_count=len(authors),
                is_at_risk=is_risk,
            )
        )

    # Sort by risk status (at risk first), then by total revisions descending
    results.sort(key=lambda x: (not x.is_at_risk, -x.total_revisions, x.path))
    return results


def summarize_bus_factor(bus_factors: list[FileBusFactor]) -> dict[str, Any]:
    """Computes summary metrics for bus factor analysis."""
    total_files = len(bus_factors)
    at_risk_files = [b for b in bus_factors if b.is_at_risk]
    risk_authors = Counter(b.top_author for b in at_risk_files)

    return {
        "total_analyzed_files": total_files,
        "at_risk_count": len(at_risk_files),
        "at_risk_pct": (len(at_risk_files) / total_files * 100.0) if total_files > 0 else 0.0,
        "top_bottleneck_authors": dict(risk_authors.most_common(5)),
    }
