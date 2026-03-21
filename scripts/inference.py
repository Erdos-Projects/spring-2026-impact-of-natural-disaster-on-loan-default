"""Inference: panel OLS regressions of delinquency on disaster exposure."""

# %%
import numpy as np
import pandas as pd
from linearmodels.panel import PanelOLS

from climatefinance import utils

results: list[dict] = []

# %% Load data
analysis_df = utils.load_analysis_data()
analysis_df["month"] = pd.to_datetime(analysis_df["month"])

# %% Set panel index
panel_df = analysis_df.copy()
panel_df = panel_df.set_index(["fips", "month"]).sort_index()

# %% Model 1 — Baseline: Early delinquency ~ event_occur
y1 = panel_df["Early_Delinquency_Rate"]
X1 = panel_df[["event_occur"]]

mod1 = PanelOLS(y1, X1, entity_effects=True, time_effects=True, drop_absorbed=True)
res1 = mod1.fit(cov_type="clustered", cluster_entity=True)
print(res1.summary)
results.extend(utils.extract_panel_results(res1, "baseline", "Early_Delinquency_Rate"))

# %% Model 1 — Baseline: Late delinquency ~ event_occur
y2 = panel_df["Late_Delinquency_Rate"]
X2 = panel_df[["event_occur"]]

mod2 = PanelOLS(y2, X2, entity_effects=True, time_effects=True, drop_absorbed=True)
res2 = mod2.fit(cov_type="clustered", cluster_entity=True)
print(res2.summary)
results.extend(utils.extract_panel_results(res2, "baseline", "Late_Delinquency_Rate"))

# %% Model 2 — Distributed lag: Early delinquency
panel_df = analysis_df.copy()
panel_df = panel_df.set_index(["fips", "month"]).sort_index()

for k in range(1, 7):
    panel_df[f"log_total_damage_lag{k}"] = (
        panel_df.groupby(level=0)["log_total_damage"].shift(k).fillna(0)
    )

lag_cols = ["log_total_damage"] + [f"log_total_damage_lag{k}" for k in range(1, 7)]

mod_dl = PanelOLS(
    panel_df["Early_Delinquency_Rate"],
    panel_df[lag_cols],
    entity_effects=True,
    time_effects=True,
    drop_absorbed=True,
)
res_dl = mod_dl.fit(cov_type="clustered", cluster_entity=True)
print(res_dl.summary)
results.extend(utils.extract_panel_results(res_dl, "distributed_lag", "Early_Delinquency_Rate"))

# %% Model 2 — Distributed lag: Late delinquency
panel_df = analysis_df.copy()
panel_df = panel_df.set_index(["fips", "month"]).sort_index()

for k in range(1, 7):
    panel_df[f"log_total_damage_lag{k}"] = (
        panel_df.groupby(level=0)["log_total_damage"].shift(k).fillna(0)
    )

mod_l_late = PanelOLS(
    panel_df["Late_Delinquency_Rate"],
    panel_df[lag_cols],
    entity_effects=True,
    time_effects=True,
    drop_absorbed=True,
)
res_l_late = mod_l_late.fit(cov_type="clustered", cluster_entity=True)
print(res_l_late.summary)
results.extend(utils.extract_panel_results(res_l_late, "distributed_lag", "Late_Delinquency_Rate"))

# %% Model 3 — Disaster type indicators
panel_df["flood_occur"] = (panel_df["n_flood"] > 0).astype(int)
panel_df["tornado_occur"] = (panel_df["n_tornado"] > 0).astype(int)
panel_df["thunder_occur"] = (panel_df["n_thunderstorm"] > 0).astype(int)
panel_df["hail_occur"] = (panel_df["n_hail"] > 0).astype(int)

# %% Flood — Early & Late
X_types = panel_df[["flood_occur"]]

mod_types = PanelOLS(
    panel_df["Early_Delinquency_Rate"],
    X_types,
    entity_effects=True,
    time_effects=True,
    drop_absorbed=True,
)
res_types = mod_types.fit(cov_type="clustered", cluster_entity=True)
print(res_types.summary)
results.extend(utils.extract_panel_results(res_types, "flood_only", "Early_Delinquency_Rate"))

mod_types = PanelOLS(
    panel_df["Late_Delinquency_Rate"],
    X_types,
    entity_effects=True,
    time_effects=True,
    drop_absorbed=True,
)
res_types = mod_types.fit(cov_type="clustered", cluster_entity=True)
print(res_types.summary)
results.extend(utils.extract_panel_results(res_types, "flood_only", "Late_Delinquency_Rate"))

# %% Hail — Early & Late
X_types = panel_df[["hail_occur"]]

mod_types = PanelOLS(
    panel_df["Early_Delinquency_Rate"],
    X_types,
    entity_effects=True,
    time_effects=True,
    drop_absorbed=True,
)
res_types = mod_types.fit(cov_type="clustered", cluster_entity=True)
print(res_types.summary)
results.extend(utils.extract_panel_results(res_types, "hail_only", "Early_Delinquency_Rate"))

mod_types = PanelOLS(
    panel_df["Late_Delinquency_Rate"],
    X_types,
    entity_effects=True,
    time_effects=True,
    drop_absorbed=True,
)
res_types = mod_types.fit(cov_type="clustered", cluster_entity=True)
print(res_types.summary)
results.extend(utils.extract_panel_results(res_types, "hail_only", "Late_Delinquency_Rate"))

# %% Tornado — Early & Late
X_types = panel_df[["tornado_occur"]]

mod_types = PanelOLS(
    panel_df["Early_Delinquency_Rate"],
    X_types,
    entity_effects=True,
    time_effects=True,
    drop_absorbed=True,
)
res_types = mod_types.fit(cov_type="clustered", cluster_entity=True)
print(res_types.summary)
results.extend(utils.extract_panel_results(res_types, "tornado_only", "Early_Delinquency_Rate"))

mod_types = PanelOLS(
    panel_df["Late_Delinquency_Rate"],
    X_types,
    entity_effects=True,
    time_effects=True,
    drop_absorbed=True,
)
res_types = mod_types.fit(cov_type="clustered", cluster_entity=True)
print(res_types.summary)
results.extend(utils.extract_panel_results(res_types, "tornado_only", "Late_Delinquency_Rate"))

# %% Joint type model — Early & Late
type_cols = ["flood_occur", "tornado_occur", "thunder_occur", "hail_occur"]

mod_types_early = PanelOLS(
    panel_df["Early_Delinquency_Rate"],
    panel_df[type_cols],
    entity_effects=True,
    time_effects=True,
    drop_absorbed=True,
)
res_types_early = mod_types_early.fit(cov_type="clustered", cluster_entity=True)
print(res_types_early.summary)
results.extend(
    utils.extract_panel_results(res_types_early, "joint_types", "Early_Delinquency_Rate")
)

mod_types_late = PanelOLS(
    panel_df["Late_Delinquency_Rate"],
    panel_df[type_cols],
    entity_effects=True,
    time_effects=True,
    drop_absorbed=True,
)
res_types_late = mod_types_late.fit(cov_type="clustered", cluster_entity=True)
print(res_types_late.summary)
results.extend(utils.extract_panel_results(res_types_late, "joint_types", "Late_Delinquency_Rate"))

# %% Model 4 — County heterogeneity: identify top 5 exposed counties
df = analysis_df.copy()
df["month"] = pd.to_datetime(df["month"])
df["flood_occur"] = (df["n_flood"] > 0).astype(int)

county_exposure = df.groupby(["fips", "County"], as_index=False).agg(
    total_damage_sum=("total_damage", "sum"),
    treated_months=("event_occur", "sum"),
    total_disaster_events=("n_disasters", "sum"),
)

top5 = county_exposure.sort_values("total_damage_sum", ascending=False).head(5)
print(top5)
top5_fips = top5["fips"].tolist()

# %% Build interaction terms
df_int = df.copy()

for f in top5_fips:
    df_int[f"flood_x_{f}"] = (df_int["fips"] == f).astype(int) * df_int["flood_occur"]

panel_int = df_int.set_index(["fips", "month"]).sort_index()
interaction_cols = ["flood_occur"] + [f"flood_x_{f}" for f in top5_fips]

# %% Interaction model estimation
mod_county_het = PanelOLS(
    panel_int["Early_Delinquency_Rate"],
    panel_int[interaction_cols],
    entity_effects=True,
    time_effects=True,
    drop_absorbed=True,
)
res_county_het = mod_county_het.fit(cov_type="clustered", cluster_entity=True)
print(res_county_het.summary)
results.extend(
    utils.extract_panel_results(res_county_het, "county_heterogeneity", "Early_Delinquency_Rate")
)

# %% County-specific total flood effects
base_effect = res_county_het.params["flood_occur"]

rows = []
for f in top5_fips:
    interaction_name = f"flood_x_{f}"
    county_name = top5.loc[top5["fips"] == f, "County"].iloc[0]
    county_effect = base_effect + res_county_het.params.get(interaction_name, 0.0)

    rows.append(
        {
            "fips": f,
            "County": county_name,
            "base_flood_effect": base_effect,
            "interaction": res_county_het.params.get(interaction_name, np.nan),
            "county_flood_effect": county_effect,
        }
    )

county_effects_table = pd.DataFrame(rows)
print(county_effects_table)

# %% Save all inference results
results_df = pd.DataFrame(results)
print(results_df.to_string(index=False))
utils.save_analysis_inference(results_df, index=False)
