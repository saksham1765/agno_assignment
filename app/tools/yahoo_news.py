"""Yahoo Finance news via yfinance's Search endpoint.

Agno's YFinanceTools.get_company_news uses `Ticker.news`, which Yahoo currently
returns empty for every ticker. `yfinance.Search(...).news` still works, so this
tool is the Yahoo-backed news source used by NewsAgent.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone


def get_yahoo_news(symbol: str, num_stories: int = 5) -> str:
    """Get recent Yahoo Finance headlines for a ticker.

    Args:
        symbol: Ticker symbol, e.g. NVDA.
        num_stories: How many headlines to return (max 10).

    Returns:
        JSON list of {title, publisher, published, link}, or an empty-result message.
    """
    import yfinance as yf

    sym = symbol.strip().upper()
    limit = max(1, min(int(num_stories), 10))
    try:
        items = yf.Search(sym, news_count=limit).news or []
    except Exception as exc:
        return f"Yahoo Finance news unavailable for {sym}: {type(exc).__name__}"
    out = []
    for n in items[:limit]:
        ts = n.get("providerPublishTime")
        published = (
            datetime.fromtimestamp(int(ts), tz=timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
            if ts else None
        )
        out.append({
            "title": n.get("title"),
            "publisher": n.get("publisher"),
            "published": published,
            "link": n.get("link"),
        })
    if not out:
        return f"No Yahoo Finance headlines found for {sym}."
    return json.dumps(out, indent=2, ensure_ascii=False)
