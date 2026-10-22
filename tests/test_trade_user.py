"""Slow test (real LLM + database): a trade is recorded under the user who asked for it."""

import pytest
from sqlalchemy import create_engine, text

from app.agents.model import has_llm_key
from app.agents.trader import build_trader
from app.db import get_db_url

pytestmark = pytest.mark.skipif(not has_llm_key(), reason="needs an LLM key")


def test_trade_is_recorded_under_the_real_user():
    user = "carol@valura.dev"
    agent = build_trader(["MSFT"])
    run = agent.run("Buy 1 share of MSFT.", user_id=user, session_id="t-user-1")
    assert run.is_paused
    for requirement in run.active_requirements:
        requirement.confirm()
    agent.continue_run(run_response=run)

    with create_engine(get_db_url()).connect() as conn:
        users = conn.execute(text("SELECT DISTINCT user_id FROM ai.trades WHERE ticker = 'MSFT'")).scalars().all()
    assert user in users and "demo" not in users
