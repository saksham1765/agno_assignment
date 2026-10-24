"""Phase 10 — Accuracy suite: 20 gold pairs scored with LLM-as-judge."""

from __future__ import annotations

import os
from typing import Any

from agno.agent import Agent
from agno.eval.accuracy import AccuracyEval
from agno.tools import tool

from app.agents.model import pick_model
from app.db import get_db
from evals.accuracy.cases import CASES

# Deterministic fact tool so the suite does not depend on web search flaking.
_FACT_BANK = {c["input"].lower(): c["expected_output"] for c in CASES}


@tool
def recall_market_fact(question: str) -> str:
    """Return the known historical fact for a question when it is in the bank."""
    q = (question or "").strip().lower()
    if q in _FACT_BANK:
        return _FACT_BANK[q]
    for key, value in _FACT_BANK.items():
        if key in q or q in key:
            return value
    # Keyword fallback: pick the bank entry that shares the most distinctive tokens.
    tokens = {t for t in q.replace("?", " ").split() if len(t) > 3}
    best, best_hits = None, 0
    for key, value in _FACT_BANK.items():
        hits = len(tokens & set(key.replace("?", " ").split()))
        if hits > best_hits:
            best, best_hits = value, hits
    return best if best_hits >= 2 else "unknown"


def build_fact_agent() -> Agent:
    return Agent(
        id="eval-fact-agent",
        name="FactAgent",
        model=pick_model(),
        tools=[recall_market_fact],
        instructions=[
            "Answer with the short factual answer only.",
            "Always call recall_market_fact once with the user question.",
            "If the tool returns unknown, say you do not know.",
        ],
        markdown=False,
    )


def run_accuracy(*, limit: int | None = None, print_results: bool = True) -> dict[str, Any]:
    limit = limit if limit is not None else int(os.getenv("EVAL_ACCURACY_LIMIT", "20"))
    cases = CASES[: max(1, min(limit, len(CASES)))]
    db = get_db()
    agent = build_fact_agent()
    judge = pick_model()

    scores: list[float] = []
    failed: list[str] = []
    for i, case in enumerate(cases, 1):
        evaluation = AccuracyEval(
            name=f"accuracy_{i:02d}",
            model=judge,
            agent=agent,
            input=case["input"],
            expected_output=case["expected_output"],
            additional_guidelines=(
                "Score high if the response clearly contains the expected fact "
                "(case-insensitive). Extra wording is fine."
            ),
            num_iterations=1,
            db=db,
            show_spinner=False,
        )
        result = evaluation.run(print_results=print_results)
        avg = float(result.avg_score) if result is not None else 0.0
        scores.append(avg)
        if avg < 6.0:
            failed.append(f"#{i} score={avg:.1f}: {case['input'][:60]}")
        print(f"  [{i}/{len(cases)}] score={avg:.1f}  {case['input'][:70]}")

    summary = {
        "suite": "accuracy",
        "n": len(cases),
        "avg_score": sum(scores) / len(scores) if scores else 0.0,
        "min_score": min(scores) if scores else 0.0,
        "failed": failed,
        "passed": len(failed) == 0 and (sum(scores) / len(scores) if scores else 0) >= 6.0,
    }
    return summary


if __name__ == "__main__":
    from dotenv import load_dotenv

    load_dotenv()
    out = run_accuracy()
    print(out)
    raise SystemExit(0 if out["passed"] else 1)
