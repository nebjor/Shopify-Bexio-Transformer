"""Shared helpers: number/date parsing, HTML stripping, country names."""
from __future__ import annotations

import re
from datetime import datetime

# Minimal ISO country-code -> English name map for the countries a Swiss shop
# most commonly ships to. Shopify order exports may contain either the full
# country name ("Switzerland") or the 2-letter code ("CH"); Bexio wants the
# full name. Extend as needed.
COUNTRY_NAMES = {
    "CH": "Switzerland",
    "LI": "Liechtenstein",
    "DE": "Germany",
    "AT": "Austria",
    "FR": "France",
    "IT": "Italy",
    "US": "United States",
    "GB": "United Kingdom",
    "NL": "Netherlands",
    "BE": "Belgium",
    "ES": "Spain",
    "PT": "Portugal",
    "SE": "Sweden",
    "DK": "Denmark",
    "NO": "Norway",
    "FI": "Finland",
    "PL": "Poland",
    "CZ": "Czechia",
    "LU": "Luxembourg",
    "IE": "Ireland",
    "CA": "Canada",
    "AU": "Australia",
}

_HTML_TAG = re.compile(r"<[^>]+>")
_WS = re.compile(r"[ \t]*\n[ \t]*")


def strip_html(value) -> str:
    """Turn Shopify Body (HTML) into plain, single-spaced text."""
    if value is None:
        return ""
    text = str(value)
    text = re.sub(r"<\s*br\s*/?>", "\n", text, flags=re.I)
    text = re.sub(r"</\s*p\s*>", "\n", text, flags=re.I)
    text = _HTML_TAG.sub("", text)
    text = (
        text.replace("&amp;", "&")
        .replace("&lt;", "<")
        .replace("&gt;", ">")
        .replace("&nbsp;", " ")
        .replace("&#39;", "'")
        .replace("&quot;", '"')
    )
    text = _WS.sub("\n", text).strip()
    return text


def country_name(value) -> str:
    """Normalise a Shopify country value to a full country name for Bexio."""
    if value is None:
        return ""
    v = str(value).strip()
    if not v:
        return ""
    if len(v) == 2 and v.upper() in COUNTRY_NAMES:
        return COUNTRY_NAMES[v.upper()]
    return v  # already a full name


def parse_number(value) -> float:
    """Parse a monetary/quantity value that may use ',' or '.' as decimals."""
    if value is None:
        return 0.0
    if isinstance(value, (int, float)):
        try:
            import math

            if isinstance(value, float) and math.isnan(value):
                return 0.0
        except Exception:
            pass
        return float(value)
    s = str(value).strip()
    if not s:
        return 0.0
    s = s.replace("'", "").replace(" ", "")
    # If both separators present, assume '.' thousands + ',' decimal (EU) OR
    # ',' thousands + '.' decimal (US). Decide by the LAST separator.
    if "," in s and "." in s:
        if s.rfind(",") > s.rfind("."):
            s = s.replace(".", "").replace(",", ".")
        else:
            s = s.replace(",", "")
    elif "," in s:
        s = s.replace(",", ".")
    try:
        return float(s)
    except ValueError:
        return 0.0


_DATE_INPUT_FORMATS = (
    "%Y-%m-%d %H:%M:%S %z",
    "%Y-%m-%d %H:%M:%S",
    "%Y-%m-%dT%H:%M:%S%z",
    "%Y-%m-%d",
    "%d.%m.%Y",
    "%m/%d/%Y",
)


def parse_date(value):
    """Parse a Shopify date string into a datetime (or None)."""
    if value is None:
        return None
    s = str(value).strip()
    if not s or s.lower() in {"nan", "nat"}:
        return None
    # Shopify uses e.g. "2026-03-14 09:12:33 +0100"; normalise the tz colon.
    for fmt in _DATE_INPUT_FORMATS:
        try:
            return datetime.strptime(s, fmt)
        except ValueError:
            continue
    # last resort: take the leading YYYY-MM-DD
    m = re.match(r"(\d{4})-(\d{2})-(\d{2})", s)
    if m:
        return datetime(int(m.group(1)), int(m.group(2)), int(m.group(3)))
    return None


def format_date(value, date_format: str) -> str:
    dt = parse_date(value)
    return dt.strftime(date_format) if dt else ""


def format_number(value: float, decimal_separator: str) -> str:
    s = f"{float(value):.2f}"
    if decimal_separator != ".":
        s = s.replace(".", decimal_separator)
    return s
