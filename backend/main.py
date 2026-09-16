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

# Allow Django frontend (port 8001) and any local dev
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8001", "http://127.0.0.1:8001"],
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
