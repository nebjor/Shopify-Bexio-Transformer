#!/usr/bin/env python3
"""Convenience launcher so you can just run `python run.py` from the project root."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from shopify_bexio.cli import main  # noqa: E402

if __name__ == "__main__":
    raise SystemExit(main())
