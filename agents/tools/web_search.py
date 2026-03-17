"""Web search tool — thin wrapper over the tool registry.

The actual search execution is handled by Anthropic's built-in
``web_search_20250305`` tool.  The ``research_node`` is responsible
for calling the Anthropic API with this tool and processing the
response.

Legacy ``web_search()`` function and ``WEB_SEARCH_TOOL_DEFINITION``
are kept for backward compatibility with any code that still imports
them, but new code should use the registry directly.
"""

from __future__ import annotations

from agents.tools.registry import TOOL_REGISTRY, WriterTool, get_anthropic_tools

# Re-export registry helpers so callers can do:
#   from agents.tools.web_search import get_anthropic_tools
__all__ = [
    "TOOL_REGISTRY",
    "WriterTool",
    "get_anthropic_tools",
    "WEB_SEARCH_TOOL",
]

#: Convenience alias for the web_search registry entry.
WEB_SEARCH_TOOL: WriterTool = TOOL_REGISTRY["web_search"]
