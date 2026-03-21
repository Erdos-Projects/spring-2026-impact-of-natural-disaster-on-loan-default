# Inference

This folder contains the panel econometric analysis estimating the causal effect of natural disaster events on mortgage loan delinquency rates at the U.S. county level.

## File

| File | Description |
|------|-------------|
| `Inference.ipynb` | Panel OLS regressions of delinquency rates on disaster exposure variables |

## Data

The notebook reads `Finance_Disaster_Analysis.csv` from the `Data/3-Analysis/` folder of the project. The dataset is a county-month panel containing:

- **`fips`** – County FIPS code (entity identifier)
- **`month`** – Year-month (time identifier)
- **`Early_Delinquency_Rate`** – Share of loans 30–89 days past due
- **`Late_Delinquency_Rate`** – Share of loans 90+ days past due
- **`event_occur`** – Binary indicator for any disaster event in that county-month
- **`log_total_damage`** – Log of total property + crop damage from disasters
- **`n_flood`, `n_tornado`, `n_thunderstorm`, `n_hail`** – Count of events by disaster type
- **`total_damage`, `n_disasters`** – Aggregate damage and event counts

## Methodology

All models use **two-way fixed effects Panel OLS** (entity + time fixed effects) with standard errors clustered at the county level, estimated via the `linearmodels` Python package.

```
y_{it} = α_i + λ_t + β X_{it} + ε_{it}
```

where `α_i` are county fixed effects and `λ_t` are month fixed effects.

## Models

### 1. Baseline Event Occurrence
Regresses each delinquency rate on a binary indicator for any disaster event occurring in that county-month.

- **Outcome:** `Early_Delinquency_Rate`, `Late_Delinquency_Rate`
- **Regressor:** `event_occur`

**Results:** The baseline models reveal a weak and statistically ambiguous average relationship between disaster occurrence and delinquency rates. The coefficient on `event_occur` is negative for both outcomes, but significance varies. This suggests that a raw occurrence indicator is too coarse to detect a consistent signal — disaster events differ widely in severity, and their effects may be distributed across time rather than concentrated in the event month.

### 2. Distributed Lag Model (Damage Severity)
Estimates the dynamic response of delinquency rates to disaster damage over a 0–6 month window, using lags of `log_total_damage`.

- **Outcome:** `Early_Delinquency_Rate`, `Late_Delinquency_Rate`
- **Regressors:** `log_total_damage`, `log_total_damage_lag1` … `log_total_damage_lag6`

**Results:** For early delinquency, lags 1–4 are negative and statistically significant:

| Lag | Coefficient |
|-----|------------|
| Lag 1 | −0.0030 |
| Lag 2 | −0.0036 |
| Lag 3 | −0.0045 |
| Lag 4 | −0.0033 |

Lags 5–6 are not significant, and the contemporaneous effect (lag 0) is also not significant. This pattern indicates that greater disaster damage is followed by a *temporary decline* in early delinquency, peaking around 2–4 months after the event. Rather than deteriorating, delinquency rates fall in the aftermath of severe disasters — consistent with post-disaster mortgage forbearance programs, FEMA aid, and other relief mechanisms that temporarily ease borrowers' financial burden. No significant lagged effects are found for late delinquency.

### 3. Disaster-Type Effects
Tests whether specific disaster types (flood, tornado, thunderstorm, hail) drive delinquency differently, both individually and in a joint model.

- **Outcome:** `Early_Delinquency_Rate`, `Late_Delinquency_Rate`
- **Regressors (individual):** `flood_occur`, `tornado_occur`, `thunder_occur`, `hail_occur` (each run separately, then jointly)

**Results:** When each type is run separately, flood and tornado each show negative point estimates for early delinquency, but neither hail nor thunderstorm yields a robust effect. In the joint four-type model, **flood exposure is the only disaster type with a statistically significant negative effect on early delinquency**. Tornado, hail, and thunderstorm lose significance when estimated jointly, suggesting they are collinear with flood or lack the severity to generate a detectable average signal. No disaster type shows a significant effect on late delinquency in either the individual or joint specifications, implying that relief programs act faster than serious delinquency can develop.

### 4. County Heterogeneity (Flood Interactions)
Examines whether the flood effect varies across the five most disaster-exposed counties by interacting `flood_occur` with county-level indicators.

- **Outcome:** `Early_Delinquency_Rate`
- **Regressors:** `flood_occur` + interaction terms for the top-5 counties by cumulative total damage

**Results:** The county-level interaction model reveals substantial heterogeneity in the flood effect. The base flood coefficient remains negative, but the interaction terms vary in sign and magnitude across the five counties. Some high-exposure counties show an even larger negative effect than the average (consistent with more active forbearance deployment), while others show a positive interaction term — indicating that in those counties flood exposure is associated with *rising* early delinquency. This suggests that county-level characteristics such as local income levels, lender composition, disaster preparedness, and relief access meaningfully moderate the aggregate relationship identified in the simpler models.

## Key Results Summary

| Model | Outcome | Main Finding |
|-------|---------|-------------|
| Baseline (event_occur) | Early & Late Delinquency | Negative but weak / statistically ambiguous |
| Distributed lag (log damage) | Early Delinquency | Lags 1–4 significantly negative; peak at lag 3 (−0.0045) |
| Distributed lag (log damage) | Late Delinquency | No significant lagged effects |
| Flood occurrence (individual) | Early Delinquency | Significant negative effect |
| Flood occurrence (individual) | Late Delinquency | Not significant |
| Joint type model | Early Delinquency | Only flood significant; tornado/hail/thunder are not |
| County heterogeneity | Early Delinquency | Flood effect varies by county — some positive, some negative |

