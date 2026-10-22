"""Coordinate team: the leader splits an open-ended question, delegates, then combines.

Agno's Team has no `reasoning=True` flag any more, so the leader is told to start with a
"## Reasoning" section, and the runner saves the whole trace to logs/phase4_reasoning.log.
"""

from agno.team import Team
from agno.team.mode import TeamMode

from app.agents.model import pick_model
from app.db import get_db
from app.teams.members import pick_members


def build_coordinate_team() -> Team:
    return Team(
        id="research-coordinate",
        name="ResearchCoordinateTeam",
        model=pick_model(),
        members=pick_members,                 # a function: members depend on the role
        mode=TeamMode.coordinate,
        db=get_db(),
        instructions=[
            "Split the question, delegate to the specialists, then write one clear answer.",
            "Start with a '## Reasoning' section: 3-6 bullets on who you will ask and why.",
            "DataAnalyst: numbers. NewsAgent: headlines. Sourcer: web. "
            "RiskAgent (admin only): concentration risk. Reporter: polish.",
            "Keep the answer after the reasoning under 150 words.",
            "Session role: {role}",
        ],
        session_state={"role": "viewer"},
        # Do NOT set add_session_state_to_context: Agno would copy the whole session_state
        # into every member's prompt. "{role}" above still works without it.
        cache_callables=False,                # build the members again on every run
        store_member_responses=True,
        markdown=True,
    )
