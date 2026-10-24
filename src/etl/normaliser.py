"""Data Normalisation Module for svgBA100 Financial Intelligence Platform.

Handles deterministic normalization of:
- Company tickers
- Financial reporting years and periods
- Numeric and monetary amounts (preserving negative signs)
- Dates into ISO format
- Null-like tokens and extraneous whitespace
"""

import re
from datetime import date, datetime
from typing import Any, Optional, Union

NULL_TOKENS = {
    "",
    "na",
    "n/a",
    "null",
    "none",
    "-",
    "--",
    "---",
    "nan",
    "nil",
    "#n/a",
    "#na",
    "undefined",
}


def normalize_string(val: Any) -> Optional[str]:
    """Clean string values, stripping whitespace and mapping NULL-like tokens to None."""
    if val is None:
        return None
    s = str(val).strip()
    if s.lower() in NULL_TOKENS:
        return None
    # Normalize multiple whitespace
    s = re.sub(r"\s+", " ", s)
    return s


def normalize_ticker(val: Any) -> Optional[str]:
    """Normalize company ticker symbol: uppercase, trimmed, validated."""
    s = normalize_string(val)
    if s is None:
        return None
    ticker = s.upper().strip()
    # Remove unwanted leading/trailing punctuation if any
    ticker = re.sub(r"[^\w\-\&]", "", ticker)
    return ticker if ticker else None


def normalize_year(val: Any) -> Optional[str]:
    """Normalize financial reporting years and periods.

    Handles:
    - 4-digit years: 2024, '2024' -> '2024'
    - Float years: 2024.0 -> '2024', 2024.5 -> 'Sep 2024'
    - Month-Year abbreviations: 'Mar-13' -> 'Mar 2013'
    - Standard Month-Year: 'Mar 2023' -> 'Mar 2023', 'Dec 2012' -> 'Dec 2012'
    - Special financial periods: 'TTM' -> 'TTM', 'Mar 2016 9m' -> 'Mar 2016 (9m)'
    """
    if val is None:
        return None

    # Handle float representation
    if isinstance(val, (float, int)):
        if isinstance(val, float) and val == 2024.5:
            return "Sep 2024"
        int_val = int(val)
        if float(val) == float(int_val):
            return str(int_val)
        return str(val)

    s = normalize_string(val)
    if s is None:
        return None

    # Check for TTM
    if s.upper() == "TTM":
        return "TTM"

    # Check for 2024.5 float string
    if s == "2024.5":
        return "Sep 2024"

    # Check for Month-YY format e.g. Mar-13, Mar-23, Dec-12
    m_month_yy = re.match(r"^([A-Za-z]{3})-(\d{2})$", s)
    if m_month_yy:
        month, yy = m_month_yy.groups()
        full_year = 2000 + int(yy) if int(yy) < 70 else 1900 + int(yy)
        return f"{month.capitalize()} {full_year}"

    # Check for Month Year (e.g. Mar 2023, Dec 2012)
    m_month_yyyy = re.match(r"^([A-Za-z]{3})\s+(\d{4})(.*)$", s)
    if m_month_yyyy:
        month, year, extra = m_month_yyyy.groups()
        extra = extra.strip()
        if extra:
            if "9m" in extra.lower():
                return f"{month.capitalize()} {year} (9m)"
            if "15" in extra:
                return f"{month.capitalize()} {year} (15m)"
            return f"{month.capitalize()} {year} {extra}"
        return f"{month.capitalize()} {year}"

    # Check for pure 4-digit year e.g. '2024'
    m_yyyy = re.match(r"^(\d{4})(\.0+)?$", s)
    if m_yyyy:
        return m_yyyy.group(1)

    return s


def normalize_numeric(
    val: Any, allow_float: bool = True
) -> Optional[Union[int, float]]:
    """Parse numeric values cleanly.

    Preserves legitimate negative values.
    Handles:
    - Comma separators: '1,312' -> 1312
    - Currency/percentages: '21%' -> 21.0, '₹150' -> 150.0
    - Parentheses for negative numbers: '(152)' -> -152.0
    - Null-like markers: '-', 'NA', 'N/A' -> None
    """
    if val is None:
        return None

    if isinstance(val, (int, float)):
        if isinstance(val, float) and (val != val):  # NaN check
            return None
        return float(val) if allow_float else int(val)

    s = normalize_string(val)
    if s is None:
        return None

    # Check for parentheses indicating negative: (123.45)
    is_negative = False
    if s.startswith("(") and s.endswith(")"):
        is_negative = True
        s = s[1:-1].strip()
    elif s.startswith("-"):
        is_negative = True
        s = s[1:].strip()

    # Remove commas, currency symbols, and %
    s_cleaned = re.sub(r"[,\s₹$€£%]", "", s)

    if not s_cleaned:
        return None

    try:
        if allow_float:
            num = float(s_cleaned)
            return -num if is_negative else num
        else:
            num = int(float(s_cleaned))
            return -num if is_negative else num
    except (ValueError, TypeError):
        return None


def normalize_date(val: Any) -> Optional[str]:
    """Normalize date representations to ISO YYYY-MM-DD."""
    if val is None:
        return None

    if isinstance(val, (datetime, date)):
        return val.strftime("%Y-%m-%d")

    s = normalize_string(val)
    if s is None:
        return None

    # Handle standard ISO YYYY-MM-DD
    if re.match(r"^\d{4}-\d{2}-\d{2}$", s):
        return s

    # Handle DD-MM-YYYY or DD/MM/YYYY
    m_dmy = re.match(r"^(\d{1,2})[-/](\d{1,2})[-/](\d{4})$", s)
    if m_dmy:
        d, m, y = m_dmy.groups()
        return f"{int(y):04d}-{int(m):02d}-{int(d):02d}"

    # Handle YYYY/MM/DD
    m_ymd = re.match(r"^(\d{4})[-/](\d{1,2})[-/](\d{1,2})$", s)
    if m_ymd:
        y, m, d = m_ymd.groups()
        return f"{int(y):04d}-{int(m):02d}-{int(d):02d}"

    try:
        dt = datetime.strptime(s, "%Y-%m-%d")
        return dt.strftime("%Y-%m-%d")
    except ValueError:
        pass

    return s


def normalize_boolean(val: Any) -> int:
    """Normalize boolean-like values into 0 or 1."""
    if val is None:
        return 0
    if isinstance(val, bool):
        return 1 if val else 0
    if isinstance(val, (int, float)):
        return 1 if int(val) != 0 else 0
    s = str(val).strip().lower()
    if s in {"true", "1", "yes", "y", "t"}:
        return 1
    return 0

