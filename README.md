# Shopify → Bexio Transformer

A small Python command-line tool that converts **Shopify CSV exports** into
**Bexio import CSV files** (products, invoices and payments), so a shop can move
its data into Bexio without a paid third-party app.

> **Status: proof of concept.** This is an offline CSV converter, not a live
> integration. It does not talk to the Shopify or Bexio APIs. You export from
> Shopify, run the script, and import the resulting files in Bexio by hand.

---

## What it does

| Shopify export | → | Bexio output | Import in Bexio under |
|---|---|---|---|
| `products_export.csv` | → | `bexio_products.csv` | Items (products) |
| `orders_export.csv` | → | `bexio_invoices.csv` | Invoices |
| `transactions_export.csv` *(or orders as fallback)* | → | `bexio_payments.csv` | Bank transactions |

- One Bexio **item per Shopify variant** (SKU, name incl. options, price, cost, VAT).
- One Bexio **invoice per order**, with each line item + shipping as positions
  (parent-row / child-row layout).
- One **payment row per transaction**; refunds come through as negative amounts.

---

## Setup (one time)

Requires Python 3.10+.

```bash
git clone https://github.com/nebjor/Shopify-Bexio-Transformer.git
cd Shopify-Bexio-Transformer
pip install -r requirements.txt
cp config.example.yaml config.yaml     # Windows: copy config.example.yaml config.yaml
```

Then open **`config.yaml`** and confirm the accounting values against **your**
Bexio chart of accounts and VAT codes:

- `income_account` / `shipping_account`, e.g. `3200`
- `vat_code_standard`, e.g. `UN81` (8.1 %); `vat_code_exempt`, e.g. `UEX`
- `payment_account`: the bank/clearing account payments land in

Without a `config.yaml` the built-in defaults (the values in
`config.example.yaml`) are used.

## Usage

1. In Shopify, export:
   - **Products** → Export → CSV
   - **Orders** → Export (include line items)
   - **Orders** → *Export transaction histories* (optional, recommended)
2. Drop those CSVs into **`input/`**. Filenames don't matter; each export is
   auto-detected by its columns.
3. Run:
   ```bash
   python run.py                       # or: python run.py -c path/to/config.yaml
   ```
4. Review the files in **`output/`**, then import each one in Bexio.

---

## Try it with sample data

Synthetic exports live in `samples/`:

```bash
python tests/test_transform.py     # prints "All tests passed."
```

Or copy `samples/*.csv` into `input/` and run `python run.py`.

---

## Project layout

```
├─ run.py                 # entry point:  python run.py
├─ config.example.yaml    # copy to config.yaml and edit
├─ input/                 # drop Shopify exports here (git-ignored)
├─ output/                # Bexio CSVs land here (git-ignored)
├─ samples/               # synthetic exports for testing
├─ src/shopify_bexio/
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

## Limitations

- **Manual round trip.** No API sync, no webhooks; every migration is
  export → run → import.
- **VAT codes and account numbers** in the defaults are Swiss-typical
  placeholders. Bexio VAT codes vary per account, so check them.
- **Bexio's invoice import caps at ~200 rows per file.** The tool does not split
  output; split large order sets yourself.
- **Invoice columns are a generic layout.** Depending on the Bexio import
  template, header names may need adjusting. All mapping lives in `orders.py`
  and `config.yaml`.
- Shopify payout exports are not processed.

## Possible next step

Turning this into a real integration would mean a Shopify app / webhook that
creates Bexio contacts, invoices and payments through the Bexio API on each new
order. The field mapping here is reusable for that.

## License

MIT
