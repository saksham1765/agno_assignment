"""Phase 8+9 - one AgentOS server for everything built so far.

Run it:
    fastapi dev app/server.py        (or:  python -m app.server)
    open  http://localhost:8000/docs  and  https://os.agno.com  (connect to localhost:8000)

What is in it:
    agents     the Phase 1-7 agents + Phase 9 backtester
    teams      the three Phase 4 teams (coordinate, route, broadcast)
    workflows  the Phase 5 morning briefing
    tracing    every run is traced into Postgres (agno_traces / agno_spans)
    scheduler  06:00 morning-briefing cron per user (survives restart in agno_schedules)
    Slack      talks to the ROUTE team   (only added when SLACK_TOKEN is set)
    AG-UI      talks to the research agent (browser chat)
    /webhooks/news   a plain FastAPI route that runs the news agent
"""

import os
from contextlib import asynccontextmanager

from dotenv import load_dotenv

# Load .env before importing Agno Slack (its signing secret is read at import time).
load_dotenv()

from agno.os import AgentOS  # noqa: E402
from agno.os.interfaces.agui import AGUI  # noqa: E402
from agno.os.interfaces.slack import Slack  # noqa: E402
from agno.os.interfaces.slack import event_handler as _slack_eh  # noqa: E402
from agno.os.interfaces.slack import helpers as _slack_helpers  # noqa: E402
from fastapi import FastAPI, HTTPException  # noqa: E402
from pydantic import BaseModel  # noqa: E402

# Agno's Slack streaming uses chat.startStream(thread_ts=message.ts). That fails on
# top-level DMs (invalid_thread_ts), so error replies also vanish into a bad thread.
# For DMs without an existing thread: one session per DM, reply in the main chat.
_orig_extract_event_context = _slack_helpers.extract_event_context
_orig_resolve_session_id = _slack_helpers.resolve_session_id
_orig_send_slack_message_async = _slack_helpers.send_slack_message_async


def _extract_event_context(event: dict):
    ctx = _orig_extract_event_context(event)
    if event.get("channel_type") == "im" and not event.get("thread_ts"):
        ctx["thread_id"] = ""
    return ctx


async def _resolve_session_id(entity, entity_id: str, channel_id: str, thread_ts: str) -> str:
    if not thread_ts and str(channel_id).startswith("D"):
        return f"{entity_id}:{channel_id}:dm"
    return await _orig_resolve_session_id(entity, entity_id, channel_id, thread_ts)


async def _send_slack_message_async(async_client, channel: str, thread_ts: str, message: str, **kwargs):
    if not message or not str(message).strip():
        return
    if not thread_ts:
        # Omit thread_ts so the reply appears in the main DM timeline.
        delivery = _slack_helpers.slack_delivery_kwargs(
            kwargs.get("unfurl_links", True),
            kwargs.get("unfurl_media", True),
            kwargs.get("mrkdwn", True),
        )
        italics = kwargs.get("italics", False)
        text = message
        if italics:
            text = "\n".join([f"_{line}_" for line in message.split("\n")])
        await async_client.chat_postMessage(channel=channel, text=text, **delivery)
        return
    await _orig_send_slack_message_async(
        async_client, channel=channel, thread_ts=thread_ts, message=message, **kwargs
    )


_slack_helpers.extract_event_context = _extract_event_context
_slack_helpers.resolve_session_id = _resolve_session_id
_slack_helpers.send_slack_message_async = _send_slack_message_async
_slack_eh.extract_event_context = _extract_event_context
_slack_eh.resolve_session_id = _resolve_session_id
_slack_eh.send_slack_message_async = _send_slack_message_async

from app.agents.backtester import build_backtester  # noqa: E402
from app.agents.data_analyst import build_data_analyst  # noqa: E402
from app.agents.multimodal import build_multimodal_agent  # noqa: E402
from app.agents.news import build_news_agent  # noqa: E402
from app.agents.persistent import build_persistent_research_agent  # noqa: E402
from app.agents.rag import build_rag_agent  # noqa: E402
from app.agents.trader import build_trader  # noqa: E402
from app.db import get_db, get_trace_db, get_trace_db_url  # noqa: E402
from app.schedules import register_morning_briefing_schedules  # noqa: E402
from app.teams import (  # noqa: E402
    build_broadcast_team,
    build_coordinate_team,
    build_route_team,
    build_tasks_team,
)
from app.workflows.morning_briefing import build_morning_briefing  # noqa: E402

db = get_db()
trace_db = get_trace_db()

PORT = int(os.getenv("PORT", "8000"))
# Scheduler fires due jobs over HTTP against this URL. Must match the serve port.
SCHEDULER_BASE_URL = os.getenv("SCHEDULER_BASE_URL", f"http://127.0.0.1:{PORT}")
RUNTIME_ENV = os.getenv("RUNTIME_ENV", "dev").lower()
# Production: require JWTs (set JWT_VERIFICATION_KEY). Local/dev stays open.
USE_JWT = RUNTIME_ENV in ("prd", "prod", "production") or os.getenv("FORCE_JWT", "0") == "1"

# Phase 11: optional separate trace database (before AgentOS so spans do not hit primary).
if get_trace_db_url():
    from agno.tracing import setup_tracing

    setup_tracing(db=trace_db)
    print(f"[server] tracing -> TRACE_DATABASE_URL (separate from primary)")
    _tracing_flag = False  # already configured
else:
    _tracing_flag = True

# ---- the pieces -------------------------------------------------------------------
# One agent answers in the browser AND in Slack. Both use the same database and ask Agno
# for memory, so a user who is "you@valura.dev" in both places shares one memory.
chat_agent = build_persistent_research_agent()
chat_agent.id = "chat"

news_agent = build_news_agent()
trader = build_trader(["NVDA", "AAPL", "MSFT"])
backtester = build_backtester()
route_team = build_route_team()

agents = [
    chat_agent,
    news_agent,
    build_rag_agent(),
    build_multimodal_agent(),
    trader,
    build_data_analyst(),
    backtester,
]
teams = [build_coordinate_team(), route_team, build_broadcast_team(), build_tasks_team()]
workflows = [build_morning_briefing()]

# ---- chat surfaces -------------------------------------------------------------------
interfaces = [AGUI(agent=chat_agent)]                    # browser chat: POST /agui

if os.getenv("SLACK_TOKEN") and os.getenv("SLACK_SIGNING_SECRET"):
    interfaces.append(Slack(
        team=route_team,                                  # Slack talks to the route team
        token=os.getenv("SLACK_TOKEN"),
        signing_secret=os.getenv("SLACK_SIGNING_SECRET"),  # pass explicitly (do not rely on import-time env)
        resolve_user_identity=True,                       # user_id = the person's e-mail, not "U01ABC"
        reply_to_mentions_only=True,                      # channels need @bot, DMs always answer
        # Default OFF: chat.startStream breaks on top-level DMs (invalid_thread_ts).
        streaming=os.getenv("SLACK_STREAMING", "0") == "1",
    ))
else:
    print("[server] SLACK_TOKEN / SLACK_SIGNING_SECRET not set: Slack interface is OFF "
          "(AG-UI is on). See docs/slack_setup.md.")


@asynccontextmanager
async def lifespan(app, agent_os=None):
    """Register (or refresh) the 06:00 morning-briefing schedules on every start."""
    schedules = register_morning_briefing_schedules(db)
    print(f"[server] scheduler on; {len(schedules)} morning-briefing cron(s) "
          f"-> {SCHEDULER_BASE_URL}")
    for schedule in schedules:
        print(f"         - {schedule.name} cron={schedule.cron_expr} tz={schedule.timezone} "
              f"user={schedule.user_id}")
    yield


# ---- AgentOS ---------------------------------------------------------------------------
if USE_JWT and not os.getenv("JWT_VERIFICATION_KEY"):
    print("[server] RUNTIME_ENV=prd but JWT_VERIFICATION_KEY is missing — "
          "set the Control Plane public key (or FORCE_JWT=0 for local).")

agent_os = AgentOS(
    id="valura",
    name="Valura",
    description="Multi-agent market intelligence",
    agents=agents,
    teams=teams,
    workflows=workflows,
    interfaces=interfaces,
    db=db,
    tracing=_tracing_flag,           # True unless TRACE_DATABASE_URL already wired setup_tracing
    authorization=USE_JWT,           # Phase 11: JWT on every protected endpoint when prd
    scheduler=True,                  # Phase 9: poll agno_schedules and fire due jobs
    scheduler_poll_interval=int(os.getenv("SCHEDULER_POLL_INTERVAL", "15")),
    scheduler_base_url=SCHEDULER_BASE_URL,
    lifespan=lifespan,
)
app = agent_os.get_app()
print(f"[server] RUNTIME_ENV={RUNTIME_ENV} authorization={USE_JWT} tracing_separate={bool(get_trace_db_url())}")


# ---- custom route: /webhooks/news -----------------------------------------------------
class NewsPayload(BaseModel):
    ticker: str
    note: str = ""                   # optional: why the sender is calling


@app.post("/webhooks/news", tags=["Webhooks"])
async def news_webhook(payload: NewsPayload):
    """Another system posts {"ticker": "NVDA"} here; the NewsAgent writes a short news summary."""
    ticker = payload.ticker.strip().upper()
    if not ticker.isalpha() or len(ticker) > 5:
        raise HTTPException(status_code=422, detail="ticker must be 1-5 letters")
    run = await news_agent.arun(
        f"Give 3 recent headlines about {ticker}. {payload.note}".strip(),
        session_id=f"webhook-{ticker}",
        user_id="webhook",
    )
    return {"ticker": ticker, "run_id": run.run_id, "summary": str(run.content)}


if __name__ == "__main__":
    agent_os.serve(app="app.server:app", host="localhost", port=PORT, reload=False)
