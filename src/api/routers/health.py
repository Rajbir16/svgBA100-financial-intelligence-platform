"""Health check and database status router."""

import os
import sqlite3
from typing import Any, Dict

from fastapi import APIRouter, HTTPException

router = APIRouter(prefix="", tags=["Health"])

DB_PATH_DEFAULT = "nifty100.db"


def get_db_connection(db_path: str = DB_PATH_DEFAULT) -> sqlite3.Connection:
    if not os.path.isfile(db_path):
        raise HTTPException(status_code=503, detail=f"Database file not found: {db_path}")
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


@router.get("/health", summary="API and database health check")
def health_check() -> Dict[str, Any]:
    """Check API status and connectivity to the underlying SQLite database."""
    db_status = "connected"
    try:
        with get_db_connection() as conn:
            conn.execute("SELECT 1").fetchone()
    except Exception as e:
        db_status = f"error: {str(e)}"

    return {
        "status": "healthy" if db_status == "connected" else "degraded",
        "version": "1.0.0",
        "database": db_status,
        "database_path": DB_PATH_DEFAULT,
    }


@router.get("/health/counts", summary="Database row counts across all primary tables")
def table_row_counts() -> Dict[str, Any]:
    """Retrieve row counts across all tables in the SQLite database."""
    tables = [
        "companies",
        "sectors",
        "market_cap",
        "stock_prices",
        "financial_ratios",
        "balancesheet",
        "profitandloss",
        "cashflow",
        "peer_groups",
        "analysis",
        "prosandcons",
        "documents",
        "peer_percentiles",
    ]
    counts: Dict[str, int] = {}
    with get_db_connection() as conn:
        for tbl in tables:
            try:
                row = conn.execute(f"SELECT COUNT(*) FROM {tbl}").fetchone()
                counts[tbl] = row[0] if row else 0
            except Exception:
                counts[tbl] = 0

    return {
        "database": DB_PATH_DEFAULT,
        "tables": counts,
        "total_tables": len(tables),
    }

