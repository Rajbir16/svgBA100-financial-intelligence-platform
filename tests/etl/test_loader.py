"""Integration and unit tests for src/etl/loader.py.

Tests schema creation, header detection, transactional loading,
foreign key rejection, audit logs, and database integrity.
"""

import os
import sqlite3
import tempfile

import pytest

from src.etl.loader import ETLLoader, TABLE_CONFIGS


class TestLoader:
    @pytest.fixture
    def test_env(self):
        """Fixture providing temp database, temp output dir, and real datasets."""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_db = os.path.join(tmpdir, "test_nifty100.db")
            output_dir = os.path.join(tmpdir, "output")
            schema_path = "db/schema.sql"
            data_dir = "./data"
            loader = ETLLoader(
                db_path=test_db,
                data_dir=data_dir,
                output_dir=output_dir,
                schema_path=schema_path,
            )
            yield loader, test_db, output_dir

    def test_schema_initialization(self, test_env):
        loader, test_db, _ = test_env
        conn = sqlite3.connect(test_db)
        loader.initialize_database(conn)

        c = conn.cursor()
        c.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = {row[0] for row in c.fetchall()}

        expected_tables = {
            "companies",
            "sectors",
            "market_cap",
            "stock_prices",
            "financial_ratios",
            "balancesheet",
            "profitandloss",
            "cashflow",
            "peer_groups",
            "analysis",
            "prosandcons",
            "documents",
        }
        assert expected_tables.issubset(tables)
        conn.close()

    def test_foreign_key_enforcement_in_sqlite(self, test_env):
        loader, test_db, _ = test_env
        conn = sqlite3.connect(test_db)
        loader.initialize_database(conn)

        # Insert a valid company
        conn.execute("INSERT INTO companies (id, company_name) VALUES ('TCS', 'Tata Consultancy Services');")
        conn.commit()

        # Insert child referencing valid company -> should succeed
        conn.execute("INSERT INTO sectors (id, company_id, broad_sector) VALUES (1, 'TCS', 'Technology');")
        conn.commit()

        # Insert child referencing invalid company -> must fail with IntegrityError
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute("INSERT INTO sectors (id, company_id, broad_sector) VALUES (2, 'NONEXISTENT', 'Finance');")
            conn.commit()

        conn.close()

    def test_companies_loaded_count(self, test_env):
        loader, test_db, _ = test_env
        conn = sqlite3.connect(test_db)
        loader.initialize_database(conn)

        companies_cfg = next(c for c in TABLE_CONFIGS if c["table_name"] == "companies")
        audit = loader.load_table(conn, companies_cfg)

        assert audit["rows_read"] == 92
        assert audit["rows_inserted"] == 92
        assert audit["rows_rejected"] == 0
        assert audit["status"] == "SUCCESS"
        assert len(loader.valid_company_ids) == 92
        conn.close()

    def test_foreign_key_rejection_for_orphan_tickers(self, test_env):
        loader, test_db, _ = test_env
        conn = sqlite3.connect(test_db)
        loader.initialize_database(conn)

        # Load companies first
        companies_cfg = next(c for c in TABLE_CONFIGS if c["table_name"] == "companies")
        loader.load_table(conn, companies_cfg)

        # Load balancesheet which contains orphan tickers (e.g. WIPRO, VEDL)
        bs_cfg = next(c for c in TABLE_CONFIGS if c["table_name"] == "balancesheet")
        audit = loader.load_table(conn, bs_cfg)

        assert audit["rows_read"] == 1312
        assert audit["rows_rejected"] == 85
        assert audit["rows_inserted"] == 1227
        assert audit["status"] == "COMPLETED_WITH_REJECTIONS"

        # Verify PRAGMA foreign_key_check passes with 0 violations
        c = conn.cursor()
        c.execute("PRAGMA foreign_key_check;")
        assert len(c.fetchall()) == 0
        conn.close()

    def test_transaction_rollback_on_error(self, test_env):
        loader, test_db, _ = test_env
        conn = sqlite3.connect(test_db)
        loader.initialize_database(conn)

        # Test broken insert tuple
        broken_cfg = {
            "table_name": "companies",
            "file_pattern": "*companies.xlsx",
            "sheet_name": "Companies",
            "is_parent": True,
            "columns": [("id", "id", "ticker")],  # incomplete columns for table
        }
        # Attempting invalid columns must fail and update audit log
        audit = loader.load_table(conn, broken_cfg)
        assert audit["status"].startswith("FAILED") or audit["rows_inserted"] == 0
        conn.close()

    def test_header_detection_banner_and_direct(self, test_env):
        loader, _, _ = test_env
        # balancesheet has banner in row 1, headers in row 2
        bs_file = loader.find_file("*balancesheet.xlsx")
        headers, data = loader.read_sheet_data(bs_file, "Balance Sheet")
        assert headers[0].lower() == "id"
        assert headers[1].lower() == "company_id"
        assert len(data) == 1312

        # sectors has direct headers in row 1
        sec_file = loader.find_file("*sectors.xlsx")
        headers_sec, data_sec = loader.read_sheet_data(sec_file, "Sheet1")
        assert headers_sec[0].lower() == "id"
        assert headers_sec[1].lower() == "company_id"
        assert len(data_sec) == 92

    def test_audit_and_validation_csv_exports(self, test_env):
        loader, _, output_dir = test_env
        audit_file = os.path.join(output_dir, "test_audit.csv")
        failures_file = os.path.join(output_dir, "test_failures.csv")

        loader.audit_log.append(
            {
                "source_file": "test.xlsx",
                "source_sheet": "Sheet1",
                "target_table": "test_table",
                "rows_read": 10,
                "rows_inserted": 8,
                "rows_rejected": 2,
                "status": "COMPLETED_WITH_REJECTIONS",
                "timestamp": "2026-09-13T12:00:00",
            }
        )
        loader.validator.record_failure("DQ-03", "CRITICAL", "test_table", "TEST", "2024", "id", 1, "FK missing")

        loader.write_audit_csv(audit_file)
        loader.validator.export_failures_csv(failures_file)

        assert os.path.exists(audit_file)
        assert os.path.exists(failures_file)
        assert os.path.getsize(audit_file) > 0
        assert os.path.getsize(failures_file) > 0

    def test_manual_review_report_structure(self, test_env):
        loader, test_db, _ = test_env
        conn = sqlite3.connect(test_db)
        loader.initialize_database(conn)

        # Seed minimal data
        conn.execute("INSERT INTO companies (id, company_name) VALUES ('TCS', 'Tata Consultancy Services');")
        conn.execute("INSERT INTO profitandloss (id, company_id, year, sales) VALUES (1, 'TCS', '2023', 1000);")
        conn.commit()

        report = loader.generate_manual_review_report(conn, sample_companies=["TCS"])
        assert "MANUAL REVIEW REPORT" in report
        assert "TCS" in report
        conn.close()

    def test_full_pipeline_execution(self, test_env):
        loader, test_db, output_dir = test_env
        result = loader.run_pipeline()

        assert result["companies_count"] == 92
        assert len(result["fk_violations"]) == 0
        assert os.path.exists(os.path.join(output_dir, "load_audit.csv"))
        assert os.path.exists(os.path.join(output_dir, "validation_failures.csv"))


