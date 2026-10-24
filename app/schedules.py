"""Phase 9 - morning-briefing cron schedules (one per user, 06:00 in their timezone).

Registered at AgentOS startup via ScheduleManager. Rows live in ai.agno_schedules
so they survive a process restart. Slack DM delivery is optional (see maybe_post_slack_dm).
"""

from __future__ import annotations

import os
from dataclasses import dataclass

from agno.scheduler import ScheduleManager


@dataclass(frozen=True)
class BriefingUser:
    user_id: str
    timezone: str
    slack_user_id: str | None = None  # Slack member id (U...) when DM posting is wanted


def briefing_users() -> list[BriefingUser]:
    """Parse MORNING_BRIEFING_USERS=email:Timezone[:SlackU],email:... or use the demo user."""
    raw = os.getenv("MORNING_BRIEFING_USERS", "").strip()
    if not raw:
        return [BriefingUser("demo@valura.dev", os.getenv("MORNING_BRIEFING_TZ", "UTC"))]
    users: list[BriefingUser] = []
    for part in raw.split(","):
        bits = [b.strip() for b in part.strip().split(":") if b.strip()]
        if len(bits) < 2:
            continue
        users.append(BriefingUser(bits[0], bits[1], bits[2] if len(bits) > 2 else None))
    return users or [BriefingUser("demo@valura.dev", "UTC")]


def schedule_name(user_id: str) -> str:
    # Schedule names are unique per owner; keep them filesystem/URL-safe.
    safe = user_id.replace("@", "_at_").replace(".", "_")
    return f"morning_briefing_{safe}"


def briefing_cron() -> str:
    """Cron for the morning briefing. Default 06:00; override with MORNING_BRIEFING_CRON for tests."""
    return os.getenv("MORNING_BRIEFING_CRON", "0 6 * * *").strip() or "0 6 * * *"


def register_morning_briefing_schedules(db) -> list:
    """Idempotent: create-or-update a cron per user targeting the workflow endpoint."""
    manager = ScheduleManager(db=db)
    cron = briefing_cron()
    created = []
    for user in briefing_users():
        schedule = manager.create(
            name=schedule_name(user.user_id),
            cron=cron,
            timezone=user.timezone,
            endpoint="/workflows/morning_briefing/runs",
            method="POST",
            description=f"Morning briefing ({cron}) for {user.user_id} ({user.timezone})",
            payload={
                "message": "Run the morning briefing.",
                "session_id": f"scheduled-briefing-{user.user_id}",
            },
            user_id=user.user_id,
            if_exists="update",
            timeout_seconds=600,
            max_retries=1,
            provenance={
                "managed_by": "valura",
                "target_type": "workflow",
                "target_id": "morning_briefing",
            },
        )
        created.append(schedule)
    return created


def slack_user_for(user_id: str) -> str | None:
    for user in briefing_users():
        if user.user_id == user_id and user.slack_user_id:
            return user.slack_user_id
    return os.getenv("SLACK_BRIEFING_USER_ID")  # optional single-user override


def maybe_post_slack_dm(user_id: str, text: str) -> str:
    """Post `text` to the user's Slack DM when credentials exist; otherwise no-op.

    This is a Slack DM (not email). Opens a DM channel first, then posts.
    """
    token = os.getenv("SLACK_TOKEN", "").strip()
    slack_user = slack_user_for(user_id)
    if not token or not slack_user:
        return "skipped (set SLACK_TOKEN and a Slack user id on MORNING_BRIEFING_USERS)"
    if token.startswith("xoxb-dummy") or token == "xoxb-dummy":
        return "skipped (dummy Slack token)"
    try:
        import httpx

        headers = {"Authorization": f"Bearer {token}"}
        # Prefer opening a DM; if the bot lacks im:write, fall back to posting to the user id.
        channel = slack_user
        opened = httpx.post(
            "https://slack.com/api/conversations.open",
            headers=headers,
            json={"users": slack_user},
            timeout=20,
        ).json()
        if opened.get("ok"):
            channel = opened["channel"]["id"]
        response = httpx.post(
            "https://slack.com/api/chat.postMessage",
            headers=headers,
            json={"channel": channel, "text": text[:3500]},
            timeout=20,
        )
        body = response.json()
        if body.get("ok"):
            return f"posted to Slack DM {slack_user} (channel {channel})"
        err = body.get("error", response.text[:120])
        if err == "missing_scope":
            return (
                "Slack error: missing_scope — add Bot scope `im:write` "
                "(and reinstall the app), then try again"
            )
        return f"Slack error: {err}"
    except Exception as exc:  # noqa: BLE001 - never fail the briefing on Slack
        return f"Slack post failed: {exc}"
