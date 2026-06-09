"""MCP server entry point for perf-mcp.

This module creates the FastMCP server instance, the shared PerfExecutor,
and auto-discovers tool modules from the ``perf_mcp.tools`` package.

Tool discovery works by scanning ``perf_mcp/tools/*.py`` for modules that
export a ``register_tools(mcp, executor)`` function. Each such module
registers one or more MCP tools via ``@mcp.tool()`` decorators.

The server runs on stdio transport (standard for Claude Code integration).
"""

from __future__ import annotations

import importlib
import pkgutil

from mcp.server.fastmcp import FastMCP

from perf_mcp.executor import PerfExecutor

# The FastMCP server instance. Tools are registered onto this via
# register_tools() calls from each tool module.
mcp = FastMCP(
    "perf-mcp",
    instructions=(
        "Linux perf analysis tools. Each tool wraps a perf subcommand that "
        "reads an existing perf.data file. Use perf_evlist first to inspect "
        "what events were recorded, then perf_report or perf_script for analysis."
    ),
)

# Shared executor instance. All tool modules use the same executor, which
# handles path validation, timeout, and output truncation.
executor = PerfExecutor()


def _register_all_tools() -> None:
    """Auto-discover and register all tool modules from perf_mcp.tools.

    Scans the ``perf_mcp.tools`` package for Python modules, imports each
    one, and calls its ``register_tools(mcp, executor)`` function if present.
    Modules without ``register_tools`` (like ``__init__.py``) are skipped.
    """
    package = importlib.import_module("perf_mcp.tools")
    for _, module_name, _ in pkgutil.iter_modules(package.__path__):
        module = importlib.import_module(f"perf_mcp.tools.{module_name}")
        if hasattr(module, "register_tools"):
            module.register_tools(mcp, executor)


def main() -> None:
    """Entry point: register tools and start the MCP stdio server."""
    _register_all_tools()
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
