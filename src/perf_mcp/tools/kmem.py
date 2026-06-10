"""perf kmem stat -- kernel memory allocation analysis."""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from perf_mcp.executor import PerfExecutor
from perf_mcp.schema import PerfOption, register_perf_tool

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
    register_perf_tool(
        mcp,
        executor,
        tool_name="perf_kmem_stat",
        command=["kmem", "stat"],
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
        options=KMEM_OPTIONS,
        input_before_subcommand=1,
    )
