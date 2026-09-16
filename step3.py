"""
step3.py  Full Fast Batch Data Import Pipeline
===============================================
Runs all three import steps in order using fast bulk inserts (execute_values):
  1. Players     (from cricket_squad_detailed.json)
  2. Matches     (from t20s_json/*.json)
  3. Deliveries  (from t20s_json/*.json)
"""

import os
import sys
import json
import psycopg2
from psycopg2.extras import execute_values

# --- Config -------------------------------------------------------------------

BASE_DIR    = os.path.dirname(os.path.abspath(__file__))
JSON_FOLDER = os.path.join(BASE_DIR, "t20s_json")

PLAYER_JSON = os.path.join(BASE_DIR, "Cricket", "Data", "cricket_squad_detailed.json")
if not os.path.exists(PLAYER_JSON):
    PLAYER_JSON = os.path.join(BASE_DIR, "cricket_data_engineering", "Data", "cricket_squad_detailed.json")
if not os.path.exists(PLAYER_JSON):
    PLAYER_JSON = os.path.join(BASE_DIR, "Data", "cricket_squad_detailed.json")

DB_CONFIG = dict(
    host="localhost",
    database="t20i_cricket_analytics",
    user="postgres",
    password="postgres",
    port="5432",
)

# --- Helpers ------------------------------------------------------------------

def to_int(value):
    if value is None or value == "" or value == "-":
        return None
    try:
        return int(str(value).replace(",", ""))
    except Exception:
        return None


def to_float(value):
    if value is None or value == "" or value == "-":
        return None
    try:
        return float(str(value).replace(",", ""))
    except Exception:
        return None


def get_phase(over_number):
    if over_number <= 5:
        return "Powerplay"
    elif over_number <= 14:
        return "Middle"
    else:
        return "Death"


# --- Step 1: Import Players ---------------------------------------------------

def import_players(cursor, conn):
    print("\n" + "=" * 60, flush=True)
    print("STEP 1: Importing Players (Fast Bulk Insert)...", flush=True)
    print("=" * 60, flush=True)

    if not os.path.exists(PLAYER_JSON):
        print(f"  [SKIP] Player JSON not found: {PLAYER_JSON}", flush=True)
        return

    with open(PLAYER_JSON, "r", encoding="utf-8") as f:
        data = json.load(f)

    player_records = []
    for team, players in data.items():
        for player in players:
            name        = player.get("name")
            profile_url = player.get("profile_url")
            image_url   = player.get("image_url")
            personal    = player.get("personal_info", {})
            batting     = player.get("batting_career_stats", {})
            bowling     = player.get("bowling_career_stats", {})

            player_records.append((
                name, team, profile_url, image_url,
                personal.get("Role"), personal.get("Batting Style"), personal.get("Bowling Style"),
                to_int(batting.get("Mat")), to_int(batting.get("Inns")), to_int(batting.get("NO")),
                to_int(batting.get("Runs")), batting.get("HS"), to_float(batting.get("Ave")),
                to_int(batting.get("BF")), to_float(batting.get("SR")),
                to_int(batting.get("100s")), to_int(batting.get("50s")),
                to_int(batting.get("4s")), to_int(batting.get("6s")),
                to_int(batting.get("Ct")), to_int(batting.get("St")),
                to_int(bowling.get("Mat")), to_int(bowling.get("Inns")),
                to_int(bowling.get("Balls")), to_int(bowling.get("Runs")),
                to_int(bowling.get("Wkts")), bowling.get("BBI"), bowling.get("BBM"),
                to_float(bowling.get("Ave")), to_float(bowling.get("Econ")),
                to_float(bowling.get("SR")), to_int(bowling.get("4w")),
                to_int(bowling.get("5w")), to_int(bowling.get("10w")),
            ))

    insert_query = """
        INSERT INTO players (
            name, team, profile_url, image_url,
            role, batting_style, bowling_style,
            batting_matches, batting_innings, batting_not_out, batting_runs,
            batting_highest, batting_average, batting_balls, batting_strike_rate,
            batting_100s, batting_50s, batting_4s, batting_6s,
            catches, stumpings,
            bowling_matches, bowling_innings, bowling_balls, bowling_runs,
            bowling_wickets, bowling_bbi, bowling_bbm, bowling_average,
            bowling_economy, bowling_strike_rate, bowling_4w, bowling_5w, bowling_10w
        )
        VALUES %s
        ON CONFLICT (name, team) DO UPDATE SET
            profile_url         = EXCLUDED.profile_url,
            image_url           = EXCLUDED.image_url,
            role                = EXCLUDED.role,
            batting_style       = EXCLUDED.batting_style,
            bowling_style       = EXCLUDED.bowling_style,
            batting_matches     = EXCLUDED.batting_matches,
            batting_innings     = EXCLUDED.batting_innings,
            batting_not_out     = EXCLUDED.batting_not_out,
            batting_runs        = EXCLUDED.batting_runs,
            batting_highest     = EXCLUDED.batting_highest,
            batting_average     = EXCLUDED.batting_average,
            batting_balls       = EXCLUDED.batting_balls,
            batting_strike_rate = EXCLUDED.batting_strike_rate,
            batting_100s        = EXCLUDED.batting_100s,
            batting_50s         = EXCLUDED.batting_50s,
            batting_4s          = EXCLUDED.batting_4s,
            batting_6s          = EXCLUDED.batting_6s,
            catches             = EXCLUDED.catches,
            stumpings           = EXCLUDED.stumpings,
            bowling_matches     = EXCLUDED.bowling_matches,
            bowling_innings     = EXCLUDED.bowling_innings,
            bowling_balls       = EXCLUDED.bowling_balls,
            bowling_runs        = EXCLUDED.bowling_runs,
            bowling_wickets     = EXCLUDED.bowling_wickets,
            bowling_bbi         = EXCLUDED.bowling_bbi,
            bowling_bbm         = EXCLUDED.bowling_bbm,
            bowling_average     = EXCLUDED.bowling_average,
            bowling_economy     = EXCLUDED.bowling_economy,
            bowling_strike_rate = EXCLUDED.bowling_strike_rate,
            bowling_4w          = EXCLUDED.bowling_4w,
            bowling_5w          = EXCLUDED.bowling_5w,
            bowling_10w         = EXCLUDED.bowling_10w
    """

    execute_values(cursor, insert_query, player_records, page_size=200)
    conn.commit()
    print(f"  -> {len(player_records)} players imported/updated successfully.", flush=True)


# --- Step 2: Import Matches ---------------------------------------------------

def import_matches(cursor, conn):
    print("\n" + "=" * 60, flush=True)
    print("STEP 2: Importing Matches (Fast Bulk Insert)...", flush=True)
    print("=" * 60, flush=True)

    match_records = []
    skipped = 0

    for filename in sorted(os.listdir(JSON_FOLDER)):
        if not filename.endswith(".json"):
            continue

        file_path = os.path.join(JSON_FOLDER, filename)
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        info  = data.get("info", {})
        teams = info.get("teams", [])

        if len(teams) < 2:
            skipped += 1
            continue

        team1, team2  = teams[0], teams[1]
        dates         = info.get("dates", [])
        match_date    = dates[0] if dates else None
        season        = info.get("season")
        venue         = info.get("venue")
        city          = info.get("city")

        toss          = info.get("toss", {})
        toss_winner   = toss.get("winner")
        toss_decision = toss.get("decision")

        outcome     = info.get("outcome", {})
        winner      = outcome.get("winner")
        result_type = outcome.get("result")

        if winner:
            result_type = "winner"
        elif result_type:
            result_type = str(result_type)
        elif outcome.get("eliminator"):
            result_type = "tie/eliminator"
        else:
            result_type = "unknown"

        event        = info.get("event", {})
        event_name   = event.get("name")
        match_number = event.get("match_number")
        if match_number is not None:
            match_number = str(match_number)

        match_type = info.get("match_type")

        match_records.append((
            filename, match_date, season, team1, team2, venue, city,
            toss_winner, toss_decision, winner, result_type,
            event_name, match_number, match_type
        ))

    insert_query = """
        INSERT INTO matches (
            source_file, match_date, season, team1, team2, venue, city,
            toss_winner, toss_decision, winner, result_type,
            event_name, match_number, match_type
        )
        VALUES %s
        ON CONFLICT (source_file) DO UPDATE SET
            match_date    = EXCLUDED.match_date,
            season        = EXCLUDED.season,
            team1         = EXCLUDED.team1,
            team2         = EXCLUDED.team2,
            venue         = EXCLUDED.venue,
            city          = EXCLUDED.city,
            toss_winner   = EXCLUDED.toss_winner,
            toss_decision = EXCLUDED.toss_decision,
            winner        = EXCLUDED.winner,
            result_type   = EXCLUDED.result_type,
            event_name    = EXCLUDED.event_name,
            match_number  = EXCLUDED.match_number,
            match_type    = EXCLUDED.match_type
    """

    execute_values(cursor, insert_query, match_records, page_size=200)
    conn.commit()
    print(f"  -> {len(match_records)} matches imported/updated successfully ({skipped} skipped).", flush=True)


# --- Step 3: Import Deliveries ------------------------------------------------

def import_deliveries(cursor, conn):
    print("\n" + "=" * 60, flush=True)
    print("STEP 3: Importing Deliveries (Fast Bulk Insert)...", flush=True)
    print("=" * 60, flush=True)

    # Pre-fetch match_id mappings
    cursor.execute("SELECT source_file, match_id FROM matches")
    match_map = dict(cursor.fetchall())

    all_deliveries = []
    processed_matches = 0

    for filename in sorted(os.listdir(JSON_FOLDER)):
        if not filename.endswith(".json"):
            continue

        match_id = match_map.get(filename)
        if not match_id:
            continue

        file_path = os.path.join(JSON_FOLDER, filename)
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        innings_list = data.get("innings", [])

        for innings_index, innings_data in enumerate(innings_list, start=1):
            batting_team = innings_data.get("team")
            overs        = innings_data.get("overs", [])

            for over_data in overs:
                over_number = over_data.get("over")
                phase       = get_phase(over_number)
                deliveries  = over_data.get("deliveries", [])

                for delivery in deliveries:
                    actual_delivery = delivery.get("actual_delivery")
                    ball_number     = str(actual_delivery) if actual_delivery is not None else None

                    batter      = delivery.get("batter")
                    non_striker = delivery.get("non_striker")
                    bowler      = delivery.get("bowler")

                    runs        = delivery.get("runs", {})
                    batter_runs = runs.get("batter", 0)
                    extras_runs = runs.get("extras", 0)
                    total_runs  = runs.get("total", 0)

                    extras   = delivery.get("extras", {})
                    wides    = extras.get("wides", 0)
                    no_balls = extras.get("noballs", 0)
                    byes     = extras.get("byes", 0)
                    leg_byes = extras.get("legbyes", 0)

                    wickets        = delivery.get("wickets", [])
                    is_wicket      = len(wickets) > 0
                    player_out     = None
                    dismissal_type = None

                    if wickets:
                        first_wicket   = wickets[0]
                        player_out     = first_wicket.get("player_out")
                        dismissal_type = first_wicket.get("kind")

                    all_deliveries.append((
                        match_id, innings_index, batting_team,
                        over_number, ball_number,
                        batter, non_striker, bowler,
                        batter_runs, extras_runs, total_runs,
                        wides, no_balls, byes, leg_byes,
                        is_wicket, player_out, dismissal_type, phase
                    ))

        processed_matches += 1
        if len(all_deliveries) >= 10000:
            # Batch flush deliveries
            _flush_deliveries(cursor, conn, all_deliveries)
            print(f"  [Progress] Inserted {len(all_deliveries)} deliveries across {processed_matches} matches...", flush=True)
            all_deliveries = []

    if all_deliveries:
        _flush_deliveries(cursor, conn, all_deliveries)

    print(f"  -> Deliveries imported across all {processed_matches} matches successfully.", flush=True)


def _flush_deliveries(cursor, conn, delivery_records):
    insert_query = """
        INSERT INTO deliveries (
            match_id, innings, batting_team,
            over_number, ball_number,
            batter, non_striker, bowler,
            batter_runs, extras_runs, total_runs,
            wides, no_balls, byes, leg_byes,
            is_wicket, player_out, dismissal_type, phase
        )
        VALUES %s
    """
    execute_values(cursor, insert_query, delivery_records, page_size=2000)
    conn.commit()


# --- Main ---------------------------------------------------------------------

if __name__ == "__main__":
    print("Connecting to database...", flush=True)
    db_url = os.getenv("DATABASE_URL")
    if db_url:
        if "+asyncpg" in db_url:
            db_url = db_url.replace("+asyncpg", "")
        conn = psycopg2.connect(db_url)
    else:
        conn = psycopg2.connect(**DB_CONFIG)
    cursor = conn.cursor()

    try:
        import_players(cursor, conn)
        import_matches(cursor, conn)
        import_deliveries(cursor, conn)

        print("\n" + "=" * 60, flush=True)
        print("ALL DATA IMPORTED SUCCESSFULLY TO POSTGRESQL!", flush=True)
        print("=" * 60, flush=True)

    except Exception as e:
        conn.rollback()
        print(f"\nError: {e}", flush=True)
        raise

    finally:
        cursor.close()
        conn.close()
        print("Database connection closed.", flush=True)
