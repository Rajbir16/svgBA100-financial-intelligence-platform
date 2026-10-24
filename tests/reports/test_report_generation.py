"""Integration tests for Sprint 5 tear-sheet, sector, and portfolio PDFs."""

import csv
import re
import sqlite3
from pathlib import Path

try:
    from pypdf import PdfReader
except ImportError:
    from PyPDF2 import PdfReader

from src.reports import tearsheet
from src.reports.portfolio_report import generate_portfolio_report
from src.reports.report_data import DB_PATH, load_company_summaries
from src.reports.sector_report import generate_sector_report


def _assert_a4_pages(pdf_path: Path, expected_pages=None) -> str:
    reader = PdfReader(str(pdf_path))
    assert reader.pages
    if expected_pages is not None:
        assert len(reader.pages) == expected_pages
    for page in reader.pages:
        assert abs(float(page.mediabox.width) - 595.28) < 1
        assert abs(float(page.mediabox.height) - 841.89) < 1
    return "\n".join(page.extract_text() or "" for page in reader.pages)


def test_company_tearsheet_is_two_pages_with_key_sections(tmp_path):
    output_path = tmp_path / "TCS_tearsheet.pdf"

    assert tearsheet.generate_tearsheet("TCS", str(output_path), DB_PATH)
    text = _assert_a4_pages(output_path, expected_pages=2)
    reader = PdfReader(str(output_path))

    assert "TCS" in text
    assert len(reader.pages[0].images) >= 2
    assert "Detailed Analysis" in text
    assert "Capital Allocation Pattern" in text


def test_sector_report_contains_company_fundamentals(tmp_path):
    output_path = tmp_path / "consumer_staples.pdf"

    summary = generate_sector_report(
        "Consumer Staples", str(output_path), DB_PATH
    )
    text = _assert_a4_pages(output_path)

    assert summary["company_count"] == 7
    assert "Consumer Staples" in text
    assert "Sector Snapshot" in text
    assert "Company Fundamentals" in text
    assert "Ticker" in text


def test_portfolio_report_contains_full_universe_and_sector_allocation(tmp_path):
    output_path = tmp_path / "portfolio_summary.pdf"

    summary = generate_portfolio_report(str(output_path), DB_PATH)
    text = _assert_a4_pages(output_path)

    assert summary["company_count"] == 92
    assert summary["market_cap_coverage"] == 92
    assert "Nifty 100 Portfolio Summary" in text
    assert "Sector Allocation by Market Capitalization" in text
    assert "Top 10 Holdings" in text
    assert "Company Summaries" in text
    assert "Cash-Flow Quality" in text
    assert "Capital Allocation" in text
    assert "Revenue CAGR (5Y)" in text
    assert "PAT CAGR (5Y)" in text
    assert "Net Profit Margin" in text
    assert "Debt-to-Equity" in text
    assert "Free Cash Flow" in text
    for summary_row in load_company_summaries(DB_PATH):
        assert len(re.findall(
            r"(?<![A-Z0-9])" + re.escape(summary_row["ticker"]) + r"(?![A-Z0-9])",
            text,
        )) == 1


def test_tearsheet_batch_records_only_ineligible_and_failed_companies(
    tmp_path, monkeypatch
):
    db_path = tmp_path / "companies.db"
    with sqlite3.connect(str(db_path)) as conn:
        conn.executescript(
            """
            CREATE TABLE companies (id TEXT PRIMARY KEY, company_name TEXT);
            CREATE TABLE profitandloss (company_id TEXT, year TEXT);
            INSERT INTO companies VALUES ('GOOD', 'Good Company');
            INSERT INTO companies VALUES ('SHORT', 'Short History Ltd');
            INSERT INTO companies VALUES ('FAIL', 'Failed Generation Ltd');
            INSERT INTO profitandloss VALUES ('GOOD', 'Mar 2022');
            INSERT INTO profitandloss VALUES ('GOOD', 'Mar 2023');
            INSERT INTO profitandloss VALUES ('GOOD', 'Mar 2024');
            INSERT INTO profitandloss VALUES ('SHORT', 'Mar 2024');
            INSERT INTO profitandloss VALUES ('FAIL', 'Mar 2022');
            INSERT INTO profitandloss VALUES ('FAIL', 'Mar 2023');
            INSERT INTO profitandloss VALUES ('FAIL', 'Mar 2024');
            """
        )

    def fake_generate(ticker, *_):
        return ticker == "GOOD"

    monkeypatch.setattr(tearsheet, "generate_tearsheet", fake_generate)
    skipped_path = tmp_path / "skipped.csv"
    summary = tearsheet.generate_all_tearsheets(
        output_dir=str(tmp_path / "tearsheets"),
        db_path=str(db_path),
        skipped_csv=str(skipped_path),
    )

    assert summary["total_companies"] == 3
    assert summary["generated_tickers"] == ["GOOD"]
    assert [row["ticker"] for row in summary["skipped_details"]] == [
        "FAIL", "SHORT"
    ]
    with skipped_path.open(newline="", encoding="utf-8") as csv_file:
        skipped_rows = list(csv.DictReader(csv_file))
    assert [row["ticker"] for row in skipped_rows] == ["FAIL", "SHORT"]


def test_report_data_covers_the_full_company_universe():
    summaries = load_company_summaries(DB_PATH)

    assert len(summaries) == 92
    assert all(row["ticker"] and row["fiscal_year"] for row in summaries)
    assert all(row["market_cap"] is not None for row in summaries)
