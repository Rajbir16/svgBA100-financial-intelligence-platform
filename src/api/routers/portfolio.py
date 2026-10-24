"""Portfolio Statistics and Clustering Archetypes API router."""

import os
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query
import pandas as pd

router = APIRouter(prefix="/portfolio", tags=["Portfolio"])

PORTFOLIO_STATS_CSV = "output/portfolio_stats.csv"
CLUSTER_LABELS_CSV = "output/cluster_labels.csv"


@router.get("/stats", summary="Portfolio-wide KPI distribution statistics")
def get_portfolio_stats(
    metric: Optional[str] = Query(None, description="Filter by metric name"),
) -> Dict[str, Any]:
    """Retrieve portfolio percentile distribution statistics (P10, P25, P50, P75, P90, mean, std)."""
    if not os.path.isfile(PORTFOLIO_STATS_CSV):
        raise HTTPException(
            status_code=503,
            detail="Portfolio statistics file not found. Run clustering pipeline first.",
        )

    df = pd.read_csv(PORTFOLIO_STATS_CSV)
    if metric:
        df = df[df["metric"].str.lower() == metric.strip().lower()]
        if df.empty:
            raise HTTPException(
                status_code=404,
                detail=f"Metric '{metric}' not found in portfolio statistics.",
            )

    from src.api.utils import sanitize_records
    records = sanitize_records(df.to_dict(orient="records"))
    return {
        "count": len(records),
        "statistics": records,
    }


@router.get("/clusters", summary="K-Means company archetypes and cluster labels")
def get_portfolio_clusters(
    cluster_id: Optional[int] = Query(None, description="Filter by cluster ID (0-4)"),
    company_id: Optional[str] = Query(None, description="Filter by company ticker"),
) -> Dict[str, Any]:
    """Retrieve 5-archetype cluster assignments, descriptive provisional names, and centroid distances."""
    if not os.path.isfile(CLUSTER_LABELS_CSV):
        raise HTTPException(
            status_code=503,
            detail="Cluster labels file not found. Run clustering pipeline first.",
        )

    df = pd.read_csv(CLUSTER_LABELS_CSV)

    if cluster_id is not None:
        if cluster_id not in (0, 1, 2, 3, 4):
            raise HTTPException(status_code=400, detail="cluster_id must be an integer between 0 and 4")
        df = df[df["cluster_id"] == cluster_id]

    if company_id:
        df = df[df["company_id"].str.upper() == company_id.strip().upper()]
        if df.empty:
            raise HTTPException(
                status_code=404,
                detail=f"Company '{company_id}' not found in cluster assignments.",
            )

    cluster_counts = df["cluster_id"].value_counts().to_dict()
    from src.api.utils import sanitize_records
    records = sanitize_records(df.to_dict(orient="records"))

    return {
        "total_records": len(records),
        "cluster_distribution": cluster_counts,
        "note": "Archetype labels are provisional pending formal team-lead sign-off.",
        "assignments": records,
    }
