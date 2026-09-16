from _typeshed import importlib
import pandas as pd

from sqlalchemy import create_engine

from sklearn.ensemble import RandomForestClassifier

from sklearn.metrics import (
    accuracy_score,
    f1_score,
    roc_auc_score
)


# ==================================================
# DATABASE
# ==================================================

engine = create_engine(
    "postgresql+psycopg2://postgres:postgres@localhost:5432/t20i_cricket_analytics"
)

df = pd.read_sql(
    """
    SELECT *
    FROM ml_training_dataset_v2
    ORDER BY match_date, match_id
    """,
    engine
)

df["match_date"] = pd.to_datetime(df["match_date"])

print("Total matches:", len(df))
print(
    "Date range:",
    df["match_date"].min().date(),
    "to",
    df["match_date"].max().date()
)


# ==================================================
# V1 TEAM FEATURES
# ==================================================

v1_features = [

    "team1_win_percentage_last_5",
    "team2_win_percentage_last_5",

    "team1_avg_runs_last_5",
    "team2_avg_runs_last_5",

    "team1_avg_wickets_last_5",
    "team2_avg_wickets_last_5",

    "team1_bowling_economy_last_5",
    "team2_bowling_economy_last_5",

    "previous_h2h_matches",

    "team1_h2h_win_percentage",
    "team2_h2h_win_percentage",

    "team1_previous_venue_matches",
    "team1_venue_win_percentage",

    "team2_previous_venue_matches",
    "team2_venue_win_percentage",

    "team1_won_toss",
    "toss_decision_field"
]


# ==================================================
# V2 FULL PLAYER FEATURES
# ==================================================

full_player_features = [

    "team1_players_detected",
    "team2_players_detected",

    "team1_players_batting_history",
    "team2_players_batting_history",

    "team1_players_bowling_history",
    "team2_players_bowling_history",

    "team1_xi_runs_previous_5",
    "team2_xi_runs_previous_5",

    "team1_xi_batting_strike_rate",
    "team2_xi_batting_strike_rate",

    "team1_xi_runs_per_innings",
    "team2_xi_runs_per_innings",

    "team1_xi_wickets_previous_5",
    "team2_xi_wickets_previous_5",

    "team1_xi_wickets_per_bowling_match",
    "team2_xi_wickets_per_bowling_match",

    "team1_xi_bowling_economy",
    "team2_xi_bowling_economy"
]


# ==================================================
# CLEAN PLAYER PERFORMANCE FEATURES
# Removes player-count/history-count features
# ==================================================

clean_player_features = [

    "team1_xi_runs_previous_5",
    "team2_xi_runs_previous_5",

    "team1_xi_batting_strike_rate",
    "team2_xi_batting_strike_rate",

    "team1_xi_runs_per_innings",
    "team2_xi_runs_per_innings",

    "team1_xi_wickets_previous_5",
    "team2_xi_wickets_previous_5",

    "team1_xi_wickets_per_bowling_match",
    "team2_xi_wickets_per_bowling_match",

    "team1_xi_bowling_economy",
    "team2_xi_bowling_economy"
]


v2_full_features = (
    v1_features
    +
    full_player_features
)

v2_clean_features = (
    v1_features
    +
    clean_player_features
)


# ==================================================
# TARGET
# ==================================================

y = df["team1_win"].astype(int)


# ==================================================
# PREPARE TRAIN / TEST DATA
# ==================================================

def prepare_data(
    train_df,
    test_df,
    features
):

    X_train = train_df[
        features
    ].copy()

    X_test = test_df[
        features
    ].copy()

    y_train = train_df[
        "team1_win"
    ].astype(int)

    y_test = test_df[
        "team1_win"
    ].astype(int)

    neutral_columns = [

        "team1_win_percentage_last_5",
        "team2_win_percentage_last_5",

        "team1_h2h_win_percentage",
        "team2_h2h_win_percentage",

        "team1_venue_win_percentage",
        "team2_venue_win_percentage"
    ]

    for column in neutral_columns:

        if column in X_train.columns:

            X_train[column] = (
                X_train[column]
                .fillna(50)
            )

            X_test[column] = (
                X_test[column]
                .fillna(50)
            )

    medians = X_train.median(
        numeric_only=True
    )

    X_train = X_train.fillna(
        medians
    )

    X_test = X_test.fillna(
        medians
    )

    return (
        X_train,
        X_test,
        y_train,
        y_test
    )


# ==================================================
# RANDOM FOREST
# ==================================================

def run_model(
    train_df,
    test_df,
    features
):

    (
        X_train,
        X_test,
        y_train,
        y_test
    ) = prepare_data(
        train_df,
        test_df,
        features
    )

    model = RandomForestClassifier(
        n_estimators=500,
        max_depth=6,
        min_samples_leaf=4,
        random_state=42,
        n_jobs=-1
    )

    model.fit(
        X_train,
        y_train
    )

    predictions = model.predict(
        X_test
    )

    probabilities = model.predict_proba(
        X_test
    )[:, 1]

    accuracy = accuracy_score(
        y_test,
        predictions
    )

    f1 = f1_score(
        y_test,
        predictions,
        zero_division=0
    )

    auc = roc_auc_score(
        y_test,
        probabilities
    )

    correct = (
        predictions
        ==
        y_test.values
    ).sum()

    return {
        "accuracy": accuracy * 100,
        "correct": correct,
        "total": len(y_test),
        "f1": f1,
        "auc": auc
    }


# ==================================================
# ORIGINAL 80 / 20 TEST
# ==================================================

split_index = int(
    len(df) * 0.80
)

train_df = df.iloc[
    :split_index
].copy()

test_df = df.iloc[
    split_index:
].copy()


print("\n======================================")
print("ORIGINAL 80/20 VALIDATION")
print("======================================")

results = []

versions = {

    "V1 Team Only":
        v1_features,

    "V2 Full":
        v2_full_features,

    "V2 Clean Player":
        v2_clean_features
}

for name, features in versions.items():

    result = run_model(
        train_df,
        test_df,
        features
    )

    results.append({
        "Model": name,
        "Features": len(features),
        "Accuracy": round(
            result["accuracy"],
            2
        ),
        "Correct": (
            str(result["correct"])
            +
            "/"
            +
            str(result["total"])
        ),
        "F1": round(
            result["f1"],
            4
        ),
        "ROC_AUC": round(
            result["auc"],
            4
        )
    })


print(
    pd.DataFrame(
        results
    ).to_string(
        index=False
    )
)


# ==================================================
# MULTIPLE CHRONOLOGICAL WINDOWS
# ==================================================
#
# Expanding-window validation:
#
# 60% -> next 10%
# 70% -> next 10%
# 80% -> final 20%
#
# No future matches are used for training.
# ==================================================

windows = [

    (
        "Window 1",
        0.60,
        0.70
    ),

    (
        "Window 2",
        0.70,
        0.80
    ),

    (
        "Window 3",
        0.80,
        1.00
    )
]


all_results = []


print("\n======================================")
print("CHRONOLOGICAL WINDOW VALIDATION")
print("======================================")


for (
    window_name,
    train_end_ratio,
    test_end_ratio
) in windows:

    train_end = int(
        len(df)
        *
        train_end_ratio
    )

    test_end = int(
        len(df)
        *
        test_end_ratio
    )

    window_train = df.iloc[
        :train_end
    ].copy()

    window_test = df.iloc[
        train_end:test_end
    ].copy()

    print("\n--------------------------------------")
    print(window_name)
    print("--------------------------------------")

    print(
        "Train:",
        len(window_train),
        "matches"
    )

    print(
        "Test :",
        len(window_test),
        "matches"
    )

    print(
        "Train dates:",
        window_train[
            "match_date"
        ].min().date(),
        "to",
        window_train[
            "match_date"
        ].max().date()
    )

    print(
        "Test dates :",
        window_test[
            "match_date"
        ].min().date(),
        "to",
        window_test[
            "match_date"
        ].max().date()
    )

    for name, features in versions.items():

        result = run_model(
            window_train,
            window_test,
            features
        )

        all_results.append({

            "Window":
                window_name,

            "Model":
                name,

            "Accuracy":
                round(
                    result["accuracy"],
                    2
                ),

            "Correct":
                (
                    str(
                        result["correct"]
                    )
                    +
                    "/"
                    +
                    str(
                        result["total"]
                    )
                ),

            "F1":
                round(
                    result["f1"],
                    4
                ),

            "ROC_AUC":
                round(
                    result["auc"],
                    4
                )
        })


validation_df = pd.DataFrame(
    all_results
)


print("\n======================================")
print("ALL WINDOW RESULTS")
print("======================================")

print(
    validation_df.to_string(
        index=False
    )
)


# ==================================================
# AVERAGE ACROSS WINDOWS
# ==================================================

average_results = (

    validation_df
    .groupby("Model")[
        [
            "Accuracy",
            "F1",
            "ROC_AUC"
        ]
    ]
    .mean()
    .round(4)
    .reset_index()
)


print("\n======================================")
print("AVERAGE ACROSS WINDOWS")
print("======================================")

print(
    average_results.to_string(
        index=False
    )
)





