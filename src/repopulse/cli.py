"""Command Line Interface for RepoPulse."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

# UTF-8 safety on Windows terminals
if sys.platform == "win32":
    try:
        if hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        if hasattr(sys.stderr, "reconfigure"):
            sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

from repopulse import __version__
from repopulse.engine import RepoPulseEngine
from repopulse.formatter import (
    format_busfactor_table,
    format_coupling_table,
    format_hotspots_table,
    format_json,
    format_markdown,
    format_text,
    should_use_color,
)


def add_common_analysis_flags(parser: argparse.ArgumentParser) -> None:
    """Adds shared flags to subcommands."""
    parser.add_argument(
        "path",
        nargs="?",
        default=".",
        help="Path to target Git repository (default: current directory)",
    )
    parser.add_argument(
        "-n",
        "--max-commits",
        type=int,
        help="Limit analysis to last N commits",
    )
    parser.add_argument(
        "--since",
        help="Analyze commits since date/duration (e.g. '1.year.ago', '2026-01-01', '6.months.ago')",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output raw machine-readable JSON",
    )
    parser.add_argument(
        "--markdown",
        action="store_true",
        help="Output GitHub-flavored Markdown",
    )
    parser.add_argument(
        "-f",
        "--format",
        choices=["text", "json", "markdown"],
        help="Explicit output format (default: text)",
    )
    parser.add_argument(
        "-o",
        "--output",
        dest="output_file",
        help="File path to save the generated report",
    )
    parser.add_argument(
        "--export",
        dest="export_file",
        help="Alias for --output: export report to file",
    )
    parser.add_argument(
        "--summary",
        action="store_true",
        help="Append formatted Markdown health card to $GITHUB_STEP_SUMMARY",
    )
    parser.add_argument(
        "--no-color",
        action="store_true",
        help="Disable ANSI colors (also respects NO_COLOR env var)",
    )
    parser.add_argument(
        "--ascii",
        action="store_true",
        help="Use basic ASCII characters instead of Unicode box borders",
    )


def build_parser() -> argparse.ArgumentParser:
    """Constructs CLI argument parser with subcommands."""
    parser = argparse.ArgumentParser(
        prog="repopulse",
        description="Zero-dependency Git forensic health, hotspot churn, and bus-factor risk engine.",
    )
    parser.add_argument("-v", "--version", action="version", version=f"RepoPulse v{__version__}")

    subparsers = parser.add_subparsers(dest="command", help="Available subcommands")

    # 1. audit
    audit_parser = subparsers.add_parser(
        "audit", help="Run full forensic health audit on repository"
    )
    add_common_analysis_flags(audit_parser)
    audit_parser.add_argument(
        "--fail-under",
        type=int,
        help="CI Quality Gate: Exit with code 1 if health score is strictly below this threshold",
    )

    # 2. busfactor
    bus_parser = subparsers.add_parser(
        "busfactor", help="Analyze bus factor and knowledge concentration"
    )
    add_common_analysis_flags(bus_parser)

    # 3. hotspots
    hotspot_parser = subparsers.add_parser(
        "hotspots", help="Identify high-churn architectural hotspots"
    )
    add_common_analysis_flags(hotspot_parser)

    # 4. coupling
    coupling_parser = subparsers.add_parser(
        "coupling", help="Analyze temporal co-change file coupling"
    )
    add_common_analysis_flags(coupling_parser)

    return parser


def write_github_step_summary(markdown_text: str) -> None:
    """Appends markdown content to $GITHUB_STEP_SUMMARY if available."""
    summary_path = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary_path:
        try:
            with open(summary_path, "a", encoding="utf-8") as f:
                f.write(markdown_text + "\n")
        except OSError:
            pass


def determine_format(parsed: argparse.Namespace) -> str:
    """Determines desired output format based on flags."""
    if parsed.json:
        return "json"
    if parsed.markdown:
        return "markdown"
    if parsed.format:
        return parsed.format
    return "text"


def main(args: list[str] | None = None) -> int:
    parser = build_parser()

    # Handle direct invocations like 'repopulse' or 'repopulse /path/to/repo' without subcommands
    raw_args = list(args) if args is not None else sys.argv[1:]
    if not raw_args or (
        raw_args[0]
        not in ("audit", "busfactor", "hotspots", "coupling", "-h", "--help", "-v", "--version")
    ):
        # If the first argument is not a known subcommand or help flag, default to 'audit'
        raw_args = ["audit"] + raw_args

    parsed = parser.parse_args(raw_args)

    target_path = getattr(parsed, "path", ".")
    use_color = should_use_color(parsed.no_color)
    use_ascii = getattr(parsed, "ascii", False)
    fmt = determine_format(parsed)
    dest_file = parsed.export_file or parsed.output_file

    try:
        engine = RepoPulseEngine(target_path)
    except (ValueError, RuntimeError) as e:
        print(f"Error: {e}", file=sys.stderr)
        return 2

    if parsed.command == "audit":
        try:
            report = engine.analyze(max_commits=parsed.max_commits, since=parsed.since)
        except (ValueError, RuntimeError) as e:
            print(f"Error: {e}", file=sys.stderr)
            return 2

        if fmt == "json":
            content = format_json(report)
        elif fmt == "markdown":
            content = format_markdown(report)
        else:
            content = format_text(report, use_color=use_color, use_ascii=use_ascii)

        if dest_file:
            out_p = Path(dest_file)
            out_p.parent.mkdir(parents=True, exist_ok=True)
            out_p.write_text(content, encoding="utf-8")
            print(f"Report written to '{dest_file}'.")
        else:
            print(content)

        if parsed.summary:
            write_github_step_summary(format_markdown(report))

        if parsed.fail_under is not None and report.overall_health_score < parsed.fail_under:
            print(
                f"\nCI Gate Failed: Health score {report.overall_health_score} is below threshold {parsed.fail_under}.",
                file=sys.stderr,
            )
            return 1

        return 0

    elif parsed.command == "busfactor":
        try:
            bus_risks = engine.get_bus_factor(max_commits=parsed.max_commits, since=parsed.since)
        except (ValueError, RuntimeError) as e:
            print(f"Error: {e}", file=sys.stderr)
            return 2

        if fmt == "json":
            import json

            content = json.dumps([b.to_dict() for b in bus_risks], indent=2, ensure_ascii=False)
        elif fmt == "markdown":
            lines = ["# 🚨 Bus Factor Knowledge Concentration", ""]
            lines.extend(
                [
                    "| File Path | Revisions | Top Author | Solo % | Risk |",
                    "|:---|:---:|:---|:---:|:---:|",
                ]
            )
            for b in bus_risks:
                status = "⚠️ Risk" if b.is_at_risk else "✅ Balanced"
                lines.append(
                    f"| `{b.path}` | {b.total_revisions} | {b.top_author} | {b.top_author_pct:.1f}% | {status} |"
                )
            content = "\n".join(lines)
        else:
            content = format_busfactor_table(bus_risks, use_color=use_color, use_ascii=use_ascii)

        if dest_file:
            out_p = Path(dest_file)
            out_p.parent.mkdir(parents=True, exist_ok=True)
            out_p.write_text(content, encoding="utf-8")
            print(f"Report written to '{dest_file}'.")
        else:
            print(content)
        return 0

    elif parsed.command == "hotspots":
        try:
            hotspots = engine.get_hotspots(max_commits=parsed.max_commits, since=parsed.since)
        except (ValueError, RuntimeError) as e:
            print(f"Error: {e}", file=sys.stderr)
            return 2

        if fmt == "json":
            import json

            content = json.dumps([h.to_dict() for h in hotspots], indent=2, ensure_ascii=False)
        elif fmt == "markdown":
            lines = ["# 🔥 Architectural Hotspots", ""]
            lines.extend(
                [
                    "| File Path | Churn | Lines Added | Lines Deleted | Score | Risk Level |",
                    "|:---|:---:|:---:|:---:|:---:|:---:|",
                ]
            )
            for h in hotspots:
                lines.append(
                    f"| `{h.path}` | {h.churn_count} | {h.lines_added} | {h.lines_deleted} | {h.hotspot_score:.1f} | {h.risk_level} |"
                )
            content = "\n".join(lines)
        else:
            content = format_hotspots_table(hotspots, use_color=use_color, use_ascii=use_ascii)

        if dest_file:
            out_p = Path(dest_file)
            out_p.parent.mkdir(parents=True, exist_ok=True)
            out_p.write_text(content, encoding="utf-8")
            print(f"Report written to '{dest_file}'.")
        else:
            print(content)
        return 0

    elif parsed.command == "coupling":
        try:
            couplings = engine.get_coupling(max_commits=parsed.max_commits, since=parsed.since)
        except (ValueError, RuntimeError) as e:
            print(f"Error: {e}", file=sys.stderr)
            return 2

        if fmt == "json":
            import json

            content = json.dumps([c.to_dict() for c in couplings], indent=2, ensure_ascii=False)
        elif fmt == "markdown":
            lines = ["# 🔗 Temporal Coupling", ""]
            lines.extend(
                [
                    "| File Pair | Co-Changes | Coupling % |",
                    "|:---|:---:|:---:|",
                ]
            )
            for c in couplings:
                lines.append(
                    f"| `{c.file_a}` ⟷ `{c.file_b}` | {c.co_changes} | {c.coupling_pct:.1f}% |"
                )
            content = "\n".join(lines)
        else:
            content = format_coupling_table(couplings, use_color=use_color, use_ascii=use_ascii)

        if dest_file:
            out_p = Path(dest_file)
            out_p.parent.mkdir(parents=True, exist_ok=True)
            out_p.write_text(content, encoding="utf-8")
            print(f"Report written to '{dest_file}'.")
        else:
            print(content)
        return 0

    return 0


if __name__ == "__main__":
    sys.exit(main())
