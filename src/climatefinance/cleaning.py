"""Data cleaning utilities for the upstream Stata-to-Python pipeline."""

import pandas as pd

from climatefinance.preprocessing import parse_damage

_DAMAGE_SUFFIXES = frozenset(("K", "M", "B"))
_ZERO_VALUES = frozenset(("0.00K", "0", "0K"))


def parse_damage_column(series: pd.Series) -> pd.Series:
    """Vectorized damage parsing for a column of NOAA damage strings.

    Applies ``parse_damage`` row-by-row, then drops rows that had
    missing, zero, or unparseable values. Returns the numeric series
    (caller should assign it back to the DataFrame).
    """
    result: pd.Series = series.apply(parse_damage)
    return result


def drop_invalid_damage_rows(df: pd.DataFrame, col: str = "damage_property") -> pd.DataFrame:
    """Drop rows with missing, zero, or non-K/M/B damage strings."""
    raw = df[col].astype(str)
    last_char = raw.str[-1].str.upper()
    drop_mask = (
        raw.isna() | (raw == "nan") | raw.isin(_ZERO_VALUES) | (~last_char.isin(_DAMAGE_SUFFIXES))
    )
    return df[~drop_mask].copy()


_THUNDER_KEYWORDS = [
    "THUNDER",
    "THUNDERSTORM WIND/ TREE",
    "THUNDERSTORM WIND/ TREES",
    "THUNDERSTORM WINDS LIGHTNING",
    "THUNDERSTORM WINDS/ FLOOD",
    "THUNDERSTORM WINDS/FLOODING",
    "THUNDERSTORM WIND",
]

_HURRICANE_KEYWORDS = [
    "HURRICANE",
    "TYPHOON",
    "STORM SURGE/TIDE",
    "HIGH SURF",
    "MARINE HIGH WIND",
]

_WINTER_KEYWORDS = [
    "WINTER STORM",
    "SLEET",
    "WINTER WEATHER",
    "ICE STORM",
    "FROST/FREEZE",
    "FREEZING FOG",
    "EXTREME COLD/WIND CHILL",
    "HEAVY SNOW",
    "BLIZZARD",
    "COLD/WIND CHILL",
]

_FLOOD_KEYWORDS = ["FLASH FLOOD", "LAKESHORE FLOOD", "COASTAL FLOOD"]

_EVENT_RULES: list[tuple[list[str], str]] = [
    (_THUNDER_KEYWORDS, "Thunderstorm"),
    (["DUST DEVIL", "DUST STORM"], "Dust Storm"),
    (_HURRICANE_KEYWORDS, "Hurricane"),
    (_WINTER_KEYWORDS, "Winter Wave"),
    (_FLOOD_KEYWORDS, "Flood"),
    (["EXCESSIVE HEAT", "HEAT"], "Heat Wave"),
]


def classify_event(et: object) -> str:
    """Classify a raw NOAA event label into a broad category.

    Uses the same keyword rules as the original Stata cleaning pipeline.
    Categories: Thunderstorm, Dust Storm, Hurricane, Winter Wave, Flood,
    Heat Wave. Unmatched labels are returned as-is.
    """
    up = str(et).upper()
    for keywords, category in _EVENT_RULES:
        if any(kw in up for kw in keywords):
            return category
    return str(et)
