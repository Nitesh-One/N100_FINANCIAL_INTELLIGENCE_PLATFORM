import pandas as pd

def load_excel(filepath):
    return pd.read_excel(filepath, header=1)

def clean_columns(df):
    new_cols = []
    for i, c in enumerate(df.columns):
        if pd.isna(c):
            new_cols.append(f"col_{i}")
        else:
            new_cols.append(str(c).strip().lower().replace(" ", "_"))
    df.columns = new_cols
    return df

def load_and_clean(filepath):
    df = load_excel(filepath)
    df = clean_columns(df)
    return df