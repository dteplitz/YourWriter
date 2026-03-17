"""Tests for agents.tools.registry."""

from __future__ import annotations

import pytest

from agents.tools.registry import TOOL_REGISTRY, WriterTool, get_anthropic_tools


# ---------------------------------------------------------------------------
# TOOL_REGISTRY contents
# ---------------------------------------------------------------------------


def test_registry_contains_web_search():
    assert "web_search" in TOOL_REGISTRY


def test_web_search_tool_has_correct_type():
    tool = TOOL_REGISTRY["web_search"]
    assert tool.anthropic_type == "web_search_20250305"


def test_web_search_tool_has_display_name():
    tool = TOOL_REGISTRY["web_search"]
    assert tool.display_name  # non-empty string


def test_web_search_tool_executor_is_none():
    """Built-in tools don't have a local executor."""
    tool = TOOL_REGISTRY["web_search"]
    assert tool.executor is None


# ---------------------------------------------------------------------------
# get_anthropic_tools
# ---------------------------------------------------------------------------


def test_get_anthropic_tools_returns_correct_structure():
    result = get_anthropic_tools(["web_search"])
    assert result == [{"type": "web_search_20250305", "name": "web_search"}]


def test_get_anthropic_tools_multiple_names():
    """When called with the same name twice, each occurrence is included."""
    result = get_anthropic_tools(["web_search", "web_search"])
    assert len(result) == 2


def test_get_anthropic_tools_unknown_name_skipped():
    result = get_anthropic_tools(["does_not_exist"])
    assert result == []


def test_get_anthropic_tools_empty_list():
    result = get_anthropic_tools([])
    assert result == []


def test_get_anthropic_tools_mixed_known_unknown():
    result = get_anthropic_tools(["web_search", "unknown_tool"])
    # Only the known tool is included
    assert len(result) == 1
    assert result[0]["name"] == "web_search"


def test_get_anthropic_tools_skips_tools_without_anthropic_type():
    """Tools with anthropic_type=None (custom tools) are excluded."""
    custom = WriterTool(
        name="custom_tool",
        display_name="Custom",
        anthropic_type=None,
        executor=lambda: None,
    )
    original = TOOL_REGISTRY.pop("custom_tool", None)
    TOOL_REGISTRY["custom_tool"] = custom
    try:
        result = get_anthropic_tools(["custom_tool"])
        assert result == []
    finally:
        del TOOL_REGISTRY["custom_tool"]
        if original is not None:
            TOOL_REGISTRY["custom_tool"] = original
