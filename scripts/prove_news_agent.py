"""NewsAgent must return real Yahoo Finance headlines (publisher + date), via its tool."""

from dotenv import load_dotenv

load_dotenv()
from app.agents.news import build_news_agent  # noqa: E402
from app.tools.yahoo_news import get_yahoo_news  # noqa: E402

r = build_news_agent().run("Give me 3 recent headlines about NVDA with publisher and date.", stream=False)
called = [t.tool_name for t in (r.tools or [])]
print("tools called:", called)
tool_out = next((str(t.result) for t in (r.tools or []) if t.tool_name == "get_yahoo_news"), "")
print("yahoo tool returned headlines:", tool_out.lstrip().startswith("["))
print("answer:", str(r.content)[:300].replace("\n", " "))
assert "get_yahoo_news" in called, "NewsAgent did not use the Yahoo Finance tool"
assert tool_out.lstrip().startswith("["), "Yahoo tool returned no headlines"
print("[ok] NewsAgent used Yahoo Finance and got real headlines")
