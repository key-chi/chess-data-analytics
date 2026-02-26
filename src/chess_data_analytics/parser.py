"""Parse Chess.com game review HTML to extract player and move data."""
import re

from bs4 import BeautifulSoup


def _safe_int(text: str | None) -> int:
    """Parse text to int, return 0 if invalid."""
    if text is None:
        return 0
    text = (text or "").strip()
    if not text:
        return 0
    try:
        return int(text)
    except ValueError:
        return 0


def _safe_float(text: str | None) -> float:
    """Parse text to float, return 0.0 if invalid."""
    if text is None:
        return 0.0
    text = (text or "").strip()
    if not text:
        return 0.0
    try:
        return float(text)
    except ValueError:
        return 0.0


def parse_pgn_text(pgn: str) -> dict:
    """
    Parse raw PGN text to extract result and optional ratings.
    Returns dict with keys: result, white_rating, black_rating (0 if not in PGN).
    """
    result = ""
    result_match = re.search(r'\[Result\s+"([^"]+)"\]', pgn)
    if result_match:
        r = result_match.group(1).strip().replace("\\/", "/")
        if r in ("1-0", "0-1", "1/2-1/2", "*"):
            result = r

    white_rating = 0
    black_rating = 0
    w_match = re.search(r'\[WhiteElo\s+"(\d+)"\]', pgn)
    if w_match:
        white_rating = _safe_int(w_match.group(1))
    b_match = re.search(r'\[BlackElo\s+"(\d+)"\]', pgn)
    if b_match:
        black_rating = _safe_int(b_match.group(1))

    return {"result": result, "white_rating": white_rating, "black_rating": black_rating}


def _extract_pgn_result(html: str) -> str:
    """Extract game result from PGN in window.chesscom.analysis.pgn. Returns '1-0', '0-1', '1/2-1/2', or ''."""
    match = re.search(r"pgn:\s*'(.+?)',", html, re.DOTALL)
    if not match:
        return ""
    try:
        pgn_raw = match.group(1).replace("\\/", "/")  # normalize JSON-escaped slashes
        pgn = pgn_raw.encode().decode("unicode_escape")
    except Exception:
        return ""
    result_match = re.search(r'\[Result\s+"([^"]+)"\]', pgn)
    if not result_match:
        return ""
    result = result_match.group(1).strip().replace("\\/", "/")  # normalize \/ from JSON
    if result in ("1-0", "0-1", "1/2-1/2", "*"):
        return result
    return ""


def _extract_user_details(html: str) -> dict:
    """Extract userDetails JSON from window.chesscom.analysis."""
    # Match userDetails: JSON.parse("...")
    match = re.search(
        r'userDetails:\s*JSON\.parse\s*\(\s*"(.+?)"\s*\)',
        html,
        re.DOTALL,
    )
    if not match:
        return {}
    # Unescape the JSON string
    escaped = match.group(1)
    # Unescape common JSON escapes
    unescaped = escaped.encode().decode("unicode_escape")
    try:
        import json

        return json.loads(unescaped)
    except Exception:
        return {}


def parse_game_review_page(html: str, game_id: str) -> dict:
    """
    Parse game review page HTML to extract player names, move tallies, and ratings.
    Returns a dict suitable for database storage.
    """
    soup = BeautifulSoup(html, "html.parser")

    # Try to get userDetails from embedded JSON (has usernames, gameRating, IDs)
    user_details = _extract_user_details(html)
    white_details = user_details.get("white", {})
    black_details = user_details.get("black", {})

    white_username = white_details.get("username") if isinstance(white_details, dict) else None
    black_username = black_details.get("username") if isinstance(black_details, dict) else None

    # Fallback: parse from DOM
    if not white_username:
        top_player = soup.select_one("[data-cy='analysis-player-Top']")
        if top_player:
            username_el = top_player.select_one("[data-test-element='user-tagline-username']")
            white_username = username_el.get_text(strip=True) if username_el else None

    if not black_username:
        bottom_player = soup.select_one("[data-cy='analysis-player-Bottom']")
        if bottom_player:
            username_el = bottom_player.select_one("[data-test-element='user-tagline-username']")
            black_username = username_el.get_text(strip=True) if username_el else None

    # Game ratings: prefer data-cy="review-rating-1300" (has rating in attribute)
    # Else use span text from .game-overview-row .review-rating-white/black
    # Fallback to userDetails.gameRating (Elo at game time)
    white_rating = 0
    black_rating = 0
    for el in soup.select("[data-cy^='review-rating-']"):
        data_cy = el.get("data-cy", "")
        classes = el.get("class") or []
        try:
            num = int(data_cy.split("-")[-1])
            if "review-rating-white" in classes:
                white_rating = num
            elif "review-rating-black" in classes:
                black_rating = num
        except (ValueError, IndexError):
            pass
    # Fallback: span text in game-overview-row with "Game Rating" (avoids other rows)
    if white_rating == 0 or black_rating == 0:
        for row in soup.select(".game-overview-row"):
            title = row.select_one(".game-overview-row-title")
            if title and "Game Rating" in (title.get_text() or ""):
                if white_rating == 0:
                    w_el = row.select_one(".review-rating-white span")
                    white_rating = _safe_int(w_el.get_text() if w_el else None)
                if black_rating == 0:
                    b_el = row.select_one(".review-rating-black span")
                    black_rating = _safe_int(b_el.get_text() if b_el else None)
                break
    if white_rating == 0 and isinstance(white_details, dict):
        white_rating = white_details.get("gameRating") or 0
    if black_rating == 0 and isinstance(black_details, dict):
        black_rating = black_details.get("gameRating") or 0

    # Parse accuracy (e.g. 81.5, 76.6) - game-overview-row with "Accuracy" or data-cy
    white_accuracy = 0.0
    black_accuracy = 0.0
    for row in soup.select(".game-overview-row"):
        title = row.select_one(".game-overview-row-title")
        if title and "Accuracy" in (title.get_text() or ""):
            w_el = row.select_one(".review-accuracy-white span, [data-cy*='accuracy-white'] span")
            b_el = row.select_one(".review-accuracy-black span, [data-cy*='accuracy-black'] span")
            if w_el:
                white_accuracy = _safe_float(w_el.get_text())
            if b_el:
                black_accuracy = _safe_float(b_el.get_text())
            if white_accuracy == 0 and black_accuracy == 0:
                items = row.select(".game-overview-row-item")
                if len(items) >= 2:
                    white_accuracy = _safe_float(items[0].get_text(strip=True))
                    black_accuracy = _safe_float(items[1].get_text(strip=True))
            break
    if white_accuracy == 0 and black_accuracy == 0:
        for el in soup.select("[data-cy^='review-accuracy-'], [data-cy^='game-review-accuracy-']"):
            data_cy = el.get("data-cy", "")
            classes = el.get("class") or []
            span = el.select_one("span")
            val = _safe_float(span.get_text() if span else None) if span else 0.0
            if val == 0 and data_cy:
                try:
                    val = int(data_cy.split("-")[-1]) / 10.0
                except (ValueError, IndexError):
                    pass
            if "white" in data_cy or "review-accuracy-white" in str(classes):
                white_accuracy = val
            elif "black" in data_cy or "review-accuracy-black" in str(classes):
                black_accuracy = val

    # Parse move tallies
    tallies = {}
    tally_types = [
        "Brilliant",
        "GreatFind",
        "Book",
        "BestMove",
        "Excellent",
        "Good",
        "Inaccuracy",
        "Mistake",
        "Miss",
        "Blunder",
    ]
    for tally_type in tally_types:
        white_el = soup.select_one(f"[data-cy='game-review-tallies-number-{tally_type}-white']")
        black_el = soup.select_one(f"[data-cy='game-review-tallies-number-{tally_type}-black']")
        tallies[f"{tally_type}_white"] = _safe_int(white_el.get_text() if white_el else None)
        tallies[f"{tally_type}_black"] = _safe_int(black_el.get_text() if black_el else None)

    result = _extract_pgn_result(html)

    return {
        "game_id": game_id,
        "white_username": white_username or "",
        "black_username": black_username or "",
        "white_rating": white_rating or 0,
        "black_rating": black_rating or 0,
        "white_accuracy": white_accuracy,
        "black_accuracy": black_accuracy,
        "result": result,
        **tallies,
    }
