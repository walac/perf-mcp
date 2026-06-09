"""perf mem report -- memory access profiling.

Analyzes memory access patterns: data source (L1/L2/L3 cache, DRAM),
access latency, and load/store breakdown. Requires memory data
recording (perf mem record or perf record -d).

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

MEM_OPTIONS = [
    PerfOption("input", "i", "string", "Path to perf.data file"),
    PerfOption("verbose", "v", "incr", "Verbosity level", default=0),
    PerfOption("force", "f", "boolean", "Don't complain, do it"),
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
    @mcp.tool(
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
    )
    async def perf_mem_report(
        input: str,
        verbose: int = 0,
        force: bool = False,
        sort: str | None = None,
        vmlinux: str | None = None,
        cpu: str | None = None,
        type: str | None = None,
        phys_data: bool = False,
        data_page_size: bool = False,
        all_kernel: bool = False,
        all_user: bool = False,
        dump_raw_samples: bool = False,
        event: str | None = None,
        field_separator: str | None = None,
        hide_unresolved: bool = False,
        ldlat: int | None = None,
        type_profile: bool = False,
    ) -> str:
        params = build_params(locals())
        cli_args = options_to_cli_args(MEM_OPTIONS, params)
        args = ["mem", "report", "--stdio"] + cli_args
        result = await executor.run(args, input_path=input)
        return format_result(result)

    enrich_tool_schema(mcp, "perf_mem_report", MEM_OPTIONS)
