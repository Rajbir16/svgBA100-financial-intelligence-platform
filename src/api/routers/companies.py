"""Companies router providing master info, financials, and PDF tearsheets."""

import os
import sqlite3
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse

router = APIRouter(prefix="/companies", tags=["Companies"])

DB_PATH_DEFAULT = "nifty100.db"


def _get_db():
    if not os.path.isfile(DB_PATH_DEFAULT):
        raise HTTPException(status_code=503, detail="Database not found")
    conn = sqlite3.connect(DB_PATH_DEFAULT)
    conn.row_factory = sqlite3.Row
    return conn


def _validate_ticker(ticker: str, conn: sqlite3.Connection) -> sqlite3.Row:
    row = conn.execute("SELECT * FROM companies WHERE id = ?", (ticker,)).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail=f"Company with ticker '{ticker}' not found")
    return row


@router.get("", summary="List all companies with sector and profile info")
def list_companies(
    sector: Optional[str] = Query(None, description="Filter by broad sector"),
    limit: int = Query(100, ge=1, le=100, description="Max records to return"),
    offset: int = Query(0, ge=0, description="Records offset"),
) -> Dict[str, Any]:
    """Retrieve universe companies with metadata, broad sector, and index weights."""
    with _get_db() as conn:
        query = (
            "SELECT c.id, c.company_name, s.broad_sector, s.sub_sector, "
            "s.market_cap_category, s.index_weight_pct, "
            "c.face_value, c.book_value, c.roce_percentage, c.roe_percentage, c.website "
            "FROM companies c "
            "LEFT JOIN sectors s ON c.id = s.company_id "
        )
        params: List[Any] = []
        if sector:
            query += "WHERE s.broad_sector = ? "
            params.append(sector)

        query += "ORDER BY c.id LIMIT ? OFFSET ?"
        params.extend([limit, offset])

        rows = conn.execute(query, params).fetchall()
        count_query = "SELECT COUNT(*) FROM companies c LEFT JOIN sectors s ON c.id = s.company_id "
        if sector:
            total = conn.execute(count_query + "WHERE s.broad_sector = ?", (sector,)).fetchone()[0]
        else:
            total = conn.execute(count_query).fetchone()[0]

    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "count": len(rows),
        "companies": [dict(r) for r in rows],
    }


@router.get("/{ticker}", summary="Detailed company profile")
def get_company_profile(ticker: str) -> Dict[str, Any]:
    """Retrieve full company profile including latest financial ratios and pros/cons."""
    ticker_clean = ticker.upper()
    with _get_db() as conn:
        co = _validate_ticker(ticker_clean, conn)
        sec = conn.execute("SELECT * FROM sectors WHERE company_id = ?", (ticker_clean,)).fetchone()

        # Latest ratios (exclude TTM)
        ratios = conn.execute(
            "SELECT * FROM financial_ratios WHERE company_id = ? AND year != 'TTM' "
            "ORDER BY id DESC LIMIT 1",
            (ticker_clean,),
        ).fetchone()

        # Pros and cons
        pc = conn.execute("SELECT pros, cons FROM prosandcons WHERE company_id = ?", (ticker_clean,)).fetchone()

    return {
        "ticker": ticker_clean,
        "master": dict(co),
        "sector": dict(sec) if sec else None,
        "latest_ratios": dict(ratios) if ratios else None,
        "pros_and_cons": dict(pc) if pc else {"pros": "", "cons": ""},
    }


@router.get("/{ticker}/pnl", summary="Historical Profit and Loss statements")
def get_company_pnl(
    ticker: str,
    annual_only: bool = Query(True, description="Exclude interim / TTM entries if True"),
) -> Dict[str, Any]:
    """Retrieve historical annual and TTM profit and loss statements."""
    ticker_clean = ticker.upper()
    with _get_db() as conn:
        _validate_ticker(ticker_clean, conn)
        query = "SELECT * FROM profitandloss WHERE company_id = ? "
        params: List[Any] = [ticker_clean]
        if annual_only:
            query += "AND year != 'TTM' "
        query += "ORDER BY id ASC"
        rows = conn.execute(query, params).fetchall()

    return {
        "ticker": ticker_clean,
        "count": len(rows),
        "records": [dict(r) for r in rows],
    }


@router.get("/{ticker}/balancesheet", summary="Historical Balance Sheet statements")
def get_company_balancesheet(
    ticker: str,
    annual_only: bool = Query(True, description="Exclude interim / TTM entries if True"),
) -> Dict[str, Any]:
    """Retrieve historical balance sheet statements."""
    ticker_clean = ticker.upper()
    with _get_db() as conn:
        _validate_ticker(ticker_clean, conn)
        query = "SELECT * FROM balancesheet WHERE company_id = ? "
        params: List[Any] = [ticker_clean]
        if annual_only:
            query += "AND year != 'TTM' "
        query += "ORDER BY id ASC"
        rows = conn.execute(query, params).fetchall()

    return {
        "ticker": ticker_clean,
        "count": len(rows),
        "records": [dict(r) for r in rows],
    }


@router.get("/{ticker}/cashflow", summary="Historical Cash Flow statements")
def get_company_cashflow(ticker: str) -> Dict[str, Any]:
    """Retrieve historical cash flow statements."""
    ticker_clean = ticker.upper()
    with _get_db() as conn:
        _validate_ticker(ticker_clean, conn)
        rows = conn.execute(
            "SELECT * FROM cashflow WHERE company_id = ? ORDER BY id ASC",
            (ticker_clean,),
        ).fetchall()

    return {
        "ticker": ticker_clean,
        "count": len(rows),
        "records": [dict(r) for r in rows],
    }


@router.get("/{ticker}/ratios", summary="Historical Financial Ratios")
def get_company_ratios(ticker: str) -> Dict[str, Any]:
    """Retrieve all historical financial ratio records for the company."""
    ticker_clean = ticker.upper()
    with _get_db() as conn:
        _validate_ticker(ticker_clean, conn)
        rows = conn.execute(
            "SELECT * FROM financial_ratios WHERE company_id = ? ORDER BY id ASC",
            (ticker_clean,),
        ).fetchall()

    return {
        "ticker": ticker_clean,
        "count": len(rows),
        "records": [dict(r) for r in rows],
    }


@router.get("/{ticker}/tearsheet", summary="Download company 2-page PDF tear sheet")
def get_company_tearsheet(ticker: str):
    """Download the official two-page PDF tear sheet for the specified company."""
    ticker_clean = ticker.upper()
    with _get_db() as conn:
        _validate_ticker(ticker_clean, conn)

    pdf_path = os.path.join("reports", "tearsheets", f"{ticker_clean}_tearsheet.pdf")
    if not os.path.isfile(pdf_path):
        # Check if company was skipped (e.g. JIOFIN due to <3 annual observations)
        raise HTTPException(
            status_code=404,
            detail=f"Tear sheet for '{ticker_clean}' not found. Company may have insufficient history (e.g., JIOFIN) or generation was skipped.",
        )

    return FileResponse(
        path=pdf_path,
        media_type="application/pdf",
        filename=f"{ticker_clean}_tearsheet.pdf",
    )


@router.get("/{ticker}/peers", summary="Company peer comparison and percentile ranks")
def get_company_peers_alias(ticker: str) -> Dict[str, Any]:
    """Retrieve peer group and percentiles for the company (alias to /peers/company/{ticker})."""
    from src.api.routers.peers import get_company_peer_comparison
    return get_company_peer_comparison(ticker)


@router.get("/{ticker}/valuation", summary="Company valuation history and summary")
def get_company_valuation_alias(ticker: str) -> Dict[str, Any]:
    """Retrieve valuation history and summary for the company (alias to /valuation/{ticker})."""
    from src.api.routers.valuation import get_company_valuation
    return get_company_valuation(ticker)


@router.get("/{ticker}/documents", summary="Company annual reports and filings")
def get_company_documents_alias(ticker: str) -> Dict[str, Any]:
    """Retrieve annual report filing links for the company (alias to /documents/{ticker})."""
    from src.api.routers.documents import get_company_documents
    return get_company_documents(ticker)
