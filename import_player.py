import os
import json
import psycopg2

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
JSON_FILE = os.path.join(BASE_DIR, "Cricket", "Data", "cricket_squad_detailed.json")
if not os.path.exists(JSON_FILE):
    JSON_FILE = os.path.join(BASE_DIR, "Data", "cricket_squad_detailed.json")

conn = psycopg2.connect(
    host="localhost",
    database="t20i_cricket_analytics",
    user="postgres",
    password="postgres",
    port="5432"
)

cursor = conn.cursor()

cursor.execute(
    """
    CREATE TABLE IF NOT EXISTS players (
        player_id SERIAL PRIMARY KEY,
        name VARCHAR(255),
        team VARCHAR(255),
        profile_url TEXT,
        image_url TEXT,
        role VARCHAR(100),
        batting_style VARCHAR(100),
        bowling_style VARCHAR(100),
        batting_matches INT,
        batting_innings INT,
        batting_not_out INT,
        batting_runs INT,
        batting_highest VARCHAR(50),
        batting_average NUMERIC,
        batting_balls INT,
        batting_strike_rate NUMERIC,
        batting_100s INT,
        batting_50s INT,
        batting_4s INT,
        batting_6s INT,
        catches INT,
        stumpings INT,
        bowling_matches INT,
        bowling_innings INT,
        bowling_balls INT,
        bowling_runs INT,
        bowling_wickets INT,
        bowling_bbi VARCHAR(50),
        bowling_bbm VARCHAR(50),
        bowling_average NUMERIC,
        bowling_economy NUMERIC,
        bowling_strike_rate NUMERIC,
        bowling_4w INT,
        bowling_5w INT,
        bowling_10w INT,
        UNIQUE (name, team)
    );
    ALTER TABLE players ADD COLUMN IF NOT EXISTS player_id SERIAL;
    CREATE UNIQUE INDEX IF NOT EXISTS idx_players_player_id ON players (player_id);
    """
)
conn.commit()


def to_int(value):
    if value is None or value == "" or value == "-":
        return None

    try:
        return int(str(value).replace(",", ""))
    except:
        return None


def to_float(value):
    if value is None or value == "" or value == "-":
        return None

    try:
        return float(str(value).replace(",", ""))
    except:
        return None


with open(
    JSON_FILE,
    "r",
    encoding="utf-8"
) as file:

    data = json.load(file)


for team, players in data.items():

    for player in players:

        name = player.get("name")
        profile_url = player.get("profile_url")
        image_url = player.get("image_url")

        personal = player.get(
            "personal_info",
            {}
        )

        batting = player.get(
            "batting_career_stats",
            {}
        )

        bowling = player.get(
            "bowling_career_stats",
            {}
        )

        cursor.execute(
            """
            INSERT INTO players (

                name,
                team,

                profile_url,
                image_url,

                role,
                batting_style,
                bowling_style,

                batting_matches,
                batting_innings,
                batting_not_out,
                batting_runs,
                batting_highest,
                batting_average,
                batting_balls,
                batting_strike_rate,
                batting_100s,
                batting_50s,
                batting_4s,
                batting_6s,
                catches,
                stumpings,

                bowling_matches,
                bowling_innings,
                bowling_balls,
                bowling_runs,
                bowling_wickets,
                bowling_bbi,
                bowling_bbm,
                bowling_average,
                bowling_economy,
                bowling_strike_rate,
                bowling_4w,
                bowling_5w,
                bowling_10w

            )

            VALUES (

                %s, %s,

                %s, %s,

                %s, %s, %s,

                %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s,
                %s, %s, %s, %s,

                %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s,
                %s, %s, %s

            )

            ON CONFLICT (name, team)

            DO UPDATE SET

                profile_url = EXCLUDED.profile_url,
                image_url = EXCLUDED.image_url,

                role = EXCLUDED.role,
                batting_style = EXCLUDED.batting_style,
                bowling_style = EXCLUDED.bowling_style,

                batting_matches = EXCLUDED.batting_matches,
                batting_innings = EXCLUDED.batting_innings,
                batting_not_out = EXCLUDED.batting_not_out,
                batting_runs = EXCLUDED.batting_runs,
                batting_highest = EXCLUDED.batting_highest,
                batting_average = EXCLUDED.batting_average,
                batting_balls = EXCLUDED.batting_balls,
                batting_strike_rate = EXCLUDED.batting_strike_rate,
                batting_100s = EXCLUDED.batting_100s,
                batting_50s = EXCLUDED.batting_50s,
                batting_4s = EXCLUDED.batting_4s,
                batting_6s = EXCLUDED.batting_6s,
                catches = EXCLUDED.catches,
                stumpings = EXCLUDED.stumpings,

                bowling_matches = EXCLUDED.bowling_matches,
                bowling_innings = EXCLUDED.bowling_innings,
                bowling_balls = EXCLUDED.bowling_balls,
                bowling_runs = EXCLUDED.bowling_runs,
                bowling_wickets = EXCLUDED.bowling_wickets,
                bowling_bbi = EXCLUDED.bowling_bbi,
                bowling_bbm = EXCLUDED.bowling_bbm,
                bowling_average = EXCLUDED.bowling_average,
                bowling_economy = EXCLUDED.bowling_economy,
                bowling_strike_rate = EXCLUDED.bowling_strike_rate,
                bowling_4w = EXCLUDED.bowling_4w,
                bowling_5w = EXCLUDED.bowling_5w,
                bowling_10w = EXCLUDED.bowling_10w
            """,

            (

                name,
                team,

                profile_url,
                image_url,

                personal.get("Role"),
                personal.get("Batting Style"),
                personal.get("Bowling Style"),

                to_int(batting.get("Mat")),
                to_int(batting.get("Inns")),
                to_int(batting.get("NO")),
                to_int(batting.get("Runs")),
                batting.get("HS"),
                to_float(batting.get("Ave")),
                to_int(batting.get("BF")),
                to_float(batting.get("SR")),
                to_int(batting.get("100s")),
                to_int(batting.get("50s")),
                to_int(batting.get("4s")),
                to_int(batting.get("6s")),
                to_int(batting.get("Ct")),
                to_int(batting.get("St")),

                to_int(bowling.get("Mat")),
                to_int(bowling.get("Inns")),
                to_int(bowling.get("Balls")),
                to_int(bowling.get("Runs")),
                to_int(bowling.get("Wkts")),
                bowling.get("BBI"),
                bowling.get("BBM"),
                to_float(bowling.get("Ave")),
                to_float(bowling.get("Econ")),
                to_float(bowling.get("SR")),
                to_int(bowling.get("4w")),
                to_int(bowling.get("5w")),
                to_int(bowling.get("10w"))

            )
        )


conn.commit()

print("Players imported successfully.")


cursor.close()
conn.close()