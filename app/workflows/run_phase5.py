"""Phase 5 demo: run the morning briefing and check the assignment's criteria.

Run:  python -m app.workflows.run_phase5
"""

import time

from agno.workflow import Parallel, Step, Workflow
from dotenv import load_dotenv

load_dotenv()

from app.tools.portfolio import ensure_portfolio_table  # noqa: E402
from app.workflows import data  # noqa: E402
from app.workflows.morning_briefing import (  # noqa: E402
    build_morning_briefing, fetch_macro, fetch_portfolio, fetch_watchlist_news)

USER = "demo@valura.dev"                        # has 3 positions: NVDA, AAPL, MSFT
WATCHLIST = ["TSLA", "AMD", "META", "GOOGL"]    # 4 watchlist tickers


def briefing(**settings) -> str:
    state = {"user_id": USER, "watchlist": list(WATCHLIST), **settings}
    return str(build_morning_briefing().run(input="Run the briefing", session_state=state).content)


def with_price_moves(change_for_ticker):
    """Temporarily replace the pretend price moves (to fake a red flag)."""
    class Patch:
        def __enter__(self):
            self.original = data.day_change_pct
            data.day_change_pct = change_for_ticker
        def __exit__(self, *args):
            data.day_change_pct = self.original
    return Patch()


def check_end_to_end():
    print("\n[1] End to end: 3 positions + 4 watchlist tickers")
    text = briefing()
    print(text)
    assert all(t in text for t in ["NVDA", "AAPL", "MSFT", *WATCHLIST])


def check_parallel_is_faster():
    print("\n[2] Parallel vs one-after-the-other")
    fetches = [("fetch_portfolio", fetch_portfolio), ("fetch_watchlist_news", fetch_watchlist_news),
               ("fetch_macro", fetch_macro)]
    steps = [Step(name=name, executor=fn) for name, fn in fetches]
    one_by_one = Workflow(name="sequential", steps=steps)
    together = Workflow(name="parallel", steps=[Parallel(*steps, name="fetch")])
    state = {"user_id": USER, "watchlist": WATCHLIST}

    start = time.perf_counter()
    one_by_one.run(input="x", session_state=dict(state))
    sequential = time.perf_counter() - start
    start = time.perf_counter()
    together.run(input="x", session_state=dict(state))
    parallel = time.perf_counter() - start

    saved = 100 * (sequential - parallel) / sequential
    print(f"    sequential {sequential:.1f}s, parallel {parallel:.1f}s -> {saved:.0f}% faster")
    assert saved >= 30


def check_red_flag_condition():
    print("\n[3] RiskAgent step runs only when there is a red flag")
    with with_price_moves(lambda t: -9.0 if t == "NVDA" else 1.0):
        flagged = briefing()
    assert "RiskAgent: red flags on NVDA" in flagged
    with with_price_moves(lambda t: 1.0):
        clean = briefing()
    assert "RiskAgent" not in clean and "No red flags." in clean


def check_circuit_breaker_stops_early():
    print("\n[4] Circuit-breaker stops the workflow")
    text = briefing(macro_override="circuit-breaker")
    print(text)
    assert "CIRCUIT-BREAKER" in text and "## Portfolio" not in text


def check_same_input_same_output():
    print("\n[5] Same input -> same output")
    assert briefing() == briefing() == briefing()


def check_any_portfolio_size():
    print("\n[6] The Loop copes with 1 and 7 watchlist tickers")
    for watchlist in (["TSLA"], ["TSLA", "AMD", "META", "GOOGL", "NFLX", "ORCL", "CRM"]):
        assert all(t in briefing(watchlist=watchlist) for t in watchlist)


def check_workflow_is_an_agent_tool():
    print("\n[7] The Phase 1 research agent can call the workflow")
    from agno.tools.workflow import WorkflowTools

    from app.agents.research import build_research_agent

    tool = WorkflowTools(workflow=build_morning_briefing("morning_briefing_tool"))
    agent = build_research_agent(extra_tools=[tool])
    names = [name for toolkit in agent.tools if hasattr(toolkit, "functions") for name in toolkit.functions]
    assert "run_workflow" in names, names


if __name__ == "__main__":
    print("=== Phase 5 - Morning briefing workflow ===")
    ensure_portfolio_table()
    check_end_to_end()
    check_parallel_is_faster()
    check_red_flag_condition()
    check_circuit_breaker_stops_early()
    check_same_input_same_output()
    check_any_portfolio_size()
    check_workflow_is_an_agent_tool()
    print("\nPhase 5 checks passed")
