"""Valuation and Market Capitalization API router."""

import os
import sqlite3
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query
import pandas as pd

from src.api.utils import sanitize_json_value, sanitize_records

router = APIRouter(prefix="/valuation", tags=["Valuation"])

DB_PATH_DEFAULT = "nifty100.db"
VALUATION_EXCEL = "output/valuation_summary.xlsx"


def _get_db():
    if not os.path.isfile(DB_PATH_DEFAULT):
        raise HTTPException(status_code=503, detail="Database not found")
    conn = sqlite3.connect(DB_PATH_DEFAULT)
    conn.row_factory = sqlite3.Row
    return conn


@router.get("/summary", summary="Universe valuation summary and valuation flags")
def get_valuation_summary(
    sector: Optional[str] = Query(None, description="Filter by sector"),
    flag: Optional[str] = Query(None, description="Filter by valuation flag (e.g. OVERVALUED, UNDERVALUED, FAIR)"),
) -> Dict[str, Any]:
    """Retrieve universe valuation summary containing P/E, P/B, EV/EBITDA, and sector-relative flags."""
    if not os.path.isfile(VALUATION_EXCEL):
        # Fallback to latest market_cap from database
        with _get_db() as conn:
            df = pd.read_sql(
                "SELECT mc.company_id, c.company_name, s.broad_sector AS sector, "
                "mc.pe_ratio AS [P/E], mc.pb_ratio AS [P/B], mc.ev_ebitda AS [EV/EBITDA], "
                "mc.dividend_yield_pct "
                "FROM market_cap mc "
                "JOIN companies c ON mc.company_id = c.id "
                "LEFT JOIN sectors s ON mc.company_id = s.company_id "
                "WHERE mc.year = (SELECT MAX(year) FROM market_cap WHERE company_id = mc.company_id)",
                conn,
            )
            df["flag"] = "FAIR"
    else:
        df = pd.read_excel(VALUATION_EXCEL)

    if sector:
        df = df[df["sector"].astype(str).str.lower() == sector.strip().lower()]

    if flag:
        df = df[df["flag"].astype(str).str.upper() == flag.strip().upper()]

    from src.api.utils import sanitize_records, sanitize_json_value
    records = sanitize_records(df.to_dict(orient="records"))

    return {
        "count": len(records),
        "valuation_summary": records,
    }


@router.get("/{ticker}", summary="Historical valuation and market cap series for a company")
def get_company_valuation(ticker: str) -> Dict[str, Any]:
    """Retrieve historical market capitalization, P/E, P/B, EV/EBITDA, and dividend yield."""
    ticker_clean = ticker.upper()
    with _get_db() as conn:
        co = conn.execute("SELECT id, company_name FROM companies WHERE id = ?", (ticker_clean,)).fetchone()
        if not co:
            raise HTTPException(status_code=404, detail=f"Company '{ticker_clean}' not found")

        history = conn.execute(
            "SELECT year, market_cap_crore, enterprise_value_crore, pe_ratio, pb_ratio, "
            "ev_ebitda, dividend_yield_pct "
            "FROM market_cap WHERE company_id = ? ORDER BY year ASC",
            (ticker_clean,),
        ).fetchall()

    summary_record = None
    if os.path.isfile(VALUATION_EXCEL):
        df_summary = pd.read_excel(VALUATION_EXCEL)
        match = df_summary[df_summary["company_id"] == ticker_clean]
        if not match.empty:
            summary_record = sanitize_json_value(match.iloc[0].to_dict())

    return {
        "ticker": ticker_clean,
        "company_name": co["company_name"],
        "summary": summary_record,
        "history_count": len(history),
        "history": [dict(r) for r in history],
    }
