"""Transform Shopify orders_export.csv -> Bexio invoice import CSV.

Shopify puts one row per line item; only the FIRST row of an order carries the
order-level fields (customer, totals, dates). We group by order Name, forward
-fill those fields, then emit a Bexio "parent + positions" layout:

  * the parent row holds the contact + invoice date + the first position
  * each additional position is a child row where the contact/date cells are
    left blank (this is how Bexio/most importers attach positions to an invoice)
"""
from __future__ import annotations

import pandas as pd

from . import utils

# Output column order (parent-level fields first, then position fields).
COLUMNS = [
    "order_ref",
    "contact_type",
    "name_1",
    "name_2",
    "address",
    "postal_code",
    "city",
    "country",
    "email",
    "invoice_date",
    "position_description",
    "unit_price",
    "quantity",
    "account",
    "vat_code",
]

POSITION_ONLY = {
    "position_description",
    "unit_price",
    "quantity",
    "account",
    "vat_code",
    "order_ref",
}


def _col(row: pd.Series, name: str) -> str:
    return str(row.get(name, "") or "").strip()


def _contact_from_header(header: pd.Series, cfg: dict) -> dict:
    company = _col(header, "Billing Company")
    billing_name = _col(header, "Billing Name")
    use_company = bool(company) and cfg["options"]["company_when_billing_company"]

    if use_company:
        contact_type = "1"  # company
        name_1 = company
        name_2 = billing_name  # keep the person as Name_2
    else:
        contact_type = "2"  # person
        parts = billing_name.split(" ", 1) if billing_name else ["", ""]
        name_1 = parts[0]
        name_2 = parts[1] if len(parts) > 1 else ""

    address = _col(header, "Billing Address1")
    addr2 = _col(header, "Billing Address2")
    if addr2:
        address = f"{address} {addr2}".strip()

    return {
        "contact_type": contact_type,
        "name_1": name_1,
        "name_2": name_2,
        "address": address,
        "postal_code": _col(header, "Billing Zip"),
        "city": _col(header, "Billing City"),
        "country": utils.country_name(_col(header, "Billing Country")),
        "email": _col(header, "Email"),
    }


def transform_orders(df: pd.DataFrame, cfg: dict) -> pd.DataFrame:
    dec = cfg["formatting"]["decimal_separator"]
    date_fmt = cfg["formatting"]["date_format"]
    acct = cfg["accounting"]
    status_filter = {
        s.lower() for s in cfg["options"].get("order_financial_status_filter", []) or []
    }

    out_rows: list[dict] = []

    # Preserve order; group consecutive rows by order Name.
    for name, group in df.groupby("Name", sort=False):
        header = group.iloc[0]

        if status_filter:
            fin = _col(header, "Financial Status").lower()
            if fin not in status_filter:
                continue

        contact = _contact_from_header(header, cfg)
        invoice_date = utils.format_date(header.get("Created at", ""), date_fmt)

        positions: list[dict] = []
        for _, line in group.iterrows():
            li_name = _col(line, "Lineitem name")
            if not li_name:
                continue
            qty = utils.parse_number(line.get("Lineitem quantity", "")) or 1
            price = utils.parse_number(line.get("Lineitem price", ""))
            taxable = _col(line, "Lineitem taxable").lower() != "false"
            positions.append(
                {
                    "position_description": li_name,
                    "unit_price": utils.format_number(price, dec),
                    "quantity": utils.format_number(qty, dec).rstrip("0").rstrip(".")
                    if dec == "."
                    else utils.format_number(qty, dec),
                    "account": acct["income_account"],
                    "vat_code": acct["vat_code_standard"]
                    if taxable
                    else acct["vat_code_exempt"],
                }
            )

        # Optional: shipping as its own position.
        shipping = utils.parse_number(header.get("Shipping", ""))
        if cfg["options"]["shipping_as_position"] and shipping > 0:
            positions.append(
                {
                    "position_description": _col(header, "Shipping Method") or "Shipping",
                    "unit_price": utils.format_number(shipping, dec),
                    "quantity": "1",
                    "account": acct["shipping_account"],
                    "vat_code": acct["vat_code_standard"],
                }
            )

        if not positions:
            continue

        # Emit parent (first position) + child rows (positions only).
        for idx, pos in enumerate(positions):
            record = {c: "" for c in COLUMNS}
            record["order_ref"] = name
            if idx == 0:
                record.update(contact)
                record["invoice_date"] = invoice_date
            record.update(pos)
            out_rows.append(record)

    return pd.DataFrame(out_rows, columns=COLUMNS)
