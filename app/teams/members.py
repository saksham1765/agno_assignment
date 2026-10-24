"""The team members, chosen by the user's role (the "callable factory").

    admin  -> Sourcer, DataAnalyst, NewsAgent, RiskAgent, Reporter
    viewer -> Sourcer, DataAnalyst, NewsAgent, Reporter      (no RiskAgent)

`build_sourcing_desk()` is a nested Team (sub-team) used in the Phase 4 demo.
Every call builds brand-new agents, so members never share state.
"""

from agno.team import Team
from agno.team.mode import TeamMode

from app.agents.data_analyst import build_data_analyst
from app.agents.model import pick_model
from app.agents.news import build_news_agent
from app.agents.reporter import build_reporter
from app.agents.risk import build_risk_agent
from app.agents.sourcer import build_sourcer
from app.db import get_db


def build_sourcing_desk() -> Team:
    """Sub-team: Sourcer + NewsAgent under one desk (Phase 4 matrix: sub-teams)."""
    return Team(
        id="sourcing-desk",
        name="SourcingDesk",
        role="Web + news gathering desk (sub-team).",
        model=pick_model(),
        db=get_db(),
        mode=TeamMode.broadcast,
        members=[build_sourcer(), build_news_agent()],
        instructions=["Broadcast the ask to Sourcer and NewsAgent, then return both findings."],
        markdown=True,
    )


def members_for_role(role: str) -> list:
    members = [build_sourcer(), build_data_analyst(), build_news_agent(), build_reporter()]
    if role == "admin":
        members.insert(3, build_risk_agent())      # before the Reporter, who writes last
    return members


def pick_members(session_state: dict) -> list:
    """Passed to Team(members=...): Agno calls it on every run with the session_state."""
    role = (session_state or {}).get("role", "viewer")
    members = members_for_role(role)
    print(f"[factory] role={role!r} -> {[m.name for m in members]}")
    return members
