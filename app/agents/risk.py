"""RiskAgent - checks concentration and risk against the portfolio and watchlist (Phase 4)."""

from agno.agent import Agent
from agno.tools.yfinance import YFinanceTools

from app.agents.model import pick_model
from app.tools.portfolio import get_portfolio, list_watchlist_tickers, portfolio_concentration


def build_risk_agent() -> Agent:
    return Agent(
        id="risk-agent",
        name="RiskAgent",
        role="Risk specialist: concentration and watchlist checks.",
        model=pick_model(),
        tools=[
            YFinanceTools(enable_stock_price=True, enable_key_financial_ratios=True),
            get_portfolio,
            portfolio_concentration,
            list_watchlist_tickers,
        ],
        instructions=[
            "Call portfolio_concentration for the user_id you are given.",
            "Mark RED_FLAG when one name is 40% or more of the shares held.",
            "Answer in a few short risk bullets, not a full report.",
        ],
        markdown=True,
    )
