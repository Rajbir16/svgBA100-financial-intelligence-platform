"""Page 07 — Capital Allocation: 8-Pattern Cash Flow Archetype Treemap."""

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
import plotly.express as px
import streamlit as st
from src.dashboard.utils.db import get_companies

st.markdown("## 🗺️ **Corporate Capital Allocation Archetypes**")
st.markdown("Macro cash flow taxonomy classifying all 92 Nifty 100 enterprises across 8 institutional capital allocation patterns based on Operating (CFO), Investing (CFI), and Financing (CFF) cash flows.")

PATTERN_DESCRIPTIONS = {
    "Shareholder Returns": ("(+ CFO, - CFI, - CFF)", "Mature Cash Cow generating healthy operating cash, maintaining disciplined capex, and returning surplus capital to shareholders via dividends or debt reduction."),
    "Reinvestor": ("(+ CFO, - CFI, - CFF)", "High-growth compounding archetype plowing heavy operating cash flow back into productive capital expenditure and capacity expansion."),
    "Mixed": ("(Variable Cash Flows)", "Balanced or cyclical cash generation with alternating financing and investment cycles."),
    "Growth Funded by Debt": ("(- CFO, - CFI, + CFF)", "Aggressive expansionary phase where negative operating cash flow and high capex are bridged through external debt or equity capital."),
    "Liquidating Assets": ("(+ CFO, + CFI, - CFF)", "Generating cash by divesting non-core plant, property, or subsidiary assets, often to repay debt."),
    "Distress Signal": ("(- CFO, + CFI, - CFF)", "Troubled operational profile where asset divestment is required to fund operational cash shortfalls and mandatory debt servicing."),
    "Pre-Revenue": ("(- CFO, - CFI, + CFF)", "Nascent or incubation phase reliant entirely on capital infusions to build initial infrastructure."),
    "Cash Accumulator": ("(+ CFO, - CFI, + CFF)", "Generating strong operational cash while simultaneously taking on debt or raising equity to build cash buffers."),
}

@st.cache_data(ttl=600)
def _load_capital_allocation_data():
    csv_path = os.path.join(root, "output", "capital_allocation.csv")
    if not os.path.exists(csv_path):
        return pd.DataFrame()
    df = pd.read_csv(csv_path)
    
    # Authoritative annual row: SIEMENS Sep 2024, all others Mar 2024
    siemens_mask = (df["company_id"] == "SIEMENS") & (df["year"] == "Sep 2024")
    others_mask = (df["company_id"] != "SIEMENS") & (df["year"] == "Mar 2024")
    latest = df[siemens_mask | others_mask].copy()
    
    # Merge with companies metadata and market cap for sizing
    cos = get_companies()
    merged = pd.merge(latest, cos, left_on="company_id", right_on="id", how="left")
    
    # Fetch 2024 market cap from database
    import sqlite3
    from src.dashboard.utils.db import DB_PATH
    conn = sqlite3.connect(DB_PATH)
    mc_df = pd.read_sql_query("SELECT company_id, market_cap_crore FROM market_cap WHERE year = 2024", conn)
    conn.close()
    
    final_df = pd.merge(merged, mc_df, on="company_id", how="left")
    final_df["market_cap_crore"] = final_df["market_cap_crore"].fillna(10000.0)
    return final_df

cap_df = _load_capital_allocation_data()

if cap_df.empty:
    st.error("Capital allocation classification data not found in output/capital_allocation.csv.")
    st.stop()

# Interactive Pattern Selector Filter
all_patterns = sorted(cap_df["pattern_label"].dropna().unique().tolist())
pattern_options = ["All Patterns (92 Companies)"] + all_patterns

selected_pattern = st.selectbox(
    "🏷️ Filter by Capital Allocation Pattern",
    pattern_options,
    index=0
)

if selected_pattern != "All Patterns (92 Companies)":
    signs, desc = PATTERN_DESCRIPTIONS.get(selected_pattern, ("", ""))
    st.info(f"**{selected_pattern}** `{signs}`: {desc}")
    display_subset = cap_df[cap_df["pattern_label"] == selected_pattern].copy()
else:
    st.info("💡 **Interactive Treemap Guide**: Click on any pattern tile to zoom into its constituent companies. Hover to inspect market cap and cash flow signs.")
    display_subset = cap_df.copy()

# Plotly Hierarchical Treemap
st.markdown("### 🗺️ **Nifty 100 Capital Allocation Treemap**")

fig_tree = px.treemap(
    cap_df,
    path=["pattern_label", "broad_sector", "company_id"],
    values="market_cap_crore",
    color="pattern_label",
    hover_data={
        "company_name": True,
        "cfo_sign": True,
        "cfi_sign": True,
        "cff_sign": True,
        "market_cap_crore": ":,.0f",
    },
    color_discrete_sequence=px.colors.qualitative.Prism,
)

fig_tree.update_traces(
    textinfo="label+value",
    hovertemplate="<b>%{label}</b><br>Market Cap: ₹%{value:,.0f} Cr<extra></extra>"
)

fig_tree.update_layout(
    height=550,
    margin=dict(t=20, b=20, l=10, r=10)
)

st.plotly_chart(fig_tree, use_container_width=True)

st.markdown("---")

# Constituent Companies Table
st.markdown(f"### 📋 **Companies Belonging to Selected Pattern ({len(display_subset)})**")

table_cols = [
    "company_id", "company_name", "broad_sector", "pattern_label",
    "cfo_sign", "cfi_sign", "cff_sign", "market_cap_crore"
]

disp_df = display_subset[table_cols].copy()
disp_df = disp_df.sort_values(by="market_cap_crore", ascending=False)

disp_df = disp_df.rename(columns={
    "company_id": "Ticker",
    "company_name": "Company Name",
    "broad_sector": "Sector",
    "pattern_label": "Allocation Archetype",
    "cfo_sign": "CFO",
    "cfi_sign": "CFI",
    "cff_sign": "CFF",
    "market_cap_crore": "Market Cap (₹ Cr)",
})

disp_df["Market Cap (₹ Cr)"] = disp_df["Market Cap (₹ Cr)"].apply(lambda x: f"₹{x:,.0f}" if pd.notna(x) else "N/A")

st.dataframe(disp_df, use_container_width=True, hide_index=True)
