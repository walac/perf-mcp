"""perf timechart -- generate scheduling timechart SVG.

Produces an SVG visualization of CPU activity and task scheduling
over time. The output file path is validated against BLOCKED_PREFIXES.

Requires data from perf timechart record.
"""

from __future__ import annotations

import os

from mcp.server.fastmcp import FastMCP

from perf_mcp.executor import PerfExecutor
from perf_mcp.schema import (
    enrich_tool_schema,
    build_params,
    PerfOption,
    format_result,
    options_to_cli_args,
)

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
    @mcp.tool(
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
    )
    async def perf_timechart(
        input: str,
        output: str | None = None,
        verbose: int = 0,
        force: bool = False,
        width: int | None = None,
        power_only: bool = False,
        tasks_only: bool = False,
        process: str | None = None,
        io_skip_eagain: bool = False,
        io_min_time: int | None = None,
        io_merge_dist: int | None = None,
        highlight: str | None = None,
        topology: bool = False,
        callchain: bool = False,
        io_only: bool = False,
        proc_num: int | None = None,
        symfs: str | None = None,
    ) -> str:
        params = build_params(locals())
        if output is not None:
            params["output"] = executor.validate_output_path(output)
        cli_args = options_to_cli_args(TIMECHART_OPTIONS, params)
        args = ["timechart"] + cli_args
        result = await executor.run(args, input_path=input)
        out_path = params.get("output", "output.svg")
        if result.returncode == 0:
            try:
                size = os.path.getsize(out_path)
                return f"Timechart written to: {out_path} ({size} bytes)"
            except OSError:
                return format_result(result)
        return format_result(result)

    enrich_tool_schema(mcp, "perf_timechart", TIMECHART_OPTIONS)
