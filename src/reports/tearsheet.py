"""Company Tear Sheet Generator — Sprint 5 Phase 3, Day 33.

Generates a professional two-page PDF tear sheet per company using
ReportLab for layout and matplotlib for embedded charts.
"""

import io
import os
import re
import sqlite3
from datetime import date
from typing import Any, Dict, List, Optional, Tuple
from xml.sax.saxutils import escape

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import numpy as np
import pandas as pd

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import (
    Image,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

# ── Constants ────────────────────────────────────────────────────────────────

PAGE_W, PAGE_H = A4  # 595.27 × 841.89 pt
MARGIN = 1.5 * cm
CONTENT_W = PAGE_W - 2 * MARGIN

NAVY = colors.HexColor("#1B2A4A")
DARK_BLUE = colors.HexColor("#2C3E6B")
LIGHT_GREY = colors.HexColor("#F5F6FA")
GREEN = colors.HexColor("#27AE60")
RED = colors.HexColor("#E74C3C")
WHITE = colors.white
BADGE_BLUE = colors.HexColor("#3498DB")

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "nifty100.db")
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "output")

# ── Helpers ──────────────────────────────────────────────────────────────────

def _parse_year_key(yr: str) -> Tuple[int, int]:
    """Return (year_number, month_number) for sorting."""
    months = {"Jan": 1, "Feb": 2, "Mar": 3, "Apr": 4, "May": 5, "Jun": 6,
              "Jul": 7, "Aug": 8, "Sep": 9, "Oct": 10, "Nov": 11, "Dec": 12}
    m = re.match(r"([A-Za-z]+)\s+(\d{4})", yr)
    if m:
        return int(m.group(2)), months.get(m.group(1), 1)
    m2 = re.match(r"(\d{4})", yr)
    if m2:
        return int(m2.group(1)), 3
    return 0, 0


def _short_yr(yr: str) -> str:
    """Shorten 'Mar 2024' to 'FY24' etc."""
    m = re.match(r"([A-Za-z]+)\s+(\d{4})", yr)
    if m:
        return f"FY{m.group(2)[-2:]}"
    return yr[:6]


def _fmt_val(v: Any, decimals: int = 1, suffix: str = "") -> str:
    """Format a numeric value, returning 'N/A' for None."""
    if v is None:
        return "N/A"
    try:
        f = float(v)
        if abs(f) >= 1e5:
            return f"{f / 1000:,.{decimals}f}K{suffix}"
        return f"{f:,.{decimals}f}{suffix}"
    except (TypeError, ValueError):
        return "N/A"


def _fmt_cr(v: Any) -> str:
    """Format a value in Crores."""
    if v is None:
        return "N/A"
    try:
        f = float(v)
        if abs(f) >= 100000:
            return f"₹{f / 100000:,.1f}L Cr"
        if abs(f) >= 1000:
            return f"₹{f / 1000:,.1f}K Cr"
        return f"₹{f:,.0f} Cr"
    except (TypeError, ValueError):
        return "N/A"


def _fig_to_image(fig: plt.Figure, width: float, height: float) -> Image:
    """Convert a matplotlib figure to a ReportLab Image."""
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=150, bbox_inches="tight",
                facecolor="white", edgecolor="none")
    plt.close(fig)
    buf.seek(0)
    return Image(buf, width=width, height=height)


# ── Data fetchers ────────────────────────────────────────────────────────────

def _load_company_data(conn: sqlite3.Connection, ticker: str) -> Dict[str, Any]:
    """Fetch all required data for a single company tear sheet."""
    data: Dict[str, Any] = {}

    # Company info
    row = conn.execute(
        "SELECT id, company_name, book_value, roe_percentage, roce_percentage "
        "FROM companies WHERE id = ?", (ticker,)
    ).fetchone()
    if not row:
        return data
    data["ticker"] = row[0]
    data["name"] = row[1]
    data["book_value"] = row[2]
    data["source_roe"] = row[3]
    data["source_roce"] = row[4]

    # Sector
    sec = conn.execute(
        "SELECT broad_sector, sub_sector FROM sectors WHERE company_id = ?",
        (ticker,)
    ).fetchone()
    data["sector"] = sec[0] if sec else "N/A"
    data["sub_sector"] = sec[1] if sec else "N/A"

    # P&L (annual only, no TTM)
    pnl_rows = conn.execute(
        "SELECT year, sales, net_profit, operating_profit, eps, opm_percentage "
        "FROM profitandloss WHERE company_id = ? AND year != 'TTM' ORDER BY id",
        (ticker,)
    ).fetchall()
    data["pnl"] = [
        {"year": r[0], "sales": r[1], "net_profit": r[2],
         "operating_profit": r[3], "eps": r[4], "opm": r[5]}
        for r in pnl_rows
    ]
    data["pnl"].sort(key=lambda row: _parse_year_key(row["year"]))

    # Balance Sheet (annual, no TTM)
    bs_rows = conn.execute(
        "SELECT year, equity_capital, reserves, borrowings, other_liabilities, total_liabilities, total_assets "
        "FROM balancesheet WHERE company_id = ? AND year != 'TTM' ORDER BY id",
        (ticker,)
    ).fetchall()
    data["bs"] = [
        {"year": r[0], "equity": (r[1] or 0) + (r[2] or 0),
         "equity_capital": r[1], "reserves": r[2],
         "borrowings": r[3], "other_liabilities": r[4],
         "total_liabilities": r[5], "total_assets": r[6]}
        for r in bs_rows
    ]
    data["bs"].sort(key=lambda row: _parse_year_key(row["year"]))

    # Cash Flow (annual only)
    cf_rows = conn.execute(
        "SELECT year, operating_activity, investing_activity, financing_activity, net_cash_flow "
        "FROM cashflow WHERE company_id = ? AND year != 'TTM' ORDER BY id",
        (ticker,)
    ).fetchall()
    data["cf"] = [
        {"year": r[0], "cfo": r[1], "cfi": r[2], "cff": r[3], "net": r[4]}
        for r in cf_rows
    ]

    # Financial Ratios (latest available annual observation)
    fr = conn.execute(
        "SELECT year, net_profit_margin_pct, operating_profit_margin_pct, return_on_equity_pct, "
        "return_on_capital_employed_pct, debt_to_equity, interest_coverage, "
        "free_cash_flow_cr, revenue_cagr_5yr, pat_cagr_5yr, eps_cagr_5yr, "
        "composite_quality_score, cfo_quality_5yr, cfo_quality_label, "
        "capex_intensity_pct, capex_intensity_label, fcf_conversion_pct "
        "FROM financial_ratios WHERE company_id = ? AND year != 'TTM' "
        "ORDER BY id DESC LIMIT 1",
        (ticker,)
    ).fetchone()
    if fr:
        latest_yr = fr[0]
        data["ratios"] = {
            "npm": fr[1], "opm": fr[2], "roe": fr[3], "roce": fr[4],
            "de": fr[5], "icr": fr[6], "fcf": fr[7],
            "rev_cagr_5yr": fr[8], "pat_cagr_5yr": fr[9], "eps_cagr_5yr": fr[10],
            "quality_score": fr[11], "cfo_quality": fr[12], "cfo_label": fr[13],
            "capex_pct": fr[14], "capex_label": fr[15], "fcf_conv": fr[16],
        }
    else:
        data["ratios"] = {}
        latest_yr = data["pnl"][-1]["year"] if data["pnl"] else "N/A"

    # ROE / ROCE time series
    ratio_ts = conn.execute(
        "SELECT year, return_on_equity_pct, return_on_capital_employed_pct "
        "FROM financial_ratios WHERE company_id = ? AND year != 'TTM' ORDER BY id",
        (ticker,)
    ).fetchall()
    data["ratio_ts"] = [
        {"year": r[0], "roe": r[1], "roce": r[2]}
        for r in ratio_ts
    ]
    data["ratio_ts"].sort(key=lambda row: _parse_year_key(row["year"]))

    data["latest_year"] = latest_yr
    return data


def _load_pros_cons(ticker: str) -> Tuple[List[str], List[str]]:
    """Load pros and cons from generated CSV."""
    csv_path = os.path.join(OUTPUT_DIR, "pros_cons_generated.csv")
    pros, cons = [], []
    if not os.path.exists(csv_path):
        return pros, cons
    df = pd.read_csv(csv_path)
    company_df = df[df["company_id"] == ticker]
    for _, row in company_df.iterrows():
        if row["type"] == "pro":
            pros.append(row["text"])
        else:
            cons.append(row["text"])
    return pros, cons


def _load_capital_allocation_label(ticker: str) -> str:
    """Load latest capital allocation pattern label."""
    csv_path = os.path.join(OUTPUT_DIR, "capital_allocation.csv")
    if not os.path.exists(csv_path):
        return "N/A"
    df = pd.read_csv(csv_path)
    latest_yr = "Sep 2024" if ticker == "SIEMENS" else "Mar 2024"
    match = df[(df["company_id"] == ticker) & (df["year"] == latest_yr)]
    if not match.empty:
        return match.iloc[0]["pattern_label"]
    return "N/A"


# ── Chart builders ───────────────────────────────────────────────────────────

def _revenue_profit_chart(pnl_data: List[Dict], chart_w: float, chart_h: float) -> Optional[Image]:
    """Bar chart: Revenue and Net Profit side by side over up to 10 years."""
    if not pnl_data:
        return None
    entries = pnl_data[-10:]  # last 10 years
    years = [_short_yr(e["year"]) for e in entries]
    revenue = [e["sales"] or 0 for e in entries]
    profit = [e["net_profit"] or 0 for e in entries]

    fig, ax = plt.subplots(figsize=(chart_w / 72, chart_h / 72))
    x = np.arange(len(years))
    w = 0.38
    ax.bar(x - w / 2, revenue, w, label="Revenue", color="#3498DB", alpha=0.85)
    ax.bar(x + w / 2, profit, w, label="Net Profit", color="#27AE60", alpha=0.85)
    ax.set_xticks(x)
    ax.set_xticklabels(years, fontsize=7, rotation=45, ha="right")
    ax.set_ylabel("₹ Cr", fontsize=8)
    ax.legend(fontsize=7, loc="upper left")
    ax.set_title("Revenue & Net Profit (₹ Cr)", fontsize=9, fontweight="bold")
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda v, _: f"{v / 1000:.0f}K" if abs(v) >= 1000 else f"{v:.0f}"))
    ax.grid(axis="y", alpha=0.3)
    fig.tight_layout()
    return _fig_to_image(fig, chart_w, chart_h)


def _roe_roce_chart(ratio_ts: List[Dict], chart_w: float, chart_h: float) -> Optional[Image]:
    """Dual-axis line chart: ROE and ROCE trends."""
    valid = [r for r in ratio_ts if r["roe"] is not None or r["roce"] is not None]
    if len(valid) < 2:
        return None
    valid = valid[-10:]
    years = [_short_yr(r["year"]) for r in valid]
    roe = [r["roe"] for r in valid]
    roce = [r["roce"] for r in valid]

    fig, ax1 = plt.subplots(figsize=(chart_w / 72, chart_h / 72))
    x = np.arange(len(years))

    # Plot ROE
    roe_vals = [v if v is not None else np.nan for v in roe]
    ax1.plot(x, roe_vals, "o-", color="#E74C3C", markersize=4, linewidth=1.5, label="ROE %")
    ax1.set_ylabel("ROE %", fontsize=8, color="#E74C3C")
    ax1.tick_params(axis="y", labelcolor="#E74C3C", labelsize=7)

    # Plot ROCE on same axis
    roce_vals = [v if v is not None else np.nan for v in roce]
    ax1.plot(x, roce_vals, "s-", color="#3498DB", markersize=4, linewidth=1.5, label="ROCE %")

    ax1.set_xticks(x)
    ax1.set_xticklabels(years, fontsize=7, rotation=45, ha="right")
    ax1.legend(fontsize=7, loc="upper left")
    ax1.set_title("ROE & ROCE Trends (%)", fontsize=9, fontweight="bold")
    ax1.grid(axis="y", alpha=0.3)
    fig.tight_layout()
    return _fig_to_image(fig, chart_w, chart_h)


def _balance_sheet_chart(bs_data: List[Dict], chart_w: float, chart_h: float) -> Optional[Image]:
    """Stacked bar chart: balance sheet composition by year."""
    if not bs_data:
        return None
    entries = bs_data[-10:]
    years = [_short_yr(e["year"]) for e in entries]
    equity = [e["equity"] or 0 for e in entries]
    borrowings = [e["borrowings"] or 0 for e in entries]
    other = [e["other_liabilities"] or 0 for e in entries]

    fig, ax = plt.subplots(figsize=(chart_w / 72, chart_h / 72))
    x = np.arange(len(years))
    w = 0.55
    ax.bar(x, equity, w, label="Equity", color="#27AE60", alpha=0.85)
    ax.bar(x, borrowings, w, bottom=equity, label="Borrowings", color="#E74C3C", alpha=0.85)
    bottoms = [e + b for e, b in zip(equity, borrowings)]
    ax.bar(x, other, w, bottom=bottoms, label="Other Liabilities", color="#95A5A6", alpha=0.85)
    ax.set_xticks(x)
    ax.set_xticklabels(years, fontsize=7, rotation=45, ha="right")
    ax.set_ylabel("₹ Cr", fontsize=8)
    ax.legend(fontsize=7, loc="upper left")
    ax.set_title("Balance Sheet Composition (₹ Cr)", fontsize=9, fontweight="bold")
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda v, _: f"{v / 1000:.0f}K" if abs(v) >= 1000 else f"{v:.0f}"))
    ax.grid(axis="y", alpha=0.3)
    fig.tight_layout()
    return _fig_to_image(fig, chart_w, chart_h)


def _cashflow_waterfall(cf_data: List[Dict], latest_year: str,
                         chart_w: float, chart_h: float) -> Optional[Image]:
    """Cash-flow waterfall chart for the latest comparable annual year."""
    entry = None
    for r in reversed(cf_data):
        if r["year"] == latest_year:
            entry = r
            break
    if entry is None and cf_data:
        # Fallback: last available row
        for r in reversed(cf_data):
            if r["year"] != "TTM":
                entry = r
                break
    if entry is None:
        return None

    labels = ["CFO", "CFI", "CFF", "Net"]
    values = [entry.get("cfo") or 0, entry.get("cfi") or 0,
              entry.get("cff") or 0, entry.get("net") or 0]
    bar_colors = []
    for v in values:
        bar_colors.append("#27AE60" if v >= 0 else "#E74C3C")

    fig, ax = plt.subplots(figsize=(chart_w / 72, chart_h / 72))
    x = np.arange(len(labels))
    ax.bar(x, values, color=bar_colors, width=0.55, alpha=0.85)
    ax.set_xticks(x)
    ax.set_xticklabels(labels, fontsize=8)
    ax.axhline(0, color="black", linewidth=0.5)
    for i, v in enumerate(values):
        y_pos = v + (abs(max(values, key=abs)) * 0.02 if v >= 0 else -abs(max(values, key=abs)) * 0.06)
        ax.text(i, y_pos, f"{v:,.0f}", ha="center", va="bottom" if v >= 0 else "top", fontsize=7)
    ax.set_ylabel("₹ Cr", fontsize=8)
    ax.set_title(f"Cash Flow Waterfall — {entry['year']}", fontsize=9, fontweight="bold")
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda v, _: f"{v / 1000:.0f}K" if abs(v) >= 1000 else f"{v:.0f}"))
    ax.grid(axis="y", alpha=0.3)
    fig.tight_layout()
    return _fig_to_image(fig, chart_w, chart_h)


# ── PDF builder ──────────────────────────────────────────────────────────────

def _build_header(ticker: str, name: str, sector: str, latest_year: str) -> Table:
    """Build navy header bar with company name and ticker."""
    styles = getSampleStyleSheet()
    header_style = ParagraphStyle("Header", parent=styles["Normal"],
                                   fontSize=16, textColor=WHITE,
                                   fontName="Helvetica-Bold", leading=20)
    sub_style = ParagraphStyle("SubHeader", parent=styles["Normal"],
                                fontSize=9, textColor=colors.HexColor("#BDC3C7"),
                                fontName="Helvetica", leading=12)
    date_style = ParagraphStyle("DateStyle", parent=styles["Normal"],
                                 fontSize=8, textColor=colors.HexColor("#BDC3C7"),
                                 fontName="Helvetica", leading=10, alignment=TA_RIGHT)

    name_para = Paragraph(escape(str(name)), header_style)
    sub_para = Paragraph(
        f"{escape(str(ticker))} | {escape(str(sector))} | FY Basis: {escape(str(latest_year))}",
        sub_style,
    )
    date_para = Paragraph(f"Generated: {date.today().strftime('%d %b %Y')}", date_style)

    tbl = Table(
        [[name_para, date_para], [sub_para, ""]],
        colWidths=[CONTENT_W * 0.72, CONTENT_W * 0.28],
        rowHeights=[24, 16],
    )
    tbl.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), NAVY),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 10),
        ("RIGHTPADDING", (-1, 0), (-1, -1), 10),
        ("TOPPADDING", (0, 0), (-1, 0), 6),
        ("BOTTOMPADDING", (0, -1), (-1, -1), 4),
    ]))
    return tbl


def _kpi_tile(label: str, value: str, color: colors.Color = DARK_BLUE) -> Table:
    """Single KPI tile for the dashboard row."""
    styles = getSampleStyleSheet()
    lbl_style = ParagraphStyle("KPILabel", parent=styles["Normal"],
                                fontSize=7, textColor=colors.HexColor("#7F8C8D"),
                                fontName="Helvetica", alignment=TA_CENTER, leading=9)
    val_style = ParagraphStyle("KPIValue", parent=styles["Normal"],
                                fontSize=11, textColor=color,
                                fontName="Helvetica-Bold", alignment=TA_CENTER, leading=14)
    tile_w = CONTENT_W / 3 - 4
    tbl = Table(
        [[Paragraph(value, val_style)], [Paragraph(label, lbl_style)]],
        colWidths=[tile_w],
        rowHeights=[20, 14],
    )
    tbl.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), LIGHT_GREY),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#DDE1E6")),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
    ]))
    return tbl


def _build_kpi_rows(ratios: Dict) -> Table:
    """Build two rows of three KPI tiles."""
    tiles_row1 = [
        _kpi_tile("ROE %", _fmt_val(ratios.get("roe"), 1, "%")),
        _kpi_tile("ROCE %", _fmt_val(ratios.get("roce"), 1, "%")),
        _kpi_tile("Net Profit Margin", _fmt_val(ratios.get("npm"), 1, "%")),
    ]
    tiles_row2 = [
        _kpi_tile("D/E Ratio", _fmt_val(ratios.get("de"), 2)),
        _kpi_tile("Rev CAGR 5yr", _fmt_val(ratios.get("rev_cagr_5yr"), 1, "%")),
        _kpi_tile("FCF", _fmt_cr(ratios.get("fcf"))),
    ]
    col_w = CONTENT_W / 3
    tbl = Table(
        [tiles_row1, tiles_row2],
        colWidths=[col_w] * 3,
        rowHeights=[42, 42],
    )
    tbl.setStyle(TableStyle([
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 2),
        ("RIGHTPADDING", (0, 0), (-1, -1), 2),
    ]))
    return tbl


def _build_pros_cons_section(pros: List[str], cons: List[str]) -> List:
    """Build pros and cons bullet point sections."""
    styles = getSampleStyleSheet()
    elements = []

    section_style = ParagraphStyle("SectionTitle", parent=styles["Normal"],
                                    fontSize=11, fontName="Helvetica-Bold",
                                    textColor=NAVY, spaceAfter=4, spaceBefore=6)
    pro_style = ParagraphStyle("Pro", parent=styles["Normal"],
                                fontSize=8, textColor=GREEN,
                                fontName="Helvetica", leading=11,
                                leftIndent=12, spaceAfter=2)
    con_style = ParagraphStyle("Con", parent=styles["Normal"],
                                fontSize=8, textColor=RED,
                                fontName="Helvetica", leading=11,
                                leftIndent=12, spaceAfter=2)

    if pros:
        elements.append(Paragraph("Strengths", section_style))
        for p in pros[:6]:
            elements.append(Paragraph(f"- {escape(str(p))}", pro_style))

    if cons:
        elements.append(Spacer(1, 4))
        elements.append(Paragraph("Risks", section_style))
        for c in cons[:6]:
            elements.append(Paragraph(f"- {escape(str(c))}", con_style))

    return elements


def _build_badge(label: str) -> Table:
    """Build capital allocation pattern badge."""
    styles = getSampleStyleSheet()
    badge_style = ParagraphStyle("Badge", parent=styles["Normal"],
                                  fontSize=9, textColor=WHITE,
                                  fontName="Helvetica-Bold",
                                  alignment=TA_CENTER, leading=12)
    label_style = ParagraphStyle("BadgeLabel", parent=styles["Normal"],
                                  fontSize=7, textColor=colors.HexColor("#7F8C8D"),
                                  fontName="Helvetica", alignment=TA_CENTER, leading=9)
    tbl = Table(
        [[Paragraph("Capital Allocation Pattern", label_style)],
         [Paragraph(label, badge_style)]],
        colWidths=[CONTENT_W * 0.5],
        rowHeights=[14, 22],
    )
    tbl.setStyle(TableStyle([
        ("BACKGROUND", (0, 1), (-1, 1), BADGE_BLUE),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("BOX", (0, 1), (-1, 1), 0.5, DARK_BLUE),
        ("TOPPADDING", (0, 1), (-1, 1), 4),
        ("BOTTOMPADDING", (0, 1), (-1, 1), 4),
    ]))
    return tbl


def generate_tearsheet(
    ticker: str,
    output_path: str,
    db_path: str = None,
) -> bool:
    """Generate a two-page PDF tear sheet for the given company ticker.

    Returns True on success, False if insufficient data.
    """
    if db_path is None:
        db_path = os.path.abspath(DB_PATH)

    conn = sqlite3.connect(db_path)
    try:
        data = _load_company_data(conn, ticker)
    finally:
        conn.close()

    if not data or "ticker" not in data:
        return False

    # Check minimum data: at least 3 annual PnL observations
    if len(data.get("pnl", [])) < 3:
        return False

    pros, cons = _load_pros_cons(ticker)
    cap_label = _load_capital_allocation_label(ticker)

    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)

    # Build the PDF
    doc = SimpleDocTemplate(
        output_path,
        pagesize=A4,
        leftMargin=MARGIN,
        rightMargin=MARGIN,
        topMargin=MARGIN,
        bottomMargin=MARGIN,
    )

    elements = []

    # ── PAGE 1 ───────────────────────────────────────────────────────────
    # Header
    header = _build_header(data["ticker"], data["name"],
                           data["sector"], data["latest_year"])
    elements.append(header)
    elements.append(Spacer(1, 8))

    # KPI tiles
    kpi_tbl = _build_kpi_rows(data.get("ratios", {}))
    elements.append(kpi_tbl)
    elements.append(Spacer(1, 8))

    # Revenue & Profit chart
    chart_w = CONTENT_W
    chart_h = 170
    rev_chart = _revenue_profit_chart(data.get("pnl", []), chart_w, chart_h)
    if rev_chart:
        elements.append(rev_chart)
        elements.append(Spacer(1, 6))

    # ROE & ROCE chart
    roe_chart = _roe_roce_chart(data.get("ratio_ts", []), chart_w, chart_h)
    if roe_chart:
        elements.append(roe_chart)

    # Force page break
    from reportlab.platypus import PageBreak
    elements.append(PageBreak())

    # ── PAGE 2 ───────────────────────────────────────────────────────────
    # Mini header
    styles = getSampleStyleSheet()
    pg2_title = ParagraphStyle("Pg2Title", parent=styles["Normal"],
                                fontSize=12, fontName="Helvetica-Bold",
                                textColor=NAVY, spaceAfter=6)
    elements.append(Paragraph(
        f"{escape(str(data['name']))} — Detailed Analysis", pg2_title
    ))
    elements.append(Spacer(1, 4))

    # Balance sheet composition chart
    bs_chart = _balance_sheet_chart(data.get("bs", []), chart_w, 155)
    if bs_chart:
        elements.append(bs_chart)
        elements.append(Spacer(1, 6))

    # Cash flow waterfall
    cf_chart = _cashflow_waterfall(data.get("cf", []), data["latest_year"],
                                    chart_w * 0.6, 145)
    if cf_chart:
        elements.append(cf_chart)
        elements.append(Spacer(1, 6))

    # Pros and cons
    pc_elements = _build_pros_cons_section(pros, cons)
    elements.extend(pc_elements)

    if pc_elements:
        elements.append(Spacer(1, 6))

    # Capital allocation badge
    badge = _build_badge(cap_label)
    elements.append(badge)

    # Build
    def add_page_number(canvas, document):
        canvas.saveState()
        canvas.setFont("Helvetica", 8)
        canvas.setFillColor(colors.HexColor("#7F8C8D"))
        canvas.drawString(MARGIN, 0.8 * cm, f"{data['ticker']} | Company Tear Sheet")
        canvas.drawRightString(PAGE_W - MARGIN, 0.8 * cm, f"Page {document.page}")
        canvas.restoreState()

    doc.build(elements, onFirstPage=add_page_number, onLaterPages=add_page_number)
    return True


# ── Batch generation ─────────────────────────────────────────────────────────

def generate_all_tearsheets(
    output_dir: str = "reports/tearsheets",
    db_path: str = None,
    skipped_csv: str = "output/skipped_tearsheets.csv",
) -> Dict[str, Any]:
    """Generate tear sheets for all 92 companies. Returns summary stats."""
    if db_path is None:
        db_path = os.path.abspath(DB_PATH)

    os.makedirs(output_dir, exist_ok=True)
    os.makedirs(os.path.dirname(skipped_csv) or ".", exist_ok=True)

    conn = sqlite3.connect(db_path)
    companies = conn.execute(
        "SELECT c.id, c.company_name FROM companies c ORDER BY c.id"
    ).fetchall()

    # Get annual observation counts
    obs_counts = {}
    for cid, cname in companies:
        pnl_count = conn.execute(
            "SELECT COUNT(*) FROM profitandloss WHERE company_id = ? AND year != 'TTM'",
            (cid,)
        ).fetchone()[0]
        obs_counts[cid] = pnl_count
    conn.close()

    generated = []
    skipped = []

    for cid, cname in companies:
        annual_obs = obs_counts[cid]
        if annual_obs < 3:
            skipped.append({
                "company_id": cid,
                "company_name": cname,
                "ticker": cid,
                "available_annual_observations": annual_obs,
                "reason": f"Fewer than 3 annual PnL observations ({annual_obs} available)",
            })
            continue

        pdf_path = os.path.join(output_dir, f"{cid}_tearsheet.pdf")
        success = generate_tearsheet(cid, pdf_path, db_path)
        if success:
            generated.append(cid)
        else:
            skipped.append({
                "company_id": cid,
                "company_name": cname,
                "ticker": cid,
                "available_annual_observations": annual_obs,
                "reason": "Insufficient data to generate tear sheet",
            })

    # Write skipped CSV
    if skipped:
        pd.DataFrame(skipped).to_csv(skipped_csv, index=False)
    else:
        pd.DataFrame(columns=[
            "company_id", "company_name", "ticker",
            "available_annual_observations", "reason"
        ]).to_csv(skipped_csv, index=False)

    return {
        "total_companies": len(companies),
        "generated": len(generated),
        "skipped": len(skipped),
        "generated_tickers": generated,
        "skipped_details": skipped,
    }


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        ticker = sys.argv[1]
        out = f"reports/tearsheets/{ticker}_tearsheet.pdf"
        ok = generate_tearsheet(ticker, out)
        print(f"{'Generated' if ok else 'Failed'}: {out}")
    else:
        result = generate_all_tearsheets()
        print(f"Generated: {result['generated']}, Skipped: {result['skipped']}")
        for s in result["skipped_details"]:
            print(f"  SKIP: {s['company_id']} - {s['reason']}")
