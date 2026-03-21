"""Data cleaning pipeline: disaster data processing and finance-disaster merge.

Translates the upstream Stata .do files into Python. Reads raw data from the
data/ directory and produces the cleaned .dta files consumed by the analysis
pipeline. See docs/Cleaning.md for full documentation.
"""

# %%
import os
import re

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from climatefinance import cleaning, constants, utils

# ============================================================
# Part 1 — Disaster Dataset Cleaning
# ============================================================

# %% Load raw disaster dataset
disaster_raw = pd.read_stata(utils.repo_path(constants.DISASTER_RAW_FILE))
print(f"Loaded disaster_dataset.dta: {len(disaster_raw)} rows")

# %% Parse damage and drop invalid rows
disaster_raw["property_damage_value"] = cleaning.parse_damage_column(
    disaster_raw["damage_property"]
)
disaster_raw = cleaning.drop_invalid_damage_rows(disaster_raw, col="damage_property")
print(f"After damage filter: {len(disaster_raw)} rows")

# %% Reclassify event_type into broader categories
disaster_raw["Event_Subtype"] = disaster_raw["event_type"].copy()
disaster_raw["event_type"] = disaster_raw["event_type"].apply(cleaning.classify_event)
print(disaster_raw["event_type"].value_counts().head(10))

# %% Split by event type and label high/low cost events
disaster_cleaned = disaster_raw.copy()

for event in constants.CLEANING_EVENTS:
    df_event = disaster_cleaned[disaster_cleaned["event_type"] == event].copy()

    if df_event.empty:
        print(f"No observations for {event}, skipping.")
        continue

    median_val = df_event["property_damage_value"].median()

    df_event.insert(
        df_event.columns.get_loc("event_type") + 1,
        "event_damage_indicator",
        np.where(
            df_event["property_damage_value"] > median_val,
            "High_Cost_Event",
            "Low_Cost_Event",
        ),
    )

    fname = event.replace(" ", "_")
    out_file = utils.repo_path(constants.DISASTER_FOLDER, f"{fname}.dta")
    df_event.to_stata(out_file, write_index=False, version=118)
    print(f"Saved {fname}.dta ({len(df_event)} obs, median={median_val:,.0f})")


# ============================================================
# Part 2 — Finance Dataset Cleaning
# ============================================================


# %% Helper: build month-column rename mapping
def build_month_rename_map(
    start_vnum: int = 4,
    full_years: range = range(2008, 2025),
    partial_year: int = 2025,
    partial_months: range = range(1, 4),
) -> dict[str, str]:
    """Map v4, v5, ... to m2008_01, m2008_02, ... m2025_03."""
    rename_map: dict[str, str] = {}
    vnum = start_vnum
    for y in full_years:
        for m in range(1, 13):
            rename_map[f"v{vnum}"] = f"m{y}_{m:02d}"
            vnum += 1
    for m in partial_months:
        rename_map[f"v{vnum}"] = f"m{partial_year}_{m:02d}"
        vnum += 1
    return rename_map


def clean_finance_csv(filepath: str, delinquency_label: str) -> pd.DataFrame:
    """Import a delinquency CSV, rename month columns, clean FIPS."""
    df = pd.read_csv(utils.repo_path(filepath), header=0, dtype=str)
    rename_map = build_month_rename_map()
    df = df.rename(columns=rename_map)
    df = df.rename(columns={"Name": "County"})
    df["fips"] = df["FIPSCode"].apply(lambda x: re.sub(r"[^0-9]", "", str(x)))
    df = df.drop(columns=["FIPSCode"])
    df["fips"] = pd.to_numeric(df["fips"], errors="coerce")
    df.insert(df.columns.get_loc("County") + 1, "Delinquency_Status", delinquency_label)
    return df


# %% Import and clean both delinquency CSVs
early = clean_finance_csv(constants.FINANCE_EARLY_CSV, "Early_30_89Day_Delinquency")
late = clean_finance_csv(constants.FINANCE_LATE_CSV, "Late_>90Day_Delinquency")
print(f"Early delinquency: {len(early)} rows, Late: {len(late)} rows")

# %% Append, reshape wide → long, collapse
combined = pd.concat([late, early], ignore_index=True)
combined = combined.sort_values(["fips", "Delinquency_Status"]).reset_index(drop=True)

id_vars = [c for c in combined.columns if not c.startswith("m")]
value_vars = [c for c in combined.columns if c.startswith("m")]

long = combined.melt(
    id_vars=id_vars, value_vars=value_vars, var_name="yearmonth", value_name="delinquency_rate"
)

long["yearmonth"] = long["yearmonth"].str.lstrip("m")
long["year"] = long["yearmonth"].str[:4].astype(int)
long["mon"] = long["yearmonth"].str[5:7].astype(int)
long["time"] = (long["year"] - 1960) * 12 + (long["mon"] - 1)
long = long.drop(columns=["yearmonth", "year", "mon"])

long["delinquency_rate"] = pd.to_numeric(long["delinquency_rate"], errors="coerce")
long = long.sort_values(["fips", "Delinquency_Status", "time"]).reset_index(drop=True)

long["Early_Delinquency_Rate"] = np.where(
    long["Delinquency_Status"] == "Early_30_89Day_Delinquency", long["delinquency_rate"], np.nan
)
long["Late_Delinquency_Rate"] = np.where(
    long["Delinquency_Status"] == "Late_>90Day_Delinquency", long["delinquency_rate"], np.nan
)

finance = long.groupby(["State", "County", "fips", "time"], as_index=False).agg(
    Early_Delinquency_Rate=("Early_Delinquency_Rate", "mean"),
    Late_Delinquency_Rate=("Late_Delinquency_Rate", "mean"),
)
finance = finance.sort_values(["fips", "time", "State", "County"]).reset_index(drop=True)
finance = finance.drop_duplicates(subset=["fips", "time"], keep="first")

finance.to_stata(utils.repo_path(constants.FINANCE_DATASET_FILE), write_index=False, version=118)
print(f"Finance_Dataset.dta: {len(finance)} rows")

# %% Property damage bar chart
disaster_for_chart = pd.read_stata(utils.repo_path(constants.DISASTER_RAW_FILE))
disaster_for_chart["property_damage_billions"] = disaster_for_chart["property_damage_value"] / 1e9

damage_by_type = (
    disaster_for_chart.groupby("event_type", as_index=False)["property_damage_billions"]
    .sum()
    .sort_values("property_damage_billions", ascending=False)
)

fig_dir = utils.repo_path(constants.FIGURE_FOLDER)
os.makedirs(fig_dir, exist_ok=True)

fig, ax = plt.subplots(figsize=(10, 6))
ax.bar(damage_by_type["event_type"], damage_by_type["property_damage_billions"], color="#3B82BA")
ax.set_ylabel("Total Property Damage Value (Billions $)")
ax.set_title("Property Damage by Disaster Type")
plt.xticks(rotation=45, ha="right")
plt.tight_layout()
fig.savefig(os.path.join(fig_dir, "Property_Damage_by_DisasterType.png"), dpi=300)
plt.close(fig)
print("Saved Property_Damage_by_DisasterType.png")


# ============================================================
# Part 3 — Merge Finance + Disaster → Master Panel
# ============================================================

# %% Merge finance with disaster
finance_clean = pd.read_stata(utils.repo_path(constants.FINANCE_CLEANED_FILE))
disaster_clean = pd.read_stata(utils.repo_path(constants.DISASTER_FILE))

master = finance_clean.merge(disaster_clean, on=["fips", "time"], how="left")
master = master.drop_duplicates(subset=["fips", "time"], keep="first")

master["Event_Occur"] = np.where(master["event_type"].notna(), 1, 0)
print(f"After merge: {len(master)} rows, {master['Event_Occur'].sum()} treated")

# %% Contamination filter: drop counties with repeat events within 12 months
master = master.sort_values(["fips", "time"]).reset_index(drop=True)

events = master[master["Event_Occur"] == 1].copy()
events = events.sort_values(["fips", "time"])

events["time_to_next"] = events.groupby("fips")["time"].shift(-1) - events["time"]
events["time_to_prev"] = events["time"] - events.groupby("fips")["time"].shift(1)

events["contaminated"] = (
    ((events["time_to_next"] <= 12) & events["time_to_next"].notna())
    | ((events["time_to_prev"] <= 12) & events["time_to_prev"].notna())
).astype(int)

contaminated_fips = set(events.loc[events["contaminated"] == 1, "fips"])
master = master[~master["fips"].isin(contaminated_fips)].copy()
print(f"After contamination filter: {len(master)} rows ({len(contaminated_fips)} counties dropped)")

# %% Merge auxiliary county datasets
county_area = pd.read_stata(utils.repo_path(constants.COUNTY_AREA_FILE))
master = master.merge(county_area, on="fips", how="inner")

coastal = pd.read_stata(utils.repo_path(constants.COASTAL_COUNTIES_FILE))
master = master.merge(coastal, on="fips", how="left")

coast_dist = pd.read_stata(utils.repo_path(constants.COUNTY_COASTDIST_FILE))
master = master.merge(coast_dist, on="fips", how="inner")

master = master.drop_duplicates(subset=["fips", "time"], keep="first")

master["Coastal_County"] = np.where(master["COASTLINEREGION"].notna(), "Coastal", "Non-Coastal")

# %% Event damage indicator (high/low cost by median within event type)
master["Event_Damage_Indicator"] = ""

for event in constants.CLEANING_EVENTS:
    mask = master["event_type"] == event
    if mask.sum() == 0:
        continue
    med = master.loc[mask, "property_damage_value"].median()
    master.loc[mask & (master["property_damage_value"] > med), "Event_Damage_Indicator"] = (
        "High_Cost_Event"
    )
    master.loc[mask & (master["property_damage_value"] <= med), "Event_Damage_Indicator"] = (
        "Low_Cost_Event"
    )

# %% Column cleanup
drop_cols = ["COUNTYNAME", "STATENAME", "stateFIPS", "countyFIPS", "county", "state"]
master = master.drop(columns=[c for c in drop_cols if c in master.columns], errors="ignore")

if "COASTLINEREGION" in master.columns:
    master = master.rename(columns={"COASTLINEREGION": "Coastline_Region"})
if "tor_f_scale" in master.columns:
    master = master.rename(columns={"tor_f_scale": "Tornado_Intensity_Scale"})

master.columns = master.columns.str.lower()
master.columns = master.columns.str.title()
master = master.rename(columns={"Fips": "fips", "Time": "time"})

# %% Save final master panel
master.to_stata(utils.repo_path(constants.FINANCE_FILE), write_index=False, version=118)
print(f"Saved finance_disaster_master.dta: {len(master)} rows")


# ============================================================
# Part 4 — Event Study Plots by Disaster Type
# ============================================================

# %% Generate event study plots for each disaster type
finance_disaster = pd.read_stata(utils.repo_path("data/analysis/Finance_Disaster.dta"))

for event in constants.CLEANING_EVENTS:
    base = finance_disaster.copy()
    fname = event.replace(" ", "_")

    base["treated"] = ((base["Event_Type"] == event) & (base["Event_Occur"] == 1)).astype(int)
    base["Treated_Ever"] = base.groupby("fips")["treated"].transform("max")

    base["State_Treated"] = base.groupby("State")["Treated_Ever"].transform("max")
    base = base[base["State_Treated"] == 1].drop(columns=["State_Treated"])

    base["event_time"] = np.where(base["treated"] == 1, base["time"], np.nan)
    base["Event_Time"] = base.groupby("fips")["event_time"].transform("min")
    base = base.drop(columns=["event_time", "treated"])

    base["Rel_Time"] = base["time"] - base["Event_Time"]

    base = base[
        ((base["Treated_Ever"] == 1) & (base["Rel_Time"].between(-12, 12)))
        | (base["Treated_Ever"] == 0)
    ].copy()

    # Stacked cohort design
    etimes = base.loc[base["Treated_Ever"] == 1, "Event_Time"].dropna().unique()

    stacked_frames = []
    for et in etimes:
        sub = base[
            ((base["Treated_Ever"] == 1) & (base["Event_Time"] == et)) | (base["Treated_Ever"] == 0)
        ].copy()
        sub.loc[sub["Treated_Ever"] == 0, "Rel_Time"] = (
            sub.loc[sub["Treated_Ever"] == 0, "time"] - et
        )
        sub = sub[sub["Rel_Time"].between(-12, 12)].copy()
        sub["cohort"] = et
        stacked_frames.append(sub)

    if not stacked_frames:
        print(f"No stacked data for {event}, skipping plots.")
        continue

    stacked = pd.concat(stacked_frames, ignore_index=True)
    stacked = stacked.drop_duplicates(subset=["fips", "time", "cohort"], keep="first")

    for depvar in ["Early_Delinquency_Rate", "Late_Delinquency_Rate"]:
        if depvar not in stacked.columns:
            continue

        agg = stacked.groupby(["Rel_Time", "Treated_Ever"], as_index=False)[depvar].mean()

        fig, ax = plt.subplots(figsize=(10, 5))

        treated_data = agg[agg["Treated_Ever"] == 1].sort_values("Rel_Time")
        control_data = agg[agg["Treated_Ever"] == 0].sort_values("Rel_Time")

        ax.plot(
            treated_data["Rel_Time"],
            treated_data[depvar],
            color="blue",
            linewidth=1.8,
            label="Treated",
        )
        ax.plot(
            control_data["Rel_Time"],
            control_data[depvar],
            color="green",
            linewidth=1.2,
            linestyle="--",
            label="Control",
        )

        ax.axvline(x=0, color="red", linestyle="--", linewidth=0.8)
        ax.set_xlabel("Months to Event")
        ax.set_ylabel(depvar)
        ax.set_title(event)
        ax.set_xticks(range(-12, 13))
        ax.legend(loc="upper center", ncol=2, frameon=False)

        plt.tight_layout()
        fig.savefig(os.path.join(fig_dir, f"{fname}_{depvar}.png"), dpi=300)
        plt.close(fig)

    print(f"Plots saved for {event}")

print("Done.")
