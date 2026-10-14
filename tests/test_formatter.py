"""Unit tests for formatters (text, ANSI, ASCII, markdown, and JSON)."""

import json

from repopulse.formatter import (
    format_busfactor_table,
    format_coupling_table,
    format_hotspots_table,
    format_json,
    format_markdown,
    format_text,
    render_progress_bar,
    should_use_color,
)
from repopulse.models import (
    FileBusFactor,
    Hotspot,
    RepoHealthReport,
    TemporalCoupling,
)


def create_sample_report() -> RepoHealthReport:
    return RepoHealthReport(
        repo_name="demo-repo",
        total_commits=42,
        total_authors=3,
        active_days=14,
        bus_factor_risks=[
            FileBusFactor("src/core.py", 10, "Alice", 90.0, 1, is_at_risk=True),
            FileBusFactor("src/utils.py", 5, "Bob", 40.0, 3, is_at_risk=False),
        ],
        hotspots=[
            Hotspot("src/core.py", 12, 350, 40, 310, 32.5, "CRITICAL"),
            Hotspot("src/api.py", 4, 80, 10, 70, 9.2, "MEDIUM"),
        ],
        couplings=[
            TemporalCoupling("src/core.py", "src/api.py", 5, 83.3),
        ],
        author_contributions={"Alice": 25, "Bob": 12, "Charlie": 5},
        overall_health_score=75,
        health_grade="C",
    )


def test_format_text_output():
    report = create_sample_report()
    text = format_text(report, use_color=False, use_ascii=False)
    assert "RepoPulse Git Forensic Health Audit" in text
    assert "demo-repo" in text
    assert "75/100" in text
    assert "src/core.py" in text
    assert "Alice" in text
    assert "src/api.py" in text


def test_format_text_ascii_mode():
    report = create_sample_report()
    ascii_text = format_text(report, use_color=False, use_ascii=True)
    assert "[BUS RISK]" in ascii_text
    assert "[HOTSPOTS]" in ascii_text
    assert "[COUPLING]" in ascii_text
    assert "===" in ascii_text


def test_format_markdown_output():
    report = create_sample_report()
    md = format_markdown(report)
    assert "# 🩺 RepoPulse Git Forensic Health Audit: `demo-repo`" in md
    assert "**`75 / 100`**" in md
    assert "| `src/core.py` | 10 | Alice | **90.0%** | ⚠️ At Risk |" in md
    assert "## 🔥 Architectural Hotspots" in md
    assert "## 🔗 Temporal Co-Change Coupling" in md


def test_format_json_output():
    report = create_sample_report()
    raw_json = format_json(report)
    parsed = json.loads(raw_json)
    assert parsed["repo_name"] == "demo-repo"
    assert parsed["overall_health_score"] == 75
    assert parsed["health_grade"] == "C"
    assert len(parsed["bus_factor_risks"]) == 2
    assert len(parsed["hotspots"]) == 2
    assert len(parsed["couplings"]) == 1


def test_format_sub_tables():
    report = create_sample_report()
    bf_out = format_busfactor_table(report.bus_factor_risks, use_color=False)
    assert "RepoPulse Bus Factor & Knowledge Silo Analysis" in bf_out
    assert "src/core.py" in bf_out

    hs_out = format_hotspots_table(report.hotspots, use_color=False)
    assert "RepoPulse Architectural Hotspots & Churn Analysis" in hs_out
    assert "src/core.py" in hs_out

    cp_out = format_coupling_table(report.couplings, use_color=False)
    assert "RepoPulse Temporal Co-Change Coupling" in cp_out
    assert "src/core.py" in cp_out


def test_format_sub_tables_empty():
    bf_out = format_busfactor_table([], use_color=False)
    assert "No acute bus factor bottlenecks found." in bf_out

    hs_out = format_hotspots_table([], use_color=False)
    assert "No architectural hotspots detected." in hs_out

    cp_out = format_coupling_table([], use_color=False)
    assert "No tight temporal coupling detected between disjoint files." in cp_out


def test_table_column_alignment():
    report = create_sample_report()
    text = format_text(report, use_color=False)
    lines = text.splitlines()

    # Verify Hotspots column alignment
    header_idx = next(i for i, line in enumerate(lines) if "Risk Level" in line and "Churn" in line)
    data_idx = header_idx + 2
    header_line = lines[header_idx]
    data_line = lines[data_idx]

    # "Churn" header and churn value should start at matching character offsets
    churn_header_pos = header_line.index("Churn")
    assert header_line[churn_header_pos : churn_header_pos + 5] == "Churn"
    assert data_line[churn_header_pos].isdigit()

    # Bus factor sub-table alignment
    bf_text = format_busfactor_table(report.bus_factor_risks, use_color=False)
    bf_lines = bf_text.splitlines()
    bf_hdr_idx = next(
        i for i, line in enumerate(bf_lines) if "Status" in line and "Revisions" in line
    )
    bf_hdr = bf_lines[bf_hdr_idx]
    bf_row = bf_lines[bf_hdr_idx + 2]
    rev_pos = bf_hdr.index("Revisions")
    assert bf_row[rev_pos].isdigit()


def test_render_progress_bar():
    bar_unicode = render_progress_bar(50, width=10, use_ascii=False)
    assert "█████" in bar_unicode
    bar_ascii = render_progress_bar(50, width=10, use_ascii=True)
    assert "[#####-----]" == bar_ascii


def test_should_use_color(monkeypatch):
    assert not should_use_color(no_color_flag=True)

    monkeypatch.setenv("NO_COLOR", "1")
    assert not should_use_color(no_color_flag=False)

    monkeypatch.delenv("NO_COLOR", raising=False)
    monkeypatch.setenv("TERM", "dumb")
    assert not should_use_color(no_color_flag=False)
