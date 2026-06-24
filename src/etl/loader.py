import pandas as pd

def load_excel(filepath):
    return pd.read_excel(filepath, header=1)

def clean_columns(df):
    df.columns = (
        df.columns
        .str.strip()
        .str.lower()
        .str.replace(" ", "_")
    )
    return df

def load_and_clean(filepath):
    df = load_excel(filepath)
    df = clean_columns(df)
    return df