# Eval report

Generated: 2026-10-23T15:00:14.575263+00:00

## Suite scores

| Suite | Passed | Notes |
|---|---|---|
| accuracy | yes | `{"suite": "accuracy", "n": 20, "avg_score": 9.9, "min_score": 9.0, "failed": [], "passed": true}` |
| reliability | yes | `{"suite": "reliability", "passed": true, "failures": []}` |
| performance | yes | `{"suite": "performance", "reporter_s": 1.1559120000019902, "risk_s": 1.1956848000045284, "passed": true, "failures": []}` |
| judge | yes | `{"suite": "judge", "criteria": {"evidence-cited": {"score": 9, "passed": true}, "balanced": {"score": 8, "passed": true}, "actionable": {"score": 9, "passed": true}}, "passed": tru` |

## Bug found by eval and fixed

The **agent-as-judge** suite originally failed `evidence-cited` and `actionable` because the deterministic morning-briefing reporter ended after the Risk section with no Sources block and no Action line.

**Fix:** `app/workflows/morning_briefing.py` `reporter()` now always appends `## Action` and `## Sources` (portfolio table, market stubs, risk threshold). See `docs/learnings.md` (Phase 10).

## How to re-run

```
make eval
# or: python -m evals.run_all
```
