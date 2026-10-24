"""Comprehensive API integration tests for svgBA100 RESTful endpoints (Sprint 6 Days 38–42)."""

import pytest
from starlette.testclient import TestClient

from src.api.main import app
from src.screener.engine import apply_screener_filters, get_screener_universe, load_config


@pytest.fixture(scope="module")
def client():
    return TestClient(app)


# 1. Health Endpoints
def test_health_check(client):
    r = client.get("/api/v1/health")
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "healthy"
    assert data["database"] == "connected"


def test_health_table_counts(client):
    r = client.get("/api/v1/health/counts")
    assert r.status_code == 200
    tables = r.json()["tables"]
    assert tables["companies"] == 92
    assert tables["sectors"] == 92
    assert tables["financial_ratios"] > 1000
    assert tables["peer_groups"] > 50


# 2. Company Endpoints
def test_list_companies_total_and_pagination(client):
    r = client.get("/api/v1/companies?limit=10&offset=0")
    assert r.status_code == 200
    data = r.json()
    assert data["total"] == 92
    assert data["count"] == 10
    assert len(data["companies"]) == 10


def test_list_companies_sector_filter(client):
    r = client.get("/api/v1/companies?sector=Information%20Technology")
    assert r.status_code == 200
    data = r.json()
    assert data["count"] == 5
    for co in data["companies"]:
        assert co["broad_sector"] == "Information Technology"


def test_get_company_profile_valid(client):
    r = client.get("/api/v1/companies/TCS")
    assert r.status_code == 200
    data = r.json()
    assert data["ticker"] == "TCS"
    assert "master" in data
    assert "latest_ratios" in data
    assert data["master"]["company_name"] == "Tata Consultancy Services Ltd"


def test_get_company_profile_not_found(client):
    r = client.get("/api/v1/companies/NONEXISTENT_TICKER")
    assert r.status_code == 404
    assert "not found" in r.json()["detail"].lower()


def test_get_company_financial_statements(client):
    for stmt in ["pnl", "balancesheet", "cashflow", "ratios"]:
        r = client.get(f"/api/v1/companies/TCS/{stmt}")
        assert r.status_code == 200
        data = r.json()
        assert data["ticker"] == "TCS"
        assert data["count"] > 0
        assert len(data["records"]) == data["count"]


def test_get_company_tearsheet_pdf(client):
    r = client.get("/api/v1/companies/TCS/tearsheet")
    assert r.status_code == 200
    assert r.headers["content-type"] == "application/pdf"
    assert len(r.content) >= 30000


def test_get_company_tearsheet_skipped_404(client):
    r = client.get("/api/v1/companies/JIOFIN/tearsheet")
    assert r.status_code == 404
    assert "insufficient" in r.json()["detail"].lower() or "skipped" in r.json()["detail"].lower()


# 3. Screener Endpoints
def test_screener_presets_list(client):
    r = client.get("/api/v1/screener/presets")
    assert r.status_code == 200
    data = r.json()
    assert data["count"] >= 6
    preset_names = [p["name"] for p in data["presets"]]
    assert "Quality Compounder" in preset_names


def test_screener_run_preset_quality_compounders(client):
    r1 = client.get("/api/v1/screener?preset=Quality%20Compounder")
    r2 = client.get("/api/v1/screener?preset=quality_compounders")
    assert r1.status_code == 200
    assert r2.status_code == 200
    assert r1.json()["total_matched"] == r2.json()["total_matched"]
    assert r1.json()["total_matched"] > 0


def test_screener_custom_filters_and_sorting(client):
    r = client.get("/api/v1/screener?roe_min=15&max_de=1.0&sort_by=return_on_equity_pct&sort_order=desc")
    assert r.status_code == 200
    results = r.json()["results"]
    for row in results:
        if row["broad_sector"].lower() != "financials":
            assert row["debt_to_equity"] <= 1.0


def test_screener_invalid_sort_parameter(client):
    r1 = client.get("/api/v1/screener?sort_order=sideways")
    assert r1.status_code == 400
    r2 = client.get("/api/v1/screener?sort_by=non_existent_column")
    assert r2.status_code == 400


# 4. Sector Endpoints
def test_list_sectors_authoritative_ten(client):
    r = client.get("/api/v1/sectors")
    assert r.status_code == 200
    data = r.json()
    assert data["authoritative_broad_sectors_count"] == 10
    assert len(data["sectors"]) == 10
    total_companies = sum(s["company_count"] for s in data["sectors"])
    assert total_companies == 92


def test_get_sector_detail_valid_and_invalid(client):
    r_it = client.get("/api/v1/sectors/Information%20Technology")
    assert r_it.status_code == 200
    assert r_it.json()["company_count"] == 5

    r_bad = client.get("/api/v1/sectors/SpaceExploration")
    assert r_bad.status_code == 404


# 5. Peer Group Endpoints
def test_list_peer_groups_eleven(client):
    r = client.get("/api/v1/peers")
    assert r.status_code == 200
    data = r.json()
    assert data["count"] == 11
    assert len(data["peer_groups"]) == 11


def test_get_peer_group_detail(client):
    r = client.get("/api/v1/peers/IT%20Services")
    assert r.status_code == 200
    data = r.json()
    assert data["member_count"] == 5
    assert data["benchmark_ticker"] == "TCS"
    assert data["percentile_records_count"] > 0


def test_get_company_peer_comparison(client):
    r = client.get("/api/v1/companies/TCS/peers")
    assert r.status_code == 200
    data = r.json()
    assert data["peer_group_name"] == "IT Services"
    assert data["is_benchmark"] is True
    assert len(data["percentiles"]) > 0


# 6. Valuation Endpoints
def test_valuation_summary_and_filters(client):
    r = client.get("/api/v1/valuation/summary")
    assert r.status_code == 200
    assert r.json()["count"] == 92

    r_sec = client.get("/api/v1/valuation/summary?sector=Information%20Technology")
    assert r_sec.status_code == 200
    assert r_sec.json()["count"] == 5


def test_company_valuation_history(client):
    r = client.get("/api/v1/companies/TCS/valuation")
    assert r.status_code == 200
    data = r.json()
    assert data["history_count"] >= 5
    assert data["summary"]["company_id"] == "TCS"


# 7. Portfolio Endpoints
def test_portfolio_stats_endpoint(client):
    r = client.get("/api/v1/portfolio/stats")
    assert r.status_code == 200
    assert r.json()["count"] == 10

    r_kpi = client.get("/api/v1/portfolio/stats?metric=return_on_equity_pct")
    assert r_kpi.status_code == 200
    assert r_kpi.json()["count"] == 1


def test_portfolio_clusters_endpoint(client):
    r = client.get("/api/v1/portfolio/clusters")
    assert r.status_code == 200
    data = r.json()
    assert data["total_records"] == 92
    assert len(data["cluster_distribution"]) == 5

    r_co = client.get("/api/v1/portfolio/clusters?company_id=TCS")
    assert r_co.status_code == 200
    assert r_co.json()["total_records"] == 1


# 8. Documents Endpoints
def test_company_documents_endpoint(client):
    r = client.get("/api/v1/companies/TCS/documents")
    assert r.status_code == 200
    data = r.json()
    assert data["ticker"] == "TCS"
    assert data["count"] > 0
    assert "annual_report" in data["annual_reports"][0]


# 9. Dashboard / API Screener Consistency Test
def test_dashboard_and_api_screener_consistency(client):
    """Verify API screener results strictly match underlying screener engine logic."""
    r = client.get("/api/v1/screener?preset=Quality%20Compounder")
    assert r.status_code == 200
    api_tickers = [row["company_id"] for row in r.json()["results"]]

    df = get_screener_universe("nifty100.db")
    cfg = load_config("config/screener_config.yaml")
    direct_filtered = apply_screener_filters(df, cfg["presets"]["Quality Compounder"])
    direct_tickers = direct_filtered["company_id"].tolist()

    assert api_tickers == direct_tickers

