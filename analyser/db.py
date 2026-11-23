"""SQLite storage: schema setup, writes, and named queries from the sql/ folder."""
from __future__ import annotations

import sqlite3
from pathlib import Path

import pandas as pd

SQL_DIR = Path(__file__).resolve().parent.parent / "sql"


def connect(db_path: Path) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.executescript((SQL_DIR / "schema.sql").read_text(encoding="utf-8"))
    return conn


def query(conn: sqlite3.Connection, name: str) -> pd.DataFrame:
    """Run sql/<name>.sql and return the result as a DataFrame."""
    sql = (SQL_DIR / f"{name}.sql").read_text(encoding="utf-8")
    return pd.read_sql_query(sql, conn)


def save_holdings(conn: sqlite3.Connection, holdings: pd.DataFrame) -> None:
    rows = [
        (str(r.ticker), str(r.name), float(r.shares), str(r.buy_date))
        for r in holdings.itertuples(index=False)
    ]
    with conn:
        conn.execute("DELETE FROM holdings")
        conn.executemany(
            "INSERT INTO holdings (ticker, name, shares, buy_date) VALUES (?, ?, ?, ?)", rows
        )


def save_prices(conn: sqlite3.Connection, prices: pd.DataFrame) -> int:
    """Upsert long-format prices (date, ticker, close, volume). Returns rows written."""
    rows = [
        (str(r.ticker), str(r.date), float(r.close), None if pd.isna(r.volume) else int(r.volume))
        for r in prices.itertuples(index=False)
    ]
    with conn:
        conn.executemany(
            "INSERT OR REPLACE INTO prices (ticker, date, close, volume) VALUES (?, ?, ?, ?)", rows
        )
    return len(rows)


def load_close_prices(conn: sqlite3.Connection) -> pd.DataFrame:
    """Wide table of closes: one column per ticker, indexed by date."""
    df = pd.read_sql_query("SELECT ticker, date, close FROM prices", conn, parse_dates=["date"])
    return df.pivot(index="date", columns="ticker", values="close").sort_index()
