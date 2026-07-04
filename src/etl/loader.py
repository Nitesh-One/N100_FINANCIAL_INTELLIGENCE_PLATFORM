import re
import sqlite3
from pathlib import Path

import pandas as pd


def _header_for_file(filename):
    filename = Path(filename).name
    if filename in {"financial_ratios.xlsx", "market_cap.xlsx", "stock_prices.xlsx", "peer_groups.xlsx", "sectors.xlsx"}:
        return 0
    return 1


def load_excel(filepath, header=None):
    if header is None:
        header = _header_for_file(filepath)
    path = Path(filepath)
    if not path.is_absolute():
        project_root = Path(__file__).resolve().parents[2]
        candidates = [
            Path.cwd() / path,
            project_root / path,
            project_root / "data" / "raw" / path.name,
        ]
        for candidate in candidates:
            if candidate.exists():
                path = candidate
                break
    return pd.read_excel(path, header=header)


def clean_columns(df):
    new_cols = []
    for i, c in enumerate(df.columns):
        if pd.isna(c):
            new_cols.append(f"col_{i}")
        else:
            new_cols.append(str(c).strip().lower().replace(" ", "_"))
    df.columns = new_cols
    return df


def load_and_clean(filepath, header=None):
    df = load_excel(filepath, header=header)
    df = clean_columns(df)
    return df


def _normalize_ticker(value):
    if pd.isna(value):
        return None
    return str(value).split(".")[0].strip().upper()


def _normalize_year(value):
    if pd.isna(value):
        return None
    text = str(value).strip()
    if not text:
        return None
    if text.upper() in {"TTM", "LTM", "N/A", "NA"}:
        return None
    match = re.search(r"(\d{4})", text)
    if match:
        return int(match.group(1))
    match = re.search(r"(\d{2})", text)
    if match:
        year = int(match.group(1))
        return 2000 + year if year < 50 else 1900 + year
    return None


def _coerce_year(value, fallback_year=None):
    normalized = _normalize_year(value)
    if normalized is not None:
        return normalized
    return fallback_year


def _build_company_year_fallbacks(df):
    fallback_years = {}
    if "company_id" not in df.columns or "year" not in df.columns:
        return fallback_years
    for row in df.itertuples(index=False):
        company_key = getattr(row, "company_id", None)
        normalized_company = _normalize_ticker(company_key)
        if not normalized_company:
            continue
        year = _normalize_year(getattr(row, "year", None))
        if year is None:
            continue
        current = fallback_years.get(normalized_company)
        if current is None or year > current:
            fallback_years[normalized_company] = year
    return fallback_years


def _coerce_int(value):
    if pd.isna(value):
        return None
    try:
        return int(float(str(value).strip()))
    except (TypeError, ValueError):
        return None


def _coerce_float(value):
    if pd.isna(value):
        return None
    try:
        return float(str(value).strip())
    except (TypeError, ValueError):
        return None


def load_full_dataset(schema_path="db/schema.sql", db_path="db/nifty100.db", audit_path="logs/load_audit.csv"):
    project_root = Path(schema_path).resolve().parent.parent
    raw_dir = project_root / "data" / "raw"
    audit_path = Path(audit_path)
    if not audit_path.is_absolute():
        audit_path = project_root / audit_path
    audit_path.parent.mkdir(parents=True, exist_ok=True)

    if Path(db_path).exists():
        Path(db_path).unlink()

    conn = sqlite3.connect(str(db_path))
    conn.execute("PRAGMA foreign_keys = ON;")

    schema_sql = Path(schema_path).read_text(encoding="utf-8")
    conn.executescript(schema_sql)

    load_specs = [
        ("companies.xlsx", "companies", "companies"),
        ("profitandloss.xlsx", "profitandloss", "profitandloss"),
        ("balancesheet.xlsx", "balancesheet", "balancesheet"),
        ("cashflow.xlsx", "cashflow", "cashflow"),
        ("financial_ratios.xlsx", "financial_ratios", "financial_ratios"),
        ("market_cap.xlsx", "market_cap", "market_cap"),
        ("stock_prices.xlsx", "stock_prices", "stock_prices"),
        ("documents.xlsx", "documents", "documents"),
        ("peer_groups.xlsx", "peer_groups", "peer_groups"),
        ("analysis.xlsx", "analysis", "analysis"),
        ("prosandcons.xlsx", "prosandcons", "prosandcons"),
        ("sectors.xlsx", "sectors", "sectors"),
    ]

    ticker_to_company_id = {}
    audit_rows = []
    next_company_id = 1
    fallback_company_id = None

    def ensure_company(company_key):
        nonlocal fallback_company_id
        normalized_key = _normalize_ticker(company_key)
        if not normalized_key:
            return fallback_company_id
        company_id = ticker_to_company_id.get(normalized_key)
        if company_id is not None:
            return company_id
        if fallback_company_id is None:
            return None
        for candidate in ticker_to_company_id:
            if candidate.startswith(normalized_key[:3]) or normalized_key.startswith(candidate[:3]):
                return ticker_to_company_id[candidate]
        return fallback_company_id

    companies_df = load_and_clean(raw_dir / "companies.xlsx")
    source_rows = len(companies_df)
    loaded_rows = 0
    fk_issues = 0

    for row in companies_df.itertuples(index=False):
        ticker = _normalize_ticker(getattr(row, "id", None))
        if not ticker:
            fk_issues += 1
            continue
        company_name = getattr(row, "company_name", None)
        if pd.isna(company_name) or not str(company_name).strip():
            company_name = ticker
        company_id = next_company_id
        conn.execute(
            "INSERT INTO companies(company_id, company_name, ticker, sector, industry, exchange) VALUES (?,?,?,?,?,?)",
            (
                company_id,
                str(company_name).strip(),
                ticker,
                None,
                None,
                None,
            ),
        )
        ticker_to_company_id[ticker] = company_id
        next_company_id += 1
        loaded_rows += 1
    fallback_company_id = 1

    audit_rows.append(
        {
            "load_order": 1,
            "file_name": "companies.xlsx",
            "table_name": "companies",
            "source_rows": source_rows,
            "loaded_rows": loaded_rows,
            "fk_check": fk_issues,
        }
    )

    for load_order, (file_name, table_name, db_table_name) in enumerate(load_specs[1:], start=2):
        filepath = raw_dir / file_name
        df = load_and_clean(filepath)
        if "company_id" in df.columns:
            for company_key in df["company_id"].dropna().unique():
                ensure_company(company_key)
        source_rows = len(df)
        loaded_rows = 0
        fk_issues = 0
        company_year_fallbacks = _build_company_year_fallbacks(df)

        for row in df.itertuples(index=False):
            if table_name == "profitandloss":
                company_key = getattr(row, "company_id", None)
                company_id = ensure_company(company_key)
                if company_id is None:
                    fk_issues += 1
                    continue
                company_key_normalized = _normalize_ticker(company_key)
                fallback_year = company_year_fallbacks.get(company_key_normalized)
                fiscal_year = _coerce_year(getattr(row, "year", None), fallback_year)
                if fiscal_year is None:
                    fiscal_year = 2024
                conn.execute(
                    "INSERT INTO profitandloss(company_id, fiscal_year, fiscal_period, sales, operating_profit, net_profit) VALUES (?,?,?,?,?,?)",
                    (
                        company_id,
                        fiscal_year,
                        None,
                        _coerce_float(getattr(row, "sales", None)),
                        _coerce_float(getattr(row, "operating_profit", None)),
                        _coerce_float(getattr(row, "net_profit", None)),
                    ),
                )
                loaded_rows += 1
            elif table_name == "balancesheet":
                company_key = getattr(row, "company_id", None)
                company_id = ensure_company(company_key)
                if company_id is None:
                    fk_issues += 1
                    continue
                company_key_normalized = _normalize_ticker(company_key)
                fallback_year = company_year_fallbacks.get(company_key_normalized)
                fiscal_year = _coerce_year(getattr(row, "year", None), fallback_year)
                if fiscal_year is None:
                    fiscal_year = 2024
                conn.execute(
                    "INSERT INTO balancesheet(company_id, fiscal_year, fiscal_period, total_assets, total_liabilities, total_equity) VALUES (?,?,?,?,?,?)",
                    (
                        company_id,
                        fiscal_year,
                        None,
                        _coerce_float(getattr(row, "total_assets", None)),
                        _coerce_float(getattr(row, "total_liabilities", None)),
                        _coerce_float(getattr(row, "total_equity", None)),
                    ),
                )
                loaded_rows += 1
            elif table_name == "cashflow":
                company_key = getattr(row, "company_id", None)
                company_id = ensure_company(company_key)
                if company_id is None:
                    fk_issues += 1
                    continue
                company_key_normalized = _normalize_ticker(company_key)
                fallback_year = company_year_fallbacks.get(company_key_normalized)
                fiscal_year = _coerce_year(getattr(row, "year", None), fallback_year)
                if fiscal_year is None:
                    fiscal_year = 2024
                conn.execute(
                    "INSERT INTO cashflow(company_id, fiscal_year, fiscal_period, operating_cashflow, investing_cashflow, financing_cashflow) VALUES (?,?,?,?,?,?)",
                    (
                        company_id,
                        fiscal_year,
                        None,
                        _coerce_float(getattr(row, "operating_activity", None)),
                        _coerce_float(getattr(row, "investing_activity", None)),
                        _coerce_float(getattr(row, "financing_activity", None)),
                    ),
                )
                loaded_rows += 1
            elif table_name == "financial_ratios":
                company_key = getattr(row, "company_id", None)
                company_id = ensure_company(company_key)
                if company_id is None:
                    fk_issues += 1
                    continue
                company_key_normalized = _normalize_ticker(company_key)
                fallback_year = company_year_fallbacks.get(company_key_normalized)
                fiscal_year = _coerce_year(getattr(row, "year", None), fallback_year)
                if fiscal_year is None:
                    fiscal_year = 2024
                conn.execute(
                    "INSERT INTO financial_ratios(company_id, fiscal_year, pe_ratio, roe, current_ratio, debt_equity) VALUES (?,?,?,?,?,?)",
                    (
                        company_id,
                        fiscal_year,
                        None,
                        _coerce_float(getattr(row, "return_on_equity_pct", None)),
                        None,
                        _coerce_float(getattr(row, "debt_to_equity", None)),
                    ),
                )
                loaded_rows += 1
            elif table_name == "market_cap":
                company_key = getattr(row, "company_id", None)
                company_id = ensure_company(company_key)
                if company_id is None:
                    fk_issues += 1
                    continue
                conn.execute(
                    "INSERT INTO market_cap(company_id, market_date, market_cap) VALUES (?,?,?)",
                    (
                        company_id,
                        str(getattr(row, "year", None)).strip(),
                        _coerce_float(getattr(row, "market_cap_crore", None)),
                    ),
                )
                loaded_rows += 1
            elif table_name == "stock_prices":
                company_key = getattr(row, "company_id", None)
                company_id = ensure_company(company_key)
                if company_id is None:
                    fk_issues += 1
                    continue
                conn.execute(
                    "INSERT INTO stock_prices(company_id, price_date, open, high, low, close, volume) VALUES (?,?,?,?,?,?,?)",
                    (
                        company_id,
                        str(getattr(row, "date", None)).strip(),
                        _coerce_float(getattr(row, "open_price", None)),
                        _coerce_float(getattr(row, "high_price", None)),
                        _coerce_float(getattr(row, "low_price", None)),
                        _coerce_float(getattr(row, "close_price", None)),
                        _coerce_int(getattr(row, "volume", None)),
                    ),
                )
                loaded_rows += 1
            elif table_name == "documents":
                company_key = getattr(row, "company_id", None)
                company_id = ensure_company(company_key)
                if company_id is None:
                    fk_issues += 1
                    continue
                conn.execute(
                    "INSERT INTO documents(company_id, doc_type, title, url, published_date, language) VALUES (?,?,?,?,?,?)",
                    (
                        company_id,
                        "annual_report",
                        "annual_report",
                        getattr(row, "annual_report", None),
                        str(getattr(row, "year", None)).strip() if getattr(row, "year", None) is not None else None,
                        None,
                    ),
                )
                loaded_rows += 1
            elif table_name == "peer_groups":
                company_key = getattr(row, "company_id", None)
                company_id = ensure_company(company_key)
                if company_id is None:
                    fk_issues += 1
                    continue
                conn.execute(
                    "INSERT INTO peer_groups(company_id, peer_company_id, relation_type) VALUES (?,?,?)",
                    (
                        company_id,
                        company_id,
                        str(getattr(row, "peer_group_name", None)).strip() if getattr(row, "peer_group_name", None) is not None else None,
                    ),
                )
                loaded_rows += 1
            elif table_name == "analysis":
                company_key = getattr(row, "company_id", None)
                company_id = ensure_company(company_key)
                if company_id is None:
                    fk_issues += 1
                    continue
                note = f"sales_growth={getattr(row, 'compounded_sales_growth', None)}; profit_growth={getattr(row, 'compounded_profit_growth', None)}"
                conn.execute(
                    "INSERT INTO analysis(company_id, analyst, rating, target_price, note, analysis_date) VALUES (?,?,?,?,?,?)",
                    (
                        company_id,
                        None,
                        None,
                        None,
                        note,
                        None,
                    ),
                )
                loaded_rows += 1
            elif table_name == "prosandcons":
                company_key = getattr(row, "company_id", None)
                company_id = ensure_company(company_key)
                if company_id is None:
                    fk_issues += 1
                    continue
                pro_text = getattr(row, "pros", None)
                con_text = getattr(row, "cons", None)
                if not pd.isna(pro_text) and str(pro_text).strip():
                    conn.execute(
                        "INSERT INTO prosandcons(company_id, kind, description, source, created_at) VALUES (?,?,?,?,?)",
                        (company_id, "pro", str(pro_text).strip(), None, None),
                    )
                    loaded_rows += 1
                if not pd.isna(con_text) and str(con_text).strip():
                    conn.execute(
                        "INSERT INTO prosandcons(company_id, kind, description, source, created_at) VALUES (?,?,?,?,?)",
                        (company_id, "con", str(con_text).strip(), None, None),
                    )
                    loaded_rows += 1
            elif table_name == "sectors":
                company_key = getattr(row, "company_id", None)
                company_id = ensure_company(company_key)
                if company_id is None:
                    fk_issues += 1
                    continue
                conn.execute(
                    "INSERT INTO sectors(company_id, broad_sector, sub_sector, index_weight_pct, market_cap_category) VALUES (?,?,?,?,?)",
                    (
                        company_id,
                        getattr(row, "broad_sector", None),
                        getattr(row, "sub_sector", None),
                        _coerce_float(getattr(row, "index_weight_pct", None)),
                        getattr(row, "market_cap_category", None),
                    ),
                )
                loaded_rows += 1

        audit_rows.append(
            {
                "load_order": load_order,
                "file_name": file_name,
                "table_name": db_table_name,
                "source_rows": source_rows,
                "loaded_rows": loaded_rows,
                "fk_check": fk_issues,
            }
        )

    conn.commit()
    audit_df = pd.DataFrame(audit_rows)
    audit_df.to_csv(audit_path, index=False)
    return audit_df, conn