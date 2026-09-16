import json
import os
import psycopg2

JSON_FOLDER = r"C:\Users\josep\OneDrive\Desktop\Cricket\t20s_json"

conn = psycopg2.connect(
    host="localhost",
    database="t20i_cricket_analytics",
    user="postgres",
    password="postgres",
    port="5432"
)

cursor = conn.cursor()

for filename in os.listdir(JSON_FOLDER):

    if not filename.endswith(".json"):
        continue

    file_path = os.path.join(
        JSON_FOLDER,
        filename
    )

    with open(
        file_path,
        "r",
        encoding="utf-8"
    ) as file:
        data = json.load(file)

    info = data.get(
        "info",
        {}
    )

    teams = info.get(
        "teams",
        []
    )

    if len(teams) < 2:
        print(
            "Skipping:",
            filename,
            "- teams missing"
        )
        continue

    team1 = teams[0]
    team2 = teams[1]

    dates = info.get(
        "dates",
        []
    )

    match_date = (
        dates[0]
        if dates
        else None
    )

    season = info.get(
        "season"
    )

    venue = info.get(
        "venue"
    )

    city = info.get(
        "city"
    )

    toss = info.get(
        "toss",
        {}
    )

    toss_winner = toss.get(
        "winner"
    )

    toss_decision = toss.get(
        "decision"
    )

    outcome = info.get(
        "outcome",
        {}
    )

    winner = outcome.get(
        "winner"
    )

    result_type = outcome.get(
        "result"
    )

    if winner:
        result_type = "winner"

    elif result_type:
        result_type = str(
            result_type
        )

    elif outcome.get("eliminator"):
        result_type = "tie/eliminator"

    else:
        result_type = "unknown"

    event = info.get(
        "event",
        {}
    )

    event_name = event.get(
        "name"
    )

    match_number = event.get(
        "match_number"
    )

    if match_number is not None:
        match_number = str(
            match_number
        )

    match_type = info.get(
        "match_type"
    )

    cursor.execute(
        """
        INSERT INTO matches (
            source_file,
            match_date,
            season,
            team1,
            team2,
            venue,
            city,
            toss_winner,
            toss_decision,
            winner,
            result_type,
            event_name,
            match_number,
            match_type
        )

        VALUES (
            %s, %s, %s, %s, %s,
            %s, %s, %s, %s, %s,
            %s, %s, %s, %s
        )

        ON CONFLICT (source_file)

        DO UPDATE SET
            match_date = EXCLUDED.match_date,
            season = EXCLUDED.season,
            team1 = EXCLUDED.team1,
            team2 = EXCLUDED.team2,
            venue = EXCLUDED.venue,
            city = EXCLUDED.city,
            toss_winner = EXCLUDED.toss_winner,
            toss_decision = EXCLUDED.toss_decision,
            winner = EXCLUDED.winner,
            result_type = EXCLUDED.result_type,
            event_name = EXCLUDED.event_name,
            match_number = EXCLUDED.match_number,
            match_type = EXCLUDED.match_type
        """,
        (
            filename,
            match_date,
            season,
            team1,
            team2,
            venue,
            city,
            toss_winner,
            toss_decision,
            winner,
            result_type,
            event_name,
            match_number,
            match_type
        )
    )

    print(
        "Imported/Updated:",
        filename
    )

conn.commit()

print(
    "\nAll matches imported/updated successfully."
)

cursor.close()
conn.close()