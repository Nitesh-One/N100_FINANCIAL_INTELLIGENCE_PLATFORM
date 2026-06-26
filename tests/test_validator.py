from src.etl.loader import load_and_clean
from src.etl.validator import validation_summary

def test_validation():

    df = load_and_clean("data/companies.xlsx")

    validation_summary(df)

    assert len(df) > 0