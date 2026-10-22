"""Fast tests for Phase 5 data and Phase 7 routing. No LLM; the workflow test needs the database."""

import pytest

from app.tools.trading import LARGE_TRADE_USD, check_trade, route_trade_tool
from app.workflows import data
from app.workflows.morning_briefing import build_morning_briefing


def test_trades_over_10k_go_to_the_admin_tool():
    assert route_trade_tool(500) == "propose_trade"
    assert route_trade_tool(LARGE_TRADE_USD) == "propose_trade"          # exactly 10K is still small
    assert route_trade_tool(LARGE_TRADE_USD + 0.01) == "propose_large_trade"


def test_made_up_data_is_stable():
    assert data.day_change_pct("NVDA") == data.day_change_pct("NVDA")
    assert data.news_for("AMD") == data.news_for("AMD")
    assert -8.0 <= data.day_change_pct("TSLA") <= 6.0


def test_macro_override_is_respected():
    assert data.macro_signal("circuit-breaker") == "circuit-breaker"
    assert data.macro_signal() in ("risk-on", "neutral")


def test_trade_checks_refuse_bad_input():
    assert check_trade("demo@valura.dev", "NVDA", "hold", 5, 100) is not None        # bad side
    assert check_trade("demo@valura.dev", "NVDA", "buy", 0, 100) is not None         # zero shares
    assert "not enough cash" in check_trade("demo@valura.dev", "NVDA", "buy", 1e9, 100)


def test_cannot_sell_more_than_held():
    assert "cannot sell" in check_trade("demo@valura.dev", "NVDA", "sell", 1e6, 100)   # holds only 40


def test_circuit_breaker_stops_the_workflow_before_the_portfolio_part():
    text = str(build_morning_briefing().run(
        input="go", session_state={"user_id": "demo@valura.dev", "macro_override": "circuit-breaker"}).content)
    assert "CIRCUIT-BREAKER" in text and "## Portfolio" not in text
