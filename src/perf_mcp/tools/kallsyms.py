"""perf kallsyms -- kernel symbol lookup.

Looks up kernel symbols by name or address using the kernel symbol
table (kallsyms). Unlike other tools, this does not require a
perf.data file.

Uses -- separator before the symbol argument to prevent
argument injection.
"""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from perf_mcp.executor import PerfExecutor
from perf_mcp.schema import format_result


def register_tools(mcp: FastMCP, executor: PerfExecutor) -> None:
    @mcp.tool(
        description=(
            "Look up a kernel symbol by name. Returns address, type, and module.\n"
            "\n"
            "Does NOT require a perf.data file — reads the running kernel's symbol table directly.\n"
            "\n"
            "Parameters:\n"
            "- symbol: kernel function/variable name to look up (required).\n"
            "- verbose: increase detail level (0-2).\n"
            "\n"
            "Output: '<address> <type> <name> [module]'."
        ),
    )
    async def perf_kallsyms(
        symbol: str,
        verbose: int = 0,
    ) -> str:
        args = ["kallsyms"]
        if verbose > 0:
            args.extend(["-v"] * verbose)
        args.extend(["--", symbol])
        result = await executor.run(args)
        return format_result(result)

    # Manually describe params (kallsyms has no PerfOption list)
    tool = mcp._tool_manager._tools.get("perf_kallsyms")
    if tool:
        props = tool.parameters.get("properties", {})
        props.setdefault("symbol", {})["description"] = "Kernel symbol name or address to look up"
        props.setdefault("verbose", {})["description"] = "Verbosity level (0-2)"
