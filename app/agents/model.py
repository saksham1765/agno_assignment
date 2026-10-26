"""Which LLM to use, and which web-search tool (shared by every agent)."""

import os

from agno.models.groq import Groq
from agno.models.openai import OpenAIChat

from app.tools.websearch import ResilientWebSearch


def has_llm_key() -> bool:
    return bool(os.getenv("LITELLM_API_KEY") or os.getenv("GROQ_API_KEY"))


def pick_model():
    """LiteLLM if its key is set (and USE_LITELLM is not 0), otherwise Groq.
    
    Set LITELLM_MODEL=smart (default). If smart is unavailable, swap
    LITELLM_MODEL=cheap in Railway Variables (no code change needed).
    """
    use_litellm = os.getenv("USE_LITELLM", "1").lower() not in ("0", "false", "no", "off")

    if os.getenv("LITELLM_API_KEY") and use_litellm:
        # The LiteLLM proxy speaks the OpenAI protocol, so Agno's OpenAIChat class talks to it.
        # No OpenAI account is involved: only the proxy's address and key are used.
        return OpenAIChat(
            id=os.getenv("LITELLM_MODEL", "smart"),
            api_key=os.getenv("LITELLM_API_KEY"),
            base_url=os.getenv("LITELLM_BASE_URL", "https://litellm-infra.valura.ai"),
        )
    if os.getenv("GROQ_API_KEY"):
        return Groq(id=os.getenv("GROQ_MODEL", "openai/gpt-oss-20b"))
    if os.getenv("GROQ_API_KEY"):
        return Groq(id=os.getenv("GROQ_MODEL", "openai/gpt-oss-20b"))

    raise SystemExit("No LLM key found. Set LITELLM_API_KEY or GROQ_API_KEY in .env "
                     "(USE_LITELLM=0 forces Groq).")


def web_search_toolkit():
    """DuckDuckGo search with fallback engines (see app/tools/websearch.py). No key needed."""
    return ResilientWebSearch()
