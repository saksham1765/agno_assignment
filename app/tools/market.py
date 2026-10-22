"""A tiny Yahoo Finance price lookup used by the trade tools."""

import yfinance as yf


def last_price(ticker: str) -> float:
    """Latest traded price (live during market hours, last close otherwise).

    Raises an error if there is none, because a trade must never use a price of 0.
    """
    price = yf.Ticker(ticker.upper()).fast_info["lastPrice"]
    if not price or price <= 0:
        raise ValueError(f"No Yahoo Finance price for {ticker}")
    return float(price)
