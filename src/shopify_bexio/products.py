"""Transform Shopify products_export.csv -> Bexio item import CSV.

Shopify lists one row per variant; the parent row carries the Title/Body and
each following row (same Handle, blank Title) is another variant. We emit one
Bexio item per variant, falling back to the product itself when it has no
distinct variants.
"""
from __future__ import annotations

import pandas as pd

from . import utils


def _col(row: pd.Series, name: str) -> str:
    return str(row.get(name, "") or "").strip()


def transform_products(df: pd.DataFrame, cfg: dict) -> pd.DataFrame:
    dec = cfg["formatting"]["decimal_separator"]

    rows: list[dict] = []
    current_title = ""
    current_body = ""
    current_vendor = ""

    for _, row in df.iterrows():
        handle = _col(row, "Handle")
        title = _col(row, "Title")
        if title:
            current_title = title
            current_body = utils.strip_html(row.get("Body (HTML)", ""))
            current_vendor = _col(row, "Vendor")

        sku = _col(row, "Variant SKU")
        price = _col(row, "Variant Price")
        # Skip pure image rows (no variant info at all).
        if not sku and not price and not title:
            continue

        # Build a name that distinguishes variants (e.g. "T-Shirt - Red / L").
        option_bits = []
        for opt_name, opt_val in (
            ("Option1 Name", "Option1 Value"),
            ("Option2 Name", "Option2 Value"),
            ("Option3 Name", "Option3 Value"),
        ):
            val = _col(row, opt_val)
            if val and val.lower() != "default title":
                option_bits.append(val)
        name = current_title
        if option_bits:
            name = f"{current_title} - {' / '.join(option_bits)}"

        code = sku or (f"{handle}-{'-'.join(option_bits)}" if option_bits else handle)

        sale_price = utils.parse_number(price)
        cost = utils.parse_number(row.get("Cost per item", ""))

        rows.append(
            {
                "intern_code": code,
                "intern_name": name,
                "description": current_body,
                "sale_price": utils.format_number(sale_price, dec),
                "purchase_price": utils.format_number(cost, dec) if cost else "",
                "vendor": current_vendor,
                "barcode": _col(row, "Variant Barcode"),
                "income_account": cfg["accounting"]["income_account"],
                "vat_code": cfg["accounting"]["vat_code_standard"]
                if _col(row, "Variant Taxable").lower() != "false"
                else cfg["accounting"]["vat_code_exempt"],
            }
        )

    out = pd.DataFrame(rows)
    # Drop exact duplicate codes (same variant appearing twice) keeping first.
    if not out.empty:
        out = out.drop_duplicates(subset=["intern_code"], keep="first").reset_index(
            drop=True
        )
    return out
