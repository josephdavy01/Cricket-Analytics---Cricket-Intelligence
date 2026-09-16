CREATE TABLE players (
    player_id SERIAL PRIMARY KEY,

    name VARCHAR(150) NOT NULL,
    team VARCHAR(100) NOT NULL,

    profile_url TEXT,
    image_url TEXT,

    role VARCHAR(100),
    batting_style VARCHAR(100),
    bowling_style VARCHAR(100),

    batting_matches INTEGER,
    batting_innings INTEGER,
    batting_not_out INTEGER,
    batting_runs INTEGER,
    batting_highest VARCHAR(20),
    batting_average NUMERIC(10,2),
    batting_balls INTEGER,
    batting_strike_rate NUMERIC(10,2),
    batting_100s INTEGER,
    batting_50s INTEGER,
    batting_4s INTEGER,
    batting_6s INTEGER,
    catches INTEGER,
    stumpings INTEGER,

    bowling_matches INTEGER,
    bowling_innings INTEGER,
    bowling_balls INTEGER,
    bowling_runs INTEGER,
    bowling_wickets INTEGER,
    bowling_bbi VARCHAR(30),
    bowling_bbm VARCHAR(30),
    bowling_average NUMERIC(10,2),
    bowling_economy NUMERIC(10,2),
    bowling_strike_rate NUMERIC(10,2),
    bowling_4w INTEGER,
    bowling_5w INTEGER,
    bowling_10w INTEGER,
    is_active BOOLEAN DEFAULT TRUE,

    UNIQUE(name, team)
);

CREATE TABLE matches (
    match_id SERIAL PRIMARY KEY,

    source_file VARCHAR(100) UNIQUE,

    match_date DATE,
    season VARCHAR(20),

    team1 VARCHAR(100),
    team2 VARCHAR(100),

    venue TEXT,
    city VARCHAR(100),

    toss_winner VARCHAR(100),
    toss_decision VARCHAR(20),

    winner VARCHAR(100),

    event_name TEXT,
    match_number VARCHAR(50),

    match_type VARCHAR(20),

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

ALTER TABLE matches
ADD COLUMN result_type VARCHAR(50);

CREATE TABLE deliveries (
    delivery_id BIGSERIAL PRIMARY KEY,

    match_id INTEGER NOT NULL
        REFERENCES matches(match_id)
        ON DELETE CASCADE,

    innings INTEGER NOT NULL,
    batting_team VARCHAR(100),

    over_number INTEGER NOT NULL,
    ball_number NUMERIC(6,2),

    batter VARCHAR(150),
    non_striker VARCHAR(150),
    bowler VARCHAR(150),

    batter_runs INTEGER DEFAULT 0,
    extras_runs INTEGER DEFAULT 0,
    total_runs INTEGER DEFAULT 0,

    wides INTEGER DEFAULT 0,
    no_balls INTEGER DEFAULT 0,
    byes INTEGER DEFAULT 0,
    leg_byes INTEGER DEFAULT 0,

    is_wicket BOOLEAN DEFAULT FALSE,
    player_out VARCHAR(150),
    dismissal_type VARCHAR(100),

    phase VARCHAR(20)
);

ALTER TABLE deliveries
ALTER COLUMN ball_number TYPE VARCHAR(10)
USING ball_number::VARCHAR;

 TRUNCATE TABLE deliveries RESTART IDENTITY;

ALTER TABLE deliveries
ALTER COLUMN ball_number TYPE VARCHAR(10);

ALTER TABLE deliveries
ADD COLUMN batter_id INTEGER,
ADD COLUMN non_striker_id INTEGER,
ADD COLUMN bowler_id INTEGER;

ALTER TABLE deliveries
ADD CONSTRAINT fk_batter
FOREIGN KEY (batter_id)
REFERENCES players(player_id);

ALTER TABLE deliveries
ADD CONSTRAINT fk_non_striker
FOREIGN KEY (non_striker_id)
REFERENCES players(player_id);

ALTER TABLE deliveries
ADD CONSTRAINT fk_bowler
FOREIGN KEY (bowler_id)
REFERENCES players(player_id);

UPDATE deliveries d
SET batter_id = p.player_id
FROM players p
WHERE d.batter = p.name
  AND d.batting_team = p.team;

UPDATE deliveries d
SET non_striker_id = p.player_id
FROM players p
WHERE d.non_striker = p.name
  AND d.batting_team = p.team;

 
UPDATE deliveries d
SET bowler_id = p.player_id
FROM players p, matches m
WHERE d.match_id = m.match_id
  AND d.bowler = p.name
  AND p.team =
      CASE
          WHEN d.batting_team = m.team1
              THEN m.team2
          ELSE m.team1
      END;

TRUNCATE TABLE deliveries RESTART IDENTITY CASCADE;
TRUNCATE TABLE matches RESTART IDENTITY CASCADE;

CREATE TABLE batting_match_stats (
    batting_stat_id BIGSERIAL PRIMARY KEY,

    match_id INTEGER NOT NULL
        REFERENCES matches(match_id)
        ON DELETE CASCADE,

    innings INTEGER NOT NULL,

    player_id INTEGER NOT NULL
        REFERENCES players(player_id),

    team VARCHAR(100),

    runs INTEGER DEFAULT 0,
    balls_faced INTEGER DEFAULT 0,
    fours INTEGER DEFAULT 0,
    sixes INTEGER DEFAULT 0,

    dismissed BOOLEAN DEFAULT FALSE,

    strike_rate NUMERIC(10,2),

    UNIQUE (
        match_id,
        innings,
        player_id
    )
);


INSERT INTO batting_match_stats (
    match_id,
    innings,
    player_id,
    team,
    runs,
    balls_faced,
    fours,
    sixes,
    dismissed,
    strike_rate
)

SELECT
    d.match_id,
    d.innings,
    d.batter_id,
    d.batting_team,

    SUM(d.batter_runs) AS runs,

    COUNT(*) FILTER (
        WHERE d.wides = 0
    ) AS balls_faced,

    COUNT(*) FILTER (
        WHERE d.batter_runs = 4
    ) AS fours,

    COUNT(*) FILTER (
        WHERE d.batter_runs = 6
    ) AS sixes,

    BOOL_OR(
        d.player_out = d.batter
    ) AS dismissed,

    ROUND(
        (
            SUM(d.batter_runs)::NUMERIC * 100
            /
            NULLIF(
                COUNT(*) FILTER (
                    WHERE d.wides = 0
                ),
                0
            )
        ),
        2
    ) AS strike_rate

FROM deliveries d

WHERE d.batter_id IS NOT NULL

GROUP BY
    d.match_id,
    d.innings,
    d.batter_id,
    d.batting_team

ON CONFLICT (
    match_id,
    innings,
    player_id
)

DO UPDATE SET
    team = EXCLUDED.team,
    runs = EXCLUDED.runs,
    balls_faced = EXCLUDED.balls_faced,
    fours = EXCLUDED.fours,
    sixes = EXCLUDED.sixes,
    dismissed = EXCLUDED.dismissed,
    strike_rate = EXCLUDED.strike_rate;


CREATE TABLE bowling_match_stats (
    bowling_stat_id BIGSERIAL PRIMARY KEY,

    match_id INTEGER NOT NULL
        REFERENCES matches(match_id)
        ON DELETE CASCADE,

    innings INTEGER NOT NULL,

    player_id INTEGER NOT NULL
        REFERENCES players(player_id),

    team VARCHAR(100),

    balls_bowled INTEGER DEFAULT 0,
    runs_conceded INTEGER DEFAULT 0,
    wickets INTEGER DEFAULT 0,
    dot_balls INTEGER DEFAULT 0,

    economy NUMERIC(10,2),

    UNIQUE (
        match_id,
        innings,
        player_id
    )
);

WITH bowling_data AS (
    SELECT
        d.match_id,
        d.innings,
        d.bowler_id,

        CASE
            WHEN d.batting_team = m.team1
                THEN m.team2
            ELSE m.team1
        END AS bowling_team,

        COUNT(*) FILTER (
            WHERE d.wides = 0
              AND d.no_balls = 0
        ) AS balls_bowled,

        SUM(
            d.total_runs
            - d.byes
            - d.leg_byes
        ) AS runs_conceded,

        COUNT(*) FILTER (
            WHERE d.is_wicket = TRUE
              AND d.dismissal_type NOT IN (
                  'run out',
                  'retired hurt',
                  'retired out',
                  'obstructing the field'
              )
        ) AS wickets,

        COUNT(*) FILTER (
            WHERE d.total_runs = 0
        ) AS dot_balls

    FROM deliveries d

    JOIN matches m
        ON d.match_id = m.match_id

    WHERE d.bowler_id IS NOT NULL

    GROUP BY
        d.match_id,
        d.innings,
        d.bowler_id,
        bowling_team
)

INSERT INTO bowling_match_stats (
    match_id,
    innings,
    player_id,
    team,
    balls_bowled,
    runs_conceded,
    wickets,
    dot_balls,
    economy
)

SELECT
    match_id,
    innings,
    bowler_id,
    bowling_team,
    balls_bowled,
    runs_conceded,
    wickets,
    dot_balls,

    ROUND(
        runs_conceded::NUMERIC * 6
        / NULLIF(balls_bowled, 0),
        2
    ) AS economy

FROM bowling_data

ON CONFLICT (
    match_id,
    innings,
    player_id
)

DO UPDATE SET
    team = EXCLUDED.team,
    balls_bowled = EXCLUDED.balls_bowled,
    runs_conceded = EXCLUDED.runs_conceded,
    wickets = EXCLUDED.wickets,
    dot_balls = EXCLUDED.dot_balls,
    economy = EXCLUDED.economy;



CREATE OR REPLACE VIEW player_recent_form AS

WITH recent_batting AS (
    SELECT
        b.player_id,
        b.match_id,
        b.runs,
        b.balls_faced,
        b.dismissed,

        ROW_NUMBER() OVER (
            PARTITION BY b.player_id
            ORDER BY m.match_date DESC, b.match_id DESC
        ) AS rn

    FROM batting_match_stats b

    JOIN matches m
        ON b.match_id = m.match_id
),

batting_summary AS (
    SELECT
        player_id,

        COUNT(*) FILTER (
            WHERE rn <= 5
        ) AS batting_innings_used,

        SUM(runs) FILTER (
            WHERE rn <= 5
        ) AS total_runs_last_5_innings,

        SUM(balls_faced) FILTER (
            WHERE rn <= 5
        ) AS total_balls_last_5_innings,

        COUNT(*) FILTER (
            WHERE rn <= 5
              AND dismissed = TRUE
        ) AS dismissals_last_5_innings

    FROM recent_batting

    GROUP BY player_id
),

recent_bowling AS (
    SELECT
        b.player_id,
        b.match_id,
        b.wickets,
        b.dot_balls,
        b.runs_conceded,
        b.balls_bowled,

        ROW_NUMBER() OVER (
            PARTITION BY b.player_id
            ORDER BY m.match_date DESC, b.match_id DESC
        ) AS rn

    FROM bowling_match_stats b

    JOIN matches m
        ON b.match_id = m.match_id
),

bowling_summary AS (
    SELECT
        player_id,

        COUNT(*) FILTER (
            WHERE rn <= 5
        ) AS bowling_matches_used,

        SUM(wickets) FILTER (
            WHERE rn <= 5
        ) AS total_wickets_last_5_matches,

        SUM(dot_balls) FILTER (
            WHERE rn <= 5
        ) AS total_dot_balls,

        SUM(runs_conceded) FILTER (
            WHERE rn <= 5
        ) AS total_runs_conceded,

        SUM(balls_bowled) FILTER (
            WHERE rn <= 5
        ) AS total_balls_bowled

    FROM recent_bowling

    GROUP BY player_id
)

SELECT
    p.player_id,
    p.name,
    p.team,
    p.role,

    COALESCE(
        bs.batting_innings_used,
        0
    ) AS batting_innings_used,

    COALESCE(
        bs.total_runs_last_5_innings,
        0
    ) AS total_runs_last_5_innings,

    COALESCE(
        bs.dismissals_last_5_innings,
        0
    ) AS dismissals_last_5_innings,

    ROUND(
        bs.total_runs_last_5_innings::NUMERIC
        /
        NULLIF(
            bs.dismissals_last_5_innings,
            0
        ),
        2
    ) AS batting_average,

    ROUND(
        bs.total_runs_last_5_innings::NUMERIC * 100
        /
        NULLIF(
            bs.total_balls_last_5_innings,
            0
        ),
        2
    ) AS batting_strike_rate,

    COALESCE(
        bw.bowling_matches_used,
        0
    ) AS bowling_matches_used,

    COALESCE(
        bw.total_wickets_last_5_matches,
        0
    ) AS total_wickets_last_5_matches,

    COALESCE(
        bw.total_dot_balls,
        0
    ) AS total_dot_balls,

    ROUND(
        bw.total_runs_conceded::NUMERIC * 6
        /
        NULLIF(
            bw.total_balls_bowled,
            0
        ),
        2
    ) AS bowling_economy

FROM players p

LEFT JOIN batting_summary bs
    ON p.player_id = bs.player_id

LEFT JOIN bowling_summary bw
    ON p.player_id = bw.player_id;


CREATE VIEW batter_phase_stats AS

SELECT
    d.batter_id AS player_id,
    p.name,
    p.team,
    d.phase,

    COUNT(*) FILTER (
        WHERE d.wides = 0
    ) AS balls_faced,

    SUM(d.batter_runs) AS runs,

    COUNT(*) FILTER (
        WHERE d.batter_runs = 4
    ) AS fours,

    COUNT(*) FILTER (
        WHERE d.batter_runs = 6
    ) AS sixes,

    ROUND(
        SUM(d.batter_runs)::NUMERIC * 100
        /
        NULLIF(
            COUNT(*) FILTER (
                WHERE d.wides = 0
            ),
            0
        ),
        2
    ) AS strike_rate

FROM deliveries d

JOIN players p
    ON d.batter_id = p.player_id

GROUP BY
    d.batter_id,
    p.name,
    p.team,
    d.phase;



CREATE VIEW bowler_phase_stats AS

SELECT
    d.bowler_id AS player_id,
    p.name,
    p.team,
    d.phase,

    COUNT(*) FILTER (
        WHERE d.wides = 0
          AND d.no_balls = 0
    ) AS balls_bowled,

    SUM(
        d.total_runs
        - d.byes
        - d.leg_byes
    ) AS runs_conceded,

    COUNT(*) FILTER (
        WHERE d.is_wicket = TRUE
          AND d.dismissal_type NOT IN (
              'run out',
              'retired hurt',
              'retired out',
              'obstructing the field'
          )
    ) AS wickets,

    COUNT(*) FILTER (
        WHERE d.total_runs = 0
    ) AS dot_balls,

    ROUND(
        SUM(
            d.total_runs
            - d.byes
            - d.leg_byes
        )::NUMERIC * 6
        /
        NULLIF(
            COUNT(*) FILTER (
                WHERE d.wides = 0
                  AND d.no_balls = 0
            ),
            0
        ),
        2
    ) AS economy

FROM deliveries d

JOIN players p
    ON d.bowler_id = p.player_id

GROUP BY
    d.bowler_id,
    p.name,
    p.team,
    d.phase;



CREATE VIEW batter_bowler_head_to_head AS

SELECT
    d.batter_id,
    batter.name AS batter,
    batter.team AS batter_team,

    d.bowler_id,
    bowler.name AS bowler,
    bowler.team AS bowler_team,

    COUNT(*) FILTER (
        WHERE d.wides = 0
    ) AS balls_faced,

    SUM(d.batter_runs) AS runs,

    COUNT(*) FILTER (
        WHERE d.player_out = d.batter
          AND d.dismissal_type NOT IN (
              'run out',
              'retired hurt',
              'retired out',
              'obstructing the field'
          )
    ) AS dismissals,

    COUNT(*) FILTER (
        WHERE d.batter_runs = 4
    ) AS fours,

    COUNT(*) FILTER (
        WHERE d.batter_runs = 6
    ) AS sixes,

    ROUND(
        SUM(d.batter_runs)::NUMERIC * 100
        /
        NULLIF(
            COUNT(*) FILTER (
                WHERE d.wides = 0
            ),
            0
        ),
        2
    ) AS strike_rate

FROM deliveries d

JOIN players batter
    ON d.batter_id = batter.player_id

JOIN players bowler
    ON d.bowler_id = bowler.player_id

GROUP BY
    d.batter_id,
    batter.name,
    batter.team,
    d.bowler_id,
    bowler.name,
    bowler.team;


CREATE VIEW batting_position_performance AS

WITH first_appearance AS (
    SELECT
        d.match_id,
        d.innings,
        d.batter_id,
        d.batting_team,
        MIN(d.delivery_id) AS first_delivery_id
    FROM deliveries d
    WHERE d.batter_id IS NOT NULL
    GROUP BY
        d.match_id,
        d.innings,
        d.batter_id,
        d.batting_team
),

positions AS (
    SELECT
        match_id,
        innings,
        batter_id,
        batting_team,

        ROW_NUMBER() OVER (
            PARTITION BY match_id, innings
            ORDER BY first_delivery_id
        ) AS batting_position

    FROM first_appearance
),

innings_stats AS (
    SELECT
        b.match_id,
        b.innings,
        b.player_id,
        b.team,
        b.runs,
        b.balls_faced,
        b.dismissed,
        p.batting_position

    FROM batting_match_stats b

    JOIN positions p
        ON b.match_id = p.match_id
       AND b.innings = p.innings
       AND b.player_id = p.batter_id
)

SELECT
    i.player_id,
    p.name,
    p.team,
    i.batting_position,

    COUNT(*) AS innings,

    SUM(i.runs) AS runs,

    SUM(i.balls_faced) AS balls_faced,

    COUNT(*) FILTER (
        WHERE i.dismissed = TRUE
    ) AS dismissals,

    ROUND(
        SUM(i.runs)::NUMERIC
        /
        NULLIF(
            COUNT(*) FILTER (
                WHERE i.dismissed = TRUE
            ),
            0
        ),
        2
    ) AS batting_average,

    ROUND(
        SUM(i.runs)::NUMERIC * 100
        /
        NULLIF(SUM(i.balls_faced), 0),
        2
    ) AS strike_rate

FROM innings_stats i

JOIN players p
    ON i.player_id = p.player_id

GROUP BY
    i.player_id,
    p.name,
    p.team,
    i.batting_position;


CREATE VIEW venue_stats AS

WITH innings_scores AS (
    SELECT
        d.match_id,
        d.innings,
        m.venue,

        SUM(d.total_runs) AS innings_score

    FROM deliveries d

    JOIN matches m
        ON d.match_id = m.match_id

    GROUP BY
        d.match_id,
        d.innings,
        m.venue
),

match_context AS (
    SELECT
        m.match_id,
        m.venue,
        m.team1,
        m.team2,
        m.toss_winner,
        m.toss_decision,
        m.winner,

        CASE
            WHEN m.toss_decision = 'bat'
                THEN m.toss_winner

            ELSE
                CASE
                    WHEN m.toss_winner = m.team1
                        THEN m.team2
                    ELSE m.team1
                END
        END AS batting_first_team

    FROM matches m

    WHERE m.winner IS NOT NULL
),

match_scores AS (
    SELECT
        mc.match_id,
        mc.venue,
        mc.winner,
        mc.batting_first_team,

        MAX(
            CASE
                WHEN i.innings = 1
                THEN i.innings_score
            END
        ) AS first_innings_score

    FROM match_context mc

    JOIN innings_scores i
        ON mc.match_id = i.match_id

    GROUP BY
        mc.match_id,
        mc.venue,
        mc.winner,
        mc.batting_first_team
)

SELECT
    venue,

    COUNT(*) AS matches_played,

    ROUND(
        AVG(first_innings_score),
        2
    ) AS avg_first_innings_score,

    COUNT(*) FILTER (
        WHERE winner = batting_first_team
    ) AS defending_wins,

    COUNT(*) FILTER (
        WHERE winner <> batting_first_team
    ) AS chasing_wins,

    ROUND(
        COUNT(*) FILTER (
            WHERE winner = batting_first_team
        )::NUMERIC * 100
        /
        NULLIF(COUNT(*), 0),
        2
    ) AS defending_win_percentage,

    ROUND(
        COUNT(*) FILTER (
            WHERE winner <> batting_first_team
        )::NUMERIC * 100
        /
        NULLIF(COUNT(*), 0),
        2
    ) AS chasing_win_percentage

FROM match_scores

GROUP BY venue;



CREATE VIEW team_venue_stats AS

WITH team_matches AS (

    SELECT
        m.match_id,
        m.match_date,
        m.venue,
        m.team1 AS team,
        m.winner
    FROM matches m

    WHERE m.winner IS NOT NULL

    UNION ALL

    SELECT
        m.match_id,
        m.match_date,
        m.venue,
        m.team2 AS team,
        m.winner
    FROM matches m

    WHERE m.winner IS NOT NULL
)

SELECT
    team,
    venue,

    COUNT(*) AS matches_played,

    COUNT(*) FILTER (
        WHERE winner = team
    ) AS matches_won,

    COUNT(*) FILTER (
        WHERE winner <> team
    ) AS matches_lost,

    ROUND(
        COUNT(*) FILTER (
            WHERE winner = team
        )::NUMERIC * 100
        /
        NULLIF(COUNT(*), 0),
        2
    ) AS win_percentage

FROM team_matches

GROUP BY
    team,
    venue;


CREATE VIEW team_vs_team_stats AS

WITH normalized_matches AS (
    SELECT
        match_id,
        match_date,
        winner,

        LEAST(team1, team2) AS team_a,
        GREATEST(team1, team2) AS team_b

    FROM matches

    WHERE winner IS NOT NULL
),

innings_scores AS (
    SELECT
        d.match_id,
        d.innings,
        d.batting_team,

        SUM(d.total_runs) AS team_score

    FROM deliveries d

    GROUP BY
        d.match_id,
        d.innings,
        d.batting_team
),

match_scores AS (
    SELECT
        n.match_id,
        n.match_date,
        n.team_a,
        n.team_b,
        n.winner,

        MAX(
            CASE
                WHEN i.batting_team = n.team_a
                THEN i.team_score
            END
        ) AS team_a_score,

        MAX(
            CASE
                WHEN i.batting_team = n.team_b
                THEN i.team_score
            END
        ) AS team_b_score

    FROM normalized_matches n

    JOIN innings_scores i
        ON n.match_id = i.match_id

    GROUP BY
        n.match_id,
        n.match_date,
        n.team_a,
        n.team_b,
        n.winner
)

SELECT
    team_a,
    team_b,

    COUNT(*) AS matches_played,

    COUNT(*) FILTER (
        WHERE winner = team_a
    ) AS team_a_wins,

    COUNT(*) FILTER (
        WHERE winner = team_b
    ) AS team_b_wins,

    ROUND(
        COUNT(*) FILTER (
            WHERE winner = team_a
        )::NUMERIC * 100
        /
        NULLIF(COUNT(*), 0),
        2
    ) AS team_a_win_percentage,

    ROUND(
        COUNT(*) FILTER (
            WHERE winner = team_b
        )::NUMERIC * 100
        /
        NULLIF(COUNT(*), 0),
        2
    ) AS team_b_win_percentage,

    ROUND(
        AVG(team_a_score),
        2
    ) AS team_a_average_score,

    ROUND(
        AVG(team_b_score),
        2
    ) AS team_b_average_score,

    MAX(team_a_score)
        AS team_a_highest_score,

    MAX(team_b_score)
        AS team_b_highest_score

FROM match_scores

GROUP BY
    team_a,
    team_b;



CREATE VIEW team_toss_situation_stats AS

WITH team_matches AS (

    SELECT
        m.match_id,
        m.match_date,
        m.team1 AS team,
        m.team1,
        m.team2,
        m.toss_winner,
        m.toss_decision,
        m.winner
    FROM matches m
    WHERE m.winner IS NOT NULL

    UNION ALL

    SELECT
        m.match_id,
        m.match_date,
        m.team2 AS team,
        m.team1,
        m.team2,
        m.toss_winner,
        m.toss_decision,
        m.winner
    FROM matches m
    WHERE m.winner IS NOT NULL
),

match_context AS (

    SELECT
        match_id,
        match_date,
        team,
        winner,

        CASE
            WHEN toss_winner = team
                THEN 'Won Toss'
            ELSE 'Lost Toss'
        END AS toss_result,

        CASE
            WHEN (
                toss_winner = team
                AND toss_decision = 'bat'
            )
            OR (
                toss_winner <> team
                AND toss_decision = 'field'
            )
                THEN 'Batting First'

            ELSE 'Chasing'
        END AS batting_situation

    FROM team_matches
)

SELECT
    team,
    toss_result,
    batting_situation,

    COUNT(*) AS matches_played,

    COUNT(*) FILTER (
        WHERE winner = team
    ) AS matches_won,

    COUNT(*) FILTER (
        WHERE winner <> team
    ) AS matches_lost,

    ROUND(
        COUNT(*) FILTER (
            WHERE winner = team
        )::NUMERIC * 100
        /
        NULLIF(COUNT(*), 0),
        2
    ) AS win_percentage

FROM match_context

GROUP BY
    team,
    toss_result,
    batting_situation;




CREATE VIEW match_momentum AS

WITH over_summary AS (
    SELECT
        d.match_id,
        d.innings,
        d.batting_team,
        d.over_number + 1 AS over_number,

        SUM(d.total_runs) AS runs_in_over,

        COUNT(*) FILTER (
            WHERE d.is_wicket = TRUE
        ) AS wickets_in_over

    FROM deliveries d

    GROUP BY
        d.match_id,
        d.innings,
        d.batting_team,
        d.over_number
)

SELECT
    match_id,
    innings,
    batting_team,
    over_number,
    runs_in_over,
    wickets_in_over,

    SUM(runs_in_over) OVER (
        PARTITION BY match_id, innings
        ORDER BY over_number
    ) AS cumulative_score,

    SUM(wickets_in_over) OVER (
        PARTITION BY match_id, innings
        ORDER BY over_number
    ) AS cumulative_wickets

FROM over_summary;




CREATE VIEW team_recent_strength AS

WITH innings_scores AS (
    SELECT
        d.match_id,
        d.innings,
        d.batting_team AS team,
        m.match_date,

        SUM(d.total_runs) AS team_score,

        COUNT(*) FILTER (
            WHERE d.is_wicket = TRUE
        ) AS wickets_lost

    FROM deliveries d

    JOIN matches m
        ON d.match_id = m.match_id

    WHERE m.winner IS NOT NULL

    GROUP BY
        d.match_id,
        d.innings,
        d.batting_team,
        m.match_date
),

team_matches AS (
    SELECT
        i.match_id,
        i.match_date,
        i.team,
        i.team_score,

        CASE
            WHEN i.team = m.team1 THEN m.team2
            ELSE m.team1
        END AS opponent,

        opp.wickets_lost AS wickets_taken

    FROM innings_scores i

    JOIN matches m
        ON i.match_id = m.match_id

    JOIN innings_scores opp
        ON i.match_id = opp.match_id
       AND i.innings <> opp.innings

    WHERE m.winner IS NOT NULL
),

ranked_matches AS (
    SELECT
        *,

        ROW_NUMBER() OVER (
            PARTITION BY team
            ORDER BY match_date DESC, match_id DESC
        ) AS rn

    FROM team_matches
),

last_5 AS (
    SELECT *
    FROM ranked_matches
    WHERE rn <= 5
),

batting_wickets AS (
    SELECT
        team,

        COUNT(*) AS matches_used,

        SUM(team_score) AS total_runs_last_5_matches,

        ROUND(
            AVG(team_score),
            2
        ) AS avg_score_last_5_matches,

        SUM(wickets_taken) AS wickets_last_5_matches

    FROM last_5

    GROUP BY team
),

bowling AS (
    SELECT
        b.team,

        ROUND(
            SUM(b.runs_conceded)::NUMERIC * 6
            /
            NULLIF(
                SUM(b.balls_bowled),
                0
            ),
            2
        ) AS economy_last_5_matches,

        SUM(b.dot_balls) AS dot_balls_last_5_matches

    FROM bowling_match_stats b

    JOIN last_5 l
        ON b.team = l.team
       AND b.match_id = l.match_id

    GROUP BY b.team
)

SELECT
    bw.team,
    bw.matches_used,
    bw.total_runs_last_5_matches,
    bw.avg_score_last_5_matches,
    bw.wickets_last_5_matches,
    bl.economy_last_5_matches,
    bl.dot_balls_last_5_matches

FROM batting_wickets bw

LEFT JOIN bowling bl
    ON bw.team = bl.team;



CREATE VIEW player_performance_score AS

WITH raw_scores AS (
    SELECT
        player_id,
        name,
        team,
        role,

        total_runs_last_5_innings,
        batting_average,
        batting_strike_rate,

        total_wickets_last_5_matches,
        total_dot_balls,
        bowling_economy,

        CASE
            WHEN role IN (
                'Batter',
                'Opening Batter',
                'Wicketkeeper Batter'
            ) THEN
                COALESCE(total_runs_last_5_innings, 0)
                + COALESCE(batting_strike_rate, 0)
                + COALESCE(batting_average, 0)

            WHEN role IN (
                'Allrounder',
                'Batting Allrounder',
                'Bowling Allrounder'
            ) THEN
                COALESCE(total_runs_last_5_innings, 0)
                + COALESCE(batting_strike_rate, 0)
                + COALESCE(batting_average, 0)
                + COALESCE(total_wickets_last_5_matches, 0) * 20
                + COALESCE(total_dot_balls, 0)

            WHEN role = 'Bowler' THEN
                COALESCE(total_wickets_last_5_matches, 0) * 25
                + COALESCE(total_dot_balls, 0)
                + CASE
                    WHEN bowling_economy IS NOT NULL
                    THEN GREATEST(0, 12 - bowling_economy) * 10
                    ELSE 0
                  END

            ELSE
                COALESCE(total_runs_last_5_innings, 0)
                + COALESCE(total_wickets_last_5_matches, 0) * 20
        END AS raw_score,

        CASE
            WHEN role IN (
                'Batter',
                'Opening Batter'
            ) THEN 'Batter'

            WHEN role = 'Wicketkeeper Batter'
                THEN 'Wicketkeeper'

            WHEN role IN (
                'Allrounder',
                'Batting Allrounder',
                'Bowling Allrounder'
            ) THEN 'Allrounder'

            WHEN role = 'Bowler'
                THEN 'Bowler'

            ELSE 'Other'
        END AS role_group

    FROM player_recent_form
),

ranked AS (
    SELECT
        *,

        PERCENT_RANK() OVER (
            PARTITION BY role_group
            ORDER BY raw_score
        ) AS percentile

    FROM raw_scores
)

SELECT
    player_id,
    name,
    team,
    role,
    role_group,

    total_runs_last_5_innings,
    batting_average,
    batting_strike_rate,

    total_wickets_last_5_matches,
    total_dot_balls,
    bowling_economy,

    ROUND(
        (50 + percentile * 50)::NUMERIC,
        2
    ) AS performance_score

FROM ranked;



CREATE VIEW eligible_current_players AS

WITH last_played AS (
    SELECT
        player_id,
        MAX(match_date) AS last_match_date
    FROM (
        SELECT
            b.player_id,
            m.match_date
        FROM batting_match_stats b
        JOIN matches m
            ON b.match_id = m.match_id

        UNION

        SELECT
            bw.player_id,
            m.match_date
        FROM bowling_match_stats bw
        JOIN matches m
            ON bw.match_id = m.match_id
    ) x
    GROUP BY player_id
)

SELECT
    p.player_id,
    p.name,
    p.team,
    p.role,
    p.is_active,
    l.last_match_date

FROM players p

LEFT JOIN last_played l
    ON p.player_id = l.player_id

WHERE p.is_active = TRUE
  AND l.last_match_date >= CURRENT_DATE - INTERVAL '6 months';


  CREATE OR REPLACE FUNCTION get_eligible_player_pool(
    input_team VARCHAR
)
RETURNS TABLE (
    player_id INTEGER,
    player_name VARCHAR,
    team VARCHAR,
    role VARCHAR,
    last_match_date DATE,
    selection_pool VARCHAR
)
AS $$
BEGIN

RETURN QUERY

WITH last_played AS (
    SELECT
        x.player_id,
        MAX(x.match_date) AS last_played_date
    FROM (
        SELECT
            b.player_id,
            m.match_date
        FROM batting_match_stats b
        JOIN matches m
            ON b.match_id = m.match_id

        UNION ALL

        SELECT
            bw.player_id,
            m.match_date
        FROM bowling_match_stats bw
        JOIN matches m
            ON bw.match_id = m.match_id
    ) x

    GROUP BY
        x.player_id
),

active_players AS (
    SELECT
        p.player_id AS pid,
        p.name AS pname,
        p.team AS pteam,
        p.role AS prole,
        lp.last_played_date

    FROM players p

    LEFT JOIN last_played lp
        ON p.player_id = lp.player_id

    WHERE p.team = input_team
      AND p.is_active = TRUE
),

pool_count AS (
    SELECT
        COUNT(*) FILTER (
            WHERE ap.last_played_date >=
                CURRENT_DATE - INTERVAL '6 months'
        ) AS six_month_count,

        COUNT(*) FILTER (
            WHERE ap.last_played_date >=
                CURRENT_DATE - INTERVAL '12 months'
        ) AS twelve_month_count

    FROM active_players ap
)

SELECT
    ap.pid::INTEGER,
    ap.pname::VARCHAR,
    ap.pteam::VARCHAR,
    ap.prole::VARCHAR,
    ap.last_played_date::DATE,

    CASE
        WHEN pc.six_month_count >= 15
            THEN 'Last 6 Months'

        WHEN pc.twelve_month_count >= 15
            THEN 'Last 12 Months'

        ELSE
            'All Active Players'
    END::VARCHAR

FROM active_players ap

CROSS JOIN pool_count pc

WHERE
    (
        pc.six_month_count >= 15
        AND ap.last_played_date >=
            CURRENT_DATE - INTERVAL '6 months'
    )

    OR

    (
        pc.six_month_count < 15
        AND pc.twelve_month_count >= 15
        AND ap.last_played_date >=
            CURRENT_DATE - INTERVAL '12 months'
    )

    OR

    (
        pc.six_month_count < 15
        AND pc.twelve_month_count < 15
    )

ORDER BY
    ap.last_played_date DESC NULLS LAST;

END;
$$ LANGUAGE plpgsql;


CREATE OR REPLACE FUNCTION get_eligible_player_pool(
    input_team VARCHAR
)
RETURNS TABLE (
    player_id INTEGER,
    player_name VARCHAR,
    team VARCHAR,
    role VARCHAR,
    last_match_date DATE,
    selection_pool VARCHAR
)
AS $$
BEGIN

RETURN QUERY

WITH last_played AS (
    SELECT
        x.player_id,
        MAX(x.match_date) AS last_played_date
    FROM (
        SELECT
            b.player_id,
            m.match_date
        FROM batting_match_stats b
        JOIN matches m
            ON b.match_id = m.match_id

        UNION ALL

        SELECT
            bw.player_id,
            m.match_date
        FROM bowling_match_stats bw
        JOIN matches m
            ON bw.match_id = m.match_id
    ) x

    GROUP BY
        x.player_id
),

active_players AS (
    SELECT
        p.player_id AS pid,
        p.name AS pname,
        p.team AS pteam,
        p.role AS prole,
        lp.last_played_date

    FROM players p

    LEFT JOIN last_played lp
        ON p.player_id = lp.player_id

    WHERE p.team = input_team
      AND p.is_active = TRUE
),

pool_count AS (
    SELECT
        COUNT(*) FILTER (
            WHERE ap.last_played_date >=
                CURRENT_DATE - INTERVAL '6 months'
        ) AS six_month_count,

        COUNT(*) FILTER (
            WHERE ap.last_played_date >=
                CURRENT_DATE - INTERVAL '12 months'
        ) AS twelve_month_count

    FROM active_players ap
)

SELECT
    ap.pid::INTEGER,
    ap.pname::VARCHAR,
    ap.pteam::VARCHAR,
    ap.prole::VARCHAR,
    ap.last_played_date::DATE,

    CASE
        WHEN pc.six_month_count >= 15
            THEN 'Last 6 Months'

        WHEN pc.twelve_month_count >= 15
            THEN 'Last 12 Months'

        ELSE
            'All Active Players'
    END::VARCHAR

FROM active_players ap

CROSS JOIN pool_count pc

WHERE
    (
        pc.six_month_count >= 15
        AND ap.last_played_date >=
            CURRENT_DATE - INTERVAL '6 months'
    )

    OR

    (
        pc.six_month_count < 15
        AND pc.twelve_month_count >= 15
        AND ap.last_played_date >=
            CURRENT_DATE - INTERVAL '12 months'
    )

    OR

    (
        pc.six_month_count < 15
        AND pc.twelve_month_count < 15
    )

ORDER BY
    ap.last_played_date DESC NULLS LAST;

END;
$$ LANGUAGE plpgsql;



CREATE VIEW active_player_pool AS

WITH last_played AS (
    SELECT
        x.player_id,
        MAX(x.match_date) AS last_match_date
    FROM (
        SELECT
            b.player_id,
            m.match_date
        FROM batting_match_stats b
        JOIN matches m
            ON b.match_id = m.match_id

        UNION ALL

        SELECT
            bw.player_id,
            m.match_date
        FROM bowling_match_stats bw
        JOIN matches m
            ON bw.match_id = m.match_id
    ) x
    GROUP BY x.player_id
)

SELECT
    p.player_id,
    p.name,
    p.team,
    p.role,
    lp.last_match_date,

    CASE
        WHEN lp.last_match_date >= CURRENT_DATE - INTERVAL '6 months'
            THEN 100.00

        WHEN lp.last_match_date >= CURRENT_DATE - INTERVAL '12 months'
            THEN 85.00

        WHEN lp.last_match_date IS NOT NULL
            THEN 65.00

        ELSE 50.00
    END AS activity_score,

    CASE
        WHEN lp.last_match_date >= CURRENT_DATE - INTERVAL '6 months'
            THEN 'Recent'

        WHEN lp.last_match_date >= CURRENT_DATE - INTERVAL '12 months'
            THEN 'Returning'

        WHEN lp.last_match_date IS NOT NULL
            THEN 'Long Gap'

        ELSE 'No Recent T20I Data'
    END AS activity_status

FROM players p

LEFT JOIN last_played lp
    ON p.player_id = lp.player_id

WHERE p.is_active = TRUE;




UPDATE players
SET role = CASE player_id
    WHEN 40   THEN 'Batter'
    WHEN 569  THEN 'Top order Batter'
    WHEN 1266 THEN 'Wicketkeeper Batter'
    WHEN 1265 THEN 'Wicketkeeper Batter'

    WHEN 1306 THEN 'Bowler'
    WHEN 1302 THEN 'Bowler'
    WHEN 1303 THEN 'Batter'
    WHEN 1305 THEN 'Bowler'
    WHEN 1304 THEN 'Batting Allrounder'
    WHEN 1301 THEN 'Bowling Allrounder'

    WHEN 1370 THEN 'Bowler'
    WHEN 1371 THEN 'Bowler'

    WHEN 1423 THEN 'Batting Allrounder'
    WHEN 1435 THEN 'Batter'
    WHEN 1432 THEN 'Batting Allrounder'
    WHEN 1422 THEN 'Bowler'
    WHEN 1430 THEN 'Wicketkeeper Batter'

    WHEN 1472 THEN 'Batter'
    WHEN 1467 THEN 'Batter'
    WHEN 1473 THEN 'Bowler'
    WHEN 1470 THEN 'Allrounder'
    WHEN 1471 THEN 'Wicketkeeper'

    WHEN 1541 THEN 'Bowler'

    WHEN 916  THEN 'Bowler'

    WHEN 1010 THEN 'Batting Allrounder'
    WHEN 1002 THEN 'Wicketkeeper Batter'
    WHEN 1003 THEN 'Batting Allrounder'

    WHEN 1635 THEN 'Batter'

    WHEN 1681 THEN 'Bowler'
    WHEN 1683 THEN 'Bowling Allrounder'
    WHEN 1686 THEN 'Allrounder'
    WHEN 1682 THEN 'Wicketkeeper'
    WHEN 1685 THEN 'Batter'
    WHEN 1684 THEN 'Batting Allrounder'

    WHEN 1138 THEN 'Bowling Allrounder'

    WHEN 1221 THEN 'Bowler'
    WHEN 1219 THEN 'Bowler'
    WHEN 1222 THEN 'Bowling Allrounder'
    WHEN 1223 THEN 'Bowling Allrounder'
    WHEN 1226 THEN 'Batting Allrounder'
    WHEN 1224 THEN 'Bowling Allrounder'
    WHEN 1225 THEN 'Bowling Allrounder'
    WHEN 1220 THEN 'Allrounder'

    ELSE role
END

WHERE player_id IN (
    40,569,1266,1265,
    1306,1302,1303,1305,1304,1301,
    1370,1371,
    1423,1435,1432,1422,1430,
    1472,1467,1473,1470,1471,
    1541,916,
    1010,1002,1003,
    1635,
    1681,1683,1686,1682,1685,1684,
    1138,
    1221,1219,1222,1223,1226,1224,1225,1220
);



UPDATE players
SET role = CASE player_id
    WHEN 1434 THEN 'Wicketkeeper'
    WHEN 1433 THEN 'Allrounder'
    WHEN 1429 THEN 'Bowler'
    WHEN 1424 THEN 'Bowler'
    WHEN 1428 THEN 'Bowler'
    WHEN 1427 THEN 'Allrounder'
    WHEN 1426 THEN 'Bowler'
    WHEN 1425 THEN 'Allrounder'
    WHEN 1469 THEN 'Allrounder'
    WHEN 1468 THEN 'Allrounder'
    WHEN 1687 THEN 'Batter'
    ELSE role
END
WHERE player_id IN (
    1434,1433,1429,1424,1428,
    1427,1426,1425,1469,1468,1687
);


UPDATE players
SET role = CASE player_id
    WHEN 1436 THEN 'Allrounder'
    WHEN 1431 THEN 'Allrounder'
    WHEN 1636 THEN 'Batter'
    ELSE role
END
WHERE player_id IN (1436, 1431, 1636);




CREATE VIEW player_actual_capability AS

SELECT
    ap.player_id,
    ap.name,
    ap.team,
    ap.role,
    ap.last_match_date,
    ap.activity_status,
    ap.activity_score,

    COALESCE(pps.performance_score, 0) AS performance_score,

    ROUND(
        (
            COALESCE(pps.performance_score, 0) * 0.80
            +
            COALESCE(ap.activity_score, 0) * 0.20
        )::NUMERIC,
        2
    ) AS base_selection_score,

    CASE
        WHEN ap.role IN (
            'Wicketkeeper',
            'Wicketkeeper Batter'
        ) THEN TRUE
        ELSE FALSE
    END AS can_keep,

    CASE
        WHEN ap.role IN (
            'Batter',
            'Opening Batter',
            'Top order Batter',
            'Middle order Batter',
            'Wicketkeeper Batter',
            'Allrounder',
            'Batting Allrounder',
            'Bowling Allrounder'
        ) THEN TRUE
        ELSE FALSE
    END AS can_bat,

    CASE
        WHEN ap.role IN (
            'Bowler',
            'Allrounder',
            'Bowling Allrounder',
            'Batting Allrounder'
        ) THEN TRUE
        ELSE FALSE
    END AS can_bowl,

    CASE
        WHEN ap.role IN (
            'Bowler',
            'Allrounder',
            'Bowling Allrounder',
            'Batting Allrounder'
        ) THEN TRUE
        ELSE FALSE
    END AS genuine_bowling_option,

    CASE
        WHEN ap.role IN (
            'Opening Batter',
            'Top order Batter'
        ) THEN TRUE
        ELSE FALSE
    END AS top_order_option

FROM active_player_pool ap

LEFT JOIN player_performance_score pps
    ON ap.player_id = pps.player_id;

CREATE OR REPLACE VIEW player_selection_score AS
SELECT * FROM player_actual_capability;




CREATE FUNCTION suggest_playing_xi(
    input_team VARCHAR
)
RETURNS TABLE (
    player_id INTEGER,
    player_name VARCHAR,
    role VARCHAR,
    base_selection_score NUMERIC,
    can_keep BOOLEAN,
    can_bat BOOLEAN,
    genuine_bowling_option BOOLEAN,
    top_order_option BOOLEAN,
    selection_reason VARCHAR
)
LANGUAGE SQL
AS $$

WITH pool AS (
    SELECT
        pac.player_id,
        pac.name,
        pac.role,
        pac.base_selection_score,
        pac.can_keep,
        pac.can_bat,
        pac.genuine_bowling_option,
        pac.top_order_option
    FROM player_actual_capability pac
    WHERE pac.team = input_team
),

keeper AS (
    SELECT
        p.*
    FROM pool p
    WHERE p.can_keep = TRUE
    ORDER BY p.base_selection_score DESC
    LIMIT 1
),

top_order AS (
    SELECT
        p.*
    FROM pool p
    WHERE p.top_order_option = TRUE
      AND p.player_id NOT IN (
          SELECT k.player_id
          FROM keeper k
      )
    ORDER BY p.base_selection_score DESC
    LIMIT 2
),

bowlers AS (
    SELECT
        p.*
    FROM pool p
    WHERE p.genuine_bowling_option = TRUE
      AND p.player_id NOT IN (
          SELECT k.player_id
          FROM keeper k

          UNION

          SELECT t.player_id
          FROM top_order t
      )
    ORDER BY p.base_selection_score DESC
    LIMIT 5
),

initial_selection AS (
    SELECT * FROM keeper
    UNION
    SELECT * FROM top_order
    UNION
    SELECT * FROM bowlers
),

remaining AS (
    SELECT
        p.*,
        ROW_NUMBER() OVER (
            ORDER BY p.base_selection_score DESC
        ) AS rn
    FROM pool p
    WHERE p.player_id NOT IN (
        SELECT i.player_id
        FROM initial_selection i
    )
),

final_fill AS (
    SELECT
        r.player_id,
        r.name,
        r.role,
        r.base_selection_score,
        r.can_keep,
        r.can_bat,
        r.genuine_bowling_option,
        r.top_order_option
    FROM remaining r
    WHERE r.rn <= GREATEST(
        0,
        11 - (
            SELECT COUNT(*)
            FROM initial_selection
        )
    )
),

final_xi AS (
    SELECT * FROM initial_selection
    UNION
    SELECT * FROM final_fill
)

SELECT
    fx.player_id,
    fx.name::VARCHAR AS player_name,
    fx.role::VARCHAR,
    fx.base_selection_score::NUMERIC,
    fx.can_keep,
    fx.can_bat,
    fx.genuine_bowling_option,
    fx.top_order_option,

    CASE
        WHEN fx.can_keep = TRUE
            THEN 'Wicketkeeper'
        WHEN fx.top_order_option = TRUE
            THEN 'Top-order option'
        WHEN fx.genuine_bowling_option = TRUE
            THEN 'Bowling option'
        ELSE
            'Best remaining performer'
    END::VARCHAR AS selection_reason

FROM final_xi fx

ORDER BY
    fx.base_selection_score DESC;

$$;




CREATE OR REPLACE FUNCTION player_score_vs_opponent(
    input_team VARCHAR,
    input_opponent VARCHAR
)
RETURNS TABLE (
    player_id INTEGER,
    player_name VARCHAR,
    role VARCHAR,
    base_score NUMERIC,
    vs_runs BIGINT,
    vs_balls BIGINT,
    vs_wickets BIGINT,
    vs_batting_sr NUMERIC,
    opponent_score NUMERIC,
    final_score NUMERIC
)
LANGUAGE SQL
AS $$

WITH team_players AS (
    SELECT
        pac.player_id,
        pac.name,
        pac.role,
        pac.base_selection_score
    FROM player_actual_capability pac
    WHERE pac.team = input_team
),

batting_vs AS (
    SELECT
        h.batter_id AS player_id,

        SUM(h.runs) AS runs,
        SUM(h.balls_faced) AS balls,

        ROUND(
            SUM(h.runs)::NUMERIC * 100
            /
            NULLIF(SUM(h.balls_faced), 0),
            2
        ) AS strike_rate

    FROM batter_bowler_head_to_head h

    WHERE h.batter_team = input_team
      AND h.bowler_team = input_opponent

    GROUP BY h.batter_id
),

bowling_vs AS (
    SELECT
        d.bowler_id AS player_id,

        COUNT(*) FILTER (
            WHERE d.is_wicket = TRUE
              AND d.dismissal_type NOT IN (
                  'run out',
                  'retired hurt',
                  'retired out',
                  'obstructing the field'
              )
        ) AS wickets

    FROM deliveries d

    JOIN players batter
        ON d.batter_id = batter.player_id

    JOIN players bowler
        ON d.bowler_id = bowler.player_id

    WHERE bowler.team = input_team
      AND batter.team = input_opponent

    GROUP BY d.bowler_id
),

raw AS (
    SELECT
        tp.player_id,
        tp.name,
        tp.role,
        tp.base_selection_score,

        COALESCE(bv.runs, 0) AS vs_runs,
        COALESCE(bv.balls, 0) AS vs_balls,
        COALESCE(bw.wickets, 0) AS vs_wickets,
        COALESCE(bv.strike_rate, 0) AS vs_batting_sr,

        (
            COALESCE(bv.runs, 0) * 0.20
            +
            COALESCE(bv.strike_rate, 0) * 0.30
            +
            COALESCE(bw.wickets, 0) * 10
        ) AS raw_opponent_score

    FROM team_players tp

    LEFT JOIN batting_vs bv
        ON tp.player_id = bv.player_id

    LEFT JOIN bowling_vs bw
        ON tp.player_id = bw.player_id
),

normalized AS (
    SELECT
        *,

        CASE
            WHEN MAX(raw_opponent_score) OVER () =
                 MIN(raw_opponent_score) OVER ()
                THEN 50

            ELSE
                (
                    (
                        raw_opponent_score
                        -
                        MIN(raw_opponent_score) OVER ()
                    )
                    /
                    NULLIF(
                        MAX(raw_opponent_score) OVER ()
                        -
                        MIN(raw_opponent_score) OVER (),
                        0
                    )
                ) * 100
        END AS normalized_opponent_score

    FROM raw
)

SELECT
    n.player_id,
    n.name::VARCHAR,
    n.role::VARCHAR,

    ROUND(
        n.base_selection_score::NUMERIC,
        2
    ),

    n.vs_runs::BIGINT,
    n.vs_balls::BIGINT,
    n.vs_wickets::BIGINT,

    ROUND(
        n.vs_batting_sr::NUMERIC,
        2
    ),

    ROUND(
        n.normalized_opponent_score::NUMERIC,
        2
    ),

    ROUND(
        (
            n.base_selection_score * 0.75
            +
            n.normalized_opponent_score * 0.25
        )::NUMERIC,
        2
    )

FROM normalized n

ORDER BY
    (
        n.base_selection_score * 0.75
        +
        n.normalized_opponent_score * 0.25
    ) DESC;

$$;



CREATE OR REPLACE FUNCTION player_score_vs_opponent_venue(
    input_team VARCHAR,
    input_opponent VARCHAR,
    input_venue TEXT
)
RETURNS TABLE (
    player_id INTEGER,
    player_name VARCHAR,
    role VARCHAR,
    opponent_score NUMERIC,
    venue_runs BIGINT,
    venue_balls BIGINT,
    venue_wickets BIGINT,
    venue_score NUMERIC,
    final_score NUMERIC
)
LANGUAGE SQL
AS $$

WITH opponent_scores AS (
    SELECT *
    FROM player_score_vs_opponent(
        input_team,
        input_opponent
    )
),

venue_batting AS (
    SELECT
        d.batter_id AS player_id,
        SUM(d.batter_runs) AS runs,

        COUNT(*) FILTER (
            WHERE d.wides = 0
        ) AS balls

    FROM deliveries d

    JOIN matches m
        ON d.match_id = m.match_id

    WHERE d.batting_team = input_team
      AND m.venue = input_venue

    GROUP BY d.batter_id
),

venue_bowling AS (
    SELECT
        d.bowler_id AS player_id,

        COUNT(*) FILTER (
            WHERE d.is_wicket = TRUE
              AND d.dismissal_type NOT IN (
                  'run out',
                  'retired hurt',
                  'retired out',
                  'obstructing the field'
              )
        ) AS wickets

    FROM deliveries d

    JOIN matches m
        ON d.match_id = m.match_id

    JOIN players p
        ON d.bowler_id = p.player_id

    WHERE p.team = input_team
      AND m.venue = input_venue

    GROUP BY d.bowler_id
),

raw AS (
    SELECT
        os.player_id,
        os.player_name,
        os.role,
        os.final_score AS opponent_score,

        COALESCE(vb.runs, 0) AS venue_runs,
        COALESCE(vb.balls, 0) AS venue_balls,
        COALESCE(vw.wickets, 0) AS venue_wickets,

        (
            COALESCE(vb.runs, 0) * 0.20
            +
            CASE
                WHEN COALESCE(vb.balls, 0) > 0
                THEN
                    (
                        COALESCE(vb.runs, 0)::NUMERIC
                        * 100
                        / vb.balls
                    ) * 0.20
                ELSE 0
            END
            +
            COALESCE(vw.wickets, 0) * 10
        ) AS raw_venue_score

    FROM opponent_scores os

    LEFT JOIN venue_batting vb
        ON os.player_id = vb.player_id

    LEFT JOIN venue_bowling vw
        ON os.player_id = vw.player_id
),

normalized AS (
    SELECT
        *,

        CASE
            WHEN MAX(raw_venue_score) OVER () =
                 MIN(raw_venue_score) OVER ()
                THEN 50

            ELSE
                (
                    (
                        raw_venue_score
                        -
                        MIN(raw_venue_score) OVER ()
                    )
                    /
                    NULLIF(
                        MAX(raw_venue_score) OVER ()
                        -
                        MIN(raw_venue_score) OVER (),
                        0
                    )
                ) * 100
        END AS normalized_venue_score

    FROM raw
)

SELECT
    n.player_id,
    n.player_name::VARCHAR,
    n.role::VARCHAR,

    ROUND(
        n.opponent_score::NUMERIC,
        2
    ),

    n.venue_runs::BIGINT,
    n.venue_balls::BIGINT,
    n.venue_wickets::BIGINT,

    ROUND(
        n.normalized_venue_score::NUMERIC,
        2
    ),

    ROUND(
        (
            n.opponent_score * 0.85
            +
            n.normalized_venue_score * 0.15
        )::NUMERIC,
        2
    )

FROM normalized n

ORDER BY
    (
        n.opponent_score * 0.85
        +
        n.normalized_venue_score * 0.15
    ) DESC;

$$;




CREATE OR REPLACE FUNCTION player_phase_score(
    input_team VARCHAR
)
RETURNS TABLE (
    player_id INTEGER,
    player_name VARCHAR,
    role VARCHAR,
    powerplay_score NUMERIC,
    middle_score NUMERIC,
    death_score NUMERIC,
    overall_phase_score NUMERIC
)
LANGUAGE SQL
AS $$

WITH batting AS (
    SELECT
        b.player_id,

        MAX(
            CASE
                WHEN b.phase = 'Powerplay'
                THEN (
                    b.runs * 0.5
                    + COALESCE(b.strike_rate, 0) * 0.5
                )
            END
        ) AS powerplay_batting,

        MAX(
            CASE
                WHEN b.phase = 'Middle'
                THEN (
                    b.runs * 0.5
                    + COALESCE(b.strike_rate, 0) * 0.5
                )
            END
        ) AS middle_batting,

        MAX(
            CASE
                WHEN b.phase = 'Death'
                THEN (
                    b.runs * 0.5
                    + COALESCE(b.strike_rate, 0) * 0.5
                )
            END
        ) AS death_batting

    FROM batter_phase_stats b

    WHERE b.team = input_team

    GROUP BY b.player_id
),

bowling AS (
    SELECT
        b.player_id,

        MAX(
            CASE
                WHEN b.phase = 'Powerplay'
                THEN (
                    b.wickets * 15
                    + b.dot_balls
                    + GREATEST(
                        0,
                        10 - COALESCE(b.economy, 10)
                    ) * 5
                )
            END
        ) AS powerplay_bowling,

        MAX(
            CASE
                WHEN b.phase = 'Middle'
                THEN (
                    b.wickets * 15
                    + b.dot_balls
                    + GREATEST(
                        0,
                        10 - COALESCE(b.economy, 10)
                    ) * 5
                )
            END
        ) AS middle_bowling,

        MAX(
            CASE
                WHEN b.phase = 'Death'
                THEN (
                    b.wickets * 15
                    + b.dot_balls
                    + GREATEST(
                        0,
                        10 - COALESCE(b.economy, 10)
                    ) * 5
                )
            END
        ) AS death_bowling

    FROM bowler_phase_stats b

    WHERE b.team = input_team

    GROUP BY b.player_id
),

combined AS (
    SELECT
        p.player_id,
        p.name,
        p.role,

        COALESCE(bt.powerplay_batting, 0)
        + COALESCE(bw.powerplay_bowling, 0)
            AS powerplay_raw,

        COALESCE(bt.middle_batting, 0)
        + COALESCE(bw.middle_bowling, 0)
            AS middle_raw,

        COALESCE(bt.death_batting, 0)
        + COALESCE(bw.death_bowling, 0)
            AS death_raw

    FROM players p

    LEFT JOIN batting bt
        ON p.player_id = bt.player_id

    LEFT JOIN bowling bw
        ON p.player_id = bw.player_id

    WHERE p.team = input_team
      AND p.is_active = TRUE
),

normalized AS (
    SELECT
        *,

        CASE
            WHEN MAX(powerplay_raw) OVER () =
                 MIN(powerplay_raw) OVER ()
                THEN 50
            ELSE
                (
                    (
                        powerplay_raw
                        - MIN(powerplay_raw) OVER ()
                    )
                    /
                    NULLIF(
                        MAX(powerplay_raw) OVER ()
                        - MIN(powerplay_raw) OVER (),
                        0
                    )
                ) * 100
        END AS powerplay_norm,

        CASE
            WHEN MAX(middle_raw) OVER () =
                 MIN(middle_raw) OVER ()
                THEN 50
            ELSE
                (
                    (
                        middle_raw
                        - MIN(middle_raw) OVER ()
                    )
                    /
                    NULLIF(
                        MAX(middle_raw) OVER ()
                        - MIN(middle_raw) OVER (),
                        0
                    )
                ) * 100
        END AS middle_norm,

        CASE
            WHEN MAX(death_raw) OVER () =
                 MIN(death_raw) OVER ()
                THEN 50
            ELSE
                (
                    (
                        death_raw
                        - MIN(death_raw) OVER ()
                    )
                    /
                    NULLIF(
                        MAX(death_raw) OVER ()
                        - MIN(death_raw) OVER (),
                        0
                    )
                ) * 100
        END AS death_norm

    FROM combined
)

SELECT
    n.player_id,
    n.name::VARCHAR,
    n.role::VARCHAR,

    ROUND(n.powerplay_norm::NUMERIC, 2),
    ROUND(n.middle_norm::NUMERIC, 2),
    ROUND(n.death_norm::NUMERIC, 2),

    ROUND(
        (
            n.powerplay_norm * 0.30
            +
            n.middle_norm * 0.35
            +
            n.death_norm * 0.35
        )::NUMERIC,
        2
    )

FROM normalized n

ORDER BY
    (
        n.powerplay_norm * 0.30
        +
        n.middle_norm * 0.35
        +
        n.death_norm * 0.35
    ) DESC;

$$;




CREATE OR REPLACE FUNCTION suggest_match_playing_xi(
    input_team VARCHAR,
    input_opponent VARCHAR,
    input_venue TEXT
)
RETURNS TABLE (
    player_id INTEGER,
    player_name VARCHAR,
    role VARCHAR,
    match_score NUMERIC,
    can_keep BOOLEAN,
    can_bat BOOLEAN,
    can_bowl BOOLEAN,
    top_order BOOLEAN,
    selection_reason VARCHAR
)
LANGUAGE SQL
AS $$

WITH match_scores AS (
    SELECT
        v.player_id,
        v.player_name,
        v.role,

        ROUND(
            (
                v.final_score * 0.85
                +
                COALESCE(ph.overall_phase_score, 50) * 0.15
            )::NUMERIC,
            2
        ) AS match_score

    FROM player_score_vs_opponent_venue(
        input_team,
        input_opponent,
        input_venue
    ) v

    LEFT JOIN player_phase_score(input_team) ph
        ON v.player_id = ph.player_id
),

pool AS (
    SELECT
        ms.player_id,
        ms.player_name,
        ms.role,
        ms.match_score,

        pac.can_keep,
        pac.can_bat,
        pac.genuine_bowling_option AS can_bowl,
        pac.top_order_option AS top_order

    FROM match_scores ms

    JOIN player_actual_capability pac
        ON ms.player_id = pac.player_id

    WHERE pac.team = input_team
),

keeper AS (
    SELECT p.*
    FROM pool p
    WHERE p.can_keep = TRUE
    ORDER BY p.match_score DESC
    LIMIT 1
),

top_players AS (
    SELECT p.*
    FROM pool p
    WHERE p.top_order = TRUE
      AND p.player_id NOT IN (
          SELECT k.player_id
          FROM keeper k
      )
    ORDER BY p.match_score DESC
    LIMIT 2
),

bowling_players AS (
    SELECT p.*
    FROM pool p
    WHERE p.can_bowl = TRUE
      AND p.player_id NOT IN (
          SELECT k.player_id FROM keeper k

          UNION

          SELECT t.player_id FROM top_players t
      )
    ORDER BY p.match_score DESC
    LIMIT 5
),

initial_xi AS (
    SELECT * FROM keeper

    UNION

    SELECT * FROM top_players

    UNION

    SELECT * FROM bowling_players
),

remaining AS (
    SELECT
        p.*,

        ROW_NUMBER() OVER (
            ORDER BY p.match_score DESC
        ) AS rn

    FROM pool p

    WHERE p.player_id NOT IN (
        SELECT i.player_id
        FROM initial_xi i
    )
),

fill_players AS (
    SELECT
        r.player_id,
        r.player_name,
        r.role,
        r.match_score,
        r.can_keep,
        r.can_bat,
        r.can_bowl,
        r.top_order

    FROM remaining r

    WHERE r.rn <= GREATEST(
        0,
        11 - (
            SELECT COUNT(*)
            FROM initial_xi
        )
    )
),

final_xi AS (
    SELECT * FROM initial_xi

    UNION

    SELECT * FROM fill_players
)

SELECT
    f.player_id,
    f.player_name::VARCHAR,
    f.role::VARCHAR,
    f.match_score::NUMERIC,
    f.can_keep,
    f.can_bat,
    f.can_bowl,
    f.top_order,

    CASE
        WHEN f.can_keep
            THEN 'Wicketkeeper'

        WHEN f.top_order
            THEN 'Top-order option'

        WHEN f.can_bowl
            THEN 'Bowling option'

        ELSE
            'Best match performer'
    END::VARCHAR AS selection_reason

FROM final_xi f

ORDER BY f.match_score DESC;

$$;




CREATE VIEW historical_team_form AS

WITH team_matches AS (

    SELECT
        m.match_id,
        m.match_date,
        m.team1 AS team,
        m.team2 AS opponent,
        m.winner
    FROM matches m
    WHERE m.winner IS NOT NULL

    UNION ALL

    SELECT
        m.match_id,
        m.match_date,
        m.team2 AS team,
        m.team1 AS opponent,
        m.winner
    FROM matches m
    WHERE m.winner IS NOT NULL
),

historical_form AS (

    SELECT
        current_match.match_id,
        current_match.team,

        COUNT(previous_match.match_id) AS previous_matches,

        COUNT(*) FILTER (
            WHERE previous_match.winner = current_match.team
        ) AS previous_wins

    FROM team_matches current_match

    LEFT JOIN LATERAL (

        SELECT
            previous_match.match_id,
            previous_match.winner

        FROM team_matches previous_match

        WHERE previous_match.team = current_match.team

          AND (
                previous_match.match_date < current_match.match_date

                OR (
                    previous_match.match_date = current_match.match_date
                    AND previous_match.match_id < current_match.match_id
                )
          )

        ORDER BY
            previous_match.match_date DESC,
            previous_match.match_id DESC

        LIMIT 5

    ) previous_match
        ON TRUE

    GROUP BY
        current_match.match_id,
        current_match.team
)

SELECT
    match_id,
    team,

    previous_matches AS matches_used,

    previous_wins AS wins_last_5,

    ROUND(
        previous_wins::NUMERIC * 100
        /
        NULLIF(previous_matches, 0),
        2
    ) AS win_percentage_last_5

FROM historical_form;




CREATE VIEW historical_team_scoring_form AS

WITH match_team_runs AS (

    SELECT
        m.match_id,
        m.match_date,
        d.batting_team AS team,
        SUM(d.total_runs) AS team_runs

    FROM matches m

    JOIN deliveries d
        ON m.match_id = d.match_id

    GROUP BY
        m.match_id,
        m.match_date,
        d.batting_team
),

historical AS (

    SELECT
        current_match.match_id,
        current_match.team,

        COUNT(previous_match.match_id) AS matches_used,

        ROUND(
            AVG(previous_match.team_runs)::NUMERIC,
            2
        ) AS avg_runs_last_5

    FROM match_team_runs current_match

    LEFT JOIN LATERAL (

        SELECT
            previous_match.match_id,
            previous_match.team_runs

        FROM match_team_runs previous_match

        WHERE previous_match.team = current_match.team

          AND (
                previous_match.match_date < current_match.match_date

                OR (
                    previous_match.match_date = current_match.match_date
                    AND previous_match.match_id < current_match.match_id
                )
          )

        ORDER BY
            previous_match.match_date DESC,
            previous_match.match_id DESC

        LIMIT 5

    ) previous_match
        ON TRUE

    GROUP BY
        current_match.match_id,
        current_match.team
)

SELECT
    match_id,
    team,
    matches_used,
    avg_runs_last_5

FROM historical;



CREATE VIEW historical_team_bowling_form AS

WITH match_bowling AS (

    SELECT
        m.match_id,
        m.match_date,

        CASE
            WHEN d.batting_team = m.team1 THEN m.team2
            ELSE m.team1
        END AS team,

        COUNT(*) FILTER (
            WHERE d.is_wicket = TRUE
              AND d.dismissal_type NOT IN (
                  'run out',
                  'retired hurt',
                  'retired out',
                  'obstructing the field'
              )
        ) AS wickets,

        SUM(
            d.total_runs
            - COALESCE(d.byes, 0)
            - COALESCE(d.leg_byes, 0)
        ) AS runs_conceded,

        COUNT(*) FILTER (
            WHERE COALESCE(d.wides, 0) = 0
              AND COALESCE(d.no_balls, 0) = 0
        ) AS legal_balls

    FROM matches m

    JOIN deliveries d
        ON m.match_id = d.match_id

    GROUP BY
        m.match_id,
        m.match_date,
        CASE
            WHEN d.batting_team = m.team1 THEN m.team2
            ELSE m.team1
        END
),

historical AS (

    SELECT
        cm.match_id,
        cm.team,

        COUNT(pm.match_id) AS matches_used,

        COALESCE(
            SUM(pm.wickets),
            0
        ) AS total_wickets_last_5,

        ROUND(
            AVG(pm.wickets)::NUMERIC,
            2
        ) AS avg_wickets_last_5,

        COALESCE(
            SUM(pm.runs_conceded),
            0
        ) AS total_runs_conceded_last_5,

        COALESCE(
            SUM(pm.legal_balls),
            0
        ) AS total_legal_balls_last_5,

        ROUND(
            SUM(pm.runs_conceded)::NUMERIC * 6
            /
            NULLIF(SUM(pm.legal_balls), 0),
            2
        ) AS bowling_economy_last_5

    FROM match_bowling cm

    LEFT JOIN LATERAL (

        SELECT
            mb.match_id,
            mb.wickets,
            mb.runs_conceded,
            mb.legal_balls

        FROM match_bowling mb

        WHERE mb.team = cm.team

          AND (
              mb.match_date < cm.match_date

              OR (
                  mb.match_date = cm.match_date
                  AND mb.match_id < cm.match_id
              )
          )

        ORDER BY
            mb.match_date DESC,
            mb.match_id DESC

        LIMIT 5

    ) pm ON TRUE

    GROUP BY
        cm.match_id,
        cm.team
)

SELECT
    match_id,
    team,
    matches_used,
    total_wickets_last_5,
    avg_wickets_last_5,
    total_runs_conceded_last_5,
    total_legal_balls_last_5,
    bowling_economy_last_5

FROM historical;




CREATE VIEW historical_h2h_form AS

WITH completed_matches AS (
    SELECT
        m.match_id,
        m.match_date,
        m.team1,
        m.team2,
        m.winner
    FROM matches m
    WHERE m.winner IS NOT NULL
),

h2h AS (
    SELECT
        cm.match_id,

        COUNT(pm.match_id) AS previous_h2h_matches,

        COUNT(pm.match_id) FILTER (
            WHERE pm.winner = cm.team1
        ) AS team1_previous_wins,

        COUNT(pm.match_id) FILTER (
            WHERE pm.winner = cm.team2
        ) AS team2_previous_wins

    FROM completed_matches cm

    LEFT JOIN completed_matches pm
        ON (
            (pm.team1 = cm.team1 AND pm.team2 = cm.team2)
            OR
            (pm.team1 = cm.team2 AND pm.team2 = cm.team1)
        )

        AND (
            pm.match_date < cm.match_date

            OR (
                pm.match_date = cm.match_date
                AND pm.match_id < cm.match_id
            )
        )

    GROUP BY cm.match_id
)

SELECT
    match_id,
    previous_h2h_matches,
    team1_previous_wins,
    team2_previous_wins,

    ROUND(
        team1_previous_wins::NUMERIC * 100
        /
        NULLIF(previous_h2h_matches, 0),
        2
    ) AS team1_h2h_win_percentage,

    ROUND(
        team2_previous_wins::NUMERIC * 100
        /
        NULLIF(previous_h2h_matches, 0),
        2
    ) AS team2_h2h_win_percentage

FROM h2h;





CREATE VIEW historical_venue_form AS

WITH team_matches AS (

    SELECT
        m.match_id,
        m.match_date,
        m.venue,
        m.team1 AS team,
        m.winner
    FROM matches m
    WHERE m.winner IS NOT NULL

    UNION ALL

    SELECT
        m.match_id,
        m.match_date,
        m.venue,
        m.team2 AS team,
        m.winner
    FROM matches m
    WHERE m.winner IS NOT NULL
),

venue_history AS (

    SELECT
        cm.match_id,
        cm.team,

        COUNT(pm.match_id) AS previous_venue_matches,

        COUNT(pm.match_id) FILTER (
            WHERE pm.winner = cm.team
        ) AS previous_venue_wins

    FROM team_matches cm

    LEFT JOIN team_matches pm

        ON pm.team = cm.team
       AND pm.venue = cm.venue

       AND (
            pm.match_date < cm.match_date

            OR (
                pm.match_date = cm.match_date
                AND pm.match_id < cm.match_id
            )
       )

    GROUP BY
        cm.match_id,
        cm.team
)

SELECT
    match_id,
    team,
    previous_venue_matches,
    previous_venue_wins,

    ROUND(
        previous_venue_wins::NUMERIC * 100
        /
        NULLIF(previous_venue_matches, 0),
        2
    ) AS venue_win_percentage

FROM venue_history;




CREATE VIEW ml_training_dataset AS

SELECT
    m.match_id,
    m.match_date,
    m.team1,
    m.team2,
    m.venue,
    m.toss_winner,
    m.toss_decision,
    m.winner,

    -- Target
    CASE
        WHEN m.winner = m.team1 THEN 1
        WHEN m.winner = m.team2 THEN 0
        ELSE NULL
    END AS team1_win,

    -- Team 1 recent win form
    tf1.matches_used AS team1_form_matches,
    tf1.wins_last_5 AS team1_wins_last_5,
    tf1.win_percentage_last_5 AS team1_win_percentage_last_5,

    -- Team 2 recent win form
    tf2.matches_used AS team2_form_matches,
    tf2.wins_last_5 AS team2_wins_last_5,
    tf2.win_percentage_last_5 AS team2_win_percentage_last_5,

    -- Team 1 scoring form
    ts1.matches_used AS team1_scoring_matches,
    ts1.avg_runs_last_5 AS team1_avg_runs_last_5,

    -- Team 2 scoring form
    ts2.matches_used AS team2_scoring_matches,
    ts2.avg_runs_last_5 AS team2_avg_runs_last_5,

    -- Team 1 bowling form
    tb1.matches_used AS team1_bowling_matches,
    tb1.total_wickets_last_5 AS team1_total_wickets_last_5,
    tb1.avg_wickets_last_5 AS team1_avg_wickets_last_5,
    tb1.bowling_economy_last_5 AS team1_bowling_economy_last_5,

    -- Team 2 bowling form
    tb2.matches_used AS team2_bowling_matches,
    tb2.total_wickets_last_5 AS team2_total_wickets_last_5,
    tb2.avg_wickets_last_5 AS team2_avg_wickets_last_5,
    tb2.bowling_economy_last_5 AS team2_bowling_economy_last_5,

    -- Historical H2H
    h.previous_h2h_matches,
    h.team1_previous_wins,
    h.team2_previous_wins,
    h.team1_h2h_win_percentage,
    h.team2_h2h_win_percentage,

    -- Historical venue form
    v1.previous_venue_matches AS team1_previous_venue_matches,
    v1.previous_venue_wins AS team1_previous_venue_wins,
    v1.venue_win_percentage AS team1_venue_win_percentage,

    v2.previous_venue_matches AS team2_previous_venue_matches,
    v2.previous_venue_wins AS team2_previous_venue_wins,
    v2.venue_win_percentage AS team2_venue_win_percentage,

    -- Toss features
    CASE
        WHEN m.toss_winner = m.team1 THEN 1
        ELSE 0
    END AS team1_won_toss,

    CASE
        WHEN m.toss_decision = 'field' THEN 1
        ELSE 0
    END AS toss_decision_field

FROM matches m

LEFT JOIN historical_team_form tf1
    ON m.match_id = tf1.match_id
   AND m.team1 = tf1.team

LEFT JOIN historical_team_form tf2
    ON m.match_id = tf2.match_id
   AND m.team2 = tf2.team

LEFT JOIN historical_team_scoring_form ts1
    ON m.match_id = ts1.match_id
   AND m.team1 = ts1.team

LEFT JOIN historical_team_scoring_form ts2
    ON m.match_id = ts2.match_id
   AND m.team2 = ts2.team

LEFT JOIN historical_team_bowling_form tb1
    ON m.match_id = tb1.match_id
   AND m.team1 = tb1.team

LEFT JOIN historical_team_bowling_form tb2
    ON m.match_id = tb2.match_id
   AND m.team2 = tb2.team

LEFT JOIN historical_h2h_form h
    ON m.match_id = h.match_id

LEFT JOIN historical_venue_form v1
    ON m.match_id = v1.match_id
   AND m.team1 = v1.team

LEFT JOIN historical_venue_form v2
    ON m.match_id = v2.match_id
   AND m.team2 = v2.team

WHERE m.winner IS NOT NULL;



CREATE VIEW historical_player_batting_form AS

WITH player_match_batting AS (

    SELECT
        d.match_id,
        m.match_date,
        d.batter_id AS player_id,

        SUM(d.batter_runs) AS runs,

        COUNT(*) FILTER (
            WHERE COALESCE(d.wides, 0) = 0
        ) AS balls_faced

    FROM deliveries d

    JOIN matches m
        ON d.match_id = m.match_id

    WHERE d.batter_id IS NOT NULL

    GROUP BY
        d.match_id,
        m.match_date,
        d.batter_id
),

historical AS (

    SELECT
        current_player.match_id,
        current_player.player_id,

        COUNT(previous_player.match_id)
            AS previous_innings_used,

        COALESCE(
            SUM(previous_player.runs),
            0
        ) AS runs_previous_5,

        COALESCE(
            SUM(previous_player.balls_faced),
            0
        ) AS balls_previous_5

    FROM player_match_batting current_player

    LEFT JOIN LATERAL (

        SELECT
            previous_match.match_id,
            previous_match.runs,
            previous_match.balls_faced

        FROM player_match_batting previous_match

        WHERE previous_match.player_id =
              current_player.player_id

          AND (
                previous_match.match_date <
                current_player.match_date

                OR (
                    previous_match.match_date =
                    current_player.match_date

                    AND previous_match.match_id <
                        current_player.match_id
                )
          )

        ORDER BY
            previous_match.match_date DESC,
            previous_match.match_id DESC

        LIMIT 5

    ) previous_player
        ON TRUE

    GROUP BY
        current_player.match_id,
        current_player.player_id
)

SELECT
    h.match_id,
    h.player_id,
    p.name,
    p.team,

    h.previous_innings_used,

    h.runs_previous_5,

    h.balls_previous_5,

    ROUND(
        h.runs_previous_5::NUMERIC
        /
        NULLIF(h.previous_innings_used, 0),
        2
    ) AS batting_avg_runs_previous_5,

    ROUND(
        h.runs_previous_5::NUMERIC * 100
        /
        NULLIF(h.balls_previous_5, 0),
        2
    ) AS batting_sr_previous_5

FROM historical h

JOIN players p
    ON h.player_id = p.player_id;



CREATE VIEW historical_player_bowling_form AS

WITH player_match_bowling AS (

    SELECT
        d.match_id,
        m.match_date,
        d.bowler_id AS player_id,

        COUNT(*) FILTER (
            WHERE COALESCE(d.wides, 0) = 0
              AND COALESCE(d.no_balls, 0) = 0
        ) AS legal_balls,

        SUM(
            d.total_runs
            - COALESCE(d.byes, 0)
            - COALESCE(d.leg_byes, 0)
        ) AS runs_conceded,

        COUNT(*) FILTER (
            WHERE d.is_wicket = TRUE
              AND d.dismissal_type NOT IN (
                  'run out',
                  'retired hurt',
                  'retired out',
                  'obstructing the field'
              )
        ) AS wickets

    FROM deliveries d

    JOIN matches m
        ON d.match_id = m.match_id

    WHERE d.bowler_id IS NOT NULL

    GROUP BY
        d.match_id,
        m.match_date,
        d.bowler_id
),

historical AS (

    SELECT
        current_player.match_id,
        current_player.player_id,

        COUNT(previous_player.match_id)
            AS previous_matches_used,

        COALESCE(
            SUM(previous_player.legal_balls),
            0
        ) AS balls_previous_5,

        COALESCE(
            SUM(previous_player.runs_conceded),
            0
        ) AS runs_conceded_previous_5,

        COALESCE(
            SUM(previous_player.wickets),
            0
        ) AS wickets_previous_5

    FROM player_match_bowling current_player

    LEFT JOIN LATERAL (

        SELECT
            previous_match.match_id,
            previous_match.legal_balls,
            previous_match.runs_conceded,
            previous_match.wickets

        FROM player_match_bowling previous_match

        WHERE previous_match.player_id =
              current_player.player_id

          AND (
                previous_match.match_date <
                current_player.match_date

                OR (
                    previous_match.match_date =
                    current_player.match_date
                    AND previous_match.match_id <
                        current_player.match_id
                )
          )

        ORDER BY
            previous_match.match_date DESC,
            previous_match.match_id DESC

        LIMIT 5

    ) previous_player
        ON TRUE

    GROUP BY
        current_player.match_id,
        current_player.player_id
)

SELECT
    h.match_id,
    h.player_id,
    p.name,
    p.team,

    h.previous_matches_used,

    h.balls_previous_5,

    h.runs_conceded_previous_5,

    h.wickets_previous_5,

    ROUND(
        h.wickets_previous_5::NUMERIC
        /
        NULLIF(h.previous_matches_used, 0),
        2
    ) AS avg_wickets_previous_5,

    ROUND(
        h.runs_conceded_previous_5::NUMERIC * 6
        /
        NULLIF(h.balls_previous_5, 0),
        2
    ) AS economy_previous_5

FROM historical h

JOIN players p
    ON h.player_id = p.player_id;


CREATE VIEW historical_team_player_strength AS

WITH match_players AS (

    SELECT DISTINCT
        d.match_id,
        d.batter_id AS player_id,
        d.batting_team AS team
    FROM deliveries d
    WHERE d.batter_id IS NOT NULL

    UNION

    SELECT DISTINCT
        d.match_id,
        d.non_striker_id AS player_id,
        d.batting_team AS team
    FROM deliveries d
    WHERE d.non_striker_id IS NOT NULL

    UNION

    SELECT DISTINCT
        d.match_id,
        d.bowler_id AS player_id,

        CASE
            WHEN d.batting_team = m.team1
                THEN m.team2
            ELSE m.team1
        END AS team

    FROM deliveries d

    JOIN matches m
        ON d.match_id = m.match_id

    WHERE d.bowler_id IS NOT NULL
),

player_history AS (

    SELECT
        mp.match_id,
        mp.team,
        mp.player_id,

        COALESCE(
            hb.previous_innings_used,
            0
        ) AS batting_history,

        COALESCE(
            hb.runs_previous_5,
            0
        ) AS batting_runs,

        COALESCE(
            hb.balls_previous_5,
            0
        ) AS batting_balls,

        COALESCE(
            hw.previous_matches_used,
            0
        ) AS bowling_history,

        COALESCE(
            hw.wickets_previous_5,
            0
        ) AS bowling_wickets,

        COALESCE(
            hw.runs_conceded_previous_5,
            0
        ) AS bowling_runs,

        COALESCE(
            hw.balls_previous_5,
            0
        ) AS bowling_balls

    FROM match_players mp

    LEFT JOIN historical_player_batting_form hb
        ON mp.match_id = hb.match_id
       AND mp.player_id = hb.player_id

    LEFT JOIN historical_player_bowling_form hw
        ON mp.match_id = hw.match_id
       AND mp.player_id = hw.player_id
)

SELECT
    match_id,
    team,

    COUNT(DISTINCT player_id)
        AS players_detected,

    COUNT(*) FILTER (
        WHERE batting_history > 0
    ) AS players_with_batting_history,

    COUNT(*) FILTER (
        WHERE bowling_history > 0
    ) AS players_with_bowling_history,

    SUM(batting_runs)
        AS xi_runs_previous_5,

    SUM(batting_balls)
        AS xi_balls_previous_5,

    ROUND(
        SUM(batting_runs)::NUMERIC * 100
        /
        NULLIF(
            SUM(batting_balls),
            0
        ),
        2
    ) AS xi_batting_strike_rate,

    ROUND(
        SUM(batting_runs)::NUMERIC
        /
        NULLIF(
            SUM(batting_history),
            0
        ),
        2
    ) AS xi_runs_per_innings,

    SUM(bowling_wickets)
        AS xi_wickets_previous_5,

    ROUND(
        SUM(bowling_wickets)::NUMERIC
        /
        NULLIF(
            SUM(bowling_history),
            0
        ),
        2
    ) AS xi_wickets_per_bowling_match,

    ROUND(
        SUM(bowling_runs)::NUMERIC * 6
        /
        NULLIF(
            SUM(bowling_balls),
            0
        ),
        2
    ) AS xi_bowling_economy

FROM player_history

GROUP BY
    match_id,
    team;


CREATE VIEW ml_training_dataset_v2 AS

SELECT
    ml.*,

    -- Team 1 player strength
    s1.players_detected
        AS team1_players_detected,

    s1.players_with_batting_history
        AS team1_players_batting_history,

    s1.players_with_bowling_history
        AS team1_players_bowling_history,

    s1.xi_runs_previous_5
        AS team1_xi_runs_previous_5,

    s1.xi_batting_strike_rate
        AS team1_xi_batting_strike_rate,

    s1.xi_runs_per_innings
        AS team1_xi_runs_per_innings,

    s1.xi_wickets_previous_5
        AS team1_xi_wickets_previous_5,

    s1.xi_wickets_per_bowling_match
        AS team1_xi_wickets_per_bowling_match,

    s1.xi_bowling_economy
        AS team1_xi_bowling_economy,

    -- Team 2 player strength
    s2.players_detected
        AS team2_players_detected,

    s2.players_with_batting_history
        AS team2_players_batting_history,

    s2.players_with_bowling_history
        AS team2_players_bowling_history,

    s2.xi_runs_previous_5
        AS team2_xi_runs_previous_5,

    s2.xi_batting_strike_rate
        AS team2_xi_batting_strike_rate,

    s2.xi_runs_per_innings
        AS team2_xi_runs_per_innings,

    s2.xi_wickets_previous_5
        AS team2_xi_wickets_previous_5,

    s2.xi_wickets_per_bowling_match
        AS team2_xi_wickets_per_bowling_match,

    s2.xi_bowling_economy
        AS team2_xi_bowling_economy

FROM ml_training_dataset ml

LEFT JOIN historical_team_player_strength s1
    ON ml.match_id = s1.match_id
   AND ml.team1 = s1.team

LEFT JOIN historical_team_player_strength s2
    ON ml.match_id = s2.match_id
   AND ml.team2 = s2.team;




   CREATE OR REPLACE FUNCTION get_latest_batting_form(
    input_player_id INTEGER
)
RETURNS TABLE (
    player_id INTEGER,
    player_name VARCHAR,
    innings_used BIGINT,
    runs_last_5 NUMERIC,
    balls_last_5 NUMERIC,
    runs_per_innings NUMERIC,
    strike_rate NUMERIC
)
LANGUAGE SQL
AS $$

WITH match_batting AS (

    SELECT
        d.match_id,
        m.match_date,

        SUM(d.batter_runs) AS runs,

        COUNT(*) FILTER (
            WHERE COALESCE(d.wides, 0) = 0
        ) AS balls

    FROM deliveries d

    JOIN matches m
        ON d.match_id = m.match_id

    WHERE d.batter_id = input_player_id

    GROUP BY
        d.match_id,
        m.match_date
),

last_5 AS (

    SELECT
        mb.match_id,
        mb.match_date,
        mb.runs,
        mb.balls

    FROM match_batting mb

    ORDER BY
        mb.match_date DESC,
        mb.match_id DESC

    LIMIT 5
),

summary AS (

    SELECT
        COUNT(*) AS innings_used,

        COALESCE(
            SUM(runs),
            0
        ) AS total_runs,

        COALESCE(
            SUM(balls),
            0
        ) AS total_balls

    FROM last_5
)

SELECT
    p.player_id,

    p.name::VARCHAR,

    s.innings_used,

    s.total_runs::NUMERIC,

    s.total_balls::NUMERIC,

    ROUND(
        s.total_runs::NUMERIC
        /
        NULLIF(s.innings_used, 0),
        2
    ) AS runs_per_innings,

    ROUND(
        s.total_runs::NUMERIC * 100
        /
        NULLIF(s.total_balls, 0),
        2
    ) AS strike_rate

FROM players p

CROSS JOIN summary s

WHERE p.player_id = input_player_id;

$$;




CREATE OR REPLACE FUNCTION get_latest_bowling_form(
    input_player_id INTEGER
)
RETURNS TABLE (
    player_id INTEGER,
    player_name VARCHAR,
    matches_used BIGINT,
    wickets_last_5 NUMERIC,
    balls_last_5 NUMERIC,
    runs_conceded_last_5 NUMERIC,
    wickets_per_match NUMERIC,
    economy NUMERIC
)
LANGUAGE SQL
AS $$

WITH match_bowling AS (

    SELECT
        d.match_id,
        m.match_date,

        COUNT(*) FILTER (
            WHERE COALESCE(d.wides, 0) = 0
              AND COALESCE(d.no_balls, 0) = 0
        ) AS legal_balls,

        SUM(
            d.total_runs
            - COALESCE(d.byes, 0)
            - COALESCE(d.leg_byes, 0)
        ) AS runs_conceded,

        COUNT(*) FILTER (
            WHERE d.is_wicket = TRUE
              AND d.dismissal_type NOT IN (
                  'run out',
                  'retired hurt',
                  'retired out',
                  'obstructing the field'
              )
        ) AS wickets

    FROM deliveries d

    JOIN matches m
        ON d.match_id = m.match_id

    WHERE d.bowler_id = input_player_id

    GROUP BY
        d.match_id,
        m.match_date
),

last_5 AS (

    SELECT
        mb.match_id,
        mb.match_date,
        mb.legal_balls,
        mb.runs_conceded,
        mb.wickets

    FROM match_bowling mb

    ORDER BY
        mb.match_date DESC,
        mb.match_id DESC

    LIMIT 5
),

summary AS (

    SELECT
        COUNT(*) AS matches_used,

        COALESCE(
            SUM(wickets),
            0
        ) AS total_wickets,

        COALESCE(
            SUM(legal_balls),
            0
        ) AS total_balls,

        COALESCE(
            SUM(runs_conceded),
            0
        ) AS total_runs_conceded

    FROM last_5
)

SELECT
    p.player_id,
    p.name::VARCHAR,

    s.matches_used,

    s.total_wickets::NUMERIC,

    s.total_balls::NUMERIC,

    s.total_runs_conceded::NUMERIC,

    ROUND(
        s.total_wickets::NUMERIC
        /
        NULLIF(s.matches_used, 0),
        2
    ) AS wickets_per_match,

    ROUND(
        s.total_runs_conceded::NUMERIC * 6
        /
        NULLIF(s.total_balls, 0),
        2
    ) AS economy

FROM players p

CROSS JOIN summary s

WHERE p.player_id = input_player_id;

$$;





CREATE OR REPLACE FUNCTION get_xi_strength(
    input_player_ids INTEGER[]
)
RETURNS TABLE (
    players_count BIGINT,
    xi_runs_previous_5 NUMERIC,
    xi_batting_strike_rate NUMERIC,
    xi_runs_per_innings NUMERIC,
    xi_wickets_previous_5 NUMERIC,
    xi_wickets_per_bowling_match NUMERIC,
    xi_bowling_economy NUMERIC
)
LANGUAGE SQL
AS $$

WITH selected_players AS (
    SELECT
        UNNEST(input_player_ids) AS player_id
),

batting AS (
    SELECT
        sp.player_id,

        bf.innings_used,
        bf.runs_last_5,
        bf.balls_last_5

    FROM selected_players sp

    LEFT JOIN LATERAL (
        SELECT *
        FROM get_latest_batting_form(sp.player_id)
    ) bf
        ON TRUE
),

bowling AS (
    SELECT
        sp.player_id,

        bw.matches_used,
        bw.wickets_last_5,
        bw.balls_last_5,
        bw.runs_conceded_last_5

    FROM selected_players sp

    LEFT JOIN LATERAL (
        SELECT *
        FROM get_latest_bowling_form(sp.player_id)
    ) bw
        ON TRUE
),

combined AS (
    SELECT
        sp.player_id,

        COALESCE(b.innings_used, 0)
            AS batting_innings,

        COALESCE(b.runs_last_5, 0)
            AS batting_runs,

        COALESCE(b.balls_last_5, 0)
            AS batting_balls,

        COALESCE(bo.matches_used, 0)
            AS bowling_matches,

        COALESCE(bo.wickets_last_5, 0)
            AS bowling_wickets,

        COALESCE(bo.balls_last_5, 0)
            AS bowling_balls,

        COALESCE(bo.runs_conceded_last_5, 0)
            AS bowling_runs

    FROM selected_players sp

    LEFT JOIN batting b
        ON sp.player_id = b.player_id

    LEFT JOIN bowling bo
        ON sp.player_id = bo.player_id
)

SELECT
    COUNT(*) AS players_count,

    SUM(batting_runs)::NUMERIC
        AS xi_runs_previous_5,

    ROUND(
        SUM(batting_runs)::NUMERIC * 100
        /
        NULLIF(
            SUM(batting_balls),
            0
        ),
        2
    ) AS xi_batting_strike_rate,

    ROUND(
        SUM(batting_runs)::NUMERIC
        /
        NULLIF(
            SUM(batting_innings),
            0
        ),
        2
    ) AS xi_runs_per_innings,

    SUM(bowling_wickets)::NUMERIC
        AS xi_wickets_previous_5,

    ROUND(
        SUM(bowling_wickets)::NUMERIC
        /
        NULLIF(
            SUM(bowling_matches),
            0
        ),
        2
    ) AS xi_wickets_per_bowling_match,

    ROUND(
        SUM(bowling_runs)::NUMERIC * 6
        /
        NULLIF(
            SUM(bowling_balls),
            0
        ),
        2
    ) AS xi_bowling_economy

FROM combined;

$$;




DROP FUNCTION IF EXISTS get_future_match_features(
    VARCHAR,
    VARCHAR,
    VARCHAR,
    VARCHAR,
    VARCHAR,
    INTEGER[],
    INTEGER[]
);

CREATE FUNCTION get_future_match_features(
    input_team1 VARCHAR,
    input_team2 VARCHAR,
    input_venue VARCHAR,
    input_toss_winner VARCHAR,
    input_toss_decision VARCHAR,
    input_team1_xi INTEGER[],
    input_team2_xi INTEGER[]
)
RETURNS TABLE (

    team1_win_percentage_last_5 NUMERIC,
    team2_win_percentage_last_5 NUMERIC,

    team1_avg_runs_last_5 NUMERIC,
    team2_avg_runs_last_5 NUMERIC,

    team1_avg_wickets_last_5 NUMERIC,
    team2_avg_wickets_last_5 NUMERIC,

    team1_bowling_economy_last_5 NUMERIC,
    team2_bowling_economy_last_5 NUMERIC,

    previous_h2h_matches BIGINT,

    team1_h2h_win_percentage NUMERIC,
    team2_h2h_win_percentage NUMERIC,

    team1_previous_venue_matches BIGINT,
    team1_venue_win_percentage NUMERIC,

    team2_previous_venue_matches BIGINT,
    team2_venue_win_percentage NUMERIC,

    team1_won_toss INTEGER,
    toss_decision_field INTEGER,

    team1_xi_runs_previous_5 NUMERIC,
    team2_xi_runs_previous_5 NUMERIC,

    team1_xi_batting_strike_rate NUMERIC,
    team2_xi_batting_strike_rate NUMERIC,

    team1_xi_runs_per_innings NUMERIC,
    team2_xi_runs_per_innings NUMERIC,

    team1_xi_wickets_previous_5 NUMERIC,
    team2_xi_wickets_previous_5 NUMERIC,

    team1_xi_wickets_per_bowling_match NUMERIC,
    team2_xi_wickets_per_bowling_match NUMERIC,

    team1_xi_bowling_economy NUMERIC,
    team2_xi_bowling_economy NUMERIC
)
LANGUAGE SQL
AS $$

WITH

-- ==================================================
-- TEAM 1 LAST 5 WIN %
-- ==================================================

team1_last5 AS (

    SELECT
        COUNT(*) AS matches_used,

        COUNT(*) FILTER (
            WHERE x.winner = input_team1
        ) AS wins

    FROM (

        SELECT
            m.match_id,
            m.match_date,
            m.winner

        FROM matches m

        WHERE m.winner IS NOT NULL

          AND (
              m.team1 = input_team1
              OR
              m.team2 = input_team1
          )

        ORDER BY
            m.match_date DESC,
            m.match_id DESC

        LIMIT 5

    ) x
),

-- ==================================================
-- TEAM 2 LAST 5 WIN %
-- ==================================================

team2_last5 AS (

    SELECT
        COUNT(*) AS matches_used,

        COUNT(*) FILTER (
            WHERE x.winner = input_team2
        ) AS wins

    FROM (

        SELECT
            m.match_id,
            m.match_date,
            m.winner

        FROM matches m

        WHERE m.winner IS NOT NULL

          AND (
              m.team1 = input_team2
              OR
              m.team2 = input_team2
          )

        ORDER BY
            m.match_date DESC,
            m.match_id DESC

        LIMIT 5

    ) x
),

-- ==================================================
-- CURRENT TEAM FORM
-- ==================================================

team1_strength AS (

    SELECT *
    FROM team_recent_strength
    WHERE team = input_team1
),

team2_strength AS (

    SELECT *
    FROM team_recent_strength
    WHERE team = input_team2
),

-- ==================================================
-- H2H
-- ==================================================

h2h AS (

    SELECT *
    FROM team_vs_team_stats

    WHERE team_a = LEAST(
        input_team1,
        input_team2
    )

    AND team_b = GREATEST(
        input_team1,
        input_team2
    )

    LIMIT 1
),

-- ==================================================
-- VENUE
-- ==================================================

venue1 AS (

    SELECT *
    FROM team_venue_stats

    WHERE team = input_team1
      AND venue = input_venue

    LIMIT 1
),

venue2 AS (

    SELECT *
    FROM team_venue_stats

    WHERE team = input_team2
      AND venue = input_venue

    LIMIT 1
),

-- ==================================================
-- XI STRENGTH
-- ==================================================

xi1 AS (

    SELECT *
    FROM get_xi_strength(
        input_team1_xi
    )
),

xi2 AS (

    SELECT *
    FROM get_xi_strength(
        input_team2_xi
    )
)

SELECT

    -- ==================================================
    -- RECENT WIN %
    -- ==================================================

    ROUND(
        (
            t1f.wins::NUMERIC
            * 100
            /
            NULLIF(
                t1f.matches_used,
                0
            )
        ),
        2
    ),

    ROUND(
        (
            t2f.wins::NUMERIC
            * 100
            /
            NULLIF(
                t2f.matches_used,
                0
            )
        ),
        2
    ),

    -- ==================================================
    -- RECENT SCORING
    -- ==================================================

    t1.avg_score_last_5_matches,

    t2.avg_score_last_5_matches,

    -- ==================================================
    -- RECENT WICKETS
    -- ==================================================

    ROUND(
        t1.wickets_last_5_matches::NUMERIC
        /
        NULLIF(
            t1.matches_used,
            0
        ),
        2
    ),

    ROUND(
        t2.wickets_last_5_matches::NUMERIC
        /
        NULLIF(
            t2.matches_used,
            0
        ),
        2
    ),

    -- ==================================================
    -- RECENT ECONOMY
    -- ==================================================

    t1.economy_last_5_matches,

    t2.economy_last_5_matches,

    -- ==================================================
    -- H2H
    -- ==================================================

    COALESCE(
        h.matches_played,
        0
    )::BIGINT,

    CASE

        WHEN h.team_a = input_team1
            THEN h.team_a_win_percentage

        WHEN h.team_b = input_team1
            THEN h.team_b_win_percentage

        ELSE NULL

    END,

    CASE

        WHEN h.team_a = input_team2
            THEN h.team_a_win_percentage

        WHEN h.team_b = input_team2
            THEN h.team_b_win_percentage

        ELSE NULL

    END,

    -- ==================================================
    -- VENUE
    -- ==================================================

    COALESCE(
        v1.matches_played,
        0
    )::BIGINT,

    v1.win_percentage,

    COALESCE(
        v2.matches_played,
        0
    )::BIGINT,

    v2.win_percentage,

    -- ==================================================
    -- TOSS
    -- ==================================================

    CASE
        WHEN input_toss_winner = input_team1
            THEN 1
        ELSE 0
    END,

    CASE
        WHEN LOWER(input_toss_decision) = 'field'
            THEN 1
        ELSE 0
    END,

    -- ==================================================
    -- TEAM 1 XI
    -- ==================================================

    x1.xi_runs_previous_5,

    x2.xi_runs_previous_5,

    x1.xi_batting_strike_rate,

    x2.xi_batting_strike_rate,

    x1.xi_runs_per_innings,

    x2.xi_runs_per_innings,

    x1.xi_wickets_previous_5,

    x2.xi_wickets_previous_5,

    x1.xi_wickets_per_bowling_match,

    x2.xi_wickets_per_bowling_match,

    x1.xi_bowling_economy,

    x2.xi_bowling_economy

FROM team1_last5 t1f

CROSS JOIN team2_last5 t2f

CROSS JOIN team1_strength t1

CROSS JOIN team2_strength t2

CROSS JOIN xi1 x1

CROSS JOIN xi2 x2

LEFT JOIN h2h h
    ON TRUE

LEFT JOIN venue1 v1
    ON TRUE

LEFT JOIN venue2 v2
    ON TRUE;

$$;


-- IMAGE INSERTION

UPDATE players
SET image_url = CASE name
    WHEN 'Wafiullah Tarakhil' THEN 'https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcRz-Y6YarlQb4xgqldTz-3OtXrM42Qz0T1rEZpnGPKB2vRowyaEZC0QIZEWMZZbKokUkWXN7g9bca2jA85rGEQ9nxEPLnj0ZHyNZA921XraaqaP_C8wJA&s=10&ec=121966422'

    WHEN 'Ainsley Ndlovu' THEN 'https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcSY-U7IO8BcD9qBlGkJCtbZwHpjE9bdXJrnvVbxjnkAYl2U2grDAcVOlzkRvOUJlbUU9WjiOL0hPBqAKgMwOYpn9YT88BC69fl_5ABXIRfZ_YUkkO89&s=10&ec=121966422'

    WHEN 'Handre Klazinge' THEN 'https://d13ir53smqqeyp.cloudfront.net/fc-player-images/94253.png'

    WHEN 'Rijan Dhakal' THEN 'https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcQQAbH8c3VknMrP2Aa4hyNJDwMwp8Tn5nnNbwc687--NwG32_7NijTn2kNPeRgD3UnZ9IYud38GMHJSZMgJKifcZlo78OxE7SQTHuAfY8yoM20CH4menw&s=10&ec=121966422'

    WHEN 'Aakash Chand' THEN 'https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcQIKIoFFBql0iGo1qX8AcSZFid5V5WAuCWDDSYI8iq9NLK7hPixHTcVTCHdHC5mXPDNzbNwmMRhWcWZ2fBcFcwiomm9ApXlb6ECzdZdcKrqupwSyBcn&s=10&ec=121966422'

    WHEN 'Mohammad Aadil Alam' THEN 'https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcQrXMscMWiKl8rnUs0mSwgzDI4-dy4dePFYde2v-GPU5PYrqAf1sQVumTfqkxFmXMjY_JQQWVt7Uc-WJXqtEAWKTrrrMVEfTxasVVDEFavcOjUCTpUXEw&s=10&ec=121966422'

    WHEN 'Bibek Yadav' THEN 'https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcSyBM0UXZEOmqMtCXC7nt8tn5IHbADbB9_ln4LiXOAoWNWu04yddjnkAYZEOmq9rMOTDHNVlibfF09QBe_UUIzqysA6vgDkn5OiWT0V9Ht1kJe_GvvGr7_1wYag&s=10&ec=121966422'

    WHEN 'Shoaib Khan' THEN 'https://img1.hscicdn.com/image/upload/f_auto,t_ds_square_w_320,q_50/lsci/db/PICTURES/CMS/390700/390785.2.png'

    WHEN 'Shahab Alam' THEN 'https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcTt463hq-6CBA1qR_y4oExtJJpDeUP1oNzmO2p4J3xXbh1bhMWO4E56cZzkWXdR04-38qr1DBrogFk4Rfk1JayZs7FkqV94eby5eDV83TdJsHsxjMZiDA&s=10&ec=121966422'
END
WHERE name IN (
    'Wafiullah Tarakhil',
    'Ainsley Ndlovu',
    'Handre Klazinge',
    'Rijan Dhakal',
    'Aakash Chand',
    'Mohammad Aadil Alam',
    'Bibek Yadav',
    'Shoaib Khan',
    'Shahab Alam'
);





UPDATE players
SET image_url = CASE LOWER(name)

    WHEN 'abdul gaffar saqlain' THEN 'https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcSydqcRBBEqunbi062LwwvxdpVlJA0Sz9DbBvVunn-XMs_8e7sVobuwcvlDQQmv02a3bQOJnuDpfNghvuoNNE-mSHBfm74oLRq9VvgZwb8UCla3c8E4&s=10&ec=121966422'

    WHEN 'nazmus sadat' THEN 'https://d13ir53smqqeyp.cloudfront.net/fc-player-images/215.png'

    WHEN 'reinhardt strydom' THEN 'https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcTlAmhMlGDcUhUz8zu-ZfXX9UQcjoMUIFvtM-kd7Opxv61asijvDgAKZaQIhplo6rxhWNyDxnYavVpQmU1pFHYAHQTNavaex610IQU_pAyl3xm75cWvPg&s=10&ec=121966422'

    WHEN 'imran mir' THEN 'https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcRxJyiYbBxarXt4_ZZDZ_4ydMxbRkGll2ilHMyNuQ-2gakAQjDMJKvMu1kM5mLiD5Pdj13X-pJsczlWhiTFAI7F0n3sZOOZZ_KgqkKP2UuOI6DQZwyWMg&s=10&ec=121966422'

    WHEN 'kundai matigimu' THEN 'https://images.news18.com/ibnlive/uploads/2025/07/Kundai-Matigimu-2025-07-ccc67867f302b6786da36fe655184a91-16x9.png?impolicy=website&width=400&height=225'

    WHEN 'faraz akram' THEN 'https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcRwYVrJGJkLQF457agLzUCls-_z7JpFrUk7IIY1kUutUZ5v4Oq3WUN48icXlNdzMLTbjolPbUROwYkcOm-1MxzEG6fMwJ_lMB8LALRf_bdE0QZ2VdDP&s=10&ec=121966422'

    WHEN 'waldo smith' THEN 'https://d13ir53smqqeyp.cloudfront.net/fc-player-images/179907.png'

    WHEN 'max heingo' THEN 'https://encrypted-tbn0.gstatic.com/licensed-image?q=tbn:ANd9GcT9d1lpzgqG0067SMWGZhMYKRreCHy05P2qX676oRRqSjoeJ39-TjWb67bNuR3DyPji4ur4bnJ_PD2ZNHOr6o-nda6u0fVPzI2o2h1vQOiGiJrMsDup92xEfNoET-KVez43LNXa48LCz2KZWcejzsI&s=19&ec=121966422'

    WHEN 'alexander busing-volschenk' THEN 'https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcSG5TJO2CC9ikkkf2xCDs2U_-YCXmSDh-ZQPA0_ghQNk-FldOICVNY6DOpPtUh2q3fRi1ZkY5Q6XAP6bthwSD3zAt4wOVgd_cFMO1_sXOThN_ViyxEcKw&s=10&ec=121966422'

    WHEN 'jan-izak de villiers' THEN 'https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcQCCb6aRgYIfkpUdV9BqlIme1FtQcaUkAS49euZV7dS7jQ0FEjKbmHLkDn4d88DNtB2kMesR9dP8cgzSlJ5hdSa4To37quDyGHnGNwfVtJVriUbiOA&s=10&ec=121966422'

    WHEN 'shaun fouche' THEN 'https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcQdsWPUwNQXhMqN9TpKnndl6B6o07UcTG4OCVs-RK7JsaoF0NLfmFqqD5ozH8228SP-9yejiZGEBomMW53G2MN91ZfHFrZ3DQZMYNELuHFdW_ODKoXt&s=10&ec=121966422'

    WHEN 'junior taanyanda' THEN 'https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcR9WVLm94pd8osIFnZtpx3fA7mZ2Zk5QKRnrnCXL8c97UkytchnqXpdOqDDjH-FPpi9Mcm2cCLmdTWtwbm-AjjOB88ox7Ydpj5ZwujTGDqnNH25ozlSLQ&s=10&ec=121966422'

    WHEN 'sebastiaan braat' THEN 'https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcQwFUEy2iGlM30kelRNpAW9ez1-4ADaAGxhs_-f0HqdQKJ8DMh9z2iqSSh4lHs1h3bW_9hCe31w3ORJvmVq40jassyHPbl6s7o6vM68aQ3bHrePVNOJ&s=10&ec=121966422'

    WHEN 'omid shafi rahman' THEN 'https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcTho61rIpdZBU48Zh2KVGATznSbhM0t1sdVhiSfjlhq7IEGoHI62iLTYeRR-2mUEE2mgZgYUftq11osM_NYlFmxOGClHAFU9_m5rMi_c9OVRZroX9cfiw&s=10&ec=121966422'

    WHEN 'sufyan yousaf' THEN 'https://d13ir53smqqeyp.cloudfront.net/fc-player-images/111821.png'

    WHEN 'zikria islam' THEN 'https://d13ir53smqqeyp.cloudfront.net/fc-player-images/111843.png'

    WHEN 'mujibur ali' THEN 'https://d13ir53smqqeyp.cloudfront.net/fc-player-images/3644.png'

    WHEN 'hassnain shah' THEN 'https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcTUB20mMId5QA5fESL_qi6Lla5E1uXllxv0rKgUIetwNlKeJpCpwC-_y_qdB_LUbwuYVyFEOrjvYbHfPdtJUmCZbP2X_LnoytF2iU3iLDgS2CWKDRod&s=10&ec=121966422'

    WHEN 'muzahir raza' THEN 'https://d13ir53smqqeyp.cloudfront.net/fc-player-images/19540.png'

    WHEN 'rashad al balushi' THEN 'https://media.cricclubs.com/documentsRep/profilePics/771cf9f0-cc59-4a7b-96cc-720e6a75e650.jpeg'

    WHEN 'zubair al balushi' THEN 'https://media.cricclubs.com/documentsRep/profilePics/982f5862-7f3f-4c6c-8c16-1989d5a6e0e2.jpeg'

    WHEN 'wasim al balushi' THEN 'https://media.cricclubs.com/documentsRep/profilePics/680af0ed-60fa-4d1c-b03d-828f21eb868c.jpeg'

    WHEN 'mohammed al balushi' THEN 'https://media.gettyimages.com/id/678259382/photo/soccer-international-friendly-republic-of-ireland-v-oman-craven-cottage.jpg?s=2048x2048&w=gi&k=20&c=efmBegx7RIChueSmAQTFbfjXCns0R7iO0voXQS67pAo='

    WHEN 'ryan ani' THEN 'https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcRGshFH61r3RYuxueAFes5XvUDFuS5OS1d_bNBb8tnmNjKTpWWCSqS10sO01YJrzPMYUIl7sgs4V1iB1qaPgLw4cMssFX4oHA0ofIihEQ3cWDC0Spek&s=10&ec=121966422'

    WHEN 'aue oru' THEN 'https://live-production.wcms.abc-cdn.net.au/da9a8abc1fd37b174d7a6f75a24c928f?impolicy=wcms_crop_resize&cropH=1640&cropW=1640&xPos=0&yPos=306&width=862&height=862'

    WHEN 'charlie cassell' THEN 'https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcTizy55R3ZmsVupWv_o8-tHpvRQiRa3-J89xNyPXV6brQYchuD6RYzEP4TC419aFQwtRn8L3CvZdZjAuU8o5NOEdvzphKTkJ23xkxBTqQqMWGe1dISAew&s=10&ec=121966422'

    WHEN 'ajay kumar' THEN 'https://www.ilt20.ae/static-assets/images/players/132824.png?v=31.62'

    WHEN 'adeeb usmani' THEN 'https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcRSEfiqBeEKdE3fUuxBaUFKCouKery9GoGlFRGn-6KS6amojgQYpOVuzH0WtTXGCfZKIjUkg6_ICE2w-9Ehr-anvGUv8TuwB-8-8jc5c35jhEymaS_1&s=10&ec=121966422'

    WHEN 'yayin kiran rai' THEN 'https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcQWHN7yPq_Ca-PCcOpMCLyJB-DdWcPAkqJ1lLTn0RRtbYIVSxiQ5fjIP3N0UcXDaKGMo-ZnbHuLUU5tZnTT4ebcvgweT2VdChKoeQIGdBB_QaaWzHkW0g&s=10&ec=121966422'

    WHEN 'saghir khan' THEN 'https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcQWHN7yPq_Ca-PCcOpMCLyJB-DdWcPAkqJ1lLTn0RRtbYIVSxiQ5fjIP3N0UcXDaKGMo-ZnbHuLUU5tZnTT4ebcvgweT2VdChKoeQIGdBB_QaaWzHkW0g&s=10&ec=121966422'

    WHEN 'rahul chopra' THEN 'https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcQU1Tk8IxuoMmo8x-Bzz6FyE7gwRqxcf6QFYXg9LE64up9gRbHj7Kscv-ZwTZ7j4JX12L3g0WQbRwZ3BLX2wfpj-wyXPR-LIV4UWXFtNSvNz09HfPxcSg&s=10&ec=121966422'

    WHEN 'samal udawaththa' THEN 'https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcQAO6y1y6gIoXK3gJqjbsvDgTyYukgipKrTF39bFgWFWO17C7dmt3MSQjarloLTLEY5h6CJc9aBy2OjbObDzEPyBzhrYdgV4Fm6wz-v4Ww7lhKwasuIhA&s=10&ec=121966422'

    WHEN 'tanish suri' THEN 'https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcQAO6y1y6gIoXK3gJqjbsvDgTyYukgipKrTF39bFgWFWO17C7dmt3MSQjarloLTLEY5h6CJc9aBy2OjbObDzEPyBzhrYdgV4Fm6wz-v4Ww7lhKwasuIhA&s=10&ec=121966422'

    WHEN 'khalid shah' THEN 'https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcTAPrrt7DvQHv8donZnlJn4iUd9sMgxoZ9IWMaJc0Mas31neYcRJgAzJRLQ4SBJh-X8yOmkDQmc39Ush7ENVjRgybv9AwRr6IE-ZNCq5eS6UW67H8EhCQ&s=10&ec=121966422'

    WHEN 'nilansh keswani' THEN 'https://d13ir53smqqeyp.cloudfront.net/fc-player-images/54572.png'

    WHEN 'mohammed faraazuddin' THEN 'https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcQDTgMS4CctzZKF_oPbfPEj7qJqYDt3s0J8eLrJv-m7rorLp4GqsP0dZLzkISurPcQVrDpGwS6eIqZaW0bfM8FXXYjJRCfrbO5ka6Pwm-ToNpOJrssq&s=10&ec=121966422'

    WHEN 'waheed ahmed' THEN 'https://d13ir53smqqeyp.cloudfront.net/fc-player-images/88746.png'

    WHEN 'laxman sreekumar' THEN 'https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcT4aGvc3BKba4NsU4r_H4lfkvxbj9IdFihd4ioQPE-B7AODh_ayfCKvtOR5MYSI14qoOYEUHLrm_uvF9LfpLYGHPTU0mN4BF9X5XTdydcN7yjnryHMa&s=10&ec=121966422'

    WHEN 'muhammad kaleem' THEN 'https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcQwpsJ38hpgPZ1jI7wTtvC7JmoHdX1_lso682ihhBcNIHElnfABhopfBCxEK8AeZDAKycrTQ46iByC2eNvPaX9qXgAW3ddbCCxenN5wMTMCP1AmgwDyAg&s=10&ec=121966422'

    WHEN 'farhan ahmed' THEN 'https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcQwpsJ38hpgPZ1jI7wTtvC7JmoHdX1_lso682ihhBcNIHElnfABhopfBCxEK8AeZDAKycrTQ46iByC2eNvPaX9qXgAW3ddbCCxenN5wMTMCP1AmgwDyAg&s=10&ec=121966422'

    WHEN 'fahad tariq' THEN 'https://media.cricclubs.com/documentsRep/profilePics/d111a918-df6e-4e86-af77-e443f4d21b47.png'

    WHEN 'zaheer maqsood' THEN 'https://scontent.fcok6-2.fna.fbcdn.net/v/t39.30808-6/474220161_1561037195298272_8617411074449237265_n.jpg?stp=dst-jpg_tt6&cstp=mx1080x1293&ctp=s1080x1293&_nc_cat=102&_nc_map=urlgen_bucketless&ccb=1-7&_nc_sid=833d8c&_nc_ohc=qRdt1eur7osQ7kNvwFNaWK-&_nc_oc=AdqA6AG69m1V4dWZthbsVEOCvVK-o1RIftkcqfMu3XHSImsX4kBvpKvva8oLiPi8D5vgAtKDCL2SVGlXBf61DNyr&oh=00_AQIijNfbdNjluA0YJvwZS1OXJbloHhcFa0pBESnn440RMg&oe=6AAF05B9'

    WHEN 'akhilesh reddy' THEN 'https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcTpCw2hASEZiYbUs3f0R9owLwDxZHxfVYBrHXIT7ZVUr7vrYJCbmbk1_scch7d79xCObHYcKMrJhC9bCybKvt6t2EQQcEcFh52ML_lubHO2efmsTbMi&s=10&ec=121966422'

    WHEN 'utkarsh srivastava' THEN 'https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcRGZnQ7fpBRCx_d9n4crgr3xSRMktIbZK_nfxUemp6TgRqe36t6A-cZTqzfGhUjhaQzKdZdPR0iznpC2ilpWFhVpNXtblXDhvwqf6dh7_YqvR0fRDA3IQ&s=10&ec=121966422'

    WHEN 'ayan desai' THEN 'https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcQL5c88wAJpn0dVs3pYtlq_nVMX0CnqhZ-sDxQIxQDEoaqSBjV_Hk0dy8_wJ_hZMPJ4StS_epbEYK8w7MfpOVWe-6orPocjrB3FqtBTVNmUzhzvQrqL&s=10&ec=121966422'

    WHEN 'juanoy drysdale' THEN 'https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcRqqNKy_cyCGAxQWeBB3hnbF_8KWC5nHRsmJ7r9XJzaEuwsDpTbax2tmvv5vZxgBk-Tw9AQQS1ANQ70ngs_8qyUwFiMMK3KSFDnrUpPXI6RMx8tIDQZmg&s=10&ec=121966422'

    WHEN 'daniel jakiel' THEN 'https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcRR2HbvxGbmN1R0c6KIHdsN1sixq7TT23Wth0_6QIETdts1UhG1Pglix4EUVBDBqF8PkAaoOV5LpuqO2-PXdFqcMpYmI5YpQxrc7vt-h_0X8ONOObM&s=10&ec=121966422'

    WHEN 'liam basson' THEN 'https://admin.lastmanstands.com/SpawtzApp/Images/User/333223_UserProfileImage_1772701861870.jpeg'

    WHEN 'gerhard janse van rensburg' THEN 'https://d13ir53smqqeyp.cloudfront.net/fc-player-images/33779.png'

    WHEN 'santosh yadav' THEN 'https://cricketnepal.org.np/wp-content/uploads/2024/03/Santosh-Yadav.png'

    WHEN 'hemant dhami' THEN 'https://npcdn.ratopati.com/media/news/image-(1)_Q2LDROzVTN.png'

    WHEN 'kiran thagunna' THEN 'https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcTZbJODl3M9pXfmQK1ZqwRs_5OBLixrRiv-Oke2eOHgX4FbB6x-lHP5kI7DCZCVax5TiV-EWUrPDtXIUE7IBVl6M8d36D9J9Yo1KeBCN2h6PXLWKgwrdQ&s=10&ec=121966422'

    WHEN 'rupesh singh' THEN 'https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcR9cbDnN1Uxj56Zdyi7SCK5yfJFLka_eQlejaQBaKrJrjqoPFHiD-8vOo6yH-VSuL_uOnpu8bpHFsdD7JTtooUimGi-Gl-VEEDvnkaMoEt4s6kUPgfWpQ&s=10&ec=121966422'

    WHEN 'munthir al balushi' THEN 'https://media.cricclubs.com/documentsRep/profilePics/9d75b5db-293b-47f6-a8b5-f9ba30830455.jpeg'

    WHEN 'faris al balushi' THEN 'https://d13ir53smqqeyp.cloudfront.net/fc-player-images/87473.png'

    WHEN 'muzaffar shiralkar' THEN 'https://media.cricclubs.com/documentsRep/profilePics/45f52a0f-3c5b-43f6-be89-02fde210edac.png'

    WHEN 'issa al balushi' THEN 'https://scontent.fcok6-1.fna.fbcdn.net/v/t39.30808-6/482023273_1064815535688260_1230284197374127357_n.jpg?stp=dst-jpg_tt6&cstp=mx1080x1080&ctp=s1080x1080&_nc_cat=108&_nc_map=urlgen_bucketless&ccb=1-7&_nc_sid=127cfc&_nc_ohc=e-oi0nUgdiUQ7kNvwE_6L33&_nc_oc=AdobASOUSrbGqHr7BzvN5XMkXQQUBKrVGI99ydYAfJD143D6w8E-NLDK34FcH-zKl_8WBf3-w1vwW5pDYlIAm0G5&_nc_zt=23&_nc_ht=scontent.fcok6-1.fna&_nc_gid=WhmJiohi2JFJcVICSa51Xw&_nc_ss=7b289&oh=00_AQLtatmiszGy052p2ASCp7t96Y2PZQL4cnQTWxleURNCzw&oe=6AAF29F9'

    WHEN 'gaba frank' THEN 'https://d13ir53smqqeyp.cloudfront.net/fc-player-images/138736.png'

    WHEN 'patrick nou' THEN 'https://d13ir53smqqeyp.cloudfront.net/fc-player-images/88671.png'

    WHEN 'peter karoho' THEN 'https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcQrdIxZ71E71UpB07sTKRuOA55WqH8EF4lHHgN1TCdVnMAybRYli6r1o5RVjmpM36yqIL4EPfltqwnW2_T-p-lyg26fEW5QM77eJeJepkIisAzKWGtgqA&s=10&ec=121966422'

    WHEN 'boio ray' THEN 'https://media.gettyimages.com/id/1364479840/photo/papua-new-guinea-portraits-icc-u19-mens-cricket-world-cup-west-indies-2022.jpg?s=2048x2048&w=gi&k=20&c=mh5A69Qvtq_XaDwW8277PODwA1KABXbwxexj8ABgYzY='

    WHEN 'michael charlie' THEN 'https://d13ir53smqqeyp.cloudfront.net/fc-player-images/150444.png'

    WHEN 'james dickinson' THEN 'https://gh-media.co.uk/wp-content/uploads/2018/05/James-Dickinson-768x1024.jpg.webp'

    WHEN 'jonathan figy' THEN 'https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcTlsWP5WRugK-NQuA7ARt5smY120x6SqFgBjJ7btFRNOQmzJ1gQYfmwt4W9gxiTbjzP8m3-xVpCm8h_NsEA-zxS1A5t-gnvSTNW2gN228eEaEfPDpODjA&s=10&ec=121966422'

    WHEN 'sameer othman' THEN 'https://images.firstpost.com/uploads/2026/09/BeFunky-collage-2026-09-04T180329.205-2026-09-cba9ce20df5a61775970a828e38dc75e.jpg?im=Resize,width=720,aspect=fit,type=normal'

    WHEN 'nawed al balushi' THEN 'https://img1.hscicdn.com/image/upload/f_auto,t_ds_square_w_320,q_50/lsci/db/PICTURES/CMS/386600/386644.5.png'

    WHEN 'abdul jalil' THEN 'https://media.cricclubs.com/documentsRep/profilePics/00c56f2f-bf97-4d99-a446-ad6abdadd435.jpeg'

    WHEN 'rakibul hasan' THEN 'https://img1.hscicdn.com/image/upload/f_auto,t_ds_square_w_320,q_50/lsci/db/PICTURES/CMS/319700/319737.1.png'

    WHEN 'hasnain ul wahab' THEN 'https://d13ir53smqqeyp.cloudfront.net/fc-player-images/111840.png'

    WHEN 'sinethemba qeshile' THEN 'https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcSRTZLMIsBpfpPNtQGa5dKMElI3QYStOLQGk8MHzUo7T7h6V1KFtCbdPHqM64zXGayDeGNjUAdESCUssOwDpnFKoVTxealuqyXFhvs1RadjWVSyntSO&s=10&ec=121966422'

    WHEN 'mubasir khan' THEN 'https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcTFfMRPI-A13iy6w_TrLrwMEnUqz3-ajlzwzuGwxdFroa3wAd64UuycWXgQwJjl95ieRmB_UlGlvPlXUHCT-UkYsxGMCXP-Q0xTpsYlAf_J08YCG9gH&s=10&ec=121966422'

    WHEN 'ihsanullah' THEN 'https://d13ir53smqqeyp.cloudfront.net/fc-player-images/12045.png'

    WHEN 'rafatullah mohmand' THEN 'https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcR6UqlKTYi6CQzJ0skFi7VSOJ40z_-4nJaqWiTUiSVVtlmlVfLvh1S58cgHkgVIHqMSwQpcbHNxRFULDXrn7TjyAPlWeJ3ZAYaOg2VQtAU6v6DxkfnerA&s=10&ec=121966422'

    WHEN 'imran khan' THEN 'https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcQ4eoYrz3mCy1amnZbKhOQYJehq7vVrzy7a9RfO3bAOq3SsOja5gMthmeqRKm0SzM2CrrrU3bEZHq7_GDKD2sSQ3IvqkxzRkjo55_Vwp8rlB_np9-sj&s=10&ec=121966422'

    WHEN 'nqobani mokoena' THEN 'https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcRMEu5KKdM37BUrSzDFeIM__AYYWhM319C-e4O9u1zXAEz33zKHVzxRgt1dm78xX4_kAW-66jdlRycHm0bCbRyGi01ERkCVr0AdTa0j5GG7TyWGcksb&s=10&ec=121966422'

    WHEN 'jordan hermann' THEN 'https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcT6A-quyrbxV7jC75Tcudrs01FFDbsE4K4lBtGuSRbHNjDokSiflVenoOP3UnQ-H8JJI_laUczMJ5b3mQ7N5r5b-NneLyu99jBItfjMWT5EH2UFhxWd&s=10&ec=121966422'

    WHEN 'dian forrester' THEN 'https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcRk8fW9TJUCLJpvanmKlDDTQbDVkH4eabx5M0EN_lKY4QWo4FKRWCYKCOm2ZCGD9qq98aPz3ZZbJVAPAizph7JpRpY451br1SiLAtwb4tXKdfMfILcb&s=10&ec=121966422'

    WHEN 'connor esterhuizen' THEN 'https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcQYc__SOJg2XOaB8uDpakx3hXhPwGJ6hxWoYcObbdqXA4G70shorqSoXoDrl1d1MVEM-pSfUqqVHKaPCv0Gx3kRXt2mSfzGlxfTd-Kau-McoJTFebDvFg&s=10&ec=121966422'

    WHEN 'jacques snyman' THEN 'https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcQyzNmA1URu1P3tx-0JrXJlrl_KKdD4enNQhrqmWGtmd5yldr4spBIQZ_9U-FCNoucoSXWW_lvfzw1P0alrVxjofR5QKJr8BfLcsh4DA5JnIp9uCRTHAA&s=10&ec=121966422'

    WHEN 'shehan madushanka' THEN 'https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcTC_DEurypIhIiLW3nki_xS3Q6z8i_7j1623h-dMzu8YD3mMnwF73VFYa70ZblgeXrBvXBvalVDGOWXR1tQPj2DWmRQ2jkPgynCD54f8f8KyMkUa4pM&s=10&ec=121966422'

    ELSE image_url
END
WHERE image_url ILIKE '%.svg'
AND LOWER(name) IN (
    'abdul gaffar saqlain',
    'nazmus sadat',
    'reinhardt strydom',
    'imran mir',
    'kundai matigimu',
    'faraz akram',
    'waldo smith',
    'max heingo',
    'alexander busing-volschenk',
    'jan-izak de villiers',
    'shaun fouche',
    'junior taanyanda',
    'sebastiaan braat',
    'omid shafi rahman',
    'sufyan yousaf',
    'zikria islam',
    'mujibur ali',
    'hassnain shah',
    'muzahir raza',
    'rashad al balushi',
    'zubair al balushi',
    'wasim al balushi',
    'mohammed al balushi',
    'ryan ani',
    'aue oru',
    'charlie cassell',
    'ajay kumar',
    'adeeb usmani',
    'yayin kiran rai',
    'saghir khan',
    'rahul chopra',
    'samal udawaththa',
    'tanish suri',
    'khalid shah',
    'nilansh keswani',
    'mohammed faraazuddin',
    'waheed ahmed',
    'laxman sreekumar',
    'muhammad kaleem',
    'farhan ahmed',
    'fahad tariq',
    'zaheer maqsood',
    'akhilesh reddy',
    'utkarsh srivastava',
    'ayan desai',
    'juanoy drysdale',
    'daniel jakiel',
    'liam basson',
    'gerhard janse van rensburg',
    'santosh yadav',
    'hemant dhami',
    'kiran thagunna',
    'rupesh singh',
    'munthir al balushi',
    'faris al balushi',
    'muzaffar shiralkar',
    'issa al balushi',
    'gaba frank',
    'patrick nou',
    'peter karoho',
    'boio ray',
    'michael charlie',
    'james dickinson',
    'jonathan figy',
    'sameer othman',
    'nawed al balushi',
    'abdul jalil',
    'rakibul hasan',
    'hasnain ul wahab',
    'sinethemba qeshile',
    'mubasir khan',
    'ihsanullah',
    'rafatullah mohmand',
    'imran khan',
    'nqobani mokoena',
    'jordan hermann',
    'dian forrester',
    'connor esterhuizen',
    'jacques snyman',
    'shehan madushanka'
);


UPDATE players
SET image_url = 'https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcS3HzQ_UJpiII9IQ-3u7ulADlXXanBYPJwLbIfzvgSvcy2meoj-5wYr_qc8LQ5wYdJjByS4poTkbtDzkSgUkcTGPEzaLNoKuV-xC6lOX15JdzQ6CLJENg&s=10&ec=121966422'
WHERE name = 'Aarin Nadkarni';


UPDATE players
SET image_url = CASE name

    WHEN 'Zach Lion-Cachet' THEN
        'https://encrypted-tbn0.gstatic.com/licensed-image?q=tbn:ANd9GcSAxCbk1EnIasK5YG3bqbcN1OIGnqyY4soE9dEqkpp51kOgbpgnLjiKQhBHJy3Qw0gnoFxe5XXD2SsvRlm_ju9keA2kslCRyjIpYmExtxE26xlPCXSq37wlcwaqPB-sv5WeziYSFz7naUPZUhy_Ejs&s=19&ec=121966422'

    WHEN 'Zacheo van Vuuren' THEN
        'https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcQ-fpjPNvZLYWqwhzPHZYKlaGuDentuPNQlh_W_9sfrDp6BBtdLp13BVROfS7JAqo6qRw4b9IonOHvIb4hxOGzucHZUQr1X8OoLaPPprym9kj5ocOO0&s=10&ec=121966422'

    WHEN 'Zaheer Maqsood' THEN
        'https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcQ7YrBhmIyurwk3fPKaL9BniPbXQCm864qTuD5jzXdxc8OHvM6LMMbbDTzKt_xWE7hhFQYIM9fO5ypuQAGP6BvEHolNDzIJxXBoppYFT49sF-jgnAFd&s=10&ec=121966422'

    WHEN 'Wihan Lubbe' THEN
        'https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcQJXPODBPdKot8Mtbjb8jE5xMq81o0rAiyNdbvDX1Rlovl0RiMOiFcI_Zg2osNfNenODK7ZStkjFBEj-GXEBGXqvicnKBvjBx9aNSlGHsPwDSFr2wJXxw&s=10&ec=121966422'

    WHEN 'william mashinge' THEN
        'https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcR3rCd9247zhvl8XANpJ2sCcqfbP44NKUT5-HFwWALKayucaoNm8RfLTaSZnjFxvoXI03HKoTK_1dtaKAJU34vZxPaeuqp_j8RpHgEUgxdaetAVsmtvuA&s=10&ec=121966422'

    WHEN 'trevor gwandu' THEN
        'https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcTjvH0lKbM08X10bDDu13l8jLvhowKTSHZ5Xb2OItw2UYVv8WsytoyaiVpc2flh5NZIXvztt_Bxoi6HixbOzOwNnpj7dYwF_1rRKkHmOVKaSHyH9mMP&s=10&ec=121966422'

    WHEN 'tanaka chivanga' THEN
        'https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcSNzOFqnUT5ALokDiy-g0t0auknRM6UMJsCyrnjRemGb2xcUMAzzTQ93V2jOoTIm1hmBEtDy3TZZJ89phopdxeNOFz61ZQWmtjSRbtE1XE5P0kelRv8&s=10&ec=121966422'

    WHEN 'Takudzwa Chataira' THEN
        'https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcR8Jz_vHyfsePGfnrnW2z0K4aPquLj0q0-INZ-T6qCS397jvAsOi3yCyJI_WgaKm4NhEbuYNECsHovk0f7J24OAMSQDMyJggpMk5n9Ntcjjo8MwcYwc&s=10&ec=121966422'

    WHEN 'Siddharth Bukkapatnam' THEN
        'http://d13ir53smqqeyp.cloudfront.net/fc-player-images/87447.png'

    WHEN 'Shuaib Al Balushi' THEN
        'https://d13ir53smqqeyp.cloudfront.net/fc-player-images/179336.png'

    ELSE image_url
END
WHERE name IN (
    'Zach Lion-Cachet',
    'Zacheo van Vuuren',
    'Zaheer Maqsood',
    'Wihan Lubbe',
    'william mashinge',
    'trevor gwandu',
    'tanaka chivanga',
    'Takudzwa Chataira',
    'Siddharth Bukkapatnam',
    'Shuaib Al Balushi'
);



