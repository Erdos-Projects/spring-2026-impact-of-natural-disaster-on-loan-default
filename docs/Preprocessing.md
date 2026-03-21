# Preprocessing

> **Erdős Institute — Spring 2026 Data Science Bootcamp**
> Pipeline for merging NOAA disaster events with county-level loan delinquency data.

---

## Preprocessing Pipeline

### Overview

The two raw datasets live at different levels of aggregation:

- **`disaster_dataset_cleaned.dta`** — one row per NOAA storm event (event-level), covering the full U.S.
- **`finance_disaster_master.dta`** — one row per county × month, tracking early and late loan delinquency rates

The preprocessing pipeline's job is to collapse the event-level disaster data into the same county × month grid as the finance data, then merge the two into a single analysis table.

---

### Stage 1 — Panel Preparation

**Function:** `prepare_monthly_panel(df, time_col, fips_col)`

Both datasets go through the same three cleaning steps:

1. **Datetime parsing** — converts the `time` column to `pandas` datetime, coercing errors to `NaT` rather than raising.
2. **FIPS zero-padding** — casts the county identifier to a 5-character string (e.g. `"1001"` → `"01001"`). Without this, leading-zero counties silently drop out of merges.
3. **Month index** — adds a `month` column truncated to month-start (`Period("M").to_timestamp()`), which is the common key used in every subsequent join.

---

### Stage 2 — Panel Diagnostics

**Functions:** `panel_diagnostics`, `disaster_county_month_check`

Before touching the data further, the pipeline inspects the structure of each dataset:

- **Unique counties and time periods** — confirms the size of each panel.
- **Balance check** — flags whether every county appears in every month. The finance panel is expected to be balanced; the disaster dataset is not (most county-months have zero events).
- **Duplicate county-month rows** — the finance panel should have exactly one row per county × month. The disaster dataset will have many, since multiple events can hit the same county in the same month.
- **Missing month gaps** — identifies counties that drop in and out of the panel, which matters for fixed-effects estimation later.

The key takeaway from running diagnostics: `finance_master` is already clean and model-ready; `disaster_data` is *not* a panel in the same sense and must be aggregated before it can be merged.

---

### Stage 3 — Subsetting Disasters

The raw disaster dataset covers the entire U.S. and a longer time span than the finance panel. Keeping all rows would create phantom county-months that never appear in the outcome data. The pipeline restricts disasters to:

- counties that exist in `finance_master` (inner set of FIPS codes)
- months that fall within the date range of `finance_master`

This ensures every disaster row can potentially be matched to an outcome, and prevents the aggregation step from producing disaster summaries for unobservable county-months.

---

### Stage 4 — Damage Parsing

**Function:** `parse_damage(x)`

NOAA stores damage amounts as strings like `"25K"`, `"3.5M"`, or `"1B"`. The function converts these to numeric dollars using a simple multiplier map (`K` → 1,000 · `M` → 1,000,000 · `B` → 1,000,000,000). Plain numeric strings and already-numeric values pass through unchanged. Missing or unparseable values become `NaN`, which is then filled with `0` (no recorded damage).

After parsing, `total_damage = damage_property_num + damage_crops_num`.

---

### Stage 5 — Event Type Normalization

**Function:** `normalize_event_type(x)`

NOAA uses over 60 raw event labels. The function maps them into 8 broader categories using keyword matching on the lowercased label:

| Category | Example raw labels |
|---|---|
| Hurricane | `Hurricane (Typhoon)` |
| Tropical Storm | `Tropical Storm` |
| Tornado | `Tornado`, `Waterspout` |
| Flood | `Flood`, `Flash Flood`, `Coastal Flood` |
| Thunderstorm | `Thunderstorm Wind`, `Marine Thunderstorm Wind` |
| Winter Weather | `Winter Storm`, `Cold/Wind Chill`, `Extreme Cold` |
| Wildfire | `Wildfire` |
| Hail | `Hail`, `Marine Hail` |

Anything that does not match falls into `"Other"` and is dropped in the next stage. Grouping is necessary both to reduce dimensionality for modeling and to ensure each category has enough events to estimate meaningful effects.

---

### Stage 6 — Filtering

The pipeline applies two filters in sequence:

1. **Event type filter** — keeps only the 8 target categories listed above. Events like `Dust Devil` or `Waterspout` are dropped because they are too rare or too localized to generate reliable estimates.
2. **Damage threshold** — keeps only events with `total_damage >= $500,000`. This baseline threshold focuses the analysis on economically significant events and reduces noise from minor incidents.

> **Design decision:** The $500 k threshold is a starting point, not a firm boundary. It can be adjusted to study sensitivity — a lower threshold (e.g. $0) includes more events at the cost of more noise; a higher threshold (e.g. $1 M) isolates the most severe events.

---

### Stage 7 — County-Month Aggregation

Events are collapsed to the county × month level using `groupby(["fips", "month"])`. The aggregated table includes:

| Column | Description |
|---|---|
| `n_disasters` | Total qualifying events in the county-month |
| `total_damage` | Sum of all event damages |
| `max_damage` | Largest single-event damage |
| `n_hurricane` | Count of Hurricane events |
| `n_tornado` | Count of Tornado events |
| `n_tropical_storm` | Count of Tropical Storm events |
| `n_thunderstorm` | Count of Thunderstorm events |
| `n_flood` | Count of Flood events |
| `n_winter_weather` | Count of Winter Weather events |
| `n_wildfire` | Count of Wildfire events |
| `n_hail` | Count of Hail events |
| `injuries_direct` | Summed direct injuries |
| `injuries_indirect` | Summed indirect injuries |
| `deaths_direct` | Summed direct deaths |
| `deaths_indirect` | Summed indirect deaths |
| `event_occur` | Binary indicator: 1 if any qualifying disaster occurred |
| `log_total_damage` | `log(1 + total_damage)` — compresses the damage distribution for modeling |

---

### Stage 8 — Merge and Zero-Fill

The aggregated disaster table is **left-joined** onto the finance panel on `["fips", "month"]`. This preserves all county-months in the finance data, including those with no qualifying disaster.

After the join, unmatched rows (county-months with no disaster) receive `NaN` for all disaster columns. These are filled with `0`.

> **Design decision:** Zero-filling assumes that the absence of a disaster record genuinely means no qualifying disaster occurred in that county-month — not that the data is missing. This is a reasonable assumption for NOAA Storm Events, which aims for comprehensive coverage, but it is worth flagging as an open question. An alternative would be to use `NaN` and let the model treat unobserved county-months differently, or to cross-validate against a separate coverage dataset.

The final table `analysis_df` has one row per county × month, the same shape as `finance_master`, and is saved as **`finance_disaster_analysis.csv`** in the `data/analysis/` folder — this is the file picked up by the modeling notebook.

---

## How to Run

The notebook defaults to a relative path two levels above the repo:

```python
path_data = Path("../../1-Climate Finance Project")
```

Verify this points to your local `1-Climate Finance Project` folder, and update it if your directory layout differs. Then run all cells top-to-bottom. The notebook imports all helper functions directly from `preprocessing.py` — no separate installation is needed beyond the project dependencies.

```bash
# Option 1: run interactively
jupyter lab notebooks/preprocessing.ipynb

# Option 2: execute headlessly and save output
jupyter nbconvert --to notebook --execute notebooks/preprocessing.ipynb --output notebooks/preprocessing_executed.ipynb
```

