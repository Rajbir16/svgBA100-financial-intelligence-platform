"""Shared database queries for Sprint 5 report generators."""

import os
import re
import sqlite3
from typing import Any, Dict, List, Optional, Tuple

from src.analytics.cashflow_kpis import capital_allocation_pattern


DB_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "nifty100.db")
)
_MONTHS = {
    "Jan": 1, "Feb": 2, "Mar": 3, "Apr": 4, "May": 5, "Jun": 6,
    "Jul": 7, "Aug": 8, "Sep": 9, "Oct": 10, "Nov": 11, "Dec": 12,
}


def _annual_year_key(year: str) -> Optional[Tuple[int, int]]:
    match = re.fullmatch(r"([A-Za-z]{3})\s+(\d{4})", year or "")
    if match:
        return int(match.group(2)), _MONTHS[match.group(1).title()]
    match = re.fullmatch(r"(\d{4})", year or "")
    if match:
        return int(match.group(1)), 3
    return None


def _latest_market_caps(
    conn: sqlite3.Connection,
) -> Dict[str, Tuple[Any, Any]]:
    rows = conn.execute(
        """
        SELECT company_id, market_cap_crore, pe_ratio
        FROM market_cap
        WHERE id IN (
            SELECT m.id FROM market_cap m
            WHERE m.id = (
                SELECT latest.id FROM market_cap latest
                WHERE latest.company_id = m.company_id
                ORDER BY latest.year DESC, latest.id DESC LIMIT 1
            )
        )
        """
    ).fetchall()
    return {row[0]: (row[1], row[2]) for row in rows}


def load_company_summaries(db_path: str = DB_PATH) -> List[Dict[str, Any]]:
    """Load latest usable annual KPIs and matching cash-flow indicators."""
    with sqlite3.connect(db_path) as conn:
        companies = conn.execute(
            """
            SELECT c.id, c.company_name,
                   COALESCE(s.broad_sector, 'Unclassified')
            FROM companies c
            LEFT JOIN sectors s ON s.company_id = c.id
            ORDER BY c.id
            """
        ).fetchall()
        ratio_rows = conn.execute(
            """
            SELECT company_id, year, return_on_equity_pct,
                   return_on_capital_employed_pct, net_profit_margin_pct,
                   debt_to_equity, free_cash_flow_cr, composite_quality_score,
                   cfo_quality_5yr, cfo_quality_label, fcf_conversion_pct,
                   revenue_cagr_5yr, revenue_cagr_5yr_flag,
                   pat_cagr_5yr, pat_cagr_5yr_flag, id
            FROM financial_ratios
            WHERE year != 'TTM' AND year NOT LIKE '%(%'
            ORDER BY id
            """
        ).fetchall()
        cashflow_rows = conn.execute(
            """
            SELECT company_id, year, operating_activity, investing_activity,
                   financing_activity, id
            FROM cashflow
            WHERE year != 'TTM' AND year NOT LIKE '%(%'
            ORDER BY id
            """
        ).fetchall()
        market_caps = _latest_market_caps(conn)

    ratios_by_company: Dict[str, List[Dict[str, Any]]] = {}
    for row in ratio_rows:
        year_key = _annual_year_key(row[1])
        if year_key is None:
            continue
        ratio = {
            "fiscal_year": row[1],
            "year_key": year_key,
            "roe": row[2],
            "roce": row[3],
            "net_profit_margin": row[4],
            "debt_to_equity": row[5],
            "free_cash_flow": row[6],
            "quality_score": row[7],
            "cashflow_quality_score": row[8],
            "cashflow_quality_label": row[9],
            "fcf_conversion_pct": row[10],
            "revenue_cagr_5yr": row[11],
            "revenue_cagr_5yr_flag": row[12],
            "pat_cagr_5yr": row[13],
            "pat_cagr_5yr_flag": row[14],
            "id": row[15],
        }
        ratios_by_company.setdefault(row[0], []).append(ratio)

    cashflow_by_key = {}
    for company_id, year, cfo, cfi, cff, row_id in cashflow_rows:
        cashflow_by_key[(company_id, year)] = (cfo, cfi, cff, row_id)

    summaries = []
    for company_id, company_name, sector in companies:
        candidates = ratios_by_company.get(company_id, [])
        complete = [
            row for row in candidates
            if row["roe"] is not None
            and row["roce"] is not None
            and row["net_profit_margin"] is not None
        ]
        selected_pool = complete or candidates
        latest = max(
            selected_pool,
            key=lambda row: (row["year_key"], row["id"]),
            default=None,
        )
        if latest is None:
            latest = {
                "fiscal_year": "N/A", "roe": None, "roce": None,
                "net_profit_margin": None, "debt_to_equity": None,
                "free_cash_flow": None, "quality_score": None,
                "cashflow_quality_score": None,
                "cashflow_quality_label": "Insufficient Data",
                "fcf_conversion_pct": None, "revenue_cagr_5yr": None,
                "revenue_cagr_5yr_flag": "INSUFFICIENT",
                "pat_cagr_5yr": None, "pat_cagr_5yr_flag": "INSUFFICIENT",
            }

        cashflow = cashflow_by_key.get(
            (company_id, latest["fiscal_year"])
        )
        if cashflow is None or any(value is None for value in cashflow[:3]):
            allocation = "Insufficient Data"
        else:
            allocation = capital_allocation_pattern(
                cashflow[0], cashflow[1], cashflow[2],
                latest["cashflow_quality_score"],
            )[-1]

        summary = {
            "ticker": company_id,
            "company_name": company_name,
            "sector": sector,
            "market_cap": market_caps.get(company_id, (None, None))[0],
            "pe_ratio": market_caps.get(company_id, (None, None))[1],
            "capital_allocation": allocation,
            **{
                key: value for key, value in latest.items()
                if key not in ("year_key", "id")
            },
        }
        summaries.append(summary)
    return summaries
