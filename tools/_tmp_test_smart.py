"""Quick test: does the 'smart' model respond via the actual agent path?"""
import os
from dotenv import load_dotenv
load_dotenv()

from app.agents.model import pick_model, web_search_toolkit
from agno.agent import Agent

model = pick_model()
print(f"Model: {model.id}")
print(f"Base URL: {model.base_url}")

agent = Agent(name="test", model=model, tools=[web_search_toolkit()])
print("Sending request to agent...")
for chunk in agent.run("Reply with just OK", stream=True):
    if chunk.content:
        print(f"Chunk: {chunk.content[:80]}")
        break

print("ALL GOOD — smart model works")
