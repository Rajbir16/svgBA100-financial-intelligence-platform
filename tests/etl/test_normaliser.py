"""Unit tests for src/etl/normaliser.py.

Tests ticker, year, numeric, date, and boolean normalisation.
"""

from datetime import date, datetime

import pytest

from src.etl.normaliser import (
    normalize_boolean,
    normalize_date,
    normalize_numeric,
    normalize_string,
    normalize_ticker,
    normalize_year,
)


class TestNormaliser:
    # --- Ticker Tests ---
    def test_normalize_ticker_basic(self):
        assert normalize_ticker("tcs") == "TCS"
        assert normalize_ticker("HDFCBANK") == "HDFCBANK"

    def test_normalize_ticker_whitespace_and_casing(self):
        assert normalize_ticker("  infy  ") == "INFY"
        assert normalize_ticker("\tReliance \n") == "RELIANCE"

    def test_normalize_ticker_special_chars(self):
        assert normalize_ticker("M&M") == "M&M"
        assert normalize_ticker("BAJAJ-AUTO") == "BAJAJ-AUTO"

    def test_normalize_ticker_null_and_empty(self):
        assert normalize_ticker(None) is None
        assert normalize_ticker("") is None
        assert normalize_ticker("   ") is None
        assert normalize_ticker("N/A") is None
        assert normalize_ticker("-") is None

    # --- Year Tests ---
    def test_normalize_year_four_digit(self):
        assert normalize_year("2024") == "2024"
        assert normalize_year(2023) == "2023"

    def test_normalize_year_float(self):
        assert normalize_year(2024.0) == "2024"
        assert normalize_year("2023.0") == "2023"

    def test_normalize_year_half_year(self):
        assert normalize_year(2024.5) == "Sep 2024"
        assert normalize_year("2024.5") == "Sep 2024"

    def test_normalize_year_month_abbreviation(self):
        assert normalize_year("Mar-13") == "Mar 2013"
        assert normalize_year("Dec-22") == "Dec 2022"

    def test_normalize_year_month_full(self):
        assert normalize_year("Mar 2023") == "Mar 2023"
        assert normalize_year("Dec 2012") == "Dec 2012"

    def test_normalize_year_special_periods(self):
        assert normalize_year("TTM") == "TTM"
        assert normalize_year("ttm") == "TTM"
        assert normalize_year("Mar 2016 9m") == "Mar 2016 (9m)"
        assert normalize_year("Mar 2023 15") == "Mar 2023 (15m)"

    def test_normalize_year_null_and_empty(self):
        assert normalize_year(None) is None
        assert normalize_year("") is None
        assert normalize_year("  ") is None
        assert normalize_year("NA") is None

    # --- Numeric Tests ---
    def test_normalize_numeric_integers(self):
        assert normalize_numeric(100) == 100.0
        assert normalize_numeric("250", allow_float=False) == 250

    def test_normalize_numeric_commas(self):
        assert normalize_numeric("1,312") == 1312.0
        assert normalize_numeric("24,09,821") == 2409821.0

    def test_normalize_numeric_negative_parentheses(self):
        # Legitimate negative financial value in accounting style: (152) -> -152.0
        assert normalize_numeric("(152)") == -152.0
        assert normalize_numeric("(3,450.50)") == -3450.50

    def test_normalize_numeric_negative_sign(self):
        assert normalize_numeric("-6038") == -6038.0
        assert normalize_numeric("- 1807") == -1807.0

    def test_normalize_numeric_percentages(self):
        assert normalize_numeric("21%") == 21.0
        assert normalize_numeric("12.5%") == 12.5

    def test_normalize_numeric_null_markers(self):
        assert normalize_numeric("-") is None
        assert normalize_numeric("NA") is None
        assert normalize_numeric("N/A") is None
        assert normalize_numeric("null") is None
        assert normalize_numeric("") is None
        assert normalize_numeric(None) is None

    # --- Date Tests ---
    def test_normalize_date_iso(self):
        assert normalize_date("2020-01-01") == "2020-01-01"
        assert normalize_date(date(2023, 5, 12)) == "2023-05-12"
        assert normalize_date(datetime(2023, 5, 12, 10, 30)) == "2023-05-12"

    def test_normalize_date_slashes_and_dashes(self):
        assert normalize_date("01/05/2022") == "2022-05-01"
        assert normalize_date("2022/05/01") == "2022-05-01"

    def test_normalize_date_null_and_empty(self):
        assert normalize_date(None) is None
        assert normalize_date("") is None

    # --- Boolean Tests ---
    def test_normalize_boolean(self):
        assert normalize_boolean(True) == 1
        assert normalize_boolean("True") == 1
        assert normalize_boolean("1") == 1
        assert normalize_boolean(1) == 1
        assert normalize_boolean(False) == 0
        assert normalize_boolean("false") == 0
        assert normalize_boolean(0) == 0
        assert normalize_boolean(None) == 0

    # --- String Tests ---
    def test_normalize_string_null_tokens(self):
        assert normalize_string("  Hello World  ") == "Hello World"
        assert normalize_string("Multiple   spaces") == "Multiple spaces"
        assert normalize_string("NA") is None
        assert normalize_string("N/A") is None
        assert normalize_string("null") is None
        assert normalize_string("-") is None
        assert normalize_string("") is None

