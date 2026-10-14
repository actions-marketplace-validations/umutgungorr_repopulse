"""Backwards-compatible alias for repopulse.busfactor."""

from __future__ import annotations

from repopulse.busfactor import analyze_bus_factor, summarize_bus_factor

__all__ = ["analyze_bus_factor", "summarize_bus_factor"]
