"""
Django views for Cricket Analytics.
Each view calls the FastAPI backend via api_client and renders a template.
"""

from django.shortcuts import render
from . import api_client


def dashboard(request):
    """Home dashboard with overview stats."""
    data = api_client.get_dashboard_summary()
    return render(request, 'cricket/dashboard.html', {'data': data})


def players_list(request):
    """Players listing page with team filter and name search."""
    team = request.GET.get('team', '')
    search = request.GET.get('search', '')
    teams = api_client.get_teams()
    players = api_client.get_players(team=team if team else None, search=search if search else None)
    return render(request, 'cricket/players.html', {
        'players': players,
        'teams': teams,
        'selected_team': team,
        'search_query': search,
    })


def player_detail(request, player_id):
    """Individual player profile page."""
    player = api_client.get_player(player_id)
    recent_form = api_client.get_player_recent_form(player_id)
    phase_stats = api_client.get_player_phase_stats(player_id)
    position_stats = api_client.get_player_position_stats(player_id)
    return render(request, 'cricket/player_detail.html', {
        'player': player,
        'recent_form': recent_form,
        'phase_stats': phase_stats,
        'position_stats': position_stats,
    })


def teams_page(request):
    """Team strength rankings page."""
    strength = api_client.get_team_strength()
    strength_stats = api_client.get_team_strength_stats()
    return render(request, 'cricket/teams.html', {
        'strength': strength,
        'strength_stats': strength_stats,
    })


def team_vs_team(request):
    """Team vs Team comparison page."""
    teams = api_client.get_teams()
    team_a = request.GET.get('team_a', '')
    team_b = request.GET.get('team_b', '')
    comparison = None
    if team_a and team_b:
        result = api_client.get_team_vs_team(team_a, team_b)
        comparison = result[0] if result else None
    return render(request, 'cricket/team_vs_team.html', {
        'teams': teams,
        'team_a': team_a,
        'team_b': team_b,
        'comparison': comparison,
    })


def venues_page(request):
    """Venue statistics page."""
    venues = api_client.get_venues()
    toss_stats = api_client.get_toss_stats()
    return render(request, 'cricket/venues.html', {
        'venues': venues,
        'toss_stats': toss_stats,
    })


def head_to_head(request):
    """Batter vs Bowler head-to-head matchup page."""
    batters = api_client.get_batters_list()
    bowlers = api_client.get_bowlers_list()
    batter_id = request.GET.get('batter_id', '')
    bowler_id = request.GET.get('bowler_id', '')
    matchups = None
    if batter_id or bowler_id:
        matchups = api_client.get_head_to_head(
            batter_id=int(batter_id) if batter_id else None,
            bowler_id=int(bowler_id) if bowler_id else None,
        )
    return render(request, 'cricket/head_to_head.html', {
        'batters': batters,
        'bowlers': bowlers,
        'selected_batter': batter_id,
        'selected_bowler': bowler_id,
        'matchups': matchups,
    })


def playing_xi(request):
    """Playing XI suggestion page."""
    teams = api_client.get_teams()
    team = request.GET.get('team', '')
    opponent = request.GET.get('opponent', '')
    xi = None
    if team and opponent:
        xi = api_client.get_playing_xi(team, opponent)
    return render(request, 'cricket/playing_xi.html', {
        'teams': teams,
        'selected_team': team,
        'selected_opponent': opponent,
        'xi': xi,
    })


def prediction(request):
    """Match prediction page."""
    teams = api_client.get_teams()
    venues_list = api_client.get_venues_list()
    team_a = request.GET.get('team_a', '')
    team_b = request.GET.get('team_b', '')
    venue = request.GET.get('venue', '')
    result = None
    if team_a and team_b and venue:
        result = api_client.get_match_prediction(team_a, team_b, venue)
    return render(request, 'cricket/prediction.html', {
        'teams': teams,
        'venues': venues_list,
        'team_a': team_a,
        'team_b': team_b,
        'venue': venue,
        'result': result,
    })
