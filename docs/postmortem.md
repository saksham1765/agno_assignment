# Postmortem — Valura on Agno

## What I would change in Agno

- Keep a stable HITL HTTP contract across FastAPI versions (`/continue` broke when optional form fields became `False`).
- Document `scheduler_base_url` next to every `serve(port=...)` example — wrong port fails silently until you inspect schedule runs.
- Team `reasoning=True` was removed; a first-class `reasoning_model=` on teams would replace the prompt workaround.

## What I would change in this build

- Replace deterministic Phase 5 stubs with real overnight news once API keys exist, and keep a `USE_FIXTURES=1` path for CI.
- Wire a real Slack bot + ngrok early so Phase 8/9 DM acceptance is proven, not only fake-signed events.
- Add Telegram as a third interface only after Slack is green (prereq list mentions it; Phase 8 matrix only requires two).

## What Agno made easy

- AgentOS packaging (agents + teams + workflows + AG-UI + Slack) behind one FastAPI app.
- Postgres-backed sessions, memories, traces, schedules, and evals without a custom ORM layer.
- HITL primitives (`requires_confirmation`, `@approval`, `requires_user_input`) that pause cleanly and resume over HTTP.

## What Agno made hard

- Background hooks and background runs behave differently under AgentOS vs direct `agent.run()` — easy to mis-test.
- Eval + judge suites need careful cost control (20 accuracy cases × LLM judge); we used a fact bank tool to keep student answers stable.
- Multi-DB tracing is not a single AgentOS kwarg — you must call `setup_tracing(db=trace_db)` yourself when `TRACE_DATABASE_URL` is set.
