from src.logger import logger

logger.info("Project Started")

print("Environment Setup Successful")

from src.etl.loader import load_full_dataset

audit_df, conn = load_full_dataset(
    schema_path="db/schema.sql",
    db_path="db/nifty100.db",
    audit_path="logs/load_audit.csv",
)

print(audit_df.to_string(index=False))
conn.close()