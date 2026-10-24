"""Clustering and Statistical Analysis Module — Sprint 6 (Days 36–37).

Performs K-Means clustering on 92 Nifty 100 companies using five financial features:
- return_on_equity_pct
- debt_to_equity
- revenue_cagr_5yr
- fcf_cagr_5yr
- operating_profit_margin_pct

Handles broad-sector median imputation with portfolio-median fallback,
StandardScaler normalization, elbow analysis (k=2..10), correlation heatmaps,
within-sector outlier detection (|Z| > 3), and portfolio summary percentiles.
"""

import os
import sqlite3
from typing import Any, Dict, List, Optional, Tuple

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler

DB_PATH_DEFAULT = "nifty100.db"
OUTPUT_DIR_DEFAULT = "output"
REPORTS_DIR_DEFAULT = "reports"

CLUSTERING_FEATURES = [
    "return_on_equity_pct",
    "debt_to_equity",
    "revenue_cagr_5yr",
    "fcf_cagr_5yr",
    "operating_profit_margin_pct",
]

PORTFOLIO_KPIS = [
    "return_on_equity_pct",
    "return_on_capital_employed_pct",
    "operating_profit_margin_pct",
    "net_profit_margin_pct",
    "debt_to_equity",
    "interest_coverage",
    "revenue_cagr_5yr",
    "pat_cagr_5yr",
    "cfo_quality_5yr",
    "fcf_conversion_pct",
]


def _parse_year_sort_key(year_str: str) -> Tuple[int, str]:
    """Parse 'Mar 2024' or 'Sep 2024' into a sorting tuple (2024, 'Mar')."""
    parts = str(year_str).strip().split()
    if len(parts) == 2 and parts[1].isdigit():
        return int(parts[1]), parts[0]
    return 0, str(year_str)


def load_clustering_dataset(
    db_path: str = DB_PATH_DEFAULT,
    ci_path: str = "output/cashflow_intelligence.xlsx",
) -> pd.DataFrame:
    """Load latest annual financial ratios and cash-flow intelligence for all 92 companies."""
    if not os.path.isfile(db_path):
        raise FileNotFoundError(f"Database not found: {db_path}")

    with sqlite3.connect(db_path) as conn:
        df_co = pd.read_sql(
            "SELECT c.id AS company_id, c.company_name, COALESCE(s.broad_sector, 'Unclassified') AS broad_sector "
            "FROM companies c "
            "LEFT JOIN sectors s ON c.id = s.company_id "
            "ORDER BY c.id",
            conn,
        )

        df_ratios = pd.read_sql(
            "SELECT company_id, year, "
            "return_on_equity_pct, return_on_capital_employed_pct, "
            "operating_profit_margin_pct, net_profit_margin_pct, "
            "debt_to_equity, interest_coverage, "
            "revenue_cagr_5yr, pat_cagr_5yr, cfo_quality_5yr, fcf_conversion_pct "
            "FROM financial_ratios "
            "WHERE year != 'TTM'",
            conn,
        )

    # Sort and pick latest annual record per company
    df_ratios["sort_key"] = df_ratios["year"].apply(_parse_year_sort_key)
    latest_ratios = (
        df_ratios.sort_values(["company_id", "sort_key"])
        .groupby("company_id")
        .last()
        .reset_index()
    )

    merged = pd.merge(df_co, latest_ratios, on="company_id", how="left")

    # Load fcf_cagr_5yr from cashflow_intelligence if available
    if os.path.isfile(ci_path):
        ci = pd.read_excel(ci_path)
        if "fcf_cagr_5yr" in ci.columns:
            merged = pd.merge(
                merged,
                ci[["company_id", "fcf_cagr_5yr"]],
                on="company_id",
                how="left",
            )
        else:
            merged["fcf_cagr_5yr"] = np.nan
    else:
        merged["fcf_cagr_5yr"] = np.nan

    return merged


def impute_features_sector_median(
    df: pd.DataFrame,
    features: List[str] = CLUSTERING_FEATURES,
    sector_col: str = "broad_sector",
) -> Tuple[pd.DataFrame, Dict[str, Dict[str, float]]]:
    """Impute missing values using broad-sector median, falling back to portfolio median.

    Returns:
        imputed_df: DataFrame with non-null feature values
        imputation_stats: Dictionary recording sector medians and fallbacks
    """
    imputed = df.copy()
    stats: Dict[str, Dict[str, float]] = {}

    for feat in features:
        stats[feat] = {}
        # Sector medians
        sec_medians = imputed.groupby(sector_col)[feat].median()
        port_median = imputed[feat].median()
        if pd.isna(port_median):
            port_median = 0.0

        stats[feat]["portfolio_median"] = float(port_median)

        # Apply sector median
        for sec, med_val in sec_medians.items():
            stats[feat][str(sec)] = float(med_val) if pd.notna(med_val) else float(port_median)

        imputed[feat] = imputed[feat].fillna(imputed[sector_col].map(sec_medians))
        # Fallback to portfolio median if entire sector was NaN
        imputed[feat] = imputed[feat].fillna(port_median)

    return imputed, stats


def run_clustering(
    df: pd.DataFrame,
    n_clusters: int = 5,
    random_state: int = 42,
    features: List[str] = CLUSTERING_FEATURES,
) -> Dict[str, Any]:
    """Run KMeans clustering with StandardScaler normalization.

    Returns:
        Dict containing cluster labels, model, scaler, centroids, profiles, and inertia.
    """
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(df[features].values)

    kmeans = KMeans(n_clusters=n_clusters, random_state=random_state)
    labels = kmeans.fit_predict(X_scaled)
    centers = kmeans.cluster_centers_

    # Calculate Euclidean distance from assigned centroid in scaled space
    distances = np.linalg.norm(X_scaled - centers[labels], axis=1)

    result_df = df.copy()
    result_df["cluster_id"] = labels
    result_df["distance_from_centroid"] = np.round(distances, 4)

    # Cluster profiles (unscaled mean & median)
    profiles = {}
    for cid in range(n_clusters):
        c_subset = result_df[result_df["cluster_id"] == cid]
        profiles[cid] = {
            "count": len(c_subset),
            "means": c_subset[features].mean().to_dict(),
            "medians": c_subset[features].median().to_dict(),
            "companies": c_subset["company_id"].tolist(),
        }

    # Descriptive cluster archetypes based on profile characteristics
    # Note: Clearly marked as provisional pending formal team-lead sign-off
    cluster_names = {}
    for cid, p in profiles.items():
        med_roe = p["medians"]["return_on_equity_pct"]
        med_de = p["medians"]["debt_to_equity"]
        med_rev = p["medians"]["revenue_cagr_5yr"]
        med_fcf = p["medians"]["fcf_cagr_5yr"]
        med_opm = p["medians"]["operating_profit_margin_pct"]
        mean_roe = p["means"]["return_on_equity_pct"]

        if mean_roe > 1000.0:
            cluster_names[cid] = "High Capital Turnover & Scale (Provisional)"
        elif med_de > 2.0 or (p["means"]["debt_to_equity"] > 4.0):
            cluster_names[cid] = "High-Leverage Financials & Utilities (Provisional)"
        elif p["means"]["fcf_cagr_5yr"] > 100.0:
            cluster_names[cid] = "Hyper FCF Outlier (Provisional)"
        elif med_opm > 50.0 or p["means"]["operating_profit_margin_pct"] > 60.0:
            cluster_names[cid] = "High-Margin Cash Generators (Provisional)"
        else:
            cluster_names[cid] = "Core Quality Compounders (Provisional)"

    result_df["cluster_name"] = result_df["cluster_id"].map(cluster_names)

    return {
        "df": result_df,
        "scaler": scaler,
        "model": kmeans,
        "profiles": profiles,
        "cluster_names": cluster_names,
        "inertia": float(kmeans.inertia_),
    }


def generate_elbow_plot(
    df: pd.DataFrame,
    k_range: range = range(2, 11),
    random_state: int = 42,
    features: List[str] = CLUSTERING_FEATURES,
    output_path: str = "reports/elbow_plot.png",
) -> Dict[int, float]:
    """Generate elbow plot (inertia for k=2..10) and save to PNG."""
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(df[features].values)

    inertias: Dict[int, float] = {}
    for k in k_range:
        km = KMeans(n_clusters=k, random_state=random_state)
        km.fit(X_scaled)
        inertias[k] = float(km.inertia_)

    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    fig, ax = plt.subplots(figsize=(8, 5))
    k_vals = list(inertias.keys())
    i_vals = list(inertias.values())

    ax.plot(k_vals, i_vals, "bo-", linewidth=2, markersize=7, label="Inertia")
    if 5 in inertias:
        ax.plot([5], [inertias[5]], "rs", markersize=10, label="Candidate k=5")
        ax.annotate(
            f"k=5 (Inertia: {inertias[5]:.1f})",
            xy=(5, inertias[5]),
            xytext=(5.5, inertias[5] * 1.15),
            arrowprops=dict(facecolor="black", shrink=0.05, width=1, headwidth=6),
            fontweight="bold",
            fontsize=9,
        )

    ax.set_title("K-Means Elbow Analysis for Archetype Clustering (k=2 to 10)", fontsize=11, fontweight="bold")
    ax.set_xlabel("Number of Clusters (k)", fontsize=10)
    ax.set_ylabel("Inertia (Within-Cluster Sum of Squares)", fontsize=10)
    ax.set_xticks(k_vals)
    ax.grid(True, linestyle="--", alpha=0.5)
    ax.legend(loc="upper right")
    fig.tight_layout()
    fig.savefig(output_path, dpi=200)
    plt.close(fig)

    return inertias


def generate_correlation_heatmap(
    df: pd.DataFrame,
    kpis: List[str] = PORTFOLIO_KPIS,
    output_path: str = "reports/correlation_heatmap.png",
) -> pd.DataFrame:
    """Generate Pearson correlation heatmap for selected KPIs and save to PNG."""
    available_kpis = [k for k in kpis if k in df.columns]
    corr_df = df[available_kpis].corr(method="pearson")

    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    fig, ax = plt.subplots(figsize=(10, 8))
    cax = ax.imshow(corr_df.values, cmap="coolwarm", vmin=-1.0, vmax=1.0)
    fig.colorbar(cax, ax=ax, fraction=0.046, pad=0.04)

    # Annotate labels and cells
    n = len(available_kpis)
    ax.set_xticks(range(n))
    ax.set_yticks(range(n))
    labels = [k.replace("_pct", " %").replace("_cr", " Cr").replace("_", " ") for k in available_kpis]
    ax.set_xticklabels(labels, rotation=45, ha="right", fontsize=8)
    ax.set_yticklabels(labels, fontsize=8)

    for i in range(n):
        for j in range(n):
            val = corr_df.iloc[i, j]
            text_color = "white" if abs(val) > 0.55 else "black"
            ax.text(j, i, f"{val:.2f}", ha="center", va="center", color=text_color, fontsize=7.5)

    ax.set_title("Pearson Correlation Heatmap of Primary Financial KPIs", fontsize=11, fontweight="bold", pad=12)
    fig.tight_layout()
    fig.savefig(output_path, dpi=200)
    plt.close(fig)

    return corr_df


def generate_outlier_report(
    df: pd.DataFrame,
    kpis: List[str] = PORTFOLIO_KPIS,
    sector_col: str = "broad_sector",
    z_threshold: float = 3.0,
    output_path: str = "output/outlier_report.csv",
) -> pd.DataFrame:
    """Flag within-sector outliers where |Z-score| > z_threshold."""
    records = []

    for kpi in kpis:
        if kpi not in df.columns:
            continue

        for sec, grp in df.groupby(sector_col):
            valid_vals = grp[kpi].dropna()
            if len(valid_vals) < 3:
                continue

            mean_val = valid_vals.mean()
            std_val = valid_vals.std(ddof=0)
            if std_val < 1e-6 or pd.isna(std_val):
                continue

            for _, row in grp.iterrows():
                val = row[kpi]
                if pd.notna(val):
                    z = (val - mean_val) / std_val
                    if abs(z) > z_threshold:
                        records.append({
                            "company_id": row["company_id"],
                            "broad_sector": sec,
                            "metric": kpi,
                            "value": round(float(val), 4),
                            "sector_mean": round(float(mean_val), 4),
                            "sector_std": round(float(std_val), 4),
                            "z_score": round(float(z), 4),
                        })

    outlier_df = pd.DataFrame(records)
    if outlier_df.empty:
        outlier_df = pd.DataFrame(
            columns=["company_id", "broad_sector", "metric", "value", "sector_mean", "sector_std", "z_score"]
        )
    else:
        outlier_df = outlier_df.sort_values(by="z_score", key=abs, ascending=False)

    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    outlier_df.to_csv(output_path, index=False)
    return outlier_df


def generate_portfolio_stats(
    df: pd.DataFrame,
    kpis: List[str] = PORTFOLIO_KPIS,
    output_path: str = "output/portfolio_stats.csv",
) -> pd.DataFrame:
    """Compute portfolio-wide summary distribution stats (P10..P90, mean, std) for primary KPIs."""
    records = []
    for kpi in kpis:
        if kpi not in df.columns:
            continue
        vals = df[kpi].dropna()
        if len(vals) == 0:
            continue

        records.append({
            "metric": kpi,
            "count": int(len(vals)),
            "mean": round(float(vals.mean()), 4),
            "std": round(float(vals.std(ddof=1)), 4) if len(vals) > 1 else 0.0,
            "p10": round(float(np.percentile(vals, 10)), 4),
            "p25": round(float(np.percentile(vals, 25)), 4),
            "p50": round(float(np.percentile(vals, 50)), 4),
            "p75": round(float(np.percentile(vals, 75)), 4),
            "p90": round(float(np.percentile(vals, 90)), 4),
        })

    stats_df = pd.DataFrame(records)
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    stats_df.to_csv(output_path, index=False)
    return stats_df


def execute_clustering_pipeline(
    db_path: str = DB_PATH_DEFAULT,
    ci_path: str = "output/cashflow_intelligence.xlsx",
    output_dir: str = OUTPUT_DIR_DEFAULT,
    reports_dir: str = REPORTS_DIR_DEFAULT,
) -> Dict[str, Any]:
    """Execute complete Days 36–37 statistical and clustering pipeline."""
    os.makedirs(output_dir, exist_ok=True)
    os.makedirs(reports_dir, exist_ok=True)

    raw_df = load_clustering_dataset(db_path=db_path, ci_path=ci_path)
    imputed_df, imp_stats = impute_features_sector_median(raw_df)

    clustering_res = run_clustering(imputed_df, n_clusters=5, random_state=42)
    clustered_df = clustering_res["df"]

    # Save cluster_labels.csv with exact required columns:
    # company_id, cluster_id, cluster_name, distance_from_centroid
    labels_csv_path = os.path.join(output_dir, "cluster_labels.csv")
    export_cols = ["company_id", "cluster_id", "cluster_name", "distance_from_centroid"]
    clustered_df[export_cols].sort_values("company_id").to_csv(labels_csv_path, index=False)

    # Generate elbow plot
    elbow_path = os.path.join(reports_dir, "elbow_plot.png")
    inertias = generate_elbow_plot(imputed_df, output_path=elbow_path)

    # Generate correlation heatmap
    heatmap_path = os.path.join(reports_dir, "correlation_heatmap.png")
    corr_df = generate_correlation_heatmap(raw_df, output_path=heatmap_path)

    # Generate outlier report (|Z| > 3)
    outlier_path = os.path.join(output_dir, "outlier_report.csv")
    outliers_df = generate_outlier_report(raw_df, output_path=outlier_path)

    # Generate portfolio stats (P10, P25, P50, P75, P90, mean, std)
    stats_path = os.path.join(output_dir, "portfolio_stats.csv")
    stats_df = generate_portfolio_stats(raw_df, output_path=stats_path)

    return {
        "cluster_labels_path": labels_csv_path,
        "elbow_plot_path": elbow_path,
        "correlation_heatmap_path": heatmap_path,
        "outlier_report_path": outlier_path,
        "portfolio_stats_path": stats_path,
        "total_companies": len(clustered_df),
        "cluster_counts": clustered_df["cluster_id"].value_counts().to_dict(),
        "profiles": clustering_res["profiles"],
        "cluster_names": clustering_res["cluster_names"],
        "outliers_found": len(outliers_df),
    }


if __name__ == "__main__":
    results = execute_clustering_pipeline()
    print("Clustering pipeline executed successfully.")
    print(f"Total companies: {results['total_companies']}")
    print(f"Cluster counts: {results['cluster_counts']}")
    print(f"Cluster names: {results['cluster_names']}")
    print(f"Outliers flagged: {results['outliers_found']}")
