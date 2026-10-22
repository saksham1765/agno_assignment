"""Ask Valura a question from the terminal.

  python scripts/ask.py "What should I know about NVDA?"
  python scripts/ask.py --phase 1 "What should I know about AAPL?"      stateless agent
  python scripts/ask.py --phase 2 "Add TSLA to my watchlist"            remembers you
  python scripts/ask.py --phase 3 "What did NVDA say about export controls?"   (default) uses the knowledge base
"""

import argparse
import sys
from pathlib import Path
from uuid import uuid4

from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
load_dotenv()

from app.agents.model import has_llm_key  # noqa: E402

parser = argparse.ArgumentParser()
parser.add_argument("question", nargs="?", default="What should I know about NVDA?")
parser.add_argument("--phase", type=int, choices=(1, 2, 3), default=3)
args = parser.parse_args()

if not has_llm_key():
    raise SystemExit("Set LITELLM_API_KEY or GROQ_API_KEY in .env first.")

user, session = "you@valura.dev", f"ask-{uuid4().hex[:6]}"

if args.phase == 1:
    from app.agents.research import build_research_agent
    build_research_agent().print_response(args.question, stream=True)
elif args.phase == 2:
    from app.agents.persistent import build_persistent_research_agent
    build_persistent_research_agent().print_response(args.question, user_id=user, session_id=session, stream=True)
else:
    from app.agents.rag import build_rag_agent
    build_rag_agent().print_response(args.question, user_id=user, session_id=session, stream=True)
