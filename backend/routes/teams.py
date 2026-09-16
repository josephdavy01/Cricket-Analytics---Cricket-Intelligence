"""
Teams API routes — strength scores, rankings, team vs team.
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from decimal import Decimal

from database import get_db

router = APIRouter()


def _convert(v):
    """Convert Decimal to float for JSON serialization."""
    if isinstance(v, Decimal):
        return float(v)
    return v


def row_to_dict(r):
    keys = r._fields if hasattr(r, '_fields') else r.keys()
    return {k: _convert(v) for k, v in zip(keys, r)}


@router.get("/teams")
async def list_teams(db: AsyncSession = Depends(get_db)):
    """List all distinct teams."""
    rows = (await db.execute(
        text("SELECT DISTINCT team FROM players ORDER BY team")
    )).fetchall()
    return [r[0] for r in rows]


@router.get("/teams/strength")
async def team_strength(db: AsyncSession = Depends(get_db)):
    """Team strength scores from team_strength_score view."""
    rows = (await db.execute(
        text("SELECT * FROM team_strength_score ORDER BY team_strength_score DESC")
    )).fetchall()
    return [row_to_dict(r) for r in rows]


@router.get("/teams/strength-stats")
async def team_strength_stats(db: AsyncSession = Depends(get_db)):
    """Detailed team strength stats from team_recent_strength view."""
    rows = (await db.execute(
        text("SELECT * FROM team_recent_strength ORDER BY avg_score_last_5_matches DESC")
    )).fetchall()
    return [row_to_dict(r) for r in rows]



@router.get("/teams/vs")
async def team_vs_team(
    team_a: str = Query(..., description="First team"),
    team_b: str = Query(..., description="Second team"),
    db: AsyncSession = Depends(get_db),
):
    """Head-to-head stats between two teams from team_vs_team_stats view."""
    rows = (await db.execute(
        text("""
            SELECT * FROM team_vs_team_stats
            WHERE (team_a = :ta AND team_b = :tb)
               OR (team_a = :tb AND team_b = :ta)
        """),
        {"ta": team_a, "tb": team_b},
    )).fetchall()

    if not rows:
        # Try with LEAST/GREATEST ordering
        rows = (await db.execute(
            text("""
                SELECT * FROM team_vs_team_stats
                WHERE team_a = LEAST(:ta, :tb)
                  AND team_b = GREATEST(:ta, :tb)
            """),
            {"ta": team_a, "tb": team_b},
        )).fetchall()

    return [row_to_dict(r) for r in rows]


@router.get("/teams/venue-toss")
async def team_venue_toss(
    team: str = Query(..., description="Team name"),
    db: AsyncSession = Depends(get_db),
):
    """Team venue & toss stats from team_venue_toss_stats view."""
    rows = (await db.execute(
        text("SELECT * FROM team_venue_toss_stats WHERE team = :team ORDER BY venue"),
        {"team": team},
    )).fetchall()
    return [row_to_dict(r) for r in rows]
