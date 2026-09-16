import pandas as pd
import joblib

from sqlalchemy import create_engine
from sklearn.ensemble import RandomForestClassifier


# ==================================================
# DATABASE CONNECTION
# ==================================================

engine = create_engine(
    "postgresql+psycopg2://postgres:postgres@localhost:5432/t20i_cricket_analytics"
)


# ==================================================
# LOAD V2 DATASET
# ==================================================

df = pd.read_sql(
    """
    SELECT *
    FROM ml_training_dataset_v2
    ORDER BY match_date, match_id
    """,
    engine
)

print("Total matches:", len(df))
print(
    "Date range:",
    df["match_date"].min(),
    "to",
    df["match_date"].max()
)


# ==================================================
# V2 CLEAN FEATURES
# EXACT SAME 29 FEATURES USED DURING VALIDATION
# ==================================================

features = [

    # TEAM FORM
    "team1_win_percentage_last_5",
    "team2_win_percentage_last_5",

    "team1_avg_runs_last_5",
    "team2_avg_runs_last_5",

    "team1_avg_wickets_last_5",
    "team2_avg_wickets_last_5",

    "team1_bowling_economy_last_5",
    "team2_bowling_economy_last_5",

    # HEAD TO HEAD
    "previous_h2h_matches",

    "team1_h2h_win_percentage",
    "team2_h2h_win_percentage",

    # VENUE
    "team1_previous_venue_matches",
    "team1_venue_win_percentage",

    "team2_previous_venue_matches",
    "team2_venue_win_percentage",

    # TOSS
    "team1_won_toss",
    "toss_decision_field",

    # PLAYER / XI BATTING
    "team1_xi_runs_previous_5",
    "team2_xi_runs_previous_5",

    "team1_xi_batting_strike_rate",
    "team2_xi_batting_strike_rate",

    "team1_xi_runs_per_innings",
    "team2_xi_runs_per_innings",

    # PLAYER / XI BOWLING
    "team1_xi_wickets_previous_5",
    "team2_xi_wickets_previous_5",

    "team1_xi_wickets_per_bowling_match",
    "team2_xi_wickets_per_bowling_match",

    "team1_xi_bowling_economy",
    "team2_xi_bowling_economy"
]


# ==================================================
# CREATE X AND Y
# ==================================================

X = df[features].copy()

y = df["team1_win"].astype(int)


# ==================================================
# HANDLE UNKNOWN PERCENTAGES
# ==================================================

neutral_50_columns = [

    "team1_win_percentage_last_5",
    "team2_win_percentage_last_5",

    "team1_h2h_win_percentage",
    "team2_h2h_win_percentage",

    "team1_venue_win_percentage",
    "team2_venue_win_percentage"
]

X[neutral_50_columns] = (
    X[neutral_50_columns]
    .fillna(50)
)


# ==================================================
# HANDLE REMAINING NULLS
# ==================================================

training_medians = X.median(
    numeric_only=True
)

X = X.fillna(
    training_medians
)


print("\nRemaining NULLs:", X.isnull().sum().sum())


# ==================================================
# FINAL RANDOM FOREST
# ==================================================

model = RandomForestClassifier(
    n_estimators=500,
    max_depth=6,
    min_samples_leaf=4,
    random_state=42,
    n_jobs=-1
)

print("\nTraining final V2 Clean model...")

model.fit(
    X,
    y
)

print("Training completed.")


# ==================================================
# SAVE EVERYTHING
# ==================================================

model_package = {

    "model": model,

    "features": features,

    "medians": training_medians,

    "neutral_50_columns": neutral_50_columns,

    "model_name": "V2 Clean Random Forest",

    "validation_accuracy": 83.16
}


joblib.dump(
    model_package,
    "t20i_prediction_model.joblib"
)


print("\n======================================")
print("FINAL MODEL SAVED")
print("======================================")

print("Model: V2 Clean Random Forest")
print("Training matches:", len(df))
print("Features:", len(features))
print("Saved as: t20i_prediction_model.joblib")

print(
    "Historical chronological validation:",
    "83.16%"
)