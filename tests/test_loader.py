from src.etl.loader import load_and_clean

def test_load_companies():
    df = load_and_clean("data/raw/companies.xlsx")

    assert df.shape[0] > 0
    assert len(df.columns) > 0