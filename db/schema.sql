-- svgBA100 FINANCIAL INTELLIGENCE PLATFORM
-- SPRINT 1: Database Schema (SQLite)
-- Database Name: nifty100.db

PRAGMA foreign_keys = ON;

-- 1. Companies Table (Master Table)
DROP TABLE IF EXISTS companies;
CREATE TABLE companies (
    id TEXT PRIMARY KEY,
    company_logo TEXT,
    company_name TEXT NOT NULL,
    chart_link TEXT,
    about_company TEXT,
    website TEXT,
    nse_profile TEXT,
    bse_profile TEXT,
    face_value REAL,
    book_value REAL,
    roce_percentage REAL,
    roe_percentage REAL
);

-- 2. Sectors Table
DROP TABLE IF EXISTS sectors;
CREATE TABLE sectors (
    id INTEGER PRIMARY KEY,
    company_id TEXT NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    broad_sector TEXT,
    sub_sector TEXT,
    index_weight_pct REAL,
    market_cap_category TEXT
);

-- 3. Market Capitalisation Table
DROP TABLE IF EXISTS market_cap;
CREATE TABLE market_cap (
    id INTEGER PRIMARY KEY,
    company_id TEXT NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    year INTEGER NOT NULL,
    market_cap_crore REAL,
    enterprise_value_crore REAL,
    pe_ratio REAL,
    pb_ratio REAL,
    ev_ebitda REAL,
    dividend_yield_pct REAL
);

-- 4. Stock Prices Table (Monthly historical prices)
DROP TABLE IF EXISTS stock_prices;
CREATE TABLE stock_prices (
    id INTEGER PRIMARY KEY,
    company_id TEXT NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    date TEXT NOT NULL,
    open_price REAL,
    high_price REAL,
    low_price REAL,
    close_price REAL,
    volume INTEGER,
    adjusted_close REAL
);

-- 5. Financial Ratios Table
DROP TABLE IF EXISTS financial_ratios;
CREATE TABLE financial_ratios (
    id INTEGER PRIMARY KEY,
    company_id TEXT NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    year TEXT NOT NULL,
    net_profit_margin_pct REAL,
    operating_profit_margin_pct REAL,
    return_on_equity_pct REAL,
    debt_to_equity REAL,
    interest_coverage REAL,
    asset_turnover REAL,
    free_cash_flow_cr REAL,
    capex_cr REAL,
    earnings_per_share REAL,
    book_value_per_share REAL,
    dividend_payout_ratio_pct REAL,
    total_debt_cr REAL,
    cash_from_operations_cr REAL,
    revenue_cagr_3yr REAL,
    revenue_cagr_3yr_flag TEXT,
    revenue_cagr_5yr REAL,
    revenue_cagr_5yr_flag TEXT,
    revenue_cagr_10yr REAL,
    revenue_cagr_10yr_flag TEXT,
    pat_cagr_3yr REAL,
    pat_cagr_3yr_flag TEXT,
    pat_cagr_5yr REAL,
    pat_cagr_5yr_flag TEXT,
    pat_cagr_10yr REAL,
    pat_cagr_10yr_flag TEXT,
    eps_cagr_3yr REAL,
    eps_cagr_3yr_flag TEXT,
    eps_cagr_5yr REAL,
    eps_cagr_5yr_flag TEXT,
    eps_cagr_10yr REAL,
    eps_cagr_10yr_flag TEXT,
    composite_quality_score REAL,
    high_leverage_flag INTEGER,
    icr_warning INTEGER,
    return_on_capital_employed_pct REAL,
    return_on_assets_pct REAL,
    net_debt_cr REAL,
    cfo_quality_5yr REAL,
    cfo_quality_label TEXT,
    capex_intensity_pct REAL,
    capex_intensity_label TEXT,
    fcf_conversion_pct REAL,
    icr_label TEXT,
    sales_cr REAL,
    net_profit_cr REAL,
    operating_profit_cr REAL,
    other_income_cr REAL,
    interest_expense_cr REAL,
    equity_cr REAL,
    reserves_cr REAL,
    investments_cr REAL,
    total_assets_cr REAL
);

-- 6. Balance Sheet Table
DROP TABLE IF EXISTS balancesheet;
CREATE TABLE balancesheet (
    id INTEGER PRIMARY KEY,
    company_id TEXT NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    year TEXT NOT NULL,
    equity_capital REAL,
    reserves REAL,
    borrowings REAL,
    other_liabilities REAL,
    total_liabilities REAL,
    fixed_assets REAL,
    cwip REAL,
    investments REAL,
    other_asset REAL,
    total_assets REAL
);

-- 7. Profit and Loss Table
DROP TABLE IF EXISTS profitandloss;
CREATE TABLE profitandloss (
    id INTEGER PRIMARY KEY,
    company_id TEXT NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    year TEXT NOT NULL,
    sales REAL,
    expenses REAL,
    operating_profit REAL,
    opm_percentage REAL,
    other_income REAL,
    interest REAL,
    depreciation REAL,
    profit_before_tax REAL,
    tax_percentage REAL,
    net_profit REAL,
    eps REAL,
    dividend_payout REAL
);

-- 8. Cash Flow Table
DROP TABLE IF EXISTS cashflow;
CREATE TABLE cashflow (
    id INTEGER PRIMARY KEY,
    company_id TEXT NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    year TEXT NOT NULL,
    operating_activity REAL,
    investing_activity REAL,
    financing_activity REAL,
    net_cash_flow REAL
);

-- 9. Peer Groups Table
DROP TABLE IF EXISTS peer_groups;
CREATE TABLE peer_groups (
    id INTEGER PRIMARY KEY,
    peer_group_name TEXT NOT NULL,
    company_id TEXT NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    is_benchmark INTEGER NOT NULL DEFAULT 0
);

-- 10. Analysis Table (CAGR and growth indicators)
DROP TABLE IF EXISTS analysis;
CREATE TABLE analysis (
    id INTEGER PRIMARY KEY,
    company_id TEXT NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    compounded_sales_growth TEXT,
    compounded_profit_growth TEXT,
    stock_price_cagr TEXT,
    roe TEXT
);

-- 11. Pros and Cons Table
DROP TABLE IF EXISTS prosandcons;
CREATE TABLE prosandcons (
    id INTEGER PRIMARY KEY,
    company_id TEXT NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    pros TEXT,
    cons TEXT
);

-- 12. Documents Table (Annual reports)
DROP TABLE IF EXISTS documents;
CREATE TABLE documents (
    id INTEGER PRIMARY KEY,
    company_id TEXT NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    year TEXT NOT NULL,
    annual_report TEXT
);

-- 13. Peer Percentiles Table (Sprint 3)
DROP TABLE IF EXISTS peer_percentiles;
CREATE TABLE peer_percentiles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id TEXT NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    peer_group_name TEXT NOT NULL,
    metric TEXT NOT NULL,
    value REAL,
    percentile_rank REAL,
    year TEXT NOT NULL
);

-- Indexes for efficient queries and joins
CREATE INDEX IF NOT EXISTS idx_sectors_company ON sectors(company_id);
CREATE INDEX IF NOT EXISTS idx_market_cap_co_yr ON market_cap(company_id, year);
CREATE INDEX IF NOT EXISTS idx_stock_prices_co_dt ON stock_prices(company_id, date);
CREATE INDEX IF NOT EXISTS idx_financial_ratios_co_yr ON financial_ratios(company_id, year);
CREATE INDEX IF NOT EXISTS idx_balancesheet_co_yr ON balancesheet(company_id, year);
CREATE INDEX IF NOT EXISTS idx_profitandloss_co_yr ON profitandloss(company_id, year);
CREATE INDEX IF NOT EXISTS idx_cashflow_co_yr ON cashflow(company_id, year);
CREATE INDEX IF NOT EXISTS idx_peer_groups_name ON peer_groups(peer_group_name);
CREATE INDEX IF NOT EXISTS idx_peer_groups_co ON peer_groups(company_id);
CREATE INDEX IF NOT EXISTS idx_documents_co_yr ON documents(company_id, year);
CREATE INDEX IF NOT EXISTS idx_peer_percentiles_co ON peer_percentiles(company_id);
CREATE INDEX IF NOT EXISTS idx_peer_percentiles_pg ON peer_percentiles(peer_group_name);


