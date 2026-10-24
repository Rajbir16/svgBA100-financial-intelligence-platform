"""Unit and integration tests for NLP Analysis Text Parser (Day 29)."""

import os
import sqlite3
import pandas as pd
import pytest

from src.nlp.parser import (
    ANALYSIS_YEARS_REGEX,
    cross_validate_cagrs,
    parse_analysis_data,
    parse_analysis_text,
)


class TestAnalysisParserRegex:
    """Tests for regex parsing of multi-period financial text."""

    def test_standard_format_with_decimals(self):
        result = parse_analysis_text("5 Years: 18.5%")
        assert result == (5, 18.5)

    def test_integer_percentage(self):
        result = parse_analysis_text("10 Years: 21%")
        assert result == (10, 21.0)

    def test_singular_year(self):
        result = parse_analysis_text("1 Year: 13%")
        assert result == (1, 13.0)

    def test_negative_percentage(self):
        result = parse_analysis_text("1 Year: -2%")
        assert result == (1, -2.0)
        result_dec = parse_analysis_text("3 Years: -1.75%")
        assert result_dec == (3, -1.75)

    def test_spacing_and_tab_variations(self):
        result = parse_analysis_text("   10    Years:      11%    ")
        assert result == (10, 11.0)
        result2 = parse_analysis_text("5 Years          14%")
        assert result2 == (5, 14.0)

    def test_punctuation_variations(self):
        # Missing colon, dash separator, hyphen
        assert parse_analysis_text("5 Years 14%") == (5, 14.0)
        assert parse_analysis_text("3 Years - 12.5%") == (3, 12.5)

    def test_non_matching_ttm(self):
        # TTM is a Trailing Twelve Months period, not an integer year count
        assert parse_analysis_text("TTM: 43%") is None

    def test_non_matching_last_year(self):
        # 'Last Year' lacks numeric year count
        assert parse_analysis_text("Last Year: 12%") is None

    def test_malformed_and_empty_inputs(self):
        assert parse_analysis_text("") is None
        assert parse_analysis_text("   ") is None
        assert parse_analysis_text(None) is None
        assert parse_analysis_text("N/A") is None
        assert parse_analysis_text("5 Years: invalid%") is None
        assert parse_analysis_text("5 Years: 18.5") is None  # Missing %


class TestAnalysisParserIntegration:
    """Integration tests for parse_analysis_data and cross_validate_cagrs."""

    def test_parse_analysis_data_outputs_and_columns(self):
        parsed_df, failures_df = parse_analysis_data(db_path="nifty100.db")

        # Verify parsed CSV structure
        assert os.path.exists("output/analysis_parsed.csv")
        assert list(parsed_df.columns) == [
            "company_id",
            "metric_type",
            "period_years",
            "value_pct",
        ]
        assert len(parsed_df) > 0

        # Verify failures CSV structure
        assert os.path.exists("output/parse_failures.csv")
        assert list(failures_df.columns) == [
            "company_id",
            "source_field",
            "original_text",
            "failure_reason",
        ]
        assert len(failures_df) > 0

    def test_parsed_company_ids_are_valid(self):
        conn = sqlite3.connect("nifty100.db")
        valid_ids = set(pd.read_sql("SELECT id FROM companies", conn)["id"])
        conn.close()

        parsed_df = pd.read_csv("output/analysis_parsed.csv")
        for cid in parsed_df["company_id"]:
            assert cid in valid_ids, f"Invalid company ID {cid} found in parsed CSV!"

    def test_no_duplicate_parsed_records(self):
        parsed_df = pd.read_csv("output/analysis_parsed.csv")
        assert not parsed_df.duplicated(
            subset=["company_id", "metric_type", "period_years"]
        ).any()

    def test_cagr_cross_validation_runs_and_flags_divergence(self):
        parsed_df = pd.read_csv("output/analysis_parsed.csv")
        val_df = cross_validate_cagrs(parsed_df, db_path="nifty100.db")

        assert os.path.exists("output/cagr_cross_validation.csv")
        expected_cols = [
            "company_id",
            "parsed_metric",
            "engine_metric",
            "period_years",
            "parsed_value_pct",
            "engine_value_pct",
            "absolute_divergence_pp",
            "divergence_gt_5pp",
            "status",
        ]
        assert list(val_df.columns) == expected_cols
        assert len(val_df) > 0

        # Verify divergence math
        for _, row in val_df.iterrows():
            diff = round(abs(row["parsed_value_pct"] - row["engine_value_pct"]), 4)
            assert row["absolute_divergence_pp"] == diff
            if diff > 5.0:
                assert row["divergence_gt_5pp"] is True
                assert row["status"] == "FLAG_FOR_REVIEW"
            else:
                assert row["divergence_gt_5pp"] is False
                assert row["status"] == "ALIGNED"
