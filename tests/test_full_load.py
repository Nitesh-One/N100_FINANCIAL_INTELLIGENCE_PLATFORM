import sqlite3
from pathlib import Path

import pandas as pd

from src.etl.loader import load_full_dataset


def test_full_dataset_load_creates_audit_and_expected_counts(tmp_path):
    schema_path = Path(__file__).resolve().parents[1] / "db" / "schema.sql"
    db_path = tmp_path / "nifty100.db"
    audit_path = tmp_path / "load_audit.csv"

    audit_df, conn = load_full_dataset(
        schema_path=str(schema_path),
        db_path=str(db_path),
        audit_path=str(audit_path),
    )

    assert len(audit_df) == 12
    assert audit_path.exists()
    assert audit_df.loc[audit_df["file_name"] == "companies.xlsx", "loaded_rows"].iloc[0] == 92
    assert audit_df.loc[audit_df["file_name"] == "profitandloss.xlsx", "loaded_rows"].iloc[0] >= 1200
    assert audit_df.loc[audit_df["file_name"] == "balancesheet.xlsx", "loaded_rows"].iloc[0] >= 1300
    assert audit_df.loc[audit_df["file_name"] == "cashflow.xlsx", "loaded_rows"].iloc[0] >= 1100
    assert audit_df.loc[audit_df["file_name"] == "stock_prices.xlsx", "loaded_rows"].iloc[0] >= 5500
    assert audit_df["fk_check"].eq(0).all()

    cur = conn.cursor()
    assert cur.execute("SELECT COUNT(1) FROM companies").fetchone()[0] == 92
    assert cur.execute("SELECT COUNT(1) FROM profitandloss").fetchone()[0] >= 1200
    assert cur.execute("SELECT COUNT(1) FROM balancesheet").fetchone()[0] >= 1300
    assert cur.execute("SELECT COUNT(1) FROM cashflow").fetchone()[0] >= 1100
    assert cur.execute("SELECT COUNT(1) FROM stock_prices").fetchone()[0] >= 5500

    conn.close()


def test_ttm_years_are_not_loaded_as_zero(tmp_path):
    schema_path = Path(__file__).resolve().parents[1] / "db" / "schema.sql"
    db_path = tmp_path / "nifty100.db"
    audit_path = tmp_path / "load_audit.csv"

    _, conn = load_full_dataset(
        schema_path=str(schema_path),
        db_path=str(db_path),
        audit_path=str(audit_path),
    )

    cur = conn.cursor()
    assert cur.execute("SELECT COUNT(1) FROM profitandloss WHERE fiscal_year = 0").fetchone()[0] == 0
    assert cur.execute("SELECT COUNT(1) FROM balancesheet WHERE fiscal_year = 0").fetchone()[0] == 0
    assert cur.execute("SELECT COUNT(1) FROM cashflow WHERE fiscal_year = 0").fetchone()[0] == 0

    conn.close()
