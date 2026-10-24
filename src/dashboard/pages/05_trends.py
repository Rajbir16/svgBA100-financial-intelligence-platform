"""Page 05 — Trend Analysis: Longitudinal Multi-Metric Performance Tracker."""

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

import re
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st
from src.dashboard.utils.db import get_companies, get_pl, get_ratios

st.markdown("## 📈 **Longitudinal Trend Analysis**")
st.markdown("Track up to 3 financial metrics across up to 10 historical fiscal years with automated Year-over-Year (YoY) percentage change annotations.")

cos_df = get_companies()
company_options = [f"{row['id']} — {row['company_name']}" for _, row in cos_df.iterrows()]
company_map = {opt: opt.split(" — ")[0] for opt in company_options}

col_sel, col_met = st.columns([1.2, 1.8])

with col_sel:
    selected_option = st.selectbox(
        "🔍 Select Company",
        company_options,
        index=0,
        help="Search by company ticker or name"
    )
    selected_ticker = company_map[selected_option]

AVAILABLE_METRICS = {
    "Revenue / Sales (₹ Cr)": ("pl", "sales", "₹ Cr"),
    "Net Profit / PAT (₹ Cr)": ("pl", "net_profit", "₹ Cr"),
    "Operating Profit (₹ Cr)": ("pl", "operating_profit", "₹ Cr"),
    "Free Cash Flow (₹ Cr)": ("ratios", "free_cash_flow_cr", "₹ Cr"),
    "Return on Equity (ROE %)": ("ratios", "return_on_equity_pct", "%"),
    "Return on Capital Employed (ROCE %)": ("ratios", "return_on_capital_employed_pct", "%"),
    "Net Profit Margin (NPM %)": ("ratios", "net_profit_margin_pct", "%"),
    "Operating Profit Margin (OPM %)": ("ratios", "operating_profit_margin_pct", "%"),
    "Debt-to-Equity (D/E)": ("ratios", "debt_to_equity", "x"),
    "Interest Coverage (ICR)": ("ratios", "interest_coverage", "x"),
    "Earnings Per Share (EPS ₹)": ("pl", "eps", "₹"),
}

with col_met:
    selected_metrics = st.multiselect(
        "📊 Select Metrics to Compare (Up to 3)",
        list(AVAILABLE_METRICS.keys()),
        default=["Revenue / Sales (₹ Cr)", "Net Profit / PAT (₹ Cr)"],
        max_selections=3,
        help="Choose up to 3 metrics to plot simultaneously."
    )

if not selected_metrics:
    st.info("Please select at least one metric to display trends.")
    st.stop()

# Helper for chronological fiscal year sorting
def parse_year_sort(yr_str: str) -> float:
    s = str(yr_str).strip()
    if "TTM" in s.upper():
        return 9999.0
    match = re.search(r"(\d{4})", s)
    if match:
        base = float(match.group(1))
        if "SEP" in s.upper():
            return base + 0.75
        elif "DEC" in s.upper():
            return base + 0.99
        return base + 0.25
    return 0.0

# Fetch datasets
pl_df = get_pl(selected_ticker)
ratios_df = get_ratios(selected_ticker)

# Clean datasets (exclude TTM for annual trend)
pl_clean = pl_df[pl_df["year"] != "TTM"].copy() if not pl_df.empty else pd.DataFrame()
r_clean = ratios_df[ratios_df["year"] != "TTM"].copy() if not ratios_df.empty else pd.DataFrame()

# Merge into unified historical annual dataframe
if not pl_clean.empty and not r_clean.empty:
    merged_trend = pd.merge(pl_clean, r_clean, on=["company_id", "year"], how="outer", suffixes=("_pl", "_r"))
elif not pl_clean.empty:
    merged_trend = pl_clean
else:
    merged_trend = r_clean

if merged_trend.empty:
    st.warning(f"No historical financial statements available for {selected_ticker}.")
    st.stop()

merged_trend["sort_key"] = merged_trend["year"].apply(parse_year_sort)
merged_trend = merged_trend.sort_values(by="sort_key").tail(10)  # Up to 10 annual periods

st.caption(f"Showing historical trends for **{selected_ticker}** over {len(merged_trend)} fiscal periods ({merged_trend['year'].iloc[0]} to {merged_trend['year'].iloc[-1]}).")

# Color palette for up to 3 lines
PALETTE = ["#1B365D", "#00A86B", "#E65100"]

# Check if metrics require dual axis (e.g. ₹ Cr vs %)
units = [AVAILABLE_METRICS[m][2] for m in selected_metrics]
distinct_units = list(dict.fromkeys(units))
use_secondary = len(distinct_units) > 1

if use_secondary:
    fig = make_subplots(specs=[[{"secondary_y": True}]])
else:
    fig = go.Figure()

for idx, m_name in enumerate(selected_metrics):
    source_type, col_name, unit = AVAILABLE_METRICS[m_name]
    
    # Check if column exists in merged dataframe
    target_col = None
    for cand in [col_name, f"{col_name}_pl", f"{col_name}_r"]:
        if cand in merged_trend.columns:
            target_col = cand
            break
            
    if not target_col:
        continue
        
    s_vals = merged_trend[target_col].astype(float)
    x_years = merged_trend["year"].tolist()
    
    # Calculate YoY annotations
    yoy_texts = []
    for i in range(len(s_vals)):
        curr = s_vals.iloc[i]
        if i == 0 or pd.isna(curr):
            yoy_texts.append("")
        else:
            prev = s_vals.iloc[i - 1]
            if pd.notna(prev) and prev != 0:
                pct = ((curr - prev) / abs(prev)) * 100.0
                yoy_texts.append(f"{pct:+.1f}%")
            else:
                yoy_texts.append("")
                
    color = PALETTE[idx % len(PALETTE)]
    is_sec = use_secondary and (unit == distinct_units[-1])
    
    trace = go.Scatter(
        x=x_years,
        y=s_vals,
        name=f"{m_name} ({unit})",
        mode="lines+markers+text",
        text=yoy_texts,
        textposition="top center",
        textfont=dict(size=10, color=color),
        line=dict(color=color, width=3),
        marker=dict(size=8, color=color),
        hovertemplate=f"<b>{m_name}</b>: %{{y:,.2f}} {unit}<br>Period: %{{x}}<extra></extra>"
    )
    
    if use_secondary:
        fig.add_trace(trace, secondary_y=is_sec)
    else:
        fig.add_trace(trace)

if use_secondary:
    fig.update_layout(
        yaxis_title=f"{distinct_units[0]}",
        yaxis2_title=f"{distinct_units[-1]}",
    )

fig.update_layout(
    title=f"<b>{selected_ticker} — Multi-Year Trend Trajectory</b>",
    margin=dict(t=40, b=30, l=20, r=20),
    legend=dict(orientation="h", yanchor="bottom", y=1.05, xanchor="center", x=0.5),
    height=480,
    hovermode="x unified",
    xaxis=dict(type="category")
)

st.plotly_chart(fig, use_container_width=True)

# Data Table of selected metrics below
st.markdown("#### 📋 **Historical Data Points & Annual Progression**")
display_df = merged_trend[["year"]].copy()
for m_name in selected_metrics:
    source_type, col_name, unit = AVAILABLE_METRICS[m_name]
    target_col = None
    for cand in [col_name, f"{col_name}_pl", f"{col_name}_r"]:
        if cand in merged_trend.columns:
            target_col = cand
            break
    if target_col:
        display_df[f"{m_name}"] = merged_trend[target_col].apply(
            lambda x: f"{x:,.2f} {unit}" if pd.notna(x) else "N/A"
        )

st.dataframe(display_df.set_index("year").T, use_container_width=True)
