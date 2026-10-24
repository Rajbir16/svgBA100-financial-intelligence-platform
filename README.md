# svgBA100 Financial Intelligence Platform
## Sprint 1 — Data Foundation

The **svgBA100 Financial Intelligence Platform** is an institutional-grade financial analytics and data intelligence platform built to ingest, normalize, validate, and store comprehensive financial, valuation, and market data for India's **Nifty 100** universe.

Sprint 1 establishes the **Data Foundation**:
- Structured SQLite database: `nifty100.db` with relational constraints (`PRAGMA foreign_keys = ON;`)
- High-performance deterministic ETL pipeline: `src/etl/loader.py`, `src/etl/normaliser.py`
- 16 automated Data Quality (DQ) validation rules: `src/etl/validator.py`
- Comprehensive test suite: 49 automated unit and integration tests (0 failures)
- Audit logs and validation failure reporting: `output/load_audit.csv`, `output/validation_failures.csv`
- Exploratory SQL queries: `notebooks/exploratory_queries.sql`

---

## 1. Project Architecture

```
svgBA100 Financial Intelligence Platform/
├── db/
│   └── schema.sql                  # Database DDL: 12 tables, strict FKs, and indexes
├── src/
│   ├── __init__.py
│   └── etl/
│       ├── __init__.py
│       ├── loader.py               # Excel ETL loader, transaction control, audit generation
│       ├── normaliser.py           # Field normalization (year, ticker, numeric, date)
│       └── validator.py            # 16 Data Quality rules (DQ-01 to DQ-16)
├── tests/
│   ├── __init__.py
│   └── etl/
│       ├── __init__.py
│       ├── test_loader.py          # Integration tests for schema, transactions, and loading
│       ├── test_normaliser.py      # Unit tests for normalization functions
│       └── test_validator.py       # Unit tests for 16 DQ rules and severity checks
├── notebooks/
│   └── exploratory_queries.sql     # 12 analytical, coverage, and verification SQL queries
├── output/
│   ├── load_audit.csv              # Audit per table (read, inserted, rejected, status)
│   └── validation_failures.csv     # Line-by-line DQ issues (rule_id, severity, message)
├── nifty100.db                     # Authoritative SQLite database
├── requirements.txt                # Lean Python dependencies
├── .env.example                    # Environment template
├── Makefile                        # Automation targets (install, load, validate, test, all)
└── README.md                       # Complete documentation
```

---

## 2. Source Datasets & Schema Mapping

The pipeline reads the 12 raw Excel files located in `Downloads/Dataset_sprint 2`. The loader automatically detects whether headers start in row 1 or row 2 (handling files with metadata title banners):

| # | Source Dataset File | Target Table | Primary Key | Foreign Key | Rows Read | Rows Inserted | Rows Rejected |
|---|---|---|---|---|---|---|---|
| 1 | `*companies.xlsx` | `companies` | `id TEXT` | Master Table | 92 | 92 | 0 |
| 2 | `*sectors.xlsx` | `sectors` | `id INT` | `company_id -> companies(id)` | 92 | 92 | 0 |
| 3 | `*market_cap.xlsx` | `market_cap` | `id INT` | `company_id -> companies(id)` | 552 | 552 | 0 |
| 4 | `*stock_prices.xlsx` | `stock_prices` | `id INT` | `company_id -> companies(id)` | 5,520 | 5,520 | 0 |
| 5 | `*financial_ratios.xlsx` | `financial_ratios` | `id INT` | `company_id -> companies(id)` | 1,184 | 1,160 | 24 |
| 6 | `*balancesheet.xlsx` | `balancesheet` | `id INT` | `company_id -> companies(id)` | 1,312 | 1,227 | 85 |
| 7 | `*profitandloss.xlsx` | `profitandloss` | `id INT` | `company_id -> companies(id)` | 1,276 | 1,177 | 99 |
| 8 | `*cashflow.xlsx` | `cashflow` | `id INT` | `company_id -> companies(id)` | 1,187 | 1,091 | 96 |
| 9 | `*peer_groups.xlsx` | `peer_groups` | `id INT` | `company_id -> companies(id)` | 56 | 56 | 0 |
| 10 | `*analysis.xlsx` | `analysis` | `id INT` | `company_id -> companies(id)` | 20 | 16 | 4 |
| 11 | `*prosandcons.xlsx` | `prosandcons` | `id INT` | `company_id -> companies(id)` | 16 | 14 | 2 |
| 12 | `*documents.xlsx` | `documents` | `id INT` | `company_id -> companies(id)` | 1,585 | 1,457 | 128 |

### Source Data Referential Integrity Note
The raw files for statement data contain records referencing 9 companies (`AGTL`, `ULTRACEMCO`, `UNIONBANK`, `UNITDSPR`, `VBL`, `VEDL`, `WIPRO`, `ZOMATO`, `ZYDUSLIFE`) that are **not present** in the master `companies.xlsx` file (which contains exactly 92 companies).

To maintain strict relational integrity without inventing non-existent company records:
1. `companies` preserves the authoritative 92 companies (`SELECT COUNT(*) FROM companies` = 92).
2. The loader rejects orphan records before database insertion (Rule `DQ-03`).
3. Rejections are documented in `output/load_audit.csv` and `output/validation_failures.csv`.
4. `PRAGMA foreign_key_check;` returns **0 violations**.

---

## 3. Data Quality (DQ) Rules

The validation module (`src/etl/validator.py`) implements the 16 Sprint 1 DQ rules:

| Rule ID | Name | Severity | Description |
|---|---|---|---|
| **DQ-01** | Primary-Key Validity | `CRITICAL` | Ensures `id` is not null, not empty, and integer > 0 (or valid string for companies). |
| **DQ-02** | Primary-Key Uniqueness | `CRITICAL` | Ensures `id` is globally unique across each table. |
| **DQ-03** | Foreign-Key Validity | `CRITICAL` | Ensures child `company_id` exists in master `companies(id)`. |
| **DQ-04** | Required Company ID | `CRITICAL` | Flags any record where `company_id` is null or empty. |
| **DQ-05** | Valid Year / Date | `WARNING` | Verifies financial reporting years match standard period patterns (`YYYY`, `Mon YYYY`, `TTM`). |
| **DQ-06** | Duplicate Company/Year | `WARNING` | Detects multiple statement submissions for the same `(company_id, year)` pair. |
| **DQ-07** | Numeric Field Validity | `WARNING` | Detects non-numeric characters in numeric financial columns. |
| **DQ-08** | Impossible / Null Critical Values | `WARNING` | Checks that critical statement totals (`total_assets`, `close_price`) are not null or negative. |
| **DQ-09** | Stock Price Logic | `WARNING` | Verifies `high >= low`, `high >= open`, `high >= close`, and `volume >= 0`. |
| **DQ-10** | Financial Cross-Consistency | `WARNING` | Compares net profit in P&L against net profit margin in financial ratios. |
| **DQ-11** | Sales Validity | `WARNING` | Verifies non-negative sales numbers. |
| **DQ-12** | Operating Profit / OPM Consistency | `WARNING` | Checks `sales - expenses ≈ operating_profit` and `opm ≈ (operating_profit / sales) * 100`. |
| **DQ-13** | Balance Sheet Consistency | `WARNING` | Verifies `total_assets == total_liabilities == equity + reserves + borrowings + other_liabilities`. |
| **DQ-14** | Cash Flow Consistency | `WARNING` | Verifies `operating_activity + investing_activity + financing_activity ≈ net_cash_flow`. |
| **DQ-15** | Company Year Coverage | `INFO` | Identifies companies with fewer than 5 financial reporting years. |
| **DQ-16** | Unexpected / Malformed Values | `INFO` | Flags untrimmed whitespace, raw string placeholders (`"NA"`, `"-"`, `"null"`). |

---

## 4. Setup & Quick Start

### Installation
```bash
pip install -r requirements.txt
```

### Run Full ETL Load
Loads and normalizes all 12 datasets into `nifty100.db`:
```bash
python -m src.etl.loader --db nifty100.db --data-dir "C:\Users\rajbi\Downloads\Dataset_sprint 2"
```

### Validate Database Integrity
Runs all DQ rules against the generated SQLite database:
```bash
python -m src.etl.validator --db nifty100.db
```

### Run Automated Tests
Executes the full test suite with pytest:
```bash
python -m pytest tests/ -v
```

### Using Makefile
```bash
make install     # Install dependencies
make load        # Run ETL loader
make validate    # Run DQ validator
make test        # Run test suite
make all         # Install, load, validate, and test
```

---

## 5. Manual Review: 5 Representative Companies

Execution summary of statement depth for sample Nifty 100 companies:

```
==============================================================================
MANUAL REVIEW REPORT: 5 REPRESENTATIVE COMPANIES COVERAGE
==============================================================================
Company      | Years (P&L)  | P&L Rows  | BS Rows  | CF Rows  | Prices   | Ratios  
------------------------------------------------------------------------------
ABB          | 12           | 13        | 13       | 23       | 60       | 23      
HDFCBANK     | 12           | 13        | 12       | 12       | 60       | 12      
INFY         | 12           | 13        | 13       | 12       | 60       | 12      
RELIANCE     | 12           | 13        | 13       | 12       | 60       | 12      
TCS          | 12           | 13        | 13       | 24       | 60       | 12      
==============================================================================
```

---

## 6. Sprint 2 — Financial Ratio Engine

Run the computed engine after the ETL load:

```bash
python -m src.analytics.ratios --db nifty100.db --output-dir output
```

The engine deduplicates statement inputs by `(company_id, year)`, deletes source-loaded ratio rows, and repopulates `financial_ratios` from P&L, balance-sheet, and cash-flow data. It is idempotent and currently produces 1,249 unique rows for the 92-company database.

Implemented KPI decisions:

- NPM, OPM, ROE, ROCE, ROA, D/E, ICR, net debt, and asset turnover use safe denominator handling. ROE is suppressed for non-positive equity; D/E is zero when borrowings are zero; ICR is labelled `Debt Free` when interest is zero.
- Revenue, PAT, and EPS 3/5/10-year CAGR values use exact calendar-year endpoints. Flags are stored separately as `NORMAL`, `DECLINE_TO_LOSS`, `TURNAROUND`, `BOTH_NEGATIVE`, `ZERO_BASE`, or `INSUFFICIENT`.
- FCF is CFO + CFI. CFO Quality is the average CFO/PAT over the latest five available years. CapEx Intensity uses `abs(CFI) / sales`; FCF Conversion is FCF / operating profit.
- Composite Quality Score is a normalized weighted average of OPM (30%), ROE (30%), CFO Quality (20%), and ICR (20%). Missing components are omitted and the remaining weights are renormalized; a row with no components remains NULL.
- High D/E warnings are suppressed for the 23 `Financials` companies. Computed OPM is cross-checked against source OPM above 1%; computed ROE and ROCE are cross-checked against company source values above 5%. Differences are categorized in `output/ratio_edge_cases.log` and computed values remain authoritative.
- Capital allocation patterns are written to `output/capital_allocation.csv` with sign columns and labels including Reinvestor, Shareholder Returns, Liquidating Assets, Distress Signal, Growth Funded by Debt, Cash Accumulator, Pre-Revenue, and Mixed.

Sprint 2 includes 20 formula tests under `tests/kpi/`; the complete suite contains 69 passing tests.

## 7. Sprint 3 — Screener + Peer Engine

Sprint 3 implements an institutional-grade stock screener, sector-relative composite scoring engine, peer percentile ranking, radar chart visualizer, and formatted Excel reporting.

### Key Components

1. **Configuration (`config/screener_config.yaml`)**:
   - 15 filterable metrics: ROE min, D/E max, FCF min, Revenue CAGR 5yr min, PAT CAGR 5yr min, OPM min, P/E max, P/B max, Dividend Yield min, ICR min, Market Cap min, Net Profit min, EPS CAGR min, Asset Turnover min, Sales min.
   - Built-in rules: D/E filter skips `Financials` sector; `Debt Free` ICR = infinity; results sorted by `composite_quality_score` descending.

2. **6 Predefined Screener Presets**:
   - **Quality Compounder** (22 companies): ROE >15%, D/E <1, FCF >0, Revenue CAGR 5yr >10%
   - **Value Pick** (5 companies): P/E <20, P/B <4.5, D/E <2, Dividend Yield >1%
   - **Growth Accelerator** (19 companies): PAT CAGR 5yr >20%, Revenue CAGR 5yr >15%, D/E <2
   - **Dividend Champion** (30 companies): Dividend Yield >2%, Dividend Payout <80%, FCF >0
   - **Debt-Free Blue Chip** (31 companies): D/E <=0.05 (virtually debt-free), ROE >12%, Revenue >5000 Cr
   - **Turnaround Watch** (33 companies): Revenue CAGR 3yr >10%, latest FCF positive, D/E declining YoY
   - *All presets strictly return between 5 and 50 companies.*

3. **Composite Quality Score (0–100)**:
   - **Profitability (35%)**: ROE (15), ROCE (10), NPM (10)
   - **Cash Quality (30%)**: FCF CAGR 5yr (15), CFO/PAT (10), FCF positive (5)
   - **Growth (20%)**: Revenue CAGR 5yr (10), PAT CAGR 5yr (10)
   - **Leverage (15%)**: D/E score (10, lower is better, Financials benchmarked), ICR score (5, Debt Free = 100)
   - **Normalization Decisions**: Sector-relative scaling grouped by `broad_sector` with P10/P90 winsorisation to eliminate outlier skew. Scaled to [0, 100].

4. **Peer Engine (`src/analytics/peer.py` & `peer_percentiles` table)**:
   - 11 peer groups across 10 financial metrics: ROE, ROCE, NPM, D/E (inverted so lower D/E = higher percentile), FCF, PAT CAGR 5yr, Revenue CAGR 5yr, EPS CAGR 5yr, Interest Coverage, Asset Turnover.
   - Stored in SQLite table `peer_percentiles` (560 rows).
   - Companies without a peer group safely return `"No peer group assigned"` without crashing.

5. **Visualizations & Excel Reports**:
   - `output/screener_output.xlsx`: 6 preset sheets, 20 KPI columns, sorted by composite score, green cell conditional formatting for qualifying criteria.
   - `output/peer_comparison.xlsx`: 11 peer group sheets, 20 metric columns + percentiles, conditional color fills (>=75 green, 25-75 yellow, <25 red), benchmark company row highlighted, and peer median summary row.
   - `reports/radar_charts/`: 92 radar chart PNGs across 8 financial dimensions. Companies with peer groups plot against peer average outline; companies without peer groups plot against Nifty 100 universe average.

---

## 8. Verification Results

- **Database**: `nifty100.db` generated and verified.
- **Company Count**: `SELECT COUNT(*) FROM companies;` -> **92**
- **Foreign Key Check**: `PRAGMA foreign_key_check;` -> **0 violations**
- **Peer Percentile Rows**: **560** (11 peer groups × 10 metrics)
- **Automated Tests**: **83 passed**, 0 failed
  - 49 Sprint 1 ETL/DQ tests (`tests/etl/`)
  - 20 Sprint 2 KPI formula tests (`tests/kpi/`)
  - 14 Sprint 3 Screener, Peer Engine, Scoring & Report tests (`tests/screener/`)
- **Generated Artifacts**:
  - `config/screener_config.yaml`
  - `output/screener_output.xlsx` (6 sheets)
  - `output/peer_comparison.xlsx` (11 sheets)
  - `reports/radar_charts/` (92 PNG charts)
  - `output/capital_allocation.csv`
  - `output/ratio_edge_cases.log`

---

## 9. Sprint 4 — Streamlit Dashboard & Valuation

Sprint 4 delivers an institutional-grade, multi-page financial analytics portal built on Streamlit with Plotly charts, alongside an automated valuation and multiple flag evaluation engine.

### Launch Instructions

Run the application from the project root:
```bash
streamlit run src/dashboard/app.py
```
*(Or alternatively: `python -m streamlit run src/dashboard/app.py`)*

Default URL:
```
http://localhost:8501
```

Configuration:
- **Title**: `Nifty 100 Analytics`
- **Layout**: `wide`
- **Sidebar**: Initially expanded with branding and navigation menu

---

### Dashboard Architecture & The 8 Specialized Screens

The application features 8 dedicated analytics modules:

1. **Home (`pages/01_home.py`)**:
   - **6 Macro KPI Tiles**: Average ROE, Median P/E, Median D/E, Universe Size (92 companies), Median 5-year Revenue CAGR, and Debt-Free Companies Count.
   - **Sector Distribution**: Interactive Plotly donut chart across the 10 broad sectors mapped in the database.
   - **Quality Leaders**: Top-5 companies ranked by Composite Quality Score.
   - **Year Selector**: Dynamic fiscal period selector (2019–2024) in the sidebar.

2. **Company Profile (`pages/02_profile.py`)**:
   - Searchable autocomplete dropdown by ticker or company name.
   - Company metadata, sector, sub-sector, and official filings/profile links.
   - **6 KPI Summary Cards**: ROE, ROCE, Net Margin, Debt-to-Equity, 5Y Revenue CAGR, and latest FCF.
   - **Dual Visualizations**: 10-year Revenue & Net Profit grouped bar chart and dual-trajectory ROE vs ROCE line chart.
   - **Institutional Pros & Cons**: Diagnostic bullet analysis formatted strictly with `✓` for strengths and `✗` for risks.
   - Safe degradation handling for partial data and invalid tickers.

3. **Financial Screener (`pages/03_screener.py`)**:
   - **10 Interactive Sliders**: ROE min, D/E max, FCF min, Rev CAGR 5Y min, PAT CAGR 5Y min, OPM min, P/E max, P/B max, Dividend Yield min, and ICR min.
   - **6 Strategy Presets**: Quality Compounder, Value Pick, Growth Accelerator, Dividend Champion, Debt-Free Blue Chip, and Turnaround Watch (reusing Sprint 3 screener engine logic).
   - **Result Counter**: Displays `"X companies match your filters"`.
   - **Instant CSV Export**: UTF-8 encoded download button with comprehensive ratio columns.

4. **Peer Comparison (`pages/04_peers.py`)**:
   - Covers all **11 Industry Peer Groups**: Automobiles, Consumer Finance, FMCG, IT Services, Life Insurance, Oil & Gas, Pharmaceuticals, Power & Utilities, Private Banks, Public Sector Banks, and Steel.
   - **8-Axis Scatterpolar Radar Chart**: Benchmarks selected enterprise against peer-group average across ROE, ROCE, NPM, D/E (inverted), FCF Score, PAT CAGR 5Y, Revenue CAGR 5Y, and Composite Score (all normalized to 0–100 scale).
   - **Peer Matrix Table**: Full constituent KPI table with the selected company highlighted.

5. **Trend Analysis (`pages/05_trends.py`)**:
   - Multi-metric longitudinal tracker allowing selection of up to 3 financial metrics.
   - 10-year Plotly line charts with automated Year-over-Year (YoY) percentage change annotations on each historical node.
   - Dual-axis synchronization for metrics with differing units (e.g. ₹ Cr vs %).

6. **Sector Analysis (`pages/06_sectors.py`)**:
   - Broad-sector filter dropdown.
   - **Multi-Dimensional Bubble Chart**: X = Revenue (₹ Cr), Y = Return on Equity (%), Bubble Size = Market Cap (₹ Cr), Color = Sub-Sector.
   - **Cross-Sector Medians**: Interactive bar chart comparing median ROE, ROCE, OPM, P/E, or D/E across all sectors.

7. **Capital Allocation (`pages/07_capital.py`)**:
   - Visualizes all 92 companies mapped to Sprint 2's **8 Capital Allocation Patterns** based on cash flow signs (+/- CFO, CFI, CFF):
     - *Shareholder Returns*, *Reinvestor*, *Mixed*, *Growth Funded by Debt*, *Liquidating Assets*, *Distress Signal*, *Pre-Revenue*, and *Cash Accumulator*.
   - **Hierarchical Treemap**: Plotly treemap sized by market capitalization with interactive pattern filtering.

8. **Annual Reports Vault (`pages/08_reports.py`)**:
   - Searchable corporate regulatory filings repository covering 1,457+ documents.
   - Clickable direct PDF links to official BSE India annual reports.
   - Automated online availability verification with red `"Report unavailable"` notification upon 404 or missing URLs.

---

### Valuation Analytics Engine (`src/analytics/valuation.py`)

Computes institutional valuation metrics, sector-relative medians, and valuation flags:
- **FCF Yield**: `(Free Cash Flow / Market Cap Crore) * 100`
- **5-Year Median P/E**: Computed from historical annual market cap multiples (2020–2024).
- **Sector Median P/E**: Benchmark median calculated per broad industrial sector.
- **Valuation Flags**:
  - `P/E > Sector Median * 1.5` => **Caution** (Overvalued)
  - `P/E < Sector Median * 0.7` => **Discount** (Undervalued)
  - Otherwise => **Fair**

#### Generated Output Artifacts:
- **`output/valuation_summary.xlsx`**: Exactly **92 rows** containing the 10 required columns:
  `company_id`, `company_name`, `sector`, `P/E`, `P/B`, `EV/EBITDA`, `FCF_yield_pct`, `5yr_median_PE`, `PE_vs_sector_median_pct`, `flag`.
- **`output/valuation_flags.csv`**: Filtered dataset of **44 rows** containing only actionable companies flagged as **Caution** (14 companies) or **Discount** (30 companies).

---

### Sprint 4 Verification & Performance Audit

- **Company Universe**: Full **92 companies** supported with 0 missing records.
- **Foreign Key Check**: `PRAGMA foreign_key_check` -> `[]` (0 violations).
- **Test Suite**: **83 passed** out of 83 across ETL, KPI ratio formulas, and Screener tests.
- **Profile Load Latency**: Benchmarked on 5 diverse tickers (`TCS`: 0.31s, `HDFCBANK`: 0.02s, `ITC`: 0.02s, `RELIANCE`: 0.02s, `SUNPHARMA`: 0.02s), all well below the **< 3.0s** institutional requirement.
- **Streamlit Local Server**: Verified live on `http://localhost:8501` (HTTP 200 OK).

---

## 10. Sprint 5 (Phase 1) — NLP Analysis Parser & Pros/Cons Generator

Sprint 5 Phase 1 introduces automated financial text parsing and rule-based diagnostic commentary generation.

### Day 29 — NLP Analysis Text Parser (`src/nlp/parser.py`)

- **Regular Expression Parser**: Parses multi-period financial text blocks (e.g., `5 Years: 18.5%`, `10 Years: 21%`, `5 Years 14%`, `1 Year: -2%`) supporting spacing variations, singular/plural `Year`/`Years`, optional colons and hyphens, negative values, and decimal values.
- **Parsed Dataset (`output/analysis_parsed.csv`)**: 52 unique rows covering all 4 analysis metrics (`compounded_sales_growth`, `compounded_profit_growth`, `stock_price_cagr`, `roe`) for valid master companies.
  - Columns: `company_id, metric_type, period_years, value_pct`.
- **Diagnostics & Failures (`output/parse_failures.csv`)**: 28 recorded failure entries detailing unmapped companies (e.g. `WIPRO` not present in master table) and non-numeric period labels (e.g. `TTM` and `Last Year`).
  - Columns: `company_id, source_field, original_text, failure_reason`.
- **CAGR Cross-Validation (`output/cagr_cross_validation.csv`)**: Cross-validates parsed 3Y/5Y/10Y sales and profit CAGRs against the Ratio Engine calculations from `financial_ratios`. Identifies and flags absolute divergence > 5 percentage points (`INFY` 3Y sales CAGR flagged for review).

### Day 30 — Automatic Pros & Cons Generator (`src/nlp/pros_cons_generator.py`)

- **12 Quantitative Pro Rules**:
  - `PRO_01`: ROE sustained above 20% for >= 3 consecutive years
  - `PRO_02`: Positive Free Cash Flow for 5 consecutive years
  - `PRO_03`: Latest Debt-to-Equity equals zero
  - `PRO_04`: Revenue CAGR above 15% over 5 years
  - `PRO_05`: Latest Operating Profit Margin above 25%
  - `PRO_06`: PAT CAGR above 20% over 5 years
  - `PRO_07`: Interest Coverage Ratio above 10x or Debt Free
  - `PRO_08`: Dividend Yield above 2% backed by positive Free Cash Flow
  - `PRO_09`: EPS CAGR above 15% over 5 years
  - `PRO_10`: ROE improving for 3 consecutive annual observations
  - `PRO_11`: Revenue CAGR exceeds PAT CAGR (`revenue_cagr_5yr > pat_cagr_5yr` with exact supplied operating leverage text)
  - `PRO_12`: Asset base expands while total debt declines
- **12 Quantitative Con Rules**:
  - `CON_01`: Debt-to-Equity > 2.0 for non-financial enterprises (strictly suppresses Financials sector)
  - `CON_02`: Negative Free Cash Flow for 3 consecutive years
  - `CON_03`: Operating Profit Margin declining for 3 consecutive years
  - `CON_04`: Latest financial year reported net loss
  - `CON_05`: Revenue contracting for 2 or more consecutive annual periods
  - `CON_06`: Interest Coverage Ratio below 1.5x
  - `CON_07`: Dividend Payout Ratio exceeds 100%
  - `CON_08`: Debt-to-Equity rising for 3 consecutive annual observations
  - `CON_09`: EPS declining for 3 consecutive annual observations
  - `CON_10`: Return on Capital Employed (ROCE) below 10%
  - `CON_11`: Net Debt exceeds 3x EBITDA (applied only when both are strictly available)
  - `CON_12`: Revenue CAGR below 5% over 5 years
- **Confidence Scoring & Output Filtering**: Transparent confidence scoring (0–100) based on data audit completeness, history depth, and period consistency. Only rules with `confidence_pct > 60` are emitted.
- **Generated Dataset (`output/pros_cons_generated.csv`)**: 596 generated records (412 Pros, 184 Cons) covering 92 companies.
  - Columns: `company_id, type, rule_id, text, confidence_pct`.
- **Coverage & Unresolved Reporting (`output/pros_cons_unresolved.csv`)**: 90 of 92 companies have both Pro and Con coverage. Exactly 2 companies (`SBIN` and `SIEMENS`) have pro coverage but no con criteria met due to zero excessive debt, robust returns, and positive cash generation.

---

### Sprint 5 (Phase 1) Verification

- **Automated Tests**: **127 passed**, 0 failed (`pytest tests/ -v`):
  - 49 Sprint 1 ETL & DQ tests (`tests/etl/`)
  - 20 Sprint 2 KPI formula tests (`tests/kpi/`)
  - 14 Sprint 3 Screener, Peer Engine, & Scoring tests (`tests/screener/`)
  - 44 Sprint 5 NLP Parser & Pros/Cons tests (`tests/nlp/`)
- **Foreign Key Check**: `PRAGMA foreign_key_check` -> `[]` (0 violations).

## 11. Sprint 5 Phase 3 — Company, Sector & Portfolio PDF Reports

### Day 33 — Company Tear Sheets

`src/reports/tearsheet.py` generates an A4 two-page company tear sheet, including
financial KPIs, revenue/profit and return charts, balance-sheet and cash-flow
visuals, pros/cons, and the capital-allocation pattern.

```bash
python -m src.reports.tearsheet
```

- **Generated**: 91 company PDFs in `reports/tearsheets/`.
- **Skipped**: `JIOFIN` has only two annual P&L observations; the minimum is
  three. The reason and observation count are recorded in
  `output/skipped_tearsheets.csv`.
- **Validation**: All 91 PDFs contain exactly two A4 pages, the company identity,
  both report sections, and non-empty content.

### Day 34 — Batch & Sector Reports

Batch company generation is performed by the Day 33 command above. Generate
one sector overview PDF per broad sector with:

```bash
python -m src.reports.sector_report
```

- **Generated**: 10 one-page A4 sector reports in `reports/sector/`, covering
  all 92 companies.
- Each report includes sector KPI medians and company-level fundamentals.

### Day 35 — Portfolio Summary

```bash
python -m src.reports.portfolio_report
```

- **Generated**: `reports/portfolio/portfolio_summary.pdf`, a 17-page A4
  portfolio summary with sector market-cap allocation, top holdings, and one
  detailed company card for each member of the universe.
- **Coverage**: 92 companies, all 10 sectors, and 92/92 latest market-cap
  observations. Every ticker occurs exactly once. Each card includes sector,
  ROE, ROCE, net margin, debt-to-equity, FCF, quality score, cash-flow quality,
  capital allocation, and five-year revenue/PAT CAGR values and flags. Source
  fields without data are shown as `N/A` or `Insufficient Data`.

### Sprint 5 Phase 3 Verification

- **Cash-flow and report tests**: 20 passed across
  `tests/analytics/test_cashflow_intelligence.py` and
  `tests/reports/test_report_generation.py`.
- **Full test suite**: 147 passed (`pytest tests -q`), with no exclusions.
- **Day 31/32 compatibility repair**: Restored the eight-pattern public
  `ALL_PATTERNS` constant and the cash-flow helpers/artifact exporter imported
  by the existing analytics tests. All eight established labels remain
  available.
- **Generated artifacts**: 91 company tear sheets, 10 sector reports, one
  portfolio report, and the JIOFIN skip record.
- **Sector-count reconciliation**: The authoritative `sectors.broad_sector`
  mapping contains 10 populated groups across all 92 companies, and all 10
  corresponding sector PDFs exist and contain their mapped companies. The
  separate peer-group table contains 11 industry peer groups; those peer
  groups are not additional broad sectors, so no eleventh sector report was
  invented.
- **Portfolio PDF audit**: 17 A4 pages, 92/92 unique tickers exactly once, and
  92 individual company cards. All cards include the required KPI, cash-flow,
  capital-allocation, and trend fields.

---

## 12. Sprint 6 — Advanced Analytics, REST API, Performance & Institutional Audit (Days 36–45)

Sprint 6 completes the institutional capabilities of the **svgBA100 Financial Intelligence Platform**:

### Day 36–37: Clustering & Statistical Intelligence
- **Module**: `src/analytics/clustering.py`
- **Features Used (5 KPIs)**: `return_on_equity_pct`, `debt_to_equity`, `revenue_cagr_5yr`, `fcf_cagr_5yr`, `operating_profit_margin_pct`.
- **Missing Value Imputation**: Broad-sector median imputation before scaling, with portfolio-median fallback for empty sectors (e.g. Communication Services FCF CAGR).
- **K-Means Clustering**: `n_clusters=5`, `random_state=42`, normalized with `StandardScaler`. Generates `output/cluster_labels.csv` (92 rows: `company_id, cluster_id, cluster_name, distance_from_centroid`).
- **5 Archetypes (Provisional)**:
  1. `High-Margin Cash Generators` (n=14)
  2. `Core Quality Compounders` (n=60)
  3. `High Capital Turnover & Scale` (n=2: BEL, HAL)
  4. `Hyper FCF Outlier` (n=1: CIPLA)
  5. `High-Leverage Financials & Utilities` (n=15)
- **Elbow Analysis**: `reports/elbow_plot.png` (inertia for k=2..10).
- **Correlation Heatmap**: `reports/correlation_heatmap.png` (10 primary KPIs Pearson correlation).
- **Outlier Detection**: `output/outlier_report.csv` (9 observations flagged where within-sector |Z-score| > 3.0).
- **Portfolio Distribution Stats**: `output/portfolio_stats.csv` (P10, P25, P50, P75, P90, mean, std).

### Day 38–40: Production RESTful FastAPI Service
- **Application Core**: `src/api/main.py` mounted under `/api/v1` with CORS middleware and millisecond-precision request timing/logging.
- **21 REST Endpoints**:
  - `Health`: `/api/v1/health`, `/api/v1/health/counts`
  - `Companies`: `/api/v1/companies`, `/api/v1/companies/{ticker}`, `/api/v1/companies/{ticker}/pnl`, `/api/v1/companies/{ticker}/balancesheet`, `/api/v1/companies/{ticker}/cashflow`, `/api/v1/companies/{ticker}/ratios`, `/api/v1/companies/{ticker}/tearsheet` (PDF download)
  - `Screener`: `/api/v1/screener`, `/api/v1/screener/presets` (supports 6 presets, custom thresholds, sort order asc/desc)
  - `Sectors`: `/api/v1/sectors`, `/api/v1/sectors/{sector_name}` (10 authoritative broad sectors)
  - `Peers`: `/api/v1/peers`, `/api/v1/peers/{group_name}`, `/api/v1/companies/{ticker}/peers` (11 peer cohorts)
  - `Valuation`: `/api/v1/valuation/summary`, `/api/v1/companies/{ticker}/valuation`
  - `Portfolio`: `/api/v1/portfolio/stats`, `/api/v1/portfolio/clusters`
  - `Documents`: `/api/v1/companies/{ticker}/documents`
- **Documentation Exports**:
  - Interactive Swagger UI: `http://127.0.0.1:8000/docs`
  - OpenAPI Specification: `docs/openapi.json`
  - Postman Collection v2.1: `docs/postman_collection.json`

### Day 41–42: Automated Regression Testing
- **Test Suite**: 179 total tests passing with 0 failures, 0 errors, 0 skipped.
- **Coverage**: Analytics, ETL, Normalization, Data Quality, KPI Engine, NLP Text Parser, Pros/Cons Generator, Cash Flow Intelligence, PDF Reports, Screener Engine, and RESTful API Endpoints.
- **HTML Audit Report**: Generated via `pytest --html=reports/pytest_report.html --self-contained-html`.

### Day 43: Performance & Integration Verification
- **Benchmark Script**: `scripts/benchmark_perf.py` -> `output/perf_notes.md`.
- **Concurrent API Performance**: 10 concurrent requests to `/api/v1/screener` responded with 100% success rate (HTTP 200) and identical match counts.
- **Profile Loading Latency**: Single company profile requests averaged ~13ms across representative tickers (`TCS`, `INFY`, `HDFCBANK`, `RELIANCE`, `SUNPHARMA`).
- **Dashboard / API Agreement**: 100% exact match confirmed between Streamlit dashboard screener and API responses.
- **SQLite Indexes**: Evaluated 12 existing relational indexes; sub-10ms lookup times justify no additional indexing.

### Day 44: Institutional Documentation & Code Quality
- **Analyst Guide**: `docs/analyst_guide.pdf` (11 pages, publication-grade layout with running headers/footers, covering architecture, dashboard navigation, screener formulas, API integration, and troubleshooting).
- **Code Quality**: Docstrings across public functions; strict parameter validation and JSON sanitization (handling float `NaN`/`Inf` to `None`).
- **Deliverables Archive**: Staged in `output/final_deliverables/` with complete file manifest.

### Day 45: Acceptance Audit (AC-01 to AC-20)
All 20 acceptance criteria technically verified. See `reports/sprint6_acceptance_report.md` and `docs/acceptance_checklist.pdf`.

---

## 13. System Execution Commands

```bash
# 1. Run Complete Test Suite with HTML Report
python -m pytest --html=reports/pytest_report.html --self-contained-html

# 2. Run Machine Learning Clustering & Statistical Pipeline
python -m src.analytics.clustering

# 3. Launch RESTful FastAPI Server (Port 8000)
uvicorn src.api.main:app --host 127.0.0.1 --port 8000

# 4. Launch Streamlit Analytical Dashboard (Port 8501)
streamlit run src/dashboard/app.py --server.port 8501

# 5. Run Performance Benchmark Suite
python scripts/benchmark_perf.py
```
