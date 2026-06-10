"""perf mem report -- memory access profiling.

Forces --stdio output.
"""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from perf_mcp.executor import PerfExecutor
from perf_mcp.schema import COMMON_OPTIONS, PerfOption, register_perf_tool

MEM_OPTIONS = COMMON_OPTIONS + [
    PerfOption("sort", "s", "string", "Sort by key(s)"),
    PerfOption("vmlinux", "k", "string", "vmlinux pathname"),
    PerfOption("cpu", "C", "string", "CPUs to filter"),
    PerfOption("type", "t", "string", "Memory operation type"),
    PerfOption("phys-data", "p", "boolean", "Show physical address data"),
    PerfOption("data-page-size", None, "boolean", "Show data page size"),
    PerfOption("all-kernel", None, "boolean", "Only show kernel space entries"),
    PerfOption("all-user", None, "boolean", "Only show user space entries"),
    PerfOption("dump-raw-samples", "D", "boolean", "Dump raw samples in ASCII"),
    PerfOption("event", "e", "string", "Event selector"),
    PerfOption("field-separator", "x", "string", "Field separator"),
    PerfOption("hide-unresolved", "U", "boolean", "Only display entries resolved to a symbol"),
    PerfOption("ldlat", None, "integer", "Load latency threshold in cycles"),
    PerfOption("type-profile", None, "boolean", "Show data type profile"),
]


def register_tools(mcp: FastMCP, executor: PerfExecutor) -> None:
    register_perf_tool(
        mcp,
        executor,
        tool_name="perf_mem_report",
        command=["mem", "report", "--stdio"],
        description=(
            "Memory access profiling: data source (L1/L2/L3/DRAM), latency, and load/store breakdown.\n"
            "\n"
            "Use this to find cache-miss-heavy code or NUMA-unfriendly access patterns.\n"
            "\n"
            "Key parameters:\n"
            "- sort: sort key for the histogram.\n"
            "- type: 'load' or 'store' to filter access type.\n"
            "- ldlat: load latency threshold in CPU cycles.\n"
            "- type_profile: show data type profile (DWARF-based).\n"
            "- phys_data: show physical memory addresses.\n"
            "\n"
            "Output: memory access histogram with data source breakdown.\n"
            "Requires: perf mem record (or perf record -d)."
        ),
        options=MEM_OPTIONS,
    )
