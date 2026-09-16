"""
Database initialization and migration script.
Reads DATABASE_URL and executes cricket_analytics.sql to set up tables and data.

Handles pg_dump's COPY ... FROM stdin blocks using psycopg2's copy_expert(),
and strips psql-only meta-commands (\restrict, \unrestrict) that psycopg2
cannot process.

Usage:
    python init_db.py
"""

import os
import io
import re
import sys

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


def get_connection():
    """Create a psycopg2 connection handling Render's SSL requirements."""
    import psycopg2

    connect_kwargs = {}
    url = DATABASE_URL
    if "sslmode=require" in url:
        url = url.replace("?sslmode=require", "").replace("&sslmode=require", "")
        connect_kwargs["sslmode"] = "require"
    elif "render.com" in url:
        connect_kwargs["sslmode"] = "require"

    conn = psycopg2.connect(url, **connect_kwargs)
    return conn


def check_tables_have_data():
    """Check if key tables already have data."""
    try:
        conn = get_connection()
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


def should_skip_line(line):
    """Check if a SQL line is a psql meta-command or Render-incompatible statement."""
    # psql meta-commands
    if re.match(r'^\\(restrict|unrestrict|connect)\b', line):
        return True
    # ALTER SCHEMA public OWNER (requires superuser)
    if re.match(r'^\s*ALTER SCHEMA public OWNER TO', line, re.IGNORECASE):
        return True
    # ALTER DEFAULT PRIVILEGES FOR ROLE postgres (not available on Render)
    if re.match(r'^\s*ALTER DEFAULT PRIVILEGES FOR ROLE postgres', line, re.IGNORECASE):
        return True
    return False


def import_database():
    """
    Import the pg_dump SQL file using psycopg2.
    
    Handles COPY ... FROM stdin blocks by extracting the data rows and
    feeding them through psycopg2's copy_expert() method.
    """
    import psycopg2

    if not os.path.exists(SQL_FILE):
        print(f"Error: SQL file not found at {SQL_FILE}")
        sys.exit(1)

    file_size_mb = os.path.getsize(SQL_FILE) / 1024 / 1024
    print(f"SQL file: {SQL_FILE} ({file_size_mb:.1f} MB)")
    print("Connecting to database...")

    conn = get_connection()
    conn.autocommit = False  # Use transactions for COPY blocks
    cur = conn.cursor()

    print("Parsing and executing SQL dump...")

    with open(SQL_FILE, "r", encoding="utf-8") as f:
        sql_buffer = []        # Accumulates regular SQL statements
        in_copy_block = False  # True when inside COPY ... FROM stdin data
        copy_header = ""       # The COPY ... FROM stdin; statement
        copy_data = []         # Data rows for the COPY block
        line_count = 0
        copy_count = 0
        stmt_count = 0

        for line in f:
            line_count += 1
            raw_line = line.rstrip('\n').rstrip('\r')

            # Skip psql meta-commands
            if should_skip_line(raw_line):
                continue

            if in_copy_block:
                # Check for end-of-COPY marker: a line with just '\.'
                if raw_line == '\\.':
                    # Execute the COPY block using copy_expert
                    try:
                        data_text = '\n'.join(copy_data) + '\n'
                        data_stream = io.StringIO(data_text)
                        # Build COPY ... FROM STDIN statement
                        cur.copy_expert(copy_header, data_stream)
                        conn.commit()
                        copy_count += 1
                        if copy_count % 2 == 0:
                            print(f"  Loaded {copy_count} COPY blocks... (line {line_count:,})")
                    except Exception as e:
                        print(f"  [WARN] COPY block failed at line {line_count}: {e}")
                        conn.rollback()
                    
                    in_copy_block = False
                    copy_header = ""
                    copy_data = []
                else:
                    copy_data.append(raw_line)
                continue

            # Check if this line starts a COPY ... FROM stdin block
            copy_match = re.match(r'^(COPY\s+\S+\s*\([^)]+\)\s+FROM\s+stdin)\s*;', raw_line, re.IGNORECASE)
            if copy_match:
                # First, execute any buffered SQL before this COPY
                if sql_buffer:
                    sql_text = '\n'.join(sql_buffer).strip()
                    if sql_text:
                        try:
                            cur.execute(sql_text)
                            conn.commit()
                            stmt_count += 1
                        except Exception as e:
                            error_msg = str(e).strip().split('\n')[0]
                            # Ignore "already exists" errors (re-runs)
                            if 'already exists' not in error_msg.lower():
                                print(f"  [WARN] SQL error at line {line_count}: {error_msg}")
                            conn.rollback()
                    sql_buffer = []

                in_copy_block = True
                copy_header = copy_match.group(1) + " FROM STDIN"
                copy_data = []
                continue

            # Regular SQL line — add to buffer
            sql_buffer.append(raw_line)

            # Execute when we hit a statement-ending semicolon
            # (but only outside string literals / function bodies)
            joined = '\n'.join(sql_buffer).strip()
            if joined.endswith(';') and not _in_function_body(joined):
                try:
                    cur.execute(joined)
                    conn.commit()
                    stmt_count += 1
                except Exception as e:
                    error_msg = str(e).strip().split('\n')[0]
                    if 'already exists' not in error_msg.lower():
                        print(f"  [WARN] SQL error at line {line_count}: {error_msg}")
                    conn.rollback()
                sql_buffer = []

        # Execute any remaining SQL in the buffer
        if sql_buffer:
            joined = '\n'.join(sql_buffer).strip()
            if joined:
                try:
                    cur.execute(joined)
                    conn.commit()
                    stmt_count += 1
                except Exception as e:
                    error_msg = str(e).strip().split('\n')[0]
                    if 'already exists' not in error_msg.lower():
                        print(f"  [WARN] Final SQL error: {error_msg}")
                    conn.rollback()

    cur.close()
    conn.close()
    print(f"\n[DONE] Processed {line_count:,} lines, {stmt_count} SQL statements, {copy_count} COPY blocks")


def _in_function_body(sql_text):
    """
    Rough check if we're inside a CREATE FUNCTION body (between $$ markers).
    pg_dump wraps function bodies in $$ delimiters, and these contain
    semicolons that should NOT be treated as statement terminators.
    """
    # Count $$ occurrences — if odd, we're inside a function body
    count = sql_text.count('$$')
    return count % 2 != 0


def verify_import():
    """Verify that key tables have data after import."""
    try:
        conn = get_connection()
        cur = conn.cursor()

        tables = ["players", "matches", "batting_match_stats", "bowling_match_stats", "deliveries"]
        print("\n--- Verification ---")
        all_ok = True
        for table in tables:
            try:
                cur.execute(f"SELECT COUNT(*) FROM {table}")
                count = cur.fetchone()[0]
                status = "OK" if count > 0 else "EMPTY"
                if count == 0:
                    all_ok = False
                print(f"  [{status}]  {table}: {count:,} rows")
            except Exception:
                print(f"  [MISSING]  {table}: TABLE NOT FOUND")
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
    if check_tables_have_data():
        print("[INFO] Database already has data. Skipping import.")
        verify_import()
        return

    print("Starting database initialization...")
    import_database()
    verify_import()


if __name__ == "__main__":
    run_init()
