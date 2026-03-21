"""Exploratory data analysis: distributions, treatment coverage, and event studies."""

# %%
import pandas as pd

from climatefinance import plots, utils

# %% Load data
analysis_df = utils.load_analysis_data()
analysis_df["month"] = pd.to_datetime(analysis_df["month"])

# %% Treatment balance
print(analysis_df["event_occur"].value_counts(dropna=False))

# %% Disaster frequency per treated county-month
plots.plot_eda_disaster_frequency(analysis_df)

# %% Top disaster types
plots.plot_eda_top_disaster_types(analysis_df)

# %% Delinquency over time
plots.plot_eda_delinquency_over_time(analysis_df)

# %% Damage distribution
plots.plot_eda_damage_distribution(analysis_df)

# %% Delinquency by treatment status
comparison = analysis_df.groupby("event_occur")[
    ["Early_Delinquency_Rate", "Late_Delinquency_Rate"]
].mean()
print(comparison)

plots.plot_eda_delinquency_by_treatment(analysis_df)

# %% Treatment coverage
treated_counties = analysis_df.loc[analysis_df["event_occur"] == 1, "fips"].nunique()
print("Counties ever treated:", treated_counties)
print("Share of counties ever treated:", treated_counties / analysis_df["fips"].nunique())

# %% County treatment counts
county_treatment_counts = (
    analysis_df.groupby("fips")["event_occur"].sum().sort_values(ascending=False)
)
print(county_treatment_counts.describe())
print(county_treatment_counts.head(20))

# %% Treatment rate over time
plots.plot_eda_treatment_rate(analysis_df)

# %% Raw event study
plots.plot_eda_event_study_raw(analysis_df)

# %% County-demeaned event study
plots.plot_eda_event_study_demeaned(analysis_df)
