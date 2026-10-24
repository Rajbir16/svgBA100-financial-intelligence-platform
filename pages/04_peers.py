"""Page 04 — Peer Comparison: Industry Benchmarking and Radar Diagnostics."""

import os
import sys

current_dir = os.path.dirname(os.path.abspath(__file__))
root = current_dir
while root and not os.path.exists(os.path.join(root, "nifty100.db")):
    parent = os.path.dirname(root)
    if parent == root:
        break
    root = parent
if root not in sys.path:
    sys.path.insert(0, root)

import sqlite3
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from src.dashboard.utils.db import DB_PATH, get_peers
from src.analytics.peer import _get_latest_company_ratios

st.markdown("## ⚖️ **Industry Peer Benchmarking**")
st.markdown("Percentile distributions and 8-axis Plotly Scatterpolar diagnostic radar charts across 11 key institutional peer groups.")

# Predefined 11 peer groups
PEER_GROUPS = [
    "Automobiles",
    "Consumer Finance",
    "FMCG",
    "IT Services",
    "Life Insurance",
    "Oil & Gas",
    "Pharmaceuticals",
    "Power & Utilities",
    "Private Banks",
    "Public Sector Banks",
    "Steel",
]

# Fetch universe peer ratio data
@st.cache_data(ttl=600)
def _load_peer_dataset():
    conn = sqlite3.connect(DB_PATH)
    try:
        return _get_latest_company_ratios(conn)
    finally:
        conn.close()

peer_full_df = _load_peer_dataset()

# Top Controls: Peer Group Dropdown
selected_group = st.selectbox(
    "👥 Select Industry Peer Group",
    PEER_GROUPS,
    index=3  # Default to IT Services
)

group_data = peer_full_df[peer_full_df["peer_group_name"] == selected_group].copy()

if group_data.empty:
    st.warning(f"No company records found for peer group: {selected_group}")
    st.stop()

# Company selector within the selected peer group
company_opts = [f"{r['company_id']} — {r['company_name']}" for _, r in group_data.iterrows()]
co_map = {opt: opt.split(" — ")[0] for opt in company_opts}

selected_company_str = st.selectbox(
    "🎯 Select Company to Benchmark",
    company_opts,
    index=0
)
selected_ticker = co_map[selected_company_str]

# Define the 8 Metrics for Radar Chart
RADAR_METRICS = [
    ("ROE", "return_on_equity_pct", False),
    ("ROCE", "return_on_capital_employed_pct", False),
    ("NPM", "net_profit_margin_pct", False),
    ("D/E", "debt_to_equity", True),  # Inverted: lower debt is better
    ("FCF Score", "free_cash_flow_cr", False),
    ("PAT CAGR 5Y", "pat_cagr_5yr", False),
    ("Revenue CAGR 5Y", "revenue_cagr_5yr", False),
    ("Composite Score", "composite_quality_score", False),
]

def normalize_series(series: pd.Series, invert: bool = False) -> pd.Series:
    """Normalize values in a group to a 0-100 scale."""
    valid = series.dropna()
    if valid.empty:
        return pd.Series(50.0, index=series.index)
    v_min = valid.min()
    v_max = valid.max()
    if v_max == v_min:
        return pd.Series(50.0, index=series.index)
    
    if invert:
        # Lower raw value gets higher score
        scaled = (v_max - series) / (v_max - v_min) * 100.0
    else:
        scaled = (series - v_min) / (v_max - v_min) * 100.0
    return scaled.clip(0.0, 100.0)

# Calculate normalized scores for all companies in the group
norm_df = pd.DataFrame(index=group_data.index)
norm_df["company_id"] = group_data["company_id"]

for label, col, invert in RADAR_METRICS:
    if col in group_data.columns:
        if col == "composite_quality_score":
            # Already 0-100
            norm_df[label] = group_data[col].fillna(50.0).clip(0.0, 100.0)
        elif invert and selected_group in ("Private Banks", "Public Sector Banks", "Consumer Finance"):
            # Financials have different leverage structures; give benchmark 80.0
            norm_df[label] = 80.0
        else:
            norm_df[label] = normalize_series(group_data[col], invert=invert).fillna(50.0)
    else:
        norm_df[label] = 50.0

# Extract scores for selected company and group average
co_norm_row = norm_df[norm_df["company_id"] == selected_ticker].iloc[0]
co_scores = [co_norm_row[label] for label, _, _ in RADAR_METRICS]
avg_scores = [norm_df[label].mean() for label, _, _ in RADAR_METRICS]
categories = [label for label, _, _ in RADAR_METRICS]

# Close the radar loop
co_scores_closed = co_scores + [co_scores[0]]
avg_scores_closed = avg_scores + [avg_scores[0]]
categories_closed = categories + [categories[0]]

# Plot Scatterpolar Radar
fig_radar = go.Figure()

fig_radar.add_trace(go.Scatterpolar(
    r=co_scores_closed,
    theta=categories_closed,
    fill="toself",
    name=f"{selected_ticker} (Selected)",
    line=dict(color="#1B365D", width=3),
    fillcolor="rgba(27, 54, 93, 0.25)"
))

fig_radar.add_trace(go.Scatterpolar(
    r=avg_scores_closed,
    theta=categories_closed,
    fill="toself",
    name=f"{selected_group} Peer Average",
    line=dict(color="#E65100", width=2, dash="dash"),
    fillcolor="rgba(230, 81, 0, 0.10)"
))

fig_radar.update_layout(
    polar=dict(
        radialaxis=dict(
            visible=True,
            range=[0, 100],
            tickvals=[20, 40, 60, 80, 100],
            tickfont=dict(size=9, color="#6C757D")
        ),
        angularaxis=dict(
            tickfont=dict(size=11, color="#1B365D", family="Arial Black")
        )
    ),
    showlegend=True,
    legend=dict(orientation="h", yanchor="bottom", y=1.08, xanchor="center", x=0.5),
    height=480,
    margin=dict(t=50, b=30, l=40, r=40)
)

st.plotly_chart(fig_radar, use_container_width=True)

# Comparison Table Below Radar Chart
st.markdown(f"### 📊 **Peer Group Constituents & KPI Matrix ({selected_group})**")
st.caption(f"Comparing all {len(group_data)} companies in {selected_group}. Selected company ({selected_ticker}) is highlighted.")

table_cols = [
    "company_id", "company_name", "is_benchmark",
    "composite_quality_score", "return_on_equity_pct", "return_on_capital_employed_pct",
    "net_profit_margin_pct", "debt_to_equity", "free_cash_flow_cr",
    "pat_cagr_5yr", "revenue_cagr_5yr"
]

disp_cols = [c for c in table_cols if c in group_data.columns]
raw_table = group_data[disp_cols].copy()

# Sort by composite quality score descending
raw_table = raw_table.sort_values(by="composite_quality_score", ascending=False)

rename_map = {
    "company_id": "Ticker",
    "company_name": "Company Name",
    "is_benchmark": "Benchmark?",
    "composite_quality_score": "Quality Score",
    "return_on_equity_pct": "ROE (%)",
    "return_on_capital_employed_pct": "ROCE (%)",
    "net_profit_margin_pct": "NPM (%)",
    "debt_to_equity": "D/E",
    "free_cash_flow_cr": "FCF (₹ Cr)",
    "pat_cagr_5yr": "PAT CAGR 5Y (%)",
    "revenue_cagr_5yr": "Rev CAGR 5Y (%)",
}

formatted_table = raw_table.rename(columns=rename_map).copy()

if "Benchmark?" in formatted_table.columns:
    formatted_table["Benchmark?"] = formatted_table["Benchmark?"].apply(lambda x: "⭐ Benchmark" if x == 1 else "Peer")
if "Quality Score" in formatted_table.columns:
    formatted_table["Quality Score"] = formatted_table["Quality Score"].apply(lambda x: f"{x:.2f}" if pd.notna(x) else "N/A")
if "ROE (%)" in formatted_table.columns:
    formatted_table["ROE (%)"] = formatted_table["ROE (%)"].apply(lambda x: f"{x:.2f}%" if pd.notna(x) else "N/A")
if "ROCE (%)" in formatted_table.columns:
    formatted_table["ROCE (%)"] = formatted_table["ROCE (%)"].apply(lambda x: f"{x:.2f}%" if pd.notna(x) else "N/A")
if "NPM (%)" in formatted_table.columns:
    formatted_table["NPM (%)"] = formatted_table["NPM (%)"].apply(lambda x: f"{x:.2f}%" if pd.notna(x) else "N/A")
if "D/E" in formatted_table.columns:
    formatted_table["D/E"] = formatted_table["D/E"].apply(lambda x: f"{x:.2f}" if pd.notna(x) else "N/A")
if "FCF (₹ Cr)" in formatted_table.columns:
    formatted_table["FCF (₹ Cr)"] = formatted_table["FCF (₹ Cr)"].apply(lambda x: f"₹{x:,.0f}" if pd.notna(x) else "N/A")
if "PAT CAGR 5Y (%)" in formatted_table.columns:
    formatted_table["PAT CAGR 5Y (%)"] = formatted_table["PAT CAGR 5Y (%)"].apply(lambda x: f"{x:.2f}%" if pd.notna(x) else "N/A")
if "Rev CAGR 5Y (%)" in formatted_table.columns:
    formatted_table["Rev CAGR 5Y (%)"] = formatted_table["Rev CAGR 5Y (%)"].apply(lambda x: f"{x:.2f}%" if pd.notna(x) else "N/A")

# Apply styling to highlight the selected company
def highlight_selected(row):
    if row["Ticker"] == selected_ticker:
        return ["background-color: #E3F2FD; font-weight: bold; color: #0D47A1;"] * len(row)
    return [""] * len(row)

styled_table = formatted_table.style.apply(highlight_selected, axis=1)
st.dataframe(styled_table, use_container_width=True, hide_index=True)
