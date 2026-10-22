"""Phase 3 rubric: does hybrid search beat vector-only on at least one query?

For each query we know which document SHOULD be the top answer (an exact term
that only that document contains). We compare the rank of that document under
vector-only, keyword-only and hybrid search, using the live knowledge base.
"""

from __future__ import annotations

from dotenv import load_dotenv

load_dotenv()
from agno.vectordb.search import SearchType  # noqa: E402

from app.knowledge.base import get_knowledge, get_vector_db  # noqa: E402

# (query, substring that must appear in the correct chunk, label)
CASES = [
    ("Stewart Stecker", "Stecker", "speaker name in the REAL NVDA transcript"),
    ("Luca Maestri", "Maestri", "speaker name in the REAL AAPL transcript"),
    ("CoWoS", "CoWoS", "rare acronym in a 10-K"),
    ("DMA sideloading", "sideloading", "regulatory term in AAPL note"),
    ("Blackwell HBM packaging", "HBM", "mixed keyword + concept"),
]


def rank_of(docs, needle: str):
    for i, d in enumerate(docs, 1):
        if needle.lower() in (d.content or "").lower():
            return i
    return None


def main() -> None:
    kb, vdb = get_knowledge(), get_vector_db()
    rows = []
    for query, needle, label in CASES:
        ranks = {}
        for st in (SearchType.vector, SearchType.keyword, SearchType.hybrid):
            vdb.search_type = st
            ranks[st.value] = rank_of(kb.search(query, max_results=10), needle)
        vdb.search_type = SearchType.hybrid
        rows.append((query, label, ranks))

    print(f"{'query':<26}{'vector':>8}{'keyword':>9}{'hybrid':>8}   note")
    wins = 0
    for q, label, r in rows:
        f = lambda v: "miss" if v is None else str(v)
        v, h = r["vector"], r["hybrid"]
        better = h is not None and (v is None or h < v)
        wins += better
        print(f"{q:<26}{f(v):>8}{f(r['keyword']):>9}{f(h):>8}   {label}{'  <-- hybrid wins' if better else ''}")
    print(f"\nhybrid strictly beats vector-only on {wins}/{len(rows)} queries")
    assert wins >= 1, "hybrid did not beat vector-only on any query"


if __name__ == "__main__":
    main()
