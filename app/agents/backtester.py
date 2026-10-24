"""Phase 9 - agent that owns the long-running backtest tool."""

from agno.agent import Agent

from app.agents.model import pick_model
from app.db import get_db
from app.tools.backtest import backtest

INSTRUCTIONS = [
    "You are Valura Backtester.",
    "When asked to backtest, call backtest(strategy, range) exactly once, then report its result.",
    "Do not invent numbers; only repeat what the tool returned.",
]


def build_backtester() -> Agent:
    return Agent(
        id="backtester",
        name="Backtester",
        model=pick_model(),
        db=get_db(),  # required for background runs
        tools=[backtest],
        instructions=INSTRUCTIONS,
        markdown=True,
    )
