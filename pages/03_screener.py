"""Page 03 — Financial Screener: Parametric multi-criteria equity screening."""

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

import pandas as pd
import streamlit as st
from src.dashboard.utils.db import DB_PATH
from src.screener.engine import (
    apply_screener_filters,
    get_screener_universe,
    load_config,
)

st.markdown("## 🔍 **Institutional Equity Screener**")
st.markdown("Filter the Nifty 100 universe using financial ratios, growth rates, valuation multiples, and institutional presets.")

# Load configuration and cached screener universe
config = load_config()
presets = config.get("presets", {})

@st.cache_data(ttl=600)
def _get_cached_universe():
    return get_screener_universe(DB_PATH)

universe_df = _get_cached_universe()

# Session state initialization for filter values
preset_names = [
    "Custom Filters",
    "Quality Compounder",
    "Value Pick",
    "Growth Accelerator",
    "Dividend Champion",
    "Debt-Free Blue Chip",
    "Turnaround Watch",
]

st.markdown("### ⚡ **Institutional Strategy Presets**")
preset_cols = st.columns(len(preset_names))

selected_preset = st.session_state.get("screener_preset", "Custom Filters")

for i, p_name in enumerate(preset_names):
    if preset_cols[i].button(p_name, key=f"btn_{p_name}", use_container_width=True):
        st.session_state["screener_preset"] = p_name
        selected_preset = p_name

if selected_preset != "Custom Filters":
    preset_info = presets.get(selected_preset, {})
    desc = preset_info.get("description", "")
    st.info(f"🎯 **Active Preset: {selected_preset}** — {desc}")

# Determine default/active filter parameters based on active preset
curr_preset = presets.get(selected_preset, {}) if selected_preset != "Custom Filters" else {}

with st.expander("🛠️ **Parametric Screening Filters (10 Metrics)**", expanded=(selected_preset == "Custom Filters")):
    f_col1, f_col2 = st.columns(2)
    
    with f_col1:
        roe_val = curr_preset.get("roe_min")
        roe_min = st.slider(
            "Minimum Return on Equity (ROE %)",
            min_value=-10.0, max_value=60.0,
            value=float(roe_val) if roe_val is not None else -10.0,
            step=1.0,
            help="Filters for companies generating higher net income per unit of shareholders' equity."
        )
        
        de_val = curr_preset.get("debt_to_equity_max")
        de_max = st.slider(
            "Maximum Debt-to-Equity (D/E)",
            min_value=0.0, max_value=10.0,
            value=float(de_val) if de_val is not None else 10.0,
            step=0.1,
            help="Exempts Financials sector automatically per institutional standards."
        )
        
        fcf_val = curr_preset.get("fcf_min")
        fcf_min = st.slider(
            "Minimum Free Cash Flow (₹ Cr)",
            min_value=-5000.0, max_value=25000.0,
            value=float(fcf_val) if fcf_val is not None else -5000.0,
            step=500.0,
            help="Positive operating cash flow minus capital expenditures."
        )
        
        rev_cagr_val = curr_preset.get("revenue_cagr_5yr_min")
        rev_cagr_min = st.slider(
            "Minimum Revenue CAGR 5Y (%)",
            min_value=-10.0, max_value=40.0,
            value=float(rev_cagr_val) if rev_cagr_val is not None else -10.0,
            step=1.0
        )
        
        pat_cagr_val = curr_preset.get("pat_cagr_5yr_min")
        pat_cagr_min = st.slider(
            "Minimum PAT CAGR 5Y (%)",
            min_value=-25.0, max_value=60.0,
            value=float(pat_cagr_val) if pat_cagr_val is not None else -25.0,
            step=1.0
        )

    with f_col2:
        opm_val = curr_preset.get("opm_min")
        opm_min = st.slider(
            "Minimum Operating Profit Margin (OPM %)",
            min_value=-10.0, max_value=60.0,
            value=float(opm_val) if opm_val is not None else -10.0,
            step=1.0
        )
        
        pe_val = curr_preset.get("pe_max")
        pe_max = st.slider(
            "Maximum P/E Ratio (x)",
            min_value=5.0, max_value=120.0,
            value=float(pe_val) if pe_val is not None else 120.0,
            step=1.0
        )
        
        pb_val = curr_preset.get("pb_max")
        pb_max = st.slider(
            "Maximum P/B Ratio (x)",
            min_value=0.5, max_value=25.0,
            value=float(pb_val) if pb_val is not None else 25.0,
            step=0.5
        )
        
        div_val = curr_preset.get("dividend_yield_min")
        div_min = st.slider(
            "Minimum Dividend Yield (%)",
            min_value=0.0, max_value=6.0,
            value=float(div_val) if div_val is not None else 0.0,
            step=0.25
        )
        
        icr_val = curr_preset.get("icr_min")
        icr_min = st.slider(
            "Minimum Interest Coverage (ICR x)",
            min_value=0.0, max_value=50.0,
            value=float(icr_val) if icr_val is not None else 0.0,
            step=1.0,
            help="Debt-free companies automatically pass with infinite coverage."
        )

# Construct active filter dictionary
active_filters = {}
if roe_min > -10.0:
    active_filters["roe_min"] = roe_min
if de_max < 10.0:
    active_filters["debt_to_equity_max"] = de_max
if fcf_min > -5000.0:
    active_filters["fcf_min"] = fcf_min
if rev_cagr_min > -10.0:
    active_filters["revenue_cagr_5yr_min"] = rev_cagr_min
if pat_cagr_min > -25.0:
    active_filters["pat_cagr_5yr_min"] = pat_cagr_min
if opm_min > -10.0:
    active_filters["opm_min"] = opm_min
if pe_max < 120.0:
    active_filters["pe_max"] = pe_max
if pb_max < 25.0:
    active_filters["pb_max"] = pb_max
if div_min > 0.0:
    active_filters["dividend_yield_min"] = div_min
if icr_min > 0.0:
    active_filters["icr_min"] = icr_min

# If a preset includes additional rules like sales_min or de_declining_yoy, carry them over
if selected_preset != "Custom Filters":
    for k, v in curr_preset.items():
        if k not in active_filters and k not in ("description", "name"):
            active_filters[k] = v

filtered_df = apply_screener_filters(universe_df, active_filters)

# Display Results Header
match_count = len(filtered_df)
st.markdown("---")
col_count, col_btn = st.columns([3, 1])

with col_count:
    st.markdown(f"### 📋 **{match_count} companies match your filters** (out of {len(universe_df)})")

# Desired presentation columns
display_columns = [
    "company_id",
    "company_name",
    "broad_sector",
    "composite_quality_score",
    "return_on_equity_pct",
    "debt_to_equity",
    "free_cash_flow_cr",
    "revenue_cagr_5yr",
    "pat_cagr_5yr",
    "operating_profit_margin_pct",
    "pe_ratio",
    "pb_ratio",
    "dividend_yield_pct",
    "interest_coverage",
]

col_rename = {
    "company_id": "Ticker",
    "company_name": "Company Name",
    "broad_sector": "Sector",
    "composite_quality_score": "Quality Score",
    "return_on_equity_pct": "ROE (%)",
    "debt_to_equity": "D/E",
    "free_cash_flow_cr": "FCF (₹ Cr)",
    "revenue_cagr_5yr": "Rev CAGR 5Y (%)",
    "pat_cagr_5yr": "PAT CAGR 5Y (%)",
    "operating_profit_margin_pct": "OPM (%)",
    "pe_ratio": "P/E",
    "pb_ratio": "P/B",
    "dividend_yield_pct": "Div Yield (%)",
    "interest_coverage": "ICR",
}

if filtered_df.empty:
    st.warning("⚠️ No companies matched your active filter criteria. Try relaxing slider constraints.")
else:
    # Sort by composite quality score descending by default
    res_sorted = filtered_df.sort_values(by="composite_quality_score", ascending=False)
    available_cols = [c for c in display_columns if c in res_sorted.columns]
    table_df = res_sorted[available_cols].rename(columns=col_rename).copy()

    # Format numbers for clean presentation
    if "Quality Score" in table_df.columns:
        table_df["Quality Score"] = table_df["Quality Score"].apply(lambda x: f"{x:.2f}" if pd.notna(x) else "N/A")
    if "ROE (%)" in table_df.columns:
        table_df["ROE (%)"] = table_df["ROE (%)"].apply(lambda x: f"{x:.2f}%" if pd.notna(x) else "N/A")
    if "D/E" in table_df.columns:
        table_df["D/E"] = table_df["D/E"].apply(lambda x: f"{x:.2f}" if pd.notna(x) else "N/A")
    if "FCF (₹ Cr)" in table_df.columns:
        table_df["FCF (₹ Cr)"] = table_df["FCF (₹ Cr)"].apply(lambda x: f"₹{x:,.0f}" if pd.notna(x) else "N/A")
    if "Rev CAGR 5Y (%)" in table_df.columns:
        table_df["Rev CAGR 5Y (%)"] = table_df["Rev CAGR 5Y (%)"].apply(lambda x: f"{x:.2f}%" if pd.notna(x) else "N/A")
    if "PAT CAGR 5Y (%)" in table_df.columns:
        table_df["PAT CAGR 5Y (%)"] = table_df["PAT CAGR 5Y (%)"].apply(lambda x: f"{x:.2f}%" if pd.notna(x) else "N/A")
    if "OPM (%)" in table_df.columns:
        table_df["OPM (%)"] = table_df["OPM (%)"].apply(lambda x: f"{x:.2f}%" if pd.notna(x) else "N/A")
    if "P/E" in table_df.columns:
        table_df["P/E"] = table_df["P/E"].apply(lambda x: f"{x:.2f}x" if pd.notna(x) else "N/A")
    if "P/B" in table_df.columns:
        table_df["P/B"] = table_df["P/B"].apply(lambda x: f"{x:.2f}x" if pd.notna(x) else "N/A")
    if "Div Yield (%)" in table_df.columns:
        table_df["Div Yield (%)"] = table_df["Div Yield (%)"].apply(lambda x: f"{x:.2f}%" if pd.notna(x) else "N/A")
    if "ICR" in table_df.columns:
        table_df["ICR"] = table_df["ICR"].apply(lambda x: f"{x:.2f}x" if pd.notna(x) else "Debt Free")

    # CSV Download Button
    csv_raw = res_sorted[available_cols].rename(columns=col_rename).to_csv(index=False).encode("utf-8")
    with col_btn:
        st.download_button(
            label="📥 Export CSV",
            data=csv_raw,
            file_name=f"screener_results_{selected_preset.lower().replace(' ', '_')}.csv",
            mime="text/csv",
            use_container_width=True,
        )

    st.dataframe(table_df, use_container_width=True, hide_index=True)
