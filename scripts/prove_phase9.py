"""Phase 9 proof against a REAL AgentOS server (started here on port 8019).

Checks the assignment's acceptance criteria that do not need a real Slack bot:
  1. a morning-briefing schedule is in agno_schedules (06:00, per-user timezone)
  2. that schedule is still there after a process restart
  3. a frequent proof schedule actually fires into agno_schedule_runs
  4. background backtest returns a run_id within 1 second, then polls to COMPLETED
  5. cancel_run stops a running backtest and persists CANCELLED

  python scripts/prove_phase9.py

Slack DM posting is skipped here (needs SLACK_TOKEN + a real Slack user id).
"""

from __future__ import annotations

import os
import subprocess
import sys
import time
from uuid import uuid4

import httpx
from sqlalchemy import create_engine, text

from app.db import get_db, get_db_url
from app.schedules import briefing_users, schedule_name
from app.tools.backtest import BACKTEST_SECONDS, cancel_run

PORT = 8019
BASE = f"http://127.0.0.1:{PORT}"
AGENT = "backtester"
client = httpx.Client(timeout=180)


def sql(query: str, **params):
    with create_engine(get_db_url()).connect() as conn:
        return conn.execute(text(query), params).fetchall()


def start_server() -> subprocess.Popen:
    env = {
        **os.environ,
        "PYTHONUTF8": "1",
        "PYTHONPATH": ".",
        "PORT": str(PORT),
        "SCHEDULER_BASE_URL": BASE,
        "SCHEDULER_POLL_INTERVAL": "5",
        # Keep Slack interface off for this proof (no real bot).
        "SLACK_TOKEN": "",
        "SLACK_SIGNING_SECRET": "",
    }
    process = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "app.server:app", "--port", str(PORT), "--host", "127.0.0.1"],
        env=env,
        stdout=open("server9.log", "w"),
        stderr=subprocess.STDOUT,
    )
    for _ in range(90):
        try:
            if client.get(f"{BASE}/health", timeout=2).status_code == 200:
                return process
        except Exception:
            time.sleep(1)
    process.terminate()
    raise SystemExit("server did not start, see server9.log")


def stop_server(process: subprocess.Popen) -> None:
    process.terminate()
    try:
        process.wait(timeout=15)
    except subprocess.TimeoutExpired:
        process.kill()


def schedule_rows(name: str | None = None):
    if name:
        return sql(
            "SELECT name, cron_expr, timezone, endpoint, enabled, user_id "
            "FROM ai.agno_schedules WHERE name = :n",
            n=name,
        )
    return sql(
        "SELECT name, cron_expr, timezone, endpoint, enabled, user_id FROM ai.agno_schedules"
    )


def check_1_schedule_registered():
    print("\n[1] Morning-briefing schedule is registered in agno_schedules")
    users = briefing_users()
    assert users, "no briefing users configured"
    for user in users:
        name = schedule_name(user.user_id)
        rows = schedule_rows(name)
        print(f"    {name}: {rows}")
        assert rows, f"schedule {name} missing"
        cron, tz, endpoint, enabled = rows[0][1], rows[0][2], rows[0][3], rows[0][4]
        assert cron == "0 6 * * *", cron
        assert tz == user.timezone, tz
        assert endpoint == "/workflows/morning_briefing/runs", endpoint
        assert enabled is True
    print("    [ok] 06:00 cron per user, pointing at the morning_briefing workflow")


def check_2_survives_restart(process: subprocess.Popen) -> subprocess.Popen:
    print("\n[2] Schedule re-loads after a process restart")
    before = {row[0]: row for row in schedule_rows()}
    assert before, "no schedules before restart"
    stop_server(process)
    time.sleep(1)
    process = start_server()
    after = {row[0]: row for row in schedule_rows()}
    for name in before:
        assert name in after, f"{name} vanished after restart"
    print(f"    [ok] {len(before)} schedule(s) still in agno_schedules after restart")
    return process


def check_3_schedule_fires():
    print("\n[3] A due schedule fires and lands in agno_schedule_runs")
    from agno.scheduler import ScheduleManager

    proof_name = f"phase9_proof_{uuid4().hex[:6]}"
    manager = ScheduleManager(db=get_db())
    # Every minute is the finest standard cron; poller is every 5s so we wait up to ~70s.
    proof = manager.create(
        name=proof_name,
        cron="* * * * *",
        timezone="UTC",
        endpoint="/workflows/morning_briefing/runs",
        payload={"message": "Phase 9 proof fire.", "session_id": f"p9-fire-{uuid4().hex[:6]}"},
        user_id="demo@valura.dev",
        if_exists="update",
        timeout_seconds=300,
    )
    print(f"    created proof schedule {proof_name} id={proof.id} (cron=* * * * *)")
    deadline = time.time() + 75
    runs = []
    while time.time() < deadline:
        runs = sql(
            "SELECT sr.status, sr.error FROM ai.agno_schedule_runs sr "
            "JOIN ai.agno_schedules s ON s.id = sr.schedule_id "
            "WHERE s.name = :n ORDER BY sr.created_at DESC LIMIT 3",
            n=proof_name,
        )
        if runs:
            break
        time.sleep(2)
    print("    schedule_runs:", runs)
    assert runs, "scheduler never wrote an agno_schedule_runs row"
    # Any row means the poller claimed and fired the job (status casing varies by version).
    status = str(runs[0][0]).upper()
    assert status in ("COMPLETED", "SUCCESS", "ERROR", "RUNNING", "PENDING", "TIMEOUT", "FAILED"), runs[0]
    # Prefer waiting for a terminal status so consecutive fires are observable, but don't fail on it.
    if status == "RUNNING":
        for _ in range(30):
            runs = sql(
                "SELECT sr.status, sr.error FROM ai.agno_schedule_runs sr "
                "JOIN ai.agno_schedules s ON s.id = sr.schedule_id "
                "WHERE s.name = :n ORDER BY sr.created_at DESC LIMIT 3",
                n=proof_name,
            )
            status = str(runs[0][0]).upper()
            if status != "RUNNING":
                break
            time.sleep(2)
        print("    schedule_runs (after wait):", runs)
    print(f"    [ok] schedule fired (status={status})")
    manager.delete(proof.id, user_id="demo@valura.dev")


def poll_run(run_id: str, session_id: str, timeout: float = 120.0) -> dict:
    terminal = {"COMPLETED", "CANCELLED", "ERROR", "FAILED"}
    deadline = time.time() + timeout
    last = None
    while time.time() < deadline:
        response = client.get(
            f"{BASE}/agents/{AGENT}/runs/{run_id}",
            params={"session_id": session_id},
        )
        response.raise_for_status()
        body = response.json()
        if body.get("status") != last:
            print(f"    status -> {body.get('status')}")
            last = body.get("status")
        if body.get("status") in terminal:
            return body
        time.sleep(0.4)
    raise TimeoutError(f"run {run_id} did not finish")


def check_4_background_backtest():
    print("\n[4] background=True returns a run_id within 1s, then polls to COMPLETED")
    session = f"p9-bt-{uuid4().hex[:6]}"
    started = time.perf_counter()
    response = client.post(
        f"{BASE}/agents/{AGENT}/runs",
        data={
            "message": "Backtest momentum over 1y. Call backtest(strategy='momentum', range='1y').",
            "background": "true",
            "stream": "false",
            "session_id": session,
            "user_id": "phase9@valura.dev",
        },
    )
    elapsed = time.perf_counter() - started
    print(f"    HTTP {response.status_code} in {elapsed:.3f}s: {response.text[:160]}")
    assert response.status_code == 202, response.text[:300]
    body = response.json()
    assert body.get("status") == "PENDING", body
    assert body.get("run_id") and body.get("session_id")
    assert elapsed < 1.0, f"acceptance took {elapsed:.3f}s (want < 1s)"
    print(f"    [ok] run_id={body['run_id']} accepted in {elapsed:.3f}s")

    final = poll_run(body["run_id"], body["session_id"], timeout=BACKTEST_SECONDS + 60)
    assert final["status"] == "COMPLETED", final
    content = str(final.get("content") or "")
    print("    content:", content[:140])
    assert "Backtest complete" in content or "momentum" in content.lower()
    print("    [ok] polled to COMPLETED")


def check_5_cancel_run():
    print("\n[5] cancel_run stops a backtest and persists CANCELLED")
    session = f"p9-cancel-{uuid4().hex[:6]}"
    response = client.post(
        f"{BASE}/agents/{AGENT}/runs",
        data={
            "message": "Backtest mean-reversion over 6m. Call backtest(strategy='mean-reversion', range='6m').",
            "background": "true",
            "stream": "false",
            "session_id": session,
            "user_id": "phase9@valura.dev",
        },
    )
    assert response.status_code == 202, response.text[:300]
    body = response.json()
    run_id, session_id = body["run_id"], body["session_id"]
    # Let the tool start sleeping so cancellation is mid-job, not pre-start.
    time.sleep(1.0)
    status = cancel_run(BASE, AGENT, run_id, session_id)
    print(f"    cancel_run -> HTTP {status}")
    assert status == 200, status

    final = poll_run(run_id, session_id, timeout=30)
    assert final["status"] == "CANCELLED", final
    # DB must also show cancelled (assignment: "persists a cancelled state").
    rows = sql(
        "SELECT status FROM ai.agno_runs WHERE run_id = :r",
        r=run_id,
    )
    print("    agno_runs status:", rows)
    assert rows and str(rows[0][0]).upper() in ("CANCELLED", "CANCELED"), rows
    print("    [ok] cancelled and persisted")


def main():
    process = start_server()
    try:
        check_1_schedule_registered()
        process = check_2_survives_restart(process)
        check_3_schedule_fires()
        check_4_background_backtest()
        check_5_cancel_run()
        print("\nPhase 9 checks passed")
        print("(Slack 06:00 DM delivery needs your bot token + Slack user id — see README)")
    finally:
        stop_server(process)


if __name__ == "__main__":
    main()
