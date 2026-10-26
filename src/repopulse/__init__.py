"""RepoPulse - Git forensic health, hotspot churn, and bus-factor risk engine."""

from __future__ import annotations

__version__ = "1.0.1"
__author__ = "Umut Güngör"

from repopulse.busfactor import analyze_bus_factor
from repopulse.coupling import analyze_coupling
from repopulse.engine import RepoPulseEngine
from repopulse.formatter import format_json, format_markdown, format_text
from repopulse.hotspots import analyze_hotspots
from repopulse.miner import GitMiner
from repopulse.models import FileBusFactor, Hotspot, RepoHealthReport, TemporalCoupling
from repopulse.scorer import compute_health_score

__all__ = [
    "FileBusFactor",
    "GitMiner",
    "Hotspot",
    "RepoHealthReport",
    "RepoPulseEngine",
    "TemporalCoupling",
    "__author__",
    "__version__",
    "analyze_bus_factor",
    "analyze_coupling",
    "analyze_hotspots",
    "compute_health_score",
    "format_json",
    "format_markdown",
    "format_text",
]
