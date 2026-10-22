"""Broadcast team: sends the SAME task to every member, then combines the answers."""

from agno.team import Team
from agno.team.mode import TeamMode

from app.agents.model import pick_model
from app.db import get_db
from app.teams.members import pick_members


def build_broadcast_team() -> Team:
    return Team(
        id="research-broadcast",
        name="ResearchBroadcastTeam",
        model=pick_model(),
        members=pick_members,
        mode=TeamMode.broadcast,
        db=get_db(),
        instructions=[
            "Every member gets the same task. Each uses their own speciality.",
            "Combine the answers and point out any RED_FLAG or news risk.",
            "Session role: {role}",
        ],
        session_state={"role": "admin"},
        cache_callables=False,
        store_member_responses=True,
        markdown=True,
    )
