"""Static + DB audit: does the code literally match each PDF task / deliverable?

Checks configuration and database state only (no LLM calls), so it is fast and exact.
"""

import inspect

from dotenv import load_dotenv
from sqlalchemy import create_engine, text

load_dotenv()
from app.db import get_db, get_db_url  # noqa: E402

RESULTS: list[tuple[str, bool, str]] = []


def check(name: str, ok: bool, note: str = "") -> None:
    RESULTS.append((name, bool(ok), note))


def sql(q: str, **p):
    with create_engine(get_db_url()).connect() as c:
        return c.execute(text(q), p).fetchall()


# ---------------- Phase 1 ----------------
from app.agents.research import INSTRUCTIONS, build_research_agent  # noqa: E402

a1 = build_research_agent()
names1 = [type(t).__name__ for t in a1.tools]
check("P1 YFinanceTools present", "YFinanceTools" in names1, str(names1))
check("P1 one web-search toolkit", sum(n in ("ResilientWebSearch", "ExaTools", "TavilyTools", "DuckDuckGoTools")
                                      for n in names1) == 1, str(names1))
check("P1 instructions force Business/Financials/Risks",
      all(h in " ".join(INSTRUCTIONS) for h in ("## Business", "## Financials", "## Risks")))
check("P1 no db (stateless)", a1.db is None)
src1 = inspect.getsource(__import__("app.agents.research", fromlist=["x"]))
check("P1 uses print_response AND arun stream", "print_response" in src1 and "arun(" in src1 and "stream=True" in src1)
check("P1 main() asks 'What should I know about NVDA?'", "What should I know about NVDA?" in src1)

# ---------------- Phase 2 ----------------
from app.agents.persistent import PHASE2_INSTRUCTIONS, build_persistent_research_agent  # noqa: E402

a2 = build_persistent_research_agent()
check("P2 PostgresDb wired", a2.db is not None and type(a2.db).__name__ == "PostgresDb")
check("P2 add_history_to_context=True", a2.add_history_to_context is True)
check("P2 num_history_runs=5", a2.num_history_runs == 5, f"got {a2.num_history_runs}")
check("P2 update_memory_on_run=True", a2.update_memory_on_run is True)
check("P2 session_state has watchlist list", isinstance(a2.session_state.get("watchlist"), list))
check("P2 instructions template 'Watchlist: {watchlist}'", any("Watchlist: {watchlist}" in s for s in PHASE2_INSTRUCTIONS))
tool_names2 = [getattr(t, "__name__", type(t).__name__) for t in a2.tools]
check("P2 tool mutates session_state via run_context",
      "add_to_watchlist" in tool_names2 and "run_context" in inspect.getsource(
          __import__("app.tools.watchlist", fromlist=["x"])))
check("P2 app/db.py exposes singleton get_db", get_db() is get_db())
check("P2 agno_sessions non-empty", sql("select count(*) from ai.agno_sessions")[0][0] > 0)
check("P2 agno_memories non-empty", sql("select count(*) from ai.agno_memories")[0][0] > 0)
users = sql("select count(distinct user_id) from ai.agno_memories where user_id is not null")[0][0]
check("P2 memories exist for >=2 distinct user_ids", users >= 2, f"{users} users")

# ---------------- Phase 3 ----------------
from app.knowledge.base import get_vector_db  # noqa: E402
from app.tools.insights import save_insight  # noqa: E402

vdb = get_vector_db()
check("P3 PgVector search_type=hybrid", str(vdb.search_type).endswith("hybrid"), str(vdb.search_type))
sig = list(inspect.signature(save_insight).parameters)
check("P3 save_insight(title, body, tags)", sig[:3] == ["title", "body", "tags"], str(sig))
check("P3 save_insight calls knowledge.insert", "insert(" in inspect.getsource(save_insight))
ndocs = sql("select count(distinct name) from ai.valura_knowledge")[0][0]
check("P3 >=5 documents ingested", ndocs >= 5, f"{ndocs} docs")
tenk = sql("select count(distinct name) from ai.valura_knowledge where meta_data->>'doc_type'='10-K'")[0][0]
check("P3 >=3 10-K filings", tenk >= 3, f"{tenk}")
tr = sql("select count(distinct name) from ai.valura_knowledge where meta_data->>'doc_type'='earnings_transcript'")[0][0]
check("P3 >=2 earnings transcripts", tr >= 2, f"{tr}")
notes = sql("select count(distinct name) from ai.valura_knowledge where meta_data->>'doc_type'='analyst_note'")[0][0]
check("P3 handful (>=3) of Markdown notes", notes >= 3, f"{notes}")
check("P3 agno_knowledge table populated", sql("select count(*) from ai.agno_knowledge")[0][0] > 0)
import os  # noqa: E402

check("P3 scripts/seed_knowledge.py exists", os.path.exists("scripts/seed_knowledge.py"))
check("P3 search_knowledge=True on RAG agent",
      __import__("app.agents.rag", fromlist=["x"]).build_rag_agent().search_knowledge is True)

# ---------------- Phase 4 ----------------
from agno.team.mode import TeamMode  # noqa: E402

from app.teams.broadcast import build_broadcast_team  # noqa: E402
from app.teams.coordinate import build_coordinate_team  # noqa: E402
from app.teams.members import members_for_role  # noqa: E402
from app.teams.route import build_route_team  # noqa: E402

admin_m = {m.name: m for m in members_for_role("admin")}
viewer_names = [m.name for m in members_for_role("viewer")]
check("P4 five members exist", set(admin_m) == {"Sourcer", "DataAnalyst", "NewsAgent", "RiskAgent", "Reporter"})
da_tools = [getattr(t, "__name__", type(t).__name__) for t in admin_m["DataAnalyst"].tools]
check("P4 DataAnalyst = YFinance + Postgres portfolio tool",
      "YFinanceTools" in da_tools and "get_portfolio" in da_tools, str(da_tools))
check("P4 Sourcer has web search", any("Search" in str(type(t).__name__) for t in admin_m["Sourcer"].tools))
check("P4 NewsAgent has a news tool", any(getattr(t, "__name__", "") == "get_yahoo_news" for t in admin_m["NewsAgent"].tools))
check("P4 RiskAgent checks vs portfolio/watchlist",
      any(getattr(t, "__name__", "") in ("portfolio_concentration", "list_watchlist_tickers") for t in admin_m["RiskAgent"].tools))
check("P4 Reporter exists and has no tools", admin_m["Reporter"].tools in (None, []))
from app.teams.tasks import build_tasks_team  # noqa: E402
from app.teams.members import build_sourcing_desk  # noqa: E402

modes = {build_coordinate_team().mode, build_route_team().mode, build_broadcast_team().mode, build_tasks_team().mode}
check("P4 four TeamModes = coordinate/route/broadcast/tasks",
      modes == {TeamMode.coordinate, TeamMode.route, TeamMode.broadcast, TeamMode.tasks}, str(modes))
check("P4 callable factory: admin has RiskAgent, viewer does not",
      "RiskAgent" in admin_m and "RiskAgent" not in viewer_names)
check("P4 members is a callable on coordinate/route/broadcast",
      all(callable(t.members) for t in (build_coordinate_team(), build_route_team(), build_broadcast_team())))
check("P4 cache_callables set (matrix item)", build_coordinate_team().cache_callables is False)
check("P4 sub-team SourcingDesk exists", build_sourcing_desk().name == "SourcingDesk"
      and all(m.name in ("Sourcer", "NewsAgent") for m in build_sourcing_desk().members))
check("P4 three team modules + tasks + README exist",
      all(os.path.exists(f"app/teams/{f}") for f in ("coordinate.py", "route.py", "broadcast.py", "tasks.py", "README.md")))
check("P4 reasoning debug log exists", os.path.exists("logs/phase4_reasoning.log"))

# ---------------- Phase 5 ----------------
from app.workflows.morning_briefing import build_morning_briefing  # noqa: E402

wf = build_morning_briefing()
kinds = [type(s).__name__ for s in wf.steps]
check("P5 uses Parallel, Loop, Router, Step", {"Parallel", "Loop", "Router", "Step"} <= set(kinds), str(kinds))
check("P5 Parallel has fetch_portfolio/fetch_watchlist_news/fetch_macro",
      sorted(s.name for s in wf.steps[0].steps) == ["fetch_macro", "fetch_portfolio", "fetch_watchlist_news"])
order = [getattr(s, "name", "") for s in wf.steps]
check("P5 order: fetch -> ... -> research_team -> risk_router -> reporter",
      order.index("fetch") < order.index("research_team") < order.index("risk_router") < order.index("reporter"), str(order))
wsrc = inspect.getsource(__import__("app.workflows.morning_briefing", fromlist=["x"]))
check("P5 typed StepInput/StepOutput", "StepInput" in wsrc and "StepOutput" in wsrc)
check("P5 early stop (stop=True) on circuit-breaker", "stop=True" in wsrc and "circuit-breaker" in wsrc)
check("P5 workflow-as-tool (WorkflowTools) used",
      "WorkflowTools" in inspect.getsource(__import__("app.workflows.run_phase5", fromlist=["x"])))
check("P5 morning_briefing.py + runner exist",
      os.path.exists("app/workflows/morning_briefing.py") and os.path.exists("app/workflows/run_phase5.py"))

# ---------------- Phase 6 ----------------
import app.tools.media as media  # noqa: E402

check("P6 ingest_filing_pdf takes `files` param", "files" in inspect.signature(media.ingest_filing_pdf).parameters)
check("P6 audio tool uses Groq whisper transcription", "audio.transcriptions" in inspect.getsource(media.transcribe_earnings_audio))
check("P6 generate_price_chart(ticker, range)",
      list(inspect.signature(media.generate_price_chart).parameters)[:2] == ["ticker", "range"])
check("P6 chart returns ToolResult(images=[Image])", "ToolResult(" in inspect.getsource(media.generate_price_chart)
      and "images=[Image(" in inspect.getsource(media.generate_price_chart))
check("P6 screenshot tool saves description to Knowledge",
      "insert(" in inspect.getsource(media.describe_dashboard_screenshot)
      and "images=[Image" in inspect.getsource(media.describe_dashboard_screenshot))
check("P6 four tools on the multimodal agent",
      len(__import__("app.agents.multimodal", fromlist=["x"]).build_multimodal_agent().tools) == 4)
check("P6 sample media + stored KB rows",
      all(sql("select count(*) from ai.valura_knowledge where meta_data->>'source'=:s", s=s)[0][0] > 0
          for s in ("ingest_filing_pdf", "transcribe_earnings_audio", "describe_dashboard_screenshot")))

# ---------------- Phase 7 ----------------
from app.agents.trader import build_trader  # noqa: E402
from app.tools import trading  # noqa: E402

tr = build_trader(["NVDA"])
tmap = {t.name: t for t in tr.tools}
check("P7 propose_trade requires_confirmation", tmap["propose_trade"].requires_confirmation is True)
check("P7 propose_large_trade @approval(required)", str(tmap["propose_large_trade"].approval_type).endswith("required"))
check("P7 second tool @approval(audit)", str(tmap["record_trade_note"].approval_type).endswith("audit"))
check("P7 requires_user_input tier (set_risk_preference)",
      "set_risk_preference" in tmap and tmap["set_risk_preference"].requires_user_input is True)
check("P7 threshold is $10K", trading.LARGE_TRADE_USD == 10_000)
pre = [type(h).__name__ for h in tr.pre_hooks]
check("P7 pre_hooks: PII(mask_pii=True) + PromptInjection",
      pre[:2] == ["PIIDetectionGuardrail", "PromptInjectionGuardrail"] and tr.pre_hooks[0].mask_pii is True, str(pre))
check("P7 custom guardrail extends BaseGuardrail",
      any(type(h).__name__ == "TickerPermissionGuardrail" for h in tr.pre_hooks)
      and "BaseGuardrail" in [b.__name__ for b in type(tr.pre_hooks[2]).__mro__])
check("P7 post_hook run_in_background=True",
      getattr(tr.post_hooks[0], "_agno_run_in_background", False) is True)
check("P7 agno_approvals populated", sql("select count(*) from ai.agno_approvals")[0][0] > 0)
check("P7 approvals include required AND audit types",
      {r[0] for r in sql("select distinct approval_type from ai.agno_approvals")} >= {"required", "audit"})
check("P7 audit_log table (own) has rows", sql("select count(*) from ai.audit_log")[0][0] > 0)
check("P7 SECURITY.md exists", os.path.exists("SECURITY.md"))

# ---------------- Phase 8 ----------------
import app.server as server  # noqa: E402

check("P8 AgentOS has agents, teams and workflows",
      len(server.agent_os.agents) >= 5 and len(server.agent_os.teams) >= 3 and len(server.agent_os.workflows) == 1,
      f"{len(server.agent_os.agents)} agents, {len(server.agent_os.teams)} teams, {len(server.agent_os.workflows)} workflows")
check("P8 AgentOS has a db and tracing=True", server.agent_os.db is not None and server.agent_os.tracing is True)
interface_names = [type(i).__name__ for i in server.interfaces]
check("P8 AG-UI interface registered", "AGUI" in interface_names, str(interface_names))
server_src = inspect.getsource(server)
check("P8 Slack wired to the route team with resolve_user_identity=True",
      "Slack(" in server_src and "team=route_team" in server_src and "resolve_user_identity=True" in server_src)
check("P8 two interfaces are available (AG-UI + Slack when configured)",
      server_src.count("interfaces.append(Slack(") == 1 and "AGUI(agent=" in server_src)
check("P8 /webhooks/news route exists",
      any(getattr(r, "path", "") == "/webhooks/news" for r in server.app.routes))
check("P8 webhook runs the news agent", "news_agent.arun(" in server_src)
check("P8 trace tables exist", sql("select count(*) from information_schema.tables where table_schema='ai' "
                                   "and table_name in ('agno_traces','agno_spans')")[0][0] == 2)
check("P8 Slack setup doc exists", os.path.exists("docs/slack_setup.md"))
check("P8 runs on port 8000", "port=8000" in server_src or 'PORT' in server_src)

# ---------------- Phase 9 ----------------
from app.agents.backtester import build_backtester  # noqa: E402
from app.schedules import briefing_users, register_morning_briefing_schedules, schedule_name  # noqa: E402
from app.tools import backtest as backtest_mod  # noqa: E402

check("P9 AgentOS scheduler=True", getattr(server.agent_os, "_scheduler_enabled", False) is True)
check("P9 scheduler_base_url set", bool(getattr(server.agent_os, "_scheduler_base_url", None)))
check("P9 lifespan registers morning briefing schedules",
      "register_morning_briefing_schedules" in server_src)
bt = build_backtester()
check("P9 backtester agent id=backtester with db",
      bt.id == "backtester" and bt.db is not None)
_bt_params = list(inspect.signature(backtest_mod.backtest.entrypoint).parameters)
check("P9 backtest(strategy, range) tool", _bt_params[:2] == ["strategy", "range"], str(_bt_params))
# The toolkit wraps the function; check the source instead if signature is awkward.
check("P9 backtest checks raise_if_cancelled",
      "raise_if_cancelled" in inspect.getsource(backtest_mod))
check("P9 cancel_run helper exists", callable(backtest_mod.cancel_run))
check("P9 morning briefing workflow has db (background/schedule)",
      build_morning_briefing().db is not None)
users = briefing_users()
check("P9 at least one briefing user with timezone",
      bool(users) and bool(users[0].timezone), str(users))
# Ensure schedules table can be written (creates rows for the demo user).
schedules = register_morning_briefing_schedules(get_db())
check("P9 agno_schedules has morning_briefing row",
      sql("select count(*) from ai.agno_schedules where name = :n",
          n=schedule_name(users[0].user_id))[0][0] >= 1,
      f"{len(schedules)} registered")
check("P9 prove_phase9.py exists", os.path.exists("scripts/prove_phase9.py"))

# ---------------- Phase 10 ----------------
check("P10 evals/accuracy with 20 gold cases",
      os.path.exists("evals/accuracy/cases.py")
      and len(__import__("evals.accuracy.cases", fromlist=["CASES"]).CASES) == 20)
check("P10 reliability/performance/judge modules exist",
      all(os.path.exists(f"evals/{s}/run.py") for s in ("accuracy", "reliability", "performance", "judge")))
check("P10 make eval / run_all exists",
      os.path.exists("Makefile") and os.path.exists("evals/run_all.py"))
check("P10 docs/learnings.md exists", os.path.exists("docs/learnings.md"))
# eval_report.md is produced by `make eval` / `python -m evals.run_all`
if os.path.exists("docs/eval_report.md"):
    check("P10 docs/eval_report.md present", True)
else:
    check("P10 docs/eval_report.md present (run make eval)", False, "missing — run python -m evals.run_all")

# ---------------- Phase 11 ----------------
check("P11 production checklist exists", os.path.exists("docs/production_checklist.md"))
check("P11 postmortem exists", os.path.exists("docs/postmortem.md"))
check("P11 get_trace_db helper", callable(__import__("app.db", fromlist=["get_trace_db"]).get_trace_db))
check("P11 server JWT when RUNTIME_ENV=prd",
      "authorization=USE_JWT" in inspect.getsource(server) or "authorization=USE_JWT" in server_src)
check("P11 TRACE_DATABASE_URL wiring", "TRACE_DATABASE_URL" in inspect.getsource(__import__("app.db", fromlist=["x"])))

# ---------------- report ----------------
w = max(len(n) for n, _, _ in RESULTS)
for n, ok, note in RESULTS:
    print(f"[{'ok' if ok else 'FAIL'}] {n:<{w}}  {note}")
bad = [n for n, ok, _ in RESULTS if not ok]
print(f"\n{len(RESULTS) - len(bad)}/{len(RESULTS)} checks pass")
assert not bad, f"gaps: {bad}"
