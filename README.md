# Valura

A small market-research app built step by step on Agno (Phases 1–11 of the assignment).

## Setup

```powershell
cd d:\Valura\agno\valura
uv venv --python 3.12
.\.venv\Scripts\Activate.ps1
uv pip install -e .
docker compose up -d db          # Postgres + pgvector on port 5532
$env:PYTHONUTF8=1
```

Put your keys in `.env` (copy `.env.example`): `LITELLM_API_KEY` (used first) and/or `GROQ_API_KEY` (fallback).
Set `USE_LITELLM=0` to force Groq. Web search is DuckDuckGo, market data is Yahoo Finance: no keys needed.

## Run each phase

Every command prints its checks and ends with `... checks passed`.

| Phase | What it shows | Command |
|---|---|---|
| 1 | One stateless agent, streaming, parallel tool calls (with timing) | `python -m app.agents.research` |
| 2 | Postgres sessions, memory per user, watchlist in session_state | `python -m app.agents.persistent` |
| 3 | Hybrid knowledge base, filters, the agent saves its own insights | `python scripts/seed_knowledge.py` (once), then `python -m app.agents.rag` |
| 4 | Five agents, three team modes, members chosen by role | `python -m app.teams.run_phase4` |
| 5 | Morning-briefing workflow (Parallel, Loop, Condition, early stop) | `python -m app.workflows.run_phase5` |
| 6 | PDF, audio, chart and screenshot tools in one chat | `python scripts/make_sample_media.py` (once), then `python -m app.agents.multimodal` |
| 7 | Human approval for trades, guardrails, audit log | `python -m app.agents.run_phase7` |
| 8 | AgentOS server: UI, traces, AG-UI chat, Slack, `/webhooks/news` | `python -m app.server`, then `python scripts/prove_phase8.py` |
| 9 | Scheduler (06:00 briefing), background backtest, cancel_run | `python -m app.server`, then `python scripts/prove_phase9.py` |
| 10 | Four eval suites → `docs/eval_report.md` | `make eval` or `python -m evals.run_all` |
| 11 | JWT / trace_db / Railway script / postmortem | see `docs/production_checklist.md`, `scripts/railway_up.sh` |

There is **no Phase 12** in the PDF (phases end at 11). Submission extras are `docs/learnings.md`, `docs/postmortem.md`, Loom, and a live Railway URL.

Use `python` as `.\.venv\Scripts\python.exe` if the venv is not active.

Ask your own question: `python scripts/ask.py "What should I know about NVDA?"` (`--phase 1|2|3`).

## Phase 8–9: the server

```powershell
python -m app.server        # http://localhost:8000   (docs at /docs)
```

- **AgentOS UI:** open https://os.agno.com, add a Local OS at `http://localhost:8000`, chat, and open Traces / Schedules.
- **Browser chat (AG-UI):** `POST /agui`. Memory is kept per `user_id`.
- **Slack:** off until `SLACK_TOKEN` and `SLACK_SIGNING_SECRET` are in `.env`. Steps are in `docs/slack_setup.md`.
- **Webhook:** `curl -X POST http://localhost:8000/webhooks/news -H "Content-Type: application/json" -d '{"ticker":"NVDA"}'`
- **Scheduler:** on startup registers a `0 6 * * *` cron per user (see `MORNING_BRIEFING_USERS`) that hits `/workflows/morning_briefing/runs`. Rows live in `ai.agno_schedules` and survive restart.
- **Background backtest:** `POST /agents/backtester/runs` with `background=true` returns a `run_id` immediately; poll `GET /agents/backtester/runs/{run_id}` or cancel with `POST .../cancel?session_id=...`.
- **Evals:** `make eval` runs accuracy / reliability / performance / agent-as-judge and writes `docs/eval_report.md`.
- **Prod:** `RUNTIME_ENV=prd` + `JWT_VERIFICATION_KEY` enables JWT; optional `TRACE_DATABASE_URL` (compose profile `traces` on port 5533). Deploy: `bash scripts/railway_up.sh`.

## Extra checks

```powershell
$env:PYTHONPATH="."
python -m pytest tests -q            # 33 quick tests (guardrails, routing, trade rules, server)
python scripts\audit_phases.py       # 74 checks: does the code match each assignment task?
python scripts\prove_phase8.py       # starts a real server and checks traces, memory, Slack session, webhook, approvals
python scripts\prove_phase9.py       # scheduler persistence, schedule fire, background backtest, cancel_run
python scripts\clean_test_data.py    # show test rows in the database (add --yes to delete them)
python scripts\prove_hybrid.py       # hybrid search vs vector-only vs keyword
python scripts\prove_websearch.py    # web search reliability
python scripts\prove_news_agent.py   # NewsAgent uses Yahoo Finance headlines
python scripts\prove_bg_hook.py      # the audit hook runs in the background (real server)
```

## Where things are

```
app/agents/      the agents and the phase demos (research, persistent, rag, multimodal, trader, run_phase7)
app/teams/       coordinate.py, route.py, broadcast.py, members.py (members by role), run_phase4.py
app/workflows/   morning_briefing.py, data.py, run_phase5.py
app/tools/       trading, portfolio, media, insights, watchlist, yahoo_news, websearch, backtest
app/hooks/       guardrails.py (custom guardrail), audit.py (background audit hook)
app/knowledge/   the PgVector knowledge base
app/schedules.py morning-briefing cron registration + optional Slack DM post
SECURITY.md      the three human-in-the-loop tiers
```

## Where this differs from the assignment PDF

| PDF says | This repo | Why |
|---|---|---|
| Exa or Tavily search | DuckDuckGo, then other engines if it returns nothing | No Exa/Tavily key. DuckDuckGo alone returned almost nothing here. |
| `reasoning=True` on the coordinate team | A "## Reasoning" section plus a log in `logs/` | Agno's Team no longer has that flag. |
| A news API | Yahoo Finance headlines + web search | No news-API key. |
| Real macro and news data (Phase 5) | Made-up but stable data, so runs repeat exactly | The phase asks for identical output on every run. |
| Real call audio and screenshot (Phase 6) | Computer-spoken clip and a drawn dashboard | No real files available. |
| Full 10-K PDFs | First 40 pages (seed), 6 pages (agent ingest) | Keeps local embedding fast. |
| OpenAI and Anthropic keys | LiteLLM proxy, Groq as fallback | Only these keys exist. |
| Background hook never blocks | True under AgentOS only (see `prove_bg_hook.py`); a plain `agent.run()` runs it inline | That is how Agno schedules background hooks. |
| `requires_user_input` HITL tier | Not used | The Phase 7 tasks only need confirmation and `@approval`. |
| Slack against a real bot, AgentOS UI at os.agno.com (Phase 8) | Code and docs are ready; only tested with a signed fake Slack event and a local server | Needs your Slack workspace and a browser. See `docs/slack_setup.md`. |
| Post morning briefing to Slack DM at 06:00 (Phase 9) | Cron + workflow + optional `chat.postMessage` are wired; DM is skipped without credentials | Set `SLACK_TOKEN` and `MORNING_BRIEFING_USERS=you@email:Your/Timezone:U…` |
| Deploy to Railway + Loom (Phase 11) | `scripts/railway_up.sh`, checklist, postmortem committed | Needs your Railway login, JWT public key, Slack Event URL, Loom recording |
| `fastapi dev` (Phase 8) | `python -m app.server` | Same server; the `fastapi` command also works. FastAPI is pinned to 0.115 because newer versions break Agno's approve/reject endpoint. |
