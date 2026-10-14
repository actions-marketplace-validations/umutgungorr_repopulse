"""GitHub Action runner for RepoPulse Git Forensic Health Audit.

Reads configuration from GitHub Actions runner environment, computes codebase health,
populates GITHUB_OUTPUT, and writes formatted Markdown to $GITHUB_STEP_SUMMARY.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

# Ensure repopulse package root is importable across all runner environments
_SRC_DIR = str(Path(__file__).resolve().parent.parent)
if _SRC_DIR not in sys.path:
    sys.path.insert(0, _SRC_DIR)

from repopulse.engine import RepoPulseEngine  # noqa: E402
from repopulse.formatter import format_markdown  # noqa: E402


def set_output(name: str, value: str) -> None:
    """Writes key=value output to $GITHUB_OUTPUT file."""
    output_path = os.environ.get("GITHUB_OUTPUT")
    if not output_path:
        return
    try:
        with open(output_path, "a", encoding="utf-8") as f:
            f.write(f"{name}={value}\n")
    except OSError:
        pass


def write_step_summary(markdown_text: str) -> None:
    """Appends markdown content to $GITHUB_STEP_SUMMARY."""
    summary_path = os.environ.get("GITHUB_STEP_SUMMARY")
    if not summary_path:
        return
    try:
        with open(summary_path, "a", encoding="utf-8") as f:
            f.write(markdown_text + "\n")
    except OSError:
        pass


def run_action() -> int:
    """Executes the RepoPulse GitHub Action workflow step."""
    repo_path = os.environ.get("INPUT_PATH", ".").strip() or "."
    raw_fail_under = os.environ.get("INPUT_FAIL_UNDER", "").strip()
    write_summary = os.environ.get("INPUT_SUMMARY", "true").strip().lower() in ("true", "1", "yes")
    since = os.environ.get("INPUT_SINCE", "").strip() or None
    raw_max_commits = os.environ.get("INPUT_MAX_COMMITS", "").strip()
    export_file = os.environ.get("INPUT_EXPORT_FILE", "").strip() or None

    max_commits = int(raw_max_commits) if raw_max_commits.isdigit() else None
    fail_under = int(raw_fail_under) if raw_fail_under.isdigit() else None

    try:
        engine = RepoPulseEngine(repo_path)
        report = engine.analyze(max_commits=max_commits, since=since)
    except (ValueError, RuntimeError) as e:
        sys.stderr.write(f"RepoPulse Action Error: {e}\n")
        return 2

    # Calculate metric outputs
    bus_risk_count = sum(1 for b in report.bus_factor_risks if b.is_at_risk)
    hotspot_count = sum(1 for h in report.hotspots if h.risk_level in ("CRITICAL", "HIGH"))

    set_output("health-score", str(report.overall_health_score))
    set_output("bus-factor-alerts", str(bus_risk_count))
    set_output("hotspot-count", str(hotspot_count))

    md_report = format_markdown(report)

    # Optional export file
    if export_file:
        try:
            out_p = Path(export_file)
            out_p.parent.mkdir(parents=True, exist_ok=True)
            out_p.write_text(md_report, encoding="utf-8")
        except OSError as e:
            sys.stderr.write(f"Warning: Failed to write export file '{export_file}': {e}\n")

    # Step Summary
    if write_summary:
        write_step_summary(md_report)

    # Print summary to stdout for job log visibility
    print(
        f"RepoPulse: Health Score = {report.overall_health_score}/100 (Grade {report.health_grade})"
    )
    print(
        f"RepoPulse: Bus Factor Alerts = {bus_risk_count}, Critical/High Hotspots = {hotspot_count}"
    )

    # Enforce quality gate
    if fail_under is not None and report.overall_health_score < fail_under:
        sys.stderr.write(
            f"RepoPulse CI Gate Failure: Overall health score {report.overall_health_score} "
            f"fell below required threshold of {fail_under}.\n"
        )
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(run_action())
