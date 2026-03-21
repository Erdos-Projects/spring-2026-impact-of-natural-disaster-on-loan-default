"""Preprocessing pipeline: merge NOAA disaster events with county-level delinquency data."""

# %%
import numpy as np

from climatefinance import preprocessing, utils

# %% Load raw data
disaster_data = utils.get_disaster_data()
finance_master = utils.get_finance_data()

# %% Prepare both datasets into common panel format
finance_master_clean = preprocessing.prepare_monthly_panel(
    finance_master, time_col="time", fips_col="fips"
)
disaster_data_clean = preprocessing.prepare_monthly_panel(
    disaster_data, time_col="time", fips_col="fips"
)

# %% Finance panel diagnostics
finance_diag = preprocessing.panel_diagnostics(
    finance_master_clean,
    fips_col="fips",
    month_col="month",
    name="finance_master",
)

# %% Disaster panel diagnostics
disaster_diag = preprocessing.panel_diagnostics(
    disaster_data_clean,
    fips_col="fips",
    month_col="month",
    name="disaster_data",
)

# %% Check multiple disasters in same county-month
disaster_repeat = preprocessing.disaster_county_month_check(
    disaster_data_clean,
    fips_col="fips",
    month_col="month",
    event_col="event_type",
)

# %% Restrict disasters to finance panel counties and date range
finance = finance_master_clean.copy()
disasters = disaster_data_clean.copy()

finance_counties = set(finance["fips"].unique())
finance_min_month = finance["month"].min()
finance_max_month = finance["month"].max()

disasters_sub = disasters[
    disasters["fips"].isin(finance_counties)
    & disasters["month"].between(finance_min_month, finance_max_month)
].copy()

print("Disaster rows after restricting to finance counties and months:", len(disasters_sub))
print("Unique counties after restriction:", disasters_sub["fips"].nunique())
print("Date range:", disasters_sub["month"].min(), "to", disasters_sub["month"].max())

# %% Parse damages and normalize event types
disasters_sub["damage_property_num"] = (
    disasters_sub["damage_property"].apply(preprocessing.parse_damage)
    if "damage_property" in disasters_sub.columns
    else np.nan
)

disasters_sub["damage_crops_num"] = (
    disasters_sub["damage_crops"].apply(preprocessing.parse_damage)
    if "damage_crops" in disasters_sub.columns
    else 0.0
)

disasters_sub["damage_property_num"] = disasters_sub["damage_property_num"].fillna(0)
disasters_sub["damage_crops_num"] = disasters_sub["damage_crops_num"].fillna(0)

disasters_sub["total_damage"] = (
    disasters_sub["damage_property_num"] + disasters_sub["damage_crops_num"]
)

disasters_sub["event_type_grouped"] = disasters_sub["event_type"].apply(
    preprocessing.normalize_event_type
)

print(disasters_sub["event_type_grouped"].value_counts(dropna=False))

# %% Filter to target disaster types and damage threshold
target_types = utils.get_target_types()

disasters_filtered = disasters_sub[disasters_sub["event_type_grouped"].isin(target_types)].copy()

disasters_filtered_500k = disasters_filtered[disasters_filtered["total_damage"] >= 500_000].copy()

print("Rows after type filter:", len(disasters_filtered))
print("Rows after type + 500k threshold:", len(disasters_filtered_500k))
print(disasters_filtered_500k["event_type_grouped"].value_counts())

# %% County-month aggregation
cols = disasters_filtered_500k.columns

disaster_monthly = disasters_filtered_500k.groupby(["fips", "month"], as_index=False).agg(
    n_disasters=("event_type_grouped", "size"),
    total_damage=("total_damage", "sum"),
    max_damage=("total_damage", "max"),
    n_hurricane=("event_type_grouped", lambda s: (s == "Hurricane").sum()),
    n_tornado=("event_type_grouped", lambda s: (s == "Tornado").sum()),
    n_tropical_storm=("event_type_grouped", lambda s: (s == "Tropical Storm").sum()),
    n_thunderstorm=("event_type_grouped", lambda s: (s == "Thunderstorm").sum()),
    n_flood=("event_type_grouped", lambda s: (s == "Flood").sum()),
    n_winter_weather=("event_type_grouped", lambda s: (s == "Winter Weather").sum()),
    n_wildfire=("event_type_grouped", lambda s: (s == "Wildfire").sum()),
    n_hail=("event_type_grouped", lambda s: (s == "Hail").sum()),
    injuries_direct=(
        ("injuries_direct", "sum") if "injuries_direct" in cols else ("event_type_grouped", "size")
    ),
    injuries_indirect=(
        ("injuries_indirect", "sum")
        if "injuries_indirect" in cols
        else ("event_type_grouped", "size")
    ),
    deaths_direct=(
        ("deaths_direct", "sum") if "deaths_direct" in cols else ("event_type_grouped", "size")
    ),
    deaths_indirect=(
        ("deaths_indirect", "sum") if "deaths_indirect" in cols else ("event_type_grouped", "size")
    ),
)

disaster_monthly["event_occur"] = 1
disaster_monthly["log_total_damage"] = np.log1p(disaster_monthly["total_damage"])

print(disaster_monthly.head())
print("County-month rows in aggregated disaster table:", len(disaster_monthly))

# %% Merge disaster aggregates into finance panel
analysis_df = finance.merge(disaster_monthly, on=["fips", "month"], how="left")

# %% Fill untreated county-months with zeros
fill_zero_cols = [
    "n_disasters",
    "total_damage",
    "max_damage",
    "event_occur",
    "log_total_damage",
    "n_hurricane",
    "n_tornado",
    "n_tropical_storm",
    "n_thunderstorm",
    "n_flood",
    "n_winter_weather",
    "n_wildfire",
    "n_hail",
    "injuries_direct",
    "injuries_indirect",
    "deaths_direct",
    "deaths_indirect",
]

for col in fill_zero_cols:
    if col in analysis_df.columns:
        analysis_df[col] = analysis_df[col].fillna(0)

print(analysis_df.shape)
print("Share of treated county-months:", analysis_df["event_occur"].mean())

# %% Save
utils.save_analysis_data(analysis_df, index=False)
