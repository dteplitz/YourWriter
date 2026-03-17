"""Tool registry for YourWriter writer agents.

Centralises all tool definitions so nodes can look up Anthropic API
tool specs and display metadata without needing to know implementation
details.

Adding a new tool:
1. Add a ``WriterTool`` entry to ``TOOL_REGISTRY``.
2. If it is a custom (non-built-in) tool, set ``executor`` to the
   callable that handles invocations.
3. Call ``get_anthropic_tools(["your_tool"])`` to build the API payload.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any


@dataclass
class WriterTool:
    """Descriptor for a single tool available to writer agents.

    Attributes
    ----------
    name:
        Canonical tool name — matches the Anthropic tool name.
    display_name:
        Short human-readable label used in SSE pill events
        (e.g. "Buscando" → shown while search is in progress).
    anthropic_type:
        The ``type`` string expected by the Anthropic Messages API for
        built-in tools (e.g. ``"web_search_20250305"``).  ``None`` for
        custom tools where we supply the full input schema ourselves.
    executor:
        Callable that runs the tool locally for custom tools.  Built-in
        tools are handled by Anthropic internally, so this is ``None``
        for those.
    """

    name: str
    display_name: str
    anthropic_type: str | None
    executor: Callable[..., Any] | None = field(default=None)


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------

TOOL_REGISTRY: dict[str, WriterTool] = {
    "web_search": WriterTool(
        name="web_search",
        display_name="Buscando",
        # NOTE: web_search_20250305 is a built-in Anthropic tool introduced
        # in March 2025.  If an older version of the anthropic SDK is
        # installed (< 0.49.0) this tool type will be rejected by the API.
        # The code assumes the installed SDK supports this tool; if you see
        # ``anthropic.BadRequestError`` mentioning "unknown tool type", you
        # need to upgrade: `pip install --upgrade anthropic`.
        anthropic_type="web_search_20250305",
        executor=None,  # built-in — Anthropic handles execution
    ),
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def get_anthropic_tools(tool_names: list[str]) -> list[dict[str, Any]]:
    """Build the tools list for the Anthropic Messages API.

    Only includes tools that have an ``anthropic_type`` (built-in tools).
    Custom tools with a local ``executor`` are not included here — they
    need to be handled separately via tool-use routing.

    Parameters
    ----------
    tool_names:
        Names of the tools to include, as they appear in ``TOOL_REGISTRY``.
        Unknown names are silently skipped.

    Returns
    -------
    list[dict]
        Ready-to-pass ``tools`` list for ``client.messages.create()``.

    Examples
    --------
    >>> get_anthropic_tools(["web_search"])
    [{'type': 'web_search_20250305', 'name': 'web_search'}]
    >>> get_anthropic_tools(["unknown_tool"])
    []
    """
    tools: list[dict[str, Any]] = []
    for name in tool_names:
        tool = TOOL_REGISTRY.get(name)
        if tool and tool.anthropic_type:
            tools.append({"type": tool.anthropic_type, "name": tool.name})
    return tools
