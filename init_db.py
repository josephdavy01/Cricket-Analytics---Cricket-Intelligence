"""
Database initialization and migration script.
Reads DATABASE_URL and executes cricket_analytics.sql to set up tables, data, and views.

The SQL file is a pg_dump output containing COPY ... FROM stdin blocks and psql
meta-commands (\restrict, \unrestrict) that cannot be executed via psycopg2.
This script uses the psql CLI tool to import the dump directly.

Usage:
    python init_db.py
"""

import os
import re
import sys
import subprocess
import shutil
from urllib.parse import urlparse

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres:postgres@localhost:5432/t20i_cricket_analytics",
)

# Convert asyncpg scheme if present
if "+asyncpg" in DATABASE_URL:
    DATABASE_URL = DATABASE_URL.replace("+asyncpg", "")

SQL_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cricket_analytics.sql")
if not os.path.exists(SQL_FILE):
    SQL_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "database.sql")


def check_tables_exist():
    """Quick check if key tables already have data using psycopg2."""
    try:
        import psycopg2
        connect_kwargs = {}
        url = DATABASE_URL
        if "sslmode=require" in url:
            url = url.replace("?sslmode=require", "").replace("&sslmode=require", "")
            connect_kwargs["sslmode"] = "require"
        elif "render.com" in url:
            connect_kwargs["sslmode"] = "require"

        conn = psycopg2.connect(url, **connect_kwargs)
        cur = conn.cursor()
        cur.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_schema = 'public' AND table_name = 'players'
            )
        """)
        table_exists = cur.fetchone()[0]
        if table_exists:
            cur.execute("SELECT COUNT(*) FROM players")
            count = cur.fetchone()[0]
            cur.close()
            conn.close()
            return count > 0
        cur.close()
        conn.close()
        return False
    except Exception as e:
        print(f"[WARN] Could not check existing tables: {e}")
        return False


def clean_sql_for_render(sql_content):
    """
    Strip psql meta-commands and problematic statements that fail on Render's
    managed PostgreSQL (where the connected role is not a superuser).
    """
    lines = sql_content.split('\n')
    cleaned = []
    for line in lines:
        # Skip psql meta-commands like \restrict, \unrestrict, \connect
        if re.match(r'^\\(restrict|unrestrict|connect)\b', line):
            continue
        # Skip ALTER SCHEMA public OWNER (requires superuser on Render)
        if re.match(r'^\s*ALTER SCHEMA public OWNER TO', line, re.IGNORECASE):
            continue
        # Skip ALTER DEFAULT PRIVILEGES FOR ROLE postgres (not available on Render)
        if re.match(r'^\s*ALTER DEFAULT PRIVILEGES FOR ROLE postgres', line, re.IGNORECASE):
            continue
        cleaned.append(line)
    return '\n'.join(cleaned)


def import_with_psql():
    """Use psql CLI to import the SQL dump (handles COPY FROM stdin correctly)."""
    psql_path = shutil.which("psql")
    if not psql_path:
        print("[ERROR] psql not found. Cannot import pg_dump files without psql.")
        return False

    # Read and clean the SQL file
    print(f"Reading and cleaning SQL dump from {SQL_FILE}...")
    with open(SQL_FILE, "r", encoding="utf-8") as f:
        sql_content = f.read()

    cleaned_sql = clean_sql_for_render(sql_content)

    # Write cleaned SQL to a temporary file
    cleaned_file = SQL_FILE + ".cleaned.tmp"
    with open(cleaned_file, "w", encoding="utf-8") as f:
        f.write(cleaned_sql)

    try:
        # Build psql connection URL with sslmode for Render
        conn_url = DATABASE_URL
        if "render.com" in conn_url and "sslmode=" not in conn_url:
            separator = "&" if "?" in conn_url else "?"
            conn_url += f"{separator}sslmode=require"

        print("Importing database with psql...")
        result = subprocess.run(
            [psql_path, conn_url, "-f", cleaned_file, "--set", "ON_ERROR_STOP=0"],
            capture_output=True,
            text=True,
            timeout=600,  # 10 minute timeout for large dumps
        )

        if result.returncode == 0:
            print("[SUCCESS] Database imported successfully with psql!")
            if result.stderr:
                # Show non-fatal warnings
                for line in result.stderr.strip().split('\n')[:10]:
                    if line.strip():
                        print(f"  [psql] {line.strip()}")
            return True
        else:
            print(f"[WARN] psql exited with code {result.returncode}")
            if result.stderr:
                for line in result.stderr.strip().split('\n')[:20]:
                    if line.strip():
                        print(f"  [psql] {line.strip()}")
            # Even with errors, data may have been partially loaded
            return True
    except subprocess.TimeoutExpired:
        print("[ERROR] psql import timed out after 10 minutes")
        return False
    except Exception as e:
        print(f"[ERROR] psql import failed: {e}")
        return False
    finally:
        # Clean up temp file
        if os.path.exists(cleaned_file):
            os.remove(cleaned_file)


def import_with_psycopg2():
    """
    Fallback: use psycopg2 for schema-only import (no COPY FROM stdin data).
    This strips COPY blocks entirely since psycopg2 cannot handle them.
    """
    try:
        import psycopg2
    except ImportError:
        print("[ERROR] Neither psql nor psycopg2 available. Cannot import database.")
        return False

    print(f"[FALLBACK] Using psycopg2 (COPY data blocks will be skipped)...")
    print(f"Reading SQL from {SQL_FILE}...")

    with open(SQL_FILE, "r", encoding="utf-8") as f:
        sql_content = f.read()

    # Clean meta-commands
    cleaned = clean_sql_for_render(sql_content)

    # Strip COPY ... FROM stdin blocks (psycopg2 can't handle them)
    # These blocks start with COPY ... FROM stdin; and end with \.
    cleaned = re.sub(
        r'COPY\s+\S+\s+\([^)]+\)\s+FROM\s+stdin;\n(?:.*\n)*?\\.\n',
        '',
        cleaned
    )

    connect_kwargs = {}
    url = DATABASE_URL
    if "sslmode=require" in url:
        url = url.replace("?sslmode=require", "").replace("&sslmode=require", "")
        connect_kwargs["sslmode"] = "require"
    elif "render.com" in url:
        connect_kwargs["sslmode"] = "require"

    try:
        conn = psycopg2.connect(url, **connect_kwargs)
        conn.autocommit = True
        cur = conn.cursor()
        cur.execute(cleaned)
        print("[PARTIAL SUCCESS] Schema and views created (no data — COPY blocks skipped)")
        print("[ACTION REQUIRED] Run with psql to load data: psql $DATABASE_URL -f cricket_analytics.sql")
        cur.close()
        conn.close()
        return True
    except Exception as e:
        print(f"[ERROR] psycopg2 import failed: {e}")
        return False


def verify_import():
    """Verify that key tables have data after import."""
    try:
        import psycopg2
        connect_kwargs = {}
        url = DATABASE_URL
        if "sslmode=require" in url:
            url = url.replace("?sslmode=require", "").replace("&sslmode=require", "")
            connect_kwargs["sslmode"] = "require"
        elif "render.com" in url:
            connect_kwargs["sslmode"] = "require"

        conn = psycopg2.connect(url, **connect_kwargs)
        cur = conn.cursor()

        tables = ["players", "matches", "batting_match_stats", "bowling_match_stats", "deliveries"]
        print("\n--- Verification ---")
        all_ok = True
        for table in tables:
            try:
                cur.execute(f"SELECT COUNT(*) FROM {table}")
                count = cur.fetchone()[0]
                status = "✓" if count > 0 else "✗ EMPTY"
                if count == 0:
                    all_ok = False
                print(f"  {status}  {table}: {count:,} rows")
            except Exception:
                print(f"  ✗  {table}: TABLE NOT FOUND")
                all_ok = False
                conn.rollback()

        cur.close()
        conn.close()

        if all_ok:
            print("\n[SUCCESS] All tables verified with data!")
        else:
            print("\n[WARNING] Some tables are empty or missing.")
        return all_ok
    except Exception as e:
        print(f"[WARN] Verification failed: {e}")
        return False


def run_init():
    if not os.path.exists(SQL_FILE):
        print(f"Error: SQL file not found at {SQL_FILE}")
        sys.exit(1)

    # Check if data already exists
    if check_tables_exist():
        print("[INFO] Database already has data. Skipping import.")
        verify_import()
        return

    print(f"Connecting to database...")
    print(f"SQL file: {SQL_FILE} ({os.path.getsize(SQL_FILE) / 1024 / 1024:.1f} MB)")

    # Try psql first (handles COPY FROM stdin), fall back to psycopg2
    success = import_with_psql()
    if not success:
        success = import_with_psycopg2()

    if not success:
        print("[FATAL] Database initialization failed with all methods.")
        sys.exit(1)

    # Verify the import
    verify_import()


if __name__ == "__main__":
    run_init()
