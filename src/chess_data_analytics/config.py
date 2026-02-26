"""Configuration constants for chess-data-analytics."""

import os

# Paths
USER_DATA_DIR = os.path.join(os.getcwd(), ".chess_browser_data")
DEFAULT_DB_PATH = os.path.join(os.getcwd(), "chess_analytics.db")

# Timeouts (ms)
INITIAL_LOAD_DELAY = 10000  # Chess.com computation when loading game review (~10s)
PAGE_LOAD_TIMEOUT = 15000

# Viewport
VIEWPORT_WIDTH = 1280
VIEWPORT_HEIGHT = 800

# Chess.com selectors
GAME_REVIEW_URL = "https://www.chess.com/analysis/game/live/{game_id}/review"
PGN_ANALYSIS_URL = "https://www.chess.com/analysis/game/pgn/{game_id}/review"
TALLIES_COLLAPSE_BUTTON = "[data-cy='game-review-tallies-collapse-button']"
COLLAPSE_EXPAND_DELAY = 1000  # ms to wait after expanding tallies
PLAYER_TOP_SELECTOR = "[data-cy='analysis-player-Top']"
PLAYER_BOTTOM_SELECTOR = "[data-cy='analysis-player-Bottom']"
USERNAME_SELECTOR = "[data-test-element='user-tagline-username']"

# Move tally types (Chess.com data-cy values)
TALLY_TYPES = [
    "Brilliant",
    "GreatFind",  # "Great"
    "Book",
    "BestMove",   # "Best"
    "Excellent",
    "Good",
    "Inaccuracy",
    "Mistake",
    "Miss",
    "Blunder",
]
