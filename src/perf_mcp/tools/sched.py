"""perf sched -- scheduler latency and timeline analysis.

Provides 5 MCP tools for different views of scheduler data:
- perf_sched_latency: Per-task scheduling latency statistics.
- perf_sched_timehist: Timestamped context-switch timeline.
- perf_sched_map: ASCII CPU activity visualization.
- perf_sched_script: Raw scheduler event dump.
- perf_sched_replay: Replay scheduling for simulation.

All require data from perf sched record or equivalent tracepoints.
Options are split across COMMON_SCHED_OPTIONS (shared), LATENCY_OPTIONS,
TIMEHIST_OPTIONS, and MAP_OPTIONS.
"""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from perf_mcp.executor import PerfExecutor
from perf_mcp.schema import (
    enrich_tool_schema,
    PerfOption,
    build_params,
    format_result,
    options_to_cli_args,
)

COMMON_SCHED_OPTIONS = [
    PerfOption("input", "i", "string", "Path to perf.data file"),
    PerfOption("verbose", "v", "incr", "Verbosity level", default=0),
    PerfOption("force", "f", "boolean", "Don't complain, do it"),
    PerfOption("cpu", "C", "string", "CPUs to filter"),
    PerfOption("dump-raw-trace", "D", "boolean", "Dump raw trace in ASCII"),
    PerfOption("kallsyms", None, "string", "kallsyms pathname"),
    PerfOption("symfs", None, "string", "Symbol filesystem root"),
    PerfOption("vmlinux", "k", "string", "vmlinux pathname"),
]

LATENCY_OPTIONS = COMMON_SCHED_OPTIONS + [
    PerfOption("sort", "s", "string", "Sort by key(s): max,switch,runtime,avg"),
    PerfOption("pid", "p", "string", "Analyze only these PIDs"),
    PerfOption("output", None, "string", "Output file path"),
    PerfOption("prio", None, "string", "Filter by task priority"),
    PerfOption("repeat", "r", "integer", "Number of times to repeat"),
    PerfOption("tid", None, "string", "Only these TIDs"),
]

TIMEHIST_OPTIONS = COMMON_SCHED_OPTIONS + [
    PerfOption("summary", "s", "boolean", "Show summary statistics only"),
    PerfOption("wakeups", "w", "boolean", "Show wakeup events"),
    PerfOption("migrations", "M", "boolean", "Show migration events"),
    PerfOption("idle-hist", "I", "boolean", "Show idle-related events"),
    PerfOption("state", "S", "boolean", "Show task state at switch"),
    PerfOption("next", "n", "boolean", "Show next task"),
    PerfOption("call-graph", "g", "string", "Call graph options"),
    PerfOption("max-stack", None, "integer", "Maximum stack depth"),
    PerfOption("pid", "p", "string", "Analyze only these PIDs"),
    PerfOption("comms", "c", "string", "Only show these comms"),
    PerfOption("time", None, "string", "Time span to analyze"),
    PerfOption("ns", None, "boolean", "Show times in nanoseconds"),
    PerfOption("show-prio", None, "boolean", "Show task priority"),
    PerfOption("pre-migrations", None, "boolean", "Show pre-migration events"),
    PerfOption("with-summary", None, "boolean", "Show summary with detailed output"),
    PerfOption("cpu-visual", None, "boolean", "Show CPU visualization"),
    PerfOption("tid", None, "string", "Analyze only these TIDs"),
]

MAP_OPTIONS = COMMON_SCHED_OPTIONS + [
    PerfOption("compact", None, "boolean", "Show one-letter task state"),
    PerfOption("color-pids", None, "string", "Highlight these PIDs with color"),
    PerfOption("color-cpus", None, "string", "Highlight these CPUs with color"),
    PerfOption("task-name", None, "string", "Map task name(s) to their thread ids"),
    PerfOption("fuzzy-name", None, "string", "Map fuzzy task name(s)"),
    PerfOption("cpus", None, "string", "CPUs to display in map"),
    PerfOption("pids", None, "string", "PIDs to show in map"),
]


def register_tools(mcp: FastMCP, executor: PerfExecutor) -> None:
    """Register all 5 perf sched MCP tools."""

    @mcp.tool(
        description=(
            "Per-task scheduling latency statistics. Shows max, average, and total scheduling delay per task.\n"
            "\n"
            "Use this to identify tasks that are being starved or experiencing long scheduling delays.\n"
            "\n"
            "Key parameters:\n"
            "- sort: sort key -- 'max' (default), 'switch', 'runtime', 'avg'.\n"
            "- pid: filter to specific PIDs.\n"
            "\n"
            "Output: table with task name, max latency, avg latency, switch count.\n"
            "Requires: perf sched record."
        ),
    )
    async def perf_sched_latency(
        input: str,
        verbose: int = 0,
        force: bool = False,
        cpu: str | None = None,
        sort: str | None = None,
        pid: str | None = None,
        output: str | None = None,
        prio: str | None = None,
        repeat: int | None = None,
        tid: str | None = None,
        dump_raw_trace: bool = False,
        kallsyms: str | None = None,
        symfs: str | None = None,
        vmlinux: str | None = None,
    ) -> str:
        params = build_params(locals())
        if "output" in params:
            params["output"] = executor.validate_output_path(params["output"])
        return format_result(
            await executor.run(
                ["sched", "latency"] + options_to_cli_args(LATENCY_OPTIONS, params),
                input_path=input,
            )
        )

    @mcp.tool(
        description=(
            "Timestamped scheduler timeline showing every context switch with runtime and scheduling delay.\n"
            "\n"
            "Use this for detailed scheduling analysis -- find when and why tasks were descheduled.\n"
            "\n"
            "Key parameters:\n"
            "- summary: true to show only summary stats (no per-event detail).\n"
            "- wakeups: show wakeup events between switches.\n"
            "- migrations: show CPU migration events.\n"
            "- idle_hist: show idle-time analysis.\n"
            "- state: show task state (R/S/D/T) at each switch.\n"
            "- call_graph: 'fp' or 'dwarf' for callchain at each switch.\n"
            "- with_summary: show both detail and summary.\n"
            "- comms: filter to specific task names.\n"
            "- time: restrict to time range.\n"
            "\n"
            "Output: per-event table with timestamp, task, runtime, wait-time, scheduling delay.\n"
            "Requires: perf sched record."
        ),
    )
    async def perf_sched_timehist(
        input: str,
        verbose: int = 0,
        force: bool = False,
        cpu: str | None = None,
        summary: bool = False,
        wakeups: bool = False,
        migrations: bool = False,
        idle_hist: bool = False,
        state: bool = False,
        next: bool = False,
        call_graph: str | None = None,
        max_stack: int | None = None,
        pid: str | None = None,
        comms: str | None = None,
        time: str | None = None,
        ns: bool = False,
        show_prio: bool = False,
        pre_migrations: bool = False,
        with_summary: bool = False,
        cpu_visual: bool = False,
        tid: str | None = None,
        dump_raw_trace: bool = False,
        kallsyms: str | None = None,
        symfs: str | None = None,
        vmlinux: str | None = None,
    ) -> str:
        params = build_params(locals())
        return format_result(
            await executor.run(
                ["sched", "timehist"] + options_to_cli_args(TIMEHIST_OPTIONS, params),
                input_path=input,
            )
        )

    @mcp.tool(
        description=(
            "ASCII CPU activity map showing which task ran on which CPU at each time slice.\n"
            "\n"
            "Use this for a visual overview of scheduling patterns, CPU affinity issues, and load imbalance.\n"
            "\n"
            "Key parameters:\n"
            "- compact: one-character-per-task view.\n"
            "- cpus: restrict to specific CPUs.\n"
            "- pids: restrict to specific PIDs.\n"
            "- color_pids/color_cpus: highlight specific PIDs/CPUs.\n"
            "\n"
            "Output: ASCII grid with CPUs as rows and time as columns.\n"
            "Requires: perf sched record."
        ),
    )
    async def perf_sched_map(
        input: str,
        verbose: int = 0,
        force: bool = False,
        cpu: str | None = None,
        compact: bool = False,
        color_pids: str | None = None,
        color_cpus: str | None = None,
        task_name: str | None = None,
        fuzzy_name: str | None = None,
        cpus: str | None = None,
        pids: str | None = None,
        dump_raw_trace: bool = False,
        kallsyms: str | None = None,
        symfs: str | None = None,
        vmlinux: str | None = None,
    ) -> str:
        params = build_params(locals())
        return format_result(
            await executor.run(
                ["sched", "map"] + options_to_cli_args(MAP_OPTIONS, params), input_path=input
            )
        )

    @mcp.tool(
        description=(
            "Dump raw scheduler tracepoint events from perf.data.\n"
            "\n"
            "Use this for custom analysis or when the structured views (latency, timehist, map) don't show what you need.\n"
            "\n"
            "Output: raw tracepoint event lines.\n"
            "Requires: perf sched record."
        ),
    )
    async def perf_sched_script(
        input: str,
        verbose: int = 0,
        force: bool = False,
        cpu: str | None = None,
        dump_raw_trace: bool = False,
        kallsyms: str | None = None,
        symfs: str | None = None,
        vmlinux: str | None = None,
    ) -> str:
        params = build_params(locals())
        return format_result(
            await executor.run(
                ["sched", "script"] + options_to_cli_args(COMMON_SCHED_OPTIONS, params),
                input_path=input,
            )
        )

    @mcp.tool(
        description=(
            "Replay recorded scheduler events to simulate the original scheduling.\n"
            "\n"
            "Replays the workload's scheduling decisions and reports statistics about the simulated run.\n"
            "\n"
            "Output: replay statistics (throughput, latency).\n"
            "Requires: perf sched record."
        ),
    )
    async def perf_sched_replay(
        input: str,
        verbose: int = 0,
        force: bool = False,
        cpu: str | None = None,
        dump_raw_trace: bool = False,
        kallsyms: str | None = None,
        symfs: str | None = None,
        vmlinux: str | None = None,
    ) -> str:
        params = build_params(locals())
        return format_result(
            await executor.run(
                ["sched", "replay"] + options_to_cli_args(COMMON_SCHED_OPTIONS, params),
                input_path=input,
            )
        )

    enrich_tool_schema(mcp, "perf_sched_latency", LATENCY_OPTIONS)
    enrich_tool_schema(mcp, "perf_sched_timehist", TIMEHIST_OPTIONS)
    enrich_tool_schema(mcp, "perf_sched_map", MAP_OPTIONS)
    enrich_tool_schema(mcp, "perf_sched_script", COMMON_SCHED_OPTIONS)
    enrich_tool_schema(mcp, "perf_sched_replay", COMMON_SCHED_OPTIONS)
