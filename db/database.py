from sqlalchemy import create_engine
from src.etl.loader import load_and_clean

engine = create_engine(
    "sqlite:///db/nifty100.db"
)

def load_to_database(filepath, table_name):

    df = load_and_clean(filepath)

    df.to_sql(
        table_name,
        engine,
        if_exists="replace",
        index=False
    )

    print(f"{table_name} loaded successfully.")


if __name__ == "__main__":
    from pathlib import Path

    raw_dir = Path("data/raw")
    if not raw_dir.exists():
        print("data/raw folder not found. No files to load.")
    else:
        for f in sorted(raw_dir.glob("*.xlsx")):
            table_name = f.stem
            try:
                load_to_database(str(f), table_name)
            except Exception as e:
                print(f"Failed to load {f.name}: {e}")