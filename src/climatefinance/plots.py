"""Plotting functions for climate finance analysis."""

import os

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns

from climatefinance.constants import EDA_FOLDER, FIGURE_FOLDER, MODEL_FOLDER, TARGET_TYPES
from climatefinance.utils import get_repo_root


def _savefig(fig: plt.Figure, name: str, subfolder: str = EDA_FOLDER) -> None:
    """Save figure to FIGURE_FOLDER/<subfolder>/<name>.png."""
    rel_dir = os.path.join(FIGURE_FOLDER, subfolder)
    out_dir = os.path.join(get_repo_root(), rel_dir)
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, f"{name}.png")
    fig.savefig(path, dpi=150, bbox_inches="tight")
    print(f"Saved {os.path.join(rel_dir, name)}.png")


def plot_eda_disaster_frequency(df: pd.DataFrame) -> plt.Figure:
    """Histogram of disaster counts per treated county-month."""
    x = df.loc[df["event_occur"] == 1, "n_disasters"].dropna()
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.hist(x, bins=np.arange(x.min(), x.max() + 2) - 0.5, edgecolor="black")
    ax.set_xlabel("Number of Disasters")
    ax.set_ylabel("Frequency")
    ax.set_title("Disasters per Treated County-Month")
    ax.set_xticks(range(int(x.min()), int(x.max()) + 1))
    _savefig(fig, "disaster_frequency")
    return fig


def plot_eda_delinquency_over_time(df: pd.DataFrame) -> plt.Figure:
    """Average early and late delinquency rates over time."""
    monthly_avg = df.groupby("month")[["Early_Delinquency_Rate", "Late_Delinquency_Rate"]].mean()

    fig, axes = plt.subplots(2, 1, figsize=(10, 8), sharex=True)

    axes[0].plot(monthly_avg.index, monthly_avg["Early_Delinquency_Rate"])
    axes[0].set_ylabel("Early Delinquency Rate")
    axes[0].set_title("Average Early Delinquency Rate Over Time")

    axes[1].plot(monthly_avg.index, monthly_avg["Late_Delinquency_Rate"])
    axes[1].set_ylabel("Late Delinquency Rate")
    axes[1].set_title("Average Late Delinquency Rate Over Time")
    axes[1].set_xlabel("Month")

    fig.tight_layout()
    _savefig(fig, "delinquency_over_time")
    return fig


def plot_eda_damage_distribution(df: pd.DataFrame) -> plt.Figure:
    """Histogram of log(1 + total_damage) for treated county-months."""
    treated_damage = df.loc[df["event_occur"] == 1, "total_damage"]

    fig, ax = plt.subplots(figsize=(8, 5))
    ax.hist(np.log1p(treated_damage), bins=40, edgecolor="black")
    ax.set_title("Distribution of log(1 + Total Damage)")
    ax.set_xlabel("log(1 + total_damage)")
    ax.set_ylabel("Frequency")
    _savefig(fig, "damage_distribution")
    return fig


def plot_eda_delinquency_by_treatment(df: pd.DataFrame) -> plt.Figure:
    """Violin plots of delinquency rates by treatment status."""
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))

    sns.violinplot(
        data=df,
        x="event_occur",
        y="Early_Delinquency_Rate",
        ax=axes[0],
        cut=0,
    )
    axes[0].set_title("Early Delinquency by Treatment Status")

    sns.violinplot(
        data=df,
        x="event_occur",
        y="Late_Delinquency_Rate",
        ax=axes[1],
        cut=0,
    )
    axes[1].set_title("Late Delinquency by Treatment Status")

    fig.tight_layout()
    _savefig(fig, "delinquency_by_treatment")
    return fig


def plot_eda_treatment_rate(df: pd.DataFrame) -> plt.Figure:
    """Monthly and yearly share of treated county-months."""
    monthly_treat = df.groupby("month")["event_occur"].mean()
    yearly_treat = df.groupby(df["month"].dt.year)["event_occur"].mean()

    fig, axes = plt.subplots(2, 1, figsize=(10, 8))

    axes[0].plot(monthly_treat.index, monthly_treat.values)
    axes[0].set_title("Monthly Share of Counties with a Qualifying Disaster")
    axes[0].set_ylabel("Treated Share")
    axes[0].set_xlabel("Month")

    axes[1].bar(yearly_treat.index, yearly_treat.values)
    axes[1].set_title("Yearly Share of Treated County-Months")
    axes[1].set_ylabel("Treated Share")
    axes[1].set_xlabel("Year")

    fig.tight_layout()
    _savefig(fig, "treatment_rate")
    return fig


def _build_event_study(df: pd.DataFrame) -> pd.DataFrame:
    """Add first_treat_month and event_time columns."""
    out = df.copy()
    first_treat = (
        out.loc[out["event_occur"] == 1].groupby("fips")["month"].min().rename("first_treat_month")
    )
    out = out.merge(first_treat, on="fips", how="left")
    out["event_time"] = (out["month"].dt.year - out["first_treat_month"].dt.year) * 12 + (
        out["month"].dt.month - out["first_treat_month"].dt.month
    )
    return out


def plot_eda_event_study_raw(df: pd.DataFrame, window: int = 12) -> plt.Figure:
    """Raw event study: delinquency rates around first disaster month."""
    es = _build_event_study(df)
    event_window = es[es["event_time"].between(-window, window)]

    es_early = event_window.groupby("event_time")["Early_Delinquency_Rate"].mean()
    es_late = event_window.groupby("event_time")["Late_Delinquency_Rate"].mean()

    fig, axes = plt.subplots(1, 2, figsize=(14, 5))

    axes[0].plot(es_early.index, es_early.values, marker="o")
    axes[0].axvline(0, linestyle="--", color="gray")
    axes[0].set_title("Early Delinquency Around First Disaster")
    axes[0].set_xlabel("Months Relative to First Treatment")
    axes[0].set_ylabel("Average Early Delinquency Rate")

    axes[1].plot(es_late.index, es_late.values, marker="o")
    axes[1].axvline(0, linestyle="--", color="gray")
    axes[1].set_title("Late Delinquency Around First Disaster")
    axes[1].set_xlabel("Months Relative to First Treatment")
    axes[1].set_ylabel("Average Late Delinquency Rate")

    fig.tight_layout()
    _savefig(fig, "event_study_raw")
    return fig


def plot_eda_event_study_demeaned(df: pd.DataFrame, window: int = 12) -> plt.Figure:
    """County-demeaned event study: removes cross-county baseline differences."""
    es = _build_event_study(df)

    county_means = es.groupby("fips")[
        ["Early_Delinquency_Rate", "Late_Delinquency_Rate"]
    ].transform("mean")
    es["Early_demeaned"] = es["Early_Delinquency_Rate"] - county_means["Early_Delinquency_Rate"]
    es["Late_demeaned"] = es["Late_Delinquency_Rate"] - county_means["Late_Delinquency_Rate"]

    event_window = es[es["event_time"].between(-window, window)]

    es_early_dm = event_window.groupby("event_time")["Early_demeaned"].mean()
    es_late_dm = event_window.groupby("event_time")["Late_demeaned"].mean()

    fig, axes = plt.subplots(1, 2, figsize=(14, 5))

    axes[0].plot(es_early_dm.index, es_early_dm.values, marker="o")
    axes[0].axvline(0, linestyle="--", color="gray")
    axes[0].set_title("County-Demeaned Early Delinquency Around First Treatment")
    axes[0].set_xlabel("Months Relative to First Treatment")
    axes[0].set_ylabel("Demeaned Early Delinquency")

    axes[1].plot(es_late_dm.index, es_late_dm.values, marker="o")
    axes[1].axvline(0, linestyle="--", color="gray")
    axes[1].set_title("County-Demeaned Late Delinquency Around First Treatment")
    axes[1].set_xlabel("Months Relative to First Treatment")
    axes[1].set_ylabel("Demeaned Late Delinquency")

    fig.tight_layout()
    _savefig(fig, "event_study_demeaned")
    return fig


def plot_eda_top_disaster_types(df: pd.DataFrame) -> plt.Figure:
    """Horizontal bar chart of disaster type frequencies."""
    type_counts = pd.Series(
        {t: df[f"n_{t.lower().replace(' ', '_')}"].sum() for t in TARGET_TYPES}
    ).sort_values()

    fig, ax = plt.subplots(figsize=(8, 5))
    ax.barh(type_counts.index, type_counts.values, edgecolor="black")
    ax.set_xlabel("Total Events")
    ax.set_title("Disaster Frequency by Type")
    fig.tight_layout()
    _savefig(fig, "top_disaster_types")
    return fig


# ---------------------------------------------------------------------------
# Modeling plots
# ---------------------------------------------------------------------------


def plot_model_feature_importance(
    feature_names: list[str],
    importances: np.ndarray,
    top_n: int = 20,
) -> plt.Figure:
    """Horizontal bar chart of top CatBoost feature importances."""
    imp_df = pd.DataFrame({"feature": feature_names, "importance": importances}).sort_values(
        "importance", ascending=False
    )
    top_imp = imp_df.head(top_n).iloc[::-1]

    fig, ax = plt.subplots(figsize=(8, 6))
    ax.barh(top_imp["feature"], top_imp["importance"])
    ax.set_title(f"Top {top_n} CatBoost Feature Importances")
    ax.set_xlabel("Importance")
    fig.tight_layout()
    _savefig(fig, "feature_importance", subfolder=MODEL_FOLDER)
    return fig


def plot_model_monthly_performance(
    monthly_true: pd.Series,
    monthly_pred: pd.Series,
) -> plt.Figure:
    """Line chart of average true vs predicted delinquency by month on the test set."""
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.plot(monthly_true.index, monthly_true.values, label="True")
    ax.plot(monthly_pred.index, monthly_pred.values, label="Predicted")
    ax.set_title("Average True vs Predicted Early Delinquency (Test Set)")
    ax.set_xlabel("Month")
    ax.set_ylabel("Early Delinquency Rate")
    ax.legend()
    fig.tight_layout()
    _savefig(fig, "monthly_performance", subfolder=MODEL_FOLDER)
    return fig
