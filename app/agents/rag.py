"""Phase 3 - Knowledge and RAG.

The agent searches a hybrid (BM25 + vector) PgVector knowledge base and can save
its own insights back into it.

Run:  python -m app.agents.rag
"""

from uuid import uuid4

from agno.agent import Agent
from dotenv import load_dotenv

from app.agents.model import pick_model
from app.db import get_db
from app.knowledge.base import get_knowledge
from app.tools.insights import save_insight

load_dotenv()

INSTRUCTIONS = [
    "You are Valura Research. Always call search_knowledge_base before answering questions "
    "about filings, earnings calls, risks or saved insights.",
    "Filter keys you may use: ticker (e.g. NVDA), year (e.g. 2024), "
    "doc_type (10-K, earnings_transcript, analyst_note, insight).",
    "If a filtered search finds nothing, search again without filters.",
    "To save a note or insight, call save_insight.",
    "Name the document you used. Keep answers under 200 words.",
]


def build_rag_agent() -> Agent:
    return Agent(
        name="Research",
        model=pick_model(),
        db=get_db(),
        knowledge=get_knowledge(),
        search_knowledge=True,                 # agentic RAG
        enable_agentic_knowledge_filters=True,
        tools=[save_insight],
        instructions=INSTRUCTIONS,
        add_history_to_context=True,
        num_history_runs=2,
        tool_call_limit=3,
        markdown=True,
    )


def main():
    kb = get_knowledge()
    agent = build_rag_agent()
    user = "analyst@valura.dev"

    print("=== Phase 3 - Knowledge and RAG ===")

    # 1) Hybrid search: show the top hits with their scores.
    query = "export controls advanced accelerators"
    hits = kb.search(query, max_results=3)
    print(f"\n[1] Hybrid search for {query!r}:")
    for doc in hits:
        print(f"    {doc.name}  score={doc.meta_data.get('similarity_score', 0):.2f}")
    assert hits

    # 2) Metadata filter: the NVDA filter must leave only NVDA documents.
    all_hits = kb.search("supply chain risk", max_results=10)
    nvda_hits = kb.search("supply chain risk", max_results=10, filters={"ticker": "NVDA", "year": 2024})
    print(f"\n[2] No filter: {sorted({d.meta_data['ticker'] for d in all_hits})}"
          f" | ticker=NVDA: {sorted({d.meta_data['ticker'] for d in nvda_hits})}")
    assert nvda_hits and all(d.meta_data["ticker"] == "NVDA" for d in nvda_hits)

    # 3) Two-filing question: the agent has to look in the NVDA and the AAPL filing.
    print("\n[3] Question that needs two filings")
    run = agent.run(
        "Compare NVIDIA and Apple on supply-chain risk using their 10-Ks. Search each company "
        "separately (ticker filter) and answer in 80 words.",
        user_id=user, session_id=f"p3-{uuid4().hex[:6]}",
    )
    print("   ", str(run.content)[:300].replace("\n", " "))

    # 4) The agent saves an insight itself, and a NEW session finds it again.
    marker = f"INS-{uuid4().hex[:6]}"
    print(f"\n[4] Agent saves an insight ({marker}), then a new session reads it")
    run = agent.run(
        f"Search the knowledge base for NVIDIA supply-chain risk, then call save_insight with "
        f"title 'NVDA supply chain takeaway {marker}', a one-sentence body, tags 'supply-chain', "
        f"ticker NVDA, year 2024.",
        user_id=user, session_id=f"p3-{uuid4().hex[:6]}",
    )
    assert "save_insight" in [t.tool_name for t in run.tools], "agent did not save an insight"
    assert kb.search(marker, filters={"doc_type": "insight"}), "insight not in the knowledge base"

    run = agent.run(
        f"Search the knowledge base for the insight whose title contains '{marker}' and reply "
        f"with its full title.",
        user_id=user, session_id=f"p3-{uuid4().hex[:6]}",
    )
    assert marker in str(run.content), "new session did not find the saved insight"
    print("    [ok] saved and found again")

    print("\nPhase 3 checks passed")


if __name__ == "__main__":
    main()
