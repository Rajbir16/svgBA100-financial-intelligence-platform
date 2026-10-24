"""Company Documents and Annual Reports API router."""

import os
import sqlite3
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query

router = APIRouter(prefix="/documents", tags=["Documents"])

DB_PATH_DEFAULT = "nifty100.db"


def _get_db():
    if not os.path.isfile(DB_PATH_DEFAULT):
        raise HTTPException(status_code=503, detail="Database not found")
    conn = sqlite3.connect(DB_PATH_DEFAULT)
    conn.row_factory = sqlite3.Row
    return conn


@router.get("", summary="List annual report filings across universe")
def list_documents(
    year: Optional[str] = Query(None, description="Filter by year (e.g. '2024')"),
    limit: int = Query(50, ge=1, le=100, description="Max filings to return"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
) -> Dict[str, Any]:
    """Retrieve annual report filing URLs across universe companies."""
    with _get_db() as conn:
        query = "SELECT d.id, d.company_id, c.company_name, d.year, d.annual_report FROM documents d JOIN companies c ON d.company_id = c.id "
        params: List[Any] = []
        if year:
            query += "WHERE d.year = ? "
            params.append(str(year).strip())

        query += "ORDER BY d.company_id, d.year DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])

        rows = conn.execute(query, params).fetchall()
        total = conn.execute("SELECT COUNT(*) FROM documents").fetchone()[0]

    return {
        "total_documents": total,
        "limit": limit,
        "offset": offset,
        "count": len(rows),
        "documents": [dict(r) for r in rows],
    }


@router.get("/{ticker}", summary="Retrieve annual reports for a specific company")
def get_company_documents(ticker: str) -> Dict[str, Any]:
    """Retrieve all official annual report links for a given company ticker."""
    ticker_clean = ticker.upper()
    with _get_db() as conn:
        co = conn.execute("SELECT id, company_name FROM companies WHERE id = ?", (ticker_clean,)).fetchone()
        if not co:
            raise HTTPException(status_code=404, detail=f"Company '{ticker_clean}' not found")

        docs = conn.execute(
            "SELECT year, annual_report FROM documents WHERE company_id = ? ORDER BY year DESC",
            (ticker_clean,),
        ).fetchall()

    return {
        "ticker": ticker_clean,
        "company_name": co["company_name"],
        "count": len(docs),
        "annual_reports": [dict(d) for d in docs],
    }

