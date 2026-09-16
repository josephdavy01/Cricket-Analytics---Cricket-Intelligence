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


def get_phase(over_number):
    if over_number <= 5:
        return "Powerplay"
    elif over_number <= 14:
        return "Middle"
    else:
        return "Death"


for filename in os.listdir(JSON_FOLDER):

    if not filename.endswith(".json"):
        continue

    cursor.execute(
        """
        SELECT match_id
        FROM matches
        WHERE source_file = %s
        """,
        (filename,)
    )

    row = cursor.fetchone()

    if row is None:
        print("Skipping:", filename, "- match not found")
        continue

    match_id = row[0]

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

    innings_list = data.get(
        "innings",
        []
    )

    cursor.execute(
        """
        DELETE FROM deliveries
        WHERE match_id = %s
        """,
        (match_id,)
    )

    for innings_index, innings_data in enumerate(
        innings_list,
        start=1
    ):

        batting_team = innings_data.get(
            "team"
        )

        overs = innings_data.get(
            "overs",
            []
        )

        for over_data in overs:

            over_number = over_data.get(
                "over"
            )

            phase = get_phase(
                over_number
            )

            deliveries = over_data.get(
                "deliveries",
                []
            )

            for delivery in deliveries:

                actual_delivery = delivery.get(
                    "actual_delivery"
                )

                ball_number = (
                    str(actual_delivery)
                    if actual_delivery is not None
                    else None
                )

                batter = delivery.get(
                    "batter"
                )

                non_striker = delivery.get(
                    "non_striker"
                )

                bowler = delivery.get(
                    "bowler"
                )

                runs = delivery.get(
                    "runs",
                    {}
                )

                batter_runs = runs.get(
                    "batter",
                    0
                )

                extras_runs = runs.get(
                    "extras",
                    0
                )

                total_runs = runs.get(
                    "total",
                    0
                )

                extras = delivery.get(
                    "extras",
                    {}
                )

                wides = extras.get(
                    "wides",
                    0
                )

                no_balls = extras.get(
                    "noballs",
                    0
                )

                byes = extras.get(
                    "byes",
                    0
                )

                leg_byes = extras.get(
                    "legbyes",
                    0
                )

                wickets = delivery.get(
                    "wickets",
                    []
                )

                is_wicket = (
                    len(wickets) > 0
                )

                player_out = None
                dismissal_type = None

                if wickets:
                    first_wicket = wickets[0]

                    player_out = first_wicket.get(
                        "player_out"
                    )

                    dismissal_type = first_wicket.get(
                        "kind"
                    )

                cursor.execute(
                    """
                    INSERT INTO deliveries (
                        match_id,
                        innings,
                        batting_team,
                        over_number,
                        ball_number,
                        batter,
                        non_striker,
                        bowler,
                        batter_runs,
                        extras_runs,
                        total_runs,
                        wides,
                        no_balls,
                        byes,
                        leg_byes,
                        is_wicket,
                        player_out,
                        dismissal_type,
                        phase
                    )

                    VALUES (
                        %s, %s, %s, %s, %s,
                        %s, %s, %s, %s, %s,
                        %s, %s, %s, %s, %s,
                        %s, %s, %s, %s
                    )
                    """,
                    (
                        match_id,
                        innings_index,
                        batting_team,
                        over_number,
                        ball_number,
                        batter,
                        non_striker,
                        bowler,
                        batter_runs,
                        extras_runs,
                        total_runs,
                        wides,
                        no_balls,
                        byes,
                        leg_byes,
                        is_wicket,
                        player_out,
                        dismissal_type,
                        phase
                    )
                )

    conn.commit()

    print(
        "Imported deliveries:",
        filename
    )


print(
    "\nAll deliveries imported successfully."
)

cursor.close()
conn.close()