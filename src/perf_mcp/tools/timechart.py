"""perf timechart -- generate scheduling timechart SVG.

Produces an SVG visualization of CPU activity and task scheduling
over time. The output file path is validated against BLOCKED_PREFIXES.

Requires data from perf timechart record.
"""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from perf_mcp.executor import PerfExecutor
from perf_mcp.schema import PerfOption, register_perf_tool

TIMECHART_OPTIONS = [
    PerfOption("input", "i", "string", "Path to perf.data file"),
    PerfOption("output", "o", "string", "Output SVG file path (default: output.svg)"),
    PerfOption("verbose", "v", "incr", "Verbosity level", default=0),
    PerfOption("force", "f", "boolean", "Don't complain, do it"),
    PerfOption("width", "w", "integer", "SVG width in pixels"),
    PerfOption("power-only", "P", "boolean", "Only show CPU power events"),
    PerfOption("tasks-only", "T", "boolean", "Only show task events"),
    PerfOption("process", "p", "string", "Only show specific process(es)"),
    PerfOption("io-skip-eagain", None, "boolean", "Skip EAGAIN I/O events"),
    PerfOption("io-min-time", None, "integer", "Minimum I/O time to display (ns)"),
    PerfOption("io-merge-dist", None, "integer", "Merge I/O events within distance (ns)"),
    PerfOption("highlight", None, "string", "Highlight process by name"),
    PerfOption("topology", None, "boolean", "Show CPU topology"),
    PerfOption("callchain", "g", "boolean", "Record callchain"),
    PerfOption("io-only", "I", "boolean", "Show I/O-related events only"),
    PerfOption("proc-num", "n", "integer", "Number of processes to display"),
    PerfOption("symfs", None, "string", "Symbol filesystem root"),
]


def register_tools(mcp: FastMCP, executor: PerfExecutor) -> None:
    register_perf_tool(
        mcp,
        executor,
        tool_name="perf_timechart",
        command=["timechart"],
        description=(
            "Generate a timechart SVG showing CPU activity and task scheduling over time as a visual timeline.\n"
            "\n"
            "Key parameters:\n"
            "- output: SVG file path (default: output.svg).\n"
            "- process: filter to specific process name(s).\n"
            "- power_only: show only CPU power state changes.\n"
            "- tasks_only: show only task scheduling.\n"
            "- io_only: show only I/O activity.\n"
            "- topology: include CPU topology.\n"
            "- width: SVG width in pixels.\n"
            "\n"
            "Output: returns the SVG file path and size.\n"
            "Requires: perf timechart record."
        ),
        options=TIMECHART_OPTIONS,
        output_options=["output"],
        output_file_param="output",
        output_file_message="Timechart written to",
        default_output_file="output.svg",
    )
