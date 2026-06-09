"""perf kmem stat -- kernel memory allocation analysis.

Shows slab and page allocator statistics: allocation counts, sizes,
fragmentation, and per-callsite breakdowns. Can identify memory leaks
via the live option (shows allocations not yet freed).

Requires data from perf kmem record.
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

KMEM_OPTIONS = [
    PerfOption("input", "i", "string", "Path to perf.data file"),
    PerfOption("verbose", "v", "incr", "Verbosity level", default=0),
    PerfOption("force", "f", "boolean", "Don't complain, do it"),
    PerfOption("caller", None, "boolean", "Show per-callsite statistics"),
    PerfOption("alloc", None, "boolean", "Show allocation statistics"),
    PerfOption(
        "sort",
        "s",
        "string",
        "Sort by key(s): ptr,callsite,bytes_req,bytes_alloc,hit,pingpong,frag",
    ),
    PerfOption("line", "l", "integer", "Print N lines only"),
    PerfOption("raw-ip", None, "boolean", "Print raw IP instead of symbol"),
    PerfOption("slab", None, "boolean", "Analyze slab allocator events"),
    PerfOption("page", None, "boolean", "Analyze page allocator events"),
    PerfOption("live", None, "boolean", "Show only live (not-yet-freed) allocations"),
    PerfOption("time", None, "string", "Time span to analyze"),
]


def register_tools(mcp: FastMCP, executor: PerfExecutor) -> None:
    @mcp.tool(
        description=(
            "Kernel memory allocation statistics: slab and page allocator activity with per-callsite breakdown.\n"
            "\n"
            "Use this to find excessive allocators, fragmentation, or leaks.\n"
            "\n"
            "Key parameters:\n"
            "- slab: analyze slab allocator (kmalloc/kmem_cache).\n"
            "- page: analyze page allocator.\n"
            "- caller: show per-callsite statistics.\n"
            "- live: show only allocations not yet freed (leak detection).\n"
            "- sort: 'ptr', 'callsite', 'bytes_req', 'bytes_alloc', 'hit', 'pingpong', 'frag'.\n"
            "\n"
            "Output: allocation statistics table.\n"
            "Requires: perf kmem record."
        ),
    )
    async def perf_kmem_stat(
        input: str,
        verbose: int = 0,
        force: bool = False,
        caller: bool = False,
        alloc: bool = False,
        sort: str | None = None,
        line: int | None = None,
        raw_ip: bool = False,
        slab: bool = False,
        page: bool = False,
        live: bool = False,
        time: str | None = None,
    ) -> str:
        params = build_params(locals())
        cli_args = options_to_cli_args(KMEM_OPTIONS, params)
        args = ["kmem", "stat"] + cli_args
        result = await executor.run(args, input_path=input)
        return format_result(result)

    enrich_tool_schema(mcp, "perf_kmem_stat", KMEM_OPTIONS)
