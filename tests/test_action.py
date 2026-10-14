"""Unit and integration tests for GitHub Action runner (action.py)."""

import subprocess
from pathlib import Path

from repopulse.action import run_action, set_output, write_step_summary


def create_mock_git_repo(repo_dir: Path):
    """Initializes a git repository with mock commits for testing."""
    subprocess.run(["git", "init"], cwd=repo_dir, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.name", "Alice Test"], cwd=repo_dir, check=True)
    subprocess.run(["git", "config", "user.email", "alice@test.com"], cwd=repo_dir, check=True)

    (repo_dir / "app.py").write_text("print('hello')\n")
    subprocess.run(["git", "add", "."], cwd=repo_dir, check=True)
    subprocess.run(["git", "commit", "-m", "Initial commit"], cwd=repo_dir, check=True)


def test_set_output(tmp_path: Path, monkeypatch):
    out_file = tmp_path / "github_output.txt"
    monkeypatch.setenv("GITHUB_OUTPUT", str(out_file))

    set_output("test-key", "test-val")
    assert out_file.exists()
    assert "test-key=test-val\n" in out_file.read_text(encoding="utf-8")


def test_write_step_summary(tmp_path: Path, monkeypatch):
    summary_file = tmp_path / "summary.md"
    monkeypatch.setenv("GITHUB_STEP_SUMMARY", str(summary_file))

    write_step_summary("### Markdown Summary")
    assert summary_file.exists()
    assert "### Markdown Summary\n" in summary_file.read_text(encoding="utf-8")


def test_action_run_success(tmp_path: Path, monkeypatch):
    create_mock_git_repo(tmp_path)

    out_file = tmp_path / "github_output.txt"
    summary_file = tmp_path / "summary.md"
    export_file = tmp_path / "report.md"

    monkeypatch.setenv("INPUT_PATH", str(tmp_path))
    monkeypatch.setenv("INPUT_SUMMARY", "true")
    monkeypatch.setenv("INPUT_EXPORT_FILE", str(export_file))
    monkeypatch.setenv("GITHUB_OUTPUT", str(out_file))
    monkeypatch.setenv("GITHUB_STEP_SUMMARY", str(summary_file))

    code = run_action()
    assert code == 0

    assert out_file.exists()
    out_content = out_file.read_text(encoding="utf-8")
    assert "health-score=" in out_content
    assert "bus-factor-alerts=" in out_content
    assert "hotspot-count=" in out_content

    assert summary_file.exists()
    assert "RepoPulse Git Forensic Health Audit" in summary_file.read_text(encoding="utf-8")

    assert export_file.exists()
    assert "RepoPulse Git Forensic Health Audit" in export_file.read_text(encoding="utf-8")


def test_action_run_fail_under(tmp_path: Path, monkeypatch):
    create_mock_git_repo(tmp_path)

    monkeypatch.setenv("INPUT_PATH", str(tmp_path))
    monkeypatch.setenv("INPUT_FAIL_UNDER", "101")
    monkeypatch.delenv("GITHUB_OUTPUT", raising=False)
    monkeypatch.delenv("GITHUB_STEP_SUMMARY", raising=False)

    code = run_action()
    assert code == 1


def test_action_run_invalid_path(monkeypatch):
    monkeypatch.setenv("INPUT_PATH", "non_existent_path_abc_123")
    code = run_action()
    assert code == 2
