"""Generate one data-backed PDF report for each broad sector."""

import argparse
import os
import re
from datetime import date
from statistics import median
from typing import Any, Dict, List
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import (
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


def _format_number(value: Any, suffix: str = "", decimals: int = 1) -> str:
    if value is None:
        return "N/A"
    return f"{float(value):,.{decimals}f}{suffix}"


def _median(rows: List[Dict[str, Any]], field: str) -> Any:
    values = [float(row[field]) for row in rows if row[field] is not None]
    return median(values) if values else None


def _page_footer(canvas, document) -> None:
    canvas.saveState()
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(colors.HexColor("#7F8C8D"))
    canvas.drawString(MARGIN, 0.8 * cm, "svgBA100 Financial Intelligence Platform")
    canvas.drawRightString(PAGE_W - MARGIN, 0.8 * cm, f"Page {document.page}")
    canvas.restoreState()


def generate_sector_report(
    sector: str,
    output_path: str,
    db_path: str = DB_PATH,
) -> Dict[str, Any]:
    """Generate a sector PDF with median KPIs and its company-level data."""
    rows = [
        row for row in load_company_summaries(db_path)
        if row["sector"] == sector
    ]
    if not rows:
        raise ValueError(f"No companies found for sector {sector!r}")

    rows.sort(
        key=lambda row: (
            row["market_cap"] is not None,
            row["market_cap"] or 0,
        ),
        reverse=True,
    )
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    doc = SimpleDocTemplate(
        output_path,
        pagesize=A4,
        leftMargin=MARGIN,
        rightMargin=MARGIN,
        topMargin=MARGIN,
        bottomMargin=MARGIN,
        title=f"{sector} Sector Report",
        author="svgBA100 Financial Intelligence Platform",
    )
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "SectorTitle", parent=styles["Title"], fontName="Helvetica-Bold",
        fontSize=18, leading=22, textColor=WHITE, alignment=0,
    )
    section_style = ParagraphStyle(
        "SectorSection", parent=styles["Heading2"], fontSize=11,
        textColor=NAVY, spaceBefore=8, spaceAfter=5,
    )
    body_style = ParagraphStyle(
        "SectorBody", parent=styles["BodyText"], fontSize=8, leading=10,
    )

    header = Table(
        [[Paragraph(escape(sector), title_style)],
         [Paragraph(
             f"{len(rows)} companies | Data as of {escape(str(rows[0]['fiscal_year'] or 'N/A'))}"
             f" | Generated {date.today():%d %b %Y}",
             ParagraphStyle(
                 "SectorSubtitle", parent=styles["Normal"], fontSize=8,
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

    metric_specs = [
        ("Median Market Cap", "market_cap", " Cr", 0),
        ("Median ROE", "roe", "%", 1),
        ("Median ROCE", "roce", "%", 1),
        ("Median P/E", "pe_ratio", "x", 1),
        ("Median D/E", "debt_to_equity", "x", 2),
        ("Median Quality Score", "quality_score", "", 1),
    ]
    metric_rows = [["Sector Metric", "Median", "Available"]]
    for label, field, suffix, decimals in metric_specs:
        count = sum(row[field] is not None for row in rows)
        metric_rows.append([
            label,
            _format_number(_median(rows, field), suffix, decimals),
            f"{count}/{len(rows)}",
        ])
    metric_table = Table(metric_rows, colWidths=[doc.width * .48, doc.width * .30, doc.width * .22])
    metric_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), NAVY),
        ("TEXTCOLOR", (0, 0), (-1, 0), WHITE),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("BACKGROUND", (0, 1), (-1, -1), LIGHT_GREY),
        ("GRID", (0, 0), (-1, -1), .35, colors.HexColor("#DDE1E6")),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("ALIGN", (1, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))

    company_rows = [[
        "Ticker", "Company", "Mkt Cap (Cr)", "ROE %", "ROCE %", "D/E", "Quality",
    ]]
    for row in rows:
        company_rows.append([
            row["ticker"],
            Paragraph(escape(row["company_name"]), body_style),
            _format_number(row["market_cap"], decimals=0),
            _format_number(row["roe"], decimals=1),
            _format_number(row["roce"], decimals=1),
            _format_number(row["debt_to_equity"], decimals=2),
            _format_number(row["quality_score"], decimals=1),
        ])
    company_table = Table(
        company_rows,
        colWidths=[
            doc.width * .10, doc.width * .34, doc.width * .15,
            doc.width * .10, doc.width * .10, doc.width * .09, doc.width * .12,
        ],
        repeatRows=1,
    )
    company_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), NAVY),
        ("TEXTCOLOR", (0, 0), (-1, 0), WHITE),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 7),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [WHITE, LIGHT_GREY]),
        ("GRID", (0, 0), (-1, -1), .3, colors.HexColor("#DDE1E6")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ALIGN", (2, 0), (-1, -1), "RIGHT"),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))

    elements = [
        header,
        Spacer(1, 10),
        Paragraph("Sector Snapshot", section_style),
        metric_table,
        Spacer(1, 8),
        Paragraph("Company Fundamentals", section_style),
        company_table,
    ]
    doc.build(elements, onFirstPage=_page_footer, onLaterPages=_page_footer)
    return {
        "sector": sector,
        "company_count": len(rows),
        "output_path": output_path,
        "median_market_cap": _median(rows, "market_cap"),
    }


def generate_all_sector_reports(
    output_dir: str = "reports/sector",
    db_path: str = DB_PATH,
) -> Dict[str, Any]:
    """Generate one PDF for every broad sector represented in the database."""
    rows = load_company_summaries(db_path)
    sectors = sorted({row["sector"] for row in rows})
    os.makedirs(output_dir, exist_ok=True)
    results = []
    for sector in sectors:
        slug = re.sub(r"[^a-z0-9]+", "_", sector.lower()).strip("_")
        output_path = os.path.join(output_dir, f"{slug}_sector_report.pdf")
        results.append(generate_sector_report(sector, output_path, db_path))
    return {
        "sector_count": len(results),
        "company_count": sum(item["company_count"] for item in results),
        "reports": results,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate Sprint 5 sector reports")
    parser.add_argument("--db", default=DB_PATH)
    parser.add_argument("--output-dir", default="reports/sector")
    args = parser.parse_args()
    summary = generate_all_sector_reports(args.output_dir, args.db)
    print(
        f"Generated {summary['sector_count']} sector reports "
        f"covering {summary['company_count']} companies"
    )
