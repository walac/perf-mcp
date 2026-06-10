"""perf c2c report -- cache-to-cache (false sharing) analysis.

Forces --stdio output.
"""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from perf_mcp.executor import PerfExecutor
from perf_mcp.schema import COMMON_OPTIONS, PerfOption, register_perf_tool

C2C_OPTIONS = COMMON_OPTIONS + [
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
    register_perf_tool(
        mcp,
        executor,
        tool_name="perf_c2c_report",
        command=["c2c", "report", "--stdio"],
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
        options=C2C_OPTIONS,
    )
