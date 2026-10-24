# Learnings (one bullet per phase)

- **Phase 1:** Prove concurrent tool calls with wall-clock overlap; streaming alone does not show parallelism.
- **Phase 2:** Always pass `user_id` on every run — memory without it silently mixes users.
- **Phase 3:** Hybrid search needs real keyword-bearing chunks; empty DuckDuckGo results are not a RAG failure.
- **Phase 4:** Prefer a callable `members=` factory over a static list when role changes the roster mid-session.
- **Phase 5:** Put early-stop (`stop=True`) before expensive loops; Router/Condition after research keeps risk optional.
- **Phase 6:** Agno media params (`images=` / `files=`) beat ad-hoc file paths when you want traces to show media.
- **Phase 7:** FastAPI ≥0.116 broke HITL `/continue` here — pin `<0.116` until Agno catches up.
- **Phase 8:** Background post-hooks only stay non-blocking under AgentOS, not under bare `agent.run()`.
- **Phase 9:** Set `scheduler_base_url` to the real serve port or due jobs POST into the void.
- **Phase 10:** Agent-as-judge failed `evidence-cited` / `actionable` on the deterministic reporter — fixed by always appending `## Sources` and `## Action` in `reporter()` (`app/workflows/morning_briefing.py`).
- **Phase 11:** Split `TRACE_DATABASE_URL` before enabling `tracing=True`, or AgentOS will keep writing spans to the primary DB.
