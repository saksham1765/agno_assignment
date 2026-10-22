"""Phase 6 - the four media tools: PDF, audio, chart, screenshot."""

import io
import os
from pathlib import Path
from typing import Optional, Sequence

import matplotlib
import yfinance as yf
from agno.media import File, Image
from agno.tools.function import ToolResult
from groq import Groq

from app.knowledge.base import get_knowledge

matplotlib.use("Agg")                       # draw charts to memory, no window
import matplotlib.pyplot as plt  # noqa: E402

CHART_FOLDER = Path("data/media/charts")
WHISPER_MODEL = os.getenv("WHISPER_MODEL", "whisper-large-v3-turbo")
CHART_RANGES = ("5d", "1mo", "3mo", "6mo", "1y")


def ingest_filing_pdf(file_path: str, ticker: str, year: int,
                      files: Optional[Sequence[File]] = None) -> ToolResult:
    """Add a 10-K PDF to the knowledge base.

    Agno fills `files` with the PDF attached to the run (its "file media" parameter).
    If nothing was attached, the file_path is used instead.

    Args:
        file_path: Local path to the PDF.
        ticker: Ticker the filing belongs to, e.g. NVDA.
        year: Filing year, e.g. 2024.
    """
    attached = files[0] if files else None
    path = Path(attached.filepath if attached else file_path)
    where = "run `files` media param" if attached else "file_path fallback"
    if not path.is_file():
        return ToolResult(content=f"ERROR: file not found: {path}")

    get_knowledge().insert(
        name=f"{ticker.upper()}_10K_{year}_agent",
        path=str(path),
        metadata={"ticker": ticker.upper(), "year": int(year), "doc_type": "10-K",
                  "source": "ingest_filing_pdf"},
    )
    return ToolResult(
        content=f"Ingested {path.name} as the {ticker.upper()} {year} 10-K. [source: {where}]",
        files=[File(filepath=str(path), mime_type="application/pdf")],
    )


def transcribe_earnings_audio(file_path: str, ticker: str, year: int) -> str:
    """Turn an earnings-call audio clip into text (Groq Whisper) and save it to the knowledge base.

    Args:
        file_path: Local path to the audio file (wav, mp3 or m4a).
        ticker: Ticker the call belongs to.
        year: Year of the call.
    """
    path = Path(file_path)
    if not path.is_file():
        return f"ERROR: audio not found: {path}"
    answer = Groq(api_key=os.getenv("GROQ_API_KEY")).audio.transcriptions.create(
        file=(path.name, path.read_bytes()), model=WHISPER_MODEL, response_format="text")
    transcript = str(answer).strip()

    get_knowledge().insert(
        name=f"{ticker.upper()}_earnings_audio_{year}",
        text_content=transcript,
        metadata={"ticker": ticker.upper(), "year": int(year),
                  "doc_type": "earnings_audio_transcript", "source": "transcribe_earnings_audio"},
    )
    return f"Transcribed {path.name} and saved it to knowledge. Transcript: {transcript}"


def generate_price_chart(ticker: str, range: str = "6mo") -> ToolResult:
    """Draw a price chart. The picture goes back to the model as an image.

    Args:
        ticker: Ticker symbol, e.g. NVDA.
        range: One of 5d, 1mo, 3mo, 6mo, 1y.
    """
    period = range if range in CHART_RANGES else "6mo"
    prices = yf.Ticker(ticker.upper()).history(period=period)["Close"]
    if prices.empty:
        return ToolResult(content=f"No price data for {ticker}.")

    figure, axes = plt.subplots(figsize=(7, 3.5))
    axes.plot(prices.index, prices, color="#2563eb")           # a blue line
    axes.set_title(f"{ticker.upper()} close, {period}")
    axes.grid(alpha=0.3)
    buffer = io.BytesIO()
    figure.savefig(buffer, format="png", dpi=110, bbox_inches="tight")
    plt.close(figure)
    png = buffer.getvalue()

    CHART_FOLDER.mkdir(parents=True, exist_ok=True)
    (CHART_FOLDER / f"{ticker.upper()}_{period}.png").write_bytes(png)
    change = 100 * (prices.iloc[-1] - prices.iloc[0]) / prices.iloc[0]
    return ToolResult(
        content=f"{ticker.upper()} {period}: {prices.iloc[0]:.2f} -> {prices.iloc[-1]:.2f} "
                f"({change:+.1f}%). The chart is attached.",
        images=[Image(content=png, mime_type="image/png", format="png")],   # <- goes back to the model
    )


def describe_dashboard_screenshot(file_path: str, competitor: str) -> str:
    """Describe a competitor-dashboard screenshot with the model and save it to the knowledge base.

    Args:
        file_path: Local path to the screenshot (png or jpg).
        competitor: Competitor name.
    """
    from agno.agent import Agent

    from app.agents.model import pick_model

    path = Path(file_path)
    if not path.is_file():
        return f"ERROR: screenshot not found: {path}"
    describer = Agent(model=pick_model())
    answer = describer.run(
        "Describe this competitor dashboard: list every metric with its value and trend, "
        "and summarize the chart. Be factual and short.",
        images=[Image(filepath=str(path))])
    description = str(answer.content).strip()

    get_knowledge().insert(
        name=f"{competitor}_dashboard_screenshot",
        text_content=description,
        metadata={"ticker": competitor.upper(), "year": 2026,
                  "doc_type": "dashboard_description", "source": "describe_dashboard_screenshot"},
    )
    return f"Saved the description of {path.name} to knowledge:\n{description}"
