"""perf evlist — list events recorded in a perf.data file."""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from perf_mcp.executor import PerfExecutor
from perf_mcp.schema import PerfOption, register_perf_tool

EVLIST_OPTIONS = [
    PerfOption("input", "i", "string", "Path to perf.data file"),
    PerfOption("verbose", "v", "incr", "Verbosity level", default=0),
    PerfOption("force", "f", "boolean", "Don't complain, do it"),
    PerfOption("freq", "F", "boolean", "Show the sample frequency used for each event"),
    PerfOption("group", "g", "boolean", "Show event groups"),
    PerfOption("trace-fields", None, "boolean", "Show tracepoint fields"),
]


def register_tools(mcp: FastMCP, executor: PerfExecutor) -> None:
    register_perf_tool(
        mcp,
        executor,
        tool_name="perf_evlist",
        command=["evlist"],
        description=(
            "List events in a perf.data file. Always call this first to understand what was recorded before using other tools.\n"
            "\n"
            "Shows each event's name (e.g. 'cpu/cycles/'), type, config, and sampling settings. Use freq=true to see sample frequencies, group=true to see event grouping, verbose=1 for full perf_event_attr details.\n"
            "\n"
            "Output: one event per line (e.g. 'cpu/cycles/Pu').\n"
            "No prerequisites — works on any perf.data."
        ),
        options=EVLIST_OPTIONS,
    )
