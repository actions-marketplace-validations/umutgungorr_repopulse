"""Unit tests for Hotspot analysis."""

from repopulse.hotspots import analyze_hotspots, summarize_hotspots
from repopulse.models import CommitInfo, FileChange


def test_hotspot_analysis():
    commits = []
    # 12 commits on volatile.py with 500 lines added
    for i in range(12):
        commits.append(
            CommitInfo(
                f"c{i}",
                "Dev",
                "dev@test.com",
                i,
                "2026-01-01",
                f"c{i}",
                [FileChange("volatile.py", 50, 5)],
            )
        )
    # 2 commits on quiet.py
    commits.append(
        CommitInfo(
            "cq1", "Dev", "dev@test.com", 20, "2026-01-01", "cq1", [FileChange("quiet.py", 10, 0)]
        )
    )

    hotspots = analyze_hotspots(commits)
    assert len(hotspots) >= 2

    top = hotspots[0]
    assert top.path == "volatile.py"
    assert top.churn_count == 12
    assert top.risk_level in ("CRITICAL", "HIGH")
    assert top.hotspot_score > hotspots[1].hotspot_score

    summary = summarize_hotspots(hotspots)
    assert summary["total_hotspots"] >= 2
    assert summary["highest_risk_file"] == "volatile.py"
    assert summary["critical_count"] + summary["high_count"] >= 1


def test_hotspot_net_size_clamping():
    # File with lots of deletions should have net_size clamped to minimum 5
    commits = [
        CommitInfo(
            "c1", "Dev", "dev@test.com", 1, "2026-01-01", "del", [FileChange("deleted.py", 0, 500)]
        )
    ]
    hotspots = analyze_hotspots(commits)
    assert len(hotspots) == 1
    assert hotspots[0].estimated_size == 5
    assert hotspots[0].risk_level == "LOW"


def test_hotspot_empty():
    assert analyze_hotspots([]) == []
    summary = summarize_hotspots([])
    assert summary["total_hotspots"] == 0
    assert summary["highest_risk_file"] is None


def test_hotspot_low_churn_not_critical_or_high():
    # A single commit adding 1000 lines should NOT be marked as HIGH or CRITICAL hotspot
    commits = [
        CommitInfo(
            "c1",
            "Dev",
            "dev@test.com",
            1,
            "2026-01-01",
            "init",
            [FileChange("large_init.py", 1000, 0)],
        )
    ]
    hotspots = analyze_hotspots(commits)
    assert len(hotspots) == 1
    assert hotspots[0].risk_level not in ("CRITICAL", "HIGH")
    assert hotspots[0].risk_level == "LOW"
