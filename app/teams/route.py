"""Route team: sends the user's message to exactly ONE specialist."""

from agno.team import Team
from agno.team.mode import TeamMode

from app.agents.model import pick_model
from app.db import get_db
from app.teams.members import pick_members


def build_route_team() -> Team:
    return Team(
        id="research-route",
        name="ResearchRouteTeam",
        model=pick_model(),
        members=pick_members,
        mode=TeamMode.route,
        determine_input_for_members=False,    # pass the user's text through unchanged
        db=get_db(),
        instructions=[
            "Send the message to exactly ONE specialist.",
            "Prices and portfolio: DataAnalyst. Headlines: NewsAgent. Web facts: Sourcer. "
            "Risk (admin only): RiskAgent. Writing: Reporter.",
            "Session role: {role}",
        ],
        session_state={"role": "viewer"},
        cache_callables=False,
        store_member_responses=True,
        markdown=True,
    )
