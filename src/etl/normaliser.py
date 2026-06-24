import re
import pandas as pd


def normalize_year(value):

    if pd.isna(value):
        return None

    value = str(value)

    match = re.search(r"\d{4}", value)

    if match:
        return int(match.group())

    return None

def normalize_ticker(ticker):

    if pd.isna(ticker):
        return None

    return str(ticker).split(".")[0].strip().upper()

def normalize_company_name(name):

    if pd.isna(name):
        return None

    return str(name).strip()
