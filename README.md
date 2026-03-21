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

## Datasets

The pipeline expects input data under the `data/` directory, organized as follows:

```
data/
├── disaster/          # NOAA storm-event records
│   ├── disaster_dataset.dta           # Raw NOAA storm events (event-level, full U.S.)
│   └── disaster_dataset_cleaned.dta   # Cleaned version with standardized columns and parsed fields
├── finance/           # County-level mortgage delinquency panel
│   └── finance_disaster_master.dta    # County × month panel with early & late delinquency rates
├── analysis/          # Pipeline outputs
│   ├── finance_disaster_analysis.csv   # Merged county × month panel (from Preprocessing)
│   └── inference_results.csv           # Panel OLS coefficients and p-values (from Inference)
├── figures/           # Saved plots
└── raw/               # Archival copies of all source files (not required)
```

### Key input files

| File | Directory | Description |
|------|-----------|-------------|
| `disaster_dataset.dta` | `data/disaster/` | Raw NOAA Storm Events data — one row per event, covering all U.S. counties. Contains event type, location (FIPS), date, property/crop damage strings, and injury/death counts. |
| `disaster_dataset_cleaned.dta` | `data/disaster/` | Cleaned version of the raw dataset with standardized column names, parsed damage values, and filtered date ranges. This is the input consumed by the Preprocessing notebook. |
| `finance_disaster_master.dta` | `data/finance/` | County × month panel of mortgage delinquency rates (early: 30–89 days past due, late: 90+ days). One row per FIPS code × calendar month, January 2008 – February 2025. |

### Pipeline outputs

| File | Directory | Description |
|------|-----------|-------------|
| `finance_disaster_analysis.csv` | `data/analysis/` | Merged county × month panel produced by the Preprocessing notebook. Consumed by all downstream notebooks. |
| `inference_results.csv` | `data/analysis/` | Coefficients, standard errors, and p-values from all Panel OLS models in the Inference notebook. One row per regressor per model. |

---

## Folder Structure

```
├── docs/                # Stage-specific documentation
├── notebooks/           # Jupyter notebooks and helper scripts
├── src/climatefinance/  # Reusable Python library
└── data/                # Raw and processed datasets
```

---

## Running the Pipeline

Run the notebooks **in order**. Each stage produces output consumed by the next.

### 1. Preprocessing

📂 [`Preprocessing`](docs/Preprocessing.md)

Cleans and merges two raw datasets:

- **`disaster_dataset_cleaned.dta`** — NOAA storm events (event-level)
- **`finance_disaster_master.dta`** — county × month mortgage delinquency rates

The pipeline collapses event-level disaster records into the county × month grid, parses NOAA damage strings (e.g. `"25K"`, `"3.5M"`), normalizes 60+ event types into 8 categories (Hurricane, Tropical Storm, Tornado, Flood, Thunderstorm, Winter Weather, Wildfire, Hail), and filters to economically significant events (≥ $500k damage).

**Output:** `finance_disaster_analysis.csv` — a clean county × month panel ready for analysis.

➡️ [Full Preprocessing README](docs/Preprocessing.md)

---

### 2. EDA

📂 [`EDA`](docs/EDA.md)

Explores `finance_disaster_analysis.csv` before any modeling. Key findings:

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

## Usage

### Setup

Dependencies are managed with [uv](https://github.com/astral-sh/uv). The project requires Python ≥ 3.14.

```bash
uv sync
```

This installs the `climatefinance` library in editable mode along with all dev dependencies (Jupyter, ruff, ty). See [`pyproject.toml`](pyproject.toml) for the full dependency list.

### Running notebooks

```bash
jupyter lab notebooks/preprocessing.ipynb
```

Run the notebooks in order: `preprocessing` → `eda` → `inference` → `modeling`. Each stage saves outputs consumed by the next.

### Using the library

The `climatefinance` package is importable from any notebook or script in the venv:

```python
from climatefinance import utils, plots
from climatefinance import TARGET_TYPES

df = utils.load_analysis_data()
plots.plot_eda_delinquency_over_time(df)
```

### Make commands

| Command | Description |
|---------|-------------|
| `make qc` | Run linting (ruff) and type checking (ty) on `src/` and `notebooks/` |
| `make nb-clean` | Strip all cell outputs from notebooks |

