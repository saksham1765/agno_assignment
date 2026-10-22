"""Phase 7 - a fake 'admin' who approves or rejects pending approvals.

A real system would show the pending approvals in a UI. Here a small loop plays the admin:
it lists what is pending, applies a policy, and writes the decision to the database.
"""

import time
from typing import Callable

from app.db import get_db

ADMIN_ID = "admin@valura.dev"


def approve_everything(approval: dict) -> str:
    return "approved"


def admin_approver_loop(policy: Callable[[dict], str] = approve_everything, run_id: str | None = None) -> int:
    """Resolve every pending approval (only those of one run if run_id is given)."""
    db = get_db()
    pending, _ = db.get_approvals(status="pending", run_id=run_id)
    for approval in pending:
        db.update_approval(
            approval["id"],
            expected_status="pending",           # stops two admins resolving the same one
            status=policy(approval),             # "approved" or "rejected"
            resolved_by=ADMIN_ID,
            resolved_at=int(time.time()),
        )
    return len(pending)
