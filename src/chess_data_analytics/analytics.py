"""Analytics queries for chess club data."""

import sqlite3
from pathlib import Path


def get_player_stats(conn: sqlite3.Connection) -> list[dict]:
    """
    Aggregate stats per player (as white + as black).
    Returns list of dicts with player summary.
    """
    # Union white and black players, then aggregate
    conn.row_factory = sqlite3.Row
    rows = conn.execute("""
        WITH player_games AS (
            SELECT white_username AS username, 'white' AS color,
                   white_rating AS rating, accuracy_white AS accuracy,
                   CASE WHEN result = '1-0' THEN 1 ELSE 0 END AS win,
                   CASE WHEN result = '0-1' THEN 1 ELSE 0 END AS loss,
                   CASE WHEN result = '1/2-1/2' THEN 1 ELSE 0 END AS draw,
                   brilliant_white AS brilliant, great_white AS great, book_white AS book,
                   best_white AS best, excellent_white AS excellent, good_white AS good,
                   inaccuracy_white AS inaccuracy, mistake_white AS mistake,
                   miss_white AS miss, blunder_white AS blunder
            FROM games
            WHERE white_username != ''
            UNION ALL
            SELECT black_username, 'black',
                   black_rating AS rating, accuracy_black AS accuracy,
                   CASE WHEN result = '0-1' THEN 1 ELSE 0 END AS win,
                   CASE WHEN result = '1-0' THEN 1 ELSE 0 END AS loss,
                   CASE WHEN result = '1/2-1/2' THEN 1 ELSE 0 END AS draw,
                   brilliant_black, great_black, book_black,
                   best_black, excellent_black, good_black,
                   inaccuracy_black, mistake_black, miss_black, blunder_black
            FROM games
            WHERE black_username != ''
        )
        SELECT
            username,
            COUNT(*) AS games_played,
            SUM(win) AS wins,
            SUM(loss) AS losses,
            SUM(draw) AS draws,
            ROUND(AVG(rating), 1) AS avg_rating,
            ROUND(AVG(accuracy), 1) AS avg_accuracy,
            SUM(brilliant) AS total_brilliant,
            SUM(great) AS total_great,
            SUM(book) AS total_book,
            SUM(best) AS total_best,
            SUM(excellent) AS total_excellent,
            SUM(good) AS total_good,
            SUM(inaccuracy) AS total_inaccuracy,
            SUM(mistake) AS total_mistake,
            SUM(miss) AS total_miss,
            SUM(blunder) AS total_blunder,
            ROUND(1.0 * SUM(brilliant) / NULLIF(COUNT(*), 0), 2) AS avg_brilliant_per_game,
            ROUND(1.0 * SUM(great) / NULLIF(COUNT(*), 0), 2) AS avg_great_per_game,
            ROUND(1.0 * SUM(blunder) / NULLIF(COUNT(*), 0), 2) AS avg_blunder_per_game
        FROM player_games
        GROUP BY username
        ORDER BY total_brilliant DESC, games_played DESC
    """).fetchall()
    return [dict(r) for r in rows]


def get_season_summary(conn: sqlite3.Connection) -> dict:
    """Get overall season summary."""
    total_games = conn.execute("SELECT COUNT(*) FROM games").fetchone()[0] or 0

    players = conn.execute("""
        SELECT white_username AS username FROM games WHERE white_username != ''
        UNION
        SELECT black_username FROM games WHERE black_username != ''
    """).fetchall()
    unique_players = len(set(r[0] for r in players))

    total_brilliant = conn.execute(
        "SELECT COALESCE(SUM(brilliant_white + brilliant_black), 0) FROM games"
    ).fetchone()[0]

    return {
        "total_games": total_games,
        "unique_players": unique_players,
        "total_brilliant_moves": total_brilliant,
    }
