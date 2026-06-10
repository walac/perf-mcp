"""perf diff -- compare two perf.data profiles.

Shows the difference in overhead between an old and new profile,
useful for before/after optimization comparisons. Supports delta,
absolute delta, ratio, and weighted diff computation modes.

Unlike other tools, this takes two input files as positional arguments
rather than a single --input flag.
"""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from perf_mcp.executor import PerfExecutor
from perf_mcp.schema import (
    enrich_tool_schema,
    build_params,
    PerfOption,
    format_result,
    options_to_cli_args,
)

DIFF_OPTIONS = [
    PerfOption("verbose", "v", "incr", "Verbosity level", default=0),
    PerfOption("force", "f", "boolean", "Don't complain, do it"),
    PerfOption("sort", "s", "string", "Sort by key(s)"),
    PerfOption("symbols", "S", "string", "Only consider these symbols"),
    PerfOption("dsos", "d", "string", "Only consider these DSOs"),
    PerfOption("comms", "c", "string", "Only consider these comms"),
    PerfOption("pid", None, "string", "Only consider these PIDs"),
    PerfOption("vmlinux", "k", "string", "vmlinux pathname"),
    PerfOption("modules", "m", "boolean", "Load module symbols"),
    PerfOption("cpu", "C", "string", "CPUs to filter"),
    PerfOption("time", None, "string", "Time span of interest"),
    PerfOption("period", None, "boolean", "Show period values instead of percent"),
    PerfOption("formula", None, "boolean", "Show formula for computed values"),
    PerfOption("compute", None, "string", "Comparison method"),
    PerfOption("percentage", None, "string", "How to display percentage"),
    PerfOption("order", "o", "string", "Specify compute sorting column (0-based index)"),
    PerfOption("stream", None, "boolean", "Enable hot stream comparison"),
    PerfOption("symfs", None, "string", "Symbol filesystem root"),
    PerfOption("baseline-only", "b", "boolean", "Show only items with match in baseline"),
    PerfOption("cycles-hist", None, "string", "Display cycle histogram"),
    PerfOption("dump-raw-trace", "D", "boolean", "Dump raw trace in ASCII"),
    PerfOption("field-separator", "t", "string", "Separator for columns"),
    PerfOption("kallsyms", None, "string", "kallsyms pathname"),
    PerfOption("quiet", "q", "boolean", "Do not show any warnings or messages"),
    PerfOption("tid", None, "string", "Only consider these TIDs"),
]


def register_tools(mcp: FastMCP, executor: PerfExecutor) -> None:
    @mcp.tool(
        description=(
            "Compare two perf.data profiles side by side. Shows per-symbol overhead changes between a baseline and a new measurement.\n"
            "\n"
            "Use this for before/after comparisons — optimization validation, regression detection, or A/B testing.\n"
            "\n"
            "Key parameters:\n"
            "- old_input: path to baseline perf.data (required).\n"
            "- new_input: path to comparison perf.data (required).\n"
            "- compute: comparison method — 'delta' (default, percentage-point difference), 'delta-abs' (absolute), 'ratio' (new/old), 'wdiff' (weighted), 'cycles' (cycle-level).\n"
            "- formula: true to show the computation formula.\n"
            "- symbols/dsos/comms: filter scope.\n"
            "- baseline_only: show only symbols present in baseline.\n"
            "\n"
            "Output: differential table with baseline%, new%, and delta columns.\n"
            "Both files must be from perf record with compatible events."
        ),
    )
    async def perf_diff(
        old_input: str,
        new_input: str,
        verbose: int = 0,
        force: bool = False,
        sort: str | None = None,
        symbols: str | None = None,
        dsos: str | None = None,
        comms: str | None = None,
        pid: str | None = None,
        vmlinux: str | None = None,
        modules: bool = False,
        cpu: str | None = None,
        time: str | None = None,
        period: bool = False,
        formula: bool = False,
        compute: str | None = None,
        percentage: str | None = None,
        order: str | None = None,
        stream: bool = False,
        symfs: str | None = None,
        baseline_only: bool = False,
        cycles_hist: str | None = None,
        dump_raw_trace: bool = False,
        field_separator: str | None = None,
        kallsyms: str | None = None,
        quiet: bool = False,
        tid: str | None = None,
    ) -> str:
        params = build_params(locals(), exclude={"old_input", "new_input"})

        cli_args = options_to_cli_args(DIFF_OPTIONS, params)
        old = executor.validate_input_path(old_input)
        new = executor.validate_input_path(new_input)
        args = ["diff"] + cli_args + [old, new]
        result = await executor.run(args)
        return format_result(result)

    enrich_tool_schema(mcp, "perf_diff", DIFF_OPTIONS)

    # Manually describe positional params not in DIFF_OPTIONS
    tool = mcp._tool_manager._tools.get("perf_diff")
    if tool:
        props = tool.parameters.get("properties", {})
        props.setdefault("old_input", {})["description"] = "Path to the baseline perf.data file"
        props.setdefault("new_input", {})["description"] = "Path to the comparison perf.data file"
