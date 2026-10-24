"""Page 01 — Home: Macro overview of the Nifty 100 universe."""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")))

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from src.dashboard.utils.db import get_companies, get_ratios, get_sectors
from src.screener.engine import get_screener_universe

st.markdown("## 📊 **Nifty 100 Market Overview**")
st.markdown("Macro benchmarks, valuation indicators, and industry distribution across India's top enterprises.")

# Sidebar Year Selector
years = [2024, 2023, 2022, 2021, 2020, 2019]
selected_year = st.sidebar.selectbox("📅 Select Financial Year", years, index=0)

# Fetch universe data
cos_df = get_companies()
sectors_df = get_sectors()

# Retrieve ratios for the selected year
year_str_mar = f"Mar {selected_year}"
year_str_sep = f"Sep {selected_year}"

conn_ratios = get_ratios()
year_mask = conn_ratios["year"].isin([year_str_mar, year_str_sep, str(selected_year)])
ratios_yr = conn_ratios[year_mask].copy()

# Fetch market cap multiples for that year
import sqlite3
from src.dashboard.utils.db import DB_PATH
conn = sqlite3.connect(DB_PATH)
mc_yr = pd.read_sql_query(
    "SELECT company_id, pe_ratio, pb_ratio, market_cap_crore FROM market_cap WHERE year = ?",
    conn,
    params=[selected_year]
)
conn.close()

merged = pd.merge(cos_df, ratios_yr, left_on="id", right_on="company_id", how="left")
merged = pd.merge(merged, mc_yr, left_on="company_id", right_on="company_id", how="left")

# KPI Calculations
total_cos = len(cos_df)
avg_roe = merged["return_on_equity_pct"].dropna().mean()
med_pe = merged["pe_ratio"].dropna().median()
med_de = merged["debt_to_equity"].dropna().median()
med_rev_cagr = merged["revenue_cagr_5yr"].dropna().median()

debt_free_count = (
    (merged["debt_to_equity"] <= 0.05) | 
    (merged["debt_to_equity"].fillna(0) == 0) | 
    (merged["icr_label"] == "Debt Free")
).sum()

# Display 6 KPI Tiles
k1, k2, k3, k4, k5, k6 = st.columns(6)
with k1:
    st.metric("Average ROE", f"{avg_roe:.2f}%" if pd.notna(avg_roe) else "N/A")
with k2:
    st.metric("Median P/E", f"{med_pe:.2f}x" if pd.notna(med_pe) else "N/A")
with k3:
    st.metric("Median D/E", f"{med_de:.2f}x" if pd.notna(med_de) else "N/A")
with k4:
    st.metric("Total Universe", f"{total_cos} Cos")
with k5:
    st.metric("Median Rev CAGR 5Y", f"{med_rev_cagr:.2f}%" if pd.notna(med_rev_cagr) else "N/A")
with k6:
    st.metric("Debt-Free Companies", f"{debt_free_count}")

st.markdown("---")

col_left, col_right = st.columns([1.1, 1.3])

with col_left:
    st.markdown("### 🍩 **Sector Breakdown (11 Sectors)**")
    sec_counts = cos_df["broad_sector"].value_counts().reset_index()
    sec_counts.columns = ["Sector", "Companies"]
    
    fig_donut = px.pie(
        sec_counts,
        names="Sector",
        values="Companies",
        hole=0.45,
        color_discrete_sequence=px.colors.qualitative.Prism
    )
    fig_donut.update_traces(
        textposition="inside",
        textinfo="percent+label",
        hoverinfo="label+value+percent",
        marker=dict(line=dict(color="#FFFFFF", width=2))
    )
    fig_donut.update_layout(
        margin=dict(t=20, b=20, l=10, r=10),
        showlegend=False,
        height=380
    )
    st.plotly_chart(fig_donut, use_container_width=True)

with col_right:
    st.markdown("### 🏆 **Top-5 Companies by Composite Quality Score**")
    univ_df = get_screener_universe()
    top5 = univ_df.sort_values(by="composite_quality_score", ascending=False).head(5)
    
    display_cols = [
        "company_id", "company_name", "broad_sector", 
        "composite_quality_score", "return_on_equity_pct", "debt_to_equity"
    ]
    renamed = {
        "company_id": "Ticker",
        "company_name": "Company Name",
        "broad_sector": "Sector",
        "composite_quality_score": "Quality Score",
        "return_on_equity_pct": "ROE (%)",
        "debt_to_equity": "D/E"
    }
    top5_disp = top5[display_cols].rename(columns=renamed).copy()
    top5_disp["Quality Score"] = top5_disp["Quality Score"].apply(lambda x: f"{x:.2f}" if pd.notna(x) else "N/A")
    top5_disp["ROE (%)"] = top5_disp["ROE (%)"].apply(lambda x: f"{x:.2f}%" if pd.notna(x) else "N/A")
    top5_disp["D/E"] = top5_disp["D/E"].apply(lambda x: f"{x:.2f}" if pd.notna(x) else "N/A")
    
    st.dataframe(top5_disp, use_container_width=True, hide_index=True)
    st.info("💡 Quality score balances Profitability (35%), Cash Quality (30%), Growth (20%), and Leverage (15%) using sector-relative P10/P90 winsorisation.")

