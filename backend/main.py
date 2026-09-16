"""
FastAPI main application — Cricket Analytics API.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routes import dashboard, players, teams, venues, matchups, predictions

app = FastAPI(
    title="Cricket Analytics API",
    description="REST API serving cricket statistics from PostgreSQL views",
    version="1.0.0",
)

import os

# Allow configured CORS origins or defaults
cors_origins_env = os.getenv("CORS_ORIGINS", "")
if cors_origins_env:
    allowed_origins = [orig.strip() for orig in cors_origins_env.split(",") if orig.strip()]
else:
    allowed_origins = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount route modules
app.include_router(dashboard.router, prefix="/api", tags=["Dashboard"])
app.include_router(players.router, prefix="/api", tags=["Players"])
app.include_router(teams.router, prefix="/api", tags=["Teams"])
app.include_router(venues.router, prefix="/api", tags=["Venues"])
app.include_router(matchups.router, prefix="/api", tags=["Matchups"])
app.include_router(predictions.router, prefix="/api", tags=["Predictions"])


@app.get("/")
async def root():
    return {"message": "Cricket Analytics API", "docs": "/docs"}
