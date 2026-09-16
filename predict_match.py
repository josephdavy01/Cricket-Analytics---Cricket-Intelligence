import pandas as pd
import joblib

from sqlalchemy import create_engine, text


# ==================================================
# DATABASE CONNECTION
# ==================================================

engine = create_engine(
    "postgresql+psycopg2://postgres:postgres@localhost:5432/t20i_cricket_analytics"
)


# ==================================================
# LOAD SAVED MODEL
# ==================================================

package = joblib.load(
    "t20i_prediction_model.joblib"
)

model = package["model"]
features = package["features"]
medians = package["medians"]
neutral_50_columns = package["neutral_50_columns"]

print("Model loaded:", package["model_name"])


# ==================================================
# MATCH INPUT
# CHANGE THESE VALUES FOR EACH MATCH
# ==================================================

team1 = "India"
team2 = "Australia"

venue = "Melbourne Cricket Ground"

toss_winner = "India"
toss_decision = "field"


# ==================================================
# CONFIRMED PLAYING XI PLAYER IDs
# REPLACE WITH YOUR REAL IDs
# ==================================================

team1_xi = [
      400,
      458,
      392,
      454,
      442,
      456,
      429,
      410,
      426,
      407,
      424
]

team2_xi = [
      122,
      85,
      110,
      71,
      77,
      130,
      72,
      86,
      81,
      109,
      75
]


# ==================================================
# VALIDATE XI
# ==================================================

if len(team1_xi) != 11:
    raise ValueError(
        f"{team1} XI must contain exactly 11 players."
    )

if len(team2_xi) != 11:
    raise ValueError(
        f"{team2} XI must contain exactly 11 players."
    )

if len(set(team1_xi)) != 11:
    raise ValueError(
        f"{team1} XI contains duplicate player IDs."
    )

if len(set(team2_xi)) != 11:
    raise ValueError(
        f"{team2} XI contains duplicate player IDs."
    )


# ==================================================
# CALL POSTGRESQL FEATURE FUNCTION
# ==================================================

query = text(
    """
    SELECT *
    FROM get_future_match_features(
        CAST(:team1 AS VARCHAR),
        CAST(:team2 AS VARCHAR),
        CAST(:venue AS VARCHAR),
        CAST(:toss_winner AS VARCHAR),
        CAST(:toss_decision AS VARCHAR),
        CAST(:team1_xi AS INTEGER[]),
        CAST(:team2_xi AS INTEGER[])
    )
    """
)


with engine.connect() as connection:

    result = connection.execute(
        query,
        {
            "team1": team1,
            "team2": team2,
            "venue": venue,
            "toss_winner": toss_winner,
            "toss_decision": toss_decision,
            "team1_xi": team1_xi,
            "team2_xi": team2_xi
        }
    )

    row = result.mappings().first()


if row is None:
    raise ValueError(
        "PostgreSQL returned no feature row."
    )


# ==================================================
# CONVERT SQL RESULT TO DATAFRAME
# ==================================================

X_future = pd.DataFrame(
    [dict(row)]
)


# ==================================================
# ENSURE EXACT SAME 29 FEATURES
# ==================================================

missing_features = [
    column
    for column in features
    if column not in X_future.columns
]

if missing_features:
    raise ValueError(
        "Missing model features: "
        + str(missing_features)
    )

X_future = X_future[
    features
].copy()


# ==================================================
# CONVERT TO NUMERIC
# ==================================================

for column in X_future.columns:

    X_future[column] = pd.to_numeric(
        X_future[column],
        errors="coerce"
    )


# ==================================================
# SAME NULL HANDLING AS TRAINING
# ==================================================

for column in neutral_50_columns:

    if column in X_future.columns:

        X_future[column] = (
            X_future[column]
            .fillna(50)
        )


X_future = X_future.fillna(
    medians
)


if X_future.isnull().sum().sum() > 0:

    print("\nColumns still containing NULL:")

    print(
        X_future.columns[
            X_future.isnull().any()
        ].tolist()
    )

    raise ValueError(
        "Prediction data still contains NULL values."
    )


# ==================================================
# PREDICTION
# ==================================================

prediction = model.predict(
    X_future
)[0]

probabilities = model.predict_proba(
    X_future
)[0]

team2_probability = (
    probabilities[0] * 100
)

team1_probability = (
    probabilities[1] * 100
)


if prediction == 1:
    predicted_winner = team1
else:
    predicted_winner = team2


# ==================================================
# OUTPUT
# ==================================================

print("\n======================================")
print("T20I MATCH PREDICTION")
print("======================================")

print(
    f"Match          : {team1} vs {team2}"
)

print(
    f"Venue          : {venue}"
)

print(
    f"Toss Winner    : {toss_winner}"
)

print(
    f"Toss Decision  : {toss_decision}"
)

print("\n--------------------------------------")

print(
    f"Predicted Winner: {predicted_winner}"
)

print(
    f"{team1} Win Probability: "
    f"{team1_probability:.2f}%"
)

print(
    f"{team2} Win Probability: "
    f"{team2_probability:.2f}%"
)

print("--------------------------------------")

print(
    "Model: V2 Clean Random Forest"
)

print(
    "Historical chronological validation: "
    "83.16%"
)