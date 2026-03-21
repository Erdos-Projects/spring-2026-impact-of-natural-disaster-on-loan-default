"""Utility functions for climate finance analysis."""

import os
from typing import Any

import git
import pandas as pd

from climatefinance.constants import (
    ANALYSIS_FILE,
    ANALYSIS_FOLDER,
    DISASTER_FILE,
    FINANCE_FILE,
    INFERENCE_FILE,
    MODELING_FILE,
    TARGET_TYPES,
)


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


# ---------------------------------------------------------------------------
# Generic save / load
# ---------------------------------------------------------------------------


def save_analysis(
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


def load_analysis(
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


# ---------------------------------------------------------------------------
# Specialized save / load for each output file
# ---------------------------------------------------------------------------


def save_analysis_data(df: pd.DataFrame, **kwargs: Any) -> None:
    """Save the main analysis panel (finance + disaster)."""
    save_analysis(df, ANALYSIS_FILE, **kwargs)


def load_analysis_data(**kwargs: Any) -> pd.DataFrame:
    """Load the main analysis panel (finance + disaster)."""
    return load_analysis(ANALYSIS_FILE, **kwargs)


def save_analysis_inference(df: pd.DataFrame, **kwargs: Any) -> None:
    """Save inference results."""
    save_analysis(df, INFERENCE_FILE, **kwargs)


def load_analysis_inference(**kwargs: Any) -> pd.DataFrame:
    """Load inference results."""
    return load_analysis(INFERENCE_FILE, **kwargs)


def save_analysis_modeling(df: pd.DataFrame, **kwargs: Any) -> None:
    """Save modeling results."""
    save_analysis(df, MODELING_FILE, **kwargs)


def load_analysis_modeling(**kwargs: Any) -> pd.DataFrame:
    """Load modeling results."""
    return load_analysis(MODELING_FILE, **kwargs)


# ---------------------------------------------------------------------------
# PanelOLS result extraction
# ---------------------------------------------------------------------------


def extract_panel_results(
    result: Any,
    model: str,
    outcome: str,
) -> list[dict[str, Any]]:
    """Extract key coefficients from a PanelOLS result into a list of dicts.

    Returns one dict per regressor with model name, outcome, coefficient,
    standard error, p-value, number of observations, and R².
    """
    rows: list[dict[str, Any]] = []
    for regressor in result.params.index:
        rows.append(
            {
                "model": model,
                "outcome": outcome,
                "regressor": regressor,
                "coef": result.params[regressor],
                "se": result.std_errors[regressor],
                "pvalue": result.pvalues[regressor],
                "nobs": result.nobs,
                "r2": result.rsquared,
            }
        )
    return rows
