"""Unit and integration tests for Day 31 Cash Flow Intelligence and Day 32 Capital Allocation."""

import os
import sqlite3
import pandas as pd
import pytest

from src.analytics.cashflow_kpis import (
    ALL_PATTERNS,
    capex_intensity,
    capex_label,
    capital_allocation_pattern,
    cfo_quality,
    cfo_quality_label,
    compute_fcf_cagr_5yr,
    compute_pattern_distribution,
    detect_pattern_changes,
    export_cashflow_intelligence_artifacts,
    fcf_conversion,
    free_cash_flow,
    is_deleveraging,
    is_distress,
)


class TestCashFlowKPICalculations:
    """Unit tests for cash flow formula logic and edge case handling."""

    def test_cfo_quality_zero_and_negative_pat(self):
        # Zero PAT should be excluded from denominator to avoid ZeroDivisionError
        # Negative PAT is preserved in ratio
        cfo_vals = [100.0, 50.0, -20.0]
        pat_vals = [100.0, 0.0, -10.0]
        # (100/100 = 1.0) and (-20 / -10 = 2.0) -> avg = 1.5
        assert cfo_quality(cfo_vals, pat_vals) == 1.5

    def test_cfo_quality_empty_and_insufficient(self):
        assert cfo_quality([], []) is None
        assert cfo_quality([10.0], [0.0]) is None
        assert cfo_quality([None], [50.0]) is None

    def test_cfo_quality_labels(self):
        assert cfo_quality_label(None) == "Insufficient Data"
        assert cfo_quality_label(1.25) == "High Quality"
        assert cfo_quality_label(1.0) == "Moderate"
        assert cfo_quality_label(0.5) == "Moderate"
        assert cfo_quality_label(0.49) == "Accrual Risk"
        assert cfo_quality_label(-0.2) == "Accrual Risk"

    def test_capex_intensity_boundaries(self):
        # < 3% -> Asset Light
        assert capex_label(2.9) == "Asset Light"
        # 3% to 8% -> Moderate
        assert capex_label(3.0) == "Moderate"
        assert capex_label(8.0) == "Moderate"
        # > 8% -> Capital Intensive
        assert capex_label(8.1) == "Capital Intensive"
        assert capex_label(None) == "Insufficient Data"

        # Edge cases for formula: zero / negative / None sales
        assert capex_intensity(-50.0, 1000.0) == 5.0
        assert capex_intensity(None, 1000.0) is None
        assert capex_intensity(-50.0, 0.0) is None
        assert capex_intensity(-50.0, None) is None

    def test_fcf_conversion_zero_negative_ebit(self):
        assert fcf_conversion(100.0, 200.0) == 50.0
        assert fcf_conversion(100.0, 0.0) is None
        assert fcf_conversion(100.0, None) is None
        assert fcf_conversion(None, 200.0) is None

    def test_distress_flag_conditions(self):
        # CFO < 0 and CFF > 0 -> True
        assert is_distress(-100.0, 50.0) is True
        # CFO >= 0
        assert is_distress(0.0, 50.0) is False
        assert is_distress(100.0, 50.0) is False
        # CFF <= 0
        assert is_distress(-100.0, 0.0) is False
        assert is_distress(-100.0, -50.0) is False
        # None inputs
        assert is_distress(None, 50.0) is False
        assert is_distress(-100.0, None) is False

    def test_deleveraging_flag_conditions(self):
        # CFF < 0 and curr_borrowings < prev_borrowings -> True
        assert is_deleveraging(-200.0, 800.0, 1000.0) is True
        # CFF >= 0
        assert is_deleveraging(0.0, 800.0, 1000.0) is False
        assert is_deleveraging(100.0, 800.0, 1000.0) is False
        # Borrowings increased or unchanged
        assert is_deleveraging(-200.0, 1000.0, 1000.0) is False
        assert is_deleveraging(-200.0, 1200.0, 1000.0) is False
        # Missing borrowing history
        assert is_deleveraging(-200.0, None, 1000.0) is False
        assert is_deleveraging(-200.0, 800.0, None) is False
        assert is_deleveraging(None, 800.0, 1000.0) is False

    def test_fcf_cagr_5yr_calculation(self):
        # Normal positive expansion
        cagr, flag = compute_fcf_cagr_5yr({2019: 100.0, 2024: 200.0}, latest_year=2024)
        assert flag == "NORMAL"
        assert cagr is not None and round(cagr, 2) == 14.87

        # Turnaround (- to +) returns None and TURNAROUND
        cagr, flag = compute_fcf_cagr_5yr({2019: -100.0, 2024: 200.0}, latest_year=2024)
        assert cagr is None
        assert flag == "TURNAROUND"

        # Decline to loss (+ to -) returns None and DECLINE_TO_LOSS
        cagr, flag = compute_fcf_cagr_5yr({2019: 100.0, 2024: -50.0}, latest_year=2024)
        assert cagr is None
        assert flag == "DECLINE_TO_LOSS"

        # Missing baseline (e.g. 2019 missing)
        cagr, flag = compute_fcf_cagr_5yr({2024: 200.0}, latest_year=2024)
        assert cagr is None
        assert flag == "INSUFFICIENT"


class TestCapitalAllocationAndDistribution:
    """Unit tests for capital allocation patterns, distribution, and transitions."""

    def test_capital_allocation_all_8_patterns(self):
        # (+, -, -) with quality > 1 -> Shareholder Returns
        assert capital_allocation_pattern(100.0, -40.0, -30.0, quality=1.2)[-1] == "Shareholder Returns"
        # (+, -, -) with quality <= 1 -> Reinvestor
        assert capital_allocation_pattern(100.0, -40.0, -30.0, quality=0.8)[-1] == "Reinvestor"
        # (+, +, -) -> Liquidating Assets
        assert capital_allocation_pattern(100.0, 20.0, -30.0)[-1] == "Liquidating Assets"
        # (-, +, +) -> Distress Signal
        assert capital_allocation_pattern(-50.0, 20.0, 40.0)[-1] == "Distress Signal"
        # (-, -, +) -> Growth Funded by Debt
        assert capital_allocation_pattern(-50.0, -80.0, 100.0)[-1] == "Growth Funded by Debt"
        # (+, +, +) -> Cash Accumulator
        assert capital_allocation_pattern(50.0, 20.0, 10.0)[-1] == "Cash Accumulator"
        # (-, -, -) -> Pre-Revenue
        assert capital_allocation_pattern(-50.0, -20.0, -10.0)[-1] == "Pre-Revenue"
        # (+, -, +) -> Mixed
        assert capital_allocation_pattern(50.0, -20.0, 10.0)[-1] == "Mixed"

    def test_pattern_distribution_table(self):
        sample_patterns = [
            "Shareholder Returns", "Shareholder Returns", "Reinvestor",
            "Liquidating Assets", "Distress Signal", "Growth Funded by Debt",
            "Pre-Revenue", "Mixed", "Mixed"
        ]
        dist = compute_pattern_distribution(sample_patterns)
        assert len(dist) == 8  # all 8 patterns included
        labels = [r["pattern_label"] for r in dist]
        assert set(labels) == set(ALL_PATTERNS)
        total_count = sum(r["company_count"] for r in dist)
        assert total_count == len(sample_patterns)
        total_pct = sum(r["percentage_pct"] for r in dist)
        assert round(total_pct, 1) == 100.0

    def test_pattern_changes_detection(self):
        records = [
            {"company_id": "TEST", "company_name": "Test Ltd", "year": "Mar 2021", "pattern_label": "Reinvestor"},
            {"company_id": "TEST", "company_name": "Test Ltd", "year": "Mar 2022", "pattern_label": "Reinvestor"},
            {"company_id": "TEST", "company_name": "Test Ltd", "year": "Mar 2023", "pattern_label": "Shareholder Returns"},
            {"company_id": "TEST", "company_name": "Test Ltd", "year": "Mar 2024", "pattern_label": "Mixed"},
        ]
        changes = detect_pattern_changes(records)
        assert len(changes) == 2
        assert changes[0]["previous_year"] == "Mar 2022"
        assert changes[0]["previous_pattern"] == "Reinvestor"
        assert changes[0]["current_year"] == "Mar 2023"
        assert changes[0]["current_pattern"] == "Shareholder Returns"

        assert changes[1]["previous_year"] == "Mar 2023"
        assert changes[1]["previous_pattern"] == "Shareholder Returns"
        assert changes[1]["current_year"] == "Mar 2024"
        assert changes[1]["current_pattern"] == "Mixed"


class TestCashflowArtifactsIntegration:
    """Integration tests verifying generated Sprint 5 Phase 2 outputs."""

    @pytest.fixture(scope="class", autouse=True)
    def ensure_artifacts(self):
        export_cashflow_intelligence_artifacts()

    def test_cashflow_intelligence_excel_shape_and_columns(self):
        excel_path = "output/cashflow_intelligence.xlsx"
        assert os.path.exists(excel_path)
        df = pd.read_excel(excel_path)

        assert df.shape[0] == 92
        assert df.shape[1] == 11
        expected_cols = [
            "company_id", "sector", "cfo_quality_score", "cfo_quality_label",
            "capex_intensity_pct", "capex_label", "fcf_cagr_5yr",
            "fcf_conversion_pct", "distress_flag", "deleveraging_flag",
            "capital_allocation_label"
        ]
        assert list(df.columns) == expected_cols
        assert df["company_id"].nunique() == 92
        assert df["company_id"].isnull().sum() == 0
        assert df["sector"].isnull().sum() == 0

        valid_cfo_labels = {"High Quality", "Moderate", "Accrual Risk", "Insufficient Data"}
        assert set(df["cfo_quality_label"].unique()).issubset(valid_cfo_labels)

        valid_capex_labels = {"Asset Light", "Moderate", "Capital Intensive", "Insufficient Data"}
        assert set(df["capex_label"].unique()).issubset(valid_capex_labels)

        assert set(df["capital_allocation_label"].unique()).issubset(set(ALL_PATTERNS))

    def test_distress_alerts_csv_validation(self):
        csv_path = "output/distress_alerts.csv"
        assert os.path.exists(csv_path)
        df = pd.read_csv(csv_path)

        assert len(df) == 13
        expected_cols = ["company_id", "company_name", "sector", "latest_year", "cfo", "cff", "net_profit", "reason"]
        assert list(df.columns) == expected_cols

        # All alerted companies must have cfo < 0 and cff > 0
        assert (df["cfo"] < 0).all()
        assert (df["cff"] > 0).all()
        assert (df["reason"].str.len() > 0).all()

    def test_capital_allocation_distribution_csv_validation(self):
        csv_path = "output/capital_allocation_distribution.csv"
        assert os.path.exists(csv_path)
        df = pd.read_csv(csv_path)

        assert len(df) == 8
        expected_cols = ["pattern_label", "company_count", "percentage_pct"]
        assert list(df.columns) == expected_cols
        assert set(df["pattern_label"]) == set(ALL_PATTERNS)

        assert df["company_count"].sum() == 92
        assert round(df["percentage_pct"].sum(), 2) == 100.0

    def test_pattern_changes_csv_validation(self):
        csv_path = "output/pattern_changes.csv"
        assert os.path.exists(csv_path)
        df = pd.read_csv(csv_path)

        expected_cols = [
            "company_id", "company_name", "previous_year", "previous_pattern",
            "current_year", "current_pattern"
        ]
        assert list(df.columns) == expected_cols
        assert len(df) > 0

        # Previous pattern must not equal current pattern
        assert (df["previous_pattern"] != df["current_pattern"]).all()

        # No TTM or interim transitions
        assert not df["previous_year"].str.contains("TTM").any()
        assert not df["current_year"].str.contains("TTM").any()
