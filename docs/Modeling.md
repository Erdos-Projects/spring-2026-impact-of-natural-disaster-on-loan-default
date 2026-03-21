# Modeling

This folder contains the predictive modeling pipeline for forecasting county-level mortgage delinquency rates, with a focus on understanding the impact of natural disasters.

---

## Data

The model uses `finance_disaster_analysis.csv`, a merged panel dataset at the **county × month** level covering **January 2008 – February 2025**. Each row represents one county (identified by FIPS code) in one month and includes:

- **Delinquency rates** — `Early_Delinquency_Rate` and `Late_Delinquency_Rate`
- **Disaster indicators** — occurrence flags and damage estimates for floods, tornadoes, thunderstorms, hail, and aggregate disaster counts
- **Geographic features** — land area, distance to coast, coastal county flag, coastline region, population
- **Calendar features** — month, year, quarter

The dataset is split **chronologically** to avoid data leakage:

| Split      | Date Range              | Observations |
|------------|-------------------------|--------------|
| Train      | Jan 2008 – Feb 2023     | 64,974       |
| Validation | Mar 2023 – Feb 2024     | 4,284        |
| Test       | Mar 2024 – Feb 2025     | 4,284        |

---

## Method

### Target

The model predicts **`Early_Delinquency_Rate` one month ahead** (`horizon = 1`).

### Feature Engineering (`modeling.py`)

60 features are constructed from the raw panel data:

- **Binary event indicators** — `flood_occur`, `tornado_occur`, `thunder_occur`, `hail_occur`
- **Calendar features** — `month_num`, `year`, `quarter`
- **Lagged targets** — lags 1, 2, 3, 6, 12 months for both `Early_Delinquency_Rate` and `Late_Delinquency_Rate`
- **Lagged disaster features** — lags 1, 2, 3, 6 months for event occurrence, log total damage, disaster count, and each disaster type
- **Rolling disaster exposure** — 3- and 6-month rolling sums of event occurrence and log total damage

### Model

A **CatBoost Regressor** is trained with the following hyperparameters:

| Hyperparameter  | Value  |
|-----------------|--------|
| Iterations      | 1,500  |
| Learning rate   | 0.03   |
| Depth           | 6      |
| Loss function   | RMSE   |
| Random seed     | 42     |

Categorical features (`fips`, `State`, `County`, `Coastal_County`, `Coastline_Region`, `month_num`, `quarter`) are passed directly to CatBoost after being cast to strings to handle any missing values.

Early stopping is applied using the validation set (`use_best_model=True`); the best model was selected at **iteration 1,497**.

### Baseline

A naive baseline predicts that next month's delinquency rate equals the current month's rate (persistence forecast).

---

## Results

| Model               | RMSE   | MAE    | R²     |
|---------------------|--------|--------|--------|
| Naive Baseline      | 0.4279 | 0.3266 | 0.7365 |
| CatBoost (Validation) | 0.2872 | 0.2114 | 0.8536 |
| CatBoost (Test)     | 0.3398 | 0.2486 | 0.8338 |

The CatBoost model substantially outperforms the naive baseline, reducing RMSE by ~21% on the test set and explaining ~83% of the variance in next-month early delinquency rates.

### Top Feature Importances

The 20 most important features (by CatBoost's built-in importance metric) are visualized in `notebooks/modeling.ipynb`. Lagged delinquency rates dominate, confirming strong autocorrelation in delinquency series — with disaster-related features contributing meaningful signal on top of that baseline.

---

## Files

| File            | Description                                              |
|-----------------|----------------------------------------------------------|
| `notebooks/modeling.ipynb` | End-to-end notebook: feature construction, model training, evaluation, and feature importance plot |
| `notebooks/modeling.py`   | Reusable helper functions: `build_prediction_dataset`, `temporal_split`, `evaluate_predictions` |

