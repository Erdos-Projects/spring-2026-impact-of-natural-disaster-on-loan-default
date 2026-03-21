"""Modeling: CatBoost regression for next-month delinquency prediction."""

# %%
import pandas as pd
from catboost import CatBoostRegressor

from climatefinance import modeling, plots, utils

results: list[dict] = []

# %% Load data
analysis_df = utils.load_analysis_data()
analysis_df["month"] = pd.to_datetime(analysis_df["month"])

# %% Feature engineering and temporal split
model_df = modeling.build_prediction_dataset(
    analysis_df,
    target_col="Early_Delinquency_Rate",
    horizon=1,
)

train_df, valid_df, test_df = modeling.temporal_split(
    model_df, date_col="month", test_months=12, valid_months=12
)

# %% Feature and target selection
categorical_cols = [
    "fips",
    "State",
    "County",
    "Coastal_County",
    "Coastline_Region",
    "month_num",
    "quarter",
]

feature_cols = [
    # static / slow-moving
    "fips",
    "State",
    "County",
    "Coastal_County",
    "Coastline_Region",
    "Land_Area",
    "Distance_To_Coast",
    "Pop",
    "month_num",
    "year",
    "quarter",
    # current disaster conditions
    "event_occur",
    "n_disasters",
    "log_total_damage",
    "flood_occur",
    "tornado_occur",
    "thunder_occur",
    "hail_occur",
    # lagged target information
    "Early_Delinquency_Rate_lag1",
    "Early_Delinquency_Rate_lag2",
    "Early_Delinquency_Rate_lag3",
    "Early_Delinquency_Rate_lag6",
    "Early_Delinquency_Rate_lag12",
    "Late_Delinquency_Rate_lag1",
    "Late_Delinquency_Rate_lag2",
    "Late_Delinquency_Rate_lag3",
    "Late_Delinquency_Rate_lag6",
    "Late_Delinquency_Rate_lag12",
    # lagged disasters
    "event_occur_lag1",
    "event_occur_lag2",
    "event_occur_lag3",
    "event_occur_lag6",
    "log_total_damage_lag1",
    "log_total_damage_lag2",
    "log_total_damage_lag3",
    "log_total_damage_lag6",
    "n_disasters_lag1",
    "n_disasters_lag2",
    "n_disasters_lag3",
    "n_disasters_lag6",
    "flood_occur_lag1",
    "flood_occur_lag2",
    "flood_occur_lag3",
    "flood_occur_lag6",
    "tornado_occur_lag1",
    "tornado_occur_lag2",
    "tornado_occur_lag3",
    "tornado_occur_lag6",
    "thunder_occur_lag1",
    "thunder_occur_lag2",
    "thunder_occur_lag3",
    "thunder_occur_lag6",
    "hail_occur_lag1",
    "hail_occur_lag2",
    "hail_occur_lag3",
    "hail_occur_lag6",
    # rolling exposure
    "event_occur_roll3",
    "event_occur_roll6",
    "log_total_damage_roll3",
    "log_total_damage_roll6",
]

# Keep only columns that actually exist
feature_cols = [c for c in feature_cols if c in model_df.columns]
categorical_cols = [c for c in categorical_cols if c in feature_cols]

X_train = train_df[feature_cols].copy()
y_train = train_df["target"].copy()

X_valid = valid_df[feature_cols].copy()
y_valid = valid_df["target"].copy()

X_test = test_df[feature_cols].copy()
y_test = test_df["target"].copy()

print("Number of features:", len(feature_cols))

# %% Naive baseline
naive_pred = test_df["Early_Delinquency_Rate"].values
baseline_metrics = modeling.evaluate_predictions(y_test, naive_pred, name="Naive baseline")
results.append(baseline_metrics)

# %% CatBoost training
for col in categorical_cols:
    X_train[col] = X_train[col].fillna("missing").astype(str)
    X_valid[col] = X_valid[col].fillna("missing").astype(str)
    X_test[col] = X_test[col].fillna("missing").astype(str)

cat_model = CatBoostRegressor(
    iterations=1500,
    learning_rate=0.03,
    depth=6,
    loss_function="RMSE",
    eval_metric="RMSE",
    random_seed=42,
    verbose=100,
)

cat_model.fit(
    X_train,
    y_train,
    cat_features=categorical_cols,
    eval_set=(X_valid, y_valid),
    use_best_model=True,
)

# %% Evaluation
valid_pred = cat_model.predict(X_valid)
test_pred = cat_model.predict(X_test)

valid_metrics = modeling.evaluate_predictions(y_valid, valid_pred, name="CatBoost validation")
test_metrics = modeling.evaluate_predictions(y_test, test_pred, name="CatBoost test")
results.append(valid_metrics)
results.append(test_metrics)

# %% Feature importance
plots.plot_model_feature_importance(feature_cols, cat_model.get_feature_importance())

# %% Monthly performance
pred_df = test_df[["fips", "County", "month"]].copy()
pred_df["y_true"] = y_test.values
pred_df["y_pred"] = test_pred

monthly_perf = pred_df.groupby("month")[["y_true", "y_pred"]].mean()

plots.plot_model_monthly_performance(monthly_perf["y_true"], monthly_perf["y_pred"])

# %% Save modeling results
results_df = pd.DataFrame(results)
print(results_df.to_string(index=False))
utils.save_analysis_modeling(results_df, index=False)
