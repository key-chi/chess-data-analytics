"""SQLite database for chess game analytics."""

import sqlite3
from pathlib import Path


def get_connection(db_path: str) -> sqlite3.Connection:
    """Get a connection to the analytics database, creating schema if needed."""
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    _init_schema(conn)
    return conn


def _init_schema(conn: sqlite3.Connection) -> None:
    """Create tables if they don't exist."""
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS games (
            game_id TEXT PRIMARY KEY,
            white_username TEXT NOT NULL,
            black_username TEXT NOT NULL,
            white_rating INTEGER DEFAULT 0,
            black_rating INTEGER DEFAULT 0,
            brilliant_white INTEGER DEFAULT 0,
            brilliant_black INTEGER DEFAULT 0,
            great_white INTEGER DEFAULT 0,
            great_black INTEGER DEFAULT 0,
            book_white INTEGER DEFAULT 0,
            book_black INTEGER DEFAULT 0,
            best_white INTEGER DEFAULT 0,
            best_black INTEGER DEFAULT 0,
            excellent_white INTEGER DEFAULT 0,
            excellent_black INTEGER DEFAULT 0,
            good_white INTEGER DEFAULT 0,
            good_black INTEGER DEFAULT 0,
            inaccuracy_white INTEGER DEFAULT 0,
            inaccuracy_black INTEGER DEFAULT 0,
            mistake_white INTEGER DEFAULT 0,
            mistake_black INTEGER DEFAULT 0,
            miss_white INTEGER DEFAULT 0,
            miss_black INTEGER DEFAULT 0,
            blunder_white INTEGER DEFAULT 0,
            blunder_black INTEGER DEFAULT 0,
            accuracy_white REAL DEFAULT 0,
            accuracy_black REAL DEFAULT 0,
            result TEXT DEFAULT '',
            created_at TEXT DEFAULT (datetime('now'))
        );

        CREATE INDEX IF NOT EXISTS idx_games_white ON games(white_username);
        CREATE INDEX IF NOT EXISTS idx_games_black ON games(black_username);
    """)
    _migrate_drop_player_ids(conn)
    _migrate_add_accuracy(conn)
    _migrate_add_result(conn)


def _migrate_drop_player_ids(conn: sqlite3.Connection) -> None:
    """Drop white_id and black_id columns from existing databases (SQLite 3.35+)."""
    try:
        info = conn.execute("PRAGMA table_info(games)").fetchall()
        cols = [r[1] for r in info]
        if "white_id" in cols:
            conn.execute("ALTER TABLE games DROP COLUMN white_id")
        if "black_id" in cols:
            conn.execute("ALTER TABLE games DROP COLUMN black_id")
    except sqlite3.OperationalError:
        pass  # Older SQLite or column already dropped


def _migrate_add_accuracy(conn: sqlite3.Connection) -> None:
    """Add accuracy_white and accuracy_black columns if missing."""
    try:
        info = conn.execute("PRAGMA table_info(games)").fetchall()
        cols = [r[1] for r in info]
        if "accuracy_white" not in cols:
            conn.execute("ALTER TABLE games ADD COLUMN accuracy_white REAL DEFAULT 0")
        if "accuracy_black" not in cols:
            conn.execute("ALTER TABLE games ADD COLUMN accuracy_black REAL DEFAULT 0")
    except sqlite3.OperationalError:
        pass


def _migrate_add_result(conn: sqlite3.Connection) -> None:
    """Add result column if missing."""
    try:
        info = conn.execute("PRAGMA table_info(games)").fetchall()
        cols = [r[1] for r in info]
        if "result" not in cols:
            conn.execute("ALTER TABLE games ADD COLUMN result TEXT DEFAULT ''")
    except sqlite3.OperationalError:
        pass


def insert_game(conn: sqlite3.Connection, data: dict) -> None:
    """Insert or replace a game record."""
    columns = [
        "game_id", "white_username", "black_username",
        "white_rating", "black_rating",
        "brilliant_white", "brilliant_black",
        "great_white", "great_black",
        "book_white", "book_black",
        "best_white", "best_black",
        "excellent_white", "excellent_black",
        "good_white", "good_black",
        "inaccuracy_white", "inaccuracy_black",
        "mistake_white", "mistake_black",
        "miss_white", "miss_black",
        "blunder_white", "blunder_black",
        "accuracy_white", "accuracy_black",
        "result",
    ]
    placeholders = ", ".join("?" * len(columns))
    conn.execute(
        f"INSERT OR REPLACE INTO games ({', '.join(columns)}) VALUES ({placeholders})",
        [
            data.get("game_id", ""),
            data.get("white_username", ""),
            data.get("black_username", ""),
            data.get("white_rating", 0),
            data.get("black_rating", 0),
            data.get("Brilliant_white", 0),
            data.get("Brilliant_black", 0),
            data.get("GreatFind_white", 0),
            data.get("GreatFind_black", 0),
            data.get("Book_white", 0),
            data.get("Book_black", 0),
            data.get("BestMove_white", 0),
            data.get("BestMove_black", 0),
            data.get("Excellent_white", 0),
            data.get("Excellent_black", 0),
            data.get("Good_white", 0),
            data.get("Good_black", 0),
            data.get("Inaccuracy_white", 0),
            data.get("Inaccuracy_black", 0),
            data.get("Mistake_white", 0),
            data.get("Mistake_black", 0),
            data.get("Miss_white", 0),
            data.get("Miss_black", 0),
            data.get("Blunder_white", 0),
            data.get("Blunder_black", 0),
            data.get("white_accuracy", 0.0),
            data.get("black_accuracy", 0.0),
            data.get("result", ""),
        ],
    )
