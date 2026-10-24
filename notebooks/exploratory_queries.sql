-- ==============================================================================
-- svgBA100 FINANCIAL INTELLIGENCE PLATFORM: SPRINT 1
-- Exploratory SQL Queries for nifty100.db
-- ==============================================================================

-- ------------------------------------------------------------------------------
-- 1. Total Company Count
-- Verify that the master companies table contains all 92 loaded companies.
-- ------------------------------------------------------------------------------
SELECT COUNT(*) AS total_companies
FROM companies;

-- ------------------------------------------------------------------------------
-- 2. Companies by Broad Sector and Sub-Sector
-- Industry distribution of Nifty 100 universe.
-- ------------------------------------------------------------------------------
SELECT 
    broad_sector,
    sub_sector,
    COUNT(company_id) AS company_count,
    ROUND(SUM(index_weight_pct), 2) AS total_sector_weight_pct
FROM sectors
GROUP BY broad_sector, sub_sector
ORDER BY total_sector_weight_pct DESC;

-- ------------------------------------------------------------------------------
-- 3. Financial-Year Coverage Summary
-- Minimum, maximum, and total distinct reporting periods per company in P&L.
-- ------------------------------------------------------------------------------
SELECT 
    company_id,
    COUNT(DISTINCT year) AS total_periods,
    MIN(year) AS earliest_period,
    MAX(year) AS latest_period
FROM profitandloss
WHERE year != 'TTM'
GROUP BY company_id
ORDER BY total_periods DESC, company_id ASC;

-- ------------------------------------------------------------------------------
-- 4. P&L Row Counts by Company
-- Distribution of income statement data depth.
-- ------------------------------------------------------------------------------
SELECT 
    company_id,
    COUNT(*) AS pnl_records_count,
    SUM(CASE WHEN year = 'TTM' THEN 1 ELSE 0 END) AS has_ttm
FROM profitandloss
GROUP BY company_id
ORDER BY pnl_records_count DESC;

-- ------------------------------------------------------------------------------
-- 5. Balance Sheet Row Counts and Balance Verification
-- Checks that total assets match total liabilities across balance sheets.
-- ------------------------------------------------------------------------------
SELECT 
    company_id,
    COUNT(*) AS bs_records_count,
    SUM(CASE WHEN ABS(total_assets - total_liabilities) > 1.0 THEN 1 ELSE 0 END) AS balance_mismatches
FROM balancesheet
GROUP BY company_id
ORDER BY bs_records_count DESC;

-- ------------------------------------------------------------------------------
-- 6. Cash Flow Row Counts and Cumulative Net Cash Flow
-- Summary of cash flow statements and aggregated net cash flow generation.
-- ------------------------------------------------------------------------------
SELECT 
    company_id,
    COUNT(*) AS cashflow_records_count,
    ROUND(SUM(operating_activity), 2) AS cumulative_operating_cf,
    ROUND(SUM(net_cash_flow), 2) AS cumulative_net_cf
FROM cashflow
GROUP BY company_id
ORDER BY cumulative_operating_cf DESC;

-- ------------------------------------------------------------------------------
-- 7. Stock Price Coverage
-- Historical price records, timespan, and total trading volume per company.
-- ------------------------------------------------------------------------------
SELECT 
    company_id,
    COUNT(*) AS monthly_price_bars,
    MIN(date) AS start_date,
    MAX(date) AS end_date,
    ROUND(MIN(low_price), 2) AS all_time_low,
    ROUND(MAX(high_price), 2) AS all_time_high,
    SUM(volume) AS total_volume_traded
FROM stock_prices
GROUP BY company_id
ORDER BY monthly_price_bars DESC, company_id ASC;

-- ------------------------------------------------------------------------------
-- 8. Companies with Fewer than 5 Financial Reporting Years
-- Identifies newly listed or coverage-limited companies.
-- ------------------------------------------------------------------------------
SELECT 
    c.id AS company_id,
    c.company_name,
    COUNT(DISTINCT p.year) AS statement_years
FROM companies c
LEFT JOIN profitandloss p ON c.id = p.company_id AND p.year != 'TTM'
GROUP BY c.id, c.company_name
HAVING statement_years < 5
ORDER BY statement_years ASC;

-- ------------------------------------------------------------------------------
-- 9. Foreign-Key Integrity Verification
-- PRAGMA foreign_key_check returns 0 rows if relational integrity is intact.
-- ------------------------------------------------------------------------------
PRAGMA foreign_key_check;

-- ------------------------------------------------------------------------------
-- 10. Sample Company Financial History (Tata Consultancy Services - TCS)
-- Comprehensive multi-year view across P&L, Balance Sheet, and Cash Flow.
-- ------------------------------------------------------------------------------
SELECT 
    p.company_id,
    p.year,
    p.sales,
    p.operating_profit,
    p.opm_percentage,
    p.net_profit,
    b.total_assets,
    b.borrowings,
    cf.net_cash_flow
FROM profitandloss p
LEFT JOIN balancesheet b ON p.company_id = b.company_id AND p.year = b.year
LEFT JOIN cashflow cf ON p.company_id = cf.company_id AND p.year = cf.year
WHERE p.company_id = 'TCS'
ORDER BY p.id ASC;

-- ------------------------------------------------------------------------------
-- 11. Peer Groups and Benchmark Distribution
-- Lists benchmark companies and their designated peer categories.
-- ------------------------------------------------------------------------------
SELECT 
    pg.peer_group_name,
    pg.company_id,
    c.company_name,
    pg.is_benchmark
FROM peer_groups pg
JOIN companies c ON pg.company_id = c.id
ORDER BY pg.peer_group_name ASC, pg.is_benchmark DESC;

-- ------------------------------------------------------------------------------
-- 12. Market Capitalisation and Valuation Overview (Latest 2024 Year)
-- Top 10 companies by market capitalisation with P/E and P/B ratios.
-- ------------------------------------------------------------------------------
SELECT 
    mc.company_id,
    c.company_name,
    mc.year,
    mc.market_cap_crore,
    mc.pe_ratio,
    mc.pb_ratio,
    mc.dividend_yield_pct
FROM market_cap mc
JOIN companies c ON mc.company_id = c.id
WHERE mc.year = 2024
ORDER BY mc.market_cap_crore DESC
LIMIT 10;

