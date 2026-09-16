"""
step3.py  Full Data Import Pipeline
=====================================
Runs all three import steps in order using a single DB connection:
  1. Players     (from cricket_squad_detailed.json)
  2. Matches     (from t20s_json/*.json)
  3. Deliveries  (from t20s_json/*.json, depends on matches being imported first)
"""

import json
import os
import psycopg2

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
    print("\n" + "=" * 60)
    print("STEP 1: Importing Players")
    print("=" * 60)

    if not os.path.exists(PLAYER_JSON):
        print(f"  [SKIP] Player JSON not found: {PLAYER_JSON}")
        return

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS players (
            player_id       SERIAL PRIMARY KEY,
            name            VARCHAR(255),
            team            VARCHAR(255),
            profile_url     TEXT,
            image_url       TEXT,
            role            VARCHAR(100),
            batting_style   VARCHAR(100),
            bowling_style   VARCHAR(100),
            batting_matches INT,
            batting_innings INT,
            batting_not_out INT,
            batting_runs    INT,
            batting_highest VARCHAR(50),
            batting_average NUMERIC,
            batting_balls   INT,
            batting_strike_rate NUMERIC,
            batting_100s    INT,
            batting_50s     INT,
            batting_4s      INT,
            batting_6s      INT,
            catches         INT,
            stumpings       INT,
            bowling_matches INT,
            bowling_innings INT,
            bowling_balls   INT,
            bowling_runs    INT,
            bowling_wickets INT,
            bowling_bbi     VARCHAR(50),
            bowling_bbm     VARCHAR(50),
            bowling_average NUMERIC,
            bowling_economy NUMERIC,
            bowling_strike_rate NUMERIC,
            bowling_4w      INT,
            bowling_5w      INT,
            bowling_10w     INT,
            UNIQUE (name, team)
        );
        ALTER TABLE players ADD COLUMN IF NOT EXISTS player_id SERIAL;
        CREATE UNIQUE INDEX IF NOT EXISTS idx_players_player_id ON players (player_id);
    """)
    conn.commit()

    with open(PLAYER_JSON, "r", encoding="utf-8") as f:
        data = json.load(f)

    count = 0
    for team, players in data.items():
        for player in players:
            name        = player.get("name")
            profile_url = player.get("profile_url")
            image_url   = player.get("image_url")
            personal    = player.get("personal_info", {})
            batting     = player.get("batting_career_stats", {})
            bowling     = player.get("bowling_career_stats", {})

            cursor.execute("""
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
                VALUES (
                    %s, %s, %s, %s, %s, %s, %s,
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                )
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
            """, (
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
            count += 1

    conn.commit()
    print(f"  -> {count} players imported/updated successfully.")


# --- Step 2: Import Matches ---------------------------------------------------

def import_matches(cursor, conn):
    print("\n" + "=" * 60)
    print("STEP 2: Importing Matches")
    print("=" * 60)

    count = 0
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
            print(f"  [SKIP] {filename} - teams missing")
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

        cursor.execute("""
            INSERT INTO matches (
                source_file, match_date, season, team1, team2, venue, city,
                toss_winner, toss_decision, winner, result_type,
                event_name, match_number, match_type
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
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
        """, (
            filename, match_date, season, team1, team2, venue, city,
            toss_winner, toss_decision, winner, result_type,
            event_name, match_number, match_type,
        ))
        count += 1
        print(f"  -> {filename}")

    conn.commit()
    print(f"\n  -> {count} matches imported/updated, {skipped} skipped.")


# --- Step 3: Import Deliveries ------------------------------------------------

def import_deliveries(cursor, conn):
    print("\n" + "=" * 60)
    print("STEP 3: Importing Deliveries")
    print("=" * 60)

    count   = 0
    skipped = 0

    for filename in sorted(os.listdir(JSON_FOLDER)):
        if not filename.endswith(".json"):
            continue

        cursor.execute(
            "SELECT match_id FROM matches WHERE source_file = %s",
            (filename,)
        )
        row = cursor.fetchone()

        if row is None:
            print(f"  [SKIP] {filename} - match not found in DB")
            skipped += 1
            continue

        match_id  = row[0]
        file_path = os.path.join(JSON_FOLDER, filename)

        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        innings_list = data.get("innings", [])

        cursor.execute("DELETE FROM deliveries WHERE match_id = %s", (match_id,))

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

                    cursor.execute("""
                        INSERT INTO deliveries (
                            match_id, innings, batting_team,
                            over_number, ball_number,
                            batter, non_striker, bowler,
                            batter_runs, extras_runs, total_runs,
                            wides, no_balls, byes, leg_byes,
                            is_wicket, player_out, dismissal_type, phase
                        )
                        VALUES (
                            %s, %s, %s, %s, %s,
                            %s, %s, %s, %s, %s, %s,
                            %s, %s, %s, %s,
                            %s, %s, %s, %s
                        )
                    """, (
                        match_id, innings_index, batting_team,
                        over_number, ball_number,
                        batter, non_striker, bowler,
                        batter_runs, extras_runs, total_runs,
                        wides, no_balls, byes, leg_byes,
                        is_wicket, player_out, dismissal_type, phase,
                    ))

        conn.commit()
        print(f"  -> {filename}")
        count += 1

    print(f"\n  -> {count} matches deliveries imported, {skipped} skipped.")


# --- Main ---------------------------------------------------------------------

if __name__ == "__main__":
    print("Connecting to database...")
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

        print("\n" + "=" * 60)
        print("All data imported successfully!")
        print("=" * 60)

    except Exception as e:
        conn.rollback()
        print(f"\nError: {e}")
        raise

    finally:
        cursor.close()
        conn.close()
        print("Database connection closed.")
