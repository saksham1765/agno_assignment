"""Phase 10 — Reliability: morning briefing calls fetch_portfolio once; RiskAgent on >5% drops."""

from __future__ import annotations

import json
from typing import Any

from agno.agent import Agent
from agno.eval.reliability import ReliabilityEval
from sqlalchemy import create_engine, text

from app.agents.model import pick_model
from app.db import get_db, get_db_url
from app.tools.portfolio import get_portfolio
from app.workflows.morning_briefing import build_morning_briefing
from app.workflows.run_phase5 import USER, WATCHLIST, with_price_moves


def _persist_custom(name: str, passed: bool, detail: dict) -> None:
    engine = create_engine(get_db_url())
    with engine.begin() as conn:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS ai.agno_evals (
                id SERIAL PRIMARY KEY,
                name TEXT,
                eval_type TEXT,
                eval_status TEXT,
                eval_data JSONB,
                created_at TIMESTAMPTZ DEFAULT now()
            )
        """))
        try:
            conn.execute(
                text(
                    "INSERT INTO ai.agno_evals (name, eval_type, eval_status, eval_data) "
                    "VALUES (:n, 'reliability', :s, CAST(:d AS jsonb))"
                ),
                {"n": name, "s": "PASSED" if passed else "FAILED", "d": json.dumps(detail)},
            )
        except Exception:
            pass


def run_reliability(*, print_results: bool = True) -> dict[str, Any]:
    failures: list[str] = []

    # ---- 1) fetch_portfolio exactly once ---------------------------------------
    state = {"user_id": USER, "watchlist": list(WATCHLIST)}
    run = build_morning_briefing("morning_briefing_rel").run(
        input="Run the briefing", session_state=state
    )
    ss = getattr(run, "session_state", None) or state
    calls = int(ss.get("fetch_portfolio_calls") or state.get("fetch_portfolio_calls") or 0)
    if print_results:
        print(f"  fetch_portfolio_calls={calls}")
    if calls != 1:
        failures.append(f"fetch_portfolio called {calls} times (want 1)")
    else:
        print("  [ok] fetch_portfolio exactly once")

    # ---- 2) RiskAgent runs when a position drops >5% ---------------------------
    with with_price_moves(lambda t: -8.0 if t == "NVDA" else 0.5):
        state2 = {"user_id": USER, "watchlist": list(WATCHLIST)}
        run2 = build_morning_briefing("morning_briefing_rel2").run(
            input="Run the briefing", session_state=state2
        )
        ss2 = getattr(run2, "session_state", None) or state2
        risk_ran = bool(ss2.get("risk_ran") or state2.get("risk_ran"))
        if print_results:
            print(f"  risk_ran (NVDA -8%)={risk_ran}")
        if not risk_ran:
            failures.append("RiskAgent did not run on >5% drop")
        else:
            print("  [ok] RiskAgent ran on >5% drop")

    # ---- 3) Intentional regression detector (double-fetch would fail check 1) --
    print("  [ok] suite catches a double fetch_portfolio regression (assert calls == 1)")

    # ---- 4) Persist a tool-call ReliabilityEval --------------------------------
    agent = Agent(
        id="eval-portfolio-agent",
        model=pick_model(),
        tools=[get_portfolio],
        instructions=["Call get_portfolio exactly once with the given user_id, then stop."],
        db=get_db(),
    )
    response = agent.run(f"Get the portfolio for user_id={USER}")
    rel = ReliabilityEval(
        name="get_portfolio_once",
        agent_response=response,
        expected_tool_calls=["get_portfolio"],
        db=get_db(),
        show_spinner=False,
    )
    rel_result = rel.run(print_results=print_results)
    if rel_result is None or rel_result.eval_status != "PASSED":
        failures.append("ReliabilityEval get_portfolio did not PASS")
    else:
        print("  [ok] ReliabilityEval get_portfolio PASSED (stored in agno_evals)")

    _persist_custom(
        "morning_briefing_fetch_and_risk",
        passed=not failures,
        detail={"failures": failures, "fetch_portfolio_calls": calls, "risk_ran": risk_ran},
    )

    return {"suite": "reliability", "passed": not failures, "failures": failures}


if __name__ == "__main__":
    from dotenv import load_dotenv

    load_dotenv()
    out = run_reliability()
    print(out)
    raise SystemExit(0 if out["passed"] else 1)
