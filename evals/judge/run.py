"""Phase 10 — Agent-as-Judge: Reporter outputs vs evidence-cited / balanced / actionable."""

from __future__ import annotations

from typing import Any

from agno.eval.agent_as_judge import AgentAsJudgeEval

from app.agents.model import pick_model
from app.db import get_db
from app.workflows.run_phase5 import briefing

CRITERIA = {
    "evidence-cited": (
        "The briefing cites evidence: tickers, concrete numbers (shares or % moves), "
        "and a Sources (or equivalent) section. Vague prose without figures fails."
    ),
    "balanced": (
        "The briefing covers macro, portfolio, and watchlist (or clearly states what is missing). "
        "It should not be only hype or only fear."
    ),
    "actionable": (
        "The briefing ends with a clear risk takeaway or next step a PM could act on "
        "(even if the action is 'do nothing / no red flags')."
    ),
}


def run_judge(*, print_results: bool = True) -> dict[str, Any]:
    db = get_db()
    model = pick_model()
    output = briefing()
    print("  Sample reporter output (first 240 chars):", output[:240].replace("\n", " "))

    scores: dict[str, Any] = {}
    failures: list[str] = []
    for name, criteria in CRITERIA.items():
        evaluation = AgentAsJudgeEval(
            name=f"reporter_{name}",
            criteria=criteria,
            scoring_strategy="numeric",
            threshold=7,
            model=model,
            db=db,
            show_spinner=False,
            additional_guidelines=[
                "Score 1-10. Be strict about the named criterion only.",
            ],
        )
        result = evaluation.run(
            input="Produce the morning briefing for demo@valura.dev",
            output=output,
            print_results=print_results,
        )
        # Result shape varies; treat missing as fail.
        passed = True
        score = None
        if result is None:
            passed = False
        else:
            score = getattr(result, "score", None) or getattr(result, "avg_score", None)
            status = getattr(result, "eval_status", None) or getattr(result, "status", None)
            if status and str(status).upper() in ("FAILED", "FAIL"):
                passed = False
            if score is not None and float(score) < 7:
                passed = False
        scores[name] = {"score": score, "passed": passed}
        print(f"  [{name}] score={score} passed={passed}")
        if not passed:
            failures.append(name)

    return {
        "suite": "judge",
        "criteria": scores,
        "passed": not failures,
        "failures": failures,
        "output_excerpt": output[:400],
    }


if __name__ == "__main__":
    from dotenv import load_dotenv

    load_dotenv()
    out = run_judge()
    print(out)
    raise SystemExit(0 if out["passed"] else 1)
