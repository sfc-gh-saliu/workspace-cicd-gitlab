import pandas as pd


def generate_sales_data():
    return pd.DataFrame({
        "month": list(range(1, 13)),
        "revenue": [100, 120, 130, 150, 170, 160, 180, 200, 190, 210, 220, 250],
    })


def forecast(df):
    avg_growth = df["revenue"].diff().mean()
    last = df["revenue"].iloc[-1]
    return pd.DataFrame({
        "month": [13, 14, 15],
        "forecast": [last + avg_growth * i for i in range(1, 4)],
    })
