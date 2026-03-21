# Impact of Natural Disasters on Loan Default

> **Erdős Institute — Spring 2026 Data Science Bootcamp**
> Examining how natural disaster events affect county-level mortgage delinquency rates across the United States.

---

## Project Overview

This project combines NOAA storm-event records with county-level mortgage delinquency data to study whether — and how — natural disasters drive loan defaults. The analysis spans **January 2008 through February 2025** and covers nearly all U.S. counties.

The pipeline moves through four sequential stages:

| Step | Folder | Description |
|------|--------|-------------|
| 1 | [Preprocessing](#1-preprocessing) | Clean and merge disaster and finance datasets |
| 2 | [EDA](#2-eda) | Explore distributions and motivate the modeling strategy |
| 3 | [Inference](#3-inference) | Estimate causal effects with panel fixed-effects regressions |
| 4 | [Modeling](#4-modeling) | Build a predictive model for next-month delinquency rates |

---

## Folder Structure

```
├── docs/            # Stage-specific documentation
├── notebooks/       # Jupyter notebooks and helper scripts
├── src/climatefinance/  # Reusable Python library
├── data/            # Raw and processed datasets
```

---

## Running the Pipeline

Run the notebooks **in order**. Each stage produces output consumed by the next.

### 1. Preprocessing

📂 [`Preprocessing`](docs/Preprocessing.md)

Cleans and merges two raw datasets:

- **`Disaster_Dataset_Cleaned.dta`** — NOAA storm events (event-level)
- **`Finance_Disaster_Master.dta`** — county × month mortgage delinquency rates

The pipeline collapses event-level disaster records into the county × month grid, parses NOAA damage strings (e.g. `"25K"`, `"3.5M"`), normalizes 60+ event types into 8 categories (Hurricane, Tropical Storm, Tornado, Flood, Thunderstorm, Winter Weather, Wildfire, Hail), and filters to economically significant events (≥ $500k damage).

**Output:** `Finance_Disaster_Analysis.csv` — a clean county × month panel ready for analysis.

➡️ [Full Preprocessing README](docs/Preprocessing.md)

---

### 2. EDA

📂 [`EDA`](docs/EDA.md)

Explores `Finance_Disaster_Analysis.csv` before any modeling. Key findings:

- ~**1.46%** of county-months are treated (disaster occurred) in any given month.
- ~**89.6%** of counties experience at least one qualifying disaster over the full sample.
- Thunderstorm and hail are the most frequent disaster types; hurricanes are rarest.
- Raw delinquency comparisons between treated and untreated county-months are dominated by cross-county baseline differences — motivating a within-county fixed-effects design.
- County-demeaned event studies (±12 months around first treatment) isolate the local treatment effect cleanly.

➡️ [Full EDA README](docs/EDA.md)

---

### 3. Inference

📂 [`Inference`](docs/Inference.md)

Estimates the **causal effect** of natural disasters on delinquency using **two-way fixed-effects Panel OLS** (county + month fixed effects, standard errors clustered at the county level).

Key results:

| Model | Outcome | Finding |
|-------|---------|---------|
| Binary event indicator | Early & Late Delinquency | Negative but weak / statistically ambiguous |
| Distributed lag (log damage, lags 0–6) | Early Delinquency | Lags 1–4 significantly negative; peak at lag 3 (−0.0045) |
| Distributed lag (log damage, lags 0–6) | Late Delinquency | No significant lagged effects |
| Flood occurrence | Early Delinquency | Significant negative effect |
| Joint disaster-type model | Early Delinquency | Only flood significant |
| County heterogeneity (flood × top-5 counties) | Early Delinquency | Effect varies by county — some positive, some negative |

The negative lagged damage effects are consistent with post-disaster mortgage forbearance programs and FEMA aid temporarily easing borrowers' financial burden.

➡️ [Full Inference README](docs/Inference.md)

---

### 4. Modeling

📂 [`Modeling`](docs/Modeling.md)

Trains a **CatBoost Regressor** to predict `Early_Delinquency_Rate` one month ahead, using 60 engineered features (lagged delinquency rates, lagged and rolling disaster exposure, calendar and geographic features). The dataset is split **chronologically** to prevent data leakage.

| Model | RMSE | MAE | R² |
|-------|------|-----|----|
| Naive baseline (persistence) | 0.4279 | 0.3266 | 0.7365 |
| CatBoost (Validation) | 0.2872 | 0.2114 | 0.8536 |
| CatBoost (Test) | 0.3398 | 0.2486 | 0.8338 |

CatBoost reduces RMSE by ~21% over the naive baseline on the held-out test set. Lagged delinquency rates are the dominant features, with disaster-related features contributing meaningful additional signal.

➡️ [Full Modeling README](docs/Modeling.md)

---

## Setup

Dependencies are managed with [uv](https://github.com/astral-sh/uv). To install:

```bash
uv sync
```

The project requires Python ≥ 3.14. Core dependencies include `pandas`, `scikit-learn`, `catboost`, `linearmodels`, `xgboost`, `plotly`, and `seaborn` (see [`pyproject.toml`](pyproject.toml) for the full list).

