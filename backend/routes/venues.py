"""
Venues API routes — venue statistics and toss stats.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from decimal import Decimal

from database import get_db

router = APIRouter()


def _convert(v):
    if isinstance(v, Decimal):
        return float(v)
    return v


def row_to_dict(r):
    keys = r._fields if hasattr(r, '_fields') else r.keys()
    return {k: _convert(v) for k, v in zip(keys, r)}


@router.get("/venues")
async def list_venues(db: AsyncSession = Depends(get_db)):
    """Venue stats from venue_stats view."""
    rows = (await db.execute(
        text("SELECT * FROM venue_stats ORDER BY matches_played DESC")
    )).fetchall()
    return [row_to_dict(r) for r in rows]


@router.get("/venues/toss-stats")
async def venue_toss_stats(db: AsyncSession = Depends(get_db)):
    """Toss stats per team/situation from team_toss_situation_stats view."""
    rows = (await db.execute(
        text("SELECT * FROM team_toss_situation_stats ORDER BY team")
    )).fetchall()
    return [row_to_dict(r) for r in rows]

