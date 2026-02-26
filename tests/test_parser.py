"""Tests for the HTML parser."""

import pytest
from pathlib import Path

from chess_data_analytics.parser import parse_game_review_page, parse_pgn_text

# Sample game HTML files (relative to project root)
SAMPLE_GAMES_DIR = Path(__file__).resolve().parent.parent / "sample_games"


# Minimal HTML with the structure we need (from sample)
SAMPLE_HTML = """
<html>
<body>
<div data-cy="analysis-player-Top">
  <div data-test-element="user-tagline-username">white_player</div>
  <img class="cc-avatar-img" src="https://noavatar.gif" />
</div>
<div data-cy="analysis-player-Bottom">
  <div data-test-element="user-tagline-username">black_player</div>
  <img class="cc-avatar-img" src="https://images.chesscomfiles.com/uploads/v1/user/155108491.cb6a8a46.50x50o.jpg" />
</div>
<div data-cy="game-review-tallies-number-Brilliant-white">0</div>
<div data-cy="game-review-tallies-number-Brilliant-black">1</div>
<div data-cy="game-review-tallies-number-GreatFind-white">1</div>
<div data-cy="game-review-tallies-number-GreatFind-black">0</div>
<div data-cy="game-review-tallies-number-Book-white">5</div>
<div data-cy="game-review-tallies-number-Book-black">5</div>
<div data-cy="game-review-tallies-number-BestMove-white">4</div>
<div data-cy="game-review-tallies-number-BestMove-black">10</div>
<div data-cy="game-review-tallies-number-Excellent-white">11</div>
<div data-cy="game-review-tallies-number-Excellent-black">9</div>
<div data-cy="game-review-tallies-number-Good-white">10</div>
<div data-cy="game-review-tallies-number-Good-black">4</div>
<div data-cy="game-review-tallies-number-Inaccuracy-white">2</div>
<div data-cy="game-review-tallies-number-Inaccuracy-black">4</div>
<div data-cy="game-review-tallies-number-Mistake-white">0</div>
<div data-cy="game-review-tallies-number-Mistake-black">2</div>
<div data-cy="game-review-tallies-number-Miss-white">0</div>
<div data-cy="game-review-tallies-number-Miss-black">0</div>
<div data-cy="game-review-tallies-number-Blunder-white">1</div>
<div data-cy="game-review-tallies-number-Blunder-black">0</div>
<div class="game-overview-row"><span class="game-overview-row-title">Accuracy</span>
  <div class="game-overview-row-item"><div class="review-accuracy-white"><span>76.6</span></div></div>
  <div class="game-overview-row-item"><div class="review-accuracy-black"><span>81.5</span></div></div>
</div>
<div class="game-overview-row"><span class="game-overview-row-title">Game Rating</span>
  <div class="game-overview-row-item"><div class="review-rating-component review-rating-white"><span>1300</span></div></div>
  <div class="game-overview-row-item"><div class="review-rating-component review-rating-black"><span>1450</span></div></div>
</div>
<script>
window.chesscom = { analysis: { pgn: '[Result "0-1"]', } };
</script>
</body>
</html>
"""


def test_parse_game_review_page():
    """Test parsing extracts players, tallies, and ratings."""
    data = parse_game_review_page(SAMPLE_HTML, "165168859868")

    assert data["game_id"] == "165168859868"
    assert data["white_username"] == "white_player"
    assert data["black_username"] == "black_player"

    assert data["Brilliant_white"] == 0
    assert data["Brilliant_black"] == 1
    assert data["GreatFind_white"] == 1
    assert data["Book_white"] == 5
    assert data["BestMove_black"] == 10
    assert data["Blunder_white"] == 1

    assert data["white_rating"] == 1300
    assert data["black_rating"] == 1450
    assert data["white_accuracy"] == 76.6
    assert data["black_accuracy"] == 81.5
    assert data["result"] == "0-1"


def test_parse_draw_result():
    """Test that draw results (escaped as 1\\/2-1\\/2 in JSON) are normalized to 1/2-1/2."""
    html = """
    <html><body>
    <script>
    window.chesscom = { analysis: { pgn: '[Result "1\\/2-1\\/2"]', } };
    </script>
    </body></html>
    """
    data = parse_game_review_page(html, "148226648158")
    assert data["result"] == "1/2-1/2"


def test_parse_draw_from_sample_file():
    """Test parsing draw game from sample_games/draw.html."""
    draw_file = SAMPLE_GAMES_DIR / "draw.html"
    if not draw_file.exists():
        pytest.skip("sample_games/draw.html not found")
    html = draw_file.read_text()
    data = parse_game_review_page(html, "148226648158")
    assert data["result"] == "1/2-1/2"
    assert data["white_username"] == "white_player"
    assert data["black_username"] == "black_player"


def test_parse_win_loss_from_sample_file():
    """Test parsing win/loss game from sample_games/win-loss.html."""
    win_loss_file = SAMPLE_GAMES_DIR / "win-loss.html"
    if not win_loss_file.exists():
        pytest.skip("sample_games/win-loss.html not found")
    html = win_loss_file.read_text()
    data = parse_game_review_page(html, "165168859868")
    assert data["result"] == "0-1"
    assert data["white_username"] == "white_player"
    assert data["black_username"] == "black_player"


def test_parse_custom_from_sample_file():
    """Test parsing custom/editor game from sample_games/custom.html (accuracy, tallies, ratings)."""
    custom_file = SAMPLE_GAMES_DIR / "custom.html"
    if not custom_file.exists():
        pytest.skip("sample_games/custom.html not found")
    html = custom_file.read_text()
    game_id = "1cd09cc8-089e-11f1-a2f4-e57e4701000d"
    data = parse_game_review_page(html, game_id)
    assert data["game_id"] == game_id
    assert data["result"] == "*"
    # custom.html has Top=Black, Bottom=White in the DOM
    assert data["white_username"] == "Black"
    assert data["black_username"] == "White"
    # Accuracy and tallies from Chess.com analysis
    assert data["white_accuracy"] == 73.9
    assert data["black_accuracy"] == 87.7
    assert data["white_rating"] == 1750
    assert data["black_rating"] == 2350
    assert data["Book_white"] == 3
    assert data["BestMove_white"] == 11
    assert data["GreatFind_black"] == 4


def test_parse_pgn_text():
    """Test parsing raw PGN text for result and ratings."""
    pgn = '[Event "League"]\n[White "Alice"]\n[Black "Bob"]\n[Result "1-0"]\n[WhiteElo "1200"]\n[BlackElo "1150"]\n\n1. e4 e5 1-0'
    data = parse_pgn_text(pgn)
    assert data["result"] == "1-0"
    assert data["white_rating"] == 1200
    assert data["black_rating"] == 1150

    pgn_draw = '[Result "1/2-1/2"]\n\n1. e4 e5 1/2-1/2'
    data2 = parse_pgn_text(pgn_draw)
    assert data2["result"] == "1/2-1/2"
    assert data2["white_rating"] == 0
    assert data2["black_rating"] == 0


def test_parse_with_user_details_json():
    """Test parsing when userDetails JSON is present."""
    html = SAMPLE_HTML + '''
    <script>
    userDetails: JSON.parse("{\\"white\\":{\\"username\\":\\"white_player\\",\\"gameRating\\":841},\\"black\\":{\\"username\\":\\"black_player\\",\\"gameRating\\":877}}")
    </script>
    '''
    # Our regex looks for userDetails in window.chesscom.analysis - the sample has different format
    # So DOM fallback should still work
    data = parse_game_review_page(html, "123")
    assert data["white_username"] == "white_player"
    assert data["black_username"] == "black_player"
