"""perf evlist — list events recorded in a perf.data file.

This is the simplest tool module and serves as the canonical example of
the tool module pattern used throughout perf-mcp. Every tool module:

1. Defines an OPTIONS list of PerfOption objects describing each CLI flag.
2. Exports a ``register_tools(mcp, executor)`` function.
3. Inside register_tools, uses ``@mcp.tool()`` to register an async function
   whose parameter names match the PerfOption.param_name values.
4. The function body calls ``build_params(locals())`` to capture parameters,
   ``options_to_cli_args()`` to convert them to CLI flags, and
   ``executor.run()`` to invoke perf.

The function parameters define the MCP tool's JSON Schema — FastMCP infers
types and defaults from the Python signature. Parameters with no default
are required; ``None`` defaults make them optional.
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

# Each PerfOption maps to one perf CLI flag.
# Fields: long_name, short_name, param_type, description [, default] [, negatable]
EVLIST_OPTIONS = [
    PerfOption("input", "i", "string", "Path to perf.data file"),
    PerfOption("verbose", "v", "incr", "Verbosity level", default=0),
    PerfOption("force", "f", "boolean", "Don't complain, do it"),
    PerfOption("freq", "F", "boolean", "Show the sample frequency used for each event"),
    PerfOption("group", "g", "boolean", "Show event groups"),
    PerfOption("trace-fields", None, "boolean", "Show tracepoint fields"),
]


def register_tools(mcp: FastMCP, executor: PerfExecutor) -> None:
    """Register the perf_evlist MCP tool.

    Called automatically by server.py's auto-discovery mechanism.
    The ``mcp`` and ``executor`` are shared instances from server.py.
    """

    @mcp.tool(
        description=(
            "List events in a perf.data file. Always call this first to understand what was recorded before using other tools.\n"
            "\n"
            "Shows each event's name (e.g. 'cpu/cycles/'), type, config, and sampling settings. Use freq=true to see sample frequencies, group=true to see event grouping, verbose=1 for full perf_event_attr details.\n"
            "\n"
            "Output: one event per line (e.g. 'cpu/cycles/Pu').\n"
            "No prerequisites — works on any perf.data."
        ),
    )
    async def perf_evlist(
        input: str,
        verbose: int = 0,
        force: bool = False,
        freq: bool = False,
        group: bool = False,
        trace_fields: bool = False,
    ) -> str:
        # 1. Capture all function parameters as a dict, filtering out defaults.
        params = build_params(locals())
        # 2. Convert the params dict to CLI arguments using the OPTIONS list.
        cli_args = options_to_cli_args(EVLIST_OPTIONS, params)
        # 3. Execute: perf evlist [--input path] [--freq] [--group] ...
        args = ["evlist"] + cli_args
        result = await executor.run(args, input_path=input)
        # 4. Format stdout + stderr + exit code into a single string.
        return format_result(result)

    enrich_tool_schema(mcp, "perf_evlist", EVLIST_OPTIONS)
