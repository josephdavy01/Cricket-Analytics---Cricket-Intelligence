"""
Predictions API routes — Playing XI suggestion and match prediction features.
"""

import os
import joblib
import pandas as pd
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from decimal import Decimal

from database import get_db

router = APIRouter()

_model_pkg = None


def get_ml_model():
    global _model_pkg
    if _model_pkg is not None:
        return _model_pkg

    candidate_paths = [
        os.getenv("MODEL_PATH", ""),
        os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "t20i_prediction_model.joblib"),
        os.path.join(os.path.dirname(os.path.dirname(__file__)), "t20i_prediction_model.joblib"),
        os.path.join(os.path.dirname(os.path.dirname(__file__)), "ipl_match_model.joblib"),
        os.path.join(os.getcwd(), "t20i_prediction_model.joblib"),
        os.path.join(os.getcwd(), "backend", "ipl_match_model.joblib"),
    ]

    for p in candidate_paths:
        if p and os.path.exists(p):
            try:
                _model_pkg = joblib.load(p)
                print(f"Loaded ML model from: {p}")
                return _model_pkg
            except Exception as e:
                print(f"Failed to load ML model package from {p}: {e}")

    return None


def _convert(v):
    if isinstance(v, Decimal):
        return float(v)
    return v


def row_to_dict(r):
    keys = r._fields if hasattr(r, '_fields') else r.keys()
    return {k: _convert(v) for k, v in zip(keys, r)}


@router.get("/playing-xi")
async def playing_xi(
    team: str = Query(..., description="Selected team"),
    opponent: str = Query(..., description="Opponent team"),
    db: AsyncSession = Depends(get_db),
):
    """Suggested Playing XI using player_score_vs_opponent() for opponent-aware selection."""
    rows = (await db.execute(
        text("SELECT * FROM player_score_vs_opponent(:team, :opponent)"),
        {"team": team, "opponent": opponent},
    )).fetchall()

    # Columns: player_id, player_name, role, base_score, vs_runs, vs_balls, vs_wickets, vs_batting_sr, opponent_score, final_score
    return [
        {
            "player_id": r[0],
            "name": r[1],
            "role": r[2],
            "recent_runs": int(r[4]) if r[4] else 0,        # vs_runs
            "recent_wickets": int(r[6]) if r[6] else 0,      # vs_wickets
            "performance_score": float(r[3]) if r[3] else 0,  # base_score
            "final_selection_score": float(r[9]) if r[9] else 0,  # final_score
        }
        for r in rows
    ]


@router.get("/playing-xi/default")
async def playing_xi_default(
    team: str = Query(..., description="Team name"),
    db: AsyncSession = Depends(get_db),
):
    """Default Playing XI suggestion (no opponent bias) using suggest_playing_xi()."""
    rows = (await db.execute(
        text("SELECT * FROM suggest_playing_xi(:team)"),
        {"team": team},
    )).fetchall()

    # Columns: player_id, player_name, role, base_selection_score, can_keep, can_bat, genuine_bowling_option, top_order_option, selection_reason
    return [
        {
            "player_id": r[0],
            "name": r[1],
            "role": r[2],
            "performance_score": float(r[3]) if r[3] else 0,
            "selection_reason": r[8],
        }
        for r in rows
    ]


@router.get("/predict")
async def predict_match(
    team_a: str = Query(..., description="Team A"),
    team_b: str = Query(..., description="Team B"),
    venue: str = Query(..., description="Venue"),
    db: AsyncSession = Depends(get_db),
):
    """Get pre-match features and calculate match prediction."""
    # Fetch team A strength
    row_a = (await db.execute(
        text("SELECT team, team_strength_score FROM team_strength_score WHERE team = :t"),
        {"t": team_a},
    )).fetchone()

    # Fetch team B strength
    row_b = (await db.execute(
        text("SELECT team, team_strength_score FROM team_strength_score WHERE team = :t"),
        {"t": team_b},
    )).fetchone()

    # Fetch recent stats from team_recent_strength
    recent_a = (await db.execute(
        text("SELECT * FROM team_recent_strength WHERE team = :t"),
        {"t": team_a},
    )).fetchone()

    recent_b = (await db.execute(
        text("SELECT * FROM team_recent_strength WHERE team = :t"),
        {"t": team_b},
    )).fetchone()

    # Fetch H2H form
    h2h_rows = (await db.execute(
        text("""
            SELECT winner, COUNT(*) as cnt FROM matches
            WHERE (team1 = :ta AND team2 = :tb) OR (team1 = :tb AND team2 = :ta)
            GROUP BY winner
        """),
        {"ta": team_a, "tb": team_b},
    )).fetchall()

    total_h2h = sum(r[1] for r in h2h_rows)
    h2h_a_wins = sum(r[1] for r in h2h_rows if r[0] == team_a)
    h2h_b_wins = sum(r[1] for r in h2h_rows if r[0] == team_b)

    # Fetch Venue stats
    v_rows = (await db.execute(
        text("SELECT * FROM venue_stats WHERE venue = :v"),
        {"v": venue},
    )).fetchone()

    strength_a = float(row_a[1]) if row_a and len(row_a) > 1 and row_a[1] else 50.0
    strength_b = float(row_b[1]) if row_b and len(row_b) > 1 and row_b[1] else 50.0

    score_a = float(recent_a[3]) if recent_a and len(recent_a) > 3 and recent_a[3] else 160.0
    score_b = float(recent_b[3]) if recent_b and len(recent_b) > 3 and recent_b[3] else 160.0

    w_a = int(recent_a[4]) if recent_a and len(recent_a) > 4 and recent_a[4] else 25
    w_b = int(recent_b[4]) if recent_b and len(recent_b) > 4 and recent_b[4] else 25

    econ_a = float(recent_a[5]) if recent_a and len(recent_a) > 5 and recent_a[5] else 8.5
    econ_b = float(recent_b[5]) if recent_b and len(recent_b) > 5 and recent_b[5] else 8.5

    h2h_pct_a = round((h2h_a_wins / total_h2h * 100), 1) if total_h2h > 0 else 50.0
    h2h_pct_b = round((h2h_b_wins / total_h2h * 100), 1) if total_h2h > 0 else 50.0

    v_matches = v_rows[1] if v_rows and len(v_rows) > 1 else 0
    v_avg_score = float(v_rows[2]) if v_rows and len(v_rows) > 2 and v_rows[2] else 160.0

    result = {
        "team_a": team_a,
        "team_b": team_b,
        "venue": venue,
        "team_a_strength": strength_a,
        "team_b_strength": strength_b,
        "team_a_recent_avg_score": score_a,
        "team_b_recent_avg_score": score_b,
        "team_a_recent_wickets": w_a,
        "team_b_recent_wickets": w_b,
        "team_a_recent_economy": econ_a,
        "team_b_recent_economy": econ_b,
        "team_a_h2h_win_percentage": h2h_pct_a,
        "team_b_h2h_win_percentage": h2h_pct_b,
        "venue_matches": v_matches,
        "venue_avg_first_innings_score": v_avg_score,
    }

    # AI Model inference using t20i_prediction_model.joblib
    pkg = get_ml_model()
    prob_a, prob_b = None, None

    if pkg and "model" in pkg:
        try:
            feature_res = (await db.execute(
                text("""
                    SELECT * FROM get_future_match_features(
                        CAST(:team1 AS VARCHAR),
                        CAST(:team2 AS VARCHAR),
                        CAST(:venue AS VARCHAR),
                        CAST(:toss_winner AS VARCHAR),
                        CAST(:toss_decision AS VARCHAR),
                        CAST(:team1_xi AS INTEGER[]),
                        CAST(:team2_xi AS INTEGER[])
                    )
                """),
                {
                    "team1": team_a,
                    "team2": team_b,
                    "venue": venue,
                    "toss_winner": team_a,
                    "toss_decision": "field",
                    "team1_xi": None,
                    "team2_xi": None,
                }
            )).mappings().first()

            if feature_res:
                df_feat = pd.DataFrame([dict(feature_res)])
                features = pkg["features"]
                X = df_feat[features].copy()

                if "neutral_50_columns" in pkg:
                    X[pkg["neutral_50_columns"]] = X[pkg["neutral_50_columns"]].fillna(50)
                if "medians" in pkg:
                    X = X.fillna(pkg["medians"])

                probs = pkg["model"].predict_proba(X)[0]
                # Index 0 is team1_win = 0 (team_b win), Index 1 is team1_win = 1 (team_a win)
                prob_a = round(float(probs[1]) * 100, 1)
                prob_b = round(float(probs[0]) * 100, 1)
        except Exception as err:
            print(f"ML Inference error: {err}")

    if prob_a is None or prob_b is None:
        # Fallback heuristic calculation if ML model fails or feature generation returns empty
        prob_score_a = strength_a * 0.4 + h2h_pct_a * 0.3 + (score_a / (score_a + score_b) * 100) * 0.3
        prob_score_b = strength_b * 0.4 + h2h_pct_b * 0.3 + (score_b / (score_a + score_b) * 100) * 0.3
        tot = prob_score_a + prob_score_b
        prob_a = round(prob_score_a / tot * 100, 1) if tot > 0 else 50.0
        prob_b = round(prob_score_b / tot * 100, 1) if tot > 0 else 50.0

    result["team_a_win_probability"] = prob_a
    result["team_b_win_probability"] = prob_b
    result["predicted_winner"] = team_a if prob_a >= prob_b else team_b

    return result



@router.get("/venues/list")
async def venues_list(db: AsyncSession = Depends(get_db)):
    """Simple list of venue names for selectors."""
    rows = (await db.execute(
        text("SELECT DISTINCT venue FROM matches ORDER BY venue")
    )).fetchall()
    return [r[0] for r in rows]
