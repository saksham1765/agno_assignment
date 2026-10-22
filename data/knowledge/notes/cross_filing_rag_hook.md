# How to test cross-filing RAG

Ask the agent a question that **requires both** NVDA and AAPL 2024 10-K content, for example:

> Compare what NVIDIA and Apple each disclose in their 2024 Form 10-K about international / geopolitical risk and supply-chain concentration. Cite each filing.

Without knowledge search the model may invent section text. With hybrid RAG it should pull chunks tagged `ticker=NVDA` and `ticker=AAPL` (and optionally `year=2024`).

Also verify metadata filters:

```python
knowledge.search("export controls", filters={"ticker": "NVDA", "year": 2024})
# should not return AAPL-only chunks
```
