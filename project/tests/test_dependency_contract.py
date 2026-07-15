"""Dependency contract smoke tests for the canonical Python environment."""
from __future__ import annotations

import platform
import sys
from importlib.metadata import version
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src import stage124_gate_b_readiness as readiness  # noqa: E402

REQUIREMENTS_PATH = ROOT / "requirements.txt"
ENVIRONMENT_PATH = ROOT / "environment.yml"
EXPECTED_PYTHON = "3.13.5"
EXPECTED_JDATETIME = "6.0.1"


def test_requirements_txt_pins_jdatetime():
    text = REQUIREMENTS_PATH.read_text(encoding="utf-8")
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    assert lines.count("jdatetime==6.0.1") == 1


def test_environment_yml_pins_python_exactly():
    text = ENVIRONMENT_PATH.read_text(encoding="utf-8")
    assert "python=3.13.5" in text
    assert "python=3.13\n" not in text
    assert "python=3.13 " not in text


def test_environment_yml_resolves_requirements_reference():
    text = ENVIRONMENT_PATH.read_text(encoding="utf-8")
    assert "-r requirements.txt" in text
    resolved = (ENVIRONMENT_PATH.parent / "requirements.txt").resolve()
    assert resolved.is_file()
    assert resolved == REQUIREMENTS_PATH.resolve()


def test_runtime_python_version_matches_contract():
    assert platform.python_version() == EXPECTED_PYTHON


def test_installed_jdatetime_version_matches_pin():
    assert version("jdatetime") == EXPECTED_JDATETIME


def test_jdatetime_importable():
    import jdatetime

    assert jdatetime.date(1400, 1, 1).year == 1400


def test_stage124_readiness_reports_jdatetime_available():
    assert readiness.HAS_JDATETIME is True
