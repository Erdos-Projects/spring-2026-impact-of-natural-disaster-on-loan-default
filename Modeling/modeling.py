import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from catboost import CatBoostRegressor


def build_prediction_dataset(df, target_col="Early_Delinquency_Rate", horizon=1):
    """Build a feature-rich dataset for predicting delinquency rates one step ahead."""
    data = df.copy()
    data["month"] = pd.to_datetime(data["month"])
    data = data.sort_values(["fips", "month"]).copy()

    # ---------------------------
    # Basic event indicators
    # ---------------------------
    data["flood_occur"] = (data["n_flood"] > 0).astype(int)
    data["tornado_occur"] = (data["n_tornado"] > 0).astype(int)
    data["thunder_occur"] = (data["n_thunderstorm"] > 0).astype(int)
    data["hail_occur"] = (data["n_hail"] > 0).astype(int)

    # ---------------------------
    # Calendar features
    # ---------------------------
    data["month_num"] = data["month"].dt.month
    data["year"] = data["month"].dt.year
    data["quarter"] = data["month"].dt.quarter

    # ---------------------------
    # Lagged targets
    # ---------------------------
    # Include lags of both delinquency rates to capture cross-series dynamics
    for lag in [1, 2, 3, 6, 12]:
        data[f"{target_col}_lag{lag}"] = data.groupby("fips")[target_col].shift(lag)

    other_target = "Late_Delinquency_Rate" if target_col == "Early_Delinquency_Rate" else "Early_Delinquency_Rate"
    for lag in [1, 2, 3, 6, 12]:
        data[f"{other_target}_lag{lag}"] = data.groupby("fips")[other_target].shift(lag)

    # ---------------------------
    # Lagged disaster features
    # ---------------------------
    lag_vars = [
        "event_occur", "log_total_damage", "n_disasters",
        "flood_occur", "tornado_occur", "thunder_occur", "hail_occur"
    ]

    for var in lag_vars:
        for lag in [1, 2, 3, 6]:
            data[f"{var}_lag{lag}"] = data.groupby("fips")[var].shift(lag).fillna(0)

    # ---------------------------
    # Rolling disaster exposure
    # Use only past/current information
    # ---------------------------
    g = data.groupby("fips")

    # 3- and 6-month rolling sums of disaster occurrence and damage
    data["event_occur_roll3"] = (
        g["event_occur"].rolling(3, min_periods=1).sum().reset_index(level=0, drop=True)
    )
    data["event_occur_roll6"] = (
        g["event_occur"].rolling(6, min_periods=1).sum().reset_index(level=0, drop=True)
    )

    data["log_total_damage_roll3"] = (
        g["log_total_damage"].rolling(3, min_periods=1).sum().reset_index(level=0, drop=True)
    )
    data["log_total_damage_roll6"] = (
        g["log_total_damage"].rolling(6, min_periods=1).sum().reset_index(level=0, drop=True)
    )

    # ---------------------------
    # Next-month target
    # ---------------------------
    # Shift target forward by `horizon` months within each county
    data["target"] = data.groupby("fips")[target_col].shift(-horizon)

    # Drop rows where the future target is unavailable (end of series)
    data = data.dropna(subset=["target"]).copy()

    return data


def temporal_split(df, date_col="month", test_months=12, valid_months=12):
    """Split data chronologically into train, validation, and test sets."""
    months = np.array(sorted(df[date_col].unique()))

    test_cut = months[-test_months:]
    valid_cut = months[-(test_months + valid_months):-test_months]
    train_cut = months[:-(test_months + valid_months)]

    train_df = df[df[date_col].isin(train_cut)].copy()
    valid_df = df[df[date_col].isin(valid_cut)].copy()
    test_df = df[df[date_col].isin(test_cut)].copy()

    print("Train range:", train_df[date_col].min(), "to", train_df[date_col].max(), "| n =", len(train_df))
    print("Valid range:", valid_df[date_col].min(), "to", valid_df[date_col].max(), "| n =", len(valid_df))
    print("Test range: ", test_df[date_col].min(), "to", test_df[date_col].max(), "| n =", len(test_df))

    return train_df, valid_df, test_df


def evaluate_predictions(y_true, y_pred, name="model"):
    """Compute and print RMSE, MAE, and R² for a set of predictions."""
    rmse = np.sqrt(mean_squared_error(y_true, y_pred))
    mae = mean_absolute_error(y_true, y_pred)
    r2 = r2_score(y_true, y_pred)
    print(f"{name}")
    print("RMSE:", round(rmse, 4))
    print("MAE: ", round(mae, 4))
    print("R2:  ", round(r2, 4))
    print("-" * 40)
    return {"model": name, "RMSE": rmse, "MAE": mae, "R2": r2}

