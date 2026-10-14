"""Unit tests for composite health scoring and grading."""

from repopulse.models import FileBusFactor, Hotspot, TemporalCoupling
from repopulse.scorer import assign_grade, compute_health_score


def test_pristine_repo_score():
    breakdown = compute_health_score(
        bus_risks=[],
        hotspots=[],
        couplings=[],
        total_commits=50,
        total_authors=5,
    )
    assert breakdown.overall_score == 100
    assert breakdown.grade == "A"
    assert breakdown.bus_factor_deduction == 0
    assert breakdown.hotspot_deduction == 0
    assert breakdown.coupling_deduction == 0
    assert breakdown.single_author_deduction == 0


def test_bus_factor_deduction_capping():
    # 10 at-risk files * 5 = 50, but capped at 35
    bus_risks = [
        FileBusFactor(f"file_{i}.py", 5, "Alice", 100.0, 1, is_at_risk=True) for i in range(10)
    ]
    breakdown = compute_health_score(
        bus_risks=bus_risks,
        hotspots=[],
        couplings=[],
        total_commits=50,
        total_authors=5,
    )
    assert breakdown.bus_factor_deduction == 35
    assert breakdown.overall_score == 65
    assert breakdown.grade == "D"


def test_hotspot_deduction_capping():
    # 8 CRITICAL hotspots * 5 = 40, capped at 35
    hotspots = [Hotspot(f"hot_{i}.py", 20, 200, 10, 190, 30.0, "CRITICAL") for i in range(8)]
    breakdown = compute_health_score(
        bus_risks=[],
        hotspots=hotspots,
        couplings=[],
        total_commits=50,
        total_authors=5,
    )
    assert breakdown.hotspot_deduction == 35
    assert breakdown.overall_score == 65


def test_coupling_deduction_capping():
    # 10 coupled pairs * 3 = 30, capped at 20
    couplings = [TemporalCoupling(f"a_{i}.py", f"b_{i}.py", 5, 80.0) for i in range(10)]
    breakdown = compute_health_score(
        bus_risks=[],
        hotspots=[],
        couplings=couplings,
        total_commits=50,
        total_authors=5,
    )
    assert breakdown.coupling_deduction == 20
    assert breakdown.overall_score == 80
    assert breakdown.grade == "B"


def test_single_author_penalty():
    # Single author with >= 10 commits gets 10 points penalty
    breakdown = compute_health_score(
        bus_risks=[],
        hotspots=[],
        couplings=[],
        total_commits=15,
        total_authors=1,
    )
    assert breakdown.single_author_deduction == 10
    assert breakdown.overall_score == 90
    assert breakdown.grade == "A"


def test_minimum_score_floor():
    # Maximum possible penalties: 35 + 35 + 20 + 10 = 100 deduction
    bus_risks = [FileBusFactor(f"f{i}.py", 5, "Solo", 100.0, 1, True) for i in range(10)]
    hotspots = [Hotspot(f"h{i}.py", 20, 200, 10, 190, 30.0, "CRITICAL") for i in range(10)]
    couplings = [TemporalCoupling(f"a{i}.py", f"b{i}.py", 5, 80.0) for i in range(10)]

    breakdown = compute_health_score(
        bus_risks=bus_risks,
        hotspots=hotspots,
        couplings=couplings,
        total_commits=20,
        total_authors=1,
    )
    # 100 - 35 - 35 - 20 - 10 = 0 -> clamped to minimum 10
    assert breakdown.overall_score == 10
    assert breakdown.grade == "F"


def test_assign_grade_ranges():
    assert assign_grade(95)[0] == "A"
    assert assign_grade(85)[0] == "B"
    assert assign_grade(75)[0] == "C"
    assert assign_grade(65)[0] == "D"
    assert assign_grade(50)[0] == "F"
