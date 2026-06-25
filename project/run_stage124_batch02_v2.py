#!/usr/bin/env python3
"""Runner for Stage124 Batch 2 Gate A V2."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from src.stage124_batch02_v2 import run

if __name__ == "__main__":
    run()
