#Libraries
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import re
from pathlib import Path
import os


def prepare_monthly_panel(df, time_col="time", fips_col="fips"):
    """
    Returns a copy of df with:
    - parsed datetime column
    - month column normalized to month start
    - fips as string
    """
    out = df.copy()

    # Parse time
    out[time_col] = pd.to_datetime(out[time_col], errors="coerce")

    # FIPS as string (important to avoid dropping leading zeros)
    out[fips_col] = out[fips_col].astype(str).str.zfill(5)

    # Monthly time index
    out["month"] = out[time_col].dt.to_period("M").dt.to_timestamp()

    return out


# -----------------------------
def panel_diagnostics(df, fips_col="fips", month_col="month", name="dataset"):
    """
    Checks:
    - how many unique counties?
    - how many time periods?
    - is the panel balanced?
    - are there duplicate county-month rows?
    - are there missing months for some counties?
    """
    print(f"\n{'=' * 60}")
    print(f"Diagnostics for: {name}")
    print(f"{'=' * 60}")

    # Drop rows with missing county or month for diagnostics
    d = df.dropna(subset=[fips_col, month_col]).copy()

    # 1) Unique counties
    n_counties = d[fips_col].nunique()
    print(f"Unique counties: {n_counties}")

    # 2) Unique time periods
    n_periods = d[month_col].nunique()
    print(f"Unique time periods: {n_periods}")
    print(f"Date range: {d[month_col].min()} to {d[month_col].max()}")

    # 3) Duplicate county-month rows
    county_month_counts = d.groupby([fips_col, month_col]).size().rename("n_rows").reset_index()
    duplicates = county_month_counts[county_month_counts["n_rows"] > 1].sort_values("n_rows", ascending=False)

    print(f"Duplicate county-month rows: {len(duplicates)}")
    if len(duplicates) > 0:
        print("Top duplicate county-month combinations:")
        print(duplicates.head(10))

    # 4) Balanced panel check
    # For a strictly balanced panel, each county should appear in every month
    obs_per_county = d.drop_duplicates([fips_col, month_col]).groupby(fips_col)[month_col].nunique()
    balanced = obs_per_county.eq(n_periods).all()

    print(f"Balanced panel? {balanced}")
    print("Observation counts per county:")
    print(obs_per_county.describe())

    # 5) Missing months by county
    all_counties = d[fips_col].drop_duplicates().sort_values()
    all_months = pd.Series(pd.date_range(d[month_col].min(), d[month_col].max(), freq="MS"), name=month_col)

    full_index = pd.MultiIndex.from_product(
        [all_counties, all_months],
        names=[fips_col, month_col]
    )

    observed_index = d.drop_duplicates([fips_col, month_col]).set_index([fips_col, month_col]).index
    missing_index = full_index.difference(observed_index)

    missing_months = pd.DataFrame(index=missing_index).reset_index()
    print(f"Total missing county-month combinations: {len(missing_months)}")

    if len(missing_months) > 0:
        missing_summary = missing_months.groupby(fips_col).size().rename("n_missing_months").sort_values(
            ascending=False)
        print("Counties with most missing months:")
        print(missing_summary.head(10))
    else:
        missing_summary = pd.Series(dtype=int, name="n_missing_months")

    return {
        "n_counties": n_counties,
        "n_periods": n_periods,
        "balanced": balanced,
        "duplicates": duplicates,
        "missing_months": missing_months,
        "missing_summary": missing_summary,
        "obs_per_county": obs_per_county,
    }


# Disaster repetition check
# -----------------------------
def disaster_county_month_check(disaster_df, fips_col="fips", month_col="month", event_col="event_type"):
    """
    Checks whether multiple disasters occur in the same county-month.
    """
    d = disaster_df.dropna(subset=[fips_col, month_col]).copy()

    county_month_event_counts = (
        d.groupby([fips_col, month_col])
        .size()
        .rename("n_disasters")
        .reset_index()
        .sort_values("n_disasters", ascending=False)
    )

    multiple_disasters = county_month_event_counts[county_month_event_counts["n_disasters"] > 1]

    print(f"\n{'=' * 60}")
    print("Disaster county-month repetition check")
    print(f"{'=' * 60}")
    print(f"County-months with >1 disaster row: {len(multiple_disasters)}")

    if len(multiple_disasters) > 0:
        print("Top county-months with multiple disasters:")
        print(multiple_disasters.head(10))

    # Optional: see which event types co-occur in those county-months
    if len(multiple_disasters) > 0 and event_col in d.columns:
        merged = multiple_disasters.head(10).merge(
            d[[fips_col, month_col, event_col]],
            on=[fips_col, month_col],
            how="left"
        )
        print("\nExample event types in repeated county-months:")
        print(merged.sort_values([fips_col, month_col]))

    return {
        "county_month_event_counts": county_month_event_counts,
        "multiple_disasters": multiple_disasters
    }


#  Optional filtering for relevant disasters
# -----------------------------
def filter_target_disasters(disaster_df, damage_col="damage_property"):
    """
    Restrict to the disaster types you mentioned and optionally damage >= 500k.
    Adjust event labels if needed to match your actual data.
    """
    target_events = [
        "Hurricane",
        "Tornado",
        "Tropical Storm",
        "Thunderstorm",
        "Flood",
        "Winter Weather",
        "Wildfire",
        "Hail"
    ]

    d = disaster_df.copy()

    # Standardize event_type a bit
    d["event_type"] = d["event_type"].astype(str).str.strip()

    # Keep only target events
    d = d[d["event_type"].isin(target_events)].copy()

    # If damage is already numeric, this works directly
    if damage_col in d.columns:
        d[damage_col] = pd.to_numeric(d[damage_col], errors="coerce")
        d = d[d[damage_col] >= 500_000]

    return d


def parse_damage(x):
    """
    Converts strings to numeric dollars.
    Examples:
        '25K' -> 25000
        '3.5M' -> 3500000
        '1B' -> 1000000000
        500000 -> 500000
    """
    if pd.isna(x):
        return np.nan

    if isinstance(x, (int, float, np.integer, np.floating)):
        return float(x)

    x = str(x).strip().upper().replace(",", "")

    if x in ["", "0", "0.00"]:
        return 0.0

    multipliers = {
        "K": 1_000,
        "M": 1_000_000,
        "B": 1_000_000_000
    }

    last = x[-1]
    if last in multipliers:
        try:
            return float(x[:-1]) * multipliers[last]
        except:
            return np.nan
    else:
        try:
            return float(x)
        except:
            return np.nan


def normalize_event_type(x):
    """
    Maps raw event labels into broader categories for your project.
    Adjust as needed after inspecting unique labels.
    """
    if pd.isna(x):
        return np.nan

    x = str(x).strip().lower()

    # Hurricane / tropical
    if "hurricane" in x:
        return "Hurricane"
    if "tropical storm" in x:
        return "Tropical Storm"

    # Tornado
    if "tornado" in x:
        return "Tornado"

    # Flood family
    if "flash flood" in x or x == "flood" or "coastal flood" in x:
        return "Flood"

    # Thunderstorm family
    if "thunderstorm" in x:
        return "Thunderstorm"

    # Winter weather family
    if "winter storm" in x or "winter weather" in x or "cold/wind chill" in x or "extreme cold" in x:
        return "Winter Weather"

    # Wildfire
    if "wildfire" in x:
        return "Wildfire"

    # Hail
    if "hail" in x:
        return "Hail"

    return "Other"

