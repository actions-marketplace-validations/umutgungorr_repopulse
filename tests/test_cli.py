"""Integration tests for RepoPulse CLI using a local temporary git repository."""

import json
import subprocess
from pathlib import Path

from repopulse.cli import main


def create_mock_git_repo(repo_dir: Path):
    """Initializes a git repository with mock commits for testing."""
    subprocess.run(["git", "init"], cwd=repo_dir, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.name", "Alice Test"], cwd=repo_dir, check=True)
    subprocess.run(["git", "config", "user.email", "alice@test.com"], cwd=repo_dir, check=True)

    # Commit 1
    (repo_dir / "app.py").write_text("print('hello')\n")
    (repo_dir / "utils.py").write_text("def helper(): pass\n")
    subprocess.run(["git", "add", "."], cwd=repo_dir, check=True)
    subprocess.run(["git", "commit", "-m", "Initial commit"], cwd=repo_dir, check=True)

    # Commit 2
    (repo_dir / "app.py").write_text("print('hello world')\n")
    subprocess.run(["git", "commit", "-am", "Update app"], cwd=repo_dir, check=True)


def test_cli_audit_text(tmp_path: Path):
    create_mock_git_repo(tmp_path)

    code = main(["audit", str(tmp_path)])
    assert code == 0


def test_cli_default_without_subcommand(tmp_path: Path):
    create_mock_git_repo(tmp_path)

    # Directly passing path without 'audit' should default to audit
    code = main([str(tmp_path)])
    assert code == 0


def test_cli_audit_json(tmp_path: Path):
    create_mock_git_repo(tmp_path)
    out_json = tmp_path / "report.json"

    code = main(["audit", str(tmp_path), "--json", "-o", str(out_json)])
    assert code == 0
    assert out_json.exists()

    data = json.loads(out_json.read_text(encoding="utf-8"))
    assert data["total_commits"] == 2
    assert data["total_authors"] == 1
    assert data["overall_health_score"] > 0


def test_cli_audit_markdown_and_export(tmp_path: Path):
    create_mock_git_repo(tmp_path)
    out_md = tmp_path / "report.md"

    code = main(["audit", str(tmp_path), "--markdown", "--export", str(out_md)])
    assert code == 0
    assert out_md.exists()
    assert "# 🩺 RepoPulse Git Forensic Health Audit" in out_md.read_text(encoding="utf-8")


def test_cli_audit_fail_under(tmp_path: Path):
    create_mock_git_repo(tmp_path)

    # A health score is at most 100. If we require 101, it must fail with exit code 1
    code = main(["audit", str(tmp_path), "--fail-under", "101"])
    assert code == 1


def test_cli_audit_step_summary(tmp_path: Path, monkeypatch):
    create_mock_git_repo(tmp_path)
    summary_file = tmp_path / "step_summary.md"
    monkeypatch.setenv("GITHUB_STEP_SUMMARY", str(summary_file))

    code = main(["audit", str(tmp_path), "--summary"])
    assert code == 0
    assert summary_file.exists()
    assert "RepoPulse Git Forensic Health Audit" in summary_file.read_text(encoding="utf-8")


def test_cli_subcommands(tmp_path: Path):
    create_mock_git_repo(tmp_path)

    # Bus factor subcommand
    assert main(["busfactor", str(tmp_path)]) == 0
    assert main(["busfactor", str(tmp_path), "--json"]) == 0
    assert main(["busfactor", str(tmp_path), "--markdown"]) == 0

    # Hotspots subcommand
    assert main(["hotspots", str(tmp_path)]) == 0
    assert main(["hotspots", str(tmp_path), "--json"]) == 0
    assert main(["hotspots", str(tmp_path), "--markdown"]) == 0

    # Coupling subcommand
    assert main(["coupling", str(tmp_path)]) == 0
    assert main(["coupling", str(tmp_path), "--json"]) == 0
    assert main(["coupling", str(tmp_path), "--markdown"]) == 0


def test_cli_flags(tmp_path: Path):
    create_mock_git_repo(tmp_path)
    assert main(["audit", str(tmp_path), "--no-color", "--ascii", "-n", "10"]) == 0


def test_cli_invalid_path():
    code = main(["audit", "non_existent_path_xyz_123"])
    assert code == 2
