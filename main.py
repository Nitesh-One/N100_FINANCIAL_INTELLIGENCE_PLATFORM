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