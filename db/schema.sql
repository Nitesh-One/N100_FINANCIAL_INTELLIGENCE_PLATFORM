-- Enable foreign key enforcement for SQLite connections created by sqlite3/sqlalchemy
PRAGMA foreign_keys = ON;

-- Companies: master table for listed companies. `company_id` is the primary key.
-- `ticker` is unique so each listed instrument maps to a single company record.
CREATE TABLE IF NOT EXISTS companies (
    company_id INTEGER PRIMARY KEY,
    company_name TEXT NOT NULL,
    ticker TEXT NOT NULL UNIQUE,
    sector TEXT,
    industry TEXT,
    exchange TEXT
);

CREATE TABLE IF NOT EXISTS sectors (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id INTEGER NOT NULL,
    broad_sector TEXT,
    sub_sector TEXT,
    index_weight_pct REAL,
    market_cap_category TEXT,
    FOREIGN KEY(company_id) REFERENCES companies(company_id) ON DELETE CASCADE ON UPDATE NO ACTION
);

-- Profit and Loss (income statement) records.
-- FK: `company_id` -> companies(company_id). Uses ON DELETE CASCADE so related
-- financial records are removed when a company is removed.
CREATE TABLE IF NOT EXISTS profitandloss (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id INTEGER NOT NULL,
    fiscal_year INTEGER NOT NULL,
    fiscal_period TEXT,
    sales REAL NOT NULL DEFAULT 0,
    operating_profit REAL,
    net_profit REAL,
    FOREIGN KEY(company_id) REFERENCES companies(company_id) ON DELETE CASCADE ON UPDATE NO ACTION
);

-- Balance Sheet records.
-- FK: `company_id` -> companies(company_id)
CREATE TABLE IF NOT EXISTS balancesheet (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id INTEGER NOT NULL,
    fiscal_year INTEGER NOT NULL,
    fiscal_period TEXT,
    total_assets REAL,
    total_liabilities REAL,
    total_equity REAL,
    FOREIGN KEY(company_id) REFERENCES companies(company_id) ON DELETE CASCADE ON UPDATE NO ACTION
);

-- Cash Flow statements.
-- FK: `company_id` -> companies(company_id)
CREATE TABLE IF NOT EXISTS cashflow (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id INTEGER NOT NULL,
    fiscal_year INTEGER NOT NULL,
    fiscal_period TEXT,
    operating_cashflow REAL,
    investing_cashflow REAL,
    financing_cashflow REAL,
    FOREIGN KEY(company_id) REFERENCES companies(company_id) ON DELETE CASCADE ON UPDATE NO ACTION
);

-- Financial ratios (derived metrics) per company per period.
-- FK: `company_id` -> companies(company_id)
CREATE TABLE IF NOT EXISTS financial_ratios (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id INTEGER NOT NULL,
    fiscal_year INTEGER NOT NULL,
    pe_ratio REAL,
    roe REAL,
    current_ratio REAL,
    debt_equity REAL,
    FOREIGN KEY(company_id) REFERENCES companies(company_id) ON DELETE CASCADE ON UPDATE NO ACTION
);

-- Market capitalisation time series. Composite PK (company_id, market_date)
-- FK: `company_id` -> companies(company_id)
CREATE TABLE IF NOT EXISTS market_cap (
    company_id INTEGER NOT NULL,
    market_date TEXT NOT NULL,
    market_cap REAL NOT NULL,
    PRIMARY KEY (company_id, market_date),
    FOREIGN KEY(company_id) REFERENCES companies(company_id) ON DELETE CASCADE ON UPDATE NO ACTION
);

-- Stock prices time series. Composite PK (company_id, price_date).
-- FK: `company_id` -> companies(company_id)
CREATE TABLE IF NOT EXISTS stock_prices (
    company_id INTEGER NOT NULL,
    price_date TEXT NOT NULL,
    open REAL,
    high REAL,
    low REAL,
    close REAL NOT NULL,
    volume INTEGER,
    PRIMARY KEY (company_id, price_date),
    FOREIGN KEY(company_id) REFERENCES companies(company_id) ON DELETE CASCADE ON UPDATE NO ACTION
);

-- Documents (reports, filings) associated with a company.
-- FK: `company_id` -> companies(company_id)
CREATE TABLE IF NOT EXISTS documents (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id INTEGER NOT NULL,
    doc_type TEXT NOT NULL,
    title TEXT,
    url TEXT,
    published_date TEXT,
    language TEXT,
    FOREIGN KEY(company_id) REFERENCES companies(company_id) ON DELETE CASCADE ON UPDATE NO ACTION
);

-- Peer groups (self-referential mapping between companies).
-- FK: `company_id` -> companies(company_id)
-- FK: `peer_company_id` -> companies(company_id)
CREATE TABLE IF NOT EXISTS peer_groups (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id INTEGER NOT NULL,
    peer_company_id INTEGER NOT NULL,
    relation_type TEXT,
    UNIQUE(company_id, peer_company_id),
    FOREIGN KEY(company_id) REFERENCES companies(company_id) ON DELETE CASCADE ON UPDATE NO ACTION,
    FOREIGN KEY(peer_company_id) REFERENCES companies(company_id) ON DELETE CASCADE ON UPDATE NO ACTION
);

-- Analyst analysis / ratings for a company.
-- FK: `company_id` -> companies(company_id)
CREATE TABLE IF NOT EXISTS analysis (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id INTEGER NOT NULL,
    analyst TEXT,
    rating TEXT,
    target_price REAL,
    note TEXT,
    analysis_date TEXT,
    FOREIGN KEY(company_id) REFERENCES companies(company_id) ON DELETE CASCADE ON UPDATE NO ACTION
);

-- Qualitative pros and cons for a company.
-- FK: `company_id` -> companies(company_id)
CREATE TABLE IF NOT EXISTS prosandcons (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id INTEGER NOT NULL,
    kind TEXT NOT NULL CHECK(kind IN ('pro','con')),
    description TEXT NOT NULL,
    source TEXT,
    created_at TEXT,
    FOREIGN KEY(company_id) REFERENCES companies(company_id) ON DELETE CASCADE ON UPDATE NO ACTION
);

-- Re-assert foreign key enforcement (safe to run multiple times).
PRAGMA foreign_keys = ON;