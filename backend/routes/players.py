"""
Players API routes — player profiles, recent form, phase stats.
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from typing import Optional

from database import get_db

router = APIRouter()


@router.get("/players")
async def list_players(
    team: Optional[str] = Query(None, description="Filter by team name"),
    search: Optional[str] = Query(None, description="Search player by name"),
    include_retired: bool = Query(False, description="Include retired (is_active=FALSE) players"),
    db: AsyncSession = Depends(get_db),
):
    """List all players, optionally filtered by team and searched by name."""
    query = "SELECT player_id, name, team, role, batting_style, bowling_style, image_url FROM players WHERE 1=1"
    params = {}

    if not include_retired:
        query += " AND is_active = TRUE"

    if team:
        query += " AND team = :team"
        params["team"] = team
    if search:
        query += " AND name ILIKE :search"
        params["search"] = f"%{search}%"

    query += " ORDER BY name"
    rows = (await db.execute(text(query), params)).fetchall()

    return [
        {
            "player_id": r[0], "name": r[1], "team": r[2], "role": r[3],
            "batting_style": r[4], "bowling_style": r[5], "image_url": r[6],
        }
        for r in rows
    ]


@router.get("/players/{player_id}")
async def get_player(player_id: int, db: AsyncSession = Depends(get_db)):
    """Get a single player's details."""
    row = (await db.execute(
        text("""
            SELECT player_id, name, team, role, batting_style, bowling_style, image_url, profile_url,
                   batting_strike_rate AS strike_rate, batting_average AS average,
                   bowling_wickets AS wickets, bowling_economy AS economy
            FROM players WHERE player_id = :pid
        """),
        {"pid": player_id},
    )).fetchone()

    if not row:
        return {"error": "Player not found"}

    return {
        "player_id": row[0], "name": row[1], "team": row[2], "role": row[3],
        "batting_style": row[4], "bowling_style": row[5], "image_url": row[6],
        "profile_url": row[7], "strike_rate": float(row[8]) if row[8] else None,
        "average": float(row[9]) if row[9] else None,
        "wickets": row[10], "economy": float(row[11]) if row[11] else None,
    }


@router.get("/players/{player_id}/recent-form")
async def player_recent_form(player_id: int, db: AsyncSession = Depends(get_db)):
    """Get recent form stats from the player_recent_form view."""
    row = (await db.execute(
        text("SELECT * FROM player_recent_form WHERE player_id = :pid"),
        {"pid": player_id},
    )).fetchone()

    if not row:
        return {"error": "No recent form data"}

    keys = row._fields if hasattr(row, '_fields') else row.keys()
    return {k: (float(v) if isinstance(v, __import__('decimal').Decimal) else v) for k, v in zip(keys, row)}


@router.get("/players/{player_id}/phase-stats")
async def player_phase_stats(player_id: int, db: AsyncSession = Depends(get_db)):
    """Batting and bowling phase stats for a player."""
    # Batting phase stats
    bat_rows = (await db.execute(
        text("SELECT * FROM batter_phase_stats WHERE player_id = :pid ORDER BY phase"),
        {"pid": player_id},
    )).fetchall()

    # Bowling phase stats
    bowl_rows = (await db.execute(
        text("SELECT * FROM bowler_phase_stats WHERE player_id = :pid ORDER BY phase"),
        {"pid": player_id},
    )).fetchall()

    def row_to_dict(r):
        keys = r._fields if hasattr(r, '_fields') else r.keys()
        return {k: (float(v) if isinstance(v, __import__('decimal').Decimal) else v) for k, v in zip(keys, r)}

    return {
        "batting": [row_to_dict(r) for r in bat_rows],
        "bowling": [row_to_dict(r) for r in bowl_rows],
    }


@router.get("/players/{player_id}/position-stats")
async def player_position_stats(player_id: int, db: AsyncSession = Depends(get_db)):
    """Batting position stats from batting_position_performance view."""
    rows = (await db.execute(
        text("SELECT * FROM batting_position_performance WHERE player_id = :pid ORDER BY batting_position"),
        {"pid": player_id},
    )).fetchall()


    def row_to_dict(r):
        keys = r._fields if hasattr(r, '_fields') else r.keys()
        return {k: (float(v) if isinstance(v, __import__('decimal').Decimal) else v) for k, v in zip(keys, r)}

    return [row_to_dict(r) for r in rows]
