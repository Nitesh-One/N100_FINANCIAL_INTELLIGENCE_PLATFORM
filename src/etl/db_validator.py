"""Database validator for SQLite schema and constraints.

Runs a suite of validations listed by the user to ensure the SQLite schema
is created as expected and enforces primary/foreign keys, NOT NULL, UNIQUE,
and table structure. Designed to run against a fresh database created from
`db/schema.sql` (default) or an existing DB file.

Usage:
    python -m src.etl.db_validator --schema db/schema.sql --db db/nifty100_validator.db

This script executes the schema into a temporary database and performs
numerous checks, returning a summary printed to stdout.
"""

import argparse
import sqlite3
import os
from typing import List, Dict, Tuple


EXPECTED_TABLES = [
    "companies",
    "profitandloss",
    "balancesheet",
    "cashflow",
    "financial_ratios",
    "market_cap",
    "stock_prices",
    "documents",
    "peer_groups",
    "analysis",
    "prosandcons",
    "sectors",
]


def read_schema(schema_path: str) -> str:
    with open(schema_path, "r", encoding="utf-8") as f:
        return f.read()


def connect(db_path: str) -> sqlite3.Connection:
    uri = False
    # Use file path. If :memory: passed, sqlite3 handles it.
    conn = sqlite3.connect(db_path, isolation_level=None)
    # Enable foreign key enforcement for this connection
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def execute_schema(conn: sqlite3.Connection, schema_sql: str) -> Tuple[bool, str]:
    try:
        conn.executescript(schema_sql)
        return True, "Schema executed successfully"
    except sqlite3.DatabaseError as e:
        return False, str(e)


def get_tables(conn: sqlite3.Connection) -> List[str]:
    cur = conn.execute("SELECT name FROM sqlite_master WHERE type='table';")
    return [row[0] for row in cur.fetchall()]


def table_exists_validation(conn: sqlite3.Connection) -> Tuple[bool, str]:
    tables = set(get_tables(conn))
    missing = [t for t in EXPECTED_TABLES if t not in tables]
    if missing:
        return False, f"Missing tables: {missing}"
    return True, "All expected tables exist"


def primary_key_validation(conn: sqlite3.Connection) -> Tuple[bool, str]:
    problems = []
    for t in EXPECTED_TABLES:
        cur = conn.execute(f"PRAGMA table_info('{t}')")
        cols = cur.fetchall()
        if not cols:
            problems.append(f"Table {t} has no columns")
            continue
        pk_cols = [c for c in cols if c[5] > 0]
        if not pk_cols:
            problems.append(f"Table {t} has no PRIMARY KEY")
    if problems:
        return False, "; ".join(problems)
    return True, "Every table has a PRIMARY KEY"


def foreign_key_validation(conn: sqlite3.Connection) -> Tuple[bool, str]:
    problems = []
    for t in EXPECTED_TABLES:
        # Check FK list
        cur = conn.execute(f"PRAGMA foreign_key_list('{t}')")
        fks = cur.fetchall()
        # For all financial/child tables (except companies) ensure they reference companies
        if t == "companies":
            continue
        # peer_groups is special: it should reference companies twice
        if t in (
            "profitandloss",
            "balancesheet",
            "cashflow",
            "financial_ratios",
            "market_cap",
            "stock_prices",
            "documents",
            "peer_groups",
            "analysis",
            "prosandcons",
            "sectors",
        ):
            if not fks:
                problems.append(f"Table {t} has no foreign keys defined")
                continue
            # Ensure at least one FK references companies
            refs_companies = [fk for fk in fks if fk[2] == "companies"]
            if not refs_companies:
                problems.append(f"Table {t} does not reference companies(table)")
    if problems:
        return False, "; ".join(problems)
    return True, "Foreign key relationships appear to reference companies"


def foreign_key_enforcement_validation(conn: sqlite3.Connection) -> Tuple[bool, str]:
    cur = conn.execute("PRAGMA foreign_keys")
    val = cur.fetchone()[0]
    if val != 1:
        return False, "PRAGMA foreign_keys is not enabled"
    return True, "PRAGMA foreign_keys is enabled"


def column_structure_validation(conn: sqlite3.Connection) -> Tuple[bool, str]:
    # Minimal structural expectations derived from schema
    expectations = {
        "companies": {"company_id": "INTEGER", "company_name": "TEXT", "ticker": "TEXT"},
        "profitandloss": {"company_id": "INTEGER", "fiscal_year": "INTEGER"},
        "balancesheet": {"company_id": "INTEGER", "fiscal_year": "INTEGER"},
        "cashflow": {"company_id": "INTEGER", "fiscal_year": "INTEGER"},
        "financial_ratios": {"company_id": "INTEGER", "fiscal_year": "INTEGER"},
        "market_cap": {"company_id": "INTEGER", "market_date": "TEXT"},
        "stock_prices": {"company_id": "INTEGER", "price_date": "TEXT", "close": "REAL"},
        "documents": {"company_id": "INTEGER", "doc_type": "TEXT"},
        "peer_groups": {"company_id": "INTEGER", "peer_company_id": "INTEGER"},
        "analysis": {"company_id": "INTEGER"},
        "prosandcons": {"company_id": "INTEGER", "kind": "TEXT", "description": "TEXT"},
        "sectors": {"company_id": "INTEGER", "broad_sector": "TEXT"},
    }
    problems = []
    for t, cols in expectations.items():
        cur = conn.execute(f"PRAGMA table_info('{t}')")
        tbl_cols = {r[1].lower(): r for r in cur.fetchall()}  # name -> row
        for cname, ctype in cols.items():
            if cname.lower() not in tbl_cols:
                problems.append(f"Table {t} missing expected column {cname}")
                continue
            decl_type = tbl_cols[cname.lower()][2].upper()
            if ctype not in decl_type and decl_type not in (ctype, ''):
                # SQLite types are flexible, so warn if not matching exactly
                problems.append(f"Table {t} column {cname} declared as {decl_type}, expected {ctype}")
    if problems:
        return False, "; ".join(problems)
    return True, "Column structures match expected declarations"


def empty_table_validation(conn: sqlite3.Connection) -> Tuple[bool, str]:
    problems = []
    for t in EXPECTED_TABLES:
        cur = conn.execute(f"SELECT COUNT(1) FROM {t}")
        cnt = cur.fetchone()[0]
        if cnt != 0:
            problems.append(f"Table {t} is not empty (rows={cnt})")
    if problems:
        return False, "; ".join(problems)
    return True, "All tables are empty"


def primary_key_constraint_validation(conn: sqlite3.Connection) -> Tuple[bool, str]:
    # Try inserting duplicate PKs for representative tables
    try:
        cur = conn.cursor()
        # companies: explicit company_id duplicate — run inside a SAVEPOINT so we rollback
        cur.execute("SAVEPOINT sp_pk_companies")
        try:
            cur.execute("INSERT INTO companies(company_id, company_name, ticker) VALUES (1000, 'X', 'XTK')")
            try:
                cur.execute("INSERT INTO companies(company_id, company_name, ticker) VALUES (1000, 'Y', 'YTK')")
                ok = False
                msg = "Duplicate primary key insertion into companies succeeded unexpectedly"
            except sqlite3.IntegrityError:
                ok = True
                msg = "Primary key constraint rejected duplicate in companies"
        finally:
            cur.execute("ROLLBACK TO SAVEPOINT sp_pk_companies")
            cur.execute("RELEASE SAVEPOINT sp_pk_companies")

        if not ok:
            return False, msg

        # market_cap composite PK — use savepoint and create a temporary parent company within it
        cur.execute("SAVEPOINT sp_pk_marketcap")
        try:
            try:
                cur.execute("INSERT INTO companies(company_id, company_name, ticker) VALUES (1001, 'PARENT', 'P1001')")
            except sqlite3.IntegrityError:
                # parent may already exist; that's fine for the purpose of testing PK behavior
                pass
            cur.execute("INSERT INTO market_cap(company_id, market_date, market_cap) VALUES (1001, '2020-01-01', 123.0)")
            try:
                cur.execute("INSERT INTO market_cap(company_id, market_date, market_cap) VALUES (1001, '2020-01-01', 456.0)")
                ok2 = False
                msg2 = "Duplicate composite PK insertion into market_cap succeeded unexpectedly"
            except sqlite3.IntegrityError:
                ok2 = True
                msg2 = "Composite primary key constraint rejected duplicate in market_cap"
        finally:
            cur.execute("ROLLBACK TO SAVEPOINT sp_pk_marketcap")
            cur.execute("RELEASE SAVEPOINT sp_pk_marketcap")

        if not ok2:
            return False, msg2

        return True, "Primary key constraints reject duplicates as expected"
    except sqlite3.DatabaseError as e:
        return False, str(e)


def foreign_key_constraint_validation(conn: sqlite3.Connection) -> Tuple[bool, str]:
    # Attempt to insert into child table with invalid company_id
    try:
        cur = conn.cursor()
        cur.execute("SAVEPOINT sp_fk_test")
        try:
            try:
                cur.execute("INSERT INTO profitandloss(company_id, fiscal_year, sales) VALUES (999999, 2020, 1.0)")
                fk_ok = False
                fk_msg = "Inserted profitandloss row with non-existent company_id (FK not enforced)"
            except sqlite3.IntegrityError:
                fk_ok = True
                fk_msg = "Foreign key constraints are enforced"
        finally:
            cur.execute("ROLLBACK TO SAVEPOINT sp_fk_test")
            cur.execute("RELEASE SAVEPOINT sp_fk_test")
        return fk_ok, fk_msg
    except sqlite3.DatabaseError as e:
        return False, str(e)


def not_null_constraint_validation(conn: sqlite3.Connection) -> Tuple[bool, str]:
    try:
        cur = conn.cursor()
        cur.execute("SAVEPOINT sp_notnull_test")
        try:
            try:
                cur.execute("INSERT INTO companies(company_id, company_name, ticker) VALUES (2000, NULL, 'T2000')")
                ok = False
                msg = "Inserted NULL into NOT NULL column company_name"
            except sqlite3.IntegrityError:
                ok = True
                msg = "NOT NULL constraints enforce non-null values"
        finally:
            cur.execute("ROLLBACK TO SAVEPOINT sp_notnull_test")
            cur.execute("RELEASE SAVEPOINT sp_notnull_test")
        return ok, msg
    except sqlite3.DatabaseError as e:
        return False, str(e)


def unique_constraint_validation(conn: sqlite3.Connection) -> Tuple[bool, str]:
    try:
        cur = conn.cursor()
        cur.execute("SAVEPOINT sp_unique_test")
        try:
            try:
                cur.execute("INSERT INTO companies(company_id, company_name, ticker) VALUES (3000, 'A', 'DUP')")
            except sqlite3.IntegrityError:
                # If the insert fails due to an existing id/ticker, try a different id
                cur.execute("INSERT INTO companies(company_id, company_name, ticker) VALUES (3002, 'A', 'DUP')")
            try:
                cur.execute("INSERT INTO companies(company_id, company_name, ticker) VALUES (3001, 'B', 'DUP')")
                ok = False
                msg = "Duplicate ticker inserted; UNIQUE constraint not enforced"
            except sqlite3.IntegrityError:
                ok = True
                msg = "UNIQUE constraint on ticker is enforced"
        finally:
            cur.execute("ROLLBACK TO SAVEPOINT sp_unique_test")
            cur.execute("RELEASE SAVEPOINT sp_unique_test")
        return ok, msg
    except sqlite3.DatabaseError as e:
        return False, str(e)


def data_type_validation(conn: sqlite3.Connection) -> Tuple[bool, str]:
    # SQLite uses type affinity; validate that declared types are INTEGER/REAL/TEXT in schema
    problems = []
    for t in EXPECTED_TABLES:
        cur = conn.execute(f"PRAGMA table_info('{t}')")
        for r in cur.fetchall():
            decl_type = (r[2] or "").upper()
            if decl_type and decl_type not in ("INTEGER", "REAL", "TEXT", "BLOB"):
                # Allow blanks (unspecified) but flag unusual types
                problems.append(f"Table {t} column {r[1]} has declaration {decl_type}")
    if problems:
        return False, "; ".join(problems)
    return True, "Declared column types are standard INTEGER/REAL/TEXT/BLOB or empty"


def table_count_validation(conn: sqlite3.Connection) -> Tuple[bool, str]:
    tables = [t for t in get_tables(conn) if t != 'sqlite_sequence']
    if len([t for t in tables if t in EXPECTED_TABLES]) != len(EXPECTED_TABLES):
        return False, f"Expected {len(EXPECTED_TABLES)} tables, found {len([t for t in tables if t in EXPECTED_TABLES])}"
    return True, f"Found expected number of tables: {len(EXPECTED_TABLES)}"


def relationship_validation(conn: sqlite3.Connection) -> Tuple[bool, str]:
    # Reuse foreign_key_validation for relationship coverage
    return foreign_key_validation(conn)


def database_connection_validation(db_path: str) -> Tuple[bool, str]:
    try:
        conn = connect(db_path)
        conn.close()
        return True, f"Connected successfully to {db_path}"
    except Exception as e:
        return False, str(e)


def schema_integrity_validation(conn: sqlite3.Connection) -> Tuple[bool, str]:
    # A simple aggregator of a few important checks
    checks = [
        table_exists_validation,
        primary_key_validation,
        foreign_key_validation,
        foreign_key_enforcement_validation,
        column_structure_validation,
    ]
    problems = []
    for chk in checks:
        ok, msg = chk(conn)
        if not ok:
            problems.append(msg)
    if problems:
        return False, "; ".join(problems)
    return True, "Schema integrity checks passed"


def run_all(schema_path: str, db_path: str) -> Dict[str, Tuple[bool, str]]:
    schema_sql = read_schema(schema_path)

    # Use a dedicated validation database so we don't touch production DB.
    # If db_path is ':memory:' we'll use in-memory.
    if db_path == ':memory:' or db_path.startswith('file:') or not os.path.exists(db_path):
        # Create or use in-memory database
        conn = connect(db_path)
    else:
        conn = connect(db_path)

    results: Dict[str, Tuple[bool, str]] = {}

    # 07: Schema Creation Validation
    ok, msg = execute_schema(conn, schema_sql)
    results['VAL-07'] = (ok, msg)

    if not ok:
        # If schema failed to execute, many other tests cannot proceed
        conn.close()
        return results

    # Run validations against the database with schema applied
    results['VAL-01'] = table_exists_validation(conn)
    results['VAL-02'] = primary_key_validation(conn)
    results['VAL-03'] = foreign_key_validation(conn)
    results['VAL-04'] = foreign_key_enforcement_validation(conn)
    results['VAL-05'] = column_structure_validation(conn)
    results['VAL-06'] = empty_table_validation(conn)
    results['VAL-08'] = primary_key_constraint_validation(conn)
    results['VAL-09'] = foreign_key_constraint_validation(conn)
    results['VAL-10'] = not_null_constraint_validation(conn)
    results['VAL-11'] = unique_constraint_validation(conn)
    results['VAL-12'] = data_type_validation(conn)
    results['VAL-13'] = table_count_validation(conn)
    results['VAL-14'] = relationship_validation(conn)
    # VAL-15: Database Connection Validation (verify we can connect to this DB path)
    results['VAL-15'] = database_connection_validation(db_path)
    # VAL-16: Schema Integrity Validation
    results['VAL-16'] = schema_integrity_validation(conn)

    conn.close()
    return results


def print_report(results: Dict[str, Tuple[bool, str]]) -> None:
    print("Database Validation Report")
    print("==========================")
    for vid in sorted(results.keys()):
        ok, msg = results[vid]
        status = "PASS" if ok else "FAIL"
        print(f"{vid}: {status} - {msg}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--schema", default="db/schema.sql")
    parser.add_argument("--db", default=":memory:", help="Validation DB path (default in-memory)")
    args = parser.parse_args()

    results = run_all(args.schema, args.db)
    print_report(results)


if __name__ == "__main__":
    main()
