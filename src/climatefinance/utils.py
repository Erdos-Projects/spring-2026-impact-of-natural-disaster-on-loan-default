"""Utility functions for climate finance analysis."""

import os
from typing import Any

import git
import pandas as pd

# Constant to be used
FINANCE_FILE = "data/finance/finance_disaster_master.dta"
DISASTER_FILE = "data/disaster/disaster_dataset_cleaned.dta"
ANALYSIS_FOLDER = "data/analysis"
TARGET_TYPES = [
    "Hurricane",
    "Tornado",
    "Tropical Storm",
    "Thunderstorm",
    "Flood",
    "Winter Weather",
    "Wildfire",
    "Hail",
]


def get_repo_root() -> str:
    """Return the git repository root directory."""
    return str(git.Repo(os.getcwd(), search_parent_directories=True).working_dir)


def read_dta(filepath: str) -> pd.DataFrame:
    """Read a Stata .dta file relative to the repo root."""
    path = os.path.join(get_repo_root(), filepath)
    df: pd.DataFrame = pd.read_stata(path)  # ty: ignore[invalid-assignment]
    print(f"Loaded {len(df)} rows from {filepath}")
    return df


def get_disaster_data(filepath: str = DISASTER_FILE) -> pd.DataFrame:
    """Load the cleaned NOAA disaster dataset."""
    return read_dta(filepath)


def get_finance_data(filepath: str = FINANCE_FILE) -> pd.DataFrame:
    """Load the county × month mortgage delinquency panel."""
    return read_dta(filepath)


def get_target_types() -> list:
    """Return list of strings with pre-defined disaster types"""
    return TARGET_TYPES


def save_analysis_data(
    df: pd.DataFrame,
    filename: str,
    subdir: str = ANALYSIS_FOLDER,
    **kwargs: Any,
) -> None:
    """Save a DataFrame as CSV to repo_root/subdir/filename.csv."""
    path = os.path.join(get_repo_root(), subdir, f"{filename}.csv")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    df.to_csv(path, **kwargs)
    rel_path = os.path.join(subdir, f"{filename}.csv")
    print(f"Saved {len(df)} rows to {rel_path}")


def load_analysis_data(
    filename: str,
    subdir: str = ANALYSIS_FOLDER,
    **kwargs: Any,
) -> pd.DataFrame:
    """Load a CSV from repo_root/subdir/filename.csv."""
    path = os.path.join(get_repo_root(), subdir, f"{filename}.csv")
    df: pd.DataFrame = pd.read_csv(path, **kwargs)
    rel_path = os.path.join(subdir, f"{filename}.csv")
    print(f"Loaded {len(df)} rows from {rel_path}")
    return df
