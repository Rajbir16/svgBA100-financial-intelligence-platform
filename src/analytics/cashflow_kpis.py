"""Cash-flow KPI and capital-allocation formulas."""

import os
import re
import sqlite3
from collections import Counter, defaultdict
from typing import Any, Dict, List, Optional, Sequence, Tuple

import pandas as pd


ALL_PATTERNS = (
    "Shareholder Returns",
    "Reinvestor",
    "Mixed",
    "Growth Funded by Debt",
    "Liquidating Assets",
    "Distress Signal",
    "Pre-Revenue",
    "Cash Accumulator",
)

_MONTHS = {
    "Jan": 1, "Feb": 2, "Mar": 3, "Apr": 4, "May": 5, "Jun": 6,
    "Jul": 7, "Aug": 8, "Sep": 9, "Oct": 10, "Nov": 11, "Dec": 12,
}


def _year_key(value: Any) -> Optional[Tuple[int, int]]:
    match = re.fullmatch(r"([A-Za-z]{3})\s+(\d{4})", str(value or "").strip())
    if match:
        month = _MONTHS.get(match.group(1).title())
        return (int(match.group(2)), month) if month is not None else None
    match = re.fullmatch(r"(\d{4})", str(value or "").strip())
    if match:
        return int(match.group(1)), 3
    return None


def free_cash_flow(operating_activity: Optional[float], investing_activity: Optional[float]) -> Optional[float]:
    if operating_activity is None or investing_activity is None:
        return None
    return operating_activity + investing_activity


def cfo_quality(cfo_values: Sequence[Optional[float]], pat_values: Sequence[Optional[float]]) -> Optional[float]:
    ratios = [cfo / pat for cfo, pat in zip(cfo_values, pat_values) if cfo is not None and pat not in (None, 0)]
    return sum(ratios) / len(ratios) if ratios else None


def cfo_quality_label(value: Optional[float]) -> str:
    if value is None:
        return "Insufficient Data"
    if value > 1:
        return "High Quality"
    if value >= 0.5:
        return "Moderate"
    return "Accrual Risk"


def capex_intensity(investing_activity: Optional[float], sales: Optional[float]) -> Optional[float]:
    if investing_activity is None or sales in (None, 0):
        return None
    return abs(investing_activity) / abs(sales) * 100


def capex_label(value: Optional[float]) -> str:
    if value is None:
        return "Insufficient Data"
    if value < 3:
        return "Asset Light"
    if value <= 8:
        return "Moderate"
    return "Capital Intensive"


def fcf_conversion(fcf: Optional[float], operating_profit: Optional[float]) -> Optional[float]:
    if fcf is None or operating_profit in (None, 0):
        return None
    return fcf / operating_profit * 100


def sign(value: Optional[float]) -> str:
    return "+" if value is not None and value > 0 else "-" if value is not None and value < 0 else "0"


def capital_allocation_pattern(cfo: Optional[float], cfi: Optional[float], cff: Optional[float], quality: Optional[float] = None) -> Tuple[str, str, str, str]:
    signs = (sign(cfo), sign(cfi), sign(cff))
    labels = {
        ("+", "-", "-"): "Shareholder Returns" if quality is not None and quality > 1 else "Reinvestor",
        ("+", "+", "-"): "Liquidating Assets",
        ("-", "+", "+"): "Distress Signal",
        ("-", "-", "+"): "Growth Funded by Debt",
        ("+", "+", "+"): "Cash Accumulator",
        ("-", "-", "-"): "Pre-Revenue",
        ("+", "-", "+"): "Mixed",
    }
    return (*signs, labels.get(signs, "Mixed"))


def compute_fcf_cagr_5yr(
    fcf_by_year: Dict[int, Optional[float]],
    latest_year: int = 2024,
) -> Tuple[Optional[float], str]:
    """Compute a five-year FCF CAGR and preserve turnaround/decline cases."""
    start = fcf_by_year.get(latest_year - 5)
    end = fcf_by_year.get(latest_year)
    if start is None or end is None:
        return None, "INSUFFICIENT"
    if start <= 0 < end:
        return None, "TURNAROUND"
    if start > 0 >= end:
        return None, "DECLINE_TO_LOSS"
    if start <= 0 or end <= 0:
        return None, "INSUFFICIENT"
    return ((end / start) ** (1 / 5.0) - 1) * 100, "NORMAL"


def compute_pattern_distribution(patterns: Sequence[str]) -> List[Dict[str, Any]]:
    """Return counts and percentages for the eight canonical patterns."""
    unknown = set(patterns).difference(ALL_PATTERNS)
    if unknown:
        raise ValueError(f"Unknown capital-allocation patterns: {sorted(unknown)}")
    counts = Counter(patterns)
    total = sum(counts.values())
    return [
        {
            "pattern_label": label,
            "company_count": counts.get(label, 0),
            "percentage_pct": counts.get(label, 0) / total * 100 if total else 0.0,
        }
        for label in ALL_PATTERNS
    ]


def detect_pattern_changes(records: Sequence[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Report transitions between adjacent annual patterns for each company."""
    companies: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for record in records:
        year_key = _year_key(record.get("year"))
        if year_key is not None:
            companies[str(record["company_id"])].append(record)

    changes = []
    for company_records in companies.values():
        ordered = sorted(company_records, key=lambda record: _year_key(record["year"]))
        for previous, current in zip(ordered, ordered[1:]):
            if previous["pattern_label"] == current["pattern_label"]:
                continue
            changes.append({
                "company_id": current["company_id"],
                "company_name": current.get("company_name", ""),
                "previous_year": previous["year"],
                "previous_pattern": previous["pattern_label"],
                "current_year": current["year"],
                "current_pattern": current["pattern_label"],
            })
    return changes


def is_distress(
    operating_activity: Optional[float],
    financing_activity: Optional[float],
) -> bool:
    """Flag negative operating cash flow funded by positive financing flow."""
    return (
        operating_activity is not None
        and financing_activity is not None
        and operating_activity < 0
        and financing_activity > 0
    )


def is_deleveraging(
    financing_activity: Optional[float],
    current_borrowings: Optional[float],
    previous_borrowings: Optional[float],
) -> bool:
    """Flag financing outflows accompanied by a reduction in borrowings."""
    return (
        financing_activity is not None
        and current_borrowings is not None
        and previous_borrowings is not None
        and financing_activity < 0
        and current_borrowings < previous_borrowings
    )


def export_cashflow_intelligence_artifacts(
    db_path: str = "nifty100.db",
    output_dir: str = "output",
) -> Dict[str, Any]:
    """Generate the cash-flow intelligence workbook and supporting CSVs."""
    if not os.path.isfile(db_path):
        raise FileNotFoundError(f"Cash-flow intelligence database not found: {db_path}")
    os.makedirs(output_dir, exist_ok=True)

    with sqlite3.connect(db_path) as conn:
        companies = conn.execute(
            "SELECT c.id, c.company_name, COALESCE(s.broad_sector, 'Unclassified') "
            "FROM companies c LEFT JOIN sectors s ON s.company_id = c.id ORDER BY c.id"
        ).fetchall()
        pnl_rows = conn.execute(
            "SELECT company_id, year, sales, net_profit, operating_profit "
            "FROM profitandloss ORDER BY id"
        ).fetchall()
        cashflow_rows = conn.execute(
            "SELECT company_id, year, operating_activity, investing_activity, "
            "financing_activity, net_cash_flow FROM cashflow ORDER BY id"
        ).fetchall()
        balance_rows = conn.execute(
            "SELECT company_id, year, borrowings FROM balancesheet ORDER BY id"
        ).fetchall()
        ratio_rows = conn.execute(
            "SELECT company_id, year, cfo_quality_5yr, cfo_quality_label, "
            "fcf_conversion_pct FROM financial_ratios ORDER BY id"
        ).fetchall()

    pnl_by_key = {}
    for company_id, year, sales, profit, operating_profit in pnl_rows:
        if year != "TTM" and _year_key(year) is not None:
            pnl_by_key[(company_id, year)] = {
                "sales": sales, "profit": profit, "operating_profit": operating_profit,
            }

    annual_cashflows: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for company_id, year, cfo, cfi, cff, net in cashflow_rows:
        key = _year_key(year)
        if year == "TTM" or key is None:
            continue
        record = {
            "company_id": company_id, "year": year, "year_key": key,
            "cfo": cfo, "cfi": cfi, "cff": cff, "net": net,
        }
        annual_cashflows[company_id].append(record)

    borrowings_by_key = {}
    for company_id, year, borrowings in balance_rows:
        if year != "TTM" and _year_key(year) is not None:
            borrowings_by_key[(company_id, year)] = borrowings

    quality_by_key = {}
    for company_id, year, quality, label, conversion in ratio_rows:
        if year != "TTM" and _year_key(year) is not None:
            quality_by_key[(company_id, year)] = {
                "quality": quality, "label": label, "conversion": conversion,
            }

    records_by_company = []
    distress_rows = []
    distribution_labels = []
    pattern_history = []

    for company_id, company_name, sector in companies:
        history = sorted(
            annual_cashflows.get(company_id, []),
            key=lambda record: record["year_key"],
        )
        latest = next(
            (
                record for record in reversed(history)
                if record["cfo"] is not None
                and record["cfi"] is not None
                and record["cff"] is not None
            ),
            None,
        )
        latest_year = latest["year"] if latest else None
        quality_data = quality_by_key.get((company_id, latest_year), {}) if latest_year else {}
        quality = quality_data.get("quality")
        label = quality_data.get("label") or cfo_quality_label(quality)
        pnl = pnl_by_key.get((company_id, latest_year), {}) if latest_year else {}
        capex_pct = capex_intensity(latest["cfi"], pnl.get("sales")) if latest else None
        pattern = capital_allocation_pattern(
            latest["cfo"], latest["cfi"], latest["cff"], quality
        )[-1] if latest else "Mixed"
        distribution_labels.append(pattern)

        fcf_by_year = {}
        for cashflow_record in history:
            key_year = cashflow_record["year_key"][0]
            value = free_cash_flow(cashflow_record["cfo"], cashflow_record["cfi"])
            fcf_by_year[key_year] = value
        latest_fcf_year = latest["year_key"][0] if latest else None
        fcf_cagr, _ = compute_fcf_cagr_5yr(fcf_by_year, latest_fcf_year) if latest_fcf_year else (None, "INSUFFICIENT")

        previous_borrowings = None
        current_borrowings = None
        if latest:
            current_borrowings = borrowings_by_key.get((company_id, latest_year))
            older = [
                (record["year_key"], borrowings_by_key.get((company_id, record["year"])))
                for record in history
                if record["year_key"] < latest["year_key"]
            ]
            older = [(year_key, amount) for year_key, amount in older if amount is not None]
            if older:
                previous_borrowings = max(older, key=lambda item: item[0])[1]

        distress = is_distress(
            latest["cfo"], latest["cff"]
        ) if latest else False
        deleveraging = is_deleveraging(
            latest["cff"], current_borrowings, previous_borrowings
        ) if latest else False
        if latest:
            for record in history:
                record_quality = quality_by_key.get(
                    (company_id, record["year"]), {}
                ).get("quality")
                pattern_history.append({
                    "company_id": company_id,
                    "company_name": company_name,
                    "year": record["year"],
                    "pattern_label": capital_allocation_pattern(
                        record["cfo"], record["cfi"], record["cff"], record_quality
                    )[-1],
                })
        if distress:
            distress_rows.append({
                "company_id": company_id,
                "company_name": company_name,
                "sector": sector,
                "latest_year": latest_year,
                "cfo": latest["cfo"],
                "cff": latest["cff"],
                "net_profit": pnl.get("profit"),
                "reason": "Negative CFO with positive CFF (external financing dependency)",
            })

        records_by_company.append({
            "company_id": company_id,
            "sector": sector,
            "cfo_quality_score": quality,
            "cfo_quality_label": label,
            "capex_intensity_pct": capex_pct,
            "capex_label": capex_label(capex_pct),
            "fcf_cagr_5yr": fcf_cagr,
            "fcf_conversion_pct": quality_data.get("conversion"),
            "distress_flag": distress,
            "deleveraging_flag": deleveraging,
            "capital_allocation_label": pattern,
        })

    workbook = pd.DataFrame(records_by_company, columns=[
        "company_id", "sector", "cfo_quality_score", "cfo_quality_label",
        "capex_intensity_pct", "capex_label", "fcf_cagr_5yr",
        "fcf_conversion_pct", "distress_flag", "deleveraging_flag",
        "capital_allocation_label",
    ])
    workbook.to_excel(
        os.path.join(output_dir, "cashflow_intelligence.xlsx"), index=False
    )

    pd.DataFrame(distress_rows, columns=[
        "company_id", "company_name", "sector", "latest_year", "cfo", "cff",
        "net_profit", "reason",
    ]).to_csv(os.path.join(output_dir, "distress_alerts.csv"), index=False)

    pd.DataFrame(compute_pattern_distribution(distribution_labels)).to_csv(
        os.path.join(output_dir, "capital_allocation_distribution.csv"),
        index=False,
    )

    changes = detect_pattern_changes(pattern_history)
    pd.DataFrame(changes, columns=[
        "company_id", "company_name", "previous_year", "previous_pattern",
        "current_year", "current_pattern",
    ]).to_csv(os.path.join(output_dir, "pattern_changes.csv"), index=False)

    return {
        "companies": len(records_by_company),
        "distress_alerts": len(distress_rows),
        "pattern_changes": len(changes),
        "output_dir": output_dir,
    }