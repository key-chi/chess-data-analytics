"""Browser automation for Chess.com game review data extraction."""

import os
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

from .config import (
    COLLAPSE_EXPAND_DELAY,
    GAME_REVIEW_URL,
    INITIAL_LOAD_DELAY,
    PAGE_LOAD_TIMEOUT,
    PGN_ANALYSIS_URL,
    TALLIES_COLLAPSE_BUTTON,
    USER_DATA_DIR,
    VIEWPORT_HEIGHT,
    VIEWPORT_WIDTH,
)
from .parser import parse_game_review_page


def extract_game_review(
    game_id: str,
    headless: bool = False,
    pgn: bool = False,
) -> dict | None:
    """
    Load a Chess.com game review page and extract parsed data.
    Returns parsed game data dict, or None on failure.
    If pgn=True, uses PGN analysis URL (for codes like jFY6SgYtW).
    """
    url = (
        PGN_ANALYSIS_URL.format(game_id=game_id)
        if pgn
        else GAME_REVIEW_URL.format(game_id=game_id)
    )

    with sync_playwright() as p:
        context = p.chromium.launch_persistent_context(
            user_data_dir=USER_DATA_DIR,
            headless=headless,
            viewport={"width": VIEWPORT_WIDTH, "height": VIEWPORT_HEIGHT},
            args=["--disable-blink-features=AutomationControlled"],
        )
        context.set_default_timeout(PAGE_LOAD_TIMEOUT)
        page = context.pages[0] if context.pages else context.new_page()

        try:
            page.goto(url, wait_until="domcontentloaded")
            page.wait_for_load_state("networkidle", timeout=PAGE_LOAD_TIMEOUT)
        except Exception as e:
            print(f"Error loading page: {e}", file=sys.stderr)
            context.close()
            return None

        # Wait for board or main content
        try:
            page.wait_for_selector(
                "canvas, [class*='board'], [class*='chess']", timeout=INITIAL_LOAD_DELAY
            )
        except Exception:
            if "login" in page.url.lower() or "signin" in page.url.lower():
                print(
                    "Redirected to login. Log in manually in the browser window, "
                    "then re-run the script.",
                    file=sys.stderr,
                )
            else:
                print(
                    "Game review page did not load. Check the game ID and your connection.",
                    file=sys.stderr,
                )
            context.close()
            return None

        # Wait for Chess.com to finish game review computation
        page.wait_for_timeout(INITIAL_LOAD_DELAY)

        # Wait for tallies to appear (game review complete)
        try:
            page.wait_for_selector(
                "[data-cy='game-review-tallies-number-Brilliant-white'], "
                "[data-cy='game-review-tallies-number-BestMove-white']",
                timeout=PAGE_LOAD_TIMEOUT,
            )
        except Exception:
            print(
                f"Game review tallies did not appear for {game_id}. "
                "The game may not be reviewable.",
                file=sys.stderr,
            )
            context.close()
            return None

        # Expand tallies if collapsed (chevron-down = collapsed, chevron-up = expanded)
        collapse_locator = page.locator(TALLIES_COLLAPSE_BUTTON)
        if collapse_locator.count() > 0:
            try:
                btn = collapse_locator.first
                if "chevron-down" in (btn.get_attribute("class") or ""):
                    btn.click()
                    page.wait_for_timeout(COLLAPSE_EXPAND_DELAY)
            except Exception:
                pass  # Non-fatal; proceed with parse

        # Parse the page
        html = page.content()
        context.close()

    data = parse_game_review_page(html, game_id)
    return data
