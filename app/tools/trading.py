"""Phase 7 - the trade tools. Each one is guarded by a human step (see SECURITY.md).

    propose_trade        @tool(requires_confirmation=True)  the user confirms
    propose_large_trade  @approval(type="required")         an admin must approve (over $10K)
    record_trade_note    @approval(type="audit")            the user confirms, an audit record is kept

execute_trade is a STUB: it only writes a row to ai.trades. No real brokerage is involved.
"""

from agno.approval import approval
from agno.run import RunContext
from agno.tools import tool
from sqlalchemy import create_engine, text

from app.db import get_db_url
from app.tools.market import last_price

LARGE_TRADE_USD = 10_000
STARTING_CASH_USD = 1_000_000      # every user starts with this much (pretend) cash


def run_sql(query: str, **params) -> list:
    with create_engine(get_db_url()).begin() as conn:
        result = conn.execute(text(query), params)
        return result.fetchall() if result.returns_rows else []


def ensure_trade_tables() -> None:
    run_sql("""CREATE TABLE IF NOT EXISTS ai.trades (
                   id SERIAL PRIMARY KEY, user_id TEXT, ticker TEXT, side TEXT,
                   qty DOUBLE PRECISION, price DOUBLE PRECISION, notional DOUBLE PRECISION,
                   created_at TIMESTAMPTZ DEFAULT now())""")
    run_sql("""CREATE TABLE IF NOT EXISTS ai.audit_log (
                   id SERIAL PRIMARY KEY, created_at TIMESTAMPTZ DEFAULT now(),
                   run_id TEXT, user_id TEXT, agent TEXT, action TEXT, detail TEXT)""")


def cash_available(user_id: str) -> float:
    """Starting cash, minus what this user bought, plus what they sold."""
    bought, sold = run_sql(
        "SELECT COALESCE(SUM(notional) FILTER (WHERE side = 'buy'), 0), "
        "       COALESCE(SUM(notional) FILTER (WHERE side = 'sell'), 0) "
        "FROM ai.trades WHERE user_id = :u", u=user_id)[0]
    return STARTING_CASH_USD - bought + sold


def check_trade(user_id: str, ticker: str, side: str, qty: float, price: float) -> str | None:
    """Return a reason to refuse the trade, or None if it is fine."""
    if side.lower() not in ("buy", "sell") or qty <= 0:
        return "side must be 'buy' or 'sell' and qty must be above 0"
    if side.lower() == "buy" and price * qty > cash_available(user_id):
        return f"not enough cash (need {price * qty:,.0f}, have {cash_available(user_id):,.0f})"
    if side.lower() == "sell":
        held = run_sql("SELECT shares FROM ai.portfolio WHERE user_id = :u AND ticker = :t",
                       u=user_id, t=ticker.upper())
        if not held or held[0][0] < qty:
            return f"cannot sell {qty:g} {ticker.upper()}: only {held[0][0] if held else 0:g} held"
    return None


def execute_trade(ticker: str, side: str, qty: float, user_id: str) -> str:
    """Pretend to place the trade: checks it, then records it in ai.trades."""
    ensure_trade_tables()
    price = last_price(ticker)
    problem = check_trade(user_id, ticker, side, qty, price)
    if problem:
        return f"REFUSED: {problem}"
    run_sql("INSERT INTO ai.trades (user_id, ticker, side, qty, price, notional) "
            "VALUES (:u, :t, :s, :q, :p, :n)",
            u=user_id, t=ticker.upper(), s=side.lower(), q=qty, p=price, n=price * qty)
    return f"EXECUTED {side.upper()} {qty:g} {ticker.upper()} @ {price:.2f} (stub, saved in ai.trades)"


def who(run_context: RunContext) -> str:
    return run_context.user_id or "unknown"


@tool(requires_confirmation=True)
def propose_trade(run_context: RunContext, ticker: str, side: str, qty: float) -> str:
    """Propose a trade. The run pauses until the user confirms or rejects.

    Args:
        ticker: Ticker symbol, e.g. NVDA.
        side: "buy" or "sell".
        qty: Number of shares.
    """
    return execute_trade(ticker, side, qty, who(run_context))


@approval(type="required")
@tool(requires_confirmation=True)
def propose_large_trade(run_context: RunContext, ticker: str, side: str, qty: float) -> str:
    """Propose a LARGE trade (over $10K). An admin has to approve it.

    Args:
        ticker: Ticker symbol, e.g. NVDA.
        side: "buy" or "sell".
        qty: Number of shares.
    """
    return execute_trade(ticker, side, qty, who(run_context))


@approval(type="audit")
@tool(requires_confirmation=True)
def record_trade_note(ticker: str, note: str) -> str:
    """Save a compliance note about a ticker. The user confirms and an audit record is kept.

    Args:
        ticker: Ticker symbol.
        note: The note text.
    """
    ensure_trade_tables()
    run_sql("INSERT INTO ai.audit_log (action, detail) VALUES ('trade_note', :d)",
            d=f"{ticker.upper()}: {note}")
    return f"Noted {ticker.upper()}: {note}"


@tool(requires_user_input=True, user_input_fields=["risk_tolerance"])
def set_risk_preference(run_context: RunContext, risk_tolerance: str = "") -> str:
    """Ask the user for their risk tolerance, then save it (HITL tier: requires_user_input).

    Args:
        risk_tolerance: Filled in by the user when the run pauses (e.g. conservative / moderate / aggressive).
    """
    ensure_trade_tables()
    value = (risk_tolerance or "").strip() or "unspecified"
    run_sql(
        "INSERT INTO ai.audit_log (user_id, action, detail) VALUES (:u, 'risk_preference', :d)",
        u=who(run_context), d=value,
    )
    return f"Saved risk preference for {who(run_context)}: {value}"


def route_trade_tool(notional_usd: float) -> str:
    """Which tool a trade of this size must use."""
    return "propose_large_trade" if notional_usd > LARGE_TRADE_USD else "propose_trade"
