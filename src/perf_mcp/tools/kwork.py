"""perf kwork -- kernel work item analysis (IRQ, softirq, workqueue)."""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from perf_mcp.executor import PerfExecutor
from perf_mcp.schema import PerfOption, register_perf_tool

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

    register_perf_tool(
        mcp,
        executor,
        tool_name="perf_kwork_report",
        command=["kwork", "report"],
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
        options=COMMON_KWORK_OPTIONS,
    )

    register_perf_tool(
        mcp,
        executor,
        tool_name="perf_kwork_latency",
        command=["kwork", "latency"],
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
        options=COMMON_KWORK_OPTIONS,
    )

    register_perf_tool(
        mcp,
        executor,
        tool_name="perf_kwork_timehist",
        command=["kwork", "timehist"],
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
        options=TIMEHIST_OPTIONS,
    )

    register_perf_tool(
        mcp,
        executor,
        tool_name="perf_kwork_top",
        command=["kwork", "top"],
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
        options=COMMON_KWORK_OPTIONS,
    )
