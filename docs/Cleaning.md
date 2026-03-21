# Data Cleaning

> Documentation of the upstream data cleaning pipeline that produces the input files consumed by the analysis notebooks.

The cleaning was performed in Stata with a Python translation available in the repository. The outputs are the two `.dta` files that our preprocessing notebook reads.

---

## Source Data

| Source | Format | Description |
|--------|--------|-------------|
| NOAA Storm Events Database | Yearly CSVs (1980–2025) | Event-level disaster records for the U.S. — one row per storm event with type, location, damage, injuries, and deaths |
| CFPB / Mortgage Performance | `Finance_30_89_EarlyDelinquency.csv` | County-level early delinquency rates (30–89 days past due), wide format with one column per month |
| CFPB / Mortgage Performance | `Finance_90_LateDelinquency.csv` | County-level late delinquency rates (90+ days past due), same wide format |
| `CountyCode.dta` | FIPS crosswalk | Maps state + county FIPS codes to a single 5-digit FIPS identifier |
| `County_Area.dta`, `Coastal_Counties.dta`, `County_CoastDist.dta` | Auxiliary | Land area, coastal status, and distance-to-coast for each county |

---

## Disaster Dataset Cleaning

**Output:** `data/disaster/disaster_dataset.dta` → `data/disaster/disaster_dataset_cleaned.dta`

### Step 1 — Combine yearly CSVs

All NOAA Storm Events CSV files from 1980 to 2025 are appended into a single dataset (`NWS_temp.dta`).

### Step 2 — FIPS crosswalk merge

The raw data uses separate `state_fips` and `cz_fips` (county zone FIPS) columns. These are merged with a `CountyCode.dta` crosswalk to produce a single 5-digit county `fips` code. Only records that match a valid county FIPS are kept (inner join).

### Step 3 — Time variable construction

- Month names are parsed into numeric month values
- A Stata monthly time variable is created from `year` and `month_num` (`ym(year, month_num)`)
- Duplicate records on `(fips, time, event_id)` are dropped

### Step 4 — Damage parsing

The `damage_property` column stores values as strings with suffixes (`"25K"`, `"3.5M"`, `"1B"`). The cleaning:

1. Extracts the last character as the multiplier (`K` = 1,000, `M` = 1,000,000, `B` = 1,000,000,000)
2. Extracts the numeric prefix
3. Computes `property_damage_value = numeric_part × multiplier`
4. Drops rows with missing, zero, or unparseable damage values (`"0"`, `"0K"`, `"0.00K"`)
5. Drops rows where the suffix is not K, M, or B

### Step 5 — Event type reclassification

The 60+ raw NOAA event labels are consolidated into broader categories:

| Category | Raw labels included |
|----------|-------------------|
| Hurricane | `Hurricane (Typhoon)`, `Storm Surge/Tide`, `High Surf`, `Marine High Wind` |
| Tropical Storm | `Tropical Storm` |
| Tornado | `Tornado` |
| Flood | `Flood`, `Flash Flood`, `Lakeshore Flood`, `Coastal Flood` |
| Thunderstorm | All labels containing "Thunder" or "Thunderstorm" |
| Winter Wave | `Winter Storm`, `Sleet`, `Winter Weather`, `Ice Storm`, `Frost/Freeze`, `Freezing Fog`, `Extreme Cold/Wind Chill`, `Heavy Snow`, `Blizzard`, `Cold/Wind Chill` |
| Wildfire | `Wildfire` |
| Hail | `Hail` |
| Dust Storm | `Dust Devil`, `Dust Storm` |
| Heat Wave | `Excessive Heat`, `Heat` |

The original event label is preserved as `Event_Subtype`.

### Step 6 — Column selection

The final disaster dataset keeps: `fips`, `time`, `Event_Subtype`, `event_type`, `event_id`, `tor_f_scale`, `injuries_indirect`, `injuries_direct`, `deaths_direct`, `deaths_indirect`, `property_damage_value`, `damage_property`, `damage_crops`, `event_narrative`.

### Step 7 — Per-type damage classification

For each of the 8 target disaster types, the median `property_damage_value` is computed. Events above the median are labeled `High_Cost_Event`, at or below are `Low_Cost_Event`. Each type is saved as a separate `.dta` file (e.g., `Hurricane.dta`, `Tornado.dta`).

---

## Finance Dataset Cleaning

**Output:** `data/finance/finance_disaster_master.dta`

### Step 1 — Import delinquency CSVs

Both delinquency CSV files are imported. The wide-format columns (`v4`, `v5`, ...) are renamed to `m2008_01`, `m2008_02`, ..., `m2025_03` using a loop over years and months. The `FIPSCode` column is cleaned to digits only and destringed.

### Step 2 — Reshape and collapse

The two datasets (early and late delinquency) are appended, then reshaped from wide to long format:
- `yearmonth` strings (`"2008_01"`) are converted to Stata monthly dates
- Early and late delinquency rates are split into separate columns
- The data is collapsed to one row per `(fips, time)` by averaging the rates

**Output:** `Finance_Dataset.dta`

### Step 3 — Merge with disaster data

`Finance_Cleaned.dta` (a cleaned version of the finance panel) is left-joined with `Disaster_Dataset_Cleaned.dta` on `(fips, time)`. An `Event_Occur` binary indicator is created (1 if any disaster event is present).

### Step 4 — Contamination filter

Counties with repeat disaster events within 12 months of each other are identified and **dropped entirely**. This is a conservative filter to ensure clean identification in the event study design — it removes counties where overlapping treatment episodes would confound the timing-based identification.

> **Note:** This filter is applied in the Stata cleaning stage but **not** in our Python preprocessing notebook. Our notebook operates on the already-filtered `finance_disaster_master.dta`.

### Step 5 — Auxiliary county data merge

Three additional datasets are merged onto the panel:
- **`County_Area.dta`** — land area (inner join, drops counties without area data)
- **`Coastal_Counties.dta`** — coastal county flag (left join)
- **`County_CoastDist.dta`** — distance to coast (inner join)

A `Coastal_County` indicator is derived: `"Coastal"` if `COASTLINEREGION` is non-missing, else `"Non-Coastal"`.

### Step 6 — Event damage classification

Same median-based `High_Cost_Event` / `Low_Cost_Event` classification as in the disaster pipeline, applied within the merged panel.

### Step 7 — Column cleanup

- Helper columns (`COUNTYNAME`, `STATENAME`, state/county FIPS duplicates) are dropped
- `COASTLINEREGION` → `Coastline_Region`, `tor_f_scale` → `Tornado_Intensity_Scale`
- All columns are standardized to proper case, with `fips` and `time` kept lowercase

**Final output:** `finance_disaster_master.dta` — the county × month panel with delinquency rates, disaster indicators, damage values, and geographic features.

---

## File Lineage

```
NOAA CSVs (1980–2025)
    │
    ▼
disaster_dataset.dta          ← raw combined + FIPS merged + damage parsed + types classified
    │
    ▼
disaster_dataset_cleaned.dta  ← manual review / additional cleaning
    │
    ├──▶ Hurricane.dta, Tornado.dta, ...  (per-type splits with cost labels)
    │
    ▼
Finance CSVs ──▶ Finance_Dataset.dta ──▶ Finance_Cleaned.dta
                                              │
                                              ├── + disaster_dataset_cleaned.dta
                                              ├── + County_Area.dta
                                              ├── + Coastal_Counties.dta
                                              ├── + County_CoastDist.dta
                                              ▼
                                    finance_disaster_master.dta  ← final input to our pipeline
```

---

## Relationship to Our Pipeline

The Python preprocessing notebook (`notebooks/preprocessing.ipynb`) picks up where the Stata cleaning leaves off:

1. Loads `disaster_dataset_cleaned.dta` and `finance_disaster_master.dta`
2. Re-parses damage strings and normalizes event types (our categories differ slightly — we use "Winter Weather" instead of "Winter Wave")
3. Applies its own damage threshold ($500k) and aggregates to county × month
4. Merges and zero-fills to produce `finance_disaster_analysis.csv`

The Stata contamination filter (dropping counties with events within 12 months) is **already baked into** `finance_disaster_master.dta`, so our notebook does not repeat it.
