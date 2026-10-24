"""Script to generate the comprehensive, publication-grade Analyst Guide PDF (>=10 pages)."""

import os
import sys
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm, mm
from reportlab.pdfgen import canvas
from reportlab.platypus import (
    HRFlowable,
    KeepTogether,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

NAVY = colors.HexColor("#1B2A4A")
STEEL = colors.HexColor("#2C3E6B")
LIGHT_BG = colors.HexColor("#F8F9FA")
BORDER_COLOR = colors.HexColor("#DDE1E6")
ACCENT = colors.HexColor("#0D6EFD")
TEXT_DARK = colors.HexColor("#212529")
TEXT_MUTED = colors.HexColor("#6C757D")


class NumberedCanvas(canvas.Canvas):
    """Canvas that computes total pages dynamically and adds running headers & footers."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_decorations(num_pages)
            super().showPage()
        super().save()

    def draw_page_decorations(self, page_count):
        self.saveState()
        self.setFont("Helvetica", 8)
        self.setFillColor(TEXT_MUTED)

        # Do not draw running header on cover page
        if self._pageNumber > 1:
            self.drawString(1.5 * cm, A4[1] - 1.0 * cm, "svgBA100 Financial Intelligence Platform — Analyst Reference Guide")
            self.setStrokeColor(BORDER_COLOR)
            self.setLineWidth(0.5)
            self.line(1.5 * cm, A4[1] - 1.15 * cm, A4[0] - 1.5 * cm, A4[1] - 1.15 * cm)

        # Running Footer
        page_str = f"Page {self._pageNumber} of {page_count}"
        self.drawRightString(A4[0] - 1.5 * cm, 0.9 * cm, page_str)
        self.drawString(1.5 * cm, 0.9 * cm, "CONFIDENTIAL & PROPRIETARY — FOR LOCAL ANALYST USE ONLY")
        self.setStrokeColor(BORDER_COLOR)
        self.setLineWidth(0.5)
        self.line(1.5 * cm, 1.15 * cm, A4[0] - 1.5 * cm, 1.15 * cm)
        self.restoreState()


def build_analyst_guide(output_path: str = "docs/analyst_guide.pdf"):
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    doc = SimpleDocTemplate(
        output_path,
        pagesize=A4,
        leftMargin=1.5 * cm,
        rightMargin=1.5 * cm,
        topMargin=1.5 * cm,
        bottomMargin=1.5 * cm,
    )

    styles = getSampleStyleSheet()

    # Custom styles
    title_style = ParagraphStyle(
        "CoverTitle",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=24,
        leading=28,
        textColor=NAVY,
        alignment=TA_LEFT,
    )
    subtitle_style = ParagraphStyle(
        "CoverSubtitle",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=12,
        leading=16,
        textColor=STEEL,
        spaceAfter=12,
    )
    h1_style = ParagraphStyle(
        "H1",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=15,
        leading=18,
        textColor=NAVY,
        spaceBefore=10,
        spaceAfter=6,
    )
    h2_style = ParagraphStyle(
        "H2",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=11,
        leading=14,
        textColor=STEEL,
        spaceBefore=6,
        spaceAfter=3,
    )
    body_style = ParagraphStyle(
        "Body",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=8.5,
        leading=12,
        textColor=TEXT_DARK,
        alignment=TA_JUSTIFY,
        spaceAfter=5,
    )
    bullet_style = ParagraphStyle(
        "Bullet",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=8.5,
        leading=11.5,
        textColor=TEXT_DARK,
        leftIndent=12,
        spaceAfter=3,
    )
    code_style = ParagraphStyle(
        "CodeBlock",
        parent=styles["Normal"],
        fontName="Courier",
        fontSize=7.5,
        leading=9.5,
        textColor=colors.HexColor("#2C3E50"),
        backColor=LIGHT_BG,
        borderColor=BORDER_COLOR,
        borderWidth=0.5,
        borderPadding=4,
        spaceAfter=5,
    )

    story = []

    # =========================================================================
    # PAGE 1: TITLE & EXECUTIVE PLATFORM OVERVIEW
    # =========================================================================
    story.append(Spacer(1, 20))
    story.append(Paragraph("svgBA100 FINANCIAL INTELLIGENCE PLATFORM", title_style))
    story.append(Paragraph("Comprehensive Analyst Operations & System Reference Guide", subtitle_style))
    story.append(HRFlowable(width="100%", thickness=2, color=NAVY, spaceAfter=15))

    story.append(Paragraph("1. Executive Overview & Purpose", h1_style))
    story.append(Paragraph(
        "The <b>svgBA100 Financial Intelligence Platform</b> is an institutional-grade financial analysis, "
        "screening, valuation, and capital allocation intelligence system tailored for the Nifty 100 constituent universe. "
        "Spanning Sprints 1 through 6 (Days 1–45), the platform integrates automated ETL pipelines, authoritative SQLite data stores, "
        "deterministic ratio computation engines, natural language text extraction, machine-learning archetypal clustering, "
        "an interactive multi-page Streamlit analytical dashboard, and high-performance RESTful FastAPI services.",
        body_style,
    ))
    story.append(Paragraph(
        "This guide serves as the definitive reference manual for financial analysts, portfolio managers, and quantitative engineers "
        "operating the system locally. It details architecture, screening workflows, report generation, API endpoints, troubleshooting, "
        "and documented data exceptions.",
        body_style,
    ))

    story.append(Paragraph("Core Platform Capabilities", h2_style))
    story.append(Paragraph("● <b>Master Universe:</b> Exactly 92 verified Indian enterprise corporations with multi-year audited histories.", bullet_style))
    story.append(Paragraph("● <b>Analytics & Ratio Engine:</b> Deterministic computation of 55+ KPIs (ROE, ROCE, OPM, NPM, D/E, ICR, FCF, 3/5/10yr CAGRs).", bullet_style))
    story.append(Paragraph("● <b>Screener & Scoring:</b> Sector-relative P10/P90 normalized Composite Quality Score (0–100) and 6 predefined strategy presets.", bullet_style))
    story.append(Paragraph("● <b>Peer Cohort Benchmarking:</b> Percentile rankings across 11 industry cohorts and 92 automated radar charts.", bullet_style))
    story.append(Paragraph("● <b>Cash Flow Intelligence:</b> 8-pattern capital allocation taxonomy, distress early-warning flags, and deleveraging detectors.", bullet_style))
    story.append(Paragraph("● <b>Automated PDF Reporting:</b> 2-page company tear sheets, 10 broad-sector reports, and a 17-page portfolio summary.", bullet_style))
    story.append(Paragraph("● <b>Machine Learning:</b> 5-archetype K-Means clustering, within-sector outlier detection (|Z| > 3), and elbow analysis.", bullet_style))
    story.append(Paragraph("● <b>RESTful API & Dashboard:</b> 21 FastAPI endpoints under /api/v1 and an 8-screen Streamlit application.", bullet_style))

    story.append(Spacer(1, 10))
    metadata_tbl = Table([
        ["Target Universe", "Nifty 100 Constituents (92 Authoritative Master Companies)"],
        ["Primary Data Store", "SQLite (db/schema.sql, nifty100.db with Foreign Key Constraints ON)"],
        ["Local API Server", "FastAPI / Uvicorn (http://127.0.0.1:8000, OpenAPI docs at /docs)"],
        ["Analytical Dashboard", "Streamlit Multi-page App (http://localhost:8501)"],
        ["Authoritative Sprints", "Sprint 1 through Sprint 6 Complete (179 Regression Tests Passing)"],
    ], colWidths=[130, 360])
    metadata_tbl.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, -1), LIGHT_BG),
        ("TEXTCOLOR", (0, 0), (-1, -1), TEXT_DARK),
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("FONTNAME", (1, 0), (1, -1), "Helvetica"),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("GRID", (0, 0), (-1, -1), 0.5, BORDER_COLOR),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("PADDING", (0, 0), (-1, -1), 4),
    ]))
    story.append(metadata_tbl)
    story.append(PageBreak())

    # =========================================================================
    # PAGE 2: SYSTEM ARCHITECTURE & DATA MODEL
    # =========================================================================
    story.append(Paragraph("2. System Architecture & Relational Data Model", h1_style))
    story.append(HRFlowable(width="100%", thickness=1, color=NAVY, spaceAfter=8))
    story.append(Paragraph(
        "The platform follows a layered modular architecture designed for local execution, deterministic auditability, and zero cloud dependency. "
        "The relational core is stored in <b>nifty100.db</b> with foreign key enforcement enabled (`PRAGMA foreign_keys = ON`).",
        body_style,
    ))

    story.append(Paragraph("Database Schema Overview", h2_style))
    schema_tbl = Table([
        ["Table Name", "Primary Key / FK", "Record Count", "Functional Description"],
        ["companies", "id (TEXT PK)", "92", "Master table containing company names, logos, face value, book value."],
        ["sectors", "id (PK), company_id (FK)", "92", "10 authoritative broad sectors, sub-sectors, and index weights."],
        ["profitandloss", "id (PK), company_id (FK)", "1,146", "Historical P&L: sales, expenses, operating profit, net profit, EPS."],
        ["balancesheet", "id (PK), company_id (FK)", "1,143", "Historical BS: equity, reserves, borrowings, total assets/liabilities."],
        ["cashflow", "id (PK), company_id (FK)", "1,091", "Historical CF: operating (CFO), investing (CFI), financing (CFF)."],
        ["financial_ratios", "id (PK), company_id (FK)", "1,160", "Calculated ratios: ROE, ROCE, OPM, D/E, ICR, CAGRs, quality score."],
        ["peer_groups", "id (PK), company_id (FK)", "59", "11 industry peer cohorts with designated benchmark tickers."],
        ["peer_percentiles", "id (PK), company_id (FK)", "560", "Peer cohort percentiles for 10 financial metrics."],
        ["market_cap", "id (PK), company_id (FK)", "552", "Market cap, enterprise value, PE, PB, EV/EBITDA, dividend yield."],
        ["documents", "id (PK), company_id (FK)", "1,457", "Annual report PDF URLs and regulatory filing links."],
    ], colWidths=[90, 100, 65, 235])
    schema_tbl.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), NAVY),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 7.5),
        ("GRID", (0, 0), (-1, -1), 0.5, BORDER_COLOR),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, LIGHT_BG]),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("PADDING", (0, 0), (-1, -1), 3),
    ]))
    story.append(schema_tbl)

    story.append(Paragraph("Authoritative Broad Sectors vs Industry Peer Cohorts", h2_style))
    story.append(Paragraph(
        "A critical architectural distinction verified during Sprint 5 and preserved in Sprint 6 is that the database maintains "
        "<b>two complementary categorization dimensions</b>:",
        body_style,
    ))
    story.append(Paragraph("1. <b>10 Authoritative Broad Sectors:</b> Populated in the `sectors` table (Communication Services, Consumer Discretionary, Consumer Staples, Energy, Financials, Healthcare, Industrials, Information Technology, Materials, Real Estate). Every one of the 92 companies belongs to exactly one broad sector.", bullet_style))
    story.append(Paragraph("2. <b>11 Industry Peer Cohorts:</b> Populated in `peer_groups` (Automobiles, Consumer Finance, FMCG, IT Services, Life Insurance, Oil & Gas, Pharmaceuticals, Power & Utilities, Private Banks, Public Sector Banks, Steel). Used specifically for intra-industry percentile rankings.", bullet_style))
    story.append(Paragraph(
        "Analysts must not conflate these dimensions: `/api/v1/sectors` exposes the 10 broad sectors, while `/api/v1/peers` exposes the 11 peer cohorts.",
        body_style,
    ))
    story.append(PageBreak())

    # =========================================================================
    # PAGE 3: DASHBOARD NAVIGATION — SCREENS 1–4
    # =========================================================================
    story.append(Paragraph("3. Dashboard Navigation & Screen Walkthrough (Part 1)", h1_style))
    story.append(HRFlowable(width="100%", thickness=1, color=NAVY, spaceAfter=8))
    story.append(Paragraph(
        "The interactive Streamlit dashboard is launched via `streamlit run src/dashboard/app.py --server.port 8501`. "
        "The application provides eight dedicated analytical screens accessible via the left sidebar.",
        body_style,
    ))

    story.append(Paragraph("Screen 01: Home & Executive Overview", h2_style))
    story.append(Paragraph(
        "The Home screen displays high-level portfolio KPIs: total universe market capitalization, average ROE, median Debt-to-Equity, "
        "and top-ranked companies by Composite Quality Score. It features a distribution chart of the 10 broad sectors and direct quick-links "
        "to detailed company analyses.",
        body_style,
    ))

    story.append(Paragraph("Screen 02: Company Profile & Financial Statements", h2_style))
    story.append(Paragraph(
        "Allows single-company drill-down via ticker selection. Displays:",
        body_style,
    ))
    story.append(Paragraph("● Master corporate profile: sector, sub-sector, face value, book value, and website.", bullet_style))
    story.append(Paragraph("● Key Financial Ratios: ROE %, ROCE %, Net Profit Margin %, OPM %, Debt-to-Equity, and ICR.", bullet_style))
    story.append(Paragraph("● Full historical tables for Profit & Loss, Balance Sheet, and Cash Flows with annual/TTM toggles.", bullet_style))
    story.append(Paragraph("● Automated Strengths and Weaknesses generated from the rule-based NLP engine.", bullet_style))
    story.append(Paragraph("● Direct one-click download of the 2-page publication-grade PDF Tear Sheet.", bullet_style))

    story.append(Paragraph("Screen 03: Multi-Metric Financial Screener", h2_style))
    story.append(Paragraph(
        "The core screening module allowing interactive filtering across 15 metrics. Analysts can activate one of the 6 predefined presets "
        "or customize minimum/maximum thresholds for ROE, ROCE, D/E, FCF, Revenue CAGR, and Valuation multiples. "
        "Results update instantaneously with sorting on any metric and CSV export functionality.",
        body_style,
    ))

    story.append(Paragraph("Screen 04: Peer Comparison & Benchmarking", h2_style))
    story.append(Paragraph(
        "Enables head-to-head benchmarking within any of the 11 industry peer cohorts. Displays side-by-side metric tables, "
        "percentile rankings (0–100th percentile), benchmark company deltas, and embedded 10-axis radar charts generated during Sprint 3.",
        body_style,
    ))
    story.append(PageBreak())

    # =========================================================================
    # PAGE 4: DASHBOARD NAVIGATION — SCREENS 5–8
    # =========================================================================
    story.append(Paragraph("4. Dashboard Navigation & Screen Walkthrough (Part 2)", h1_style))
    story.append(HRFlowable(width="100%", thickness=1, color=NAVY, spaceAfter=8))

    story.append(Paragraph("Screen 05: Historical Trends & Growth Analysis", h2_style))
    story.append(Paragraph(
        "Focuses on multi-year longitudinal trends. Provides interactive dual-axis line charts comparing revenue growth vs operating profit, "
        "net margin progression, and compound annual growth rates (3-year, 5-year, and 10-year CAGRs). Highlights inflection points and growth decelerations.",
        body_style,
    ))

    story.append(Paragraph("Screen 06: Broad Sector Intelligence", h2_style))
    story.append(Paragraph(
        "Summarizes sector-level fundamental health across all 10 authoritative broad sectors. Features median ROE, ROCE, leverage, "
        "and market capitalization concentration charts. Clicking any sector reveals its constituent companies and sector-relative rankings.",
        body_style,
    ))

    story.append(Paragraph("Screen 07: Capital Allocation & Cash Flow Health", h2_style))
    story.append(Paragraph(
        "Visualizes the 8-pattern cash flow taxonomy established in Sprint 5. Identifies whether companies are Shareholder Returners, "
        "Reinvestors, Cash Accumulators, or Distress Signals. Highlights early warning distress alerts (negative CFO funded by CFF borrowings) "
        "and active deleveraging trends.",
        body_style,
    ))

    story.append(Paragraph("Screen 08: Institutional Reports & Document Hub", h2_style))
    story.append(Paragraph(
        "Central repository for viewing and downloading institutional PDF deliverables: individual company tear sheets, 10 broad-sector reports, "
        "the 17-page portfolio summary document, and direct hyperlinks to official annual report filings stored in the database.",
        body_style,
    ))

    story.append(Spacer(1, 10))
    story.append(Paragraph("Operational Summary of Dashboard Screens", h2_style))
    screen_tbl = Table([
        ["Screen", "Module Path", "Key Analytical Function", "Primary Data Source"],
        ["01 Home", "src/dashboard/pages/01_home.py", "Portfolio snapshot & market overview", "companies, sectors, financial_ratios"],
        ["02 Profile", "src/dashboard/pages/02_profile.py", "Company financials, pros/cons, PDF export", "All financial tables, prosandcons"],
        ["03 Screener", "src/dashboard/pages/03_screener.py", "15-metric filtering & composite scoring", "src/screener/engine.py"],
        ["04 Peers", "src/dashboard/pages/04_peers.py", "11 peer cohorts, radar charts & ranks", "peer_groups, peer_percentiles"],
        ["05 Trends", "src/dashboard/pages/05_trends.py", "CAGR time series & margin trends", "financial_ratios, analysis"],
        ["06 Sectors", "src/dashboard/pages/06_sectors.py", "10 broad sectors median analysis", "sectors, financial_ratios"],
        ["07 Capital", "src/dashboard/pages/07_capital.py", "8-pattern cash flow & distress alerts", "output/cashflow_intelligence.xlsx"],
        ["08 Reports", "src/dashboard/pages/08_reports.py", "PDF report repository & regulatory links", "reports/, documents table"],
    ], colWidths=[70, 140, 150, 130])
    screen_tbl.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), STEEL),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 7.5),
        ("GRID", (0, 0), (-1, -1), 0.5, BORDER_COLOR),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, LIGHT_BG]),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("PADDING", (0, 0), (-1, -1), 3),
    ]))
    story.append(screen_tbl)
    story.append(PageBreak())

    # =========================================================================
    # PAGE 5: FINANCIAL SCREENER & COMPOSITE QUALITY SCORING
    # =========================================================================
    story.append(Paragraph("5. Financial Screener & Composite Quality Scoring", h1_style))
    story.append(HRFlowable(width="100%", thickness=1, color=NAVY, spaceAfter=8))
    story.append(Paragraph(
        "The platform includes an institutional-grade screener operating on `src/screener/engine.py`. "
        "The engine evaluates all 92 companies against custom threshold constraints and calculates a sector-relative Composite Quality Score.",
        body_style,
    ))

    story.append(Paragraph("Composite Quality Score Methodology (0–100 Scale)", h2_style))
    story.append(Paragraph(
        "To prevent cross-sector bias (e.g. IT services naturally having higher ROE than capital-heavy utilities), "
        "every component metric is normalized sector-relative using 10th and 90th percentile winsorisation:",
        body_style,
    ))
    story.append(Paragraph("$$Score_{i} = \\frac{\\text{clip}(X_i, P_{10}, P_{90}) - P_{10}}{P_{90} - P_{10}} \\times 100$$", code_style))
    story.append(Paragraph(
        "The four foundational pillars and their exact scoring weights are:",
        body_style,
    ))
    story.append(Paragraph("1. <b>Profitability (35%):</b> Return on Equity (15%), Return on Capital Employed (10%), Net Profit Margin (10%).", bullet_style))
    story.append(Paragraph("2. <b>Cash Quality (30%):</b> 5-Year FCF CAGR (15%), CFO/Operating Profit Quality Ratio (10%), Positive FCF Bonus (5%).", bullet_style))
    story.append(Paragraph("3. <b>Growth (20%):</b> 5-Year Compounded Revenue CAGR (10%), 5-Year PAT CAGR (10%).", bullet_style))
    story.append(Paragraph("4. <b>Leverage & Solvency (15%):</b> Debt-to-Equity (10%, inverted), Interest Coverage Ratio (5%). Financial sector companies are exempted from standard industrial D/E penalties.", bullet_style))

    story.append(Paragraph("Standard Screener Presets", h2_style))
    preset_tbl = Table([
        ["Preset Key", "Preset Strategy Name", "Target Investment Criteria"],
        ["quality_compounders", "Quality Compounder", "ROE > 15%, D/E <= 1.0 (excl. Financials), FCF > 0, Rev CAGR 5yr > 10%."],
        ["value_picks", "Value Pick", "P/E <= 20.0, P/B <= 4.5, D/E <= 2.0, Dividend Yield >= 1.0%."],
        ["growth_accelerators", "Growth Accelerator", "PAT CAGR 5yr > 20%, Revenue CAGR 5yr > 15%, D/E <= 2.0."],
        ["dividend_champions", "Dividend Champion", "Dividend Yield >= 2.0%, Payout Ratio < 80%, Free Cash Flow > 0."],
        ["debt_free_blue_chips", "Debt-Free Blue Chip", "D/E <= 0.05, ROE > 12.0%, Annual Sales > 5,000 Cr."],
        ["turnaround_watch", "Turnaround Watch", "Revenue CAGR 3yr > 10%, Positive Latest FCF, Declining D/E YoY."],
    ], colWidths=[110, 120, 260])
    preset_tbl.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), NAVY),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("GRID", (0, 0), (-1, -1), 0.5, BORDER_COLOR),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, LIGHT_BG]),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("PADDING", (0, 0), (-1, -1), 4),
    ]))
    story.append(preset_tbl)
    story.append(PageBreak())

    # =========================================================================
    # PAGE 6: TEAR SHEETS, SECTOR & PORTFOLIO REPORTS
    # =========================================================================
    story.append(Paragraph("6. Institutional PDF Reports & Automated Generation", h1_style))
    story.append(HRFlowable(width="100%", thickness=1, color=NAVY, spaceAfter=8))
    story.append(Paragraph(
        "Sprint 5 established automated, publication-quality PDF reporting using ReportLab. "
        "All generated documents adhere strictly to A4 page geometry with zero blank pages, text clipping, or overlapping canvas elements.",
        body_style,
    ))

    story.append(Paragraph("1. Individual Company Tear Sheets (reports/tearsheets/*.pdf)", h2_style))
    story.append(Paragraph(
        "Each eligible company possesses an authoritative <b>exactly two-page</b> PDF tear sheet (file size 47KB–118KB):",
        body_style,
    ))
    story.append(Paragraph("● <b>Page 1:</b> Navy corporate header bar, 6 KPI dashboard tiles (ROE, ROCE, NPM, D/E, Rev CAGR, FCF), 10-year Revenue & Net Profit bar chart, and 10-year ROE/ROCE dual-axis trend line chart.", bullet_style))
    story.append(Paragraph("● <b>Page 2:</b> Balance sheet composition stacked bar chart (Equity vs Borrowings vs Other Liabilities), latest cash-flow waterfall chart (CFO, CFI, CFF, Net), rule-based Strengths & Weaknesses bullet points, and Capital Allocation Pattern badge.", bullet_style))
    story.append(Paragraph("● <b>Eligible Coverage:</b> 91 companies. <b>JIOFIN</b> is documented as skipped due to having only 2 annual observations (<3 required).", bullet_style))

    story.append(Paragraph("2. Broad-Sector Intelligence Reports (reports/sector/*.pdf)", h2_style))
    story.append(Paragraph(
        "A dedicated one-page PDF report for each of the <b>10 authoritative broad sectors</b>. "
        "Each report presents sector median ROE, ROCE, OPM, D/E, 5yr Rev CAGR, total market cap, and a constituent fundamentals table.",
        body_style,
    ))

    story.append(Paragraph("3. Executive Portfolio Summary (reports/portfolio/portfolio_summary.pdf)", h2_style))
    story.append(Paragraph(
        "A comprehensive <b>17-page A4 document</b> indexing all 92 master companies alphabetically by ticker. "
        "Each company card provides: broad sector, fiscal year basis, market cap, portfolio weight, 6 core KPIs, capital allocation pattern, "
        "cash-flow quality label, and 5-year Revenue and PAT CAGR trend direction indicators (Up / Down / Stable).",
        body_style,
    ))
    story.append(PageBreak())

    # =========================================================================
    # PAGE 7: CLUSTERING & STATISTICAL ARCHETYPES (DAY 36–37)
    # =========================================================================
    story.append(Paragraph("7. Statistical Clustering & Company Archetypes", h1_style))
    story.append(HRFlowable(width="100%", thickness=1, color=NAVY, spaceAfter=8))
    story.append(Paragraph(
        "Implemented in `src/analytics/clustering.py`, the statistical clustering pipeline categorizes all 92 companies into "
        "five distinct financial archetypes using unsupervised machine learning.",
        body_style,
    ))

    story.append(Paragraph("Clustering Methodology & Preprocessing", h2_style))
    story.append(Paragraph("● <b>Feature Selection (5 KPIs):</b> Return on Equity (%), Debt-to-Equity, 5-Year Revenue CAGR (%), 5-Year FCF CAGR (%), Operating Profit Margin (%).", bullet_style))
    story.append(Paragraph("● <b>Missing Data Imputation:</b> Missing values are imputed using the company's broad-sector median. If an entire sector lacks data (e.g. FCF CAGR in Communication Services), the portfolio-wide median is used as a deterministic fallback.", bullet_style))
    story.append(Paragraph("● <b>Feature Scaling:</b> Standardized using `StandardScaler` (zero mean, unit variance).", bullet_style))
    story.append(Paragraph("● <b>K-Means Algorithm:</b> Initialized with `n_clusters=5`, `random_state=42`, and Euclidean distance to centroid computed for every company.", bullet_style))

    story.append(Paragraph("Five Provisional Cluster Archetypes", h2_style))
    cluster_tbl = Table([
        ["Cluster ID", "Archetype Designation (Provisional)", "Count", "Profile Summary & Representative Members"],
        ["Cluster 0", "High-Margin Cash Generators", "14", "Very high operating margin (median 85.1%), negligible debt (median 0.05). Members: ADANIPORTS, BHARTIARTL, COALINDIA, HDFCLIFE."],
        ["Cluster 1", "Core Quality Compounders", "60", "Steady revenue growth (11.4%), solid profitability (ROE 17.0%), modest debt (0.17). Members: TCS, INFY, ASIANPAINT, HINDUNILVR, TITAN."],
        ["Cluster 2", "High Capital Turnover & Scale", "2", "PSU defense manufacturing champions with extreme ROE and capital turnover. Members: BEL, HAL."],
        ["Cluster 3", "Hyper FCF Outlier", "1", "Pharmaceutical giant exhibiting hyper-expansion in 5-year free cash flow CAGR (228.8%). Member: CIPLA."],
        ["Cluster 4", "High-Leverage Financials & Utilities", "15", "High financial leverage (D/E mean 7.2) and robust revenue CAGR (19.0%). Members: HDFCBANK, AXISBANK, BAJFINANCE, ADANIGREEN."],
    ], colWidths=[55, 135, 35, 265])
    cluster_tbl.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), NAVY),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 7.5),
        ("GRID", (0, 0), (-1, -1), 0.5, BORDER_COLOR),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, LIGHT_BG]),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("PADDING", (0, 0), (-1, -1), 3),
    ]))
    story.append(cluster_tbl)

    story.append(Paragraph("Statistical Artifacts Generated", h2_style))
    story.append(Paragraph("● `output/cluster_labels.csv`: 92 rows mapping `company_id`, `cluster_id`, `cluster_name`, and `distance_from_centroid`.", bullet_style))
    story.append(Paragraph("● `output/outlier_report.csv`: 9 flagged observations where within-sector absolute Z-score > 3.0 (e.g. INDIGO, PNB, BAJAJHLDNG).", bullet_style))
    story.append(Paragraph("● `output/portfolio_stats.csv`: P10, P25, P50, P75, P90, mean, and standard deviation across primary portfolio KPIs.", bullet_style))
    story.append(Paragraph("● `reports/elbow_plot.png` & `reports/correlation_heatmap.png`: Visual statistical diagnostic figures.", bullet_style))
    story.append(PageBreak())

    # =========================================================================
    # PAGE 8: RESTFUL FASTAPI INTEGRATION GUIDE
    # =========================================================================
    story.append(Paragraph("8. RESTful API Architecture & Endpoint Reference", h1_style))
    story.append(HRFlowable(width="100%", thickness=1, color=NAVY, spaceAfter=8))
    story.append(Paragraph(
        "Implemented in `src/api/main.py`, the FastAPI server provides 21 endpoints under `/api/v1`. "
        "It features automated request timing/logging middleware, CORS headers for frontend integration, and interactive OpenAPI docs at `/docs`.",
        body_style,
    ))

    api_tbl = Table([
        ["Method", "Endpoint Path", "Description", "Status Codes"],
        ["GET", "/api/v1/health", "API health & database connectivity check", "200, 503"],
        ["GET", "/api/v1/health/counts", "Table row counts across all SQLite tables", "200, 503"],
        ["GET", "/api/v1/companies", "List universe companies with sector and index weight", "200"],
        ["GET", "/api/v1/companies/{ticker}", "Detailed company profile, ratios, pros/cons", "200, 404"],
        ["GET", "/api/v1/companies/{ticker}/pnl", "Historical profit & loss statements", "200, 404"],
        ["GET", "/api/v1/companies/{ticker}/balancesheet", "Historical balance sheet statements", "200, 404"],
        ["GET", "/api/v1/companies/{ticker}/cashflow", "Historical cash flow statements", "200, 404"],
        ["GET", "/api/v1/companies/{ticker}/ratios", "Complete historical financial ratios", "200, 404"],
        ["GET", "/api/v1/companies/{ticker}/tearsheet", "Download official 2-page PDF tear sheet", "200, 404"],
        ["GET", "/api/v1/screener/presets", "List predefined screener presets", "200, 500"],
        ["GET", "/api/v1/screener", "Run financial screener with presets or custom filters", "200, 400"],
        ["GET", "/api/v1/sectors", "List 10 authoritative broad sectors & medians", "200"],
        ["GET", "/api/v1/sectors/{sector_name}", "Broad sector detail & constituent companies", "200, 404"],
        ["GET", "/api/v1/peers", "List 11 industry peer cohorts & benchmarks", "200"],
        ["GET", "/api/v1/peers/{group_name}", "Peer group members & percentile rankings", "200, 404"],
        ["GET", "/api/v1/companies/{ticker}/peers", "Company peer group benchmarking & percentiles", "200, 404"],
        ["GET", "/api/v1/valuation/summary", "Universe valuation summary (PE, PB, EV/EBITDA)", "200"],
        ["GET", "/api/v1/companies/{ticker}/valuation", "Company valuation history & sector multiples", "200, 404"],
        ["GET", "/api/v1/portfolio/stats", "Portfolio KPI distribution stats (P10..P90)", "200, 503"],
        ["GET", "/api/v1/portfolio/clusters", "K-Means archetypes & centroid distances", "200, 400, 503"],
        ["GET", "/api/v1/companies/{ticker}/documents", "Official annual report filing URLs", "200, 404"],
    ], colWidths=[40, 185, 205, 60])
    api_tbl.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), NAVY),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 7),
        ("GRID", (0, 0), (-1, -1), 0.5, BORDER_COLOR),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, LIGHT_BG]),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("PADDING", (0, 0), (-1, -1), 2.5),
    ]))
    story.append(api_tbl)
    story.append(PageBreak())

    # =========================================================================
    # PAGE 9: PRACTICAL API CODE EXAMPLES
    # =========================================================================
    story.append(Paragraph("9. Practical API Code Examples (Python & cURL)", h1_style))
    story.append(HRFlowable(width="100%", thickness=1, color=NAVY, spaceAfter=8))

    story.append(Paragraph("Starting the API Server Locally", h2_style))
    story.append(Paragraph("uvicorn src.api.main:app --host 127.0.0.1 --port 8000 --reload", code_style))

    story.append(Paragraph("Example 1: Running the Quality Compounder Screener via Python", h2_style))
    story.append(Paragraph(
        """import requests

url = "http://127.0.0.1:8000/api/v1/screener"
params = {"preset": "quality_compounders", "limit": 5}
response = requests.get(url, params=params)
data = response.json()

print(f"Matched {data['total_matched']} companies:")
for co in data['results']:
    print(f"- {co['company_id']} ({co['company_name']}): Score {co['composite_quality_score']}")
""",
        code_style,
    ))

    story.append(Paragraph("Example 2: Downloading a Company PDF Tear Sheet via cURL", h2_style))
    story.append(Paragraph(
        "curl -X GET http://127.0.0.1:8000/api/v1/companies/TCS/tearsheet --output TCS_tearsheet.pdf",
        code_style,
    ))

    story.append(Paragraph("Example 3: Querying Portfolio Clustering Archetypes", h2_style))
    story.append(Paragraph(
        """import requests

url = "http://127.0.0.1:8000/api/v1/portfolio/clusters"
res = requests.get(url, params={"cluster_id": 1}).json()
print(f"Cluster 1 count: {len(res['assignments'])}")
for row in res['assignments'][:5]:
    print(f"  {row['company_id']}: dist={row['distance_from_centroid']}")
""",
        code_style,
    ))
    story.append(PageBreak())

    # =========================================================================
    # PAGE 10: TROUBLESHOOTING & DOCUMENTED EXCEPTIONS
    # =========================================================================
    story.append(Paragraph("10. Troubleshooting & Documented Data Exceptions", h1_style))
    story.append(HRFlowable(width="100%", thickness=1, color=NAVY, spaceAfter=8))
    story.append(Paragraph(
        "Institutional integrity requires complete transparency regarding source data anomalies, edge cases, and known exceptions. "
        "The following findings were documented across Sprints 1–5 and verified in Sprint 6:",
        body_style,
    ))

    story.append(Paragraph("Documented Platform Exceptions", h2_style))
    exc_tbl = Table([
        ["Issue / Exception", "Root Cause & Source Evidence", "Platform Resolution & System Behavior"],
        ["JIOFIN Skipped Tearsheet", "JIOFIN has only 2 annual P&L observations in source data (demerged recently).", "Logged in `output/skipped_tearsheets.csv`; API returns 404 with descriptive explanation."],
        ["SBIN & SIEMENS No-Con Trigger", "SBIN has no raw balance sheet rows; SIEMENS triggered no negative NLP threshold.", "Documented in `output/pros_cons_unresolved.csv`; both companies retain valid Pros."],
        ["10 Sectors vs 11 Peer Cohorts", "Sectors table has 10 broad economic sectors; peer analysis uses 11 industry cohorts.", "Preserved without artificial distortion: /api/v1/sectors returns 10, /api/v1/peers returns 11."],
        ["INFY CAGR Flag for Review", "10.2 percentage point divergence between text-parsed sales CAGR and calculated CAGR.", "Logged in `output/cagr_cross_validation.csv` as FLAG_FOR_REVIEW without silent tampering."],
        ["WIPRO Parser Failure", "WIPRO text appears in source filings but WIPRO is not in the 92 master company list.", "Documented in `output/parse_failures.csv` as an unmapped ticker."],
        ["Cash Accumulator Zero Count", "No company in the latest annual period simultaneously had +CFO, +CFI, +CFF.", "Taxonomy retains all 8 patterns; distribution CSV correctly reflects 0 count."],
    ], colWidths=[110, 170, 210])
    exc_tbl.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), NAVY),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 7.5),
        ("GRID", (0, 0), (-1, -1), 0.5, BORDER_COLOR),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, LIGHT_BG]),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("PADDING", (0, 0), (-1, -1), 3),
    ]))
    story.append(exc_tbl)

    story.append(Paragraph("Common Operational Troubleshooting", h2_style))
    story.append(Paragraph("● <b>Port Collisions:</b> Ensure Streamlit runs on port 8501 and FastAPI on port 8000. Verify with `netstat -ano | findstr :8000`.", bullet_style))
    story.append(Paragraph("● <b>Database Locks:</b> SQLite operates in WAL or standard rollback mode. Do not perform external write transactions while running batch ETL.", bullet_style))
    story.append(Paragraph("● <b>Pytest HTML Reports:</b> Generated via `pytest --html=reports/pytest_report.html --self-contained-html`.", bullet_style))
    story.append(PageBreak())

    # =========================================================================
    # PAGE 11: PRODUCTION RUNBOOK & VERIFICATION SIGN-OFF
    # =========================================================================
    story.append(Paragraph("11. Production Operations Runbook & Audit Sign-Off", h1_style))
    story.append(HRFlowable(width="100%", thickness=1, color=NAVY, spaceAfter=8))
    story.append(Paragraph(
        "This section outlines standard procedures for maintaining, testing, and auditing the platform in local production environments.",
        body_style,
    ))

    story.append(Paragraph("Essential Execution Commands", h2_style))
    story.append(Paragraph("# 1. Run Complete Automated Regression Test Suite\npython -m pytest --html=reports/pytest_report.html --self-contained-html", code_style))
    story.append(Paragraph("# 2. Execute Statistical Clustering & Analysis Pipeline\npython -m src.analytics.clustering", code_style))
    story.append(Paragraph("# 3. Launch Local RESTful API Server\nuvicorn src.api.main:app --host 127.0.0.1 --port 8000", code_style))
    story.append(Paragraph("# 4. Launch Interactive Analytical Dashboard\nstreamlit run src/dashboard/app.py --server.port 8501", code_style))
    story.append(Paragraph("# 5. Run Performance & Integration Benchmarks\npython scripts/benchmark_perf.py", code_style))

    story.append(Paragraph("Verification Gate Status & Team Approvals", h2_style))
    story.append(Paragraph(
        "All 20 Sprint 6 acceptance criteria (AC-01 through AC-20) have been technically audited and verified. "
        "This guide, the underlying software artifacts, and the test reports provide factual evidence of system behavior. "
        "Final operational deployment and cluster archetype designations remain <b>Provisional</b> pending formal team-lead review and sign-off.",
        body_style,
    ))

    story.append(Spacer(1, 15))
    signoff_tbl = Table([
        ["Role", "Designation", "Verification Status", "Date"],
        ["Implementation Lead", "Senior Python Agentic Engineer", "COMPLETED (Technically Verified)", "2026-10-23"],
        ["Quantitative Reviewer", "Financial Data Lead", "PROVISIONAL (Pending Review)", "Outstanding"],
        ["Product Owner / Team Lead", "svgBA100 Project Director", "PROVISIONAL (Pending Sign-off)", "Outstanding"],
    ], colWidths=[120, 140, 140, 90])
    signoff_tbl.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), STEEL),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("GRID", (0, 0), (-1, -1), 0.5, BORDER_COLOR),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, LIGHT_BG]),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("PADDING", (0, 0), (-1, -1), 4),
    ]))
    story.append(signoff_tbl)

    doc.build(story, canvasmaker=NumberedCanvas)
    return output_path


if __name__ == "__main__":
    out = build_analyst_guide()
    print("Analyst guide generated at:", out)

