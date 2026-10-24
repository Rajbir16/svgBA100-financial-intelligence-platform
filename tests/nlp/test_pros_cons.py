"""Unit and integration tests for Automatic Pros & Cons Generator (Day 30)."""

import os
import sqlite3
import pandas as pd
import pytest

from src.nlp.pros_cons_generator import (
    CON_RULE_DEFINITIONS,
    PRO_RULE_DEFINITIONS,
    evaluate_company_pros_and_cons,
    generate_pros_and_cons,
)


class TestProsConsRulesIndividual:
    """Tests evaluating each pro and con rule individually with isolated synthetic data."""

    def test_pro_01_sustained_roe(self):
        # 3 consecutive years with ROE > 20%
        fr = pd.DataFrame({
            "year": ["Mar 2022", "Mar 2023", "Mar 2024"],
            "return_on_equity_pct": [22.0, 24.5, 21.0],
        })
        pros, cons = evaluate_company_pros_and_cons(
            "TEST", "Test Co", "Industrials", fr, pd.DataFrame(), pd.DataFrame(), None
        )
        pro_ids = [p["rule_id"] for p in pros]
        assert "PRO_01" in pro_ids

    def test_pro_02_positive_fcf_5yr(self):
        # 5 consecutive years positive FCF
        fr = pd.DataFrame({
            "year": ["Mar 2020", "Mar 2021", "Mar 2022", "Mar 2023", "Mar 2024"],
            "free_cash_flow_cr": [100.0, 150.0, 200.0, 250.0, 300.0],
        })
        pros, cons = evaluate_company_pros_and_cons(
            "TEST", "Test Co", "Industrials", fr, pd.DataFrame(), pd.DataFrame(), None
        )
        pro_ids = [p["rule_id"] for p in pros]
        assert "PRO_02" in pro_ids

    def test_pro_03_zero_de(self):
        fr = pd.DataFrame({
            "year": ["Mar 2024"],
            "debt_to_equity": [0.0],
            "icr_label": ["Debt Free"],
        })
        pros, cons = evaluate_company_pros_and_cons(
            "TEST", "Test Co", "Industrials", fr, pd.DataFrame(), pd.DataFrame(), None
        )
        pro_ids = [p["rule_id"] for p in pros]
        assert "PRO_03" in pro_ids

    def test_pro_04_revenue_cagr_gt_15(self):
        fr = pd.DataFrame({"year": ["Mar 2024"], "revenue_cagr_5yr": [18.2]})
        pros, cons = evaluate_company_pros_and_cons(
            "TEST", "Test Co", "Industrials", fr, pd.DataFrame(), pd.DataFrame(), None
        )
        pro_ids = [p["rule_id"] for p in pros]
        assert "PRO_04" in pro_ids

    def test_pro_05_opm_gt_25(self):
        fr = pd.DataFrame({"year": ["Mar 2024"], "operating_profit_margin_pct": [28.5]})
        pros, cons = evaluate_company_pros_and_cons(
            "TEST", "Test Co", "Industrials", fr, pd.DataFrame(), pd.DataFrame(), None
        )
        pro_ids = [p["rule_id"] for p in pros]
        assert "PRO_05" in pro_ids

    def test_pro_06_pat_cagr_gt_20(self):
        fr = pd.DataFrame({"year": ["Mar 2024"], "pat_cagr_5yr": [23.1]})
        pros, cons = evaluate_company_pros_and_cons(
            "TEST", "Test Co", "Industrials", fr, pd.DataFrame(), pd.DataFrame(), None
        )
        pro_ids = [p["rule_id"] for p in pros]
        assert "PRO_06" in pro_ids

    def test_pro_07_icr_gt_10(self):
        fr = pd.DataFrame({"year": ["Mar 2024"], "interest_coverage": [14.5]})
        pros, cons = evaluate_company_pros_and_cons(
            "TEST", "Test Co", "Industrials", fr, pd.DataFrame(), pd.DataFrame(), None
        )
        pro_ids = [p["rule_id"] for p in pros]
        assert "PRO_07" in pro_ids

    def test_pro_08_dividend_yield_gt_2_and_fcf_positive(self):
        fr = pd.DataFrame({"year": ["Mar 2024"], "free_cash_flow_cr": [500.0]})
        pros, cons = evaluate_company_pros_and_cons(
            "TEST", "Test Co", "Industrials", fr, pd.DataFrame(), pd.DataFrame(), div_yield=2.8
        )
        pro_ids = [p["rule_id"] for p in pros]
        assert "PRO_08" in pro_ids

    def test_pro_09_eps_cagr_gt_15(self):
        fr = pd.DataFrame({"year": ["Mar 2024"], "eps_cagr_5yr": [17.5]})
        pros, cons = evaluate_company_pros_and_cons(
            "TEST", "Test Co", "Industrials", fr, pd.DataFrame(), pd.DataFrame(), None
        )
        pro_ids = [p["rule_id"] for p in pros]
        assert "PRO_09" in pro_ids

    def test_pro_10_roe_improving_3_consecutive_years(self):
        fr = pd.DataFrame({
            "year": ["Mar 2022", "Mar 2023", "Mar 2024"],
            "return_on_equity_pct": [12.0, 15.0, 18.0],
        })
        pros, cons = evaluate_company_pros_and_cons(
            "TEST", "Test Co", "Industrials", fr, pd.DataFrame(), pd.DataFrame(), None
        )
        pro_ids = [p["rule_id"] for p in pros]
        assert "PRO_10" in pro_ids

    def test_pro_11_revenue_cagr_exceeds_pat_cagr_condition_and_text(self):
        # Stated condition: revenue_cagr_5yr > pat_cagr_5yr
        fr = pd.DataFrame({
            "year": ["Mar 2024"],
            "revenue_cagr_5yr": [20.0],
            "pat_cagr_5yr": [12.0],
        })
        pros, cons = evaluate_company_pros_and_cons(
            "TEST", "Test Co", "Industrials", fr, pd.DataFrame(), pd.DataFrame(), None
        )
        matched = [p for p in pros if p["rule_id"] == "PRO_11"]
        assert len(matched) == 1
        # Check supplied text exactly
        assert matched[0]["text"] == (
            "Revenue growing slower than profits shows improving operating leverage and scale benefits"
        )

    def test_pro_12_assets_grow_debt_declines(self):
        bs = pd.DataFrame({
            "year": ["Mar 2023", "Mar 2024"],
            "total_assets": [10000.0, 12000.0],
            "borrowings": [3000.0, 2500.0],
        })
        pros, cons = evaluate_company_pros_and_cons(
            "TEST", "Test Co", "Industrials", pd.DataFrame(), pd.DataFrame(), bs, None
        )
        pro_ids = [p["rule_id"] for p in pros]
        assert "PRO_12" in pro_ids

    def test_con_01_non_financial_de_gt_2(self):
        # Non-financial company with D/E = 2.45
        fr = pd.DataFrame({"year": ["Mar 2024"], "debt_to_equity": [2.45]})
        pros, cons = evaluate_company_pros_and_cons(
            "TEST", "Test Co", "Industrials", fr, pd.DataFrame(), pd.DataFrame(), None
        )
        matched = [c for c in cons if c["rule_id"] == "CON_01"]
        assert len(matched) == 1
        assert "Debt-to-equity ratio of 2.45 is elevated for a non-financial company" in matched[0]["text"]

    def test_con_01_financial_sector_exclusion(self):
        # Financial company with D/E = 6.5 MUST NOT trigger CON_01
        fr = pd.DataFrame({"year": ["Mar 2024"], "debt_to_equity": [6.5]})
        pros, cons = evaluate_company_pros_and_cons(
            "TEST_BANK", "Test Bank Ltd", "Financials", fr, pd.DataFrame(), pd.DataFrame(), None
        )
        con_ids = [c["rule_id"] for c in cons]
        assert "CON_01" not in con_ids

    def test_con_02_negative_fcf_3yr(self):
        fr = pd.DataFrame({
            "year": ["Mar 2022", "Mar 2023", "Mar 2024"],
            "free_cash_flow_cr": [-50.0, -100.0, -150.0],
        })
        pros, cons = evaluate_company_pros_and_cons(
            "TEST", "Test Co", "Industrials", fr, pd.DataFrame(), pd.DataFrame(), None
        )
        con_ids = [c["rule_id"] for c in cons]
        assert "CON_02" in con_ids

    def test_con_03_opm_declines_3yr(self):
        fr = pd.DataFrame({
            "year": ["Mar 2022", "Mar 2023", "Mar 2024"],
            "operating_profit_margin_pct": [25.0, 22.0, 19.0],
        })
        pros, cons = evaluate_company_pros_and_cons(
            "TEST", "Test Co", "Industrials", fr, pd.DataFrame(), pd.DataFrame(), None
        )
        con_ids = [c["rule_id"] for c in cons]
        assert "CON_03" in con_ids

    def test_con_04_latest_net_loss(self):
        pl = pd.DataFrame({"year": ["Mar 2024"], "net_profit": [-350.0]})
        pros, cons = evaluate_company_pros_and_cons(
            "TEST", "Test Co", "Industrials", pd.DataFrame(), pl, pd.DataFrame(), None
        )
        con_ids = [c["rule_id"] for c in cons]
        assert "CON_04" in con_ids

    def test_con_05_revenue_declines_2yr(self):
        pl = pd.DataFrame({
            "year": ["Mar 2022", "Mar 2023", "Mar 2024"],
            "sales": [5000.0, 4500.0, 4000.0],
        })
        pros, cons = evaluate_company_pros_and_cons(
            "TEST", "Test Co", "Industrials", pd.DataFrame(), pl, pd.DataFrame(), None
        )
        con_ids = [c["rule_id"] for c in cons]
        assert "CON_05" in con_ids

    def test_con_06_icr_below_1_point_5(self):
        fr = pd.DataFrame({
            "year": ["Mar 2024"],
            "interest_coverage": [1.1],
            "debt_to_equity": [1.5],
            "icr_label": ["Normal"],
        })
        pros, cons = evaluate_company_pros_and_cons(
            "TEST", "Test Co", "Industrials", fr, pd.DataFrame(), pd.DataFrame(), None
        )
        con_ids = [c["rule_id"] for c in cons]
        assert "CON_06" in con_ids

    def test_con_07_dividend_payout_gt_100(self):
        fr = pd.DataFrame({"year": ["Mar 2024"], "dividend_payout_ratio_pct": [125.0]})
        pros, cons = evaluate_company_pros_and_cons(
            "TEST", "Test Co", "Industrials", fr, pd.DataFrame(), pd.DataFrame(), None
        )
        con_ids = [c["rule_id"] for c in cons]
        assert "CON_07" in con_ids

    def test_con_08_de_rises_3yr(self):
        fr = pd.DataFrame({
            "year": ["Mar 2022", "Mar 2023", "Mar 2024"],
            "debt_to_equity": [0.5, 0.8, 1.2],
        })
        pros, cons = evaluate_company_pros_and_cons(
            "TEST", "Test Co", "Industrials", fr, pd.DataFrame(), pd.DataFrame(), None
        )
        con_ids = [c["rule_id"] for c in cons]
        assert "CON_08" in con_ids

    def test_con_09_eps_declines_3yr(self):
        pl = pd.DataFrame({
            "year": ["Mar 2022", "Mar 2023", "Mar 2024"],
            "eps": [45.0, 38.0, 30.0],
        })
        pros, cons = evaluate_company_pros_and_cons(
            "TEST", "Test Co", "Industrials", pd.DataFrame(), pl, pd.DataFrame(), None
        )
        con_ids = [c["rule_id"] for c in cons]
        assert "CON_09" in con_ids

    def test_con_10_roce_below_10(self):
        fr = pd.DataFrame({"year": ["Mar 2024"], "return_on_capital_employed_pct": [7.8]})
        pros, cons = evaluate_company_pros_and_cons(
            "TEST", "Test Co", "Industrials", fr, pd.DataFrame(), pd.DataFrame(), None
        )
        con_ids = [c["rule_id"] for c in cons]
        assert "CON_10" in con_ids

    def test_con_11_net_debt_exceeds_3x_ebitda(self):
        pl = pd.DataFrame({
            "year": ["Mar 2024"],
            "operating_profit": [800.0],
            "depreciation": [200.0],  # EBITDA = 1000.0
        })
        fr = pd.DataFrame({
            "year": ["Mar 2024"],
            "total_debt_cr": [3500.0],  # Debt > 3 * 1000
        })
        pros, cons = evaluate_company_pros_and_cons(
            "TEST", "Test Co", "Industrials", fr, pl, pd.DataFrame(), None
        )
        con_ids = [c["rule_id"] for c in cons]
        assert "CON_11" in con_ids

    def test_con_11_does_not_infer_missing_ebitda(self):
        # Operating profit missing -> do not trigger CON_11
        pl = pd.DataFrame({
            "year": ["Mar 2024"],
            "operating_profit": [None],
            "depreciation": [200.0],
        })
        fr = pd.DataFrame({
            "year": ["Mar 2024"],
            "total_debt_cr": [3500.0],
        })
        pros, cons = evaluate_company_pros_and_cons(
            "TEST", "Test Co", "Industrials", fr, pl, pd.DataFrame(), None
        )
        con_ids = [c["rule_id"] for c in cons]
        assert "CON_11" not in con_ids

    def test_con_12_revenue_cagr_below_5(self):
        fr = pd.DataFrame({"year": ["Mar 2024"], "revenue_cagr_5yr": [3.2]})
        pros, cons = evaluate_company_pros_and_cons(
            "TEST", "Test Co", "Industrials", fr, pd.DataFrame(), pd.DataFrame(), None
        )
        con_ids = [c["rule_id"] for c in cons]
        assert "CON_12" in con_ids


class TestProsConsGeneratorIntegration:
    """Integration tests across full database and output validation."""

    def test_generate_pros_and_cons_execution(self):
        gen_df, unres_df = generate_pros_and_cons(db_path="nifty100.db")

        # Verify output files exist
        assert os.path.exists("output/pros_cons_generated.csv")
        assert os.path.exists("output/pros_cons_unresolved.csv")

        # Verify columns
        assert list(gen_df.columns) == [
            "company_id",
            "type",
            "rule_id",
            "text",
            "confidence_pct",
        ]
        assert list(unres_df.columns) == [
            "company_id",
            "company_name",
            "sector",
            "has_pro",
            "has_con",
            "status",
            "reason",
        ]

    def test_all_confidence_strictly_greater_than_60(self):
        gen_df = pd.read_csv("output/pros_cons_generated.csv")
        assert (gen_df["confidence_pct"] > 60.0).all()

    def test_no_duplicate_records(self):
        gen_df = pd.read_csv("output/pros_cons_generated.csv")
        assert not gen_df.duplicated(subset=["company_id", "type", "rule_id"]).any()

    def test_company_ids_all_valid_master_ids(self):
        conn = sqlite3.connect("nifty100.db")
        master_ids = set(pd.read_sql("SELECT id FROM companies", conn)["id"])
        conn.close()

        gen_df = pd.read_csv("output/pros_cons_generated.csv")
        for cid in gen_df["company_id"]:
            assert cid in master_ids, f"Company {cid} not in master companies table!"

    def test_all_92_companies_covered_or_unresolved_reported(self):
        conn = sqlite3.connect("nifty100.db")
        master_ids = set(pd.read_sql("SELECT id FROM companies", conn)["id"])
        conn.close()

        assert len(master_ids) == 92

        gen_df = pd.read_csv("output/pros_cons_generated.csv")
        unres_df = pd.read_csv("output/pros_cons_unresolved.csv")

        gen_cos = set(gen_df["company_id"])
        unres_cos = set(unres_df["company_id"])

        # Every company with generated pros/cons is in master
        assert gen_cos.issubset(master_ids)
        # All 92 companies have at least one pro or con
        assert len(gen_cos) == 92
        # Unresolved coverage companies are clearly documented
        assert len(unres_df) == 2
        assert "SIEMENS" in unres_cos
        assert "SBIN" in unres_cos
