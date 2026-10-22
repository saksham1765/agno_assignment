"""NewsAgent - Yahoo Finance headlines first, web search as a back-up (Phase 4)."""

from agno.agent import Agent

from app.agents.model import pick_model, web_search_toolkit
from app.tools.yahoo_news import get_yahoo_news


def build_news_agent() -> Agent:
    return Agent(
        id="news-agent",
        name="NewsAgent",
        role="News specialist: recent headlines and market-moving stories.",
        model=pick_model(),
        tools=[get_yahoo_news, web_search_toolkit()],
        instructions=[
            "Use get_yahoo_news(symbol) first.",
            "Only if that is not enough, use search_news or web_search. If they say there are "
            "no results, do not retry: report what Yahoo Finance gave you.",
            "Give 3-5 headlines with publisher and date. Point out anything that looks risky.",
        ],
        markdown=True,
    )
