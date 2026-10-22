"""Phase 4 demo: three team modes, role-based members, a reasoning log.

Run:  python -m app.teams.run_phase4
"""

from pathlib import Path
from uuid import uuid4

from agno.team import Team
from agno.team.mode import TeamMode
from dotenv import load_dotenv

load_dotenv()

from app.agents.model import pick_model  # noqa: E402
from app.agents.reporter import build_reporter  # noqa: E402
from app.agents.sourcer import build_sourcer  # noqa: E402
from app.teams import build_broadcast_team, build_coordinate_team, build_route_team  # noqa: E402
from app.teams.members import members_for_role  # noqa: E402
from app.tools.portfolio import ensure_portfolio_table  # noqa: E402

LOG = Path("logs/phase4_reasoning.log")
ALL_FIVE = {"Sourcer", "DataAnalyst", "NewsAgent", "RiskAgent", "Reporter"}


def run(team: Team, message: str, role: str, user: str):
    return team.run(message, user_id=user, session_id=f"p4-{uuid4().hex[:6]}",
                    session_state={"role": role})


def who_ran(response) -> set:
    return {m.agent_name for m in response.member_responses}


def check_members_depend_on_role():
    print("\n[1] The member factory gives admin a RiskAgent and viewer none")
    admin = [m.name for m in members_for_role("admin")]
    viewer = [m.name for m in members_for_role("viewer")]
    print("    admin: ", admin, "\n    viewer:", viewer)
    assert set(admin) == ALL_FIVE and set(viewer) == ALL_FIVE - {"RiskAgent"}
    assert members_for_role("admin")[0] is not members_for_role("admin")[0]   # new objects each time


def check_members_do_not_share_state():
    print("\n[2] A private value in the team's session_state must not reach the members")
    secret = "ZEBRA-7731"
    response = team_run_with_secret(secret)
    assert response.member_responses, "no member ran"
    for member in response.member_responses:
        prompt_text = " ".join(str(m.content) for m in member.messages)
        assert secret not in prompt_text, f"{member.agent_name} saw the team's private state"
    print(f"    [ok] {len(response.member_responses)} members never saw it")


def team_run_with_secret(secret: str):
    return build_coordinate_team().run(
        "Ask DataAnalyst for the NVDA price and NewsAgent for one NVDA headline. 40 words.",
        user_id="admin@valura.dev", session_id=f"p4-{uuid4().hex[:6]}",
        session_state={"role": "admin", "private_note": secret})


def check_coordinate_with_reasoning():
    print("\n[3] Coordinate team: reasoning shown and saved to a log")
    response = run(
        build_coordinate_team(),
        "Research NVDA. Ask DataAnalyst for the price, NewsAgent for one headline and RiskAgent "
        "for portfolio_concentration of admin@valura.dev. Start with ## Reasoning.",
        role="admin", user="admin@valura.dev")
    print(response.content)
    assert "## Reasoning" in str(response.content)

    LOG.parent.mkdir(exist_ok=True)
    trace = [f"{m.agent_name}: {m.content}" for m in response.member_responses]
    LOG.write_text(f"{response.content}\n\n--- member answers ---\n" + "\n\n".join(trace), encoding="utf-8")
    print(f"    [ok] reasoning log written to {LOG}")


def check_route_uses_one_member():
    print("\n[4] Route team: exactly one specialist answers")
    response = run(build_route_team(), "What is the current price of AAPL?",
                   role="viewer", user="viewer@valura.dev")
    print("    ran:", who_ran(response))
    assert len(who_ran(response)) == 1


def check_broadcast_uses_every_member():
    print("\n[5] Broadcast team: every member gets the task")
    response = run(build_broadcast_team(), "Risk-check the portfolio of admin@valura.dev in 3 bullets.",
                   role="admin", user="admin@valura.dev")
    print("    ran:", sorted(who_ran(response)))
    assert who_ran(response) == ALL_FIVE


def check_tasks_mode():
    print("\n[6] Tasks mode (the fourth TeamMode) also works")
    team = Team(name="TasksTeam", model=pick_model(), members=[build_sourcer(), build_reporter()],
                mode=TeamMode.tasks, max_iterations=3)
    response = team.run("In one sentence: what is Valura?")
    assert response.content


if __name__ == "__main__":
    print("=== Phase 4 - Research teams ===")
    ensure_portfolio_table()
    check_members_depend_on_role()
    check_members_do_not_share_state()
    check_coordinate_with_reasoning()
    check_route_uses_one_member()
    check_broadcast_uses_every_member()
    check_tasks_mode()
    print("\nPhase 4 checks passed")
