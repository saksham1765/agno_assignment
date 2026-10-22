"""Phase 5 - the morning-briefing workflow.

    Parallel(fetch_portfolio, fetch_watchlist_news, fetch_macro)
      -> macro_gate           stops the workflow on a circuit-breaker
      -> Loop(analyze_ticker) one pass per ticker, so any portfolio size works
      -> research_team        puts the analysis together
      -> Condition(any_red_flag) runs the RiskAgent step only if something is flagged
      -> reporter             writes the Markdown, reading earlier steps by name

By default it uses no LLM, so the same input always gives the same briefing.
Pass use_llm=True in session_state to use the real team and RiskAgent instead.
"""

import json

from agno.workflow import Condition, Loop, Parallel, Step, StepInput, StepOutput, Workflow

from app.workflows import data

RED_FLAG_DROP_PCT = -5.0  # a held position down this much (or more) is a red flag


# ---- small helpers: steps pass JSON text, these keep that out of the way ----

def state(run_context) -> dict:
    """The shared dict every step can read and write."""
    if run_context.session_state is None:
        run_context.session_state = {}
    return run_context.session_state


def send(data_dict: dict) -> StepOutput:
    return StepOutput(content=json.dumps(data_dict))


def fetched(step_input: StepInput, step_name: str) -> dict:
    """Read the output of one of the three parallel fetch steps."""
    return json.loads(step_input.get_step_content("fetch")[step_name])


# ---- 1. Parallel fetch steps -------------------------------------------------

def fetch_portfolio(step_input: StepInput, run_context) -> StepOutput:
    data.simulate_io()
    user_id = state(run_context).get("user_id", "demo@valura.dev")
    return send({"positions": data.load_positions(user_id)})


def fetch_watchlist_news(step_input: StepInput, run_context) -> StepOutput:
    data.simulate_io()
    watchlist = state(run_context).get("watchlist") or data.DEFAULT_WATCHLIST
    return send({"watchlist": list(watchlist)})


def fetch_macro(step_input: StepInput, run_context) -> StepOutput:
    data.simulate_io()
    return send({"signal": data.macro_signal(state(run_context).get("macro_override"))})


# ---- 2. Early stop -----------------------------------------------------------

def macro_gate(step_input: StepInput, run_context) -> StepOutput:
    signal = fetched(step_input, "fetch_macro")["signal"]
    if signal == "circuit-breaker":
        text = ("# Morning Briefing\n\n## Macro\n**CIRCUIT-BREAKER** - markets are stressed. "
                "Workflow stopped; only the macro section is shown.")
        return StepOutput(content=text, stop=True)     # stop=True ends the whole workflow
    return send({"signal": signal})


# ---- 3. Loop: analyse one ticker per pass ------------------------------------

def analyze_ticker(step_input: StepInput, run_context) -> StepOutput:
    memory = state(run_context)
    if "todo" not in memory:                            # first pass: build the to-do list
        held = [p["ticker"] for p in fetched(step_input, "fetch_portfolio")["positions"]]
        watchlist = fetched(step_input, "fetch_watchlist_news")["watchlist"]
        memory["held"] = held
        memory["todo"] = held + [t for t in watchlist if t not in held]
        memory["analysis"] = {}

    ticker = memory["todo"].pop(0)
    change = data.day_change_pct(ticker)
    is_held = ticker in memory["held"]
    memory["analysis"][ticker] = {
        "ticker": ticker,
        "held": is_held,
        "day_change_pct": change,
        "red_flag": is_held and change <= RED_FLAG_DROP_PCT,
        "news": data.news_for(ticker)["headline"],
    }
    return send({"done": not memory["todo"]})


def all_tickers_done(outputs: list) -> bool:
    return json.loads(outputs[-1].content)["done"]      # Loop stops when this is True


# ---- 4. research_team ----------------------------------------------------------

def research_team(step_input: StepInput, run_context) -> StepOutput:
    rows = [state(run_context)["analysis"][t] for t in sorted(state(run_context)["analysis"])]
    result = {"rows": rows}
    if state(run_context).get("use_llm"):
        from app.teams.coordinate import build_coordinate_team

        team = build_coordinate_team()
        result["llm_summary"] = str(team.run("Summarize in 80 words: " + json.dumps(rows),
                                             session_state={"role": "viewer"}).content)
    return send(result)


# ---- 5. Condition: RiskAgent only when something is red-flagged ---------------

def any_red_flag(step_input: StepInput) -> bool:
    rows = json.loads(step_input.get_step_content("research_team"))["rows"]
    return any(row["red_flag"] for row in rows)


def risk_agent_step(step_input: StepInput, run_context) -> StepOutput:
    memory = state(run_context)
    flagged = [t for t, row in sorted(memory["analysis"].items()) if row["red_flag"]]
    memory["risk_ran"] = True
    note = f"RiskAgent: red flags on {', '.join(flagged)} (drop of {RED_FLAG_DROP_PCT}% or more)."
    if memory.get("use_llm"):
        from app.agents.risk import build_risk_agent

        note += "\n" + str(build_risk_agent().run(note).content)
    return StepOutput(content=note)


# ---- 6. Reporter: writes the Markdown ------------------------------------------

def reporter(step_input: StepInput, run_context) -> StepOutput:
    macro = fetched(step_input, "fetch_macro")["signal"]
    positions = fetched(step_input, "fetch_portfolio")["positions"]
    rows = json.loads(step_input.get_step_content("research_team"))["rows"]
    by_ticker = {row["ticker"]: row for row in rows}

    lines = ["# Morning Briefing", "", f"## Macro\nSignal: **{macro}**", "", "## Portfolio"]
    for p in positions:
        row = by_ticker[p["ticker"]]
        flag = " RED FLAG" if row["red_flag"] else ""
        lines.append(f"- {p['ticker']}: {p['shares']:g} sh, {row['day_change_pct']:+.2f}%{flag}")

    lines += ["", "## Watchlist"]
    lines += [f"- {r['ticker']}: {r['day_change_pct']:+.2f}% - {r['news']}" for r in rows if not r["held"]]

    # When the Condition is skipped Agno fills in its own "skipped" text, so only
    # show the risk note if the RiskAgent step really ran.
    risk_note = step_input.get_step_content("risk_condition") if state(run_context).get("risk_ran") else None
    lines += ["", "## Risk", str(risk_note) if risk_note else "No red flags."]
    return StepOutput(content="\n".join(lines))


def build_morning_briefing(name: str = "morning_briefing") -> Workflow:
    return Workflow(
        name=name,
        steps=[
            Parallel(
                Step(name="fetch_portfolio", executor=fetch_portfolio),
                Step(name="fetch_watchlist_news", executor=fetch_watchlist_news),
                Step(name="fetch_macro", executor=fetch_macro),
                name="fetch",
            ),
            Step(name="macro_gate", executor=macro_gate),
            Loop(name="per_ticker_loop", steps=[Step(name="analyze_ticker", executor=analyze_ticker)],
                 end_condition=all_tickers_done, max_iterations=100),
            Step(name="research_team", executor=research_team),
            Condition(name="risk_condition", evaluator=any_red_flag,
                      steps=[Step(name="risk_agent", executor=risk_agent_step)]),
            Step(name="reporter", executor=reporter),
        ],
    )
