"""perf kwork -- kernel work item analysis (IRQ, softirq, workqueue).

Provides 4 MCP tools:
- perf_kwork_report: Work item statistics.
- perf_kwork_latency: Latency breakdown.
- perf_kwork_timehist: Timestamped event timeline.
- perf_kwork_top: Top work items by runtime.

Requires data from perf kwork record.
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

COMMON_KWORK_OPTIONS = [
    PerfOption("input", "i", "string", "Path to perf.data file"),
    PerfOption("verbose", "v", "incr", "Verbosity level", default=0),
    PerfOption("force", "f", "boolean", "Don't complain, do it"),
    PerfOption("cpu", "C", "string", "CPUs to filter"),
    PerfOption("name", "n", "string", "Filter by work name"),
    PerfOption("time", None, "string", "Time span to analyze"),
    PerfOption("sort", "s", "string", "Sort by key(s): count,runtime,max,avg"),
    PerfOption("dump-raw-trace", "D", "boolean", "Dump raw trace in ASCII"),
    PerfOption("kallsyms", None, "string", "kallsyms pathname"),
    PerfOption("kwork", None, "string", "Work type to trace (irq, softirq, workqueue)"),
    PerfOption("symfs", None, "string", "Symbol filesystem root"),
    PerfOption("use-bpf", None, "boolean", "Use BPF for tracing"),
    PerfOption("vmlinux", "k", "string", "vmlinux pathname"),
    PerfOption("with-summary", None, "boolean", "Show summary along with detailed output"),
]

TIMEHIST_OPTIONS = COMMON_KWORK_OPTIONS + [
    PerfOption("call-graph", "g", "string", "Call graph options"),
    PerfOption("max-stack", None, "integer", "Maximum stack depth"),
]


def register_tools(mcp: FastMCP, executor: PerfExecutor) -> None:
    """Register all 4 perf kwork MCP tools."""

    @mcp.tool(
        description=(
            "Kernel work item statistics: IRQ, softIRQ, and workqueue handlers "
            "with count, total runtime, and max latency.\n"
            "\n"
            "Use this to find the most expensive interrupt handlers or work items.\n"
            "\n"
            "Key parameters:\n"
            "- sort: 'count', 'runtime', 'max', 'avg'.\n"
            "- name: filter to a specific handler name.\n"
            "- kwork: filter by type -- 'irq', 'softirq', 'workqueue'.\n"
            "\n"
            "Output: per-handler statistics table.\n"
            "Requires: perf kwork record."
        ),
    )
    async def perf_kwork_report(
        input: str,
        verbose: int = 0,
        force: bool = False,
        cpu: str | None = None,
        name: str | None = None,
        time: str | None = None,
        sort: str | None = None,
        dump_raw_trace: bool = False,
        kallsyms: str | None = None,
        kwork: str | None = None,
        symfs: str | None = None,
        use_bpf: bool = False,
        vmlinux: str | None = None,
        with_summary: bool = False,
    ) -> str:
        params = build_params(locals())
        return format_result(
            await executor.run(
                ["kwork", "report"] + options_to_cli_args(COMMON_KWORK_OPTIONS, params),
                input_path=input,
            )
        )

    @mcp.tool(
        description=(
            "Kernel work item latency breakdown showing scheduling delay for each handler.\n"
            "\n"
            "Key parameters:\n"
            "- sort: 'count', 'max', 'avg'.\n"
            "- name: filter to specific handler.\n"
            "- kwork: filter by type.\n"
            "\n"
            "Output: per-handler latency table.\n"
            "Requires: perf kwork record."
        ),
    )
    async def perf_kwork_latency(
        input: str,
        verbose: int = 0,
        force: bool = False,
        cpu: str | None = None,
        name: str | None = None,
        time: str | None = None,
        sort: str | None = None,
        dump_raw_trace: bool = False,
        kallsyms: str | None = None,
        kwork: str | None = None,
        symfs: str | None = None,
        use_bpf: bool = False,
        vmlinux: str | None = None,
        with_summary: bool = False,
    ) -> str:
        params = build_params(locals())
        return format_result(
            await executor.run(
                ["kwork", "latency"] + options_to_cli_args(COMMON_KWORK_OPTIONS, params),
                input_path=input,
            )
        )

    @mcp.tool(
        description=(
            "Timestamped kernel work item events showing when each handler ran and for how long.\n"
            "\n"
            "Key parameters:\n"
            "- call_graph: 'fp' or 'dwarf' for callchain.\n"
            "- name: filter to specific handler.\n"
            "\n"
            "Output: per-event timeline.\n"
            "Requires: perf kwork record."
        ),
    )
    async def perf_kwork_timehist(
        input: str,
        verbose: int = 0,
        force: bool = False,
        cpu: str | None = None,
        name: str | None = None,
        time: str | None = None,
        sort: str | None = None,
        call_graph: str | None = None,
        max_stack: int | None = None,
        dump_raw_trace: bool = False,
        kallsyms: str | None = None,
        kwork: str | None = None,
        symfs: str | None = None,
        use_bpf: bool = False,
        vmlinux: str | None = None,
        with_summary: bool = False,
    ) -> str:
        params = build_params(locals())
        return format_result(
            await executor.run(
                ["kwork", "timehist"] + options_to_cli_args(TIMEHIST_OPTIONS, params),
                input_path=input,
            )
        )

    @mcp.tool(
        description=(
            "Top kernel work items ranked by total runtime.\n"
            "\n"
            "Quick view of the busiest interrupt/softirq/workqueue handlers.\n"
            "\n"
            "Key parameters:\n"
            "- sort: ranking metric -- 'runtime' (default), 'count', 'max'.\n"
            "\n"
            "Output: ranked handler list.\n"
            "Requires: perf kwork record."
        ),
    )
    async def perf_kwork_top(
        input: str,
        verbose: int = 0,
        force: bool = False,
        cpu: str | None = None,
        name: str | None = None,
        time: str | None = None,
        sort: str | None = None,
        dump_raw_trace: bool = False,
        kallsyms: str | None = None,
        kwork: str | None = None,
        symfs: str | None = None,
        use_bpf: bool = False,
        vmlinux: str | None = None,
        with_summary: bool = False,
    ) -> str:
        params = build_params(locals())
        return format_result(
            await executor.run(
                ["kwork", "top"] + options_to_cli_args(COMMON_KWORK_OPTIONS, params),
                input_path=input,
            )
        )

    enrich_tool_schema(mcp, "perf_kwork_report", COMMON_KWORK_OPTIONS)
    enrich_tool_schema(mcp, "perf_kwork_latency", COMMON_KWORK_OPTIONS)
    enrich_tool_schema(mcp, "perf_kwork_timehist", TIMEHIST_OPTIONS)
    enrich_tool_schema(mcp, "perf_kwork_top", COMMON_KWORK_OPTIONS)
