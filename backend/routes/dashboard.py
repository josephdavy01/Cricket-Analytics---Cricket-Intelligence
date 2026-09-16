"""
Dashboard API routes — overview statistics.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from database import get_db

router = APIRouter()


@router.get("/dashboard/summary")
async def dashboard_summary(db: AsyncSession = Depends(get_db)):
    """Aggregated overview: total matches, teams, players, top performers."""

    results = {}

    # Total counts
    row = (await db.execute(text("SELECT COUNT(*) FROM matches"))).scalar()
    results["total_matches"] = row

    row = (await db.execute(text("SELECT COUNT(*) FROM players"))).scalar()
    results["total_players"] = row

    row = (await db.execute(text(
        "SELECT COUNT(DISTINCT team) FROM players"
    ))).scalar()
    results["total_teams"] = row

    # Top 5 run scorers (career)
    rows = (await db.execute(text("""
        SELECT p.player_id, p.name, p.team, p.image_url,
               SUM(b.runs) AS total_runs
        FROM batting_match_stats b
        JOIN players p ON b.player_id = p.player_id
        GROUP BY p.player_id, p.name, p.team, p.image_url
        ORDER BY total_runs DESC
        LIMIT 5
    """))).fetchall()
    results["top_scorers"] = [
        {"player_id": r[0], "name": r[1], "team": r[2],
         "image_url": r[3], "total_runs": int(r[4])}
        for r in rows
    ]

    # Top 5 wicket takers (career)
    rows = (await db.execute(text("""
        SELECT p.player_id, p.name, p.team, p.image_url,
               SUM(b.wickets) AS total_wickets
        FROM bowling_match_stats b
        JOIN players p ON b.player_id = p.player_id
        GROUP BY p.player_id, p.name, p.team, p.image_url
        ORDER BY total_wickets DESC
        LIMIT 5
    """))).fetchall()
    results["top_wicket_takers"] = [
        {"player_id": r[0], "name": r[1], "team": r[2],
         "image_url": r[3], "total_wickets": int(r[4])}
        for r in rows
    ]

    # Team strength scores
    rows = (await db.execute(text(
        "SELECT team, team_strength_score FROM team_strength_score ORDER BY team_strength_score DESC"
    ))).fetchall()
    results["team_strengths"] = [
        {"team": r[0], "score": float(r[1])} for r in rows
    ]

    # Recent matches (last 5)
    rows = (await db.execute(text("""
        SELECT match_id, season, match_date, venue, team1, team2, winner
        FROM matches ORDER BY match_date DESC, match_id DESC LIMIT 5
    """))).fetchall()
    results["recent_matches"] = [
        {"match_id": r[0], "season": r[1],
         "match_date": str(r[2]) if r[2] else None,
         "venue": r[3], "team1": r[4], "team2": r[5], "winner": r[6]}
        for r in rows
    ]

    return results
