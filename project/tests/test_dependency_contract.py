"""Dependency contract smoke tests for the canonical Python environment."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src import stage124_gate_b_readiness as readiness  # noqa: E402


def test_jdatetime_importable():
    import jdatetime

    assert jdatetime.date(1400, 1, 1).year == 1400


def test_stage124_readiness_reports_jdatetime_available():
    assert readiness.HAS_JDATETIME is True
