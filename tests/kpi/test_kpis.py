"""Twenty focused Sprint 2 KPI formula tests."""

from src.analytics.cagr import calculate_cagr, cagr_for_series
from src.analytics.cashflow_kpis import capital_allocation_pattern, capex_intensity, cfo_quality, fcf_conversion, free_cash_flow
from src.analytics.ratios import leverage_efficiency_kpis, profitability_kpis


def test_01_npm():
    assert profitability_kpis({"net_profit": 10, "sales": 100}, {})["net_profit_margin_pct"] == 10


def test_02_opm():
    assert profitability_kpis({"operating_profit": 25, "sales": 100}, {})["operating_profit_margin_pct"] == 25


def test_03_roe():
    assert profitability_kpis({"net_profit": 20}, {"equity_capital": 50, "reserves": 50})["return_on_equity_pct"] == 20


def test_04_zero_denominators():
    result = profitability_kpis({"net_profit": 20, "operating_profit": 10, "sales": 0}, {"total_assets": 0})
    assert result["net_profit_margin_pct"] is None and result["return_on_assets_pct"] is None


def test_05_negative_equity():
    assert profitability_kpis({"net_profit": 20}, {"equity_capital": 10, "reserves": -20})["return_on_equity_pct"] is None


def test_06_opm_source_mismatch_is_computable():
    assert profitability_kpis({"operating_profit": 20, "sales": 100, "opm_percentage": 10}, {})["operating_profit_margin_pct"] == 20


def test_07_debt_free_de():
    assert leverage_efficiency_kpis({}, {"borrowings": 0})["debt_to_equity"] == 0


def test_08_icr_debt_free_label():
    result = leverage_efficiency_kpis({"interest": 0}, {})
    assert result["interest_coverage"] is None and result["icr_label"] == "Debt Free"


def test_09_high_de():
    assert leverage_efficiency_kpis({}, {"borrowings": 600, "equity_capital": 100})["high_leverage_flag"] == 1


def test_10_financials_suppress_high_de():
    assert leverage_efficiency_kpis({}, {"borrowings": 600, "equity_capital": 100}, True)["high_leverage_flag"] == 0


def test_11_cagr_normal():
    value, flag = calculate_cagr(100, 121, 2)
    assert round(value, 6) == 10 and flag == "NORMAL"


def test_12_cagr_turnaround():
    assert calculate_cagr(-10, 20, 3)[1] == "TURNAROUND"


def test_13_cagr_decline_to_loss():
    assert calculate_cagr(10, -20, 3)[1] == "DECLINE_TO_LOSS"


def test_14_cagr_both_negative():
    assert calculate_cagr(-10, -20, 3)[1] == "BOTH_NEGATIVE"


def test_15_cagr_zero_base():
    assert calculate_cagr(0, 20, 3)[1] == "ZERO_BASE"


def test_16_cagr_insufficient():
    assert cagr_for_series({2022: 10, 2024: 20}, 2024, 5)[1] == "INSUFFICIENT"


def test_17_cash_flow():
    assert free_cash_flow(100, -40) == 60


def test_18_cfo_quality_average():
    assert cfo_quality([100, 50], [100, 100]) == 0.75


def test_19_capex_and_conversion():
    assert capex_intensity(-5, 100) == 5 and fcf_conversion(20, 40) == 50


def test_20_capital_allocation():
    assert capital_allocation_pattern(100, -50, -20, 1.2)[-1] == "Shareholder Returns"