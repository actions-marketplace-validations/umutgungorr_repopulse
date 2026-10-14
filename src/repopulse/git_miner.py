"""Backwards-compatible alias for repopulse.miner."""

from __future__ import annotations

from repopulse.miner import COMMIT_DELIMITER, GitMiner, clean_renamed_path

__all__ = ["COMMIT_DELIMITER", "GitMiner", "clean_renamed_path"]
