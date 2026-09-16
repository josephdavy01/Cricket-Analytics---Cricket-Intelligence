"""
step3.py — Data Import Pipeline for Airflow / Local
===================================================
Runs all three import steps in order using a single DB connection:
  1. Players     (from India_squad_detailed.json / cricket_squad_detailed.json)
  2. Matches     (from t20s_json/*.json)
  3. Deliveries  (from t20s_json/*.json)
"""

import json
import os
import logging
import psycopg2

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# --- Config -------------------------------------------------------------------

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Resolve JSON folder for matches
possible_json_folders = [
    "/opt/airflow/t20s_json",
    os.path.join(BASE_DIR, "t20s_json"),
    os.path.join(BASE_DIR, "..", "t20s_json"),
    "t20s_json",
]
JSON_FOLDER = "/opt/airflow/t20s_json"
for f in possible_json_folders:
    if os.path.exists(f):
        JSON_FOLDER = f
        break

# Resolve detailed squad JSON
possible_player_jsons = [
    "/opt/airflow/India/Data/India_squad_detailed.json",
    "/opt/airflow/India/Data/cricket_squad_detailed.json",
    os.path.join(BASE_DIR, "Cricket", "Data", "cricket_squad_detailed.json"),
    os.path.join(BASE_DIR, "..", "Cricket", "Data", "cricket_squad_detailed.json"),
    "Cricket/Data/cricket_squad_detailed.json",
    "India/Data/India_squad_detailed.json",
]
PLAYER_JSON = "/opt/airflow/India/Data/India_squad_detailed.json"
for p in possible_player_jsons:
    if os.path.exists(p) and os.path.getsize(p) > 200:
        PLAYER_JSON = p
        break

DB_CONFIG = dict(
    host=os.getenv("DB_HOST", "host.docker.internal" if os.path.exists("/.dockerenv") else "localhost"),
    database=os.getenv("DB_NAME", "t20i_cricket_analytics"),
    user=os.getenv("DB_USER", "postgres"),
    password=os.getenv("DB_PASSWORD", "postgres"),
    port=os.getenv("DB_PORT", "5432"),
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
    print("\n" + "=" * 50)
    print("STEP 1: Importing Players")
    print("=" * 50)
    print(f"Reading: {PLAYER_JSON}")

    if not os.path.exists(PLAYER_JSON):
        print(f"Warning: Player JSON not found at {PLAYER_JSON}, skipping players import.")
        return

    with open(PLAYER_JSON, "r", encoding="utf-8") as f:
        data = json.load(f)

    inserted = 0
    updated = 0

    for country, players in data.items():
        if not isinstance(players, list):
            continue

        for player in players:
            if not isinstance(player, dict) or not player.get("name"):
                continue

            name        = player.get("name")
            profile_url = player.get("profile_url")
            image_url   = player.get("image_url")
            personal    = player.get("personal_info", {})
            role        = personal.get("Role")
            bat_style   = personal.get("Batting Style")
            bowl_style  = personal.get("Bowling Style")

            batting     = player.get("batting_career_stats", {})
            bat_mat     = to_int(batting.get("Mat"))
            bat_inns    = to_int(batting.get("Inns"))
            bat_no      = to_int(batting.get("NO"))
            bat_runs    = to_int(batting.get("Runs"))
            bat_hs      = batting.get("HS")
            bat_ave     = to_float(batting.get("Ave"))
            bat_bf      = to_int(batting.get("BF"))
            bat_sr      = to_float(batting.get("SR"))
            bat_100s    = to_int(batting.get("100s"))
            bat_50s     = to_int(batting.get("50s"))
            bat_4s      = to_int(batting.get("4s"))
            bat_6s      = to_int(batting.get("6s"))
            bat_ct      = to_int(batting.get("Ct"))
            bat_st      = to_int(batting.get("St"))

            bowling     = player.get("bowling_career_stats", {})
            bowl_mat    = to_int(bowling.get("Mat"))
            bowl_inns   = to_int(bowling.get("Inns"))
            bowl_balls  = to_int(bowling.get("Balls"))
            bowl_runs   = to_int(bowling.get("Runs"))
            bowl_wkts   = to_int(bowling.get("Wkts"))
            bowl_bbi    = bowling.get("BBI")
            bowl_bbm    = bowling.get("BBM")
            bowl_ave    = to_float(bowling.get("Ave"))
            bowl_econ   = to_float(bowling.get("Econ"))
            bowl_sr     = to_float(bowling.get("SR"))
            bowl_4w     = to_int(bowling.get("4w"))
            bowl_5w     = to_int(bowling.get("5w"))
            bowl_10w    = to_int(bowling.get("10w"))

            cursor.execute("""
                INSERT INTO players (
                    name, country, profile_url, image_url,
                    role, batting_style, bowling_style,
                    batting_matches, batting_innings, not_outs, runs,
                    highest_score, batting_average, balls_faced,
                    batting_strike_rate, hundreds, fifties, fours, sixes,
                    catches, stumpings,
                    bowling_matches, bowling_innings, balls_bowled, runs_conceded,
                    wickets, best_bowling_innings, best_bowling_match,
                    bowling_average, economy_rate, bowling_strike_rate,
                    four_wickets, five_wickets, ten_wickets
                )
                VALUES (
                    %s, %s, %s, %s,
                    %s, %s, %s,
                    %s, %s, %s, %s,
                    %s, %s, %s,
                    %s, %s, %s, %s, %s,
                    %s, %s,
                    %s, %s, %s, %s,
                    %s, %s, %s,
                    %s, %s, %s,
                    %s, %s, %s
                )
                ON CONFLICT (name, country)
                DO UPDATE SET
                    profile_url          = EXCLUDED.profile_url,
                    image_url            = EXCLUDED.image_url,
                    role                 = EXCLUDED.role,
                    batting_style        = EXCLUDED.batting_style,
                    bowling_style        = EXCLUDED.bowling_style,
                    batting_matches      = EXCLUDED.batting_matches,
                    batting_innings      = EXCLUDED.batting_innings,
                    not_outs             = EXCLUDED.not_outs,
                    runs                 = EXCLUDED.runs,
                    highest_score        = EXCLUDED.highest_score,
                    batting_average      = EXCLUDED.batting_average,
                    balls_faced          = EXCLUDED.balls_faced,
                    batting_strike_rate  = EXCLUDED.batting_strike_rate,
                    hundreds             = EXCLUDED.hundreds,
                    fifties              = EXCLUDED.fifties,
                    fours                = EXCLUDED.fours,
                    sixes                = EXCLUDED.sixes,
                    catches              = EXCLUDED.catches,
                    stumpings            = EXCLUDED.stumpings,
                    bowling_matches      = EXCLUDED.bowling_matches,
                    bowling_innings      = EXCLUDED.bowling_innings,
                    balls_bowled         = EXCLUDED.balls_bowled,
                    runs_conceded        = EXCLUDED.runs_conceded,
                    wickets              = EXCLUDED.wickets,
                    best_bowling_innings = EXCLUDED.best_bowling_innings,
                    best_bowling_match   = EXCLUDED.best_bowling_match,
                    bowling_average      = EXCLUDED.bowling_average,
                    economy_rate         = EXCLUDED.economy_rate,
                    bowling_strike_rate  = EXCLUDED.bowling_strike_rate,
                    four_wickets         = EXCLUDED.four_wickets,
                    five_wickets         = EXCLUDED.five_wickets,
                    ten_wickets          = EXCLUDED.ten_wickets
            """, (
                name, country, profile_url, image_url,
                role, bat_style, bowl_style,
                bat_mat, bat_inns, bat_no, bat_runs,
                bat_hs, bat_ave, bat_bf,
                bat_sr, bat_100s, bat_50s, bat_4s, bat_6s,
                bat_ct, bat_st,
                bowl_mat, bowl_inns, bowl_balls, bowl_runs,
                bowl_wkts, bowl_bbi, bowl_bbm,
                bowl_ave, bowl_econ, bowl_sr,
                bowl_4w, bowl_5w, bowl_10w,
            ))
            inserted += 1

    conn.commit()
    print(f"  -> {inserted} players processed.")


# --- Step 2: Import Matches ---------------------------------------------------

def import_matches(cursor, conn):
    print("\n" + "=" * 50)
    print("STEP 2: Importing Matches")
    print("=" * 50)

    if not os.path.exists(JSON_FOLDER):
        print(f"Warning: JSON folder not found at {JSON_FOLDER}, skipping matches import.")
        return

    count = 0
    skipped = 0

    for filename in os.listdir(JSON_FOLDER):
        if not filename.endswith(".json"):
            continue

        file_path = os.path.join(JSON_FOLDER, filename)
        with open(file_path, "r", encoding="utf-8") as file:
            data = json.load(file)

        info = data.get("info", {})
        teams = info.get("teams", [])
        if len(teams) < 2:
            skipped += 1
            continue

        team1, team2 = teams[0], teams[1]
        dates = info.get("dates", [])
        match_date = dates[0] if dates else None
        venue = info.get("venue")
        city = info.get("city")
        match_type = info.get("match_type")
        gender = info.get("gender")
        event = info.get("event", {})
        series_name = event.get("name")
        season = info.get("season")
        match_type_number = info.get("match_type_number")

        toss = info.get("toss", {})
        toss_winner = toss.get("winner")
        toss_decision = toss.get("decision")

        outcome = info.get("outcome", {})
        winner = outcome.get("winner")
        by = outcome.get("by", {})
        win_by_runs = by.get("runs")
        win_by_wickets = by.get("wickets")
        result = outcome.get("result")
        player_of_match_list = info.get("player_of_match", [])
        player_of_match = player_of_match_list[0] if player_of_match_list else None

        cursor.execute("""
            INSERT INTO matches (
                match_id, team1, team2, match_date, venue, city,
                match_type, gender, series_name, season, match_type_number,
                toss_winner, toss_decision, winner, win_by_runs,
                win_by_wickets, result, player_of_match
            )
            VALUES (
                %s, %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s,
                %s, %s, %s, %s,
                %s, %s, %s
            )
            ON CONFLICT (match_id) DO NOTHING
        """, (
            filename.replace(".json", ""), team1, team2, match_date, venue, city,
            match_type, gender, series_name, season, match_type_number,
            toss_winner, toss_decision, winner, win_by_runs,
            win_by_wickets, result, player_of_match,
        ))

        count += 1

    conn.commit()
    print(f"  -> {count} matches processed, {skipped} skipped.")


# --- Step 3: Import Deliveries ------------------------------------------------

def import_deliveries(cursor, conn):
    print("\n" + "=" * 50)
    print("STEP 3: Importing Deliveries")
    print("=" * 50)

    if not os.path.exists(JSON_FOLDER):
        print(f"Warning: JSON folder not found at {JSON_FOLDER}, skipping deliveries import.")
        return

    count = 0
    skipped = 0

    for filename in os.listdir(JSON_FOLDER):
        if not filename.endswith(".json"):
            continue

        file_path = os.path.join(JSON_FOLDER, filename)
        with open(file_path, "r", encoding="utf-8") as file:
            data = json.load(file)

        raw_match_id = filename.replace(".json", "")

        cursor.execute("SELECT id FROM matches WHERE match_id = %s", (raw_match_id,))
        match_row = cursor.fetchone()
        if not match_row:
            skipped += 1
            continue

        match_id = match_row[0]

        innings_list = data.get("innings", [])
        for innings_index, innings_data in enumerate(innings_list, start=1):
            batting_team = innings_data.get("team")
            overs = innings_data.get("overs", [])

            for over_data in overs:
                over_number = over_data.get("over")
                phase = get_phase(over_number)

                for ball_number, delivery in enumerate(over_data.get("deliveries", []), start=1):
                    batter = delivery.get("batter")
                    non_striker = delivery.get("non_striker")
                    bowler = delivery.get("bowler")

                    runs = delivery.get("runs", {})
                    batter_runs = runs.get("batter", 0)
                    extras_runs = runs.get("extras", 0)
                    total_runs = runs.get("total", 0)

                    extras = delivery.get("extras", {})
                    wides = extras.get("wides", 0)
                    no_balls = extras.get("noballs", 0)
                    byes = extras.get("byes", 0)
                    leg_byes = extras.get("legbyes", 0)

                    wickets = delivery.get("wickets", [])
                    is_wicket = len(wickets) > 0
                    player_out = None
                    dismissal_type = None

                    if wickets:
                        first_wicket = wickets[0]
                        player_out = first_wicket.get("player_out")
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
        count += 1

    print(f"  -> {count} matches deliveries imported, {skipped} skipped.")


# --- Main ---------------------------------------------------------------------

if __name__ == "__main__":
    print(f"Connecting to database {DB_CONFIG['host']}:{DB_CONFIG['port']}/{DB_CONFIG['database']}...")
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()

        import_players(cursor, conn)
        import_matches(cursor, conn)
        import_deliveries(cursor, conn)

        print("\n" + "=" * 60)
        print("All data imported successfully!")
        print("=" * 60)

    except Exception as e:
        if 'conn' in locals() and conn:
            conn.rollback()
        print(f"\nError: {e}")
        raise

    finally:
        if 'cursor' in locals() and cursor:
            cursor.close()
        if 'conn' in locals() and conn:
            conn.close()
        print("Database connection closed.")
