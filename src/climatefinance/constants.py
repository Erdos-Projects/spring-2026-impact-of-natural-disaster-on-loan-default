"""Project-wide constants for the climatefinance library."""

# Data directories
DISASTER_FOLDER = "data/disaster"
FINANCE_FOLDER = "data/finance"

# Primary input files
FINANCE_FILE = "data/finance/finance_disaster_master.dta"
DISASTER_FILE = "data/disaster/disaster_dataset_cleaned.dta"

# Raw / intermediate files used by the cleaning pipeline
DISASTER_RAW_FILE = "data/disaster/disaster_dataset.dta"
FINANCE_EARLY_CSV = "data/finance/Finance_30_89_EarlyDelinquency.csv"
FINANCE_LATE_CSV = "data/finance/Finance_90_LateDelinquency.csv"
FINANCE_CLEANED_FILE = "data/finance/Finance_Cleaned.dta"
FINANCE_DATASET_FILE = "data/finance/Finance_Dataset.dta"
FINANCE_DISASTER_DTA = "data/analysis/Finance_Disaster.dta"
COUNTY_AREA_FILE = "data/disaster/County_Area.dta"
COASTAL_COUNTIES_FILE = "data/disaster/Coastal_Counties.dta"
COUNTY_COASTDIST_FILE = "data/disaster/County_CoastDist.dta"
ANALYSIS_FOLDER = "data/analysis"
ANALYSIS_FILE = "finance_disaster_analysis"
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
CLEANING_EVENTS = [
    "Hurricane",
    "Tornado",
    "Tropical Storm",
    "Thunderstorm",
    "Flood",
    "Winter Wave",
    "Wildfire",
    "Hail",
]
INFERENCE_FILE = "inference_results"
MODELING_FILE = "modeling_results"
FIGURE_FOLDER = "data/figures"
EDA_FOLDER = "eda"
MODEL_FOLDER = "model"
