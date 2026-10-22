"""Prove the audit post-hook does NOT block the user-facing response.

The audit hook sleeps 4s on every run (AUDIT_DELAY). We time the same simple question:
  - through a real uvicorn AgentOS server  -> hook runs in the BACKGROUND
  - through agent.run() directly           -> hook runs INLINE (Agno only backgrounds under AgentOS)
If the hook were blocking, the HTTP call would also take ~4s longer than a normal run.
(Starlette's in-process TestClient waits for background tasks, so a real server is needed.)
"""

import os
import subprocess
import sys
import time
from uuid import uuid4

import httpx

PORT, DELAY = 8017, 4.0
BASE = f"http://127.0.0.1:{PORT}"
env = {**os.environ, "AUDIT_DELAY": str(DELAY), "PYTHONUTF8": "1", "PYTHONPATH": "."}

server = subprocess.Popen([sys.executable, "-m", "uvicorn", "app.server7:app", "--port", str(PORT)],
                          env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
try:
    for _ in range(60):
        try:
            if httpx.get(f"{BASE}/health", timeout=2).status_code == 200:
                break
        except Exception:
            time.sleep(1)
    else:
        raise SystemExit("server did not start")

    times = []
    for i in range(2):  # 2 runs; the 1st includes warm-up
        t0 = time.perf_counter()
        r = httpx.post(f"{BASE}/agents/trader/runs", timeout=120,
                       data={"message": "Say hello in 3 words.", "stream": "false",
                             "session_id": f"bg-{uuid4().hex[:6]}"})
        times.append(time.perf_counter() - t0)
        assert r.status_code == 200, r.text[:200]
    http_t = min(times)
    print(f"HTTP via AgentOS, hook sleeps {DELAY:.0f}s: {times[0]:.1f}s, {times[1]:.1f}s")
finally:
    server.terminate()

# Same agent + same hook, called directly: the hook blocks.
import app.hooks.audit as audit  # noqa: E402

audit.SLOW_AUDIT_SECONDS = DELAY
from app.agents.trader import build_trader  # noqa: E402

agent = build_trader(["NVDA", "AAPL", "MSFT"])
t0 = time.perf_counter()
agent.run("Say hello in 3 words.", session_id=f"bg-{uuid4().hex[:6]}", stream=False)
direct_t = time.perf_counter() - t0
print(f"direct agent.run(), same hook:        {direct_t:.1f}s")

assert http_t < DELAY, f"HTTP response ({http_t:.1f}s) waited for the {DELAY:.0f}s hook"
assert direct_t >= DELAY, "direct run did not include the hook delay (hook not exercised?)"
print(f"[ok] response returned in {http_t:.1f}s although the hook takes {DELAY:.0f}s - it ran in the background")
