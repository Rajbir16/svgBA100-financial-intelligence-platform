"""Unit tests for src/etl/validator.py.

Tests all 16 Data Quality rules:
DQ-01 to DQ-16 and reporting logic.
"""

import os
import tempfile

import pytest

from src.etl.validator import DataValidator


class TestValidator:
    def test_dq01_primary_key_validity_numeric(self):
        v = DataValidator()
        assert v.check_pk_validity("balancesheet", 123, is_numeric=True) is True
        assert v.check_pk_validity("balancesheet", None, is_numeric=True) is False
        assert v.check_pk_validity("balancesheet", 0, is_numeric=True) is False
        assert v.check_pk_validity("balancesheet", -5, is_numeric=True) is False
        assert v.check_pk_validity("balancesheet", "invalid", is_numeric=True) is False

        fails = [f for f in v.failures if f.rule_id == "DQ-01"]
        assert len(fails) == 4
        assert all(f.severity == "CRITICAL" for f in fails)

    def test_dq01_primary_key_validity_ticker(self):
        v = DataValidator()
        assert v.check_pk_validity("companies", "TCS", is_numeric=False) is True
        assert v.check_pk_validity("companies", "", is_numeric=False) is False
        assert v.check_pk_validity("companies", None, is_numeric=False) is False

    def test_dq02_primary_key_uniqueness(self):
        v = DataValidator()
        seen = set()
        assert v.check_pk_uniqueness("sectors", 1, seen) is True
        assert v.check_pk_uniqueness("sectors", 2, seen) is True
        assert v.check_pk_uniqueness("sectors", 1, seen) is False

        fails = [f for f in v.failures if f.rule_id == "DQ-02"]
        assert len(fails) == 1
        assert fails[0].severity == "CRITICAL"

    def test_dq03_foreign_key_validity(self):
        v = DataValidator()
        valid_companies = {"TCS", "INFY", "HDFCBANK"}
        assert v.check_fk_validity("balancesheet", "TCS", valid_companies) is True
        assert v.check_fk_validity("balancesheet", "WIPRO", valid_companies) is False

        fails = [f for f in v.failures if f.rule_id == "DQ-03"]
        assert len(fails) == 1
        assert fails[0].severity == "CRITICAL"
        assert fails[0].company_id == "WIPRO"

    def test_dq04_required_company_id(self):
        v = DataValidator()
        assert v.check_required_company_id("profitandloss", "TCS") is True
        assert v.check_required_company_id("profitandloss", None) is False
        assert v.check_required_company_id("profitandloss", "") is False
        assert v.check_required_company_id("profitandloss", "null") is False

        fails = [f for f in v.failures if f.rule_id == "DQ-04"]
        assert len(fails) == 3
        assert all(f.severity == "CRITICAL" for f in fails)

    def test_dq05_valid_year(self):
        v = DataValidator()
        assert v.check_valid_year("profitandloss", "TCS", "2024") is True
        assert v.check_valid_year("profitandloss", "TCS", "Mar 2023") is True
        assert v.check_valid_year("profitandloss", "TCS", "TTM") is True
        assert v.check_valid_year("profitandloss", "TCS", "Dec 2012") is True
        assert v.check_valid_year("profitandloss", "TCS", "Sep 2024") is True
        assert v.check_valid_year("profitandloss", "TCS", "invalid_year_99") is False
        assert v.check_valid_year("profitandloss", "TCS", None) is False

        fails = [f for f in v.failures if f.rule_id == "DQ-05"]
        assert len(fails) == 2
        assert all(f.severity == "WARNING" for f in fails)

    def test_dq06_duplicate_company_year(self):
        v = DataValidator()
        seen = set()
        assert v.check_duplicate_company_year("profitandloss", "TCS", "Mar 2023", seen) is True
        assert v.check_duplicate_company_year("profitandloss", "TCS", "Mar 2024", seen) is True
        assert v.check_duplicate_company_year("profitandloss", "TCS", "Mar 2023", seen) is False

        fails = [f for f in v.failures if f.rule_id == "DQ-06"]
        assert len(fails) == 1
        assert fails[0].severity == "WARNING"

    def test_dq07_numeric_field_validity(self):
        v = DataValidator()
        assert v.check_numeric_validity("balancesheet", "TCS", "2023", "equity_capital", "100", 100.0) is True
        assert v.check_numeric_validity("balancesheet", "TCS", "2023", "equity_capital", "corrupt_text", None) is False

        fails = [f for f in v.failures if f.rule_id == "DQ-07"]
        assert len(fails) == 1
        assert fails[0].severity == "WARNING"

    def test_dq08_impossible_null_critical_values(self):
        v = DataValidator()
        valid_bs = {"total_assets": 1000.0, "total_liabilities": 1000.0}
        invalid_bs = {"total_assets": None, "total_liabilities": 1000.0}
        assert v.check_critical_values("balancesheet", "TCS", "2023", valid_bs) is True
        assert v.check_critical_values("balancesheet", "TCS", "2023", invalid_bs) is False

        valid_sp = {"close_price": 100.0, "open_price": 95.0, "high_price": 105.0, "low_price": 90.0}
        invalid_sp = {"close_price": -10.0, "open_price": 95.0, "high_price": 105.0, "low_price": 90.0}
        assert v.check_critical_values("stock_prices", "TCS", "2023-01-01", valid_sp) is True
        assert v.check_critical_values("stock_prices", "TCS", "2023-01-01", invalid_sp) is False

    def test_dq09_stock_price_sanity(self):
        v = DataValidator()
        valid_rec = {"open_price": 100.0, "high_price": 110.0, "low_price": 90.0, "close_price": 105.0, "volume": 5000}
        assert v.check_stock_price_logic("TCS", "2023-01-01", valid_rec) is True

        # High less than Low
        bad_rec1 = {"open_price": 100.0, "high_price": 80.0, "low_price": 90.0, "close_price": 85.0, "volume": 5000}
        assert v.check_stock_price_logic("TCS", "2023-01-01", bad_rec1) is False

        # Negative volume
        bad_rec2 = {"open_price": 100.0, "high_price": 110.0, "low_price": 90.0, "close_price": 105.0, "volume": -100}
        assert v.check_stock_price_logic("TCS", "2023-01-01", bad_rec2) is False

    def test_dq10_financial_statement_cross_consistency(self):
        v = DataValidator()
        # Reported NPM is 10%, computed from net_profit=100 and sales=1000 is 10%
        assert v.check_financial_cross_consistency("TCS", "2023", 100.0, 10.0, 1000.0) is True
        # Mismatch: reported NPM is 25%, computed is 10%
        assert v.check_financial_cross_consistency("TCS", "2023", 100.0, 25.0, 1000.0) is False

    def test_dq11_sales_validity(self):
        v = DataValidator()
        assert v.check_sales_validity("TCS", "2023", 5000.0) is True
        assert v.check_sales_validity("TCS", "2023", 0.0) is True
        assert v.check_sales_validity("TCS", "2023", -50.0) is False

        fails = [f for f in v.failures if f.rule_id == "DQ-11"]
        assert len(fails) == 1
        assert fails[0].severity == "WARNING"

    def test_dq12_operating_profit_consistency(self):
        v = DataValidator()
        # Sales=1000, Expenses=800, OP=200, OPM=20%
        assert v.check_operating_profit_consistency("TCS", "2023", 1000.0, 800.0, 200.0, 20.0) is True
        # Mismatched OP (reported 300, expected 200)
        assert v.check_operating_profit_consistency("TCS", "2023", 1000.0, 800.0, 300.0, 20.0) is False

    def test_dq13_balance_sheet_consistency(self):
        v = DataValidator()
        good_bs = {
            "total_assets": 1000.0,
            "total_liabilities": 1000.0,
            "equity_capital": 100.0,
            "reserves": 400.0,
            "borrowings": 300.0,
            "other_liabilities": 200.0,
        }
        assert v.check_balance_sheet_consistency("TCS", "2023", good_bs) is True

        bad_bs = {
            "total_assets": 1200.0,
            "total_liabilities": 1000.0,
            "equity_capital": 100.0,
            "reserves": 400.0,
            "borrowings": 300.0,
            "other_liabilities": 200.0,
        }
        assert v.check_balance_sheet_consistency("TCS", "2023", bad_bs) is False

    def test_dq14_cash_flow_consistency(self):
        v = DataValidator()
        # Op=500, Inv=-200, Fin=-100, Net=200
        assert v.check_cash_flow_consistency("TCS", "2023", 500.0, -200.0, -100.0, 200.0) is True
        # Net mismatch (reported 50, expected 200)
        assert v.check_cash_flow_consistency("TCS", "2023", 500.0, -200.0, -100.0, 50.0) is False

    def test_dq15_company_year_coverage(self):
        v = DataValidator()
        v.check_year_coverage("profitandloss", "TCS", ["2019", "2020", "2021", "2022", "2023", "2024"], min_years=5)
        fails_good = [f for f in v.failures if f.rule_id == "DQ-15"]
        assert len(fails_good) == 0

        v.check_year_coverage("profitandloss", "NEWCO", ["2023", "2024"], min_years=5)
        fails_bad = [f for f in v.failures if f.rule_id == "DQ-15"]
        assert len(fails_bad) == 1
        assert fails_bad[0].severity == "INFO"

    def test_dq16_unexpected_malformed_values(self):
        v = DataValidator()
        v.check_malformed_values("companies", "TCS", None, "about_company", "  Untrimmed Text  ")
        v.check_malformed_values("profitandloss", "TCS", "2023", "interest", "NA")
        fails = [f for f in v.failures if f.rule_id == "DQ-16"]
        assert len(fails) == 2
        assert all(f.severity == "INFO" for f in fails)

    def test_validator_summary_counts_and_export(self):
        v = DataValidator()
        v.record_failure("DQ-01", "CRITICAL", "test_tbl", "TCS", "2023", "id", 0, "Bad PK")
        v.record_failure("DQ-05", "WARNING", "test_tbl", "TCS", "2023", "year", "N/A", "Bad Year")
        v.record_failure("DQ-16", "INFO", "test_tbl", "TCS", "2023", "col", "-", "Placeholder")

        summary = v.get_summary()
        assert summary["CRITICAL"] == 1
        assert summary["WARNING"] == 1
        assert summary["INFO"] == 1
        assert summary["TOTAL"] == 3

        with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as tf:
            temp_csv = tf.name
        try:
            v.export_failures_csv(temp_csv)
            assert os.path.exists(temp_csv)
            assert os.path.getsize(temp_csv) > 0
        finally:
            if os.path.exists(temp_csv):
                os.remove(temp_csv)

