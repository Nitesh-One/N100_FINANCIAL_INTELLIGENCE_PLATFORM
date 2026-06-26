import pandas as pd

def check_required_columns(df, required_columns):
    """
    Check if all required columns exist.
    """

    missing = []

    for col in required_columns:
        if col not in df.columns:
            missing.append(col)

    return missing

def check_duplicate_ids(df, id_column):

    duplicates = df[
        df.duplicated(subset=id_column)
    ]

    return duplicates

def check_nulls(df, columns):

    report = {}

    for col in columns:
        report[col] = df[col].isnull().sum()

    return report

def validate_numeric(df, columns):

    invalid = {}

    for col in columns:

        invalid[col] = (
            pd.to_numeric(
                df[col],
                errors="coerce"
            )
            .isnull()
            .sum()
        )

    return invalid

def remove_duplicates(df):

    before = len(df)

    df = df.drop_duplicates()

    after = len(df)

    print(f"Removed {before-after} duplicate rows")

    return df

def validation_summary(df):

    print("=" * 40)
    print("VALIDATION SUMMARY")
    print("=" * 40)

    print(f"Rows : {len(df)}")
    print(f"Columns : {len(df.columns)}")
    print(f"Missing Values : {df.isnull().sum().sum()}")
    print(f"Duplicate Rows : {df.duplicated().sum()}")
    
def check_positive_values(df, column):

    invalid = df[df[column] < 0]

    return invalid

def validate_year(df, column):

    invalid = df[
        ~df[column]
        .astype(str)
        .str.match(r"^\d{4}$")
    ]

    return invalid

def validate_foreign_key(
    child_df,
    parent_df,
    key
):

    invalid = child_df[
        ~child_df[key].isin(parent_df[key])
    ]

    return invalid

def validate_balance_sheet(df):

    invalid = df[
        df["assets"] !=
        (
            df["liabilities"] +
            df["equity"]
        )
    ]

    return invalid

def validate_unique_ticker(df):

    duplicates = df[
        df.duplicated(
            subset=["ticker"]
        )
    ]

    return duplicates

def detect_outliers(df, column):

    q1 = df[column].quantile(0.25)
    q3 = df[column].quantile(0.75)

    iqr = q3 - q1

    lower = q1 - 1.5 * iqr
    upper = q3 + 1.5 * iqr

    return df[
        (df[column] < lower)
        |
        (df[column] > upper)
    ]
    
def save_validation_report(
    failures,
    filename
):

    failures.to_csv(
        filename,
        index=False
    )       