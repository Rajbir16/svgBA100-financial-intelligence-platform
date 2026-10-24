"""Broad Sectors API router providing sector statistics and constituent listings."""

import os
import sqlite3
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException
import numpy as np
import pandas as pd

router = APIRouter(prefix="/sectors", tags=["Sectors"])

DB_PATH_DEFAULT = "nifty100.db"


def _get_db():
    if not os.path.isfile(DB_PATH_DEFAULT):
        raise HTTPException(status_code=503, detail="Database not found")
    conn = sqlite3.connect(DB_PATH_DEFAULT)
    conn.row_factory = sqlite3.Row
    return conn


@router.get("", summary="List all 10 authoritative broad sectors with summary stats")
def list_sectors() -> Dict[str, Any]:
    """Retrieve all authoritative broad sectors with median financial metrics and constituent counts.

    Note: The platform database contains exactly 10 authoritative broad sectors in the 'sectors' table,
    while industry peer analysis uses 11 peer groups in 'peer_groups'. This endpoint reports broad sectors.
    """
    with _get_db() as conn:
        df_sec = pd.read_sql(
            "SELECT c.id AS company_id, c.company_name, s.broad_sector, s.sub_sector, "
            "fr.return_on_equity_pct, fr.return_on_capital_employed_pct, "
            "fr.operating_profit_margin_pct, fr.debt_to_equity, fr.free_cash_flow_cr, "
            "fr.revenue_cagr_5yr, fr.pat_cagr_5yr, mc.market_cap_crore "
            "FROM sectors s "
            "JOIN companies c ON s.company_id = c.id "
            "LEFT JOIN financial_ratios fr ON c.id = fr.company_id AND fr.year = ("
            "    SELECT MAX(year) FROM financial_ratios WHERE company_id = c.id AND year != 'TTM'"
            ") "
            "LEFT JOIN market_cap mc ON c.id = mc.company_id AND mc.year = ("
            "    SELECT MAX(year) FROM market_cap WHERE company_id = c.id"
            ")",
            conn,
        )

    summary_list = []
    for sector_name, grp in df_sec.groupby("broad_sector"):
        summary_list.append({
            "broad_sector": sector_name,
            "company_count": len(grp),
            "total_market_cap_cr": round(float(grp["market_cap_crore"].sum()), 2) if grp["market_cap_crore"].notna().any() else 0.0,
            "median_roe_pct": round(float(grp["return_on_equity_pct"].median()), 2) if grp["return_on_equity_pct"].notna().any() else None,
            "median_roce_pct": round(float(grp["return_on_capital_employed_pct"].median()), 2) if grp["return_on_capital_employed_pct"].notna().any() else None,
            "median_opm_pct": round(float(grp["operating_profit_margin_pct"].median()), 2) if grp["operating_profit_margin_pct"].notna().any() else None,
            "median_debt_to_equity": round(float(grp["debt_to_equity"].median()), 2) if grp["debt_to_equity"].notna().any() else None,
            "median_revenue_cagr_5yr": round(float(grp["revenue_cagr_5yr"].median()), 2) if grp["revenue_cagr_5yr"].notna().any() else None,
            "companies": grp["company_id"].tolist(),
        })

    # Sort descending by company count
    summary_list.sort(key=lambda x: x["company_count"], reverse=True)

    return {
        "authoritative_broad_sectors_count": len(summary_list),
        "note": "Authoritative sectors table contains exactly 10 broad sectors covering all 92 companies. Industry peer cohorts contain 11 peer groups in /api/v1/peers.",
        "sectors": summary_list,
    }


@router.get("/{sector_name}", summary="Detailed sector statistics and constituents")
def get_sector_detail(sector_name: str) -> Dict[str, Any]:
    """Retrieve detailed KPIs, distributions, and constituent company list for a broad sector."""
    with _get_db() as conn:
        df = pd.read_sql(
            "SELECT c.id AS company_id, c.company_name, s.broad_sector, s.sub_sector, "
            "fr.return_on_equity_pct, fr.return_on_capital_employed_pct, "
            "fr.operating_profit_margin_pct, fr.net_profit_margin_pct, "
            "fr.debt_to_equity, fr.free_cash_flow_cr, fr.revenue_cagr_5yr, fr.pat_cagr_5yr, "
            "fr.composite_quality_score, mc.market_cap_crore "
            "FROM sectors s "
            "JOIN companies c ON s.company_id = c.id "
            "LEFT JOIN financial_ratios fr ON c.id = fr.company_id AND fr.year = ("
            "    SELECT MAX(year) FROM financial_ratios WHERE company_id = c.id AND year != 'TTM'"
            ") "
            "LEFT JOIN market_cap mc ON c.id = mc.company_id AND mc.year = ("
            "    SELECT MAX(year) FROM market_cap WHERE company_id = c.id"
            ") "
            "WHERE LOWER(s.broad_sector) = LOWER(?)",
            conn,
            params=(sector_name.strip(),),
        )

    if df.empty:
        raise HTTPException(
            status_code=404,
            detail=f"Sector '{sector_name}' not found. Valid broad sectors are: Communication Services, Consumer Discretionary, Consumer Staples, Energy, Financials, Healthcare, Industrials, Information Technology, Materials, Real Estate",
        )

    matched_name = df["broad_sector"].iloc[0]
    from src.api.utils import sanitize_records
    companies = sanitize_records(df.to_dict(orient="records"))

    return {
        "broad_sector": matched_name,
        "company_count": len(df),
        "metrics": {
            "median_roe_pct": round(float(df["return_on_equity_pct"].median()), 2) if df["return_on_equity_pct"].notna().any() else None,
            "median_roce_pct": round(float(df["return_on_capital_employed_pct"].median()), 2) if df["return_on_capital_employed_pct"].notna().any() else None,
            "median_opm_pct": round(float(df["operating_profit_margin_pct"].median()), 2) if df["operating_profit_margin_pct"].notna().any() else None,
            "median_debt_to_equity": round(float(df["debt_to_equity"].median()), 2) if df["debt_to_equity"].notna().any() else None,
            "median_revenue_cagr_5yr": round(float(df["revenue_cagr_5yr"].median()), 2) if df["revenue_cagr_5yr"].notna().any() else None,
            "total_market_cap_cr": round(float(df["market_cap_crore"].sum()), 2) if df["market_cap_crore"].notna().any() else 0.0,
        },
        "companies": companies,
    }
