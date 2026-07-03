import pandas as pd


def generate_customer_data():
    return pd.DataFrame({
        "customer_id": ["C001", "C002", "C003", "C004", "C005"],
        "inactive_days": [5, 45, 10, 90, 30],
        "tenure_days": [365, 180, 730, 120, 365],
    })


def score_customers(df):
    df["churn_score"] = round(df["inactive_days"] / df["tenure_days"], 3)
    return df[["customer_id", "churn_score"]]
