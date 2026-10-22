"""Phase 2 - a research agent that remembers: Postgres sessions, memory, a watchlist.

Run:  python -m app.agents.persistent
"""

import time
from uuid import uuid4

from agno.agent import Agent
from agno.tools.yfinance import YFinanceTools
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

from app.agents.model import pick_model, web_search_toolkit
from app.db import get_db, get_db_url
from app.tools.watchlist import add_to_watchlist, remove_from_watchlist
from app.tools.yahoo_news import get_yahoo_news

load_dotenv()

PHASE2_INSTRUCTIONS = [
    "You are Valura Research, a market research assistant with memory.",
    "Watchlist: {watchlist}",                       # filled in from session_state
    "Remember what the user tells you about their preferences.",
    "To track a ticker, call add_to_watchlist.",
    "For a ticker question answer with exactly three sections: ## Business, ## Financials, ## Risks.",
    "For other questions (preferences, watchlist, memory) answer briefly without those sections.",
]


def build_persistent_research_agent() -> Agent:
    return Agent(
        name="Research",
        model=pick_model(),
        db=get_db(),                                # sessions, runs and memories go to Postgres
        tools=[
            YFinanceTools(
                enable_stock_price=True,
                enable_company_info=True,
                enable_stock_fundamentals=True,
                enable_key_financial_ratios=True,
                enable_analyst_recommendations=True,
            ),
            get_yahoo_news,
            web_search_toolkit(),
            add_to_watchlist,                       # these two change session_state
            remove_from_watchlist,
        ],
        instructions=PHASE2_INSTRUCTIONS,
        session_state={"watchlist": []},
        add_history_to_context=True,
        num_history_runs=5,
        update_memory_on_run=True,
        add_memories_to_context=True,
        markdown=True,
    )


def table_count(table: str) -> int:
    with create_engine(get_db_url()).connect() as conn:
        return conn.execute(text(f"SELECT COUNT(*) FROM ai.{table}")).scalar_one()


def ask(agent: Agent, message: str, user: str, session: str) -> str:
    answer = agent.run(message, user_id=user, session_id=session).content
    print(f"  > {message}\n    {str(answer)[:160]!r}")
    time.sleep(2)
    return str(answer)


def main():
    print("=== Phase 2 - sessions, memory, watchlist ===")
    alice, session = "alice@valura.dev", f"phase2-{uuid4().hex[:6]}"
    agent = build_persistent_research_agent()

    print("\n[1] A 5-turn conversation, one session")
    for message in [
        "Hi, I'm Alice. My risk tolerance is conservative, I only want large-cap tech.",
        "Add NVDA and AAPL to my watchlist.",
        "What tickers are on my watchlist right now?",
        "Remind me what my risk tolerance is.",
        "One sentence on my first watchlist ticker.",
    ]:
        ask(agent, message, alice, session)
    watchlist = agent.get_session_state(session_id=session)["watchlist"]
    print("    watchlist in session_state:", watchlist)
    assert watchlist == ["NVDA", "AAPL"]

    print("\n[2] Two users must not share memories")
    for name, message in [("bob", "My name is Bob and I only invest in energy stocks like XOM."),
                          ("carol", "My name is Carol and I prefer biotech, especially MRNA.")]:
        ask(agent, message, f"{name}@valura.dev", f"{name}-{uuid4().hex[:6]}")
    bob = " ".join(str(m.memory) for m in agent.get_user_memories(user_id="bob@valura.dev"))
    carol = " ".join(str(m.memory) for m in agent.get_user_memories(user_id="carol@valura.dev"))
    print("    bob  :", bob[:90], "\n    carol:", carol[:90])
    assert "XOM" in bob and "MRNA" not in bob
    assert "MRNA" in carol.upper() and "XOM" not in carol

    print("\n[3] A brand-new agent (a 'restart') still knows Alice's session")
    answer = ask(build_persistent_research_agent(), "What is my risk tolerance and my watchlist?",
                 alice, session)
    assert "conservative" in answer.lower() and "NVDA" in answer

    print("\n[4] The tables hold rows")
    for table in ("agno_sessions", "agno_memories"):
        print(f"    ai.{table}: {table_count(table)} rows")
        assert table_count(table) > 0

    print("\nPhase 2 checks passed")


if __name__ == "__main__":
    main()
