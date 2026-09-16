"""
Matchups API routes — batter vs bowler head-to-head, opponent matchups.
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from decimal import Decimal
from typing import Optional

from database import get_db

router = APIRouter()


def _convert(v):
    if isinstance(v, Decimal):
        return float(v)
    return v


def row_to_dict(r):
    keys = r._fields if hasattr(r, '_fields') else r.keys()
    return {k: _convert(v) for k, v in zip(keys, r)}


@router.get("/matchups/head-to-head")
async def head_to_head(
    batter_id: Optional[int] = Query(None),
    bowler_id: Optional[int] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """Batter vs bowler head-to-head stats."""
    if batter_id and bowler_id:
        rows = (await db.execute(
            text("SELECT * FROM batter_bowler_head_to_head WHERE batter_id = :bid AND bowler_id = :wid"),
            {"bid": batter_id, "wid": bowler_id},
        )).fetchall()
    elif batter_id:
        rows = (await db.execute(
            text("SELECT * FROM batter_bowler_head_to_head WHERE batter_id = :bid ORDER BY runs DESC LIMIT 20"),
            {"bid": batter_id},
        )).fetchall()
    elif bowler_id:
        rows = (await db.execute(
            text("SELECT * FROM batter_bowler_head_to_head WHERE bowler_id = :wid ORDER BY wickets DESC LIMIT 20"),
            {"wid": bowler_id},
        )).fetchall()
    else:
        rows = (await db.execute(
            text("SELECT * FROM batter_bowler_head_to_head ORDER BY balls_faced DESC LIMIT 50")
        )).fetchall()

    return [row_to_dict(r) for r in rows]


@router.get("/matchups/opponent")
async def opponent_matchup(
    batter_team: Optional[str] = Query(None),
    bowler_team: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """Player opponent matchup scores from player_actual_capability view."""
    conditions = []
    params = {}

    if batter_team:
        conditions.append("team = :bt")
        params["bt"] = batter_team

    where_clause = " AND ".join(conditions) if conditions else "1=1"

    rows = (await db.execute(
        text(f"SELECT * FROM player_actual_capability WHERE {where_clause} ORDER BY base_selection_score DESC NULLS LAST LIMIT 50"),
        params,
    )).fetchall()

    return [row_to_dict(r) for r in rows]



@router.get("/matchups/batters")
async def list_batters(db: AsyncSession = Depends(get_db)):
    """List players who have batting stats (for dropdown selectors)."""
    rows = (await db.execute(
        text("""
            SELECT DISTINCT p.player_id, p.name, p.team
            FROM players p
            JOIN batting_match_stats b ON p.player_id = b.player_id
            WHERE p.is_active = TRUE
            ORDER BY p.name
        """)
    )).fetchall()
    return [{"player_id": r[0], "name": r[1], "team": r[2]} for r in rows]


@router.get("/matchups/bowlers")
async def list_bowlers(db: AsyncSession = Depends(get_db)):
    """List players who have bowling stats (for dropdown selectors)."""
    rows = (await db.execute(
        text("""
            SELECT DISTINCT p.player_id, p.name, p.team
            FROM players p
            JOIN bowling_match_stats b ON p.player_id = b.player_id
            WHERE p.is_active = TRUE
            ORDER BY p.name
        """)
    )).fetchall()
    return [{"player_id": r[0], "name": r[1], "team": r[2]} for r in rows]
