"""Package final deliverables into output/final_deliverables/ and produce a manifest."""

import hashlib
import json
import os
import shutil
from datetime import datetime
import pandas as pd

DELIVERABLES = [
    # Database
    ("nifty100.db", "Relational database with 13 tables, strict FKs, and 92 companies"),
    # Sprint 6 Clustering & Stats
    ("output/cluster_labels.csv", "5-archetype K-Means cluster assignments for 92 companies"),
    ("output/outlier_report.csv", "Within-sector outlier report (|Z-score| > 3.0)"),
    ("output/portfolio_stats.csv", "Portfolio KPI distribution stats (P10..P90, mean, std)"),
    ("reports/elbow_plot.png", "K-Means elbow plot for k=2..10"),
    ("reports/correlation_heatmap.png", "Pearson correlation heatmap of 10 primary KPIs"),
    # Sprint 6 API & Performance
    ("docs/openapi.json", "OpenAPI 3.0 specification exported from FastAPI app"),
    ("docs/postman_collection.json", "Postman Collection v2.1.0 for RESTful API testing"),
    ("output/perf_notes.md", "Concurrent screener API and profile latency benchmarks"),
    ("reports/pytest_report.html", "Self-contained HTML test report for 179 regression tests"),
    # Sprint 6 Documentation
    ("docs/analyst_guide.pdf", "11-page publication-grade Analyst Operations Guide"),
    # Sprint 5 Reports & Intelligence
    ("reports/portfolio/portfolio_summary.pdf", "17-page portfolio summary PDF covering 92 companies"),
    ("output/cashflow_intelligence.xlsx", "Cash-flow intelligence workbook with 8-pattern taxonomy"),
    ("output/distress_alerts.csv", "Early warning distress alerts (negative CFO funded by CFF)"),
    ("output/capital_allocation_distribution.csv", "Distribution of companies across 8 capital allocation patterns"),
    ("output/pattern_changes.csv", "Annual transitions between adjacent capital allocation patterns"),
    ("output/skipped_tearsheets.csv", "Audit log of skipped tear sheets (JIOFIN with 2 observations)"),
    ("output/pros_cons_generated.csv", "Generated strengths and weaknesses across 92 companies"),
    ("output/pros_cons_unresolved.csv", "Documented unresolved companies (SBIN, SIEMENS)"),
    ("output/analysis_parsed.csv", "NLP-parsed CAGR and growth metrics"),
    ("output/cagr_cross_validation.csv", "Cross-validation of parsed CAGRs vs calculated CAGRs"),
    ("output/parse_failures.csv", "NLP extraction failure log and unmapped tickers"),
    # Sprints 3 & 4 Analytics
    ("output/valuation_summary.xlsx", "Valuation summary workbook with sector multiples"),
    ("output/valuation_flags.csv", "Valuation flags per company"),
    ("output/screener_output.xlsx", "Financial screener multi-preset output workbook"),
    ("output/peer_comparison.xlsx", "Peer cohort comparison workbook across 11 groups"),
]


def file_sha256(filepath: str) -> str:
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        while True:
            chunk = f.read(8192)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


def archive_deliverables(dest_dir: str = "output/final_deliverables"):
    os.makedirs(dest_dir, exist_ok=True)
    manifest_records = []

    for src_path, desc in DELIVERABLES:
        if not os.path.isfile(src_path):
            print(f"Warning: file not found: {src_path}")
            continue

        filename = os.path.basename(src_path)
        # Handle collision or nested folders
        if "reports" in src_path:
            sub = "reports"
        elif "docs" in src_path:
            sub = "docs"
        elif src_path.endswith(".db"):
            sub = "db"
        else:
            sub = "output"

        target_sub = os.path.join(dest_dir, sub)
        os.makedirs(target_sub, exist_ok=True)
        target_path = os.path.join(target_sub, filename)

        shutil.copy2(src_path, target_path)

        size = os.path.getsize(target_path)
        sha = file_sha256(target_path)

        manifest_records.append({
            "deliverable": filename,
            "category": sub,
            "original_path": src_path,
            "archive_path": target_path.replace("\\", "/"),
            "file_size_bytes": size,
            "sha256": sha,
            "description": desc,
            "timestamp": datetime.now().isoformat(),
        })

    # Save manifest CSV and JSON
    manifest_csv = os.path.join(dest_dir, "manifest.csv")
    manifest_json = os.path.join(dest_dir, "manifest.json")

    pd.DataFrame(manifest_records).to_csv(manifest_csv, index=False)
    with open(manifest_json, "w", encoding="utf-8") as f:
        json.dump(manifest_records, f, indent=2)

    print(f"Successfully archived {len(manifest_records)} deliverables to {dest_dir}")
    print(f"Manifest written to: {manifest_csv}")
    return manifest_records


if __name__ == "__main__":
    archive_deliverables()
