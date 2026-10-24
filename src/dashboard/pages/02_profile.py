"""Page 02 — Company Profile: In-depth financial health and diagnostic report."""
import os
import sys
import re
from typing import Any

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st

current_dir = os.path.dirname(os.path.abspath(__file__))
root = current_dir
while root and not os.path.exists(os.path.join(root, "nifty100.db")):
    parent = os.path.dirname(root)
    if parent == root:
        break
    root = parent
if root not in sys.path:
    sys.path.insert(0, root)

from src.dashboard.utils.db import (
    get_companies,
    get_ratios,
    get_pl,
    get_bs,
    get_cf,
    get_prosandcons,
)

st.markdown("## 🏢 **Company Profile & Diagnostics**")

cos_df = get_companies()

# Format search options: "TCS — Tata Consultancy Services Ltd"
company_options = [f"{row['id']} — {row['company_name']}" for _, row in cos_df.iterrows()]
company_map = {opt: opt.split(" — ")[0] for opt in company_options}

# Autocomplete search
search_input = st.selectbox(
    "🔍 Search Company by Name or NSE Ticker",
    company_options,
    index=0,
    help="Type any company name or ticker to filter"
)

selected_ticker = company_map.get(search_input, "").strip().upper()

# Handle invalid ticker
if not selected_ticker or selected_ticker not in cos_df["id"].values:
    st.error("Ticker not found — please try another")
    st.stop()

# Fetch company profile row
co_info = cos_df[cos_df["id"] == selected_ticker].iloc[0]

# Display Header Details
st.markdown(f"### **{co_info['company_name']}** (`{co_info['id']}`)")
col_meta1, col_meta2, col_meta3 = st.columns([1, 1, 2])
with col_meta1:
    st.markdown(f"**Sector:** {co_info.get('broad_sector', 'N/A')}")
with col_meta2:
    st.markdown(f"**Sub-sector:** {co_info.get('sub_sector', 'N/A')}")
with col_meta3:
    if pd.notna(co_info.get("website")) and co_info.get("website"):
        st.markdown(f"🌐 [Company Website]({co_info['website']}) | [NSE Profile]({co_info.get('nse_profile', '#')})")

with st.expander("📖 **About Company**", expanded=False):
    st.write(co_info.get("about_company") or "No description available.")

st.markdown("---")

# Retrieve latest ratios
ratios_df = get_ratios(selected_ticker)
if ratios_df.empty:
    st.warning("Financial ratio data is currently unavailable for this company.")
    latest_r = {}
else:
    # Filter latest annual row (excluding TTM or half-years if full annual available)
    valid_annuals = ratios_df[ratios_df["year"] != "TTM"]
    if not valid_annuals.empty:
        latest_r = valid_annuals.iloc[-1].to_dict()
    else:
        latest_r = ratios_df.iloc[-1].to_dict()

# 6 KPI Tiles
k1, k2, k3, k4, k5, k6 = st.columns(6)

roe_val = latest_r.get("return_on_equity_pct")
roce_val = latest_r.get("return_on_capital_employed_pct")
npm_val = latest_r.get("net_profit_margin_pct")
de_val = latest_r.get("debt_to_equity")
rev_cagr_val = latest_r.get("revenue_cagr_5yr")
fcf_val = latest_r.get("free_cash_flow_cr")

with k1:
    st.metric("ROE", f"{roe_val:.2f}%" if pd.notna(roe_val) and roe_val is not None else "N/A")
with k2:
    st.metric("ROCE", f"{roce_val:.2f}%" if pd.notna(roce_val) and roce_val is not None else "N/A")
with k3:
    st.metric("Net Margin", f"{npm_val:.2f}%" if pd.notna(npm_val) and npm_val is not None else "N/A")
with k4:
    st.metric("Debt-to-Equity", f"{de_val:.2f}x" if pd.notna(de_val) and de_val is not None else "N/A")
with k5:
    st.metric("Rev CAGR 5Y", f"{rev_cagr_val:.2f}%" if pd.notna(rev_cagr_val) and rev_cagr_val is not None else "N/A")
with k6:
    st.metric("FCF Latest (Cr)", f"₹{fcf_val:,.1f}" if pd.notna(fcf_val) and fcf_val is not None else "N/A")

st.markdown("<br>", unsafe_allow_html=True)

# Fetch P&L and Balance Sheet for historical charts
pl_df = get_pl(selected_ticker)

# Helper to parse year for chronological sorting
def parse_year_sort(yr_str: Any) -> float:
    s = str(yr_str)
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

if not pl_df.empty:
    pl_clean = pl_df[pl_df["year"] != "TTM"].copy()
    pl_clean["sort_key"] = pl_clean["year"].apply(parse_year_sort)
    pl_clean = pl_clean.sort_values(by="sort_key").tail(10)  # Up to 10 historical years
else:
    pl_clean = pd.DataFrame()

# Dual Charts
c_left, c_right = st.columns(2)

with c_left:
    st.markdown("#### 📊 **10-Year Revenue & Net Profit History (₹ Cr)**")
    if pl_clean.empty or "sales" not in pl_clean.columns:
        st.info("Historical revenue/profit statements unavailable.")
    else:
        fig_bar = go.Figure()
        fig_bar.add_trace(go.Bar(
            x=pl_clean["year"],
            y=pl_clean["sales"],
            name="Revenue (Sales)",
            marker_color="#1B365D"
        ))
        fig_bar.add_trace(go.Bar(
            x=pl_clean["year"],
            y=pl_clean["net_profit"],
            name="Net Profit (PAT)",
            marker_color="#00A86B"
        ))
        fig_bar.update_layout(
            barmode="group",
            margin=dict(t=25, b=25, l=10, r=10),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            height=360,
            hovermode="x unified"
        )
        st.plotly_chart(fig_bar, use_container_width=True)

with c_right:
    st.markdown("#### 📈 **ROE & ROCE Return Trajectory (%)**")
    if ratios_df.empty or "return_on_equity_pct" not in ratios_df.columns:
        st.info("Historical profitability ratios unavailable.")
    else:
        r_clean = ratios_df[ratios_df["year"] != "TTM"].copy()
        r_clean["sort_key"] = r_clean["year"].apply(parse_year_sort)
        r_clean = r_clean.sort_values(by="sort_key").tail(10)

        fig_line = go.Figure()
        fig_line.add_trace(go.Scatter(
            x=r_clean["year"],
            y=r_clean["return_on_equity_pct"],
            name="ROE (%)",
            mode="lines+markers",
            line=dict(color="#0F4C81", width=3),
            marker=dict(size=7)
        ))
        fig_line.add_trace(go.Scatter(
            x=r_clean["year"],
            y=r_clean["return_on_capital_employed_pct"],
            name="ROCE (%)",
            mode="lines+markers",
            line=dict(color="#E65100", width=3, dash="dash"),
            marker=dict(size=7)
        ))
        fig_line.update_layout(
            margin=dict(t=25, b=25, l=10, r=10),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            height=360,
            hovermode="x unified"
        )
        st.plotly_chart(fig_line, use_container_width=True)

st.markdown("---")

# Pros and Cons Section
st.markdown("### ⚖️ **Company Pros & Cons Analysis**")

pnc_df = get_prosandcons(selected_ticker)
col_pro, col_con = st.columns(2)

with col_pro:
    st.markdown("##### 🟢 **Strengths & Positives (Pros)**")
    pros_list = pnc_df["pros"].dropna().tolist() if not pnc_df.empty else []
    # If empty or generic, synthesize key strengths from computed ratios
    if pros_list:
        for p in pros_list:
            st.markdown(f"- ✓ **{p}**")
    else:
        # Diagnostic fallbacks based on verified metrics
        strengths = []
        if roe_val and roe_val > 15:
            strengths.append(f"Strong return on equity of {roe_val:.1f}%.")
        if de_val is not None and de_val <= 0.1:
            strengths.append(f"Prudent balance sheet with low leverage (D/E of {de_val:.2f}x).")
        if fcf_val and fcf_val > 0:
            strengths.append(f"Positive annual Free Cash Flow generation (₹{fcf_val:,.0f} Cr).")
        if rev_cagr_val and rev_cagr_val > 10:
            strengths.append(f"Compounded 5-year revenue growth of {rev_cagr_val:.1f}% CAGR.")
        
        if strengths:
            for s in strengths:
                st.markdown(f"- ✓ {s}")
        else:
            st.info("No specific pros documented for this enterprise.")

with col_con:
    st.markdown("##### 🔴 **Risks & Concerns (Cons)**")
    cons_list = pnc_df["cons"].dropna().tolist() if not pnc_df.empty else []
    if cons_list:
        for c in cons_list:
            st.markdown(f"- ✗ **{c}**")
    else:
        risks = []
        if de_val and de_val > 2.0:
            risks.append(f"Elevated financial leverage with Debt-to-Equity at {de_val:.2f}x.")
        if roe_val and roe_val < 8.0:
            risks.append(f"Subdued Return on Equity of {roe_val:.1f}%.")
        if fcf_val and fcf_val < 0:
            risks.append(f"Negative annual Free Cash Flow (₹{fcf_val:,.0f} Cr).")
        if rev_cagr_val and rev_cagr_val < 5.0:
            risks.append(f"Modest 5-year top-line expansion ({rev_cagr_val:.1f}% CAGR).")
            
        if risks:
            for r in risks:
                st.markdown(f"- ✗ {r}")
        else:
            st.info("No critical balance sheet warnings identified.")

