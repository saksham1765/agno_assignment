# Valura

A small market-research app built step by step on Agno (Phases 1-7 of the assignment).

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

Use `python` as `.\.venv\Scripts\python.exe` if the venv is not active.

Ask your own question: `python scripts/ask.py "What should I know about NVDA?"` (`--phase 1|2|3`).

## Extra checks

```powershell
$env:PYTHONPATH="."
python -m pytest tests -q            # 29 quick tests (guardrails, routing, trade rules)
python scripts\audit_phases.py       # 64 checks: does the code match each assignment task?
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
app/tools/       trading, portfolio, media, insights, watchlist, yahoo_news, websearch
app/hooks/       guardrails.py (custom guardrail), audit.py (background audit hook)
app/knowledge/   the PgVector knowledge base
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
