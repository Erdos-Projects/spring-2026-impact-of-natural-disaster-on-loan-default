import pandas as pd
from pathlib import Path
import numpy as np
import matplotlib.pyplot as plt




def main():
    """Load disaster data, process damage columns, and save to CSV."""
    # Load the dataset
    path_data = Path("./data")

    path_disaster_processed = path_data / "1-Disaster_processed"

    #disaster data
    disaster_data = pd.read_csv(path_disaster_processed / "Disaster_Dataset_Cleaned_v2.csv")
    print(disaster_data.shape)  # (339457, 59)  - same number as stata data
    print(disaster_data.head())

    print('Total rows:', len(disaster_data))
    print('Unique episode_ids:', disaster_data['episode_id'].nunique())

    # Aggregate by episode_id:
    #   - sum damage_property_usd and damage_crops_usd
    #   - take first value for all other columns
    sum_cols = ["damage_property_usd", "damage_crops_usd"]
    other_cols = [c for c in disaster_data.columns if c not in sum_cols and c != "episode_id"]

    agg_dict = {col: "sum" for col in sum_cols}
    agg_dict.update({col: "first" for col in other_cols})

    disaster_agg = disaster_data.groupby("episode_id", as_index=False).agg(agg_dict)

    print("\nAggregated shape:", disaster_agg.shape) # (98536, 59)
    print(disaster_agg.head())

    # --- Group by event_type and sum damage columns ---
    damage_by_event_type = disaster_agg.groupby("event_type")[sum_cols].sum()
    damage_by_event_type = damage_by_event_type.sort_values("damage_property_usd", ascending=False)

    print("\nDamage by event_type:")
    print(damage_by_event_type)

    # Create output directory for figures
    fig_dir = Path("./figures")
    fig_dir.mkdir(exist_ok=True)

    # Histogram 1: Total Property Damage by Event Type
    fig1, ax1 = plt.subplots(figsize=(14, 7))
    damage_by_event_type["damage_property_usd"].plot(kind="bar", ax=ax1, color="steelblue")
    ax1.set_title("Total Property Damage (USD) by Event Type", fontsize=16)
    ax1.set_xlabel("Event Type", fontsize=12)
    ax1.set_ylabel("Total Property Damage (USD)", fontsize=12)
    ax1.tick_params(axis="x", rotation=45)
    fig1.tight_layout()
    fig1.savefig(fig_dir / "damage_property_by_event_type.png", dpi=150)
    print(f"\nSaved: {fig_dir / 'damage_property_by_event_type.png'}")

    # Histogram 2: Total Crop Damage by Event Type
    damage_by_event_type_crops = damage_by_event_type.sort_values("damage_crops_usd", ascending=False)
    fig2, ax2 = plt.subplots(figsize=(14, 7))
    damage_by_event_type_crops["damage_crops_usd"].plot(kind="bar", ax=ax2, color="forestgreen")
    ax2.set_title("Total Crop Damage (USD) by Event Type", fontsize=16)
    ax2.set_xlabel("Event Type", fontsize=12)
    ax2.set_ylabel("Total Crop Damage (USD)", fontsize=12)
    ax2.tick_params(axis="x", rotation=45)
    fig2.tight_layout()
    fig2.savefig(fig_dir / "damage_crops_by_event_type.png", dpi=150)
    print(f"Saved: {fig_dir / 'damage_crops_by_event_type.png'}")

    plt.show()

    # --- Table: number of events per event_type ---
    event_counts = (
        disaster_agg.groupby("event_type")
        .size()
        .reset_index(name="num_events")
        .sort_values("num_events", ascending=False)
    )
    print("\nNumber of events per event_type:")
    print(event_counts.to_string(index=False))

    event_counts.to_csv(fig_dir / "event_counts_by_event_type.csv", index=False)
    print(f"Saved: {fig_dir / 'event_counts_by_event_type.csv'}")

    # --- Per event_type histograms of damage distributions ---
    event_types = sorted(disaster_agg["event_type"].dropna().unique())
    hist_dir = fig_dir / "histograms_by_event_type"
    hist_dir.mkdir(exist_ok=True)

    for event in event_types:
        subset = disaster_agg[disaster_agg["event_type"] == event]
        safe_name = event.replace("/", "-").replace(" ", "_")

        for col, color, label in [
            ("damage_property_usd", "steelblue", "Property Damage (USD)"),
            ("damage_crops_usd", "forestgreen", "Crop Damage (USD)"),
        ]:
            values = subset[col].dropna()
            values = values[values > 0]  # only non-zero damage for meaningful histogram
            if values.empty:
                continue

            fig, ax = plt.subplots(figsize=(10, 6))
            ax.hist(values, bins=50, color=color, edgecolor="black", alpha=0.7)
            ax.set_title(f"{label} Distribution — {event}", fontsize=14)
            ax.set_xlabel(label, fontsize=12)
            ax.set_ylabel("Frequency", fontsize=12)
            ax.set_yscale("log")  # log scale since damage values are highly skewed
            fig.tight_layout()

            fname = hist_dir / f"{safe_name}_{col}.png"
            fig.savefig(fname, dpi=150)
            plt.close(fig)

        print(f"  Saved histograms for: {event}")

    print(f"\nAll per-event-type histograms saved to: {hist_dir}")







if __name__ == "__main__":
    main()



