"""Data for the morning briefing.

The portfolio is a real read from Postgres. Watchlist news, price moves and the macro
signal are made-up but stable (derived from the ticker name), so every run gives the
same briefing. simulate_io() adds a 1 second delay to stand in for a slow network call;
it is what lets the Parallel step show a real speed-up.
"""

import hashlib
import time

from sqlalchemy import create_engine, text

from app.db import get_db_url
from app.tools.portfolio import ensure_portfolio_table

FETCH_DELAY_SECONDS = 1.0
DEFAULT_WATCHLIST = ["TSLA", "AMD", "META", "GOOGL"]
HEADLINES = ["beats earnings estimates", "announces product event",
             "faces regulatory probe", "raises full-year guidance"]


def stable_number(*parts: str) -> int:
    """Same input always gives the same number."""
    return int(hashlib.sha256("|".join(parts).encode()).hexdigest()[:8], 16)


def load_positions(user_id: str) -> list[dict]:
    ensure_portfolio_table()
    query = text("SELECT ticker, shares, cost_basis FROM ai.portfolio WHERE user_id = :u ORDER BY ticker")
    with create_engine(get_db_url()).connect() as conn:
        rows = conn.execute(query, {"u": user_id}).fetchall()
    return [{"ticker": t, "shares": float(s), "cost_basis": float(c or 0)} for t, s, c in rows]


def news_for(ticker: str) -> dict:
    phrase = HEADLINES[stable_number("news", ticker) % len(HEADLINES)]
    return {"ticker": ticker, "headline": f"{ticker} {phrase}"}


def day_change_pct(ticker: str) -> float:
    """A fixed pretend price move between -8% and +6%."""
    return round(-8.0 + (stable_number("move", ticker) % 1401) / 100.0, 2)


def macro_signal(override: str | None = None) -> str:
    """'risk-on', 'neutral' or 'circuit-breaker' (only via override)."""
    return override or ("risk-on", "neutral")[stable_number("macro") % 2]


def simulate_io() -> None:
    time.sleep(FETCH_DELAY_SECONDS)
