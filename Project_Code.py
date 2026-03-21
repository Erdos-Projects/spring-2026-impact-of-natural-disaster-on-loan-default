"""
Python translation of the Stata .do file for NWS disaster data processing.
Requires: pandas, numpy
"""

import os
import pandas as pd
import numpy as np

# ============================================================
# Paths (adjust these to match your system)
# ============================================================
excel_dir = r"D:\Academic\1-UNL\1-Research\1-Projects\1-US Studies\1-Hurricanes and Crime\1-Data\2-Disaster Data\NWS\Raw Data\Excel"
output_path = r"C:\Users\ghosh\OneDrive - University of Nebraska\2-Erdos\1-Climate Finance Project\Data\Raw Data"
individual_disasters_path = r"C:\Users\ghosh\OneDrive - University of Nebraska\2-Erdos\1-Climate Finance Project\Data\Individual Disasters"

os.chdir(excel_dir)

# ============================================================
# 1. Import and combine all yearly CSV files (1980–2025)
# ============================================================
frames = []
for i in range(1980, 2026):
    df = pd.read_csv(f"{i}.csv", low_memory=False)
    frames.append(df)

combined = pd.concat(frames, ignore_index=True)
combined.to_stata("NWS_temp.dta", write_index=False, version=118)

# ============================================================
# 2. Prepare the FIPS crosswalk from CountyCode.dta
# ============================================================
county_code = pd.read_stata("CountyCode.dta")
county_code = county_code.drop_duplicates(subset="FIPS", keep="first")

# Keep only FIPS-related and NAME-related columns
fips_cols = [c for c in county_code.columns if "FIPS" in c or "NAME" in c]
county_code = county_code[fips_cols]

# Drop columns that were between UANAME and DISTNAME (inclusive) and NAME
# Replicate: drop UANAME-DISTNAME, drop NAME
cols_to_drop = []
if "UANAME" in county_code.columns and "DISTNAME" in county_code.columns:
    ua_idx = list(county_code.columns).index("UANAME")
    dist_idx = list(county_code.columns).index("DISTNAME")
    cols_to_drop = list(county_code.columns[ua_idx : dist_idx + 1])
if "NAME" in county_code.columns:
    cols_to_drop.append("NAME")
county_code = county_code.drop(columns=[c for c in cols_to_drop if c in county_code.columns], errors="ignore")

# Destring FIPS columns
for col in ["FIPS_ST", "FIPS_COUNTY", "FIPS"]:
    if col in county_code.columns:
        county_code[col] = pd.to_numeric(county_code[col], errors="coerce")

county_code.to_stata("FIPS.dta", write_index=False, version=118)

# ============================================================
# 3. Cleaning – merge NWS data with FIPS crosswalk
# ============================================================
nws = pd.read_stata("NWS_temp.dta")

# Rename to match the FIPS crosswalk
nws = nws.rename(columns={"state_fips": "FIPS_ST", "cz_fips": "FIPS_COUNTY"})

# Merge m:m on FIPS_ST FIPS_COUNTY (replicate Stata's merge m:m)
merged = nws.merge(county_code, on=["FIPS_ST", "FIPS_COUNTY"], how="inner")

# Generate day and rename month
merged["day"] = merged["begin_day"]
merged = merged.rename(columns={"month_name": "month"})

# Generate month number from month name
merged["temp_date"] = pd.to_datetime(
    merged["month"].astype(str) + " 1, " + merged["year"].astype(str),
    format="%B 1, %Y",
    errors="coerce",
)
merged["month_num"] = merged["temp_date"].dt.month
merged = merged.drop(columns=["temp_date"])

# Create monthly time variable (Stata's ym(): months since Jan 1960)
merged["time"] = (merged["year"] - 1960) * 12 + (merged["month_num"] - 1)

# Reorder key columns to the front
front_cols = [
    "FIPS_ST", "STATENAME", "FIPS_COUNTY", "COUNTYNAME", "FIPS",
    "time", "day", "month", "year",
    "event_id", "event_type", "tor_f_scale",
    "injuries_indirect", "deaths_direct", "deaths_indirect",
    "damage_property", "damage_crops",
]
# Only include columns that actually exist
front_cols = [c for c in front_cols if c in merged.columns]
other_cols = [c for c in merged.columns if c not in front_cols]
merged = merged[front_cols + other_cols]

# Rename FIPS -> fips
merged = merged.rename(columns={"FIPS": "fips"})

# Sort and drop duplicates
merged = merged.sort_values(["fips", "time"]).reset_index(drop=True)
merged = merged.drop_duplicates(subset=["fips", "time", "event_id"], keep="first")

# ============================================================
# 4. Parse damage_property into numeric values
# ============================================================
merged["damage_property"] = merged["damage_property"].astype(str)

# Extract last character and numeric part
merged["last_char"] = merged["damage_property"].str[-1].str.upper()
merged["num_part"] = pd.to_numeric(
    merged["damage_property"].str[:-1], errors="coerce"
)

# Create multiplier
multiplier_map = {"K": 1_000, "M": 1_000_000, "B": 1_000_000_000}
merged["multiplier"] = merged["last_char"].map(multiplier_map).fillna(1)

# Final monetary variable
merged["property_damage_value"] = merged["num_part"] * merged["multiplier"]

# Drop rows with missing/zero damage or invalid suffix
drop_mask = (
    merged["damage_property"].isna()
    | (merged["damage_property"] == "nan")
    | (merged["damage_property"] == "0.00K")
    | (merged["damage_property"] == "0")
    | (merged["damage_property"] == "0K")
    | (~merged["last_char"].isin(["K", "M", "B"]))
)
merged = merged[~drop_mask].copy()

# Clean up helper columns
merged = merged.drop(columns=["last_char", "num_part", "multiplier"])

# ============================================================
# 5. Reclassify event_type into broader categories
# ============================================================
merged["Event_Subtype"] = merged["event_type"].copy()

def classify_event(et):
    """Return reclassified event type, or original if no match."""
    up = str(et).upper()

    # Thunderstorm
    thunder_keywords = [
        "THUNDER", "THUNDERSTORM WIND/ TREE", "THUNDERSTORM WIND/ TREES",
        "THUNDERSTORM WINDS LIGHTNING", "THUNDERSTORM WINDS/ FLOOD",
        "THUNDERSTORM WINDS/FLOODING", "THUNDERSTORM WIND",
    ]
    if any(kw in up for kw in thunder_keywords):
        return "Thunderstorm"

    # Dust Storm
    if "DUST DEVIL" in up or "DUST STORM" in up:
        return "Dust Storm"

    # Hurricane (includes Storm Surge/Tide, High Surf, Marine High Wind)
    if any(kw in up for kw in ["HURRICANE", "TYPHOON", "STORM SURGE/TIDE",
                                "HIGH SURF", "MARINE HIGH WIND"]):
        return "Hurricane"

    # Winter Wave
    winter_keywords = [
        "WINTER STORM", "SLEET", "WINTER WEATHER", "ICE STORM",
        "FROST/FREEZE", "FREEZING FOG", "EXTREME COLD/WIND CHILL",
        "HEAVY SNOW", "BLIZZARD", "COLD/WIND CHILL",
    ]
    if any(kw in up for kw in winter_keywords):
        return "Winter Wave"

    # Flood
    if any(kw in up for kw in ["FLASH FLOOD", "LAKESHORE FLOOD", "COASTAL FLOOD"]):
        return "Flood"

    # Heat Wave
    if "EXCESSIVE HEAT" in up or "HEAT" in up:
        return "Heat Wave"

    return et  # no reclassification

merged["event_type"] = merged["event_type"].apply(classify_event)

# ============================================================
# 6. Keep final columns and save
# ============================================================
keep_cols = [
    "fips", "time", "Event_Subtype", "event_type", "event_id",
    "tor_f_scale", "injuries_indirect", "injuries_direct",
    "deaths_direct", "deaths_indirect",
    "property_damage_value", "damage_property", "damage_crops",
    "event_narrative",
]
keep_cols = [c for c in keep_cols if c in merged.columns]
disaster = merged[keep_cols].copy()

disaster.to_stata("Disaster_Dataset.dta", write_index=False, version=118)
disaster.to_stata(
    os.path.join(output_path, "Disaster_Dataset.dta"),
    write_index=False,
    version=118,
)

# ============================================================
# 7. Split by event type and label high/low cost events
# ============================================================
# NOTE: The Stata code loads "Disaster_Dataset_Cleaned.dta" here.
#       Adjust the filename if you have a separate cleaned version.
disaster_cleaned = pd.read_stata("Disaster_Dataset_Cleaned.dta")

events = [
    "Hurricane", "Tornado", "Tropical Storm", "Thunderstorm",
    "Flood", "Winter Wave", "Wildfire", "Hail",
]

for event in events:
    df_event = disaster_cleaned[disaster_cleaned["event_type"] == event].copy()

    if df_event.empty:
        print(f"No observations for {event}, skipping.")
        continue

    # Median property damage
    median_val = df_event["property_damage_value"].median()

    # Label high vs low cost
    df_event.insert(
        df_event.columns.get_loc("event_type") + 1,
        "event_damage_indicator",
        np.where(
            df_event["property_damage_value"] > median_val,
            "High_Cost_Event",
            "Low_Cost_Event",
        ),
    )

    # Save individual disaster file
    fname = event.replace(" ", "_")
    out_file = os.path.join(individual_disasters_path, f"{fname}.dta")
    df_event.to_stata(out_file, write_index=False, version=118)
    print(f"Saved {out_file} ({len(df_event)} obs, median={median_val:,.0f})")

print("Done.")
# End of script

"""
Python translation of Project_Datawork.do
Requires: pandas, numpy, matplotlib
"""

import os
import re
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker

# ============================================================
# Paths (adjust to match your system)
# ============================================================
data_dir = r"C:\Users\ghosh\OneDrive - University of Nebraska\2-Erdos\1-Climate Finance Project\Data\Raw Data"
fig_dir  = r"C:\Users\ghosh\OneDrive - University of Nebraska\2-Erdos\1-Climate Finance Project\Data\Figures"

os.chdir(data_dir)
os.makedirs(fig_dir, exist_ok=True)

# ============================================================
# Helper: build month-column rename mapping (v4, v5, ... → m2008_01, ...)
# ============================================================
def build_month_rename_map(start_vnum=4, full_years=range(2008, 2025),
                           partial_year=2025, partial_months=range(1, 4)):
    """
    Replicates the nested forvalues loop that renames v4, v5, ...
    to m2008_01, m2008_02, ... m2025_03.
    Returns a dict {old_name: new_name}.
    """
    rename_map = {}
    vnum = start_vnum
    for y in full_years:
        for m in range(1, 13):
            rename_map[f"v{vnum}"] = f"m{y}_{m:02d}"
            vnum += 1
    for m in partial_months:
        rename_map[f"v{vnum}"] = f"m{partial_year}_{m:02d}"
        vnum += 1
    return rename_map


# ============================================================
# Helper: clean FIPS and add Delinquency_Status column
# ============================================================
def clean_finance_csv(filepath, delinquency_label):
    df = pd.read_csv(filepath, header=0, dtype=str)
    # Rename month columns
    rename_map = build_month_rename_map()
    df = df.rename(columns=rename_map)
    # Rename Name → County
    df = df.rename(columns={"Name": "County"})
    # Clean FIPSCode: keep digits only
    df["fips"] = df["FIPSCode"].apply(lambda x: re.sub(r"[^0-9]", "", str(x)))
    df = df.drop(columns=["FIPSCode"])
    df["fips"] = pd.to_numeric(df["fips"], errors="coerce")
    # Add delinquency status
    df.insert(df.columns.get_loc("County") + 1, "Delinquency_Status", delinquency_label)
    return df


# ============================================================
# 1. Early Delinquency (30–89 days)
# ============================================================
early = clean_finance_csv("Finance_30_89_EarlyDelinquency.csv",
                          "Early_30_89Day_Delinquency")
early.to_stata("Early_30_89Day_Delinquency.dta", write_index=False, version=118)

# ============================================================
# 2. Late Delinquency (90+ days)
# ============================================================
late = clean_finance_csv("Finance_90_LateDelinquency.csv",
                         "Late_>90Day_Delinquency")
late.to_stata("Late_90Day_Delinquency.dta", write_index=False, version=118)

# ============================================================
# 3. Append both, reshape long, collapse
# ============================================================
combined = pd.concat([late, early], ignore_index=True)
combined = combined.sort_values(["fips", "Delinquency_Status"]).reset_index(drop=True)

# Identify month-value columns (m2008_01 ... m2025_03)
id_vars = [c for c in combined.columns if not c.startswith("m")]
value_vars = [c for c in combined.columns if c.startswith("m")]

# Reshape wide → long
long = combined.melt(id_vars=id_vars, value_vars=value_vars,
                     var_name="yearmonth", value_name="delinquency_rate")

# Strip the leading "m" prefix:  m2008_01 → 2008_01
long["yearmonth"] = long["yearmonth"].str.lstrip("m")

# Convert yearmonth "2008_01" → Stata monthly date (months since Jan 1960)
long["year"] = long["yearmonth"].str[:4].astype(int)
long["mon"]  = long["yearmonth"].str[5:7].astype(int)
long["time"] = (long["year"] - 1960) * 12 + (long["mon"] - 1)
long = long.drop(columns=["yearmonth", "year", "mon"])

# Destring delinquency_rate
long["delinquency_rate"] = pd.to_numeric(long["delinquency_rate"], errors="coerce")

long = long.sort_values(["fips", "Delinquency_Status", "time"]).reset_index(drop=True)

# Split into early / late columns
long["Early_Delinquency_Rate"] = np.where(
    long["Delinquency_Status"] == "Early_30_89Day_Delinquency",
    long["delinquency_rate"], np.nan
)
long["Late_Delinquency_Rate"] = np.where(
    long["Delinquency_Status"] == "Late_>90Day_Delinquency",
    long["delinquency_rate"], np.nan
)

# Collapse to one row per fips-time (mean of each rate)
finance = (
    long
    .groupby(["State", "County", "fips", "time"], as_index=False)
    .agg(Early_Delinquency_Rate=("Early_Delinquency_Rate", "mean"),
         Late_Delinquency_Rate=("Late_Delinquency_Rate", "mean"))
)
finance = finance.sort_values(["fips", "time", "State", "County"]).reset_index(drop=True)
finance = finance.drop_duplicates(subset=["fips", "time"], keep="first")

finance.to_stata("Finance_Dataset.dta", write_index=False, version=118)

# ============================================================
# 4. Handling Disaster Data — bar chart
# ============================================================
disaster = pd.read_stata("Disaster_Dataset.dta")
disaster["property_damage_billions"] = disaster["property_damage_value"] / 1e9

# Bar chart: total property damage by event type
damage_by_type = (
    disaster
    .groupby("event_type", as_index=False)["property_damage_billions"]
    .sum()
    .sort_values("property_damage_billions", ascending=False)
)

fig, ax = plt.subplots(figsize=(10, 6))
ax.bar(damage_by_type["event_type"], damage_by_type["property_damage_billions"],
       color="#3B82BA")
ax.set_ylabel("Total Property Damage Value (Billions $)")
ax.set_title("Property Damage by Disaster Type")
plt.xticks(rotation=45, ha="right")
plt.tight_layout()
fig.savefig(os.path.join(fig_dir, "Property_Damage_by_DisasterType.png"), dpi=300)
plt.close(fig)

# ============================================================
# 5. Merging Climate Data
# ============================================================
finance_clean = pd.read_stata("Finance_Cleaned.dta")
disaster_clean = pd.read_stata("Disaster_Dataset_Cleaned.dta")

# merge m:m fips time (inner-like, then drop _merge==2)
master = finance_clean.merge(disaster_clean, on=["fips", "time"], how="left")

master = master.drop_duplicates(subset=["fips", "time"], keep="first")

# Event_Occur indicator
master["Event_Occur"] = np.where(master["event_type"].notna(), 1, 0)

# ---- Contamination filter: drop counties with repeat events within 12 months ----
master = master.sort_values(["fips", "time"]).reset_index(drop=True)

events = master[master["Event_Occur"] == 1].copy()
events = events.sort_values(["fips", "time"])

# Time to next / previous event within each county
events["time_to_next"] = events.groupby("fips")["time"].shift(-1) - events["time"]
events["time_to_prev"] = events["time"] - events.groupby("fips")["time"].shift(1)

events["contaminated"] = (
    ((events["time_to_next"] <= 12) & events["time_to_next"].notna()) |
    ((events["time_to_prev"] <= 12) & events["time_to_prev"].notna())
).astype(int)

contaminated_fips = set(events.loc[events["contaminated"] == 1, "fips"])
master = master[~master["fips"].isin(contaminated_fips)].copy()

# ---- Merge auxiliary county datasets ----
county_area = pd.read_stata("County_Area.dta")
master = master.merge(county_area, on="fips", how="inner")

coastal = pd.read_stata("Coastal_Counties.dta")
master = master.merge(coastal, on="fips", how="left")

coast_dist = pd.read_stata("County_CoastDist.dta")
master = master.merge(coast_dist, on="fips", how="inner")

master = master.drop_duplicates(subset=["fips", "time"], keep="first")

# Coastal indicator
master["Coastal_County"] = np.where(
    master["COASTLINEREGION"].notna(), "Coastal", "Non-Coastal"
)

# ---- Event damage indicator (high/low cost by median within event type) ----
master["Event_Damage_Indicator"] = ""

events_list = [
    "Hurricane", "Tornado", "Tropical Storm", "Thunderstorm",
    "Flood", "Winter Wave", "Wildfire", "Hail",
]

for event in events_list:
    mask = master["event_type"] == event
    if mask.sum() == 0:
        continue
    med = master.loc[mask, "property_damage_value"].median()
    master.loc[mask & (master["property_damage_value"] > med),
               "Event_Damage_Indicator"] = "High_Cost_Event"
    master.loc[mask & (master["property_damage_value"] <= med),
               "Event_Damage_Indicator"] = "Low_Cost_Event"

# ---- Drop / rename columns ----
drop_cols = ["COUNTYNAME", "STATENAME", "stateFIPS", "countyFIPS", "county", "state"]
master = master.drop(columns=[c for c in drop_cols if c in master.columns], errors="ignore")

if "COASTLINEREGION" in master.columns:
    master = master.rename(columns={"COASTLINEREGION": "Coastline_Region"})
if "tor_f_scale" in master.columns:
    master = master.rename(columns={"tor_f_scale": "Tornado_Intensity_Scale"})

# Lowercase all columns, then Proper-case, then fix fips/time back to lower
master.columns = master.columns.str.lower()
master.columns = master.columns.str.title()
master = master.rename(columns={"Fips": "fips", "Time": "time"})

master.to_stata("Finance_Disaster_Master.dta", write_index=False, version=118)

# ============================================================
# 6. EDA — Event Study Plots by Event Type
# ============================================================
# NOTE: The Stata code loads "Finance_Disaster.dta" inside the loop.
#       Adjust filename if yours differs (e.g., "Finance_Disaster_Master.dta").

for event in events_list:
    base = pd.read_stata("Finance_Disaster.dta")

    fname = event.replace(" ", "_")

    # Identify treated counties
    base["treated"] = (
        (base["Event_Type"] == event) & (base["Event_Occur"] == 1)
    ).astype(int)
    base["Treated_Ever"] = base.groupby("fips")["treated"].transform("max")

    # Keep only states that contain at least one treated county
    base["State_Treated"] = base.groupby("State")["Treated_Ever"].transform("max")
    base = base[base["State_Treated"] == 1].drop(columns=["State_Treated"])

    # Get the earliest event time per treated county
    base["event_time"] = np.where(base["treated"] == 1, base["time"], np.nan)
    base["Event_Time"] = base.groupby("fips")["event_time"].transform("min")
    base = base.drop(columns=["event_time", "treated"])

    # Relative time
    base["Rel_Time"] = base["time"] - base["Event_Time"]

    # Keep treated within ±12 months, keep all controls
    base = base[
        ((base["Treated_Ever"] == 1) & (base["Rel_Time"].between(-12, 12))) |
        (base["Treated_Ever"] == 0)
    ].copy()

    # ---- Stacked cohort design ----
    etimes = (
        base
        .loc[base["Treated_Ever"] == 1, "Event_Time"]
        .dropna()
        .unique()
    )

    stacked_frames = []
    for et in etimes:
        sub = base[
            ((base["Treated_Ever"] == 1) & (base["Event_Time"] == et)) |
            (base["Treated_Ever"] == 0)
        ].copy()
        # For controls, compute relative time around this cohort's event date
        sub.loc[sub["Treated_Ever"] == 0, "Rel_Time"] = sub.loc[sub["Treated_Ever"] == 0, "time"] - et
        sub = sub[sub["Rel_Time"].between(-12, 12)].copy()
        sub["cohort"] = et
        stacked_frames.append(sub)

    if not stacked_frames:
        print(f"No stacked data for {event}, skipping plots.")
        continue

    stacked = pd.concat(stacked_frames, ignore_index=True)
    stacked = stacked.drop_duplicates(subset=["fips", "time", "cohort"], keep="first")

    # ---- Plot both delinquency rates ----
    for depvar in ["Early_Delinquency_Rate", "Late_Delinquency_Rate"]:
        if depvar not in stacked.columns:
            continue

        agg = (
            stacked
            .groupby(["Rel_Time", "Treated_Ever"], as_index=False)[depvar]
            .mean()
        )

        fig, ax = plt.subplots(figsize=(10, 5))

        treated_data = agg[agg["Treated_Ever"] == 1].sort_values("Rel_Time")
        control_data = agg[agg["Treated_Ever"] == 0].sort_values("Rel_Time")

        ax.plot(treated_data["Rel_Time"], treated_data[depvar],
                color="blue", linewidth=1.8, linestyle="-", label="Treated")
        ax.plot(control_data["Rel_Time"], control_data[depvar],
                color="green", linewidth=1.2, linestyle="--", label="Control")

        ax.axvline(x=0, color="red", linestyle="--", linewidth=0.8)
        ax.set_xlabel("Months to Event")
        ax.set_ylabel(depvar)
        ax.set_title(event)
        ax.set_xticks(range(-12, 13))
        ax.legend(loc="upper center", ncol=2, frameon=False)
        ax.set_facecolor("white")
        fig.patch.set_facecolor("white")

        plt.tight_layout()
        fig.savefig(os.path.join(fig_dir, f"{fname}_{depvar}.png"), dpi=300)
        plt.close(fig)

    print(f"Plots saved for {event}")

print("Done.")
# End of script