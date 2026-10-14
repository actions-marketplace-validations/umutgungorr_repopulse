"""Terminal, Markdown, and JSON formatters for RepoPulse."""

from __future__ import annotations

import json
import os
import sys
from collections.abc import Sequence

from repopulse.models import FileBusFactor, Hotspot, RepoHealthReport, TemporalCoupling


def should_use_color(no_color_flag: bool = False) -> bool:
    """Determines whether ANSI colors should be used."""
    if no_color_flag:
        return False
    if os.environ.get("NO_COLOR", "").strip():
        return False
    if os.environ.get("TERM") == "dumb":
        return False
    return sys.stdout.isatty() or os.environ.get("FORCE_COLOR") == "1"


class Style:
    """ANSI color and styling helper with toggle capability."""

    def __init__(self, use_color: bool = True):
        self.use_color = use_color

    def _c(self, code: str, text: str) -> str:
        return f"\033[{code}m{text}\033[0m" if self.use_color else text

    def bold(self, text: str) -> str:
        return self._c("1", text)

    def red(self, text: str) -> str:
        return self._c("31;1", text)

    def yellow(self, text: str) -> str:
        return self._c("33;1", text)

    def green(self, text: str) -> str:
        return self._c("32;1", text)

    def cyan(self, text: str) -> str:
        return self._c("36;1", text)

    def magenta(self, text: str) -> str:
        return self._c("35;1", text)

    def gray(self, text: str) -> str:
        return self._c("90", text)


def render_progress_bar(score: int, width: int = 20, use_ascii: bool = False) -> str:
    """Renders visual meter for 0-100 score."""
    clamped = max(0, min(100, score))
    filled_len = int(round(width * clamped / 100))
    empty_len = width - filled_len

    if use_ascii:
        return f"[{'#' * filled_len}{'-' * empty_len}]"
    return f"[{'█' * filled_len}{'░' * empty_len}]"


def format_score_badge(score: int, grade: str, style: Style, use_ascii: bool = False) -> str:
    bar = render_progress_bar(score, width=20, use_ascii=use_ascii)
    if score >= 85:
        return style.green(f"{score}/100 [Grade {grade}] {bar} HEALTHY")
    elif score >= 70:
        return style.yellow(f"{score}/100 [Grade {grade}] {bar} MODERATE RISK")
    else:
        return style.red(f"{score}/100 [Grade {grade}] {bar} CRITICAL RISK")


def format_text(
    report: RepoHealthReport,
    use_color: bool = True,
    use_ascii: bool = False,
) -> str:
    """Renders complete forensic health dashboard."""
    s = Style(use_color)
    sep_char = "=" if use_ascii else "━"
    sub_sep = "-" if use_ascii else "─"
    bullet = "*" if use_ascii else "•"
    line_w = 78

    out: list[str] = []

    # Header
    out.append(s.bold(s.cyan("\n RepoPulse Git Forensic Health Audit")))
    out.append(s.gray(sep_char * line_w))
    out.append(f"{s.bold('Target Repository:')} {report.repo_name}")
    out.append(
        f"{s.bold('Overall Health Score:')} {format_score_badge(report.overall_health_score, report.health_grade, s, use_ascii)}"
    )
    out.append(
        f"{s.bold('Repository Vitals:')} {report.total_commits} commits {bullet} "
        f"{report.total_authors} contributor(s) {bullet} {report.active_days} active day(s)"
    )
    out.append(s.gray(sub_sep * line_w))

    # 1. Bus Factor Knowledge Concentration
    icon_bus = "[BUS RISK]" if use_ascii else "🚨 Bus Factor & Knowledge Silo Alerts"
    out.append(s.bold(f"\n{icon_bus}:"))
    at_risk = [b for b in report.bus_factor_risks if b.is_at_risk]
    if at_risk:
        out.append(
            s.gray(f"  {'Concentration':<15} {'Revisions':<11} {'Top Author':<20} {'File Path'}")
        )
        out.append(s.gray(f"  {sub_sep * (line_w - 2)}"))
        for b in at_risk[:8]:
            pct_raw = f"{b.top_author_pct:.1f}% solo"
            pct_col = s.red(f"{pct_raw:<15}")
            top_auth_col = f"{b.top_author[:18]:<20}"
            out.append(f"  {pct_col} {b.total_revisions:<11} {top_auth_col} {s.cyan(b.path)}")
        if len(at_risk) > 8:
            out.append(s.gray(f"  ... and {len(at_risk) - 8} more at-risk files."))
    else:
        ok_icon = "[OK]" if use_ascii else "✅"
        out.append(
            s.green(
                f"  {ok_icon} Balanced ownership across scanned files. No acute bus-factor bottlenecks."
            )
        )

    # 2. Architectural Hotspots
    icon_hotspot = "[HOTSPOTS]" if use_ascii else "🔥 Architectural Hotspots (High Churn + Volume)"
    out.append(s.bold(f"\n{icon_hotspot}:"))
    if report.hotspots:
        out.append(
            s.gray(
                f"  {'Risk Level':<12} {'Churn':<8} {'Net Lines':<12} {'Score':<8} {'File Path'}"
            )
        )
        out.append(s.gray(f"  {sub_sep * (line_w - 2)}"))
        for h in report.hotspots[:8]:
            tag = f"[{h.risk_level}]"
            tag_pad = f"{tag:<12}"
            if h.risk_level == "CRITICAL":
                lvl = s.red(tag_pad)
            elif h.risk_level == "HIGH":
                lvl = s.red(tag_pad)
            elif h.risk_level == "MEDIUM":
                lvl = s.yellow(tag_pad)
            else:
                lvl = s.gray(tag_pad)
            out.append(
                f"  {lvl} {h.churn_count:<8} {h.estimated_size:<12} {h.hotspot_score:<8.1f} {s.cyan(h.path)}"
            )
        if len(report.hotspots) > 8:
            out.append(s.gray(f"  ... and {len(report.hotspots) - 8} more hotspots."))
    else:
        out.append(s.gray("  No hotspots detected."))

    # 3. Temporal Coupling
    icon_coupling = "[COUPLING]" if use_ascii else "🔗 Temporal Coupling (Implicit Dependencies)"
    out.append(s.bold(f"\n{icon_coupling}:"))
    if report.couplings:
        out.append(s.gray(f"  {'Co-Changes':<12} {'Coupling %':<12} {'Connected File Pair'}"))
        out.append(s.gray(f"  {sub_sep * (line_w - 2)}"))
        for c in report.couplings[:6]:
            c_pct_str = f"{c.coupling_pct:.1f}%"
            c_pct_col = s.yellow(f"{c_pct_str:<12}")
            arrow = "<-->" if use_ascii else "⟷"
            out.append(f"  {c.co_changes:<12} {c_pct_col} {c.file_a} {arrow} {c.file_b}")
        if len(report.couplings) > 6:
            out.append(s.gray(f"  ... and {len(report.couplings) - 6} more coupled pairs."))
    else:
        ok_icon = "[OK]" if use_ascii else "✅"
        out.append(
            s.green(f"  {ok_icon} No tight temporal coupling detected between disjoint files.")
        )

    # 4. Top Contributors
    icon_contrib = "[AUTHORS]" if use_ascii else "👥 Top Contributor Distribution"
    out.append(s.bold(f"\n{icon_contrib}:"))
    if report.author_contributions:
        for author, count in list(report.author_contributions.items())[:5]:
            pct = (count / max(1, report.total_commits)) * 100
            out.append(f"  {s.gray(bullet)} {author:<24} {count} commits ({pct:.1f}%)")
    else:
        out.append(s.gray("  No contributor data recorded."))

    out.append(s.gray("\n" + sep_char * line_w + "\n"))
    return "\n".join(out)


def format_busfactor_table(
    bus_risks: Sequence[FileBusFactor],
    use_color: bool = True,
    use_ascii: bool = False,
) -> str:
    """Formats bus factor sub-analysis as dedicated terminal table."""
    s = Style(use_color)
    sub_sep = "-" if use_ascii else "─"
    line_w = 78

    out = [
        s.bold(s.cyan("\n RepoPulse Bus Factor & Knowledge Silo Analysis")),
        s.gray(sub_sep * line_w),
    ]

    if not bus_risks:
        out.append(s.green("  No acute bus factor bottlenecks found."))
        out.append(s.gray(sub_sep * line_w + "\n"))
        return "\n".join(out)

    out.append(
        s.gray(
            f"{'Status':<12} {'Revisions':<11} {'Top Author':<22} {'Concentration':<15} {'File Path'}"
        )
    )
    out.append(s.gray(sub_sep * line_w))

    for b in bus_risks:
        tag = "[RISK]" if b.is_at_risk else "[BALANCED]"
        tag_pad = f"{tag:<12}"
        status_cell = s.red(tag_pad) if b.is_at_risk else s.green(tag_pad)

        pct_str = f"{b.top_author_pct:.1f}%"
        pct_pad = f"{pct_str:<15}"
        pct_cell = s.red(pct_pad) if b.is_at_risk else s.gray(pct_pad)

        top_author_str = f"{b.top_author[:20]:<22}"
        out.append(
            f"{status_cell} {b.total_revisions:<11} {top_author_str} {pct_cell} {s.cyan(b.path)}"
        )

    out.append(s.gray(sub_sep * line_w + "\n"))
    return "\n".join(out)


def format_hotspots_table(
    hotspots: Sequence[Hotspot],
    use_color: bool = True,
    use_ascii: bool = False,
) -> str:
    """Formats hotspots sub-analysis as dedicated terminal table."""
    s = Style(use_color)
    sub_sep = "-" if use_ascii else "─"
    line_w = 78

    out = [
        s.bold(s.cyan("\n RepoPulse Architectural Hotspots & Churn Analysis")),
        s.gray(sub_sep * line_w),
    ]

    if not hotspots:
        out.append(s.green("  No architectural hotspots detected."))
        out.append(s.gray(sub_sep * line_w + "\n"))
        return "\n".join(out)

    out.append(
        s.gray(
            f"{'Risk Level':<12} {'Churn':<8} {'Added':<8} {'Deleted':<8} {'Score':<8} {'File Path'}"
        )
    )
    out.append(s.gray(sub_sep * line_w))

    for h in hotspots:
        tag = f"[{h.risk_level}]"
        tag_pad = f"{tag:<12}"
        if h.risk_level == "CRITICAL":
            lvl = s.red(tag_pad)
        elif h.risk_level == "HIGH":
            lvl = s.red(tag_pad)
        elif h.risk_level == "MEDIUM":
            lvl = s.yellow(tag_pad)
        else:
            lvl = s.gray(tag_pad)
        out.append(
            f"{lvl} {h.churn_count:<8} {h.lines_added:<8} {h.lines_deleted:<8} {h.hotspot_score:<8.1f} {s.cyan(h.path)}"
        )

    out.append(s.gray(sub_sep * line_w + "\n"))
    return "\n".join(out)


def format_coupling_table(
    couplings: Sequence[TemporalCoupling],
    use_color: bool = True,
    use_ascii: bool = False,
) -> str:
    """Formats coupling sub-analysis as dedicated terminal table."""
    s = Style(use_color)
    sub_sep = "-" if use_ascii else "─"
    arrow = "<-->" if use_ascii else "⟷"
    line_w = 78

    out = [s.bold(s.cyan("\n RepoPulse Temporal Co-Change Coupling")), s.gray(sub_sep * line_w)]

    if not couplings:
        out.append(s.green("  No tight temporal coupling detected between disjoint files."))
        out.append(s.gray(sub_sep * line_w + "\n"))
        return "\n".join(out)

    out.append(s.gray(f"{'Co-Changes':<12} {'Coupling Degree':<18} {'File Pair'}"))
    out.append(s.gray(sub_sep * line_w))

    for c in couplings:
        c_pct_str = f"{c.coupling_pct:.1f}%"
        c_pct_pad = f"{c_pct_str:<18}"
        c_pct = s.yellow(c_pct_pad)
        out.append(f"{c.co_changes:<12} {c_pct} {c.file_a} {arrow} {c.file_b}")

    out.append(s.gray(sub_sep * line_w + "\n"))
    return "\n".join(out)


def format_markdown(report: RepoHealthReport) -> str:
    """Renders PR-ready and GITHUB_STEP_SUMMARY Markdown health report."""
    grade_emoji = (
        "🟢"
        if report.overall_health_score >= 80
        else ("🟡" if report.overall_health_score >= 60 else "🔴")
    )

    lines = [
        f"# 🩺 RepoPulse Git Forensic Health Audit: `{report.repo_name}`",
        "",
        f"### {grade_emoji} Health Score: **`{report.overall_health_score} / 100`** (Grade `{report.health_grade}`)",
        "",
        f"- **Total Commits Analyzed:** `{report.total_commits}`",
        f"- **Unique Contributors:** `{report.total_authors}`",
        f"- **Active Commit Days:** `{report.active_days}`",
        "",
        "---",
        "",
        "## 🚨 Bus Factor Knowledge Concentration",
        "",
    ]

    at_risk = [b for b in report.bus_factor_risks if b.is_at_risk]
    if at_risk:
        lines.extend(
            [
                "| File Path | Revisions | Top Contributor | Concentration % | Status |",
                "|:---|:---:|:---|:---:|:---:|",
            ]
        )
        for b in at_risk[:15]:
            lines.append(
                f"| `{b.path}` | {b.total_revisions} | {b.top_author} | **{b.top_author_pct:.1f}%** | ⚠️ At Risk |"
            )
    else:
        lines.append("✅ **Balanced ownership.** No single-point-of-failure files detected.")

    lines.extend(
        [
            "",
            "## 🔥 Architectural Hotspots",
            "",
            "| File Path | Churn (Revs) | Net Lines | Hotspot Score | Risk Level |",
            "|:---|:---:|:---:|:---:|:---:|",
        ]
    )
    if report.hotspots:
        for h in report.hotspots[:15]:
            lines.append(
                f"| `{h.path}` | {h.churn_count} | {h.estimated_size} | {h.hotspot_score:.1f} | **`{h.risk_level}`** |"
            )
    else:
        lines.append("✅ No critical hotspot churn detected.")

    lines.extend(
        [
            "",
            "## 🔗 Temporal Co-Change Coupling",
            "",
        ]
    )
    if report.couplings:
        lines.extend(
            [
                "| Connected File Pair | Co-Changes | Coupling Degree |",
                "|:---|:---:|:---:|",
            ]
        )
        for c in report.couplings[:10]:
            lines.append(
                f"| `{c.file_a}` ⟷ `{c.file_b}` | {c.co_changes} | **{c.coupling_pct:.1f}%** |"
            )
    else:
        lines.append(
            "✅ **Clean architecture.** No tight temporal coupling found between disjoint files."
        )

    lines.extend(
        [
            "",
            "---",
            "<sub>Report generated automatically by [RepoPulse Git Forensic Audit](https://github.com/umutgungorr/repopulse).</sub>",
            "",
        ]
    )

    return "\n".join(lines)


def format_json(report: RepoHealthReport) -> str:
    """Formats health report as formatted JSON string."""
    return json.dumps(report.to_dict(), indent=2, ensure_ascii=False)
