# EDA

> **Erdős Institute — Spring 2026 Data Science Bootcamp**
> Exploratory analysis of the county × month panel, motivating the fixed-effects modeling strategy.

---

## Overview

`notebooks/eda.ipynb` explores `Finance_Disaster_Analysis.csv` — the merged panel produced by the Preprocessing pipeline — before any modeling. The goals are to:

1. Understand the distribution and frequency of disaster treatment events.
2. Check whether delinquency rates move around disaster dates (raw and county-demeaned).
3. Confirm that the structure of treatment (rare in time, widespread across counties) supports a within-county fixed-effects design.

---

## Input Data

**File:** `Finance_Disaster_Analysis.csv` (in `3-Analysis/`)
**Unit of observation:** county × month (one row per FIPS code × calendar month)

Key columns used in this notebook:

| Column | Description |
|---|---|
| `fips` | 5-character county FIPS code |
| `month` | Month-start timestamp (parsed from string on load) |
| `event_occur` | Binary treatment indicator — 1 if any qualifying disaster occurred |
| `n_disasters` | Number of qualifying disaster events in that county-month |
| `total_damage` | Sum of property + crop damage across all events ($) |
| `Early_Delinquency_Rate` | Share of loans 30–89 days past due |
| `Late_Delinquency_Rate` | Share of loans 90+ days past due |
| `n_hurricane`, `n_tornado`, `n_tropical_storm`, `n_thunderstorm`, `n_flood`, `n_winter_weather`, `n_wildfire`, `n_hail` | Per-category disaster counts |

---

## Notebook Structure

### Section 1 — Treatment Balance

Counts of treated (`event_occur = 1`) vs. untreated (`event_occur = 0`) county-months, followed by a histogram of `n_disasters` among treated rows. This establishes how often multiple disasters co-occur in the same county-month.

---

### Section 2 — Top Disaster Types

Totals each per-category count column to identify which disaster types dominate the sample. Categories ranked by frequency: Thunderstorm, Hail, Flood, Winter Weather, Tornado, Wildfire, Tropical Storm, Hurricane.

---

### Section 3 — Delinquency Over Time

Line plots of average `Early_Delinquency_Rate` and `Late_Delinquency_Rate` by month across the full sample. Provides a baseline view of aggregate delinquency trends (including the 2008–2010 spike) independent of disaster treatment.

---

### Section 4 — Damage Distribution

Histogram of `log(1 + total_damage)` for treated county-months. The log scale is necessary because the raw damage distribution is extremely right-skewed — most qualifying events cluster at the $500 k threshold while a small number of hurricane/flood events generate billions of dollars in damage.

---

### Section 5 — Delinquency by Treatment Status

Group means and side-by-side boxplots comparing `Early_Delinquency_Rate` and `Late_Delinquency_Rate` between treated and untreated county-months. Provides an unconditional (unadjusted) first look at the treatment–outcome relationship.

> **Note:** The boxplots reveal a large number of outliers. Cross-county level differences in baseline delinquency dominate the raw comparison — this motivates the demeaning step in Section 7.

---

### Section 6 — Treatment Coverage

Two summaries that describe the spatial and temporal distribution of treatment:

- **Counties ever treated:** share of FIPS codes that experience at least one qualifying disaster.
- **County treatment counts:** distribution of how many times each county is treated, with the top 20 most-treated counties printed.
- **Monthly and yearly treatment rate:** line plots of the share of county-months treated in each calendar period.

**Key numbers:**
- ~**1.46%** of county-months are treated in any given month.
- ~**89.6%** of counties are treated at least once over the full sample.

---

### Section 7 — Raw Event Study (±12 months)

For each ever-treated county, the first treated month is identified. Event time is computed as months relative to that first treatment. Outcomes are averaged within each event-time bin over a ±12-month window and plotted.

This raw event study does not control for county-level baseline differences — large cross-sectional variation in delinquency levels can obscure the local treatment effect.

---

### Section 8 — County-Demeaned Event Study

County-level means for `Early_Delinquency_Rate` and `Late_Delinquency_Rate` are subtracted from each observation before averaging within event-time bins. This removes the cross-county level component and isolates within-county deviations around the disaster date.

> **Design decision:** Demeaning by county is the EDA analogue of a county fixed effect. The event-study window of ±12 months is a starting point — a wider window (e.g. ±24 months) would reveal longer-run dynamics at the cost of including observations that overlap with subsequent treatment episodes.

---

## Key Findings

| Finding | Detail |
|---|---|
| Treatment is rare over time | Only ~1.46% of county-months contain a qualifying disaster |
| Treatment is widespread across space | ~89.6% of counties are treated at least once |
| Identification is within-county | With almost no never-treated counties, a clean control group comparison is not possible — variation comes from timing differences across counties |
| Raw delinquency differences are noisy | Cross-county baseline levels dominate the unconditional comparison; county demeaning is necessary to see local effects |
| County-demeaned event study | Shows the deviation in delinquency rates in months surrounding a county's first disaster, net of its long-run average |

These findings directly support using a **two-way fixed-effects (county + time) regression** as the primary modeling approach.

---

## How to Run

The notebook uses the same relative path convention as the Preprocessing notebook:

```python
path_data = Path("../../1-Climate Finance Project")
```

Verify this points to your local `1-Climate Finance Project` folder and update it if your directory layout differs. Then run all cells top-to-bottom.

```bash
# Option 1: run interactively
jupyter lab notebooks/eda.ipynb

# Option 2: execute headlessly and save output
jupyter nbconvert --to notebook --execute notebooks/eda.ipynb --output notebooks/eda_executed.ipynb
```

