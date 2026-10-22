"""DataAnalyst - Yahoo Finance numbers plus the Postgres portfolio (Phase 4)."""

from agno.agent import Agent
from agno.tools.yfinance import YFinanceTools

from app.agents.model import pick_model
from app.tools.portfolio import get_portfolio, portfolio_concentration


def build_data_analyst() -> Agent:
    return Agent(
        id="data-analyst",
        name="DataAnalyst",
        role="Data specialist: Yahoo Finance prices and fundamentals, and the user's portfolio.",
        model=pick_model(),
        tools=[
            YFinanceTools(
                enable_stock_price=True,
                enable_company_info=True,
                enable_key_financial_ratios=True,
                enable_stock_fundamentals=True,
            ),
            get_portfolio,
            portfolio_concentration,
        ],
        instructions=[
            "Use Yahoo Finance for prices and fundamentals, the Postgres tools for holdings.",
            "Be concise. Short tables are fine.",
        ],
        markdown=True,
    )
