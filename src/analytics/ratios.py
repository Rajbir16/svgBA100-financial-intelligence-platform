"""Sprint 2 computed financial ratio engine and SQLite runner."""

import argparse
import csv
import os
import sqlite3
from typing import Any, Dict, Optional

from src.analytics.cagr import cagr_for_series
from src.analytics.cashflow_kpis import capital_allocation_pattern, capex_intensity, capex_label, cfo_quality, cfo_quality_label, fcf_conversion, free_cash_flow


RATIO_COLUMNS = [
    "net_profit_margin_pct", "operating_profit_margin_pct", "return_on_equity_pct", "debt_to_equity",
    "interest_coverage", "asset_turnover", "free_cash_flow_cr", "capex_cr", "earnings_per_share",
    "book_value_per_share", "dividend_payout_ratio_pct", "total_debt_cr", "cash_from_operations_cr",
    "revenue_cagr_3yr", "revenue_cagr_3yr_flag", "revenue_cagr_5yr", "revenue_cagr_5yr_flag",
    "revenue_cagr_10yr", "revenue_cagr_10yr_flag", "pat_cagr_3yr", "pat_cagr_3yr_flag", "pat_cagr_5yr",
    "pat_cagr_5yr_flag", "pat_cagr_10yr", "pat_cagr_10yr_flag", "eps_cagr_3yr", "eps_cagr_3yr_flag",
    "eps_cagr_5yr", "eps_cagr_5yr_flag", "eps_cagr_10yr", "eps_cagr_10yr_flag", "composite_quality_score",
    "high_leverage_flag", "icr_warning", "return_on_capital_employed_pct", "return_on_assets_pct", "net_debt_cr",
    "cfo_quality_5yr", "cfo_quality_label", "capex_intensity_pct", "capex_intensity_label", "fcf_conversion_pct", "icr_label",
    "sales_cr", "net_profit_cr", "operating_profit_cr", "other_income_cr", "interest_expense_cr", "equity_cr", "reserves_cr", "investments_cr", "total_assets_cr",
]


def safe_divide(numerator: Optional[float], denominator: Optional[float], multiplier: float = 1.0) -> Optional[float]:
    return None if numerator is None or denominator in (None, 0) else numerator / denominator * multiplier


def profitability_kpis(pnl: Dict[str, Any], bs: Dict[str, Any]) -> Dict[str, Optional[float]]:
    equity = (bs.get("equity_capital") or 0) + (bs.get("reserves") or 0)
    assets = bs.get("total_assets")
    return {
        "net_profit_margin_pct": safe_divide(pnl.get("net_profit"), pnl.get("sales"), 100),
        "operating_profit_margin_pct": safe_divide(pnl.get("operating_profit"), pnl.get("sales"), 100),
        "return_on_equity_pct": safe_divide(pnl.get("net_profit"), equity, 100) if equity > 0 else None,
        "return_on_capital_employed_pct": safe_divide((pnl.get("operating_profit") or 0) + (pnl.get("other_income") or 0), equity + (bs.get("borrowings") or 0), 100),
        "return_on_assets_pct": safe_divide(pnl.get("net_profit"), assets, 100),
    }


def leverage_efficiency_kpis(pnl: Dict[str, Any], bs: Dict[str, Any], is_financials: bool = False) -> Dict[str, Any]:
    equity = (bs.get("equity_capital") or 0) + (bs.get("reserves") or 0)
    borrowings = bs.get("borrowings") or 0
    interest = pnl.get("interest")
    icr = safe_divide((pnl.get("operating_profit") or 0) + (pnl.get("other_income") or 0), interest)
    debt_to_equity = 0.0 if borrowings == 0 else safe_divide(borrowings, equity)
    return {
        "debt_to_equity": debt_to_equity,
        "high_leverage_flag": int(not is_financials and debt_to_equity is not None and debt_to_equity > 5),
        "interest_coverage": icr,
        "icr_label": "Debt Free" if icr is None else "Warning" if icr < 1.5 else "Healthy",
        "icr_warning": int(icr is not None and icr < 1.5),
        "net_debt_cr": borrowings - (bs.get("investments") or 0),
        "asset_turnover": safe_divide(pnl.get("sales"), bs.get("total_assets")),
    }


def _year_number(year: Any) -> Optional[int]:
    try:
        return int(str(year)[-4:])
    except (TypeError, ValueError):
        return None


def _dedup_rows(conn: sqlite3.Connection, table: str) -> Dict[tuple, Dict[str, Any]]:
    cols = [row[1] for row in conn.execute(f"PRAGMA table_info({table})")]
    rows = conn.execute(f"SELECT {', '.join(cols)} FROM {table} ORDER BY id").fetchall()
    return {(row[1], row[2]): dict(zip(cols, row)) for row in rows}


def _ensure_columns(conn: sqlite3.Connection) -> None:
    existing = {row[1] for row in conn.execute("PRAGMA table_info(financial_ratios)")}
    for column in RATIO_COLUMNS:
        if column not in existing:
            kind = "TEXT" if column.endswith("_flag") or column.endswith("_label") else "INTEGER" if column in ("high_leverage_flag", "icr_warning") else "REAL"
            conn.execute(f"ALTER TABLE financial_ratios ADD COLUMN {column} {kind}")


def _series(rows: Dict[tuple, Dict[str, Any]], company: str, field: str) -> Dict[int, Optional[float]]:
    result = {}
    for (company_id, raw_year), row in rows.items():
        year = _year_number(raw_year)
        if company_id == company and year is not None:
            result[year] = row.get(field)
    return result


def _populate_cagrs(company: str, year: int, pnl_rows: Dict[tuple, Dict[str, Any]]) -> Dict[str, Any]:
    result: Dict[str, Any] = {}
    for prefix, field in (("revenue", "sales"), ("pat", "net_profit"), ("eps", "eps")):
        series = _series(pnl_rows, company, field)
        for window in (3, 5, 10):
            value, flag = cagr_for_series(series, year, window)
            result[f"{prefix}_cagr_{window}yr"] = value
            result[f"{prefix}_cagr_{window}yr_flag"] = flag
    return result


def run_engine(db_path: str = "nifty100.db", output_dir: str = "output") -> Dict[str, Any]:
    os.makedirs(output_dir, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys = ON")
    _ensure_columns(conn)
    pnl_rows, bs_rows, cf_rows = (_dedup_rows(conn, table) for table in ("profitandloss", "balancesheet", "cashflow"))
    companies = {row[0]: {"book_value": row[1], "roe_percentage": row[2], "roce_percentage": row[3]} for row in conn.execute("SELECT id, book_value, roe_percentage, roce_percentage FROM companies")}
    sectors = {row[0]: (row[1] or "") for row in conn.execute("SELECT company_id, broad_sector FROM sectors")}
    keys = sorted(set(pnl_rows) | set(bs_rows) | set(cf_rows), key=lambda item: (item[0], str(item[1])))
    conn.execute("DELETE FROM financial_ratios")
    output_rows, edge_log = [], []
    ratio_insert = ["company_id", "year"] + RATIO_COLUMNS
    placeholders = ", ".join("?" for _ in ratio_insert)
    for company, raw_year in keys:
        pnl = pnl_rows.get((company, raw_year), {})
        bs = bs_rows.get((company, raw_year), {})
        cf = cf_rows.get((company, raw_year), {})
        equity = (bs.get("equity_capital") or 0) + (bs.get("reserves") or 0)
        profitability = {
            "net_profit_margin_pct": safe_divide(pnl.get("net_profit"), pnl.get("sales"), 100),
            "operating_profit_margin_pct": safe_divide(pnl.get("operating_profit"), pnl.get("sales"), 100),
            "return_on_equity_pct": safe_divide(pnl.get("net_profit"), equity, 100) if equity > 0 else None,
            "return_on_capital_employed_pct": safe_divide((pnl.get("operating_profit") or 0) + (pnl.get("other_income") or 0), equity + (bs.get("borrowings") or 0), 100),
            "return_on_assets_pct": safe_divide(pnl.get("net_profit"), bs.get("total_assets"), 100),
        }
        is_financials = sectors.get(company, "").lower() == "financials"
        leverage = leverage_efficiency_kpis(pnl, bs, is_financials)
        fcf = free_cash_flow(cf.get("operating_activity"), cf.get("investing_activity"))
        year_number = _year_number(raw_year)
        pnl_series = _series(pnl_rows, company, "net_profit")
        cfo_series = _series(cf_rows, company, "operating_activity")
        quality_years = sorted(year for year in pnl_series if year_number is not None and year <= year_number)[-5:]
        quality = cfo_quality([cfo_series.get(year) for year in quality_years], [pnl_series.get(year) for year in quality_years])
        components = [(profitability["operating_profit_margin_pct"], 0.3), (profitability["return_on_equity_pct"], 0.3), (quality, 0.2), (leverage["interest_coverage"], 0.2)]
        available_weight = sum(weight for value, weight in components if value is not None)
        score = sum(value * weight for value, weight in components if value is not None) / available_weight if available_weight else None
        capex_pct = capex_intensity(cf.get("investing_activity"), pnl.get("sales"))
        data = {**profitability, **leverage, "free_cash_flow_cr": fcf, "capex_cr": abs(cf["investing_activity"]) if cf.get("investing_activity") is not None else None, "earnings_per_share": pnl.get("eps"), "book_value_per_share": companies.get(company, {}).get("book_value"), "dividend_payout_ratio_pct": pnl.get("dividend_payout"), "total_debt_cr": bs.get("borrowings"), "cash_from_operations_cr": cf.get("operating_activity"), "composite_quality_score": score, "cfo_quality_5yr": quality, "cfo_quality_label": cfo_quality_label(quality), "capex_intensity_pct": capex_pct, "capex_intensity_label": capex_label(capex_pct), "fcf_conversion_pct": fcf_conversion(fcf, pnl.get("operating_profit")), "sales_cr": pnl.get("sales"), "net_profit_cr": pnl.get("net_profit"), "operating_profit_cr": pnl.get("operating_profit"), "other_income_cr": pnl.get("other_income"), "interest_expense_cr": pnl.get("interest"), "equity_cr": bs.get("equity_capital"), "reserves_cr": bs.get("reserves"), "investments_cr": bs.get("investments"), "total_assets_cr": bs.get("total_assets")}
        if year_number:
            data.update(_populate_cagrs(company, year_number, pnl_rows))
        conn.execute(f"INSERT INTO financial_ratios ({', '.join(ratio_insert)}) VALUES ({placeholders})", [company, raw_year] + [data.get(column) for column in RATIO_COLUMNS])
        output_rows.append((company, raw_year, *capital_allocation_pattern(cf.get("operating_activity"), cf.get("investing_activity"), cf.get("financing_activity"), quality)))
        for name, computed, source in (("ROE", profitability["return_on_equity_pct"], companies.get(company, {}).get("roe_percentage")), ("ROCE", profitability["return_on_capital_employed_pct"], companies.get(company, {}).get("roce_percentage"))):
            if computed is not None and source is not None and abs(computed - source) > 5:
                category = "data source issue" if abs(computed - source) > 20 else "version difference" if abs(computed - source) > 10 else "formula discrepancy"
                edge_log.append(f"{company},{raw_year},{name},computed={computed:.4f},source={source:.4f},category={category}")
        source_opm = pnl.get("opm_percentage")
        computed_opm = profitability["operating_profit_margin_pct"]
        if source_opm is not None and computed_opm is not None and abs(computed_opm - source_opm) > 1:
            edge_log.append(f"{company},{raw_year},OPM,computed={computed_opm:.4f},source={source_opm:.4f},category=version difference")
    conn.commit()
    with open(os.path.join(output_dir, "capital_allocation.csv"), "w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerow(["company_id", "year", "cfo_sign", "cfi_sign", "cff_sign", "pattern_label"])
        writer.writerows(output_rows)
    with open(os.path.join(output_dir, "ratio_edge_cases.log"), "w", encoding="utf-8") as file:
        file.write("OPM cross-checks above 1%; ROE/ROCE cross-checks above 5%; computed engine values retained.\nCategories: data source issue, version difference, formula discrepancy.\nFinancials high D/E warning suppressed.\n")
        file.write("\n".join(edge_log))
    count = conn.execute("SELECT count(*) FROM financial_ratios").fetchone()[0]
    conn.close()
    return {"rows": count, "capital_allocation_rows": len(output_rows), "edge_cases": len(edge_log)}


def main() -> None:
    parser = argparse.ArgumentParser(description="Compute Sprint 2 financial KPIs")
    parser.add_argument("--db", default="nifty100.db")
    parser.add_argument("--output-dir", default="output")
    args = parser.parse_args()
    print(run_engine(args.db, args.output_dir))


if __name__ == "__main__":
    main()