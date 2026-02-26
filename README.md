# Chess Data Analytics

Collect and analyze Chess.com game review data for your chess club's season. Loads game IDs from a CSV, runs each game through Chess.com's review, and builds a database of player stats (Brilliant, Great, Book, Best moves, ratings, etc.) for analytics.

## Setup

```bash
uv sync
uv run playwright install chromium
```

## Usage

### 1. Create a CSV of game IDs

Create `games.csv` with a column named `game_id`:

```csv
game_id
139647066699
139645856373
```

### 2. Collect game data

```bash
uv run chess-data-analytics collect games.csv
```

This will:
- Open each game review in a browser (log in to Chess.com manually the first time - you may need to increase the INITIAL_LOAD_DELAY in config.py to give yourself enough time to log in)
- Wait for the review to compute (with configurable delay)
- Parse players, move tallies, and ratings
- Store results in `chess_analytics.db`

### 3. View analytics

```bash
# Player summaries (totals, averages, Brilliant counts, etc.)
uv run chess-data-analytics players

# Season overview
uv run chess-data-analytics summary
```

### 4. Manual PGN (OTB / league games)

For over-the-board or league games not played on Chess.com, add them manually.

1. Paste your OTB PGN into [Chess.com Analysis Board](https://www.chess.com/analysis)
2. Let the engine run and show accuracy and move feedback
3. Copy the alpha-numeric PGN Code
4. Add the game with full data:

```bash
uv run chess-data-analytics manual-pgn PGN-CODE white-username black-username -r [1-0 | 1/2-1/2 | 0-1]
```

For example:

```bash
uv run chess-data-analytics manual-pgn jFY6SgYtW white_player black_player -r 0-1
```

### Options

| Option | Description |
|--------|-------------|
| `--move-delay` | Delay between operations in seconds (default: 1.5, avoid rate limits) |
| `--headless` | Run browser headless |
| `--db` | Database path (default: chess_analytics.db) |

## Authentication

Uses a persistent browser context. **Log in to Chess.com manually the first time** the script runs. Subsequent runs reuse your session.

## Data Collected

Per game:
- **Players**: White and Black usernames
- **Move tallies**: Brilliant, Great, Book, Best, Excellent, Good, Inaccuracy, Mistake, Miss, Blunder
- **Accuracy**: White and Black accuracy percentages (e.g. 81.5%, 76.6%)
- **Result**: Game outcome (1-0, 0-1, 1/2-1/2) for wins/losses/draws per player
- **Game ratings**: White and Black review ratings
