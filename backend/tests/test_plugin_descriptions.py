from __future__ import annotations

import pytest

from app.mcp.plugin_proxy import build_gateway_description
from app.mcp.plugin_config import AccessLevel


class FakeTool:
    def __init__(self, name, description="", input_schema=None):
        self.name = name
        self.description = description
        self.inputSchema = input_schema or {}


def test_build_description_no_tools():
    desc = build_gateway_description("test", AccessLevel.read_only, "Test plugin", [])
    assert "Available tools:" not in desc
    assert "[test plugin — read_only] Test plugin" == desc


def test_build_description_with_tools():
    tools = [
        FakeTool(
            "execute_query",
            "Execute SQL query",
            {
                "properties": {
                    "query": {"type": "string", "description": "The SQL query"}
                },
                "required": ["query"],
            },
        ),
        FakeTool("list_tables", "List all tables", {}),
    ]
    desc = build_gateway_description("mysql", AccessLevel.read_only, "MySQL Database", tools)

    assert "Available tools:" in desc
    assert "execute_query" in desc
    assert "query (string, required) - The SQL query" in desc
    assert "list_tables" in desc
    assert "Parameters: (none)" in desc


def test_build_description_optional_params():
    tools = [
        FakeTool(
            "search",
            "Search records",
            {
                "properties": {
                    "term": {"type": "string", "description": "Search term"},
                    "limit": {"type": "integer", "description": "Max results"},
                },
                "required": ["term"],
            },
        ),
    ]
    desc = build_gateway_description("db", AccessLevel.read_only, "DB", tools)

    assert "term (string, required) - Search term" in desc
    assert "limit (integer, optional) - Max results" in desc


def test_build_description_tool_without_description():
    tools = [
        FakeTool(
            "run",
            "",
            {
                "properties": {
                    "input": {"type": "string"}
                },
                "required": [],
            },
        ),
    ]
    desc = build_gateway_description("p", AccessLevel.read_write, "P", tools)

    assert "- run. Parameters:" in desc
    assert "input (string, optional)" in desc


def test_build_description_mixed_access_level():
    desc = build_gateway_description("db", AccessLevel.read_write, "DB Plugin", [])
    assert "[db plugin — read_write] DB Plugin" == desc
