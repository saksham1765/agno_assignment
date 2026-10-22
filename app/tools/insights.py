"""save_insight - lets the agent write what it learned back into the knowledge base (Phase 3)."""

from typing import Optional

from app.knowledge.base import get_knowledge


def save_insight(title: str, body: str, tags: Optional[str] = None,
                 ticker: Optional[str] = None, year: Optional[int] = None) -> str:
    """Save an insight to the knowledge base so it can be found again later.

    Args:
        title: Short title.
        body: The insight itself (facts, quotes, conclusions).
        tags: Optional comma-separated tags, e.g. "moat,export-controls".
        ticker: Optional ticker, used as a metadata filter.
        year: Optional year, used as a metadata filter.
    """
    metadata = {"doc_type": "insight", "source": "agent_save_insight"}
    if tags:
        metadata["tags"] = tags.strip()
    if ticker:
        metadata["ticker"] = ticker.strip().upper()
    if year is not None:
        metadata["year"] = int(year)

    get_knowledge().insert(
        name=title.strip()[:200],
        # The title is part of the text too: search only reads the text, not the name.
        text_content=f"{title.strip()}\n\n{body.strip()}",
        metadata=metadata,
    )
    return f"Saved insight '{title}' into knowledge."
