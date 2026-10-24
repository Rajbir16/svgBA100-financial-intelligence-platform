"""Sprint 3 Peer Percentile Engine and Comparison Reporting."""

import os
import sqlite3
from typing import Any, Dict, List, Optional, Tuple, Union
import numpy as np
import pandas as pd
import openpyxl
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

METRICS_CONFIG = [
    {"name": "ROE", "col": "return_on_equity_pct", "invert": False},
    {"name": "ROCE", "col": "return_on_capital_employed_pct", "invert": False},
    {"name": "NPM", "col": "net_profit_margin_pct", "invert": False},
    {"name": "D/E", "col": "debt_to_equity", "invert": True},
    {"name": "FCF", "col": "free_cash_flow_cr", "invert": False},
    {"name": "PAT CAGR 5yr", "col": "pat_cagr_5yr", "invert": False},
    {"name": "Revenue CAGR 5yr", "col": "revenue_cagr_5yr", "invert": False},
    {"name": "EPS CAGR 5yr", "col": "eps_cagr_5yr", "invert": False},
    {"name": "Interest Coverage", "col": "interest_coverage", "invert": False},
    {"name": "Asset Turnover", "col": "asset_turnover", "invert": False},
]


def _get_latest_company_ratios(conn: sqlite3.Connection) -> pd.DataFrame:
    query = """
        WITH ranked_ratios AS (
            SELECT fr.*,
                   ROW_NUMBER() OVER (
                       PARTITION BY fr.company_id
                       ORDER BY 
                           CASE 
                               WHEN fr.company_id = 'SIEMENS' AND fr.year = 'Sep 2024' THEN 1
                               WHEN fr.company_id != 'SIEMENS' AND fr.year = 'Mar 2024' THEN 1
                               WHEN fr.year LIKE '2024%' THEN 2
                               WHEN fr.year LIKE '%2024%' AND fr.year != 'TTM' THEN 3
                               ELSE 4
                           END,
                           fr.id DESC
                   ) as rn
            FROM financial_ratios fr
            WHERE fr.sales_cr IS NOT NULL AND fr.year != 'TTM'
        )
        SELECT 
            c.id AS company_id,
            c.company_name,
            s.broad_sector,
            s.sub_sector,
            pg.peer_group_name,
            COALESCE(pg.is_benchmark, 0) AS is_benchmark,
            r.year,
            r.return_on_equity_pct,
            r.return_on_capital_employed_pct,
            r.net_profit_margin_pct,
            r.operating_profit_margin_pct,
            r.debt_to_equity,
            r.interest_coverage,
            r.icr_label,
            r.asset_turnover,
            r.free_cash_flow_cr,
            r.sales_cr,
            r.net_profit_cr,
            r.pat_cagr_5yr,
            r.revenue_cagr_5yr,
            r.revenue_cagr_3yr,
            r.eps_cagr_5yr,
            r.cfo_quality_5yr,
            r.composite_quality_score
        FROM companies c
        LEFT JOIN sectors s ON c.id = s.company_id
        LEFT JOIN peer_groups pg ON c.id = pg.company_id
        LEFT JOIN ranked_ratios r ON c.id = r.company_id AND r.rn = 1
    """
    return pd.read_sql_query(query, conn)


def calculate_percentiles_for_group(group_df: pd.DataFrame, metric_col: str, invert: bool = False) -> List[Tuple[str, Optional[float], float]]:
    """Calculate percentile rank (0 to 100) for each company in a group.
    
    If invert is True (e.g. for D/E), lower values get higher percentile ranks.
    Special rule for interest_coverage: None / Debt Free is treated as infinite coverage (top rank).
    """
    results = []
    n = len(group_df)
    if n == 0:
        return results

    records = []
    for _, row in group_df.iterrows():
        cid = row["company_id"]
        val = row.get(metric_col)
        records.append((cid, val))

    # For sorting, define sorting keys
    def sort_key(item: Tuple[str, Any]) -> float:
        val = item[1]
        if metric_col == "interest_coverage":
            if val is None or (isinstance(val, float) and np.isnan(val)):
                return float("inf")
            return float(val)
        if val is None or (isinstance(val, float) and np.isnan(val)):
            return float("-inf") if not invert else float("inf")
        return float(val)

    # Sort ascending for normal metrics, descending for inverted (or lowest value gets highest rank)
    if invert:
        # Lower value = higher rank. Sort descending so lowest value is at the end (highest rank)
        # Or sort ascending: lowest value is rank N (100%), highest value is rank 1 (lowest %)
        sorted_records = sorted(records, key=sort_key, reverse=True)
    else:
        sorted_records = sorted(records, key=sort_key, reverse=False)

    # Handle ties with average rank
    values_list = [sort_key(rec) for rec in sorted_records]
    for idx, (cid, val) in enumerate(sorted_records):
        current_k = values_list[idx]
        same_indices = [i for i, v in enumerate(values_list) if v == current_k]
        avg_rank = (min(same_indices) + max(same_indices) + 2) / 2.0  # 1-indexed avg rank
        pct_rank = round((avg_rank / n) * 100.0, 2)
        # Ensure within 0 to 100
        pct_rank = max(0.0, min(100.0, pct_rank))
        results.append((cid, val if pd.notna(val) else None, pct_rank))

    return results


def compute_peer_percentiles(db_path: str = "nifty100.db") -> pd.DataFrame:
    """Compute percentile ranks within each of 11 peer groups and store in SQLite."""
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys = ON;")
    
    # Ensure peer_percentiles table exists
    conn.execute("""
        CREATE TABLE IF NOT EXISTS peer_percentiles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company_id TEXT NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
            peer_group_name TEXT NOT NULL,
            metric TEXT NOT NULL,
            value REAL,
            percentile_rank REAL,
            year TEXT NOT NULL
        );
    """)
    conn.execute("DELETE FROM peer_percentiles;")
    
    df = _get_latest_company_ratios(conn)
    peer_df = df[df["peer_group_name"].notna() & (df["peer_group_name"] != "")].copy()
    
    all_rows = []
    for peer_group, group in peer_df.groupby("peer_group_name"):
        year_str = group["year"].dropna().iloc[0] if not group["year"].dropna().empty else "Mar 2024"
        for m_cfg in METRICS_CONFIG:
            m_name = m_cfg["name"]
            m_col = m_cfg["col"]
            invert = m_cfg["invert"]
            
            p_ranks = calculate_percentiles_for_group(group, m_col, invert=invert)
            for cid, val, pct in p_ranks:
                all_rows.append({
                    "company_id": cid,
                    "peer_group_name": peer_group,
                    "metric": m_name,
                    "value": float(val) if val is not None else None,
                    "percentile_rank": float(pct),
                    "year": year_str
                })

    result_df = pd.DataFrame(all_rows)
    for r in all_rows:
        conn.execute("""
            INSERT INTO peer_percentiles (company_id, peer_group_name, metric, value, percentile_rank, year)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (r["company_id"], r["peer_group_name"], r["metric"], r["value"], r["percentile_rank"], r["year"]))
    
    conn.commit()
    conn.close()
    return result_df


def get_company_peer_percentiles(company_id: str, db_path: str = "nifty100.db") -> Union[Dict[str, Any], str]:
    """Return peer percentiles for a company, or 'No peer group assigned'."""
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute("SELECT peer_group_name FROM peer_groups WHERE company_id = ?", (company_id,))
    row = cur.fetchone()
    if not row or not row[0]:
        conn.close()
        return "No peer group assigned"
    
    peer_group = row[0]
    cur.execute("""
        SELECT metric, value, percentile_rank, year
        FROM peer_percentiles
        WHERE company_id = ?
        ORDER BY id
    """, (company_id,))
    records = cur.fetchall()
    conn.close()
    
    if not records:
        return "No peer group assigned"

    return {
        "company_id": company_id,
        "peer_group_name": peer_group,
        "year": records[0][3],
        "metrics": {r[0]: {"value": r[1], "percentile_rank": r[2]} for r in records}
    }


def generate_peer_excel(db_path: str = "nifty100.db", output_path: str = "output/peer_comparison.xlsx") -> None:
    """Generate peer_comparison.xlsx with 11 sheets, 20 metric columns + percentiles, conditional formatting."""
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    conn = sqlite3.connect(db_path)
    df = _get_latest_company_ratios(conn)
    
    # Read computed percentiles
    pct_df = pd.read_sql_query("SELECT * FROM peer_percentiles", conn)
    conn.close()
    
    wb = openpyxl.Workbook()
    # Remove default sheet
    wb.remove(wb.active)
    
    peer_groups = sorted(df["peer_group_name"].dropna().unique())
    
    # Styles
    navy_fill = PatternFill(start_color="1B365D", end_color="1B365D", fill_type="solid")
    header_font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
    benchmark_fill = PatternFill(start_color="E8F0FE", end_color="E8F0FE", fill_type="solid")
    benchmark_font = Font(name="Calibri", size=10, bold=True, color="1B365D")
    median_fill = PatternFill(start_color="E9ECEF", end_color="E9ECEF", fill_type="solid")
    median_font = Font(name="Calibri", size=10, bold=True)
    
    green_fill = PatternFill(start_color="D4EDDA", end_color="D4EDDA", fill_type="solid")
    green_font = Font(name="Calibri", size=10, color="155724")
    yellow_fill = PatternFill(start_color="FFF3CD", end_color="FFF3CD", fill_type="solid")
    yellow_font = Font(name="Calibri", size=10, color="856404")
    red_fill = PatternFill(start_color="F8D7DA", end_color="F8D7DA", fill_type="solid")
    red_font = Font(name="Calibri", size=10, color="721C24")
    
    thin_border = Border(
        left=Side(style="thin", color="D3D3D3"),
        right=Side(style="thin", color="D3D3D3"),
        top=Side(style="thin", color="D3D3D3"),
        bottom=Side(style="thin", color="D3D3D3")
    )
    median_border = Border(
        left=Side(style="thin", color="A0A0A0"),
        right=Side(style="thin", color="A0A0A0"),
        top=Side(style="thin", color="A0A0A0"),
        bottom=Side(style="double", color="1B365D")
    )

    for pg in peer_groups:
        ws = wb.create_sheet(title=pg[:31])  # Excel sheet title limit is 31 chars
        ws.views.sheetView[0].showGridLines = True
        
        pg_cos = df[df["peer_group_name"] == pg].sort_values(by="is_benchmark", ascending=False)
        
        # Build headers (company_id, company_name, benchmark_flag, then 20 metric columns: 10 values + 10 percentiles)
        headers = ["Company ID", "Company Name", "Is Benchmark"]
        for m_cfg in METRICS_CONFIG:
            headers.append(f"{m_cfg['name']} (Value)")
            headers.append(f"{m_cfg['name']} (Pctl)")
            
        ws.append(headers)
        for col_idx in range(1, len(headers) + 1):
            cell = ws.cell(row=1, column=col_idx)
            cell.fill = navy_fill
            cell.font = header_font
            cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
            cell.border = thin_border
            
        ws.row_dimensions[1].height = 28
        
        # Populate company rows
        row_data_collector = []
        for r_idx, (_, row) in enumerate(pg_cos.iterrows(), start=2):
            cid = row["company_id"]
            cname = row["company_name"]
            is_bm = "YES" if row["is_benchmark"] == 1 else "NO"
            
            row_vals = [cid, cname, is_bm]
            co_pcts = pct_df[(pct_df["company_id"] == cid) & (pct_df["peer_group_name"] == pg)]
            co_pct_map = dict(zip(co_pcts["metric"], co_pcts["percentile_rank"]))
            
            numeric_vals_for_median = []
            for m_cfg in METRICS_CONFIG:
                m_name = m_cfg["name"]
                m_col = m_cfg["col"]
                val = row.get(m_col)
                pct = co_pct_map.get(m_name, 0.0)
                
                # Format value
                val_disp = round(val, 2) if (val is not None and pd.notna(val)) else "N/A"
                pct_disp = round(pct, 1)
                row_vals.extend([val_disp, pct_disp])
                numeric_vals_for_median.append(val if pd.notna(val) else np.nan)
            
            row_data_collector.append(numeric_vals_for_median)
            ws.append(row_vals)
            ws.row_dimensions[r_idx].height = 20
            
            # Styling cells
            for c_idx in range(1, len(row_vals) + 1):
                cell = ws.cell(row=r_idx, column=c_idx)
                cell.border = thin_border
                cell.alignment = Alignment(horizontal="center" if c_idx != 2 else "left", vertical="center")
                
                # Benchmark highlighting
                if is_bm == "YES":
                    cell.font = benchmark_font
                    if c_idx <= 3:
                        cell.fill = benchmark_fill
                        
                # Percentile conditional coloring
                # Percentile columns are: 5, 7, 9, 11, 13, 15, 17, 19, 21, 23
                if c_idx in range(5, len(row_vals) + 1, 2):
                    pct_val = row_vals[c_idx - 1]
                    if isinstance(pct_val, (int, float)):
                        if pct_val >= 75.0:
                            cell.fill = green_fill
                            cell.font = green_font
                        elif pct_val >= 25.0:
                            cell.fill = yellow_fill
                            cell.font = yellow_font
                        else:
                            cell.fill = red_fill
                            cell.font = red_font

        # Peer Median summary row
        median_row_idx = len(pg_cos) + 2
        median_row = ["PEER MEDIAN", f"{pg} Median", "-"]
        collector_arr = np.array(row_data_collector, dtype=float)
        
        col_cursor = 0
        for m_cfg in METRICS_CONFIG:
            col_vals = collector_arr[:, col_cursor]
            valid_vals = col_vals[~np.isnan(col_vals)]
            med_val = round(float(np.median(valid_vals)), 2) if len(valid_vals) > 0 else "N/A"
            median_row.extend([med_val, 50.0])
            col_cursor += 1
            
        ws.append(median_row)
        ws.row_dimensions[median_row_idx].height = 22
        for c_idx in range(1, len(median_row) + 1):
            cell = ws.cell(row=median_row_idx, column=c_idx)
            cell.fill = median_fill
            cell.font = median_font
            cell.border = median_border
            cell.alignment = Alignment(horizontal="center" if c_idx != 2 else "left", vertical="center")

        # Column widths auto-adjustment
        for col in ws.columns:
            max_len = max(len(str(cell.value or "")) for cell in col)
            col_letter = get_column_letter(col[0].column)
            ws.column_dimensions[col_letter].width = max(max_len + 3, 12)

    wb.save(output_path)


def generate_radar_charts(db_path: str = "nifty100.db", output_dir: str = "reports/radar_charts") -> int:
    """Generate 8-axis radar charts for all 92 companies comparing against peer/universe average."""
    os.makedirs(output_dir, exist_ok=True)
    conn = sqlite3.connect(db_path)
    df = _get_latest_company_ratios(conn)
    conn.close()

    # The 8 radar chart axes:
    # ROE, ROCE, NPM, D/E (inverted score), FCF score, PAT CAGR 5yr, Revenue CAGR 5yr, Composite Score
    axes_labels = ["ROE", "ROCE", "NPM", "D/E Score", "FCF Score", "PAT CAGR", "Rev CAGR", "Composite"]
    num_axes = len(axes_labels)
    angles = np.linspace(0, 2 * np.pi, num_axes, endpoint=False).tolist()
    angles += angles[:1]  # Complete polygon loop

    # Helper function to compute a 0-100 normalized score for each axis
    def get_normalized_scores(row: pd.Series) -> List[float]:
        # ROE: clamp 0 to 40 -> 0-100
        roe = row.get("return_on_equity_pct")
        s_roe = 0.0 if (roe is None or pd.isna(roe)) else min(max(float(roe), 0.0) / 40.0, 1.0) * 100.0
        
        # ROCE: clamp 0 to 40 -> 0-100
        roce = row.get("return_on_capital_employed_pct")
        s_roce = 0.0 if (roce is None or pd.isna(roce)) else min(max(float(roce), 0.0) / 40.0, 1.0) * 100.0
        
        # NPM: clamp 0 to 30 -> 0-100
        npm = row.get("net_profit_margin_pct")
        s_npm = 0.0 if (npm is None or pd.isna(npm)) else min(max(float(npm), 0.0) / 30.0, 1.0) * 100.0
        
        # D/E: lower is better. 0 is 100, 3+ is 0
        de = row.get("debt_to_equity")
        if str(row.get("broad_sector")).lower() == "financials":
            s_de = 85.0
        elif de is None or pd.isna(de):
            s_de = 50.0
        else:
            s_de = max(0.0, min(1.0, 1.0 - (float(de) / 3.0))) * 100.0
            
        # FCF score: positive FCF -> 50-100, negative -> 0-50
        fcf = row.get("free_cash_flow_cr")
        if fcf is None or pd.isna(fcf):
            s_fcf = 50.0
        elif float(fcf) >= 0:
            s_fcf = min(100.0, 50.0 + min(float(fcf) / 5000.0, 1.0) * 50.0)
        else:
            s_fcf = max(0.0, 50.0 + max(float(fcf) / 5000.0, -1.0) * 50.0)
            
        # PAT CAGR 5yr: clamp -10 to 30 -> 0-100
        pat_cagr = row.get("pat_cagr_5yr")
        s_pat = 50.0 if (pat_cagr is None or pd.isna(pat_cagr)) else min(max((float(pat_cagr) + 10.0) / 40.0, 0.0), 1.0) * 100.0
        
        # Revenue CAGR 5yr: clamp 0 to 25 -> 0-100
        rev_cagr = row.get("revenue_cagr_5yr")
        s_rev = 50.0 if (rev_cagr is None or pd.isna(rev_cagr)) else min(max(float(rev_cagr) / 25.0, 0.0), 1.0) * 100.0
        
        # Composite score: directly 0-100
        comp = row.get("composite_quality_score")
        s_comp = 50.0 if (comp is None or pd.isna(comp)) else float(comp)
        
        return [round(s, 1) for s in [s_roe, s_roce, s_npm, s_de, s_fcf, s_pat, s_rev, s_comp]]

    # Precalculate scores for all rows
    all_scores = [get_normalized_scores(r) for _, r in df.iterrows()]
    df_scores = pd.DataFrame(all_scores, columns=axes_labels)
    df_scores["company_id"] = df["company_id"].values
    df_scores["peer_group_name"] = df["peer_group_name"].values
    
    universe_avg = df_scores[axes_labels].mean().values.tolist()
    universe_avg += universe_avg[:1]

    # Precalculate peer group averages
    peer_averages = {}
    for pg, group in df_scores.groupby("peer_group_name"):
        if pg:
            avg_vals = group[axes_labels].mean().values.tolist()
            avg_vals += avg_vals[:1]
            peer_averages[pg] = avg_vals

    count_generated = 0
    for _, row in df.iterrows():
        cid = row["company_id"]
        cname = row["company_name"]
        pg = row["peer_group_name"]
        
        co_scores = get_normalized_scores(row)
        co_scores_loop = co_scores + co_scores[:1]
        
        fig, ax = plt.subplots(figsize=(6.5, 6.5), subplot_kw=dict(polar=True))
        ax.set_theta_offset(np.pi / 2)
        ax.set_theta_direction(-1)
        
        plt.xticks(angles[:-1], axes_labels, color="#1B365D", size=10, weight="bold")
        ax.set_rscale("linear")
        ax.set_ylim(0, 100)
        ax.set_rticks([25, 50, 75, 100])
        ax.set_yticklabels(["25", "50", "75", "100"], color="#6c757d", size=8)
        
        # Plot benchmark/peer average or universe average
        if pg and pg in peer_averages:
            peer_vals = peer_averages[pg]
            ax.plot(angles, peer_vals, color="#E65100", linewidth=2, linestyle="--", label=f"{pg} Peer Avg")
            ax.fill(angles, peer_vals, color="#FFE0B2", alpha=0.25)
        else:
            ax.plot(angles, universe_avg, color="#6c757d", linewidth=2, linestyle="--", label="Nifty 100 Universe Avg")
            ax.fill(angles, universe_avg, color="#e9ecef", alpha=0.25)

        # Plot company polygon
        ax.plot(angles, co_scores_loop, color="#0F4C81", linewidth=2.5, linestyle="solid", label=f"{cid} Performance")
        ax.fill(angles, co_scores_loop, color="#0F4C81", alpha=0.35)
        
        subtitle = f"Peer Group: {pg}" if (pg and pd.notna(pg)) else "No Peer Group Assigned (Universe Benchmark)"
        plt.title(f"{cid} — {cname}\n({subtitle})", size=11, color="#1B365D", weight="bold", pad=20)
        plt.legend(loc="upper right", bbox_to_anchor=(1.25, 1.1), frameon=True, fontsize=8)
        
        out_file = os.path.join(output_dir, f"{cid}.png")
        plt.tight_layout()
        plt.savefig(out_file, dpi=120, bbox_inches="tight")
        plt.close(fig)
        count_generated += 1

    return count_generated


if __name__ == "__main__":
    print("Computing peer percentiles...")
    p_df = compute_peer_percentiles()
    print(f"Computed {len(p_df)} percentile rows.")
    print("Generating peer comparison Excel...")
    generate_peer_excel()
    print("Generating radar charts...")
    num_charts = generate_radar_charts()
    print(f"Generated {num_charts} radar charts.")

