"""Industry Peer Groups API router for peer cohorts and percentiles."""

import os
import sqlite3
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException
import pandas as pd

router = APIRouter(prefix="/peers", tags=["Peers"])

DB_PATH_DEFAULT = "nifty100.db"


def _get_db():
    if not os.path.isfile(DB_PATH_DEFAULT):
        raise HTTPException(status_code=503, detail="Database not found")
    conn = sqlite3.connect(DB_PATH_DEFAULT)
    conn.row_factory = sqlite3.Row
    return conn


@router.get("", summary="List all 11 industry peer cohorts with benchmarks")
def list_peer_groups() -> Dict[str, Any]:
    """Retrieve all 11 industry peer groups with constituent counts and benchmark companies."""
    with _get_db() as conn:
        groups_raw = conn.execute(
            "SELECT pg.peer_group_name, pg.company_id, pg.is_benchmark, c.company_name "
            "FROM peer_groups pg "
            "JOIN companies c ON pg.company_id = c.id "
            "ORDER BY pg.peer_group_name, pg.is_benchmark DESC, pg.company_id"
        ).fetchall()

    groups_map: Dict[str, Dict[str, Any]] = {}
    for r in groups_raw:
        gname = r["peer_group_name"]
        if gname not in groups_map:
            groups_map[gname] = {
                "peer_group_name": gname,
                "benchmark_ticker": None,
                "benchmark_name": None,
                "members_count": 0,
                "members": [],
            }
        groups_map[gname]["members_count"] += 1
        groups_map[gname]["members"].append({
            "ticker": r["company_id"],
            "name": r["company_name"],
            "is_benchmark": bool(r["is_benchmark"]),
        })
        if r["is_benchmark"]:
            groups_map[gname]["benchmark_ticker"] = r["company_id"]
            groups_map[gname]["benchmark_name"] = r["company_name"]

    groups_list = list(groups_map.values())
    return {
        "count": len(groups_list),
        "note": "11 industry peer groups defined in the database for cohort percentile benchmarking.",
        "peer_groups": groups_list,
    }


@router.get("/{group_name}", summary="Peer group details and constituent percentile ranks")
def get_peer_group_detail(group_name: str) -> Dict[str, Any]:
    """Retrieve constituent companies and percentile rankings for a specific peer cohort."""
    with _get_db() as conn:
        members = conn.execute(
            "SELECT pg.peer_group_name, pg.company_id, pg.is_benchmark, c.company_name "
            "FROM peer_groups pg "
            "JOIN companies c ON pg.company_id = c.id "
            "WHERE LOWER(pg.peer_group_name) = LOWER(?) "
            "ORDER BY pg.is_benchmark DESC, pg.company_id",
            (group_name.strip(),),
        ).fetchall()

        if not members:
            # Check available
            avail = [r[0] for r in conn.execute("SELECT DISTINCT peer_group_name FROM peer_groups").fetchall()]
            raise HTTPException(
                status_code=404,
                detail=f"Peer group '{group_name}' not found. Available peer groups: {sorted(avail)}",
            )

        matched_name = members[0]["peer_group_name"]
        benchmark = next((m["company_id"] for m in members if m["is_benchmark"]), None)

        # Retrieve percentiles for this peer group
        percentiles = conn.execute(
            "SELECT company_id, metric, value, percentile_rank, year "
            "FROM peer_percentiles "
            "WHERE LOWER(peer_group_name) = LOWER(?) "
            "ORDER BY company_id, metric",
            (matched_name,),
        ).fetchall()

    return {
        "peer_group_name": matched_name,
        "benchmark_ticker": benchmark,
        "member_count": len(members),
        "members": [dict(m) for m in members],
        "percentile_records_count": len(percentiles),
        "percentiles": [dict(p) for p in percentiles],
    }


@router.get("/company/{ticker}", summary="Peer comparison for a specific company")
def get_company_peer_comparison(ticker: str) -> Dict[str, Any]:
    """Retrieve the peer group, peer companies, and percentile ranking for a specific company."""
    ticker_clean = ticker.upper()
    with _get_db() as conn:
        co = conn.execute("SELECT id, company_name FROM companies WHERE id = ?", (ticker_clean,)).fetchone()
        if not co:
            raise HTTPException(status_code=404, detail=f"Company '{ticker_clean}' not found")

        pg = conn.execute(
            "SELECT peer_group_name, is_benchmark FROM peer_groups WHERE company_id = ?",
            (ticker_clean,),
        ).fetchone()

        if not pg:
            raise HTTPException(
                status_code=404,
                detail=f"Company '{ticker_clean}' is not mapped to any of the 11 industry peer groups.",
            )

        group_name = pg["peer_group_name"]
        peers = conn.execute(
            "SELECT pg.company_id, pg.is_benchmark, c.company_name "
            "FROM peer_groups pg "
            "JOIN companies c ON pg.company_id = c.id "
            "WHERE pg.peer_group_name = ?",
            (group_name,),
        ).fetchall()

        percentiles = conn.execute(
            "SELECT metric, value, percentile_rank, year "
            "FROM peer_percentiles "
            "WHERE company_id = ? AND peer_group_name = ?",
            (ticker_clean, group_name),
        ).fetchall()

    return {
        "ticker": ticker_clean,
        "company_name": co["company_name"],
        "peer_group_name": group_name,
        "is_benchmark": bool(pg["is_benchmark"]),
        "peer_members": [dict(p) for p in peers],
        "percentiles": [dict(p) for p in percentiles],
    }

