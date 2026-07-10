#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_DIR))

from src.stage124_official_api_finalize import main  # noqa: E402


if __name__ == "__main__":
    raise SystemExit(main())
