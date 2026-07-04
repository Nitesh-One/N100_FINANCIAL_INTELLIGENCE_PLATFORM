import json
import sqlite3
import random
import pandas as pd
from pathlib import Path

DATABASE = "db/nifty100.db"

REPORT = []

def get_connection():
    """
    Create connection to SQLite database.
    """

    conn = sqlite3.connect(DATABASE)

    conn.execute(
        "PRAGMA foreign_keys = ON;"
    )

    return conn

def get_random_companies(limit=5):

    conn = get_connection()

    cursor = conn.cursor()

    cursor.execute("""
        SELECT company_id,
               company_name,
               ticker
        FROM companies
        ORDER BY RANDOM()
        LIMIT ?
    """, (limit,))

    companies = cursor.fetchall()

    conn.close()

    return companies

def print_random_companies():

    companies = get_random_companies()

    print("="*50)
    print("Random Companies")
    print("="*50)

    for company in companies:

        print(company)
        
def review_profit_loss(company_id):

    conn = get_connection()

    cursor = conn.cursor()

    cursor.execute("""
        SELECT fiscal_year,
               sales,
               net_profit
        FROM profitandloss
        WHERE company_id=?
        ORDER BY fiscal_year
    """, (company_id,))

    rows = cursor.fetchall()

    conn.close()

    return rows

def review_random_companies():

    companies = get_random_companies()

    print("="*70)

    print("MANUAL DATA REVIEW")

    print("="*70)

    for company in companies:

        company_id = company[0]

        print("\n")

        print(company)

        pnl = review_profit_loss(company_id)

        print("Years Found :", len(pnl))

        print(pnl)
        
def review_table(company_id, table_name):

    conn = get_connection()

    cursor = conn.cursor()

    cursor.execute(f"""
        SELECT *
        FROM {table_name}
        WHERE company_id=?
    """, (company_id,))

    rows = cursor.fetchall()

    conn.close()

    return rows

def get_year_coverage(company_id, table_name):

    conn = get_connection()

    cursor = conn.cursor()

    cursor.execute(f"""
        SELECT
            MIN(fiscal_year),
            MAX(fiscal_year),
            COUNT(*)
        FROM {table_name}
        WHERE company_id=?
    """, (company_id,))

    result = cursor.fetchone()

    conn.close()

    return result

FINANCIAL_TABLES = [

    "profitandloss",

    "balancesheet",

    "cashflow",

    "financial_ratios"

]

def companies_with_less_than_five_years(table):

    conn = get_connection()

    cursor = conn.cursor()

    cursor.execute(f"""

        SELECT

        company_id,

        COUNT(*) AS total_years

        FROM {table}

        GROUP BY company_id

        HAVING COUNT(*) < 5

    """)

    rows = cursor.fetchall()

    conn.close()

    return rows

EXPECTED_ROWS = {

    "companies":92,

    "profitandloss":1276,

    "balancesheet":1312,

    "cashflow":1187,

    "stock_prices":5520

}

def review_financial_data():
    """
    Review financial tables for 5 random companies
    and store the results in REPORT.
    """

    companies = get_random_companies()

    print("\n")
    print("=" * 80)
    print("FINANCIAL DATA REVIEW")
    print("=" * 80)

    for company in companies:

        company_id = company[0]
        company_name = company[1]
        ticker = company[2]

        print(f"\nCompany : {company_name} ({ticker})")

        for table in FINANCIAL_TABLES:

            rows = review_table(company_id, table)

            coverage = get_year_coverage(
                company_id,
                table
            )

            if coverage[0] is not None:

                start_year = coverage[0]
                end_year = coverage[1]
                total_years = coverage[2]

            else:

                start_year = None
                end_year = None
                total_years = 0

            print(f"{table:<20} Records : {len(rows)}")

            REPORT.append({
                "company_id": company_id,
                "company_name": company_name,
                "ticker": ticker,
                "table": table,
                "records": len(rows),
                "start_year": start_year,
                "end_year": end_year,
                "total_years": total_years,
                "status": "PASS" if len(rows) > 0 else "FAIL"
            })

def verify_row_counts():

    conn = get_connection()

    cursor = conn.cursor()

    print("="*50)

    print("ROW COUNT REVIEW")

    print("="*50)

    for table, expected in EXPECTED_ROWS.items():

        cursor.execute(
            f"SELECT COUNT(*) FROM {table}"
        )

        actual = cursor.fetchone()[0]

        if actual == expected:

            print(
                f"PASS : {table} ({actual})"
            )

        else:

            print(
                f"FAIL : {table} Expected {expected} Got {actual}"
            )

    conn.close()


def review_less_than_five_years():
    """Print companies with less than five distinct years in each financial table."""
    print("\n")
    print("=" * 60)
    print("LESS THAN FIVE YEARS")
    print("=" * 60)

    for table in FINANCIAL_TABLES:
        rows = companies_with_less_than_five_years(table)
        print(table)
        print(rows)
        REPORT.append({
            "type": "coverage_issue",
            "table": table,
            "rows": rows,
        })


def check_foreign_keys():
    """Check for orphan rows in child financial tables."""
    print("\n")
    print("=" * 60)
    print("FOREIGN KEY CHECK")
    print("=" * 60)

    conn = get_connection()
    cursor = conn.cursor()
    checks = [
        ("profitandloss", "companies"),
        ("balancesheet", "companies"),
        ("cashflow", "companies"),
        ("financial_ratios", "companies"),
        ("sectors", "companies"),
    ]

    for child, parent in checks:
        cursor.execute(
            f"SELECT COUNT(*) FROM {child} c LEFT JOIN {parent} p ON c.company_id = p.company_id WHERE p.company_id IS NULL"
        )
        orphan_count = cursor.fetchone()[0]
        print(f"{child:<20} orphan_rows={orphan_count}")

    conn.close()


def detect_loader_issues():
    """Surface obvious loader problems such as zero-year financial rows."""
    print("\n")
    print("=" * 60)
    print("LOADER ISSUE CHECK")
    print("=" * 60)

    conn = get_connection()
    cursor = conn.cursor()

    for table in ["profitandloss", "balancesheet", "cashflow", "financial_ratios"]:
        cursor.execute(f"SELECT COUNT(*) FROM {table} WHERE fiscal_year IS NULL OR fiscal_year = 0")
        zero_year_rows = cursor.fetchone()[0]
        print(f"{table:<20} zero_year_rows={zero_year_rows}")

    conn.close()


def export_review_report():
    """Write the collected review data to the processed output directory."""
    output_path = Path("data/processed/manual_review_report.json")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(REPORT, indent=2), encoding="utf-8")
    print(f"\nReview report exported to {output_path}")


def final_summary():
    """Print a compact summary of the review."""
    print("\n")
    print("=" * 60)
    print("FINAL SUMMARY")
    print("=" * 60)
    print(f"Report entries: {len(REPORT)}")
    print("Manual review completed.")

def check_foreign_keys():

    conn = get_connection()

    cursor = conn.cursor()

    cursor.execute(
        "PRAGMA foreign_key_check;"
    )

    violations = cursor.fetchall()

    conn.close()

    print("\n")
    print("="*80)
    print("FOREIGN KEY CHECK")
    print("="*80)

    if len(violations) == 0:

        print("PASS : No Foreign Key Violations")

    else:

        print("FAIL : Foreign Key Violations Found")

        for row in violations:

            print(row)

    return violations

def detect_loader_issues():

    conn = get_connection()

    cursor = conn.cursor()

    issues = []

    cursor.execute("""
        SELECT COUNT(*)
        FROM companies
        WHERE company_name IS NULL
    """)

    null_names = cursor.fetchone()[0]

    if null_names:

        issues.append(
            f"{null_names} NULL company names"
        )

    cursor.execute("""
        SELECT
        COUNT(*)

        FROM
        (
            SELECT ticker,
                   COUNT(*)

            FROM companies

            GROUP BY ticker

            HAVING COUNT(*) > 1
        )
    """)

    duplicate_tickers = cursor.fetchone()[0]

    if duplicate_tickers:

        issues.append(
            f"{duplicate_tickers} Duplicate Tickers"
        )

    conn.close()

    print("\n")
    print("="*80)
    print("LOADER ISSUE REVIEW")
    print("="*80)

    if len(issues) == 0:

        print("PASS : No Loader Issues Found")

    else:

        for issue in issues:

            print(issue)

    return issues

def export_review_report():

    Path("output").mkdir(
        exist_ok=True
    )

    df = pd.DataFrame(REPORT)

    output_file = "output/manual_review_report.csv"

    df.to_csv(
        output_file,
        index=False
    )

    print("\n")
    print(f"Report saved to {output_file}")
    
def final_summary():

    total_checks = len(REPORT)

    passed = sum(
        1
        for row in REPORT
        if row.get("status") == "PASS"
    )

    failed = total_checks - passed

    print("\n")
    print("="*80)
    print("FINAL MANUAL REVIEW SUMMARY")
    print("="*80)

    print(f"Total Reviews : {total_checks}")
    print(f"Passed        : {passed}")
    print(f"Failed        : {failed}")

    if failed == 0:

        print("\nOVERALL STATUS : PASS")

    else:

        print("\nOVERALL STATUS : REVIEW REQUIRED")
        
            

def main():

    print_random_companies()

    review_random_companies()

    review_financial_data()

    review_less_than_five_years()

    verify_row_counts()

    check_foreign_keys()

    detect_loader_issues()

    export_review_report()

    final_summary()


if __name__ == "__main__":

    main()
    