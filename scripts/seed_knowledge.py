"""Phase 3 - fill the knowledge base: 10-K PDFs, earnings-call transcripts, Markdown notes.

Run once:  python scripts/seed_knowledge.py
"""

import sys
import urllib.request
from pathlib import Path

from dotenv import load_dotenv
from pypdf import PdfReader, PdfWriter

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
load_dotenv(ROOT / ".env")

from app.knowledge.base import get_knowledge  # noqa: E402

DATA = ROOT / "data" / "knowledge"
MAX_PAGES = 40            # only the first pages (business + risk factors), so embedding stays fast

# Real 10-K filings: (ticker, year, name, download link)
FILINGS = [
    ("NVDA", 2024, "NVDA_10K_FY2024",
     "https://d18rn0p25nwr6d.cloudfront.net/CIK-0001045810/1cbe8fe7-e08a-46e3-8dcc-b429fc06c1a4.pdf"),
    ("AAPL", 2024, "AAPL_10K_FY2024",
     "https://s2.q4cdn.com/470004039/files/doc_earnings/2024/q4/filing/10-Q4-2024-As-Filed.pdf"),
    ("META", 2024, "META_10K_FY2024",
     "https://d18rn0p25nwr6d.cloudfront.net/CIK-0001326801/a8eb8302-b52c-4db5-964f-a2d796c05f4b.pdf"),
]

# Real earnings-call transcripts and our own notes: (file, name, metadata)
MARKDOWN = [
    ("transcripts/nvda_fy2025_q4_REAL_transcript.md", "NVDA_FY2025_Q4_Earnings_Transcript",
     {"ticker": "NVDA", "year": 2025, "doc_type": "earnings_transcript"}),
    ("transcripts/aapl_fy2024_q4_REAL_transcript.md", "AAPL_FY2024_Q4_Earnings_Transcript",
     {"ticker": "AAPL", "year": 2024, "doc_type": "earnings_transcript"}),
    ("notes/nvda_moat.md", "Note_NVDA_Platform_Moat",
     {"ticker": "NVDA", "year": 2024, "doc_type": "analyst_note"}),
    ("notes/aapl_services.md", "Note_AAPL_Services",
     {"ticker": "AAPL", "year": 2024, "doc_type": "analyst_note"}),
    ("notes/cross_filing_rag_hook.md", "Note_Cross_Filing_RAG_Hook",
     {"ticker": "MULTI", "year": 2024, "doc_type": "analyst_note"}),
]


def download_and_trim(link: str, name: str) -> Path:
    """Download the PDF (once) and keep only its first MAX_PAGES pages."""
    folder = DATA / "filings"
    folder.mkdir(parents=True, exist_ok=True)
    full, short = folder / f"full_{name}.pdf", folder / f"{name}.pdf"
    if not full.exists():
        request = urllib.request.Request(link, headers={"User-Agent": "ValuraAgnoBot/1.0"})
        full.write_bytes(urllib.request.urlopen(request, timeout=120).read())
    if not short.exists():
        reader, writer = PdfReader(str(full)), PdfWriter()
        for page in reader.pages[:MAX_PAGES]:
            writer.add_page(page)
        writer.write(short.open("wb"))
    return short


def main():
    kb = get_knowledge()
    count = 0

    for ticker, year, name, link in FILINGS:
        print("10-K:", name)
        path = download_and_trim(link, name)
        kb.insert(name=name, path=str(path), skip_if_exists=True,
                  metadata={"ticker": ticker, "year": year, "doc_type": "10-K"})
        count += 1

    for file, name, metadata in MARKDOWN:
        print("Markdown:", name)
        kb.insert(name=name, path=str(DATA / file), metadata=metadata, skip_if_exists=True)
        count += 1

    print(f"\nDone: {count} documents (the assignment needs at least 5)")
    assert count >= 5


if __name__ == "__main__":
    main()
