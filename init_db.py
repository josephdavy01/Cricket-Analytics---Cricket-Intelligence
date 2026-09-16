"""
Database initialization and migration script.
Reads DATABASE_URL and executes database.sql to set up tables and analytical views.

Usage:
    python init_db.py
"""

import os
import sys
import psycopg2
from urllib.parse import urlparse

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres:postgres@localhost:5432/t20i_cricket_analytics"
)

# Convert asyncpg scheme if present
if "+asyncpg" in DATABASE_URL:
    DATABASE_URL = DATABASE_URL.replace("+asyncpg", "")

SQL_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cricket_analytics.sql")
if not os.path.exists(SQL_FILE):
    SQL_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "database.sql")


def run_init():
    if not os.path.exists(SQL_FILE):
        print(f"Error: {SQL_FILE} not found.")
        sys.exit(1)

    print(f"Connecting to database...")
    try:
        connect_kwargs = {}
        if "sslmode=require" in DATABASE_URL:
            clean_url = DATABASE_URL.replace("?sslmode=require", "").replace("&sslmode=require", "")
            connect_kwargs["sslmode"] = "require"
            conn = psycopg2.connect(clean_url, **connect_kwargs)
        elif "render.com" in DATABASE_URL:
            connect_kwargs["sslmode"] = "require"
            conn = psycopg2.connect(DATABASE_URL, **connect_kwargs)
        else:
            conn = psycopg2.connect(DATABASE_URL)
        conn.autocommit = True
        cur = conn.cursor()


        print(f"Reading SQL script from {SQL_FILE}...")
        with open(SQL_FILE, "r", encoding="utf-8") as f:
            sql_script = f.read()

        print("Executing schema and views setup...")
        cur.execute(sql_script)
        print("[SUCCESS] Database schema and views initialized successfully!")

        cur.close()
        conn.close()
    except Exception as e:
        print(f"[ERROR] Database initialization failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    run_init()
