"""Postgres portfolio tools for the DataAnalyst and RiskAgent (Phase 4)."""

from sqlalchemy import create_engine, text

from app.db import get_db_url

CONCENTRATION_RED_FLAG_PCT = 40.0

# Sample positions that are loaded the first time (user, ticker, shares, cost basis).
SAMPLE_POSITIONS = [
    ("demo@valura.dev", "NVDA", 40, 120.0),
    ("demo@valura.dev", "AAPL", 80, 170.0),
    ("demo@valura.dev", "MSFT", 30, 380.0),
    ("admin@valura.dev", "NVDA", 100, 110.0),
    ("admin@valura.dev", "META", 25, 450.0),
    ("admin@valura.dev", "TSLA", 50, 200.0),
]


def run_sql(query: str, **params):
    with create_engine(get_db_url()).begin() as conn:
        result = conn.execute(text(query), params)
        return result.fetchall() if result.returns_rows else []


def ensure_portfolio_table() -> None:
    """Create ai.portfolio and add the sample positions if it is empty."""
    run_sql("CREATE SCHEMA IF NOT EXISTS ai")
    run_sql("""CREATE TABLE IF NOT EXISTS ai.portfolio (
                   user_id TEXT NOT NULL, ticker TEXT NOT NULL,
                   shares DOUBLE PRECISION NOT NULL DEFAULT 0, cost_basis DOUBLE PRECISION,
                   PRIMARY KEY (user_id, ticker))""")
    if run_sql("SELECT COUNT(*) FROM ai.portfolio")[0][0] == 0:
        for user, ticker, shares, cost in SAMPLE_POSITIONS:
            run_sql("INSERT INTO ai.portfolio VALUES (:u, :t, :s, :c) ON CONFLICT DO NOTHING",
                    u=user, t=ticker, s=shares, c=cost)


def get_portfolio(user_id: str = "demo@valura.dev") -> str:
    """List a user's positions from Postgres.

    Args:
        user_id: The user's id, e.g. demo@valura.dev.
    """
    ensure_portfolio_table()
    rows = run_sql("SELECT ticker, shares, cost_basis FROM ai.portfolio WHERE user_id = :u ORDER BY ticker",
                   u=user_id)
    if not rows:
        return f"No portfolio rows for user_id={user_id}"
    lines = [f"{ticker}: shares={shares} cost_basis={cost}" for ticker, shares, cost in rows]
    return f"Portfolio for {user_id}:\n" + "\n".join(lines)


def portfolio_concentration(user_id: str = "demo@valura.dev") -> str:
    """Show each position as a percent of all shares held, and flag any over 40% as RED_FLAG.

    Args:
        user_id: The user's id, e.g. demo@valura.dev.
    """
    ensure_portfolio_table()
    rows = run_sql("SELECT ticker, shares FROM ai.portfolio WHERE user_id = :u ORDER BY ticker", u=user_id)
    if not rows:
        return f"No portfolio rows for user_id={user_id}"
    total = sum(shares for _, shares in rows)
    lines = []
    for ticker, shares in rows:
        percent = 100 * shares / total
        flag = " RED_FLAG" if percent >= CONCENTRATION_RED_FLAG_PCT else ""
        lines.append(f"{ticker}: {percent:.1f}% of share count{flag}")
    return f"Concentration for {user_id}:\n" + "\n".join(lines)


def list_watchlist_tickers(tickers: str = "") -> str:
    """Clean up a comma-separated watchlist such as 'nvda, aapl' for risk checks.

    Args:
        tickers: Comma-separated tickers.
    """
    cleaned = [t.strip().upper() for t in tickers.split(",") if t.strip()]
    return "Watchlist: " + ", ".join(cleaned) if cleaned else "Watchlist is empty."
