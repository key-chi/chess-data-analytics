"""CLI entry point for chess-data-analytics."""

import argparse
import csv
import re
import sys
import time
from pathlib import Path

from .browser import extract_game_review
from .database import get_connection, insert_game
from .analytics import get_player_stats, get_season_summary
from .config import DEFAULT_DB_PATH
from .parser import parse_pgn_text, parse_game_review_page


def extract_game_id(value: str) -> str | None:
    """Extract game ID from URL or return as-is if already numeric."""
    match = re.search(r"(?:game/live|analysis/game/live)/(\d+)", value)
    if match:
        return match.group(1)
    if value.isdigit():
        return value
    return None


def load_game_ids_from_csv(path: str) -> list[str]:
    """Load game IDs from CSV. Expects a column named 'game_id' or first column."""
    ids = []
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        if not reader.fieldnames:
            return ids
        # Try game_id column first, else use first column
        col = "game_id" if "game_id" in reader.fieldnames else reader.fieldnames[0]
        for row in reader:
            val = row.get(col, "").strip()
            gid = extract_game_id(val) if val else None
            if gid:
                ids.append(gid)
    return ids


def cmd_collect(args: argparse.Namespace) -> int:
    """Collect game data from CSV and store in database."""
    game_ids = load_game_ids_from_csv(args.csv_file)
    if not game_ids:
        print("No valid game IDs found in CSV.", file=sys.stderr)
        return 1

    print(f"Found {len(game_ids)} game(s) to process.")
    conn = get_connection(args.db)

    for i, game_id in enumerate(game_ids, 1):
        print(f"[{i}/{len(game_ids)}] Processing game {game_id}...")
        data = extract_game_review(game_id, headless=args.headless)
        if data:
            insert_game(conn, data)
            conn.commit()
            print(f"  Saved: {data.get('white_username', '?')} vs {data.get('black_username', '?')}")
        else:
            print(f"  Failed to extract data.", file=sys.stderr)

        # Delay between games to avoid rate limits
        if i < len(game_ids):
            time.sleep(args.move_delay)

    conn.close()
    print("Done.")
    return 0


def cmd_players(args: argparse.Namespace) -> int:
    """Print player summaries."""
    if not Path(args.db).exists():
        print(f"Database not found: {args.db}. Run 'collect' first.", file=sys.stderr)
        return 1

    conn = get_connection(args.db)
    stats = get_player_stats(conn)
    conn.close()

    if not stats:
        print("No player data yet. Run 'collect' first.")
        return 0

    print("\n=== Player Summaries ===\n")
    for s in stats:
        print(f"  {s['username']}")
        acc = s.get("avg_accuracy")
        acc_str = f"{acc}%" if acc is not None and acc > 0 else "—"
        wld = f"W: {s.get('wins', 0)}  L: {s.get('losses', 0)}  D: {s.get('draws', 0)}"
        print(f"    Games: {s['games_played']}  ({wld})  |  Avg Rating: {s['avg_rating']}  |  Avg Accuracy: {acc_str}")
        print(f"    Brilliant: {s['total_brilliant']}  Great: {s['total_great']}  "
              f"Best: {s['total_best']}  Book: {s['total_book']}")
        print(f"    Excellent: {s['total_excellent']}  Good: {s['total_good']}")
        print(f"    Inaccuracies: {s['total_inaccuracy']}  Mistakes: {s['total_mistake']}  "
              f"Miss: {s['total_miss']}  Blunders: {s['total_blunder']}")
        print()

    return 0


def cmd_manual_pgn(args: argparse.Namespace) -> int:
    """Add a manually entered PGN (e.g. OTB league game) to the database."""
    if args.html_file:
        # Parse Chess.com analysis HTML (has accuracy, tallies, ratings)
        html = Path(args.html_file).read_text(encoding="utf-8")
        parsed = parse_game_review_page(html, args.pgn_code)
        # Override usernames (HTML may have "White"/"Black" for custom games)
        parsed["white_username"] = args.white_username
        parsed["black_username"] = args.black_username
        if args.result:
            parsed["result"] = args.result
        data = parsed
    elif args.pgn_file or (not sys.stdin.isatty()):
        if args.pgn_file:
            pgn = Path(args.pgn_file).read_text(encoding="utf-8")
        else:
            pgn = sys.stdin.read()
        parsed = parse_pgn_text(pgn)
        result = args.result or parsed.get("result", "")
        data = {
            "game_id": args.pgn_code,
            "white_username": args.white_username,
            "black_username": args.black_username,
            "white_rating": parsed.get("white_rating", 0),
            "black_rating": parsed.get("black_rating", 0),
            "result": result,
            "white_accuracy": 0.0,
            "black_accuracy": 0.0,
            "Brilliant_white": 0,
            "Brilliant_black": 0,
            "GreatFind_white": 0,
            "GreatFind_black": 0,
            "Book_white": 0,
            "Book_black": 0,
            "BestMove_white": 0,
            "BestMove_black": 0,
            "Excellent_white": 0,
            "Excellent_black": 0,
            "Good_white": 0,
            "Good_black": 0,
            "Inaccuracy_white": 0,
            "Inaccuracy_black": 0,
            "Mistake_white": 0,
            "Mistake_black": 0,
            "Miss_white": 0,
            "Miss_black": 0,
            "Blunder_white": 0,
            "Blunder_black": 0,
        }
    else:
        # Fetch from Chess.com (opens browser like collect)
        print(f"Fetching game {args.pgn_code} from Chess.com...")
        is_pgn_code = not args.pgn_code.isdigit()
        data_fetched = extract_game_review(
            args.pgn_code,
            headless=getattr(args, "headless", False),
            pgn=is_pgn_code,
        )
        if data_fetched:
            data_fetched["white_username"] = args.white_username
            data_fetched["black_username"] = args.black_username
            if args.result:
                data_fetched["result"] = args.result
            data_fetched["game_id"] = args.pgn_code
            data = data_fetched
        elif args.result:
            data = {
                "game_id": args.pgn_code,
                "white_username": args.white_username,
                "black_username": args.black_username,
                "white_rating": 0,
                "black_rating": 0,
                "result": args.result,
                "white_accuracy": 0.0,
                "black_accuracy": 0.0,
                "Brilliant_white": 0,
                "Brilliant_black": 0,
                "GreatFind_white": 0,
                "GreatFind_black": 0,
                "Book_white": 0,
                "Book_black": 0,
                "BestMove_white": 0,
                "BestMove_black": 0,
                "Excellent_white": 0,
                "Excellent_black": 0,
                "Good_white": 0,
                "Good_black": 0,
                "Inaccuracy_white": 0,
                "Inaccuracy_black": 0,
                "Mistake_white": 0,
                "Mistake_black": 0,
                "Miss_white": 0,
                "Miss_black": 0,
                "Blunder_white": 0,
                "Blunder_black": 0,
            }
        else:
            print("Failed to fetch from Chess.com. Use --result to record metadata only.", file=sys.stderr)
            return 1

    conn = get_connection(args.db)
    insert_game(conn, data)
    conn.commit()
    conn.close()

    result_str = data.get("result", "?")
    acc_w = data.get("white_accuracy", 0) or 0
    acc_b = data.get("black_accuracy", 0) or 0
    acc_str = f" (W:{acc_w}% B:{acc_b}%)" if (acc_w or acc_b) else ""
    print(f"Saved: {data['white_username']} vs {data['black_username']} ({result_str}){acc_str}")
    return 0


def cmd_summary(args: argparse.Namespace) -> int:
    """Print season overview."""
    if not Path(args.db).exists():
        print(f"Database not found: {args.db}. Run 'collect' first.", file=sys.stderr)
        return 1

    conn = get_connection(args.db)
    s = get_season_summary(conn)
    conn.close()

    print("\n=== Season Overview ===\n")
    print(f"  Total games: {s['total_games']}")
    print(f"  Unique players: {s['unique_players']}")
    print(f"  Total Brilliant moves: {s['total_brilliant_moves']}")
    print()
    return 0


def parse_args(args: list[str] | None = None) -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Chess club data analytics from Chess.com game reviews."
    )
    parser.add_argument(
        "--db",
        default=DEFAULT_DB_PATH,
        help=f"Database path (default: {DEFAULT_DB_PATH})",
    )
    parser.add_argument(
        "--headless",
        action="store_true",
        help="Run browser headless",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    collect = sub.add_parser("collect", help="Collect game data from CSV")
    collect.add_argument(
        "csv_file",
        help="CSV file with game_id column",
    )
    collect.add_argument(
        "--move-delay",
        type=float,
        default=1.5,
        help="Delay between games in seconds (default: 1.5)",
    )
    collect.set_defaults(func=cmd_collect)

    sub.add_parser("players", help="Show player summaries").set_defaults(func=cmd_players)
    sub.add_parser("summary", help="Show season overview").set_defaults(func=cmd_summary)

    manual_pgn = sub.add_parser(
        "manual-pgn",
        help="Add manually entered PGN (e.g. OTB league game)",
    )
    manual_pgn.add_argument(
        "pgn_code",
        help="Game identifier/code (e.g. jFY6SgYtW)",
    )
    manual_pgn.add_argument(
        "white_username",
        help="White player username",
    )
    manual_pgn.add_argument(
        "black_username",
        help="Black player username",
    )
    manual_pgn.add_argument(
        "--pgn-file",
        "-f",
        help="Path to PGN file (default: read from stdin)",
    )
    manual_pgn.add_argument(
        "--html-file",
        help="Path to Chess.com analysis HTML (parses accuracy, tallies, ratings)",
    )
    manual_pgn.add_argument(
        "--result",
        "-r",
        choices=["1-0", "0-1", "1/2-1/2"],
        help="Game result: 1-0 (white won), 0-1 (black won), 1/2-1/2 (draw). Overrides PGN if set.",
    )
    manual_pgn.set_defaults(func=cmd_manual_pgn)

    return parser.parse_args(args)


def main() -> int:
    """Main entry point."""
    args = parse_args()
    return args.func(args)
