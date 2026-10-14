"""Unit tests for Git miner and log parsing."""

from pathlib import Path

import pytest

from repopulse.miner import COMMIT_DELIMITER, GitMiner, clean_renamed_path


def test_clean_renamed_path():
    assert clean_renamed_path("src/old.py => src/new.py") == "src/new.py"
    assert clean_renamed_path("lib/{foo => bar}/baz.py") == "lib/bar/baz.py"
    assert clean_renamed_path("normal/path/file.py") == "normal/path/file.py"
    assert clean_renamed_path("{old => new}") == "new"


def test_parse_git_log_output():
    raw_log = f"""
{COMMIT_DELIMITER}\x1f1a2b3c4d\x1fAlice Dev\x1falice@test.com\x1f1700000000\x1f2026-01-01 10:00:00 +0000\x1fInitial commit
10\t2\tsrc/main.py
5\t0\tsrc/utils.py

{COMMIT_DELIMITER}\x1f5e6f7a8b\x1fBob Dev\x1fbob@test.com\x1f1700005000\x1f2026-01-02 12:00:00 +0000\x1fFix bug
1\t1\tsrc/main.py
"""
    commits = GitMiner.parse_git_log_output(raw_log)
    assert len(commits) == 2

    c1 = commits[0]
    assert c1.hash == "1a2b3c4d"
    assert c1.author_name == "Alice Dev"
    assert len(c1.files) == 2
    assert c1.files[0].path == "src/main.py"
    assert c1.files[0].added == 10
    assert c1.files[0].deleted == 2

    c2 = commits[1]
    assert c2.hash == "5e6f7a8b"
    assert c2.author_name == "Bob Dev"
    assert len(c2.files) == 1
    assert c2.files[0].path == "src/main.py"


def test_parse_binary_files_skipped():
    raw_log = f"""
{COMMIT_DELIMITER}\x1fdeadbeef\x1fAlice\x1fa@test.com\x1f1700000000\x1f2026-01-01\x1fAdd assets
-\t-\tlogo.png
15\t3\tREADME.md
"""
    commits = GitMiner.parse_git_log_output(raw_log)
    assert len(commits) == 1
    assert len(commits[0].files) == 1
    assert commits[0].files[0].path == "README.md"


def test_parse_empty_and_malformed():
    assert GitMiner.parse_git_log_output("") == []
    assert GitMiner.parse_git_log_output("random unformatted string") == []


def test_invalid_git_repo_raises(tmp_path: Path):
    non_git = tmp_path / "empty_dir"
    non_git.mkdir()
    with pytest.raises(ValueError, match="not a valid Git repository"):
        GitMiner(str(non_git))
