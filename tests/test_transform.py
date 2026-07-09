"""Smoke + correctness tests using the bundled sample exports."""
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from shopify_bexio.config import load_config  # noqa: E402
from shopify_bexio.orders import transform_orders  # noqa: E402
from shopify_bexio.payments import transform_payments  # noqa: E402
from shopify_bexio.products import transform_products  # noqa: E402

SAMPLES = ROOT / "samples"


def _read(name):
    return pd.read_csv(SAMPLES / name, dtype=str, keep_default_na=False)


def test_products():
    cfg = load_config()
    out = transform_products(_read("products_export.csv"), cfg)
    codes = set(out["intern_code"])
    # 3 tee variants + 1 sticker = 4 items; image-only row ignored.
    assert len(out) == 4
    assert {"TEE-RED-S", "TEE-RED-M", "TEE-BLU-S", "STK-PACK"} == codes
    red_s = out[out["intern_code"] == "TEE-RED-S"].iloc[0]
    assert red_s["intern_name"] == "Classic Tee - Red / S"
    assert red_s["sale_price"] == "29.90"
    assert red_s["purchase_price"] == "12.50"
    # sticker is non-taxable -> exempt VAT code
    stk = out[out["intern_code"] == "STK-PACK"].iloc[0]
    assert stk["vat_code"] == cfg["accounting"]["vat_code_exempt"]


def test_orders_invoices():
    cfg = load_config()
    out = transform_orders(_read("orders_export.csv"), cfg)
    # 3 orders
    assert out["order_ref"].nunique() == 3
    o1 = out[out["order_ref"] == "#1001"]
    # 2 line items + 1 shipping position = 3 rows
    assert len(o1) == 3
    parent = o1.iloc[0]
    assert parent["contact_type"] == "2"  # person
    assert parent["name_1"] == "Anna"
    assert parent["city"] == "Zürich"
    assert parent["invoice_date"] == "14.03.2026"
    # child rows have empty contact cells
    child = o1.iloc[1]
    assert child["name_1"] == ""
    assert child["invoice_date"] == ""
    # company order -> contact_type 1
    o2 = out[out["order_ref"] == "#1002"].iloc[0]
    assert o2["contact_type"] == "1"
    assert o2["name_1"] == "Beispiel GmbH"
    assert o2["country"] == "Germany"


def test_payments_from_transactions():
    cfg = load_config()
    tx = _read("transactions_export.csv")
    out = transform_payments(tx, None, cfg)
    # 3 sales + 1 refund
    assert len(out) == 4
    refund = out[out["order_ref"] == "#1003"]
    amounts = sorted(float(a) for a in refund["amount"])
    assert amounts == [-6.0, 6.0]


if __name__ == "__main__":
    test_products()
    test_orders_invoices()
    test_payments_from_transactions()
    print("All tests passed.")
