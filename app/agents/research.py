"""Phase 1 - one agent, a few tools, streaming and parallel tool calls.

The agent has no database, so it remembers nothing between runs (stateless).

Run:  python -m app.agents.research
"""

import asyncio
import time

from agno.agent import Agent
from agno.tools.yfinance import YFinanceTools
from dotenv import load_dotenv

from app.agents.model import pick_model, web_search_toolkit
from app.tools.yahoo_news import get_yahoo_news

load_dotenv()

QUESTION = "What should I know about NVDA?"

INSTRUCTIONS = [
    "You are Valura Research, a market research assistant.",
    "For any ticker question answer with exactly three markdown sections: "
    "## Business, ## Financials, ## Risks.",
    "Say which tools you used (Yahoo Finance or web search).",
    "Call all the tools you need in the SAME turn so they run at the same time.",
]


def build_research_agent(extra_tools: list | None = None) -> Agent:
    """No db=... here on purpose: this agent is stateless."""
    return Agent(
        name="Research",
        model=pick_model(),
        tools=[
            YFinanceTools(
                enable_stock_price=True,
                enable_company_info=True,
                enable_stock_fundamentals=True,
                enable_key_financial_ratios=True,
                enable_analyst_recommendations=True,
            ),
            get_yahoo_news,         # YFinanceTools' own news call returns nothing, so use this
            web_search_toolkit(),
            *(extra_tools or []),
        ],
        instructions=INSTRUCTIONS,
        markdown=True,
    )


# --- tool timing: records when every tool call starts and ends ----------------

tool_calls = []                     # (tool name, start second, end second)
clock = {"start": time.perf_counter()}


def seconds_now() -> float:
    return time.perf_counter() - clock["start"]


def record_tool_time(function_name, function_call, arguments):
    """An Agno 'tool hook': wraps each tool call and notes its start and end time."""
    start = seconds_now()
    try:
        return function_call(**arguments)
    finally:
        tool_calls.append((function_name, start, seconds_now()))


def print_timing_proof(first_token_at: float):
    print("\n\nTool calls (seconds since the run started):")
    for name, start, end in sorted(tool_calls, key=lambda call: call[1]):
        print(f"  {name:<28} {start:5.2f} -> {end:5.2f}")

    first_start = min(start for _, start, _ in tool_calls)
    last_end = max(end for _, _, end in tool_calls)
    busy_time = sum(end - start for _, start, end in tool_calls)
    print(f"\n  all tools finished in {last_end - first_start:.1f}s; run one by one they would take {busy_time:.1f}s")
    print(f"  first streamed text at {first_token_at:.1f}s, last tool finished at {last_end:.1f}s")

    overlap = any(a[1] < b[2] and b[1] < a[2] for i, a in enumerate(tool_calls) for b in tool_calls[i + 1:])
    assert overlap, "no two tool calls overlapped"
    print("  [ok] tool calls ran at the same time")
    assert first_token_at < last_end, "text did not start before the tools finished"
    print("  [ok] text streamed before all tool calls finished")


async def stream_answer(agent: Agent) -> float:
    """Async run that streams text as it arrives. Returns when the first text appeared."""
    clock["start"] = time.perf_counter()        # time zero = the moment this run begins
    first_token_at = None
    async for event in agent.arun(QUESTION, stream=True):
        if event.content:
            first_token_at = first_token_at or seconds_now()
            print(event.content, end="", flush=True)
    return first_token_at


def main():
    agent = build_research_agent()
    assert agent.db is None
    print("=== Phase 1 - one agent, one question ===")
    print(f"database: {agent.db}   (None = stateless)\n")

    print("--- 1. print_response ---")
    start = time.perf_counter()
    agent.print_response(QUESTION, stream=True)
    seconds = time.perf_counter() - start
    print(f"\n[{seconds:.0f}s]" + ("  [ok] under 30 seconds" if seconds < 30 else "  too slow"))
    assert seconds < 30

    print("\n--- 2. arun with streaming (tool timing recorded) ---")
    agent.tool_hooks = [record_tool_time]
    first_token_at = asyncio.run(stream_answer(agent))
    print_timing_proof(first_token_at)

    print("\nPhase 1 checks passed")


if __name__ == "__main__":
    main()
