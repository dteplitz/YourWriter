"""Web search tool for writer agents.

This is a placeholder implementation that returns mock results.  It will be
replaced with a real web search integration (e.g., Tavily, SerpAPI, or an
MCP-based search tool) in a future iteration.
"""

from __future__ import annotations

from typing import Any


def web_search(query: str, num_results: int = 5) -> list[dict[str, str]]:
    """Search the web for information related to a query.

    Parameters
    ----------
    query:
        The search query string.
    num_results:
        Maximum number of results to return.

    Returns
    -------
    list[dict[str, str]]
        A list of result dicts with keys: title, url, snippet.
    """
    # Placeholder — returns mock data so the agent graph can run end-to-end
    # without a real search backend.
    return [
        {
            "title": f"Mock result for: {query}",
            "url": "https://example.com/mock",
            "snippet": (
                f"This is a placeholder search result for the query '{query}'. "
                "Replace this tool with a real search integration."
            ),
        }
    ][:num_results]


# LangChain-style tool metadata for future integration
WEB_SEARCH_TOOL_DEFINITION: dict[str, Any] = {
    "name": "web_search",
    "description": (
        "Search the web for information.  Use this when you need facts, "
        "references, or current information that you don't already know."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "The search query.",
            },
            "num_results": {
                "type": "integer",
                "description": "Maximum number of results (default 5).",
                "default": 5,
            },
        },
        "required": ["query"],
    },
}
