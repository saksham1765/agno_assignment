"""Reporter - writes the final answer from the other members' findings (Phase 4)."""

from agno.agent import Agent

from app.agents.model import pick_model


def build_reporter() -> Agent:
    return Agent(
        id="reporter",
        name="Reporter",
        role="Writes the final short answer from the teammates' findings.",
        model=pick_model(),
        instructions=[
            "Write the final answer in clear markdown, using only what the teammates found.",
            "For a ticker use ## Business, ## Financials, ## Risks. Say who found each fact.",
        ],
        markdown=True,
    )
