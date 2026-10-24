"""20 gold-standard research Q/A pairs (public historical outcomes)."""

# Each expected_output is what a correct brief answer must contain (judge is lenient on wording).
CASES: list[dict[str, str]] = [
    {
        "input": "In what year did NVIDIA IPO?",
        "expected_output": "1999",
    },
    {
        "input": "What is Apple's stock ticker symbol?",
        "expected_output": "AAPL",
    },
    {
        "input": "Who acquired LinkedIn in 2016?",
        "expected_output": "Microsoft",
    },
    {
        "input": "What company does ticker MSFT refer to?",
        "expected_output": "Microsoft",
    },
    {
        "input": "In which year did the COVID-19 stock market crash bottom (S&P 500 March low)?",
        "expected_output": "2020",
    },
    {
        "input": "What is Tesla's stock ticker?",
        "expected_output": "TSLA",
    },
    {
        "input": "Which company has the ticker AMZN?",
        "expected_output": "Amazon",
    },
    {
        "input": "Who founded Berkshire Hathaway's modern investment era (famous CEO)?",
        "expected_output": "Warren Buffett",
    },
    {
        "input": "What does the Fed funds rate decision body FOMC stand for?",
        "expected_output": "Federal Open Market Committee",
    },
    {
        "input": "In what year did Lehman Brothers file for bankruptcy?",
        "expected_output": "2008",
    },
    {
        "input": "What is Alphabet's Class A stock ticker?",
        "expected_output": "GOOGL",
    },
    {
        "input": "Which US exchange traditionally lists NYSE-style stocks under the NYSE brand?",
        "expected_output": "New York Stock Exchange",
    },
    {
        "input": "What is Meta Platforms' stock ticker (post-Facebook rename)?",
        "expected_output": "META",
    },
    {
        "input": "Which company ticker is NVDA?",
        "expected_output": "NVIDIA",
    },
    {
        "input": "What year did the Dot-com bubble peak roughly occur (NASDAQ peak year)?",
        "expected_output": "2000",
    },
    {
        "input": "Who is known as the CEO of Tesla as of the 2010s–2020s?",
        "expected_output": "Elon Musk",
    },
    {
        "input": "What is the ticker for JPMorgan Chase common stock?",
        "expected_output": "JPM",
    },
    {
        "input": "What does ETF stand for in markets?",
        "expected_output": "Exchange-Traded Fund",
    },
    {
        "input": "In what year did GameStop's famous short squeeze dominate headlines?",
        "expected_output": "2021",
    },
    {
        "input": "What is the S&P 500 — a stock, an index, or a bond?",
        "expected_output": "index",
    },
]
