"""Generate a portfolio-level PDF summary for the Nifty 100 universe."""

import argparse
import os
import re
from collections import defaultdict
from datetime import date
from typing import Any, Dict, List
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import (
    KeepTogether,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from src.reports.report_data import DB_PATH, load_company_summaries


PAGE_W, _ = A4
MARGIN = 1.5 * cm
NAVY = colors.HexColor("#1B2A4A")
LIGHT_GREY = colors.HexColor("#F5F6FA")
WHITE = colors.white
GRID = colors.HexColor("#DDE1E6")


def _format_number(value: Any, suffix: str = "", decimals: int = 1) -> str:
    if value is None:
        return "N/A"
    return f"{float(value):,.{decimals}f}{suffix}"


def _page_footer(canvas, document) -> None:
    canvas.saveState()
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(colors.HexColor("#7F8C8D"))
    canvas.drawString(MARGIN, 0.8 * cm, "svgBA100 Financial Intelligence Platform")
    canvas.drawRightString(PAGE_W - MARGIN, 0.8 * cm, f"Page {document.page}")
    canvas.restoreState()


def _table_style(header_rows: int = 1) -> TableStyle:
    return TableStyle([
        ("BACKGROUND", (0, 0), (-1, header_rows - 1), NAVY),
        ("TEXTCOLOR", (0, 0), (-1, header_rows - 1), WHITE),
        ("FONTNAME", (0, 0), (-1, header_rows - 1), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 7),
        ("ROWBACKGROUNDS", (0, header_rows), (-1, -1), [WHITE, LIGHT_GREY]),
        ("GRID", (0, 0), (-1, -1), .3, GRID),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ])


def _trend(value: Any, flag: Any) -> str:
    status = str(flag or "UNAVAILABLE").upper()
    return f"{_format_number(value, '%', 1)} ({escape(status)})"


def _company_card(row: Dict[str, Any], width: float, styles: Any) -> Table:
    header_style = ParagraphStyle(
        "HoldingHeader", parent=styles["Normal"], fontName="Helvetica-Bold",
        fontSize=9, leading=11, textColor=WHITE,
    )
    label_style = ParagraphStyle(
        "HoldingLabel", parent=styles["Normal"], fontName="Helvetica-Bold",
        fontSize=7.5, leading=9, textColor=NAVY,
    )
    value_style = ParagraphStyle(
        "HoldingValue", parent=styles["Normal"], fontSize=7.5, leading=9,
    )

    ticker = str(row["ticker"])
    company_name = str(row["company_name"])
    ticker_in_name = re.search(
        r"(?<![A-Z0-9])" + re.escape(ticker) + r"(?![A-Z0-9])",
        company_name,
    )
    company_identity = (
        escape(company_name) if ticker_in_name
        else f"{escape(ticker)} - {escape(company_name)}"
    )
    identity = (
        f"{company_identity} | {escape(str(row['sector']))}"
        f" | FY {escape(str(row['fiscal_year']))}"
    )
    metric_pairs = [
        ("Market Cap", _format_number(row["market_cap"], " Cr", 0),
         "Portfolio Weight", _format_number(row.get("weight_pct"), "%", 2)),
        ("ROE", _format_number(row.get("roe"), "%", 1),
         "ROCE", _format_number(row.get("roce"), "%", 1)),
        ("Net Profit Margin", _format_number(row.get("net_profit_margin"), "%", 1),
         "Debt-to-Equity", _format_number(row.get("debt_to_equity"), "x", 2)),
        ("Free Cash Flow", _format_number(row.get("free_cash_flow"), " Cr", 1),
         "Quality Score", _format_number(row.get("quality_score"), "", 1)),
        (
            "Cash-Flow Quality",
            f"{_format_number(row.get('cashflow_quality_score'), 'x', 2)} "
            f"({escape(str(row.get('cashflow_quality_label') or 'Insufficient Data'))})",
            "Capital Allocation",
            escape(str(row.get("capital_allocation") or "Insufficient Data")),
        ),
        (
            "Revenue CAGR (5Y)",
            _trend(row.get("revenue_cagr_5yr"), row.get("revenue_cagr_5yr_flag")),
            "PAT CAGR (5Y)",
            _trend(row.get("pat_cagr_5yr"), row.get("pat_cagr_5yr_flag")),
        ),
    ]
    data = [[Paragraph(identity, header_style), "", "", ""]]
    for label_a, value_a, label_b, value_b in metric_pairs:
        data.append([
            Paragraph(label_a, label_style),
            Paragraph(str(value_a), value_style),
            Paragraph(label_b, label_style),
            Paragraph(str(value_b), value_style),
        ])

    card = Table(
        data,
        colWidths=[width * .19, width * .31, width * .19, width * .31],
        hAlign="LEFT",
    )
    card.setStyle(TableStyle([
        ("SPAN", (0, 0), (-1, 0)),
        ("BACKGROUND", (0, 0), (-1, 0), NAVY),
        ("BACKGROUND", (0, 1), (-1, -1), LIGHT_GREY),
        ("GRID", (0, 0), (-1, -1), .3, GRID),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    return card


def generate_portfolio_report(
    output_path: str = "reports/portfolio/portfolio_summary.pdf",
    db_path: str = DB_PATH,
) -> Dict[str, Any]:
    """Create an overview, sector allocation, and a detailed card per company."""
    rows = load_company_summaries(db_path)
    if not rows:
        raise ValueError("No company data is available for the portfolio report")

    total_market_cap = sum(
        float(row["market_cap"]) for row in rows
        if row["market_cap"] is not None and float(row["market_cap"]) > 0
    )
    covered_market_caps = sum(row["market_cap"] is not None for row in rows)
    for row in rows:
        market_cap = row["market_cap"]
        row["weight_pct"] = (
            float(market_cap) / total_market_cap * 100
            if market_cap is not None and total_market_cap > 0 else None
        )
    ranked = sorted(
        rows,
        key=lambda row: (
            row["market_cap"] is not None,
            row["market_cap"] or 0,
        ),
        reverse=True,
    )

    sector_groups: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for row in rows:
        sector_groups[row["sector"]].append(row)
    sector_rows = []
    for sector, members in sorted(sector_groups.items()):
        sector_cap = sum(
            float(row["market_cap"]) for row in members
            if row["market_cap"] is not None and float(row["market_cap"]) > 0
        )
        sector_rows.append([
            sector,
            str(len(members)),
            _format_number(sector_cap, decimals=0),
            _format_number(
                sector_cap / total_market_cap * 100 if total_market_cap else None,
                "%",
                1,
            ),
        ])

    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    doc = SimpleDocTemplate(
        output_path,
        pagesize=A4,
        leftMargin=MARGIN,
        rightMargin=MARGIN,
        topMargin=MARGIN,
        bottomMargin=MARGIN,
        title="Nifty 100 Portfolio Summary",
        author="svgBA100 Financial Intelligence Platform",
    )
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "PortfolioTitle", parent=styles["Title"], fontName="Helvetica-Bold",
        fontSize=18, leading=22, textColor=WHITE, alignment=0,
    )
    section_style = ParagraphStyle(
        "PortfolioSection", parent=styles["Heading2"], fontSize=11,
        textColor=NAVY, spaceBefore=8, spaceAfter=5,
    )
    body_style = ParagraphStyle(
        "PortfolioBody", parent=styles["BodyText"], fontSize=8, leading=10,
    )
    header = Table(
        [[Paragraph("Nifty 100 Portfolio Summary", title_style)],
         [Paragraph(
             f"{len(rows)} companies | Market-cap coverage {covered_market_caps}/{len(rows)}"
             f" | Generated {date.today():%d %b %Y}",
             ParagraphStyle(
                 "PortfolioSubtitle", parent=styles["Normal"], fontSize=8,
                 textColor=colors.HexColor("#D5D9E2"),
             ),
         )]],
        colWidths=[doc.width],
        rowHeights=[30, 18],
    )
    header.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), NAVY),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 10),
    ]))

    summary_table = Table(
        [
            ["Companies", "Total Market Cap", "Market-Cap Coverage", "Fiscal Data"],
            [
                str(len(rows)),
                _format_number(total_market_cap, " Cr", 0),
                f"{covered_market_caps}/{len(rows)}",
                escape(str(max(
                    (row["fiscal_year"] for row in rows if row["fiscal_year"] != "N/A"),
                    default="N/A",
                ))),
            ],
        ],
        colWidths=[doc.width * .18, doc.width * .34, doc.width * .24, doc.width * .24],
    )
    summary_table.setStyle(_table_style())

    sector_table = Table(
        [["Sector", "Companies", "Market Cap (Cr)", "Portfolio Weight"]]
        + sector_rows,
        colWidths=[doc.width * .40, doc.width * .18, doc.width * .23, doc.width * .19],
        repeatRows=1,
    )
    sector_table.setStyle(_table_style())

    top_rows = [["Rank", "Company", "Sector", "Mkt Cap (Cr)", "Weight"]]
    for rank, row in enumerate(ranked[:10], start=1):
        top_rows.append([
            str(rank),
            Paragraph(escape(row["company_name"]), body_style),
            Paragraph(escape(row["sector"]), body_style),
            _format_number(row["market_cap"], decimals=0),
            _format_number(row["weight_pct"], "%", 2),
        ])
    top_table = Table(
        top_rows,
        colWidths=[
            doc.width * .08, doc.width * .39, doc.width * .24,
            doc.width * .17, doc.width * .12,
        ],
        repeatRows=1,
    )
    top_table.setStyle(_table_style())

    summary_heading = ParagraphStyle(
        "CompanySummaryHeading", parent=section_style,
        keepWithNext=True,
    )
    elements = [
        header,
        Spacer(1, 10),
        Paragraph("Portfolio Overview", section_style),
        summary_table,
        Spacer(1, 8),
        Paragraph("Sector Allocation by Market Capitalization", section_style),
        sector_table,
        Spacer(1, 8),
        Paragraph("Top 10 Holdings", section_style),
        top_table,
        PageBreak(),
        Paragraph("Company Summaries", summary_heading),
        Paragraph(
            "Each company card reports its latest usable annual KPIs, cash-flow "
            "quality, capital-allocation pattern, and five-year growth trends.",
            body_style,
        ),
        Spacer(1, 7),
    ]
    for row in ranked:
        elements.append(KeepTogether([
            _company_card(row, doc.width, styles),
            Spacer(1, 5),
        ]))

    doc.build(elements, onFirstPage=_page_footer, onLaterPages=_page_footer)
    return {
        "company_count": len(rows),
        "market_cap_coverage": covered_market_caps,
        "total_market_cap": total_market_cap,
        "output_path": output_path,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate Sprint 5 portfolio summary")
    parser.add_argument("--db", default=DB_PATH)
    parser.add_argument(
        "--output",
        default="reports/portfolio/portfolio_summary.pdf",
    )
    args = parser.parse_args()
    summary = generate_portfolio_report(args.output, args.db)
    print(
        f"Generated portfolio report for {summary['company_count']} companies "
        f"at {summary['output_path']}"
    )
