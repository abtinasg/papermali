"""Pytest hooks shared across project tests."""
from __future__ import annotations

from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
VERIFIED_MASTER = ROOT / "stage124" / "listing_master_verified_stage124.csv"

HANDOFF_VALIDATION_MODULE = "test_ai_handoff"


@pytest.fixture(scope="module", autouse=True)
def isolate_stage124_verified_master_for_historical_guardrails(request):
    """Hide the verified master artifact during tests that enforce Gate-A guardrails."""
    module_name = request.module.__name__.rsplit(".", 1)[-1]
    if module_name == HANDOFF_VALIDATION_MODULE:
        yield
        return

    backup = VERIFIED_MASTER.read_bytes() if VERIFIED_MASTER.is_file() else None
    if VERIFIED_MASTER.is_file():
        VERIFIED_MASTER.unlink()
    yield
    if backup is not None:
        VERIFIED_MASTER.write_bytes(backup)
