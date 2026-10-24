"""Financial Screener API router supporting presets and custom multi-metric filters."""

import os
import sqlite3
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query
import pandas as pd

from src.screener.engine import (
    DEFAULT_CONFIG_PATH,
    apply_screener_filters,
    get_screener_universe,
    load_config,
)

router = APIRouter(prefix="/screener", tags=["Screener"])

DB_PATH_DEFAULT = "nifty100.db"

ALLOWED_SORT_COLUMNS = {
    "composite_quality_score",
    "return_on_equity_pct",
    "return_on_capital_employed_pct",
    "debt_to_equity",
    "revenue_cagr_5yr",
    "pat_cagr_5yr",
    "operating_profit_margin_pct",
    "net_profit_margin_pct",
    "free_cash_flow_cr",
    "market_cap_crore",
    "pe_ratio",
    "dividend_yield_pct",
}


def _get_screener_universe() -> pd.DataFrame:
    if not os.path.isfile(DB_PATH_DEFAULT):
        raise HTTPException(status_code=503, detail="Database not found")
    return get_screener_universe(DB_PATH_DEFAULT)


def _normalize_key(s: str) -> str:
    return s.lower().replace("_", "").replace("-", "").replace(" ", "").rstrip("s")


@router.get("/presets", summary="List available screener presets")
def get_screener_presets() -> Dict[str, Any]:
    """Retrieve all predefined screener presets from configuration."""
    try:
        config = load_config(DEFAULT_CONFIG_PATH)
        presets = config.get("presets", {})
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to load screener config: {str(e)}")

    preset_list = []
    for key, p in presets.items():
        preset_list.append({
            "key": key,
            "normalized_key": _normalize_key(key),
            "name": p.get("name", key),
            "description": p.get("description", ""),
            "criteria": {k: v for k, v in p.items() if k not in ("name", "description")},
        })

    return {"count": len(preset_list), "presets": preset_list}


@router.get("", summary="Execute screener by preset or custom criteria")
def run_screener(
    preset: Optional[str] = Query(None, description="Preset name (e.g. quality_compounders)"),
    roe_min: Optional[float] = Query(None, description="Minimum ROE %"),
    roce_min: Optional[float] = Query(None, description="Minimum ROCE %"),
    max_de: Optional[float] = Query(None, description="Maximum Debt-to-Equity"),
    fcf_min: Optional[float] = Query(None, description="Minimum Free Cash Flow (Cr)"),
    revenue_cagr_5yr_min: Optional[float] = Query(None, description="Minimum 5yr Revenue CAGR %"),
    pat_cagr_5yr_min: Optional[float] = Query(None, description="Minimum 5yr PAT CAGR %"),
    quality_score_min: Optional[float] = Query(None, description="Minimum Composite Quality Score (0-100)"),
    sector: Optional[str] = Query(None, description="Filter by broad sector"),
    sort_by: str = Query("composite_quality_score", description="Column to sort by"),
    sort_order: str = Query("desc", description="Sort order: 'asc' or 'desc'"),
    limit: int = Query(100, ge=1, le=100, description="Max companies to return"),
) -> Dict[str, Any]:
    """Filter the 92-company universe using presets or customized metric thresholds."""
    if sort_order.lower() not in ("asc", "desc"):
        raise HTTPException(status_code=400, detail="sort_order must be 'asc' or 'desc'")

    if sort_by not in ALLOWED_SORT_COLUMNS:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid sort_by column '{sort_by}'. Allowed columns: {sorted(ALLOWED_SORT_COLUMNS)}",
        )

    df = _get_screener_universe()

    filters: Dict[str, Any] = {}
    preset_used: Optional[str] = None

    if preset:
        config = load_config(DEFAULT_CONFIG_PATH)
        presets = config.get("presets", {})
        norm_input = _normalize_key(preset)
        matched_preset_key = None
        for k in presets.keys():
            if _normalize_key(k) == norm_input:
                matched_preset_key = k
                break

        if not matched_preset_key:
            raise HTTPException(
                status_code=400,
                detail=f"Unknown preset '{preset}'. Available presets: {list(presets.keys())}",
            )
        filters.update(presets[matched_preset_key])
        preset_used = matched_preset_key

    # Overlay explicit query parameters
    if roe_min is not None:
        filters["roe_min"] = roe_min
    if roce_min is not None:
        filters["roce_min"] = roce_min
    if max_de is not None:
        filters["debt_to_equity_max"] = max_de
    if fcf_min is not None:
        filters["fcf_min"] = fcf_min
    if revenue_cagr_5yr_min is not None:
        filters["revenue_cagr_5yr_min"] = revenue_cagr_5yr_min
    if pat_cagr_5yr_min is not None:
        filters["pat_cagr_5yr_min"] = pat_cagr_5yr_min

    filtered_df = apply_screener_filters(df, filters)

    # Sector filter
    if sector:
        filtered_df = filtered_df[
            filtered_df["broad_sector"].str.lower() == sector.strip().lower()
        ]

    # Quality score min filter
    if quality_score_min is not None:
        filtered_df = filtered_df[
            filtered_df["composite_quality_score"].notna()
            & (filtered_df["composite_quality_score"] >= quality_score_min)
        ]

    # Custom sort
    if sort_by in filtered_df.columns:
        filtered_df = filtered_df.sort_values(
            by=sort_by,
            ascending=(sort_order.lower() == "asc"),
            na_position="last",
        )

    total_matches = len(filtered_df)
    results = filtered_df.head(limit)

    # Convert to clean JSON records
    cols_to_return = [
        "company_id", "company_name", "broad_sector", "sub_sector", "year",
        "composite_quality_score", "return_on_equity_pct", "return_on_capital_employed_pct",
        "net_profit_margin_pct", "operating_profit_margin_pct", "debt_to_equity",
        "interest_coverage", "free_cash_flow_cr", "revenue_cagr_5yr", "pat_cagr_5yr",
        "pe_ratio", "pb_ratio", "dividend_yield_pct", "market_cap_crore",
    ]
    present_cols = [c for c in cols_to_return if c in results.columns]
    raw_records = results[present_cols].to_dict(orient="records")

    from src.api.utils import sanitize_records
    records = sanitize_records(raw_records)

    return {
        "preset_applied": preset_used,
        "filters_applied": filters,
        "total_matched": total_matches,
        "limit": limit,
        "count": len(records),
        "results": records,
    }
