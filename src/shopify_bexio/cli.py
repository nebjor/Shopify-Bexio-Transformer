"""Command-line entry point: read Shopify exports, write Bexio CSVs."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

from .config import load_config
from .orders import transform_orders
from .payments import transform_payments
from .products import transform_products
from .readers import find_inputs


def _write(df: pd.DataFrame, out_dir: Path, filename: str, delimiter: str) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / filename
    df.to_csv(path, index=False, sep=delimiter, encoding="utf-8-sig")
    return path


def run(config_path: str | None = None) -> int:
    cfg = load_config(config_path)
    root = Path(__file__).resolve().parents[2]
    input_dir = (root / cfg["input_dir"]).resolve()
    output_dir = (root / cfg["output_dir"]).resolve()
    delimiter = cfg["formatting"]["output_delimiter"]

    if not input_dir.exists():
        print(f"! Input folder not found: {input_dir}")
        print("  Create it and drop your Shopify CSV exports there.")
        return 1

    inputs = find_inputs(str(input_dir), cfg["files"])
    if not inputs:
        print(f"! No recognised Shopify exports in {input_dir}")
        print("  Expected products / orders / transactions / payouts CSVs.")
        return 1

    print(f"Reading from : {input_dir}")
    print(f"Writing to   : {output_dir}\n")
    print("Detected exports: " + ", ".join(sorted(inputs.keys())) + "\n")

    summary: list[tuple[str, int, str]] = []

    if "products" in inputs:
        out = transform_products(inputs["products"], cfg)
        path = _write(out, output_dir, "bexio_products.csv", delimiter)
        summary.append(("Products (items)", len(out), path.name))

    if "orders" in inputs:
        out = transform_orders(inputs["orders"], cfg)
        path = _write(out, output_dir, "bexio_invoices.csv", delimiter)
        n_invoices = out["order_ref"].nunique() if not out.empty else 0
        summary.append((f"Invoices ({n_invoices}) / positions", len(out), path.name))

    payments = transform_payments(
        inputs.get("transactions"), inputs.get("orders"), cfg
    )
    if not payments.empty:
        path = _write(payments, output_dir, "bexio_payments.csv", delimiter)
        summary.append(("Payments", len(payments), path.name))

    print("Done. Output:")
    for label, n, fname in summary:
        print(f"  - {label:<28} {n:>6} rows  ->  {fname}")
    print("\nNext: review the CSVs, confirm account/VAT codes in config.yaml,")
    print("then import each file in Bexio (Items, Invoices, Bank transactions).")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Transform Shopify CSV exports into Bexio import files."
    )
    parser.add_argument(
        "-c", "--config", default=None, help="Path to config.yaml (optional)."
    )
    args = parser.parse_args(argv)
    return run(args.config)


if __name__ == "__main__":
    sys.exit(main())
