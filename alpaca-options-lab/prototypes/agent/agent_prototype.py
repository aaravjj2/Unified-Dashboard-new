"""
LangGraph + MCP Agent prototype (minimal stub)
This file demonstrates how an agent could be wired to call the dashboard via MCP/Playwright.
If LangGraph is not installed it will fall back to a noop stub.
"""
try:
    from langgraph import Graph  # noqa - example
    LANGGRAPH_AVAILABLE = True
except Exception:
    LANGGRAPH_AVAILABLE = False


def analyze_symbol(symbol: str):
    if LANGGRAPH_AVAILABLE:
        # placeholder for real graph construction
        g = Graph()
        return f"langgraph-analyze:{symbol}"
    else:
        return f"stub-analyze:{symbol}"


if __name__ == '__main__':
    print('Agent prototype running — LANGGRAPH_AVAILABLE=', LANGGRAPH_AVAILABLE)
    print(analyze_symbol('AAPL'))
