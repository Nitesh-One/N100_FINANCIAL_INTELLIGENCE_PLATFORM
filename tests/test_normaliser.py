from src.etl.normaliser import normalize_year
from src.etl.normaliser import normalize_ticker

def test_year_2023():
    assert normalize_year("2023") == 2023

def test_year_fy():
    assert normalize_year("FY2023") == 2023

def test_tcs():
    assert normalize_ticker("TCS.NS") == "TCS"

def test_infy():
    assert normalize_ticker("INFY.NS") == "INFY"