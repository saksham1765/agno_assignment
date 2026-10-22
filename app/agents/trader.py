"""Phase 7 - the user-facing trading agent: human-in-the-loop tools, guardrails, audit hook."""

from agno.agent import Agent
from agno.guardrails import PIIDetectionGuardrail, PromptInjectionGuardrail

from app.agents.model import pick_model
from app.db import get_db
from app.hooks.audit import audit_run
from app.hooks.guardrails import StrongerInjectionGuardrail, TickerPermissionGuardrail
from app.tools.trading import ensure_trade_tables, propose_large_trade, propose_trade, record_trade_note

INSTRUCTIONS = [
    "You are Valura Trader. You never trade by yourself, you only PROPOSE trades.",
    "Trades up to $10,000: call propose_trade(ticker, side, qty).",
    "Trades above $10,000: call propose_large_trade(ticker, side, qty).",
    "Compliance notes: call record_trade_note(ticker, note).",
    "Call a tool once, then report its result in one sentence.",
]


def build_trader(permitted_tickers: list[str]) -> Agent:
    """No user_id here on purpose: each run() says who is asking, and trades are saved under that user."""
    ensure_trade_tables()
    return Agent(
        id="trader",
        name="Trader",
        model=pick_model(),
        db=get_db(),
        tools=[propose_trade, propose_large_trade, record_trade_note],
        instructions=INSTRUCTIONS,
        pre_hooks=[
            PIIDetectionGuardrail(mask_pii=True),            # hide SSNs, cards, emails, phones
            PromptInjectionGuardrail(),                      # reject known jailbreak phrases
            TickerPermissionGuardrail(permitted_tickers),    # custom: only allowed tickers
            StrongerInjectionGuardrail(),                    # custom: catches disguised jailbreaks
        ],
        post_hooks=[audit_run],                              # background audit_log write
        markdown=True,
    )
