"""Phase 8 proof against a REAL running AgentOS server (started here on port 8018).

Checks, in the order of the assignment's acceptance criteria:
  1. the server is up and lists the agents, teams and workflows
  2. a run makes a trace with tool inputs AND outputs in Postgres (agno_traces / agno_spans)
  3. the same user_id shares memory between two surfaces (AgentOS API and AG-UI)
  4. a Slack thread reuses one session (the Slack handler is called with a signed fake event)
  5. the custom webhook /webhooks/news starts a run
  6. a HITL trade can be paused and approved over HTTP

  python scripts/prove_phase8.py
"""

import hashlib
import hmac
import json
import os
import subprocess
import sys
import time
from uuid import uuid4

import httpx
from sqlalchemy import create_engine, text

from app.db import get_db_url

PORT = 8018
BASE = f"http://127.0.0.1:{PORT}"
SLACK_SECRET = "test-signing-secret"           # a dummy secret, only for this local proof
USER = f"phase8-{uuid4().hex[:6]}@valura.dev"
client = httpx.Client(timeout=180)


def sql(query: str, **params):
    with create_engine(get_db_url()).connect() as conn:
        return conn.execute(text(query), params).fetchall()


def start_server() -> subprocess.Popen:
    # SLACK_STREAMING=0: with a fake token Slack's streaming call fails before the agent runs.
    # Without streaming the agent runs first, so the thread -> session mapping can be tested.
    env = {**os.environ, "PYTHONUTF8": "1", "PYTHONPATH": ".", "SLACK_STREAMING": "0",
           "SLACK_TOKEN": "xoxb-dummy", "SLACK_SIGNING_SECRET": SLACK_SECRET}
    process = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "app.server:app", "--port", str(PORT)],
        env=env, stdout=open("server8.log", "w"), stderr=subprocess.STDOUT)
    for _ in range(90):
        try:
            if client.get(f"{BASE}/health", timeout=2).status_code == 200:
                return process
        except Exception:
            time.sleep(1)
    process.terminate()
    raise SystemExit("server did not start, see server8.log")


def ids(kind: str) -> list:
    return [item["id"] for item in client.get(f"{BASE}/{kind}").json()]


def check_1_components():
    print("\n[1] The server lists everything")
    agents, teams, workflows = ids("agents"), ids("teams"), ids("workflows")
    print("    agents:", agents, "\n    teams:", teams, "\n    workflows:", workflows)
    assert {"chat", "news-agent", "trader"} <= set(agents)
    assert len(teams) == 3 and len(workflows) == 1


def check_2_traces():
    print("\n[2] A run leaves a trace with tool inputs and outputs")
    session = f"p8-trace-{uuid4().hex[:6]}"
    response = client.post(f"{BASE}/agents/news-agent/runs", data={
        "message": "One NVDA headline, use get_yahoo_news.", "stream": "false",
        "session_id": session, "user_id": USER})
    assert response.status_code == 200, response.text[:200]
    run_id = response.json()["run_id"]
    # Traces are written in batches, so wait for the run's tool span to show up.
    # The trace row is the HTTP request (no session id); the run id lives on the agent span.
    tool_span = None
    for _ in range(20):
        rows = sql("SELECT s.attributes FROM ai.agno_spans s WHERE s.name = 'get_yahoo_news' AND s.trace_id IN "
                   "(SELECT trace_id FROM ai.agno_spans WHERE attributes->>'agno.run.id' = :r)", r=run_id)
        if rows:
            tool_span = rows[0][0]
            break
        time.sleep(1)
    assert tool_span, "the tool call is not in the trace of this run"
    print("    tool span keys:", sorted(k for k in tool_span if k.startswith(("input", "output", "tool.name"))))
    assert "NVDA" in tool_span["input.value"].upper(), "tool INPUT missing from the span"
    assert tool_span.get("output.value"), "tool OUTPUT missing from the span"
    print("    [ok] the span holds the tool's input and its output")


def stored_memories() -> list:
    return [row[0] for row in sql("SELECT memory FROM ai.agno_memories WHERE user_id = :u", u=USER)]


def agui_answer(question: str) -> str:
    """Ask over AG-UI and join the streamed text pieces back into one string."""
    payload = {"threadId": f"p8-agui-{uuid4().hex[:6]}", "runId": uuid4().hex, "state": {}, "tools": [],
               "context": [], "forwardedProps": {"user_id": USER},
               "messages": [{"id": uuid4().hex, "role": "user", "content": question}]}
    text_pieces = []
    for line in client.post(f"{BASE}/agui", json=payload).text.splitlines():
        if line.startswith("data: "):
            event = json.loads(line[6:])
            if event.get("type") == "TEXT_MESSAGE_CONTENT":
                text_pieces.append(event["delta"])
    return "".join(text_pieces)


def check_3_memory_across_surfaces():
    print("\n[3] The same user_id shares memory between two surfaces")
    secret = f"{uuid4().hex[:4]}-semiconductors"
    # Surface 1: the plain AgentOS API. The user states a fact.
    client.post(f"{BASE}/agents/chat/runs", data={
        "message": f"My favourite sector is {secret}. Please remember that.", "stream": "false",
        "session_id": f"p8-api-{uuid4().hex[:6]}", "user_id": USER})
    for _ in range(30):                                   # the memory is written a moment after the reply
        if any(secret in memory for memory in stored_memories()):
            break
        time.sleep(1)
    print("    memories saved for the user:", stored_memories())
    assert any(secret in memory for memory in stored_memories()), "the fact was not saved as a memory"

    # Surface 2: AG-UI, a different thread and session, but the same user_id.
    answer = agui_answer("What is my favourite sector? Repeat my exact words for it, including any prefix.")
    print("    AG-UI answer:", answer[:100])
    assert secret in answer, "memory did not follow the user to the AG-UI surface"
    print("    [ok] AG-UI knew what the user said through the API")


def slack_event(text_: str, thread_ts: str) -> tuple[bytes, dict]:
    body = json.dumps({"type": "event_callback", "event_id": f"Ev{uuid4().hex[:8]}", "event": {
        "type": "message", "channel_type": "im", "channel": "D0TEST", "user": "U0TEST",
        "text": text_, "ts": f"{time.time():.6f}", "thread_ts": thread_ts}}).encode()
    stamp = str(int(time.time()))
    signature = "v0=" + hmac.new(SLACK_SECRET.encode(), f"v0:{stamp}:".encode() + body, hashlib.sha256).hexdigest()
    return body, {"X-Slack-Request-Timestamp": stamp, "X-Slack-Signature": signature,
                  "Content-Type": "application/json"}


def check_4_slack_thread_session():
    print("\n[4] Slack: two messages in one thread use ONE session")
    thread = f"{time.time():.6f}"
    for message in ("What is NVDA's ticker sector?", "And what about AAPL?"):
        body, headers = slack_event(message, thread)
        reply = client.post(f"{BASE}/slack/events", content=body, headers=headers)
        print(f"    POST /slack/events -> {reply.status_code}")
        assert reply.status_code == 200
        time.sleep(6)
    rows = sql("SELECT DISTINCT session_id FROM ai.agno_runs WHERE session_id LIKE :p", p=f"%{thread}%")
    print("    sessions for that thread:", [r[0] for r in rows])
    assert len(rows) == 1, f"expected one session for the thread, found {len(rows)}"
    assert rows[0][0].endswith(f"D0TEST:{thread}"), "session id is not entity:channel:thread"
    runs = sql("SELECT COUNT(*) FROM ai.agno_runs WHERE session_id = :s", s=rows[0][0])[0][0]
    print(f"    runs in that session: {runs}")
    assert runs >= 2, "the second message did not reuse the first message's session"
    print("    [ok] one thread, one session, both messages in it")
    print("    (not tested: real Slack delivery and e-mail lookup, they need a real bot token)")


def check_5_webhook():
    print("\n[5] /webhooks/news starts a run")
    response = client.post(f"{BASE}/webhooks/news", json={"ticker": "NVDA"})
    print("    ", response.status_code, str(response.json())[:120])
    assert response.status_code == 200 and response.json()["run_id"]
    assert client.post(f"{BASE}/webhooks/news", json={"ticker": "NOT A TICKER!"}).status_code == 422
    print("    [ok] valid payload runs the agent, a bad ticker is refused")


def trade_count(user: str) -> int:
    return sql("SELECT COUNT(*) FROM ai.trades WHERE user_id = :u", u=user)[0][0]


def paused_trade(message: str, user: str) -> tuple:
    session = f"p8-hitl-{uuid4().hex[:6]}"
    body = client.post(f"{BASE}/agents/trader/runs", data={
        "message": message, "stream": "false", "session_id": session, "user_id": user}).json()
    assert body["status"] == "PAUSED", f"expected a paused run, got {body['status']}"
    return session, body


def answer_over_http(session: str, body: dict, user: str, yes: bool):
    tools = [{**tool, "confirmed": yes} for tool in body["tools"]]
    return client.post(f"{BASE}/agents/trader/runs/{body['run_id']}/continue", data={
        "tools": json.dumps(tools), "session_id": session, "stream": "false", "user_id": user})


def check_6_hitl_over_http():
    print("\n[6] Approve and reject a paused trade over HTTP (what the UI buttons call)")
    user = f"p8-hitl-{uuid4().hex[:5]}@valura.dev"

    start = trade_count(user)
    session, body = paused_trade("Buy 1 share of MSFT.", user)
    assert trade_count(user) == start, "trade ran before anyone confirmed"
    reply = answer_over_http(session, body, user, yes=True)
    assert reply.status_code == 200, reply.text[:200]
    assert trade_count(user) == start + 1, "confirmed trade was not executed"
    print("    [ok] user confirms over HTTP -> trade executed")

    session, body = paused_trade("Buy 1 share of AAPL.", user)
    assert answer_over_http(session, body, user, yes=False).status_code == 200
    assert trade_count(user) == start + 1, "rejected trade was executed"
    print("    [ok] user rejects over HTTP -> trade not executed")

    # The admin tier: the user alone cannot continue it; an admin resolves it in the database.
    from app.agents.admin import admin_approver_loop

    session, body = paused_trade("Buy 100 shares of NVDA. It is over $10,000, use propose_large_trade.", user)
    too_early = client.post(f"{BASE}/agents/trader/runs/{body['run_id']}/continue",
                            data={"tools": "", "session_id": session, "stream": "false", "user_id": user})
    print(f"    continue before the admin approved -> HTTP {too_early.status_code}: {too_early.text[:140]}")
    pending = sql("SELECT status FROM ai.agno_approvals WHERE run_id = :r", r=body["run_id"])
    print("    approval rows for the run:", [tuple(row) for row in pending])
    assert pending and pending[0][0] == "pending", "no pending admin approval was stored"
    assert too_early.status_code in (400, 403), "the user could continue a trade that needs an admin"
    assert trade_count(user) == start + 1, "the trade ran before the admin approved"
    admin_approver_loop(run_id=body["run_id"])
    approved = client.post(f"{BASE}/agents/trader/runs/{body['run_id']}/continue",
                           data={"tools": "", "session_id": session, "stream": "false", "user_id": user})
    assert approved.status_code == 200, approved.text[:200]
    assert trade_count(user) == start + 2, "admin-approved trade was not executed"
    print("    [ok] large trade: refused (HTTP 400, approval pending) until the admin approves, then executed")


def main():
    server = start_server()
    try:
        check_1_components()
        check_2_traces()
        check_3_memory_across_surfaces()
        check_4_slack_thread_session()
        check_5_webhook()
        check_6_hitl_over_http()
        print("\nPhase 8 checks passed")
    finally:
        server.terminate()


if __name__ == "__main__":
    main()
