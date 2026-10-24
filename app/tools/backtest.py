"""Phase 9 - a deliberately slow backtest tool that cooperates with run cancellation.

Call it through the backtester agent with background=True so the HTTP response
returns a run_id in under a second; poll or cancel that run while this tool sleeps.
"""

from __future__ import annotations

import time

from agno.run import RunContext
from agno.run.cancel import raise_if_cancelled
from agno.tools import tool

# How long a full backtest sleeps, in chunks so cancel can land between them.
BACKTEST_SECONDS = 8.0
CHUNK_SECONDS = 0.4


@tool
def backtest(strategy: str, range: str, run_context: RunContext) -> str:
    """Run a long pretend backtest for `strategy` over `range` (e.g. '1y').

    Sleeps in short chunks and checks for cancellation each time so a
    POST .../cancel can stop the run and leave status CANCELLED in the DB.
    """
    strategy = (strategy or "").strip() or "unknown"
    range = (range or "").strip() or "1y"
    run_id = run_context.run_id
    elapsed = 0.0
    while elapsed < BACKTEST_SECONDS:
        raise_if_cancelled(run_id)
        time.sleep(CHUNK_SECONDS)
        elapsed += CHUNK_SECONDS
    raise_if_cancelled(run_id)
    # Stable pretend result so proofs do not need a market data key.
    return (
        f"Backtest complete for strategy={strategy!r} range={range!r}: "
        f"CAGR=12.4%, max_drawdown=-8.1%, trades=42 (simulated, {BACKTEST_SECONDS:.0f}s)."
    )


def cancel_run(base_url: str, agent_id: str, run_id: str, session_id: str) -> int:
    """Ask AgentOS to abort a background run. Returns the HTTP status code."""
    import httpx

    url = f"{base_url.rstrip('/')}/agents/{agent_id}/runs/{run_id}/cancel"
    response = httpx.post(url, params={"session_id": session_id}, timeout=30)
    return response.status_code
