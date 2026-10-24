"""Page 06 — Sector Analysis: Industry Bubble Matrices and Sector Medians."""

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
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from src.dashboard.utils.db import DB_PATH

st.markdown("## 🌐 **Sector Valuation & Profitability Dynamics**")
st.markdown("Multi-dimensional bubble visualization (Revenue vs. ROE vs. Market Cap) and cross-sector median KPI benchmarking.")

@st.cache_data(ttl=600)
def _load_sector_universe():
    conn = sqlite3.connect(DB_PATH)
    try:
        q = """
            WITH ranked_fr AS (
                SELECT fr.*,
                       ROW_NUMBER() OVER (
                           PARTITION BY fr.company_id
                           ORDER BY 
                               CASE 
                                   WHEN fr.company_id = 'SIEMENS' AND fr.year = 'Sep 2024' THEN 1
                                   WHEN fr.company_id != 'SIEMENS' AND fr.year = 'Mar 2024' THEN 1
                                   WHEN fr.year LIKE '%2024%' AND fr.year != 'TTM' THEN 2
                                   ELSE 3
                               END,
                               fr.id DESC
                       ) as rn
                FROM financial_ratios fr
                WHERE fr.sales_cr IS NOT NULL AND fr.year != 'TTM'
            )
            SELECT 
                c.id AS company_id,
                c.company_name,
                s.broad_sector,
                s.sub_sector,
                mc.market_cap_crore,
                mc.pe_ratio,
                mc.pb_ratio,
                r.sales_cr,
                r.return_on_equity_pct,
                r.return_on_capital_employed_pct,
                r.operating_profit_margin_pct,
                r.debt_to_equity
            FROM companies c
            JOIN sectors s ON c.id = s.company_id
            LEFT JOIN market_cap mc ON c.id = mc.company_id AND mc.year = 2024
            LEFT JOIN ranked_fr r ON c.id = r.company_id AND r.rn = 1
        """
        return pd.read_sql_query(q, conn)
    finally:
        conn.close()

sec_data = _load_sector_universe()

# Sector selection dropdown
all_sectors = sorted(sec_data["broad_sector"].dropna().unique().tolist())
sector_options = ["All Sectors (Full Universe)"] + all_sectors

selected_sector = st.selectbox(
    "🏢 Select Sector to Inspect",
    sector_options,
    index=0,
    help="Filter bubble chart by broad industrial sector or view aggregate market universe."
)

if selected_sector == "All Sectors (Full Universe)":
    plot_df = sec_data.copy()
else:
    plot_df = sec_data[sec_data["broad_sector"] == selected_sector].copy()

# Filter out rows missing vital coordinates
plot_df = plot_df[plot_df["sales_cr"].notna() & plot_df["return_on_equity_pct"].notna()].copy()
plot_df["market_cap_crore"] = plot_df["market_cap_crore"].fillna(5000.0).clip(lower=1000.0)

# Clamp extreme ROE outliers for visualization clarity if necessary
plot_df["display_roe"] = plot_df["return_on_equity_pct"].clip(-15.0, 75.0)

st.markdown(f"### 🎈 **Bubble Chart: Revenue vs. ROE (Size = Market Cap, Color = Sub-Sector)**")
st.caption(f"Displaying {len(plot_df)} companies. X-axis = Revenue (₹ Cr), Y-axis = ROE (%), Bubble Size = Market Cap (₹ Cr).")

fig_bubble = px.scatter(
    plot_df,
    x="sales_cr",
    y="display_roe",
    size="market_cap_crore",
    color="sub_sector",
    hover_name="company_name",
    hover_data={
        "company_id": True,
        "sales_cr": ":,.0f",
        "return_on_equity_pct": ":.2f",
        "market_cap_crore": ":,.0f",
        "display_roe": False,
        "sub_sector": True,
    },
    labels={
        "sales_cr": "Revenue / Sales (₹ Cr)",
        "display_roe": "Return on Equity (ROE %)",
        "sub_sector": "Sub-Sector",
        "market_cap_crore": "Market Cap (₹ Cr)",
    },
    size_max=50,
)

fig_bubble.update_layout(
    height=520,
    margin=dict(t=20, b=30, l=20, r=20),
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5),
    xaxis=dict(gridcolor="#E9ECEF"),
    yaxis=dict(gridcolor="#E9ECEF"),
)

st.plotly_chart(fig_bubble, use_container_width=True)

st.markdown("---")

# Sector Median KPI Bar Chart Below
st.markdown("### 📊 **Cross-Sector Median KPI Benchmarks**")

kpi_choice = st.selectbox(
    "📈 Select Sector Metric to Compare Across Industries",
    [
        "Return on Equity (ROE %)",
        "Return on Capital Employed (ROCE %)",
        "Operating Profit Margin (OPM %)",
        "P/E Multiple (x)",
        "Debt-to-Equity (D/E)",
    ],
    index=0
)

metric_col_map = {
    "Return on Equity (ROE %)": "return_on_equity_pct",
    "Return on Capital Employed (ROCE %)": "return_on_capital_employed_pct",
    "Operating Profit Margin (OPM %)": "operating_profit_margin_pct",
    "P/E Multiple (x)": "pe_ratio",
    "Debt-to-Equity (D/E)": "debt_to_equity",
}

target_col = metric_col_map[kpi_choice]

sector_medians = (
    sec_data.groupby("broad_sector")[target_col]
    .median()
    .reset_index()
    .sort_values(by=target_col, ascending=False)
)

fig_bar = px.bar(
    sector_medians,
    x="broad_sector",
    y=target_col,
    text=target_col,
    labels={"broad_sector": "Broad Sector", target_col: kpi_choice},
    color=target_col,
    color_continuous_scale="Blues",
)

fig_bar.update_traces(
    texttemplate="%{y:.2f}",
    textposition="outside",
    marker_line_color="#1B365D",
    marker_line_width=1,
)

fig_bar.update_layout(
    height=400,
    margin=dict(t=25, b=50, l=20, r=20),
    coloraxis_showscale=False,
    xaxis_tickangle=-30,
)

st.plotly_chart(fig_bar, use_container_width=True)
