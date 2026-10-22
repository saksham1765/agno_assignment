"""Phase 7 - the audit_log post-hook.

After every run it writes one row to ai.audit_log for each trade tool that was really
confirmed or approved. Rejected calls are not logged. Under AgentOS it runs in the
background (it does not delay the answer); with a plain agent.run() it runs inline.
"""

import time

from agno.hooks import hook

from app.tools.trading import ensure_trade_tables, run_sql

SLOW_AUDIT_SECONDS = 0.0        # tests set this to prove the hook does not block the response

TRADE_TOOLS = {"propose_trade", "propose_large_trade", "record_trade_note"}


def really_ran(tool) -> bool:
    """After continue_run, Agno clears `requires_confirmation` on every call, rejected or not.
    Only `confirmed` tells them apart."""
    if tool.tool_name in TRADE_TOOLS:
        return bool(tool.confirmed)
    return tool.result is not None


@hook(run_in_background=True)
def audit_run(run_output, agent) -> None:
    time.sleep(SLOW_AUDIT_SECONDS)
    ensure_trade_tables()
    for tool in run_output.tools or []:
        if really_ran(tool):
            run_sql("INSERT INTO ai.audit_log (run_id, user_id, agent, action, detail) "
                    "VALUES (:r, :u, :a, :x, :d)",
                    r=run_output.run_id, u=run_output.user_id or "unknown", a=agent.name,
                    x=tool.tool_name, d=f"args={tool.tool_args} result={str(tool.result)[:200]}")
