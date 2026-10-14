"""Git log mining and commit stream extraction engine."""

from __future__ import annotations

import re
import subprocess
from collections.abc import Iterator
from pathlib import Path

from repopulse.models import CommitInfo, FileChange

COMMIT_DELIMITER = "---REPO_PULSE_COMMIT---"


def clean_renamed_path(path: str) -> str:
    """Normalizes git renamed paths like 'lib/{old => new}/file.py' or 'old.py => new.py'."""
    path = path.strip().strip("'\"")
    if "=>" not in path:
        return path

    # Case: dir/{old => new}/file.py
    brace_match = re.search(r"\{([^}]*=>[^}]*)\}", path)
    if brace_match:
        inside = brace_match.group(1)
        parts = inside.split("=>")
        new_sub = parts[1].strip()
        prefix = path[: brace_match.start()]
        suffix = path[brace_match.end() :]
        reconstructed = prefix + new_sub + suffix
        return re.sub(r"/+", "/", reconstructed).strip().lstrip("/")

    # Case: old.py => new.py
    parts = path.split("=>")
    target = parts[-1].strip().strip("'\"")
    return re.sub(r"/+", "/", target).strip().lstrip("/")


class GitMiner:
    """Cross-platform native Git log miner with streaming and UTF-8 recovery."""

    def __init__(self, repo_path: str = "."):
        self.repo_path = Path(repo_path).resolve()
        self._verify_git_repo()

    def _verify_git_repo(self) -> None:
        if not self.repo_path.exists() or not self.repo_path.is_dir():
            raise ValueError(f"Target directory '{self.repo_path}' is not a valid Git repository.")
        try:
            res = subprocess.run(
                ["git", "rev-parse", "--is-inside-work-tree"],
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                check=False,
            )
            if res.returncode != 0 or "true" not in res.stdout.strip().lower():
                raise ValueError(
                    f"Target directory '{self.repo_path}' is not a valid Git repository."
                )
        except FileNotFoundError:
            raise RuntimeError("Git executable not found in system PATH.")

    def build_log_command(
        self,
        max_commits: int | None = None,
        since: str | None = None,
        subpath: str | None = None,
    ) -> list[str]:
        """Constructs git log command line arguments."""
        cmd = [
            "git",
            "-c",
            "core.quotepath=false",
            "log",
            f"--pretty=format:{COMMIT_DELIMITER}%x1f%H%x1f%an%x1f%ae%x1f%at%x1f%ad%x1f%s",
            "--date=iso",
            "--numstat",
            "--no-merges",
        ]
        if max_commits:
            cmd.extend(["-n", str(max_commits)])
        if since:
            cmd.extend(["--since", since])
        if subpath:
            cmd.extend(["--", subpath])
        return cmd

    def mine_commits(
        self,
        max_commits: int | None = None,
        since: str | None = None,
        subpath: str | None = None,
    ) -> list[CommitInfo]:
        """Extracts structured commit history using git log --numstat."""
        cmd = self.build_log_command(max_commits=max_commits, since=since, subpath=subpath)

        res = subprocess.run(
            cmd,
            cwd=self.repo_path,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
        )

        if res.returncode != 0:
            raise RuntimeError(f"Git log failed: {res.stderr}")

        return self.parse_git_log_output(res.stdout)

    def stream_commits(
        self,
        max_commits: int | None = None,
        since: str | None = None,
        subpath: str | None = None,
    ) -> Iterator[CommitInfo]:
        """Streams commits one by one directly from git log output for low memory overhead."""
        cmd = self.build_log_command(max_commits=max_commits, since=since, subpath=subpath)

        proc = subprocess.Popen(
            cmd,
            cwd=self.repo_path,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
        )

        if proc.stdout is None:
            return

        current_block: list[str] = []
        for line in proc.stdout:
            if line.startswith(COMMIT_DELIMITER):
                if current_block:
                    commit = self._parse_single_block("\n".join(current_block))
                    if commit:
                        yield commit
                    current_block = [line]
                else:
                    current_block.append(line)
            else:
                current_block.append(line)

        if current_block:
            commit = self._parse_single_block("\n".join(current_block))
            if commit:
                yield commit

        proc.wait()

    @classmethod
    def _parse_single_block(cls, block: str) -> CommitInfo | None:
        block = block.strip()
        if not block:
            return None

        lines = block.splitlines()
        meta_line = lines[0]
        # Remove delimiter prefix if present
        if meta_line.startswith(COMMIT_DELIMITER):
            meta_line = meta_line[len(COMMIT_DELIMITER) :]
        if meta_line.startswith("\x1f"):
            meta_line = meta_line[1:]

        fields = meta_line.split("\x1f", 5)
        if len(fields) < 5:
            return None

        commit_hash = fields[0].strip()
        author_name = fields[1].strip()
        author_email = fields[2].strip()
        ts_str = fields[3].strip()
        timestamp = int(ts_str) if ts_str.isdigit() else 0
        date_str = fields[4].strip()
        message = fields[5].strip() if len(fields) > 5 else ""

        file_changes: list[FileChange] = []
        for numstat_line in lines[1:]:
            numstat_line = numstat_line.strip()
            if not numstat_line:
                continue

            parts = numstat_line.split("\t")
            if len(parts) >= 3:
                added_str, deleted_str, raw_path = parts[0], parts[1], parts[2]
                added = int(added_str) if added_str.isdigit() else 0
                deleted = int(deleted_str) if deleted_str.isdigit() else 0
                cleaned_path = clean_renamed_path(raw_path.strip())

                # Skip non-code / binary files where git displays '-' '-'
                if added_str == "-" and deleted_str == "-":
                    continue

                file_changes.append(FileChange(path=cleaned_path, added=added, deleted=deleted))

        return CommitInfo(
            hash=commit_hash,
            author_name=author_name,
            author_email=author_email,
            timestamp=timestamp,
            date_str=date_str,
            message=message,
            files=file_changes,
        )

    @classmethod
    def parse_git_log_output(cls, output: str) -> list[CommitInfo]:
        """Parses raw text output from git log --numstat into list of CommitInfo."""
        commits: list[CommitInfo] = []
        raw_blocks = output.split(COMMIT_DELIMITER)

        for block in raw_blocks:
            c = cls._parse_single_block(block)
            if c:
                commits.append(c)

        return commits
