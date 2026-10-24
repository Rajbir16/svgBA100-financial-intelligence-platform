"""Data Quality Validation Module for svgBA100 Financial Intelligence Platform.

Implements all 16 Sprint 1 Data Quality rules:
- DQ-01: Primary-key validity (CRITICAL)
- DQ-02: Primary-key uniqueness (CRITICAL)
- DQ-03: Foreign-key validity (CRITICAL)
- DQ-04: Required company_id (CRITICAL)
- DQ-05: Valid year (WARNING)
- DQ-06: Duplicate company/year records (WARNING)
- DQ-07: Numeric field validity (WARNING)
- DQ-08: Impossible/null critical values (WARNING)
- DQ-09: Stock price validity (WARNING)
- DQ-10: Financial statement cross-consistency (WARNING)
- DQ-11: Sales validity (WARNING)
- DQ-12: Operating profit / OPM consistency (WARNING)
- DQ-13: Balance sheet consistency (WARNING)
- DQ-14: Cash flow consistency (WARNING)
- DQ-15: Company/year coverage (INFO/WARNING)
- DQ-16: Unexpected/malformed source values (INFO)
"""

import csv
import os
import re
import sqlite3
from dataclasses import asdict, dataclass
from typing import Any, Dict, List, Optional, Set, Tuple


@dataclass
class ValidationFailure:
    rule_id: str
    severity: str  # 'CRITICAL', 'WARNING', 'INFO'
    table_name: str
    company_id: Optional[str]
    year: Optional[str]
    column_name: Optional[str]
    value: Optional[str]
    message: str


class DataValidator:
    def __init__(self):
        self.failures: List[ValidationFailure] = []

    def record_failure(
        self,
        rule_id: str,
        severity: str,
        table_name: str,
        company_id: Optional[str],
        year: Optional[str],
        column_name: Optional[str],
        value: Any,
        message: str,
    ):
        """Record a validation failure."""
        val_str = str(value) if value is not None else "NULL"
        if len(val_str) > 120:
            val_str = val_str[:117] + "..."
        self.failures.append(
            ValidationFailure(
                rule_id=rule_id,
                severity=severity.upper(),
                table_name=table_name,
                company_id=str(company_id) if company_id else None,
                year=str(year) if year else None,
                column_name=column_name,
                value=val_str,
                message=message,
            )
        )

    # DQ-01: Primary-key validity
    def check_pk_validity(
        self, table_name: str, pk_val: Any, is_numeric: bool = True
    ) -> bool:
        if pk_val is None or str(pk_val).strip() == "":
            self.record_failure(
                "DQ-01",
                "CRITICAL",
                table_name,
                None,
                None,
                "id",
                pk_val,
                "Primary key 'id' is NULL or empty",
            )
            return False
        if is_numeric:
            try:
                num = int(pk_val)
                if num <= 0:
                    self.record_failure(
                        "DQ-01",
                        "CRITICAL",
                        table_name,
                        None,
                        None,
                        "id",
                        pk_val,
                        f"Primary key 'id' must be > 0, got {num}",
                    )
                    return False
            except (ValueError, TypeError):
                self.record_failure(
                    "DQ-01",
                    "CRITICAL",
                    table_name,
                    None,
                    None,
                    "id",
                    pk_val,
                    f"Primary key 'id' is not a valid integer: {pk_val}",
                )
                return False
        return True

    # DQ-02: Primary-key uniqueness
    def check_pk_uniqueness(
        self, table_name: str, pk_val: Any, seen_pks: Set[Any]
    ) -> bool:
        if pk_val in seen_pks:
            self.record_failure(
                "DQ-02",
                "CRITICAL",
                table_name,
                None,
                None,
                "id",
                pk_val,
                f"Duplicate primary key 'id' detected: {pk_val}",
            )
            return False
        seen_pks.add(pk_val)
        return True

    # DQ-03: Foreign-key validity
    def check_fk_validity(
        self, table_name: str, company_id: Any, valid_company_ids: Set[str]
    ) -> bool:
        if not company_id:
            return False
        cid = str(company_id).strip().upper()
        if cid not in valid_company_ids:
            self.record_failure(
                "DQ-03",
                "CRITICAL",
                table_name,
                cid,
                None,
                "company_id",
                company_id,
                f"Foreign key violation: company_id '{cid}' does not exist in companies table",
            )
            return False
        return True

    # DQ-04: Required company_id
    def check_required_company_id(
        self, table_name: str, company_id: Any
    ) -> bool:
        if (
            company_id is None
            or str(company_id).strip() == ""
            or str(company_id).strip().lower() in {"null", "none", "nan"}
        ):
            self.record_failure(
                "DQ-04",
                "CRITICAL",
                table_name,
                None,
                None,
                "company_id",
                company_id,
                "Required company_id is NULL or empty",
            )
            return False
        return True

    # DQ-05: Valid year / date
    def check_valid_year(
        self, table_name: str, company_id: Any, year_val: Any
    ) -> bool:
        if year_val is None or str(year_val).strip() == "":
            self.record_failure(
                "DQ-05",
                "WARNING",
                table_name,
                company_id,
                year_val,
                "year",
                year_val,
                "Year / reporting period is missing or empty",
            )
            return False
        y_str = str(year_val).strip()
        # Accept 4-digit years (2000-2030), Month Year, TTM, or specific financial periods
        valid_patterns = [
            r"^(19|20)\d{2}$",
            r"^(19|20)\d{2}\.0+$",
            r"^Sep 2024$",
            r"^[A-Za-z]{3}\s+(19|20)\d{2}.*$",
            r"^TTM$",
        ]
        if not any(re.match(p, y_str, re.IGNORECASE) for p in valid_patterns):
            self.record_failure(
                "DQ-05",
                "WARNING",
                table_name,
                company_id,
                y_str,
                "year",
                y_str,
                f"Unrecognized year/period format: '{y_str}'",
            )
            return False
        return True

    # DQ-06: Duplicate company/year records
    def check_duplicate_company_year(
        self,
        table_name: str,
        company_id: Any,
        year_val: Any,
        seen_pairs: Set[Tuple[str, str]],
    ) -> bool:
        if not company_id or not year_val:
            return True
        pair = (str(company_id).strip().upper(), str(year_val).strip())
        if pair in seen_pairs:
            self.record_failure(
                "DQ-06",
                "WARNING",
                table_name,
                pair[0],
                pair[1],
                "year",
                pair[1],
                f"Duplicate record detected for company '{pair[0]}' and year '{pair[1]}'",
            )
            return False
        seen_pairs.add(pair)
        return True

    # DQ-07: Numeric field validity
    def check_numeric_validity(
        self,
        table_name: str,
        company_id: Any,
        year: Any,
        col_name: str,
        raw_val: Any,
        parsed_val: Any,
    ) -> bool:
        if raw_val is not None:
            raw_s = str(raw_val).strip()
            if (
                raw_s != ""
                and raw_s.lower() not in {"na", "n/a", "-", "--", "null", "none"}
                and parsed_val is None
            ):
                self.record_failure(
                    "DQ-07",
                    "WARNING",
                    table_name,
                    company_id,
                    year,
                    col_name,
                    raw_val,
                    f"Non-numeric value in numeric column '{col_name}': '{raw_s}'",
                )
                return False
        return True

    # DQ-08: Impossible / null critical values
    def check_critical_values(
        self, table_name: str, company_id: Any, year: Any, record: Dict[str, Any]
    ) -> bool:
        is_valid = True
        # For balance sheet, total_assets and total_liabilities should not be null
        if table_name == "balancesheet":
            for col in ["total_assets", "total_liabilities"]:
                if record.get(col) is None:
                    self.record_failure(
                        "DQ-08",
                        "WARNING",
                        table_name,
                        company_id,
                        year,
                        col,
                        None,
                        f"Critical balance sheet column '{col}' is NULL",
                    )
                    is_valid = False
        # For stock prices, close_price and volume should not be null or negative
        elif table_name == "stock_prices":
            for col in ["close_price", "open_price", "high_price", "low_price"]:
                v = record.get(col)
                if v is None:
                    self.record_failure(
                        "DQ-08",
                        "WARNING",
                        table_name,
                        company_id,
                        year,
                        col,
                        None,
                        f"Stock price column '{col}' is NULL",
                    )
                    is_valid = False
                elif v <= 0:
                    self.record_failure(
                        "DQ-08",
                        "WARNING",
                        table_name,
                        company_id,
                        year,
                        col,
                        v,
                        f"Stock price column '{col}' is <= 0 ({v})",
                    )
                    is_valid = False
        return is_valid

    # DQ-09: Stock price validity
    def check_stock_price_logic(
        self, company_id: Any, date_val: Any, record: Dict[str, Any]
    ) -> bool:
        high = record.get("high_price")
        low = record.get("low_price")
        open_p = record.get("open_price")
        close = record.get("close_price")
        vol = record.get("volume")
        is_valid = True

        if high is not None and low is not None and high < low:
            self.record_failure(
                "DQ-09",
                "WARNING",
                "stock_prices",
                company_id,
                date_val,
                "high_price",
                f"high={high}, low={low}",
                f"Stock high price ({high}) is lower than low price ({low})",
            )
            is_valid = False

        if high is not None and open_p is not None and high < open_p:
            self.record_failure(
                "DQ-09",
                "WARNING",
                "stock_prices",
                company_id,
                date_val,
                "high_price",
                f"high={high}, open={open_p}",
                f"Stock high price ({high}) is lower than open price ({open_p})",
            )
            is_valid = False

        if high is not None and close is not None and high < close:
            self.record_failure(
                "DQ-09",
                "WARNING",
                "stock_prices",
                company_id,
                date_val,
                "high_price",
                f"high={high}, close={close}",
                f"Stock high price ({high}) is lower than close price ({close})",
            )
            is_valid = False

        if vol is not None and vol < 0:
            self.record_failure(
                "DQ-09",
                "WARNING",
                "stock_prices",
                company_id,
                date_val,
                "volume",
                vol,
                f"Stock trading volume cannot be negative ({vol})",
            )
            is_valid = False

        return is_valid

    # DQ-10: Financial statement cross-consistency
    def check_financial_cross_consistency(
        self,
        company_id: Any,
        year: Any,
        pnl_net_profit: Optional[float],
        ratio_npm: Optional[float],
        sales: Optional[float],
    ) -> bool:
        if (
            pnl_net_profit is not None
            and ratio_npm is not None
            and sales is not None
            and sales > 0
        ):
            calc_npm = (pnl_net_profit / sales) * 100
            diff = abs(calc_npm - ratio_npm)
            if diff > 5.0:  # Tolerance for rounding / accounting adjustments
                self.record_failure(
                    "DQ-10",
                    "WARNING",
                    "financial_ratios",
                    company_id,
                    year,
                    "net_profit_margin_pct",
                    f"ratio={ratio_npm}, calc={calc_npm:.2f}",
                    f"Net profit margin mismatch: reported {ratio_npm}%, computed {calc_npm:.2f}%",
                )
                return False
        return True

    # DQ-11: Sales validity
    def check_sales_validity(
        self, company_id: Any, year: Any, sales: Optional[float]
    ) -> bool:
        if sales is not None and sales < 0:
            self.record_failure(
                "DQ-11",
                "WARNING",
                "profitandloss",
                company_id,
                year,
                "sales",
                sales,
                f"Negative sales reported: {sales}",
            )
            return False
        return True

    # DQ-12: Operating-profit / OPM consistency
    def check_operating_profit_consistency(
        self,
        company_id: Any,
        year: Any,
        sales: Optional[float],
        expenses: Optional[float],
        op: Optional[float],
        opm: Optional[float],
    ) -> bool:
        is_valid = True
        if sales is not None and expenses is not None and op is not None:
            expected_op = sales - expenses
            if abs(expected_op - op) > 2.0:  # Allow 2 unit rounding tolerance
                self.record_failure(
                    "DQ-12",
                    "WARNING",
                    "profitandloss",
                    company_id,
                    year,
                    "operating_profit",
                    f"sales={sales}, exp={expenses}, op={op}",
                    f"Operating profit mismatch: sales - expenses = {expected_op:.2f}, reported {op:.2f}",
                )
                is_valid = False

        if sales is not None and op is not None and opm is not None and sales > 0:
            calc_opm = (op / sales) * 100
            if abs(calc_opm - opm) > 2.0:  # Allow 2% rounding tolerance
                self.record_failure(
                    "DQ-12",
                    "WARNING",
                    "profitandloss",
                    company_id,
                    year,
                    "opm_percentage",
                    f"reported={opm}, calc={calc_opm:.2f}",
                    f"OPM mismatch: reported {opm}%, calculated {calc_opm:.2f}%",
                )
                is_valid = False
        return is_valid

    # DQ-13: Balance sheet consistency
    def check_balance_sheet_consistency(
        self, company_id: Any, year: Any, record: Dict[str, Any]
    ) -> bool:
        tot_liab = record.get("total_liabilities")
        tot_assets = record.get("total_assets")
        eq = record.get("equity_capital") or 0.0
        res = record.get("reserves") or 0.0
        bor = record.get("borrowings") or 0.0
        oth_liab = record.get("other_liabilities") or 0.0
        is_valid = True

        if tot_assets is not None and tot_liab is not None:
            if abs(tot_assets - tot_liab) > 2.0:
                self.record_failure(
                    "DQ-13",
                    "WARNING",
                    "balancesheet",
                    company_id,
                    year,
                    "total_assets",
                    f"assets={tot_assets}, liab={tot_liab}",
                    f"Balance sheet equation mismatch: total_assets ({tot_assets}) != total_liabilities ({tot_liab})",
                )
                is_valid = False

        if tot_liab is not None:
            sum_liab = eq + res + bor + oth_liab
            if abs(sum_liab - tot_liab) > 2.0:
                self.record_failure(
                    "DQ-13",
                    "WARNING",
                    "balancesheet",
                    company_id,
                    year,
                    "total_liabilities",
                    f"sum={sum_liab:.2f}, reported={tot_liab}",
                    f"Liabilities breakdown mismatch: sum of components ({sum_liab:.2f}) != total_liabilities ({tot_liab})",
                )
                is_valid = False
        return is_valid

    # DQ-14: Cash flow consistency
    def check_cash_flow_consistency(
        self,
        company_id: Any,
        year: Any,
        op_cf: Optional[float],
        inv_cf: Optional[float],
        fin_cf: Optional[float],
        net_cf: Optional[float],
    ) -> bool:
        if (
            op_cf is not None
            and inv_cf is not None
            and fin_cf is not None
            and net_cf is not None
        ):
            calc_net = op_cf + inv_cf + fin_cf
            if abs(calc_net - net_cf) > 2.0:  # Allow 2 unit rounding tolerance
                self.record_failure(
                    "DQ-14",
                    "WARNING",
                    "cashflow",
                    company_id,
                    year,
                    "net_cash_flow",
                    f"reported={net_cf}, calc={calc_net:.2f}",
                    f"Net cash flow mismatch: operating + investing + financing = {calc_net:.2f}, reported {net_cf}",
                )
                return False
        return True

    # DQ-15: Company/year coverage
    def check_year_coverage(
        self,
        table_name: str,
        company_id: str,
        years: List[str],
        min_years: int = 5,
    ):
        clean_years = [y for y in years if y and y.upper() != "TTM"]
        if len(set(clean_years)) < min_years:
            self.record_failure(
                "DQ-15",
                "INFO",
                table_name,
                company_id,
                None,
                "year",
                f"{len(set(clean_years))} years",
                f"Company '{company_id}' has fewer than {min_years} financial years of data ({len(set(clean_years))} years)",
            )

    # DQ-16: Unexpected / malformed source values
    def check_malformed_values(
        self,
        table_name: str,
        company_id: Any,
        year: Any,
        col_name: str,
        raw_val: Any,
    ):
        if raw_val is not None:
            s = str(raw_val)
            if s.startswith(" ") or s.endswith(" ") or "  " in s:
                self.record_failure(
                    "DQ-16",
                    "INFO",
                    table_name,
                    company_id,
                    year,
                    col_name,
                    s,
                    f"Untrimmed or irregular whitespace detected in '{col_name}'",
                )
            if s.strip().lower() in {"na", "n/a", "-", "--", "#n/a"}:
                self.record_failure(
                    "DQ-16",
                    "INFO",
                    table_name,
                    company_id,
                    year,
                    col_name,
                    s,
                    f"Raw placeholder '{s}' detected in source column '{col_name}'",
                )

    def export_failures_csv(self, output_file_path: str):
        """Write all validation failures to a CSV file."""
        os.makedirs(os.path.dirname(os.path.abspath(output_file_path)), exist_ok=True)
        with open(output_file_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(
                f,
                fieldnames=[
                    "rule_id",
                    "severity",
                    "table_name",
                    "company_id",
                    "year",
                    "column_name",
                    "value",
                    "message",
                ],
            )
            writer.writeheader()
            for item in self.failures:
                writer.writerow(asdict(item))

    def get_summary(self) -> Dict[str, int]:
        """Return counts of failures by severity."""
        counts = {"CRITICAL": 0, "WARNING": 0, "INFO": 0, "TOTAL": len(self.failures)}
        for item in self.failures:
            counts[item.severity] = counts.get(item.severity, 0) + 1
        return counts

    def validate_database(self, conn: sqlite3.Connection) -> Dict[str, int]:
        """Validate all tables and integrity rules directly against a loaded SQLite database."""
        c = conn.cursor()

        # 1. Foreign key check
        c.execute("PRAGMA foreign_key_check;")
        fk_violations = c.fetchall()
        for v in fk_violations:
            self.record_failure(
                "DQ-03",
                "CRITICAL",
                v[0],
                str(v[1]),
                None,
                "company_id",
                v[1],
                f"Foreign key violation on table {v[0]}, rowid {v[1]}",
            )

        # 2. Check companies table
        c.execute("SELECT id, company_name FROM companies")
        company_rows = c.fetchall()
        valid_cids = set()
        seen_cids = set()
        for cid, cname in company_rows:
            self.check_pk_validity("companies", cid, is_numeric=False)
            self.check_pk_uniqueness("companies", cid, seen_cids)
            if cid:
                valid_cids.add(cid)
            if not cname:
                self.record_failure(
                    "DQ-08",
                    "WARNING",
                    "companies",
                    cid,
                    None,
                    "company_name",
                    cname,
                    "Company name is missing or empty",
                )

        # 3. Check statement tables for DQ rules
        # Stock prices
        c.execute(
            "SELECT id, company_id, date, open_price, high_price, low_price, close_price, volume FROM stock_prices"
        )
        for r in c.fetchall():
            rec = {
                "open_price": r[3],
                "high_price": r[4],
                "low_price": r[5],
                "close_price": r[6],
                "volume": r[7],
            }
            self.check_critical_values("stock_prices", r[1], r[2], rec)
            self.check_stock_price_logic(r[1], r[2], rec)

        # Profit & loss
        c.execute(
            "SELECT id, company_id, year, sales, expenses, operating_profit, opm_percentage FROM profitandloss"
        )
        for r in c.fetchall():
            self.check_sales_validity(r[1], r[2], r[3])
            self.check_operating_profit_consistency(
                r[1], r[2], r[3], r[4], r[5], r[6]
            )

        # Balance sheet
        c.execute(
            "SELECT id, company_id, year, equity_capital, reserves, borrowings, other_liabilities, total_liabilities, total_assets FROM balancesheet"
        )
        for r in c.fetchall():
            rec = {
                "equity_capital": r[3],
                "reserves": r[4],
                "borrowings": r[5],
                "other_liabilities": r[6],
                "total_liabilities": r[7],
                "total_assets": r[8],
            }
            self.check_critical_values("balancesheet", r[1], r[2], rec)
            self.check_balance_sheet_consistency(r[1], r[2], rec)

        # Cash flow
        c.execute(
            "SELECT id, company_id, year, operating_activity, investing_activity, financing_activity, net_cash_flow FROM cashflow"
        )
        for r in c.fetchall():
            self.check_cash_flow_consistency(
                r[1], r[2], r[3], r[4], r[5], r[6]
            )

        # Coverage checks
        for tbl in ["profitandloss", "balancesheet", "cashflow"]:
            c.execute(
                f"SELECT company_id, GROUP_CONCAT(year) FROM {tbl} GROUP BY company_id"
            )
            for cid, yrs_str in c.fetchall():
                yrs = yrs_str.split(",") if yrs_str else []
                self.check_year_coverage(tbl, cid, yrs, min_years=5)

        return self.get_summary()


def main():
    import argparse
    import sqlite3

    parser = argparse.ArgumentParser(description="Validate SQLite database for svgBA100")
    parser.add_argument("--db", default="nifty100.db", help="Path to SQLite database")
    parser.add_argument(
        "--output",
        default="output/validation_failures.csv",
        help="Path to output validation CSV",
    )
    args = parser.parse_args()

    if not os.path.exists(args.db):
        print(f"Error: Database {args.db} does not exist.")
        return

    conn = sqlite3.connect(args.db)
    validator = DataValidator()
    summary = validator.validate_database(conn)
    validator.export_failures_csv(args.output)
    conn.close()

    print("=" * 40)
    print("DATABASE VALIDATION REPORT")
    print("=" * 40)
    print(f"Database: {args.db}")
    print(f"CRITICAL Failures: {summary['CRITICAL']}")
    print(f"WARNINGs:          {summary['WARNING']}")
    print(f"INFO Findings:     {summary['INFO']}")
    print(f"TOTAL:             {summary['TOTAL']}")
    print("=" * 40)
    print(f"Report exported to: {args.output}")


if __name__ == "__main__":
    main()

