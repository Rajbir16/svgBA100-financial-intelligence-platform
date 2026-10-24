# Sprint 5 Acceptance Audit

**Project:** svgBA100 Financial Intelligence Platform  
**Audit date:** 2026-10-14  
**Scope:** Sprint 5 Phases 1-3 and generated acceptance artifacts  
**Overall result:** Technically verified with documented data exceptions and
acceptance approvals outstanding. This report does not represent team-lead
sign-off.

## Acceptance Summary

| Criterion | Result | Evidence / exception |
|---|---|---|
| Day 29 analysis parser and validation outputs | Completed with source-data limitations | 52 parsed rows cover four master companies across all four metrics; 28 parse failures are recorded. CAGR cross-validation has 23 aligned pairs and one review flag. |
| Day 30 pros/cons generation | Partial coverage, exceptions recorded | 92/92 companies have at least one pro; 90/92 have at least one con; 90 have both. SBIN and SIEMENS have no generated con row. |
| Day 31/32 cash-flow intelligence | Completed and verified | Workbook schema and all 92 company rows checked. Distress alerts, eight-pattern distribution, and pattern transitions checked. |
| Day 33 company tear sheets | Completed for eligible data | 91 eligible companies have valid two-page A4 PDFs. JIOFIN is skipped for insufficient history. |
| Day 34 sector reports | Completed for authoritative broad-sector data | The database has 10 populated broad sectors, and all 10 matching sector PDFs are valid. The separate peer-group mapping has 11 groups. |
| Day 35 portfolio summary | Completed | 17-page A4 PDF; all 92 company tickers occur exactly once, and each company card contains each required field. |
| Full test suite | Passed | `python -m pytest tests -q` — **147 passed**, no exclusions. |
| Team-lead acceptance | Outstanding | No team-lead sign-off was provided or verified during this audit. |

## Day 29 — NLP Analysis Parser

### Generated files

- `output/analysis_parsed.csv`: **52 rows** with columns
  `company_id, metric_type, period_years, value_pct`.
- Parsed company IDs: **HDFCBANK, INFY, SBILIFE, TCS** (4 distinct companies
  out of the 92-company master universe).
- All four metrics are present: 12 compounded-sales growth, 12 compounded-
  profit growth, 16 stock-price CAGR, and 12 ROE rows.
- Duplicate `(company_id, metric_type, period_years)` records: **0**.
- Every parsed company ID exists in the master `companies` table.
- `output/parse_failures.csv`: **28 rows** with the expected diagnostic
  columns. Failure reasons comprise 16 rows for unmapped `WIPRO`, 8 TTM
  periods, and 4 `Last Year` periods.
- `output/cagr_cross_validation.csv`: **24 comparable rows**; **23 ALIGNED**
  and **1 FLAG_FOR_REVIEW**. The flagged comparison is INFY's 3-year
  compounded sales growth, divergent by **10.2165 percentage points**.

### Acceptance note

The parser artifacts and tests are present and valid, but parsed coverage is
limited to four companies. This audit does not treat 52 rows as evidence of
92-company text coverage. WIPRO is absent from the master-company data, so its
source rows remain documented parser failures. The INFY divergence remains a
manual-review item; it was not silently reconciled.

## Day 30 — Pros/Cons Coverage

`output/pros_cons_generated.csv` has **596 records** and columns
`company_id, type, rule_id, text, confidence_pct`: **412 pro** records and
**184 con** records.

| Coverage measure | Companies |
|---|---:|
| At least one pro | 92 / 92 |
| At least one con | 90 / 92 |
| At least one of each | 90 / 92 |
| Neither | 0 |

The only companies without a generated con are **SBIN** and **SIEMENS**.
`output/pros_cons_unresolved.csv` contains both and records that no con-rule
criteria were met. This is a no-trigger coverage exception, not evidence that
all con rules are unsupported: the generated data uses 11 distinct con rule
IDs. **CON_07** has no generated hit in this artifact. Rule definitions and
threshold logic are implemented in `src/nlp/pros_cons_generator.py`; the
recorded unresolved explanation is the generator's explanation and should not
be interpreted as an independent fundamental assessment.

## Day 31/32 — Cash-Flow Intelligence and Capital Allocation

### `output/cashflow_intelligence.xlsx`

- **92 data rows**, **92 unique company IDs**, and no missing sectors.
- Verified columns, in order:
  `company_id, sector, cfo_quality_score, cfo_quality_label,
  capex_intensity_pct, capex_label, fcf_cagr_5yr, fcf_conversion_pct,
  distress_flag, deleveraging_flag, capital_allocation_label`.
- Seven patterns occur in company rows; `Cash Accumulator` has zero current
  latest-year observations. The complete eight-pattern taxonomy is retained
  in the distribution output.

### Supporting CSVs

- `output/distress_alerts.csv`: **13 alerts**. Every alert has negative CFO
  and positive CFF; the expected eight columns are present.
- `output/capital_allocation_distribution.csv`: **8 pattern rows**; company
  counts sum to **92**, percentages sum to **100%**. `Cash Accumulator` is
  included with count 0.
- `output/pattern_changes.csv`: **471 transitions** across 90 companies.
  Every row changes pattern; no TTM or interim period is included.
- `src/analytics/cashflow_kpis.py` exports `ALL_PATTERNS` and the existing
  cash-flow helpers used by the tests. The eight established labels are
  preserved.

## Day 33 — Individual Company Tear Sheets

- Eligible universe according to the database: **91 companies** with at least
  three annual P&L observations.
- PDFs present: **91**, matching the eligible company set exactly.
- Page count: **2 pages each**; strict PDF parsing succeeded for every file.
- Page format: **A4**; both pages of every file contain meaningful content.
- File sizes: **47,568 to 117,571 bytes**; total **9,692,650 bytes**.
- `output/skipped_tearsheets.csv` contains one row for **JIOFIN**:
  **2 annual P&L observations**, with reason
  `Fewer than 3 annual PnL observations (2 available)`.

No tear sheets were regenerated for this audit.

## Day 34 — Sector Reports

The authoritative `sectors.broad_sector` mapping contains **10 populated
groups** covering all **92 companies**:

1. Communication Services
2. Consumer Discretionary
3. Consumer Staples
4. Energy
5. Financials
6. Healthcare
7. Industrials
8. Information Technology
9. Materials
10. Real Estate

There are **10 generated sector PDFs**, one for each mapped group. Strict PDF
opening, one-page count, sector identity, sector snapshot, fundamentals
section, median KPI rows, and each mapped company ticker were verified.

The project separately has **11 peer groups** in `peer_groups`. These are
industry peer cohorts, not `broad_sector` values. Therefore the 11 requested
sector-report count does not match the authoritative broad-sector mapping.
No artificial eleventh sector was added. The dashboard README's former
11-sector claim was corrected to reflect the database's 10 broad sectors.

## Day 35 — Portfolio Summary

`reports/portfolio/portfolio_summary.pdf`:

- **17 A4 pages**, **37,374 bytes**; strict PDF parsing succeeded.
- All **92 master tickers** appear exactly once.
- Every company has a distinct summary card. Each required field label occurs
  on **all 92 cards**:
  - sector and fiscal year;
  - market capitalization and portfolio weight;
  - ROE, ROCE, net profit margin, debt-to-equity, free cash flow, and quality
    score;
  - cash-flow quality and capital-allocation pattern;
  - revenue and PAT 5-year CAGR, each with its trend flag.
- No blank pages, out-of-page text, or PDF replacement glyphs were detected.

Where the financial source data has no value, the card displays `N/A` or an
insufficient-data status rather than an invented value.

## Full Regression Test

Command:

```text
python -m pytest tests -q
```

Recorded result:

```text
147 passed
```

No test files were excluded.

## Exceptions and Outstanding Approvals

### Verified data limitations

- **Pros/cons:** SBIN and SIEMENS have no triggered con rule in the generated
  output. Neither is missing pro coverage.
- **Parser input:** only four master companies have parsed rows; 28 rejected
  source entries remain documented. The INFY sales-CAGR comparison remains
  flagged for review.
- **Tear sheets:** JIOFIN is not eligible under the three-annual-observation
  rule and is documented with two observations.
- **Sector count:** the verified broad-sector count is 10, not 11. The extra
  count in the original specification corresponds to a different dimension:
  the 11 peer groups.
- **Cash-flow distribution:** `Cash Accumulator` is valid but has zero
  observations in the current 92-company latest-period distribution.

### Approvals not evidenced

- Team lead/product owner acceptance of the 10-sector resolution against the
  original 11-sector request.
- Acceptance of the SBIN/SIEMENS no-con-trigger exceptions and the limited
  parser coverage / flagged INFY divergence.

No approval or sign-off is asserted here. Sprint 6 is outside the scope of
this audit and has not been started as part of it.
