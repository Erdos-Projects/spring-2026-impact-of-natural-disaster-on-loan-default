import pandas as pd
import re
from pathlib import Path

def parse_damage(x):
    """Convert a human-readable damage string (e.g. '10K', '2.5M', '1B') to numeric USD.

    Suffixes: K → 1e3, M → 1e6, B → 1e9, none → 1.
    Returns pd.NA for missing or unparseable values.
    """
    if pd.isna(x):
        return pd.NA
    s = str(x).strip().upper()
    if not s:                       # empty / whitespace-only → missing
        return pd.NA
    m = re.match(r"^(\d+\.?\d*|\.\d+)\s*([KMB])?$", s)
    if not m:
        return pd.NA
    val = float(m.group(1))
    suf = m.group(2)
    mult = {"K": 1e3, "M": 1e6, "B": 1e9, None: 1.0}[suf]
    return val * mult


def process_disaster_data(disaster_data: pd.DataFrame) -> pd.DataFrame:
    """Clean non-numeric FIPS rows, parse damage columns, and add numeric USD equivalents."""
    # Drop rows where FIPS_ST is not a valid number
    before = len(disaster_data)

    # disaster_data["FIPS_ST"] = pd.to_numeric(disaster_data["FIPS_ST"], errors="coerce")
    # disaster_data = disaster_data.dropna(subset=["FIPS_ST"])
    # disaster_data["FIPS_ST"] = disaster_data["FIPS_ST"].astype(int)
    # print(f"Dropped {before - len(disaster_data)} rows with non-numeric FIPS_ST")

    mask = disaster_data["FIPS_ST"].astype(str).str.strip().str.isdigit()
    disaster_data = disaster_data[mask]
    disaster_data["FIPS_ST"] = disaster_data["FIPS_ST"].astype(int)
    print(f"Dropped {before - len(disaster_data)} rows with non-numeric FIPS_ST")

    for col in ["damage_property", "damage_crops"]:
        if col in disaster_data.columns:
            disaster_data[col + "_usd"] = (
                disaster_data[col]
                .map(parse_damage)
                .astype("Float64")          # nullable float – uses pd.NA, not np.nan
            )
            print(f"\n── {col}_usd summary ──")
            print(disaster_data[col + "_usd"].describe(
                percentiles=[0.5, 0.9, 0.95, 0.99]
            ))
    return disaster_data


def main():
    """Load disaster data, process damage columns, and save to CSV."""
    # Load the dataset
    path_data = Path("./data")

    path_disaster = path_data / "1-Disaster"
    # path_finance = path_data / "2-Finance"

    path_disaster_processed = path_data / "1-Disaster_processed"

    #disaster data
    disaster_data = pd.read_stata(path_disaster / "Disaster_Dataset_Cleaned.dta")
    print(disaster_data.shape)  # (339457, 57)
    print(disaster_data.head())

    # Process damage columns
    disaster_data = process_disaster_data(disaster_data)

    # Convert all columns to pandas nullable dtypes so every missing value is
    # pd.NA (not a mix of np.nan, None, NaT, etc.) and writes out uniformly.
    disaster_data = disaster_data.convert_dtypes()

    disaster_data.to_csv(path_disaster_processed / "Disaster_Dataset_Cleaned_v2.csv", na_rep="NA", index=False)





if __name__ == "__main__":
    main()
