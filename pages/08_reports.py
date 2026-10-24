"""Page 08 — Annual Reports: Official Corporate Filings and BSE PDF Access."""

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
import requests
import streamlit as st
from src.dashboard.utils.db import get_companies, get_documents

st.markdown("## 📑 **Corporate Filings & Annual Reports Vault**")
st.markdown("Access official BSE India annual report filings for all 92 Nifty 100 constituents with automated URL health checking.")

cos_df = get_companies()
company_options = [f"{row['id']} — {row['company_name']}" for _, row in cos_df.iterrows()]
company_map = {opt: opt.split(" — ")[0] for opt in company_options}

selected_option = st.selectbox(
    "🔍 Select Company to View Filings",
    company_options,
    index=0,
    help="Search by company ticker or name"
)
selected_ticker = company_map[selected_option]
co_name = cos_df[cos_df["id"] == selected_ticker]["company_name"].iloc[0]

docs_df = get_documents(selected_ticker)

st.markdown(f"### **{co_name}** (`{selected_ticker}`) — Available Regulatory Filings")

if docs_df.empty:
    st.warning(f"No regulatory filings found in database for {selected_ticker}.")
    st.stop()

# Helper to check URL validity with caching
@st.cache_data(ttl=3600)
def check_url_status(url: str) -> bool:
    """Returns True if URL is reachable and does not return 404."""
    if not url or pd.isna(url) or not str(url).startswith("http"):
        return False
    try:
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
        resp = requests.head(url.strip(), timeout=4.0, headers=headers, allow_redirects=True)
        if resp.status_code == 404:
            return False
        # If server blocks HEAD with 403/405, test with small GET stream
        if resp.status_code in (403, 405):
            resp_get = requests.get(url.strip(), timeout=4.0, headers=headers, stream=True)
            return resp_get.status_code != 404
        return resp.status_code < 400
    except Exception:
        return False

# Year sorting
docs_sorted = docs_df.sort_values(by="year", ascending=False).reset_index(drop=True)

st.caption(f"Found {len(docs_sorted)} fiscal annual report filings.")

# Render filings in clean interactive cards / table
for _, row in docs_sorted.iterrows():
    yr = row["year"]
    url = row["annual_report"]
    
    col_yr, col_link, col_status = st.columns([1, 2.5, 1.5])
    
    with col_yr:
        st.markdown(f"**FY {yr}**")
        
    with col_link:
        if pd.isna(url) or not str(url).strip():
            st.markdown('<span style="color: #dc3545; font-weight: bold;">Report unavailable</span>', unsafe_allow_html=True)
        else:
            is_valid = check_url_status(str(url).strip())
            if is_valid:
                st.markdown(f"📄 [Download FY {yr} Annual Report]({url})")
            else:
                st.markdown('<span style="color: #dc3545; font-weight: bold;">Report unavailable</span>', unsafe_allow_html=True)
                
    with col_status:
        if pd.notna(url) and str(url).strip() and check_url_status(str(url).strip()):
            st.markdown("🟢 `Available (BSE India)`")
        else:
            st.markdown("🔴 `Unavailable (404/Missing)`")
            
    st.markdown("<hr style='margin: 4px 0; border-color: #f0f0f0;'>", unsafe_allow_html=True)
