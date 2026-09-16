"""
HTTP client module that calls the FastAPI backend.
All Django views use this to fetch data.
"""

import httpx
from django.conf import settings

API_BASE = getattr(settings, 'FASTAPI_BASE_URL', 'http://127.0.0.1:8000').rstrip('/')
if not (API_BASE.startswith('http://') or API_BASE.startswith('https://')):
    API_BASE = f"https://{API_BASE}" if "onrender.com" in API_BASE else f"http://{API_BASE}"



def _get(endpoint: str, params: dict = None) -> dict | list:
    """Synchronous GET request to FastAPI backend."""
    try:
        resp = httpx.get(f"{API_BASE}{endpoint}", params=params, timeout=15.0)
        resp.raise_for_status()
        return resp.json()
    except httpx.HTTPError as e:
        print(f"API Error: {e}")
        return {}
    except Exception as e:
        print(f"Connection Error: {e}")
        return {}


def get_dashboard_summary():
    return _get("/api/dashboard/summary")


def get_players(team=None, search=None):
    params = {}
    if team:
        params["team"] = team
    if search:
        params["search"] = search
    return _get("/api/players", params if params else None)


def get_player(player_id):
    return _get(f"/api/players/{player_id}")


def get_player_recent_form(player_id):
    return _get(f"/api/players/{player_id}/recent-form")


def get_player_phase_stats(player_id):
    return _get(f"/api/players/{player_id}/phase-stats")


def get_player_position_stats(player_id):
    return _get(f"/api/players/{player_id}/position-stats")


def get_teams():
    return _get("/api/teams")


def get_team_strength():
    return _get("/api/teams/strength")


def get_team_strength_stats():
    return _get("/api/teams/strength-stats")


def get_team_vs_team(team_a, team_b):
    return _get("/api/teams/vs", {"team_a": team_a, "team_b": team_b})


def get_venues():
    return _get("/api/venues")


def get_toss_stats():
    return _get("/api/venues/toss-stats")


def get_head_to_head(batter_id=None, bowler_id=None):
    params = {}
    if batter_id:
        params["batter_id"] = batter_id
    if bowler_id:
        params["bowler_id"] = bowler_id
    return _get("/api/matchups/head-to-head", params)


def get_opponent_matchup(batter_team=None, bowler_team=None):
    params = {}
    if batter_team:
        params["batter_team"] = batter_team
    if bowler_team:
        params["bowler_team"] = bowler_team
    return _get("/api/matchups/opponent", params)


def get_batters_list():
    return _get("/api/matchups/batters")


def get_bowlers_list():
    return _get("/api/matchups/bowlers")


def get_playing_xi(team, opponent):
    return _get("/api/playing-xi", {"team": team, "opponent": opponent})


def get_match_prediction(team_a, team_b, venue):
    return _get("/api/predict", {"team_a": team_a, "team_b": team_b, "venue": venue})


def get_venues_list():
    return _get("/api/venues/list")
