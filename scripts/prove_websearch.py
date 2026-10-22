"""Compare the old pinned-DuckDuckGo tool with the resilient tool, same queries."""

import json
import time

from dotenv import load_dotenv

load_dotenv()
from agno.tools.duckduckgo import DuckDuckGoTools  # noqa: E402

from app.tools.websearch import ResilientWebSearch  # noqa: E402

QUERIES = ["NVIDIA stock", "Apple earnings", "Tesla risks", "Microsoft AI spending", "AMD guidance",
           "Meta capex 2026", "Alphabet cloud growth", "Intel foundry"]


def got(tool, fn, q):
    try:
        out = getattr(tool, fn)(q, max_results=3)
    except Exception:
        return False
    return out.lstrip().startswith("[") and len(json.loads(out)) > 0


old, new = DuckDuckGoTools(timeout=15), ResilientWebSearch()
for fn in ("search_news", "web_search"):
    t0 = time.perf_counter()
    o = sum(got(old, fn, q) for q in QUERIES)
    t_old = time.perf_counter() - t0
    t0 = time.perf_counter()
    n = sum(got(new, fn, q) for q in QUERIES)
    t_new = time.perf_counter() - t0
    print(f"{fn:<12} old pinned-duckduckgo {o}/{len(QUERIES)} ({t_old:.0f}s)  |  resilient {n}/{len(QUERIES)} ({t_new:.0f}s)")
    assert n > o, f"{fn}: resilient tool is not better"
    assert n >= len(QUERIES) - 1, f"{fn}: resilient tool still unreliable ({n}/{len(QUERIES)})"

# Failure path: force every ddgs call to raise (a bogus backend name is NOT a failure,
# ddgs silently treats it as "auto"). The tool must return a message, not raise.
import app.tools.websearch as ws  # noqa: E402


class _Boom:
    def __init__(self, *a, **k): ...
    def __enter__(self): return self
    def __exit__(self, *a): return False
    def text(self, *a, **k): raise RuntimeError("network down")
    news = text


_real = ws.DDGS
ws.DDGS = _Boom
try:
    msg = ResilientWebSearch().web_search("anything")
finally:
    ws.DDGS = _real
print("all-fail path returns:", msg[:100])
assert msg.startswith("No text results") and "duckduckgo" in msg
print("[ok] resilient search is reliable and never raises")
