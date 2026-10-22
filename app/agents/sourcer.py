"""Sourcer - finds sources on the web (Phase 4)."""

from agno.agent import Agent

from app.agents.model import pick_model, web_search_toolkit


def build_sourcer() -> Agent:
    return Agent(
        id="sourcer",
        name="Sourcer",
        role="Web research specialist: finds sources and recent context.",
        model=pick_model(),
        tools=[web_search_toolkit()],
        instructions=[
            "Search the web for facts. Prefer primary sources and give the URLs.",
            "Leave market prices to the DataAnalyst.",
        ],
        markdown=True,
    )
