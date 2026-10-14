"""Temporal co-change coupling analyzer."""

from __future__ import annotations

from collections import Counter
from collections.abc import Iterable
from itertools import combinations
from typing import Any

from repopulse.models import CommitInfo, TemporalCoupling


def analyze_coupling(
    commits: Iterable[CommitInfo],
    min_co_changes: int = 2,
    min_coupling_pct: float = 50.0,
    top_n: int = 15,
) -> list[TemporalCoupling]:
    """
    Detects implicit architectural coupling by identifying file pairs
    that frequently commit together across multiple commits.

    Skips huge bulk commits (> 25 files) to prevent noise from dependency lockfiles
    or sweeping project-wide formatting changes.
    """
    file_revisions: Counter[str] = Counter()
    pair_co_changes: Counter[tuple[str, str]] = Counter()

    for c in commits:
        unique_paths = sorted(list({f.path for f in c.files}))
        for path in unique_paths:
            file_revisions[path] += 1

        # Calculate co-changes for all pairs in this commit
        if 2 <= len(unique_paths) <= 25:
            for pair in combinations(unique_paths, 2):
                pair_co_changes[pair] += 1

    couplings: list[TemporalCoupling] = []
    for (file_a, file_b), co_count in pair_co_changes.items():
        if co_count < min_co_changes:
            continue

        rev_a = file_revisions[file_a]
        rev_b = file_revisions[file_b]
        min_rev = min(rev_a, rev_b)
        if min_rev == 0:
            continue

        pct = (co_count / min_rev) * 100.0
        if pct >= min_coupling_pct:
            couplings.append(
                TemporalCoupling(
                    file_a=file_a,
                    file_b=file_b,
                    co_changes=co_count,
                    coupling_pct=pct,
                )
            )

    couplings.sort(key=lambda x: (-x.co_changes, -x.coupling_pct, x.file_a, x.file_b))
    return couplings[:top_n]


def summarize_coupling(couplings: list[TemporalCoupling]) -> dict[str, Any]:
    """Computes summary metrics for temporal coupling."""
    return {
        "coupled_pair_count": len(couplings),
        "strongest_pair": (
            f"{couplings[0].file_a} <-> {couplings[0].file_b} ({couplings[0].coupling_pct:.1f}%)"
            if couplings
            else None
        ),
    }
