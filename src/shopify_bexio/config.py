"""Configuration loading and defaults."""
from __future__ import annotations

import copy
from pathlib import Path
from typing import Any

import yaml

DEFAULTS: dict[str, Any] = {
    "input_dir": "input",
    "output_dir": "output",
    "files": {
        "products": "products_export*.csv",
        "orders": "orders_export*.csv",
        "transactions": "transactions_export*.csv",
        "payouts": "payouts*.csv",
    },
    "accounting": {
        "income_account": "3200",
        "shipping_account": "3200",
        "vat_code_standard": "UN81",
        "vat_code_exempt": "UEX",
        "payment_account": "1020",
    },
    "formatting": {
        "date_format": "%d.%m.%Y",
        "decimal_separator": ".",
        "output_delimiter": ";",
    },
    "options": {
        "shipping_as_position": True,
        "order_financial_status_filter": [],
        "company_when_billing_company": True,
    },
}


def _deep_merge(base: dict, override: dict) -> dict:
    out = copy.deepcopy(base)
    for key, value in (override or {}).items():
        if isinstance(value, dict) and isinstance(out.get(key), dict):
            out[key] = _deep_merge(out[key], value)
        else:
            out[key] = value
    return out


def load_config(path: str | Path | None = None) -> dict[str, Any]:
    """Load config.yaml (if present) merged over sensible defaults."""
    cfg = copy.deepcopy(DEFAULTS)
    if path is None:
        # look for config.yaml next to the project root
        candidate = Path(__file__).resolve().parents[2] / "config.yaml"
        path = candidate if candidate.exists() else None
    if path and Path(path).exists():
        with open(path, "r", encoding="utf-8") as fh:
            user_cfg = yaml.safe_load(fh) or {}
        cfg = _deep_merge(cfg, user_cfg)
    return cfg
