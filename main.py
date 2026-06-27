from src.logger import logger

logger.info("Project Started")

print("Environment Setup Successful")

from src.etl.loader import load_and_clean

files = [
    "companies.xlsx",
    "profitandloss.xlsx",
    "balancesheet.xlsx",
    "cashflow.xlsx",
    "documents.xlsx",
    "stock_prices.xlsx",
    "financial_ratios.xlsx",
    "market_cap.xlsx",
    "peer_groups.xlsx",
    "sectors.xlsx",
    "analysis.xlsx",
    "prosandcons.xlsx"
]

for file in files:
    path = f"data/raw/{file}"

    try:
        df = load_and_clean(path)
        print(f"{file}: {df.shape}")
    except Exception as e:
        print(f"{file}: ERROR -> {e}")


# Run database schema and constraint validations
try:
    from src.etl.db_validator import run_all, print_report

    print("\nRunning DB schema validations...")
    # Use an in-memory DB for validations to avoid persistent test data
    results = run_all("db/schema.sql", ":memory:")
    print_report(results)
except Exception as e:
    print(f"DB validation failed to run: {e}")