"""Watchlist tools that mutate session_state via RunContext."""

from __future__ import annotations

from agno.run import RunContext


def add_to_watchlist(run_context: RunContext, ticker: str) -> str:
    """Add a ticker to the user's watchlist in session_state."""
    state = run_context.session_state
    if state is None:
        return "No session_state available."

    watchlist = state.setdefault("watchlist", [])
    symbol = ticker.strip().upper()
    if symbol in watchlist:
        return f"{symbol} is already on the watchlist: {watchlist}"

    watchlist.append(symbol)
    return f"Added {symbol}. Watchlist: {watchlist}"


def remove_from_watchlist(run_context: RunContext, ticker: str) -> str:
    """Remove a ticker from the user's watchlist in session_state."""
    state = run_context.session_state
    if state is None:
        return "No session_state available."

    watchlist = state.setdefault("watchlist", [])
    symbol = ticker.strip().upper()
    if symbol not in watchlist:
        return f"{symbol} is not on the watchlist: {watchlist}"

    watchlist.remove(symbol)
    return f"Removed {symbol}. Watchlist: {watchlist}"
