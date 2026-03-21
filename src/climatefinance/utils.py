"""Utility functions for climate finance analysis."""

import os

import git
import pandas as pd

FINANCE_FILE = "data/finance/finance_disaster_master.dta"
DISASTER_FILE = "data/disaster/disaster_dataset_cleaned.dta"


def get_repo_root() -> str:
    """Return the git repository root directory."""
    return str(git.Repo(os.getcwd(), search_parent_directories=True).working_dir)


def read_dta(filepath: str) -> pd.DataFrame:
    """Read a Stata .dta file relative to the repo root."""
    repo_root = get_repo_root()
    df: pd.DataFrame = pd.read_stata(repo_root + "/" + filepath)
    return df


def get_disaster_data(filepath: str = DISASTER_FILE) -> pd.DataFrame:
    """Load the cleaned NOAA disaster dataset."""
    return read_dta(filepath)


def get_finance_data(filepath: str = FINANCE_FILE) -> pd.DataFrame:
    """Load the county × month mortgage delinquency panel."""
    return read_dta(filepath)
