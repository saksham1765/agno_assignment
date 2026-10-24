"""Run all four Phase 10 eval suites and write docs/eval_report.md.

    python -m evals.run_all
    make eval
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

from evals.accuracy.run import run_accuracy  # noqa: E402
from evals.judge.run import run_judge  # noqa: E402
from evals.performance.run import run_performance  # noqa: E402
from evals.reliability.run import run_reliability  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "docs" / "eval_report.md"


def main() -> int:
    print("=== Phase 10 evals ===")
    results = {}

    print("\n[accuracy]")
    results["accuracy"] = run_accuracy()

    print("\n[reliability]")
    results["reliability"] = run_reliability()

    print("\n[performance]")
    results["performance"] = run_performance()

    print("\n[judge]")
    results["judge"] = run_judge()

    all_passed = all(r.get("passed") for r in results.values())
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Eval report",
        "",
        f"Generated: {datetime.now(timezone.utc).isoformat()}",
        "",
        "## Suite scores",
        "",
        "| Suite | Passed | Notes |",
        "|---|---|---|",
    ]
    for name, r in results.items():
        note = json.dumps({k: v for k, v in r.items() if k not in ("output_excerpt",)}, default=str)[:180]
        lines.append(f"| {name} | {'yes' if r.get('passed') else 'NO'} | `{note}` |")

    lines += [
        "",
        "## Bug found by eval and fixed",
        "",
        "The **agent-as-judge** suite originally failed `evidence-cited` and `actionable` "
        "because the deterministic morning-briefing reporter ended after the Risk section "
        "with no Sources block and no Action line.",
        "",
        "**Fix:** `app/workflows/morning_briefing.py` `reporter()` now always appends "
        "`## Action` and `## Sources` (portfolio table, market stubs, risk threshold). "
        "See `docs/learnings.md` (Phase 10).",
        "",
        "## How to re-run",
        "",
        "```",
        "make eval",
        "# or: python -m evals.run_all",
        "```",
        "",
    ]
    REPORT.write_text("\n".join(lines), encoding="utf-8")
    print(f"\nWrote {REPORT}")
    print("ALL PASSED" if all_passed else "SOME FAILED")
    return 0 if all_passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
