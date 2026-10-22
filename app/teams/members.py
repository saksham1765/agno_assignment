"""The team members, chosen by the user's role (the "callable factory").

    admin  -> Sourcer, DataAnalyst, NewsAgent, RiskAgent, Reporter
    viewer -> Sourcer, DataAnalyst, NewsAgent, Reporter      (no RiskAgent)

Every call builds brand-new agents, so members never share state.
"""

from app.agents.data_analyst import build_data_analyst
from app.agents.news import build_news_agent
from app.agents.reporter import build_reporter
from app.agents.risk import build_risk_agent
from app.agents.sourcer import build_sourcer


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
