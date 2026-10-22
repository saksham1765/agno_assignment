"""Phase 6 - one conversation that uses all four media tools: PDF, audio, chart, screenshot.

Run:  python -m app.agents.multimodal      (run scripts/make_sample_media.py once first)
"""

from pathlib import Path
from uuid import uuid4

from agno.agent import Agent
from agno.media import File
from dotenv import load_dotenv
from pypdf import PdfReader, PdfWriter
from sqlalchemy import create_engine, text

from app.agents.model import pick_model
from app.db import get_db, get_db_url
from app.knowledge.base import get_knowledge
from app.tools.media import (describe_dashboard_screenshot, generate_price_chart,
                             ingest_filing_pdf, transcribe_earnings_audio)

load_dotenv()

MEDIA = Path("data/media")
FILING = Path("data/knowledge/filings/full_meta_10k_fy2024.pdf")   # a real 10-K
EXCERPT = MEDIA / "meta_10k_excerpt.pdf"                           # its first 6 pages

INSTRUCTIONS = [
    "You are Valura Research with four media tools. Call the tool the user names.",
    "After generate_price_chart returns, describe what you SEE in the attached image.",
    "Keep every answer under 80 words.",
]


def build_multimodal_agent() -> Agent:
    return Agent(
        name="MultimodalResearch",
        model=pick_model(),
        db=get_db(),
        knowledge=get_knowledge(),
        search_knowledge=True,
        tools=[ingest_filing_pdf, transcribe_earnings_audio,
               generate_price_chart, describe_dashboard_screenshot],
        instructions=INSTRUCTIONS,
        add_history_to_context=True,
        num_history_runs=4,
        markdown=True,
    )


def make_filing_excerpt() -> Path:
    """Cut the first 6 pages out of the real 10-K, so the demo stays small and fast."""
    if not EXCERPT.exists():
        reader, writer = PdfReader(str(FILING)), PdfWriter()
        for page in reader.pages[:6]:
            writer.add_page(page)
        writer.write(EXCERPT.open("wb"))
    return EXCERPT


def rows_saved_by(tool_name: str) -> int:
    query = text("SELECT COUNT(*) FROM ai.valura_knowledge WHERE meta_data->>'source' = :s")
    with create_engine(get_db_url()).connect() as conn:
        return conn.execute(query, {"s": tool_name}).scalar_one()


def tool_result(run, tool_name: str) -> str:
    return next((str(t.result) for t in run.tools if t.tool_name == tool_name), "")


def main():
    pdf = make_filing_excerpt()
    agent = build_multimodal_agent()
    session, user = f"phase6-{uuid4().hex[:6]}", "analyst@valura.dev"
    kb = get_knowledge()
    print("=== Phase 6 - multimodal tools, one conversation ===")

    def say(message: str, **media):
        print(f"\n> {message}")
        run = agent.run(message, session_id=session, user_id=user, **media)
        print(f"  {str(run.content)[:200]}")
        return run

    # 1. PDF -> the file travels through the run's `files` parameter
    run = say(f"Use ingest_filing_pdf with file_path={pdf}, ticker=META, year=2024.",
              files=[File(filepath=str(pdf), mime_type="application/pdf")])
    assert rows_saved_by("ingest_filing_pdf") > 0, "the filing was not stored"
    assert "source: run `files` media param" in tool_result(run, "ingest_filing_pdf"), \
        "the PDF did not arrive through the run's files= parameter"
    print("  [ok] 1. the filing is in the knowledge base")

    # 2. Audio -> transcript becomes searchable
    say(f"Use transcribe_earnings_audio on {MEDIA / 'earnings_clip.wav'} (ticker ACME, year 2026).")
    found = kb.search("Blackwell packaging HBM", filters={"doc_type": "earnings_audio_transcript"})
    assert any("Blackwell" in d.content for d in found), "transcript is not searchable"
    print("  [ok] 2. the transcript is searchable")

    # 3. Chart -> the image comes back to the model through ToolResult.images.
    #    The line colour is only visible in the picture, so a correct colour proves the model saw it.
    run = say("Use generate_price_chart for NVDA, range 3mo. Then tell me the colour of the price "
              "line in the image (the text result does not say).")
    assert "blue" in str(run.content).lower(), "the model did not see the chart image"
    print("  [ok] 3. the model saw the chart image")

    # 4. Screenshot -> described by the model, saved, and retrievable
    say(f"Use describe_dashboard_screenshot on {MEDIA / 'competitor_dashboard.png'} (competitor RIVALCO).")
    found = kb.search("monthly active users churn", filters={"doc_type": "dashboard_description"})
    assert any("4.2M" in d.content for d in found), "description is not retrievable"
    print("  [ok] 4. the screenshot description is retrievable")

    print("\nPhase 6 checks passed")


if __name__ == "__main__":
    main()
