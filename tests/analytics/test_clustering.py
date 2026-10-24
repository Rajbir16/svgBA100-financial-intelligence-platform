"""Unit and integration tests for Clustering and Statistical Analysis (Sprint 6 Days 36–37)."""

import os
import numpy as np
import pandas as pd
import pytest

from src.analytics.clustering import (
    CLUSTERING_FEATURES,
    PORTFOLIO_KPIS,
    execute_clustering_pipeline,
    generate_correlation_heatmap,
    generate_elbow_plot,
    generate_outlier_report,
    generate_portfolio_stats,
    impute_features_sector_median,
    load_clustering_dataset,
    run_clustering,
)


@pytest.fixture(scope="module")
def clustering_dataset():
    return load_clustering_dataset()


def test_load_clustering_dataset_universe(clustering_dataset):
    """Verify all 92 companies are loaded with valid sector classifications."""
    assert len(clustering_dataset) == 92
    assert "company_id" in clustering_dataset.columns
    assert "broad_sector" in clustering_dataset.columns
    assert clustering_dataset["company_id"].nunique() == 92


def test_impute_features_sector_median_no_nans(clustering_dataset):
    """Verify sector median imputation completely eliminates NaNs including fallback."""
    imputed_df, stats = impute_features_sector_median(clustering_dataset)
    for feat in CLUSTERING_FEATURES:
        assert imputed_df[feat].isna().sum() == 0, f"Feature {feat} has remaining NaNs"
    assert "return_on_equity_pct" in stats


def test_run_clustering_five_archetypes(clustering_dataset):
    """Verify KMeans produces exactly 5 clusters for 92 companies with reproducible labels."""
    imputed_df, _ = impute_features_sector_median(clustering_dataset)
    res = run_clustering(imputed_df, n_clusters=5, random_state=42)

    df_res = res["df"]
    assert len(df_res) == 92
    assert df_res["cluster_id"].nunique() == 5
    assert set(df_res["cluster_id"].unique()) == {0, 1, 2, 3, 4}
    assert "distance_from_centroid" in df_res.columns
    assert (df_res["distance_from_centroid"] >= 0).all()
    assert len(res["profiles"]) == 5
    for cid, name in res["cluster_names"].items():
        assert "Provisional" in name


def test_elbow_plot_generation(clustering_dataset, tmp_path):
    """Verify elbow plot calculates inertia for k=2..10 and generates PNG."""
    imputed_df, _ = impute_features_sector_median(clustering_dataset)
    plot_file = tmp_path / "test_elbow.png"
    inertias = generate_elbow_plot(imputed_df, k_range=range(2, 11), output_path=str(plot_file))

    assert len(inertias) == 9
    assert 5 in inertias
    assert inertias[2] > inertias[10]
    assert plot_file.is_file()
    assert plot_file.stat().st_size > 10000


def test_correlation_heatmap_generation(clustering_dataset, tmp_path):
    """Verify correlation heatmap produces a 10x10 matrix and valid PNG."""
    plot_file = tmp_path / "test_heatmap.png"
    corr = generate_correlation_heatmap(clustering_dataset, output_path=str(plot_file))

    assert corr.shape[0] == len(PORTFOLIO_KPIS)
    assert corr.shape[1] == len(PORTFOLIO_KPIS)
    assert np.allclose(np.diag(corr.values), 1.0)
    assert plot_file.is_file()
    assert plot_file.stat().st_size > 10000


def test_outlier_report_thresholds(clustering_dataset, tmp_path):
    """Verify within-sector outlier detection flags absolute Z-score > 3."""
    outlier_file = tmp_path / "test_outliers.csv"
    outliers = generate_outlier_report(clustering_dataset, z_threshold=3.0, output_path=str(outlier_file))

    if not outliers.empty:
        assert (outliers["z_score"].abs() > 3.0).all()
        assert set(outliers.columns) == {
            "company_id", "broad_sector", "metric", "value", "sector_mean", "sector_std", "z_score"
        }
    assert outlier_file.is_file()


def test_portfolio_stats_distributions(clustering_dataset, tmp_path):
    """Verify portfolio stats table produces P10..P90, mean, and std for all primary KPIs."""
    stats_file = tmp_path / "test_stats.csv"
    stats_df = generate_portfolio_stats(clustering_dataset, output_path=str(stats_file))

    assert len(stats_df) == len(PORTFOLIO_KPIS)
    for _, row in stats_df.iterrows():
        assert row["count"] > 0
        assert row["p10"] <= row["p50"] <= row["p90"]
    assert stats_file.is_file()


def test_complete_clustering_pipeline(tmp_path):
    """Verify end-to-end clustering pipeline generates all required artifacts."""
    out_dir = tmp_path / "output"
    rep_dir = tmp_path / "reports"
    res = execute_clustering_pipeline(output_dir=str(out_dir), reports_dir=str(rep_dir))

    assert res["total_companies"] == 92
    assert (out_dir / "cluster_labels.csv").is_file()
    assert (rep_dir / "elbow_plot.png").is_file()
    assert (rep_dir / "correlation_heatmap.png").is_file()
    assert (out_dir / "outlier_report.csv").is_file()
    assert (out_dir / "portfolio_stats.csv").is_file()

