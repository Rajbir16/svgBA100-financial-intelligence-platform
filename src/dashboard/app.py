"""Nifty 100 Analytics Dashboard — Main Application Entry Point.

svgBA100 Financial Intelligence Platform
Streamlit institutional-grade financial analytics dashboard.
"""

import streamlit as st

st.set_page_config(
    page_title="Nifty 100 Analytics",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom Institutional CSS Theme
st.markdown("""
<style>
    .main-header {
        font-size: 2.2rem;
        font-weight: 700;
        color: #1B365D;
        margin-bottom: 0.2rem;
    }
    .sub-header {
        font-size: 1.1rem;
        color: #5A6B82;
        margin-bottom: 1.5rem;
    }
    .kpi-card {
        background-color: #F8F9FA;
        border-radius: 8px;
        padding: 16px;
        border-left: 4px solid #1B365D;
        box-shadow: 0 1px 3px rgba(0,0,0,0.08);
    }
    .kpi-title {
        font-size: 0.85rem;
        color: #6C757D;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        font-weight: 600;
    }
    .kpi-val {
        font-size: 1.7rem;
        font-weight: 700;
        color: #1B365D;
        margin-top: 4px;
    }
    .badge-green {
        background-color: #D4EDDA;
        color: #155724;
        padding: 4px 8px;
        border-radius: 4px;
        font-size: 0.85rem;
        font-weight: 600;
    }
    .badge-red {
        background-color: #F8D7DA;
        color: #721C24;
        padding: 4px 8px;
        border-radius: 4px;
        font-size: 0.85rem;
        font-weight: 600;
    }
</style>
""", unsafe_allow_html=True)

# Sidebar Branding
with st.sidebar:
    st.image("https://img.icons8.com/color/96/000000/combo-chart--v1.png", width=64)
    st.markdown("## **Nifty 100 Analytics**")
    st.markdown("##### *Financial Intelligence Platform*")
    st.markdown("---")
    st.info("💡 **Navigation Guide**\nUse the sidebar pages menu above to explore all 8 specialized screens.")
    st.markdown("---")
    st.caption("svgBA100 Platform • Sprint 4 Release")

# Main Portal Welcome
st.markdown('<div class="main-header">Nifty 100 Financial Intelligence Platform</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-header">Institutional financial analytics, ratio engine, peer percentiles, and valuation dashboard for India\'s top 92 enterprises.</div>', unsafe_allow_html=True)

col1, col2, col3, col4 = st.columns(4)
with col1:
    st.markdown("""
    <div class="kpi-card">
        <div class="kpi-title">Universe Coverage</div>
        <div class="kpi-val">92 Companies</div>
    </div>
    """, unsafe_allow_html=True)
with col2:
    st.markdown("""
    <div class="kpi-card">
        <div class="kpi-title">Industry Sectors</div>
        <div class="kpi-val">11 Sectors</div>
    </div>
    """, unsafe_allow_html=True)
with col3:
    st.markdown("""
    <div class="kpi-card">
        <div class="kpi-title">Financial KPIs</div>
        <div class="kpi-val">50+ Metrics</div>
    </div>
    """, unsafe_allow_html=True)
with col4:
    st.markdown("""
    <div class="kpi-card">
        <div class="kpi-title">Historical Depth</div>
        <div class="kpi-val">Up to 12 Years</div>
    </div>
    """, unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

st.markdown("### 🧭 **Explore Available Analytics Modules**")
col_a, col_b = st.columns(2)

with col_a:
    with st.expander("📊 **1. Home Dashboard**", expanded=True):
        st.write("Macro overview across the Nifty 100 index: aggregate P/E, median leverage, average ROE, and sector market cap distribution.")
    with st.expander("🏢 **2. Company Profile**", expanded=True):
        st.write("Comprehensive single-stock diagnostic: 10-year P&L bar charts, dual-axis ROE/ROCE trajectories, and AI-curated Pros & Cons.")
    with st.expander("🔍 **3. Financial Screener**", expanded=True):
        st.write("15 customizable parametric sliders, 6 institutional presets (Quality Compounder, Value Pick, etc.), and instant CSV export.")
    with st.expander("⚖️ **4. Peer Comparison**", expanded=True):
        st.write("Percentile benchmarking within 11 industry peer groups with interactive 8-axis Plotly Scatterpolar radar charts.")

with col_b:
    with st.expander("📈 **5. Trend Analysis**", expanded=True):
        st.write("Longitudinal multi-metric performance tracker with automated Year-over-Year (YoY) percentage change annotations.")
    with st.expander("🌐 **6. Sector Analysis**", expanded=True):
        st.write("Sub-sector bubble matrices (Revenue vs. ROE vs. Market Cap) and industry median KPI benchmarks.")
    with st.expander("🗺️ **7. Capital Allocation Map**", expanded=True):
        st.write("Interactive hierarchical treemap visualizing 92 companies categorized across 8 cash flow capital allocation archetypes.")
    with st.expander("📑 **8. Annual Reports**", expanded=True):
        st.write("Official BSE corporate filings vault with direct PDF download links and automated availability health checks.")

st.markdown("---")
st.caption("Select a page from the sidebar to begin analysis.")

