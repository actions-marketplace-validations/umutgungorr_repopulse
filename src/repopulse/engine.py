"""High-level analysis orchestrator and health scoring for RepoPulse."""

from __future__ import annotations

from collections import Counter
from pathlib import Path

from repopulse.busfactor import analyze_bus_factor
from repopulse.coupling import analyze_coupling
from repopulse.hotspots import analyze_hotspots
from repopulse.miner import GitMiner
from repopulse.models import FileBusFactor, Hotspot, RepoHealthReport, TemporalCoupling
from repopulse.scorer import compute_health_score


class RepoPulseEngine:
    """Orchestrates Git mining, bus-factor analysis, hotspot detection, and composite scoring."""

    def __init__(self, repo_path: str = "."):
        self.repo_path = Path(repo_path).resolve()
        self.miner = GitMiner(str(self.repo_path))

    def analyze(
        self,
        max_commits: int | None = None,
        since: str | None = None,
        subpath: str | None = None,
    ) -> RepoHealthReport:
        """Executes full forensic health analysis across git commit history."""
        commits = self.miner.mine_commits(max_commits=max_commits, since=since, subpath=subpath)

        if not commits:
            return RepoHealthReport(
                repo_name=self.repo_path.name,
                total_commits=0,
                total_authors=0,
                active_days=0,
                bus_factor_risks=[],
                hotspots=[],
                couplings=[],
                author_contributions={},
                overall_health_score=100,
                health_grade="A",
            )

        # Basic Stats
        authors_counter = Counter(c.author_name or c.author_email for c in commits)
        active_dates = {c.date_str for c in commits if c.date_str}

        # Sub-analyses
        bus_risks = analyze_bus_factor(commits)
        hotspots = analyze_hotspots(commits)
        couplings = analyze_coupling(commits)

        # Health Scoring
        score_breakdown = compute_health_score(
            bus_risks=bus_risks,
            hotspots=hotspots,
            couplings=couplings,
            total_commits=len(commits),
            total_authors=len(authors_counter),
        )

        return RepoHealthReport(
            repo_name=self.repo_path.name,
            total_commits=len(commits),
            total_authors=len(authors_counter),
            active_days=len(active_dates),
            bus_factor_risks=bus_risks,
            hotspots=hotspots,
            couplings=couplings,
            author_contributions=dict(authors_counter.most_common(10)),
            overall_health_score=score_breakdown.overall_score,
            health_grade=score_breakdown.grade,
        )

    def get_bus_factor(
        self,
        max_commits: int | None = None,
        since: str | None = None,
        subpath: str | None = None,
    ) -> list[FileBusFactor]:
        """Runs bus factor analysis only."""
        commits = self.miner.mine_commits(max_commits=max_commits, since=since, subpath=subpath)
        return analyze_bus_factor(commits)

    def get_hotspots(
        self,
        max_commits: int | None = None,
        since: str | None = None,
        subpath: str | None = None,
        top_n: int = 15,
    ) -> list[Hotspot]:
        """Runs hotspots analysis only."""
        commits = self.miner.mine_commits(max_commits=max_commits, since=since, subpath=subpath)
        return analyze_hotspots(commits, top_n=top_n)

    def get_coupling(
        self,
        max_commits: int | None = None,
        since: str | None = None,
        subpath: str | None = None,
        top_n: int = 15,
    ) -> list[TemporalCoupling]:
        """Runs coupling analysis only."""
        commits = self.miner.mine_commits(max_commits=max_commits, since=since, subpath=subpath)
        return analyze_coupling(commits, top_n=top_n)
