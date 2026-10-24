"""Phase 4 — TeamMode.tasks research team (plan → execute tasks)."""

from agno.team import Team
from agno.team.mode import TeamMode

from app.agents.model import pick_model
from app.db import get_db
from app.teams.members import pick_members


def build_tasks_team() -> Team:
    return Team(
        id="research-tasks",
        name="ResearchTasks",
        mode=TeamMode.tasks,
        model=pick_model(),
        db=get_db(),
        members=pick_members,
        cache_callables=True,
        instructions=[
            "Break the user request into short research tasks, assign them, then synthesize.",
            "Prefer DataAnalyst for numbers, NewsAgent for headlines, RiskAgent when role=admin.",
        ],
        markdown=True,
    )
