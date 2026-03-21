"""Preprocessing pipeline for merging NOAA disaster events with county-level delinquency data."""

import numpy as np
import pandas as pd

TARGET_EVENTS = [
    "Hurricane",
    "Tornado",
    "Tropical Storm",
    "Thunderstorm",
    "Flood",
    "Winter Weather",
    "Wildfire",
    "Hail",
]


def prepare_monthly_panel(
    df: pd.DataFrame,
    time_col: str = "time",
    fips_col: str = "fips",
) -> pd.DataFrame:
    """Return a copy with parsed datetime, month-start column, and zero-padded FIPS."""
    out = df.copy()
    out[time_col] = pd.to_datetime(out[time_col], errors="coerce")
    out[fips_col] = out[fips_col].astype(str).str.zfill(5)
    out["month"] = out[time_col].dt.to_period("M").dt.to_timestamp()
    return out


def panel_diagnostics(
    df: pd.DataFrame,
    fips_col: str = "fips",
    month_col: str = "month",
    name: str = "dataset",
) -> dict:
    """Check panel balance, duplicates, and missing county-month combinations."""
    print(f"\n{'=' * 60}")
    print(f"Diagnostics for: {name}")
    print(f"{'=' * 60}")

    d = df.dropna(subset=[fips_col, month_col]).copy()

    n_counties = d[fips_col].nunique()
    print(f"Unique counties: {n_counties}")

    n_periods = d[month_col].nunique()
    print(f"Unique time periods: {n_periods}")
    print(f"Date range: {d[month_col].min()} to {d[month_col].max()}")

    county_month_counts = d.groupby([fips_col, month_col]).size().rename("n_rows").reset_index()  # ty: ignore[no-matching-overload]
    duplicates = county_month_counts[county_month_counts["n_rows"] > 1].sort_values(
        "n_rows", ascending=False
    )

    print(f"Duplicate county-month rows: {len(duplicates)}")
    if len(duplicates) > 0:
        print("Top duplicate county-month combinations:")
        print(duplicates.head(10))

    obs_per_county = d.drop_duplicates([fips_col, month_col]).groupby(fips_col)[month_col].nunique()
    balanced = obs_per_county.eq(n_periods).all()

    print(f"Balanced panel? {balanced}")
    print("Observation counts per county:")
    print(obs_per_county.describe())

    all_counties = d[fips_col].drop_duplicates().sort_values()
    all_months = pd.Series(
        pd.date_range(d[month_col].min(), d[month_col].max(), freq="MS"),
        name=month_col,
    )

    full_index = pd.MultiIndex.from_product([all_counties, all_months], names=[fips_col, month_col])
    observed_index = d.drop_duplicates([fips_col, month_col]).set_index([fips_col, month_col]).index
    missing_index = full_index.difference(observed_index)

    missing_months = pd.DataFrame(index=missing_index).reset_index()
    print(f"Total missing county-month combinations: {len(missing_months)}")

    if len(missing_months) > 0:
        missing_summary = (
            missing_months.groupby(fips_col)
            .size()
            .rename("n_missing_months")  # ty: ignore[no-matching-overload]
            .sort_values(ascending=False)
        )
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


def disaster_county_month_check(
    disaster_df: pd.DataFrame,
    fips_col: str = "fips",
    month_col: str = "month",
    event_col: str = "event_type",
) -> dict:
    """Check whether multiple disasters occur in the same county-month."""
    d = disaster_df.dropna(subset=[fips_col, month_col]).copy()

    county_month_event_counts = (
        d.groupby([fips_col, month_col])
        .size()
        .rename("n_disasters")  # ty: ignore[no-matching-overload]
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

    if len(multiple_disasters) > 0 and event_col in d.columns:
        merged = multiple_disasters.head(10).merge(
            d[[fips_col, month_col, event_col]],
            on=[fips_col, month_col],
            how="left",
        )
        print("\nExample event types in repeated county-months:")
        print(merged.sort_values([fips_col, month_col]))

    return {
        "county_month_event_counts": county_month_event_counts,
        "multiple_disasters": multiple_disasters,
    }


def filter_target_disasters(
    disaster_df: pd.DataFrame,
    damage_col: str = "damage_property",
) -> pd.DataFrame:
    """Keep only target disaster types with damage >= $500k."""
    d = disaster_df.copy()
    d["event_type"] = d["event_type"].astype(str).str.strip()
    d = d[d["event_type"].isin(TARGET_EVENTS)].copy()

    if damage_col in d.columns:
        d[damage_col] = pd.to_numeric(d[damage_col], errors="coerce")
        d = d[d[damage_col] >= 500_000]

    return d


_DAMAGE_MULTIPLIERS = {"K": 1_000, "M": 1_000_000, "B": 1_000_000_000}


def parse_damage(x: object) -> float:
    """Convert NOAA damage strings (e.g. '25K', '3.5M', '1B') to numeric dollars."""
    if pd.isna(x):
        return np.nan

    if isinstance(x, (int, float, np.integer, np.floating)):
        return float(x)

    s = str(x).strip().upper().replace(",", "")

    if s in ("", "0", "0.00"):
        return 0.0

    last = s[-1]
    if last in _DAMAGE_MULTIPLIERS:
        try:
            return float(s[:-1]) * _DAMAGE_MULTIPLIERS[last]
        except ValueError:
            return np.nan
    try:
        return float(s)
    except ValueError:
        return np.nan


_EVENT_RULES: list[tuple[str, str]] = [
    ("hurricane", "Hurricane"),
    ("tropical storm", "Tropical Storm"),
    ("tornado", "Tornado"),
    ("flash flood", "Flood"),
    ("coastal flood", "Flood"),
    ("flood", "Flood"),
    ("thunderstorm", "Thunderstorm"),
    ("winter storm", "Winter Weather"),
    ("winter weather", "Winter Weather"),
    ("cold/wind chill", "Winter Weather"),
    ("extreme cold", "Winter Weather"),
    ("wildfire", "Wildfire"),
    ("hail", "Hail"),
]


def normalize_event_type(x: object) -> str | float:
    """Map raw NOAA event labels into 8 broad categories (or 'Other')."""
    if pd.isna(x):
        return np.nan

    lowered = str(x).strip().lower()
    for keyword, category in _EVENT_RULES:
        if keyword in lowered:
            return category
    return "Other"
