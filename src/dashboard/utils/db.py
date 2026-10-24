"""Shared database access utilities for Streamlit dashboard.

Implements cached data retrieval for all 92 Nifty 100 companies.
Ensures connections are properly closed after execution to prevent SQLite locks.
"""

import os
import sqlite3
from typing import Any, Dict, List, Optional
import pandas as pd
import streamlit as st

DB_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "nifty100.db"))
if not os.path.exists(DB_PATH):
    # Fallback to local cwd
    DB_PATH = "nifty100.db"


def _get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH, timeout=10.0)
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


@st.cache_data(ttl=600)
def get_companies() -> pd.DataFrame:
    """Fetch all 92 companies with metadata."""
    conn = _get_connection()
    try:
        query = """
            SELECT c.*, s.broad_sector, s.sub_sector, s.index_weight_pct, s.market_cap_category
            FROM companies c
            LEFT JOIN sectors s ON c.id = s.company_id
            ORDER BY c.id
        """
        df = pd.read_sql_query(query, conn)
        return df
    finally:
        conn.close()


@st.cache_data(ttl=600)
def get_ratios(ticker: Optional[str] = None, year: Optional[str] = None) -> pd.DataFrame:
    """Fetch financial ratios. If ticker is None, returns all companies for the given year."""
    conn = _get_connection()
    try:
        conditions = []
        params = []
        if ticker:
            conditions.append("company_id = ?")
            params.append(ticker.strip().upper())
        if year:
            conditions.append("year = ?")
            params.append(str(year).strip())

        where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        query = f"SELECT * FROM financial_ratios {where_clause} ORDER BY id"
        df = pd.read_sql_query(query, conn, params=params if params else None)
        return df
    finally:
        conn.close()


@st.cache_data(ttl=600)
def get_pl(ticker: str) -> pd.DataFrame:
    """Fetch Profit and Loss statement history for a given ticker."""
    conn = _get_connection()
    try:
        query = "SELECT * FROM profitandloss WHERE company_id = ? ORDER BY id"
        df = pd.read_sql_query(query, conn, params=[ticker.strip().upper()])
        return df
    finally:
        conn.close()


@st.cache_data(ttl=600)
def get_bs(ticker: str) -> pd.DataFrame:
    """Fetch Balance Sheet history for a given ticker."""
    conn = _get_connection()
    try:
        query = "SELECT * FROM balancesheet WHERE company_id = ? ORDER BY id"
        df = pd.read_sql_query(query, conn, params=[ticker.strip().upper()])
        return df
    finally:
        conn.close()


@st.cache_data(ttl=600)
def get_cf(ticker: str) -> pd.DataFrame:
    """Fetch Cash Flow statement history for a given ticker."""
    conn = _get_connection()
    try:
        query = "SELECT * FROM cashflow WHERE company_id = ? ORDER BY id"
        df = pd.read_sql_query(query, conn, params=[ticker.strip().upper()])
        return df
    finally:
        conn.close()


@st.cache_data(ttl=600)
def get_sectors() -> pd.DataFrame:
    """Fetch sector mapping and company counts."""
    conn = _get_connection()
    try:
        query = """
            SELECT s.*, c.company_name
            FROM sectors s
            JOIN companies c ON s.company_id = c.id
            ORDER BY s.broad_sector, s.sub_sector, c.id
        """
        df = pd.read_sql_query(query, conn)
        return df
    finally:
        conn.close()


@st.cache_data(ttl=600)
def get_peers(group_name: Optional[str] = None) -> pd.DataFrame:
    """Fetch peer groups. If group_name is None, returns all peer mappings."""
    conn = _get_connection()
    try:
        if group_name:
            query = """
                SELECT pg.*, c.company_name, s.broad_sector
                FROM peer_groups pg
                JOIN companies c ON pg.company_id = c.id
                LEFT JOIN sectors s ON pg.company_id = s.company_id
                WHERE pg.peer_group_name = ?
                ORDER BY pg.is_benchmark DESC, c.id
            """
            df = pd.read_sql_query(query, conn, params=[group_name.strip()])
        else:
            query = """
                SELECT pg.*, c.company_name, s.broad_sector
                FROM peer_groups pg
                JOIN companies c ON pg.company_id = c.id
                LEFT JOIN sectors s ON pg.company_id = s.company_id
                ORDER BY pg.peer_group_name, pg.is_benchmark DESC, c.id
            """
            df = pd.read_sql_query(query, conn)
        return df
    finally:
        conn.close()


@st.cache_data(ttl=600)
def get_valuation(ticker: Optional[str] = None) -> pd.DataFrame:
    """Fetch valuation metrics from market_cap and valuation module."""
    from src.analytics.valuation import compute_valuation_data
    df = compute_valuation_data(DB_PATH)
    if ticker:
        return df[df["company_id"].str.upper() == ticker.strip().upper()]
    return df


@st.cache_data(ttl=600)
def get_prosandcons(ticker: str) -> pd.DataFrame:
    """Fetch pros and cons for a given ticker."""
    conn = _get_connection()
    try:
        query = "SELECT * FROM prosandcons WHERE company_id = ?"
        df = pd.read_sql_query(query, conn, params=[ticker.strip().upper()])
        return df
    finally:
        conn.close()


@st.cache_data(ttl=600)
def get_documents(ticker: str) -> pd.DataFrame:
    """Fetch annual report documents for a given ticker."""
    conn = _get_connection()
    try:
        query = "SELECT * FROM documents WHERE company_id = ? ORDER BY year DESC"
        df = pd.read_sql_query(query, conn, params=[ticker.strip().upper()])
        return df
    finally:
        conn.close()


@st.cache_data(ttl=600)
def get_market_cap_history(ticker: str) -> pd.DataFrame:
    """Fetch market cap and valuation multiple history for a given ticker."""
    conn = _get_connection()
    try:
        query = "SELECT * FROM market_cap WHERE company_id = ? ORDER BY year ASC"
        df = pd.read_sql_query(query, conn, params=[ticker.strip().upper()])
        return df
    finally:
        conn.close()

