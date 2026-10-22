"""The knowledge base: PgVector with hybrid search (keyword + vector), Phase 3."""

from agno.knowledge.embedder.fastembed import FastEmbedEmbedder
from agno.knowledge.knowledge import Knowledge
from agno.vectordb.pgvector import PgVector
from agno.vectordb.search import SearchType

from app.db import get_db, get_db_url

# The text chunks live in ai.valura_knowledge. (Agno keeps its own list of documents in
# ai.agno_knowledge, so the two tables need different names.)
TABLE = "valura_knowledge"

_knowledge = None


def get_vector_db() -> PgVector:
    return get_knowledge().vector_db


def get_knowledge() -> Knowledge:
    global _knowledge
    if _knowledge is None:
        vector_db = PgVector(
            table_name=TABLE,
            schema="ai",
            db_url=get_db_url(),
            embedder=FastEmbedEmbedder(),          # runs on this computer, no API key
            search_type=SearchType.hybrid,         # BM25-style keyword search + vector search
            vector_score_weight=0.6,
        )
        _knowledge = Knowledge(
            name="Valura Market Knowledge",
            vector_db=vector_db,
            contents_db=get_db(),
            max_results=3,
        )
    return _knowledge
