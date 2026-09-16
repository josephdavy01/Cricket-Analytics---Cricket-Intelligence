"""
HTTP client module that calls the FastAPI backend.
All Django views use this to fetch data.
"""

import httpx
from django.conf import settings

import os

def _get_api_base():
    raw_base = getattr(settings, 'FASTAPI_BASE_URL', None) or os.getenv('FASTAPI_BASE_URL', '')
    raw_base = raw_base.strip().rstrip('/')
    
    # If running locally without explicit URL
    if not os.getenv('RENDER') and not os.getenv('RENDER_SERVICE_ID'):
        if not raw_base or raw_base in ('http://127.0.0.1:8000', 'http://localhost:8000'):
            return 'http://127.0.0.1:8000'

    # Fallback default on Render
    if not raw_base or raw_base in ('http://127.0.0.1:8000', 'http://localhost:8000'):
        return 'https://cricket-analytics-api-8pbt.onrender.com'
    
    if not (raw_base.startswith('http://') or raw_base.startswith('https://')):
        if '.' not in raw_base:
            host_part = 'cricket-analytics-api-8pbt' if raw_base == 'cricket-analytics-api' else raw_base
            return f'https://{host_part}.onrender.com'
        elif 'onrender.com' in raw_base:
            return f'https://{raw_base}'
        else:
            return f'http://{raw_base}'
    
    if 'cricket-analytics-api' in raw_base and 'onrender.com' not in raw_base:
        host_part = raw_base.replace('http://', '').replace('https://', '').split(':')[0]
        if host_part == 'cricket-analytics-api':
            host_part = 'cricket-analytics-api-8pbt'
        return f'https://{host_part}.onrender.com'
        
    return raw_base

API_BASE = _get_api_base()



def _get(endpoint: str, params: dict = None) -> dict | list:
    """Synchronous GET request to FastAPI backend."""
    try:
        resp = httpx.get(f"{API_BASE}{endpoint}", params=params, timeout=30.0)
        resp.raise_for_status()
        return resp.json()
    except httpx.HTTPError as e:
        print(f"API Error at {API_BASE}{endpoint}: {e}")
        return {}
    except Exception as e:
        print(f"Connection Error at {API_BASE}{endpoint}: {e}")
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
