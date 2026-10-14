"""Unit tests for Temporal Coupling analysis."""

from repopulse.coupling import analyze_coupling, summarize_coupling
from repopulse.models import CommitInfo, FileChange


def test_coupling_analysis():
    # File A and File B commit together 3 times out of 3
    commits = [
        CommitInfo(
            "c1",
            "Dev",
            "dev@test.com",
            1,
            "2026-01-01",
            "c1",
            [FileChange("models.py", 5, 0), FileChange("api.py", 10, 0)],
        ),
        CommitInfo(
            "c2",
            "Dev",
            "dev@test.com",
            2,
            "2026-01-02",
            "c2",
            [FileChange("models.py", 2, 0), FileChange("api.py", 4, 0)],
        ),
        CommitInfo(
            "c3",
            "Dev",
            "dev@test.com",
            3,
            "2026-01-03",
            "c3",
            [FileChange("models.py", 1, 0), FileChange("api.py", 1, 0)],
        ),
        CommitInfo(
            "c4", "Dev", "dev@test.com", 4, "2026-01-04", "c4", [FileChange("isolated.py", 10, 0)]
        ),
    ]

    couplings = analyze_coupling(commits, min_co_changes=2, min_coupling_pct=50.0)
    assert len(couplings) == 1
    pair = {couplings[0].file_a, couplings[0].file_b}
    assert pair == {"api.py", "models.py"}
    assert couplings[0].co_changes == 3
    assert couplings[0].coupling_pct == 100.0

    summary = summarize_coupling(couplings)
    assert summary["coupled_pair_count"] == 1
    assert "api.py" in summary["strongest_pair"]


def test_coupling_skips_bulk_commits():
    # A single commit touching 30 files shouldn't explode into 435 fake co-changes
    bulk_files = [FileChange(f"file_{i}.py", 1, 0) for i in range(30)]
    commits = [
        CommitInfo("bulk1", "Dev", "dev@test.com", 1, "2026-01-01", "bulk", bulk_files),
        CommitInfo("bulk2", "Dev", "dev@test.com", 2, "2026-01-02", "bulk", bulk_files),
    ]
    couplings = analyze_coupling(commits)
    assert len(couplings) == 0


def test_coupling_empty():
    assert analyze_coupling([]) == []
    summary = summarize_coupling([])
    assert summary["coupled_pair_count"] == 0
    assert summary["strongest_pair"] is None
