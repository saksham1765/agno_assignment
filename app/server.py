"""Phase 8 - one AgentOS server for everything built so far.

Run it:
    fastapi dev app/server.py        (or:  python -m app.server)
    open  http://localhost:8000/docs  and  https://os.agno.com  (connect to localhost:8000)

What is in it:
    agents     the Phase 1-7 agents (research, persistent, rag, multimodal, trader, news)
    teams      the three Phase 4 teams (coordinate, route, broadcast)
    workflows  the Phase 5 morning briefing
    tracing    every run is traced into Postgres (agno_traces / agno_spans)
    Slack      talks to the ROUTE team   (only added when SLACK_TOKEN is set)
    AG-UI      talks to the research agent (browser chat)
    /webhooks/news   a plain FastAPI route that runs the news agent
"""

import os

from agno.os import AgentOS
from agno.os.interfaces.agui import AGUI
from agno.os.interfaces.slack import Slack
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

load_dotenv()

from app.agents.data_analyst import build_data_analyst  # noqa: E402
from app.agents.multimodal import build_multimodal_agent  # noqa: E402
from app.agents.news import build_news_agent  # noqa: E402
from app.agents.persistent import build_persistent_research_agent  # noqa: E402
from app.agents.rag import build_rag_agent  # noqa: E402
from app.agents.trader import build_trader  # noqa: E402
from app.db import get_db  # noqa: E402
from app.teams import build_broadcast_team, build_coordinate_team, build_route_team  # noqa: E402
from app.workflows.morning_briefing import build_morning_briefing  # noqa: E402

db = get_db()

# ---- the pieces -------------------------------------------------------------------
# One agent answers in the browser AND in Slack. Both use the same database and ask Agno
# for memory, so a user who is "you@valura.dev" in both places shares one memory.
chat_agent = build_persistent_research_agent()
chat_agent.id = "chat"

news_agent = build_news_agent()
trader = build_trader(["NVDA", "AAPL", "MSFT"])
route_team = build_route_team()

agents = [chat_agent, news_agent, build_rag_agent(), build_multimodal_agent(), trader, build_data_analyst()]
teams = [build_coordinate_team(), route_team, build_broadcast_team()]
workflows = [build_morning_briefing()]

# ---- chat surfaces -------------------------------------------------------------------
interfaces = [AGUI(agent=chat_agent)]                    # browser chat: POST /agui

if os.getenv("SLACK_TOKEN") and os.getenv("SLACK_SIGNING_SECRET"):
    interfaces.append(Slack(
        team=route_team,                                  # Slack talks to the route team
        resolve_user_identity=True,                       # user_id = the person's e-mail, not "U01ABC"
        reply_to_mentions_only=True,                      # channels need @bot, DMs always answer
        streaming=os.getenv("SLACK_STREAMING", "1") != "0",   # live typing; "0" = one message at the end
    ))
else:
    print("[server] SLACK_TOKEN / SLACK_SIGNING_SECRET not set: Slack interface is OFF "
          "(AG-UI is on). See docs/slack_setup.md.")

# ---- AgentOS ---------------------------------------------------------------------------
agent_os = AgentOS(
    id="valura",
    name="Valura",
    description="Multi-agent market intelligence",
    agents=agents,
    teams=teams,
    workflows=workflows,
    interfaces=interfaces,
    db=db,
    tracing=True,                    # traces with tool inputs/outputs go to agno_traces / agno_spans
)
app = agent_os.get_app()


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
    agent_os.serve(app="app.server:app", host="localhost", port=8000, reload=False)
