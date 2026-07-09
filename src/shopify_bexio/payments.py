"""Build a Bexio-ready payments CSV.

Two sources are supported (whichever you exported):

  * transactions_export.csv  (Orders > Export transaction histories) -> preferred,
    because it has one row per real payment/refund with gateway + amount.
  * orders_export.csv        -> fallback, using the order-level Total / Paid at /
    Financial Status when no transaction export is present.

The output is a flat statement suitable for Bexio bank-transaction import:
single currency assumed per file; refunds come through as negative amounts.
"""
from __future__ import annotations

import pandas as pd

from . import utils

COLUMNS = ["date", "amount", "currency", "description", "reference", "gateway", "order_ref"]


def _col(row: pd.Series, name: str) -> str:
    return str(row.get(name, "") or "").strip()


def from_transactions(df: pd.DataFrame, cfg: dict) -> pd.DataFrame:
    dec = cfg["formatting"]["decimal_separator"]
    date_fmt = cfg["formatting"]["date_format"]
    rows: list[dict] = []

    for _, row in df.iterrows():
        kind = _col(row, "Kind").lower()          # sale / capture / refund / void ...
        status = _col(row, "Status").lower()
        if status and status not in {"success", "captured", "paid", ""}:
            continue
        amount = utils.parse_number(row.get("Amount", ""))
        if amount == 0:
            continue
        # Refunds / returns reduce the bank balance.
        if kind in {"refund", "return"}:
            amount = -abs(amount)
        order_ref = _col(row, "Order") or _col(row, "Name")
        rows.append(
            {
                "date": utils.format_date(row.get("Processed at", ""), date_fmt),
                "amount": utils.format_number(amount, dec),
                "currency": _col(row, "Currency"),
                "description": f"Shopify {kind or 'payment'} {order_ref}".strip(),
                "reference": order_ref,
                "gateway": _col(row, "Gateway"),
                "order_ref": order_ref,
            }
        )
    return pd.DataFrame(rows, columns=COLUMNS)


def from_orders(df: pd.DataFrame, cfg: dict) -> pd.DataFrame:
    dec = cfg["formatting"]["decimal_separator"]
    date_fmt = cfg["formatting"]["date_format"]
    rows: list[dict] = []

    for name, group in df.groupby("Name", sort=False):
        header = group.iloc[0]
        fin = _col(header, "Financial Status").lower()
        if fin not in {"paid", "partially_refunded", "partially_paid"}:
            continue
        total = utils.parse_number(header.get("Total", ""))
        if total == 0:
            continue
        paid_at = header.get("Paid at", "") or header.get("Created at", "")
        rows.append(
            {
                "date": utils.format_date(paid_at, date_fmt),
                "amount": utils.format_number(total, dec),
                "currency": _col(header, "Currency"),
                "description": f"Shopify order {name}",
                "reference": _col(header, "Payment Reference") or name,
                "gateway": _col(header, "Payment Method"),
                "order_ref": name,
            }
        )
    return pd.DataFrame(rows, columns=COLUMNS)


def transform_payments(
    transactions: pd.DataFrame | None, orders: pd.DataFrame | None, cfg: dict
) -> pd.DataFrame:
    if transactions is not None and not transactions.empty:
        return from_transactions(transactions, cfg)
    if orders is not None and not orders.empty:
        return from_orders(orders, cfg)
    return pd.DataFrame(columns=COLUMNS)
