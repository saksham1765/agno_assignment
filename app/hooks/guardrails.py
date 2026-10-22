"""Phase 7 - our own guardrails (they extend Agno's BaseGuardrail).

1. TickerPermissionGuardrail  blocks tickers (or company names) the user may not trade.
                              The allow-list is read from session_state["permitted_tickers"].
2. StrongerInjectionGuardrail catches jailbreak phrases that Agno's built-in list misses,
                              including disguised ones such as "1gnore previous instructions".
"""

import re

from agno.exceptions import CheckTrigger, InputCheckError
from agno.guardrails import BaseGuardrail

# Company names people type instead of the ticker.
COMPANY_NAMES = {
    "NVIDIA": "NVDA", "APPLE": "AAPL", "MICROSOFT": "MSFT", "META": "META", "FACEBOOK": "META",
    "TESLA": "TSLA", "ADVANCED MICRO DEVICES": "AMD", "GOOGLE": "GOOGL", "ALPHABET": "GOOGL",
    "AMAZON": "AMZN", "NETFLIX": "NFLX", "EXXON": "XOM",
}
KNOWN_TICKERS = set(COMPANY_NAMES.values())


def tickers_mentioned(text: str) -> set:
    """Every known ticker named in the text, either as a symbol or as a company name."""
    upper = text.upper()
    found = {t for t in re.findall(r"\b[A-Z]{1,5}\b", upper) if t in KNOWN_TICKERS}
    found |= {ticker for name, ticker in COMPANY_NAMES.items() if re.search(rf"\b{name}\b", upper)}
    return found


class TickerPermissionGuardrail(BaseGuardrail):
    """Raises InputCheckError if the message names a ticker that is not on the allow-list.

    Agno gives a hook the arguments named in its signature, so asking for `run_context`
    lets us read session_state. If session_state has no list, `default_permitted` is used.
    """

    def __init__(self, default_permitted: list[str] | None = None):
        self.default_permitted = default_permitted or []

    def check(self, run_input, run_context=None) -> None:
        state = (run_context.session_state if run_context else None) or {}
        permitted = {t.upper() for t in state.get("permitted_tickers", self.default_permitted)}
        blocked = sorted(tickers_mentioned(run_input.input_content_string()) - permitted)
        if blocked:
            raise InputCheckError(
                f"You are not permitted to trade: {', '.join(blocked)}",
                additional_data={"blocked_tickers": blocked},
                check_trigger=CheckTrigger.INPUT_NOT_ALLOWED,
            )

    async def async_check(self, run_input, run_context=None) -> None:
        self.check(run_input, run_context)


# ---- jailbreak phrases ---------------------------------------------------------

EXTRA_INJECTION_PHRASES = [
    "ignore previous instructions", "ignore all previous", "ignore the above",
    "disregard all earlier", "disregard previous", "disregard your instructions",
    "forget your instructions", "forget previous instructions", "forget everything above",
    "override your instructions", "override the rules", "bypass your", "bypass the rules",
    "rules do not apply", "rules don t apply", "no longer bound by", "without any restrictions",
    "reveal your system prompt", "show me your system prompt", "developer mode",
    "pretend you are", "pretend the rules", "act as if you have no",
]
LOOKALIKES = str.maketrans({"0": "o", "1": "i", "3": "e", "4": "a", "5": "s", "7": "t", "@": "a", "$": "s"})


def simplify(text: str) -> str:
    """lower-case, swap look-alike characters (1gnore -> ignore), drop punctuation, squeeze spaces."""
    text = text.lower().translate(LOOKALIKES)
    return re.sub(r"\s+", " ", re.sub(r"[^a-z ]", " ", text)).strip()


class StrongerInjectionGuardrail(BaseGuardrail):
    """A wider net than Agno's PromptInjectionGuardrail (which stays in place too)."""

    def check(self, run_input) -> None:
        text = simplify(run_input.input_content_string())
        if any(simplify(phrase) in text for phrase in EXTRA_INJECTION_PHRASES):
            raise InputCheckError(
                "Potential jailbreaking or prompt injection detected.",
                check_trigger=CheckTrigger.PROMPT_INJECTION,
            )

    async def async_check(self, run_input) -> None:
        self.check(run_input)
