"""perf c2c report -- cache-to-cache (false sharing) analysis.

Analyzes HITM (Hit Modified) cache events to identify cache lines
with cross-core contention. Requires memory data recording
(perf record -d -a).

Forces --stdio output.
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

C2C_OPTIONS = [
    PerfOption("input", "i", "string", "Path to perf.data file"),
    PerfOption("verbose", "v", "incr", "Verbosity level", default=0),
    PerfOption("force", "f", "boolean", "Don't complain, do it"),
    PerfOption("vmlinux", "k", "string", "vmlinux pathname"),
    PerfOption("display", None, "string", "Display type"),
    PerfOption("coalesce", None, "string", "Coalesce fields (e.g. 'tid,pid,iaddr,dso')"),
    PerfOption("sort", "s", "string", "Sort by key(s)"),
    PerfOption("call-graph", "g", "string", "Call graph options"),
    PerfOption("node-info", None, "string", "Show extra node info"),
    PerfOption("full-symbols", None, "boolean", "Display full length of symbols"),
    PerfOption("no-source", None, "boolean", "Do not display source line column"),
    PerfOption("show-all", None, "boolean", "Show all captured HITM lines"),
    PerfOption("stats", None, "boolean", "Display only statistics (no reports)"),
    PerfOption("cpu", "C", "string", "CPUs to filter"),
    PerfOption("all-kernel", None, "boolean", "Only show kernel space entries"),
    PerfOption("all-user", None, "boolean", "Only show user space entries"),
    PerfOption("disassembler-style", "M", "string", "Disassembler style (e.g. intel)"),
    PerfOption("double-cl", None, "boolean", "Double the cache line size"),
    PerfOption("event", "e", "string", "Event selector"),
    PerfOption("ldlat", None, "integer", "Load latency threshold in cycles"),
    PerfOption("stitch-lbr", None, "boolean", "Enable LBR callgraph stitching"),
]


def register_tools(mcp: FastMCP, executor: PerfExecutor) -> None:
    @mcp.tool(
        description=(
            "Cache-to-cache false sharing analysis. Identifies cache lines with the most HITM (Hit Modified) events — the primary indicator of cross-core cache contention.\n"
            "\n"
            "Use this to diagnose multi-threaded performance issues caused by different threads accessing the same cache line.\n"
            "\n"
            "Key parameters:\n"
            "- display: 'tot' (total HITMs, default), 'lcl' (local/same-socket), 'rmt' (remote/cross-socket).\n"
            "- coalesce: group results by 'tid,pid,iaddr,dso' to see per-thread or per-address breakdown.\n"
            "- stats: true to show only summary statistics.\n"
            "- call_graph: enable callchain display.\n"
            "\n"
            "Output: multi-section report — shared data cache line table, per-cacheline detail with offsets and symbols.\n"
            "Requires: perf record -d -a (with memory data recording)."
        ),
    )
    async def perf_c2c_report(
        input: str,
        verbose: int = 0,
        force: bool = False,
        vmlinux: str | None = None,
        display: str | None = None,
        coalesce: str | None = None,
        sort: str | None = None,
        call_graph: str | None = None,
        node_info: str | None = None,
        full_symbols: bool = False,
        no_source: bool = False,
        show_all: bool = False,
        stats: bool = False,
        cpu: str | None = None,
        all_kernel: bool = False,
        all_user: bool = False,
        disassembler_style: str | None = None,
        double_cl: bool = False,
        event: str | None = None,
        ldlat: int | None = None,
        stitch_lbr: bool = False,
    ) -> str:
        params = build_params(locals())

        cli_args = options_to_cli_args(C2C_OPTIONS, params)
        args = ["c2c", "report", "--stdio"] + cli_args
        result = await executor.run(args, input_path=input)
        return format_result(result)

    enrich_tool_schema(mcp, "perf_c2c_report", C2C_OPTIONS)
