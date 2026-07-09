# Shopify → Bexio Transformer (V1)

Turns raw **Shopify CSV exports** into **Bexio import-ready CSV files** — products,
invoices (from orders) and payments — with no third-party app. Written in Python.

This is V1 of the project: export → transform → import by hand. The column
mapping built here is the same logic a future V2 Shopify app would reuse.

---

## What it does

| Shopify export | → | Bexio output | Import in Bexio under |
|---|---|---|---|
| `products_export.csv` | → | `bexio_products.csv` | Items (products) |
| `orders_export.csv` | → | `bexio_invoices.csv` | Invoices |
| `transactions_export.csv` *(or orders as fallback)* | → | `bexio_payments.csv` | Bank transactions |

- One Bexio **item per Shopify variant** (SKU, name incl. options, price, cost, VAT).
- One Bexio **invoice per order**, with each line item + shipping as positions
  (parent-row / child-row layout that Bexio importers expect).
- One **payment row per transaction**; refunds come through as negative amounts.

---

## Setup (one time)

```bash
cd shopify_bexio_transformer
pip install -r requirements.txt
copy config.example.yaml config.yaml     # Windows  (cp on macOS/Linux)
```

Then open **`config.yaml`** and confirm the accounting values against **your**
Bexio chart of accounts and VAT codes — these are the only things you must get
right:

- `income_account` / `shipping_account` – e.g. `3200`
- `vat_code_standard` – e.g. `UN81` (8.1 %); `vat_code_exempt` – e.g. `UEX`
- `payment_account` – the bank/clearing account payments land in

## Each time you want to migrate data

1. In Shopify, export:
   - **Products** → Export → CSV
   - **Orders** → Export → *include transaction/line-item data*
   - **Orders** → *Export transaction histories* (optional but recommended)
   - **Settings → Payments → Payouts → Export** (optional)
2. Drop those CSVs into the **`input/`** folder (filenames don't have to match —
   the tool auto-detects each export by its columns).
3. Run:
   ```bash
   python run.py
   ```
4. Review the files written to **`output/`**, then import each one in Bexio.

Run `python run.py -c path/to/other-config.yaml` to use an alternate config.

---

## Verify it works

Bundled synthetic exports live in `samples/`. To try the whole pipeline:

```bash
python tests/test_transform.py     # runs correctness checks (should print "All tests passed.")
```

Or copy `samples/*.csv` into `input/` and run `python run.py` to see real output.

---

## Project layout

```
shopify_bexio_transformer/
├─ run.py                 # entry point:  python run.py
├─ config.example.yaml    # copy to config.yaml and edit
├─ input/                 # you drop Shopify exports here
├─ output/                # Bexio-ready CSVs land here
├─ samples/               # synthetic exports for testing
├─ src/shopify_bexio/     # the transformer
│  ├─ cli.py              # orchestration
│  ├─ config.py           # config + defaults
│  ├─ readers.py          # find & load Shopify CSVs (auto-detect)
│  ├─ products.py         # products  → Bexio items
│  ├─ orders.py           # orders    → Bexio invoices
│  ├─ payments.py         # transactions/orders → Bexio payments
│  └─ utils.py            # dates, numbers, HTML, country names
└─ tests/test_transform.py
```

---

## Notes & limits

- **Confirm VAT codes and account numbers in `config.yaml`.** The defaults are
  Swiss-typical placeholders, not your account. Bexio VAT codes vary per account.
- Bexio's own invoice import caps at ~200 rows per file; split large order sets.
- The invoice output uses a generic *parent + positions* layout. If you import
  via a specific tool/template, you may need to rename the header columns to
  match it — all mapping is centralised in `orders.py` / `config.yaml`.
- Real store data in `input/` and `output/` is git-ignored by default.
```
