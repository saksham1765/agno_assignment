"""Minimal AgentOS app for Phase 7 (background post-hook is only async under AgentOS).

Phase 8 will grow this into the full server (interfaces, tracing, webhooks).
Run:  .\\.venv\\Scripts\\python.exe -m uvicorn app.server7:app --port 8007

AUDIT_DELAY env var (seconds) makes the audit hook slow, for the timing proof.
"""

from __future__ import annotations

import os

from agno.os import AgentOS

import app.hooks.audit as audit
from app.agents.trader import build_trader
from app.db import get_db

audit.SLOW_AUDIT_SECONDS = float(os.getenv("AUDIT_DELAY", "0"))

trader = build_trader(["NVDA", "AAPL", "MSFT"])
agent_os = AgentOS(agents=[trader], db=get_db())
app = agent_os.get_app()
