"""Locate and load raw Shopify CSV exports from the input folder."""
from __future__ import annotations

import glob
import os
from pathlib import Path

import pandas as pd

# Signature columns used to auto-detect which Shopify export a CSV is.
SIGNATURES = {
    "products": {"Handle", "Title", "Variant Price"},
    "orders": {"Name", "Financial Status", "Lineitem name"},
    "transactions": {"Transaction ID", "Kind", "Amount"},
    "payouts": {"Payout Date", "Type", "Amount"},
}


def _read_csv(path: str) -> pd.DataFrame:
    # Shopify exports are UTF-8 with a comma delimiter; keep everything as string
    # so we control parsing ourselves.
    return pd.read_csv(path, dtype=str, keep_default_na=False, encoding="utf-8-sig")


def detect_kind(df: pd.DataFrame) -> str | None:
    cols = set(df.columns)
    best, best_score = None, 0
    for kind, sig in SIGNATURES.items():
        score = len(sig & cols)
        if score == len(sig) and score > best_score:
            best, best_score = kind, score
    return best


def find_inputs(input_dir: str, patterns: dict[str, str]) -> dict[str, pd.DataFrame]:
    """Return {kind: dataframe} for every recognised export in input_dir.

    Files are matched first by the configured glob pattern, then any remaining
    *.csv files are auto-detected by their columns.
    """
    input_path = Path(input_dir)
    found: dict[str, pd.DataFrame] = {}
    used: set[str] = set()

    # 1) pattern-based matching
    for kind, pattern in patterns.items():
        for match in sorted(glob.glob(str(input_path / pattern))):
            if match in used:
                continue
            df = _read_csv(match)
            found[kind] = df
            used.add(match)
            break  # one file per kind

    # 2) auto-detect anything left over
    for match in sorted(glob.glob(str(input_path / "*.csv"))):
        if match in used:
            continue
        df = _read_csv(match)
        kind = detect_kind(df)
        if kind and kind not in found:
            found[kind] = df
            used.add(match)

    return found
