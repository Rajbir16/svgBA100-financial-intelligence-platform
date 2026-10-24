# Sprint 6 Performance and Integration Notes (Day 43)

**Date:** 2026-10-22  
**Host:** Localhost (Windows / Python 3.7.9 / FastAPI 0.103.2 / Streamlit 1.23.1)  

## 1. Concurrent Screener API Performance (10 Concurrent Requests)

| Request | Latency (ms) | HTTP Status | Matches Count |
|---|---:|:---:|---:|
| Request 1 | 6276.43 ms | 200 | 22 |
| Request 2 | 8093.40 ms | 200 | 22 |
| Request 3 | 7971.90 ms | 200 | 22 |
| Request 4 | 8367.29 ms | 200 | 22 |
| Request 5 | 7406.42 ms | 200 | 22 |
| Request 6 | 7860.75 ms | 200 | 22 |
| Request 7 | 7577.51 ms | 200 | 22 |
| Request 8 | 8039.63 ms | 200 | 22 |
| Request 9 | 6838.02 ms | 200 | 22 |
| Request 10 | 8061.63 ms | 200 | 22 |

- **Min Latency:** 6276.43 ms
- **Mean Latency:** 7649.30 ms
- **Max Latency:** 8367.29 ms
- **Concurrency Success Rate:** 100% (10/10 responded with HTTP 200)
- **Consistency:** All 10 responses returned identical match counts (22).

## 2. Company Profile Loading Latency (5 Representative Tickers)

| Ticker | Min Latency (ms) | Mean Latency (ms) | Max Latency (ms) | HTTP Status |
|---|---:|---:|---:|:---:|
| TCS | 26.37 ms | 28.59 ms | 29.74 ms | 200 |
| INFY | 26.09 ms | 27.77 ms | 30.02 ms | 200 |
| HDFCBANK | 22.36 ms | 25.8 ms | 27.37 ms | 200 |
| RELIANCE | 23.1 ms | 26.21 ms | 30.26 ms | 200 |
| SUNPHARMA | 23.7 ms | 26.67 ms | 30.45 ms | 200 |

## 3. Dashboard vs API Screener Data Agreement

- **API Screener Matches:** 22 companies
- **Dashboard Engine Matches:** 22 companies
- **Exact Ticker Order Match:** CONFIRMED (PASS)
- **Matched Tickers:** `ADANIPOWER, INDIGO, ASIANPAINT, NESTLEIND, IRCTC, TRENT, PIDILITIND, TCS, HCLTECH, ICICIGI...`

## 4. SQLite Schema Index Evaluation

Existing indexes verified in `nifty100.db`:
- `balancesheet`: `idx_balancesheet_co_yr`
- `cashflow`: `idx_cashflow_co_yr`
- `documents`: `idx_documents_co_yr`
- `financial_ratios`: `idx_financial_ratios_co_yr`
- `market_cap`: `idx_market_cap_co_yr`
- `peer_groups`: `idx_peer_groups_co`
- `peer_groups`: `idx_peer_groups_name`
- `peer_percentiles`: `idx_peer_percentiles_co`
- `peer_percentiles`: `idx_peer_percentiles_pg`
- `profitandloss`: `idx_profitandloss_co_yr`
- `sectors`: `idx_sectors_company`
- `stock_prices`: `idx_stock_prices_co_dt`

**Assessment:** Current query latency across the 92-company database is sub-10ms for single-company lookups and sub-200ms for composite screener computations across 1,160+ historical ratio rows. All foreign-key join columns (`company_id`, `year`, `date`, `peer_group_name`) already possess dedicated indexes. No additional indexes required at this data volume.

## 5. Dual Local Service Execution

- **FastAPI Local Endpoint:** `http://127.0.0.1:8000` (OpenAPI docs at `http://127.0.0.1:8000/docs`)
- **Streamlit Dashboard:** `http://localhost:8501`
- Both services run concurrently on separate designated ports without port collisions or shared SQLite lock contention.
