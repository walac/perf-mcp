"""perf data convert -- convert perf.data to other formats.

Converts perf.data files to JSON or CTF (Common Trace Format) for
processing by external tools. Output paths are validated against
BLOCKED_PREFIXES.
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

CONVERT_OPTIONS = [
    PerfOption("input", "i", "string", "Path to perf.data file"),
    PerfOption("to-json", None, "string", "Convert to JSON format, specify output file path"),
    PerfOption("to-ctf", None, "string", "Convert to CTF format, specify output directory"),
    PerfOption("verbose", "v", "incr", "Verbosity level", default=0),
    PerfOption("force", "f", "boolean", "Don't complain, do it"),
    PerfOption("all", None, "boolean", "Convert all events"),
    PerfOption("tod", None, "boolean", "Convert timestamps to wall clock time"),
    PerfOption("time", None, "string", "Time span to convert"),
]


def register_tools(mcp: FastMCP, executor: PerfExecutor) -> None:
    @mcp.tool(
        description=(
            "Convert perf.data to JSON or CTF (Common Trace Format).\n"
            "\n"
            "Use this to export data for processing in external tools.\n"
            "\n"
            "Key parameters:\n"
            "- to_json: output JSON file path (e.g. '/tmp/perf.json').\n"
            "- to_ctf: output CTF directory path.\n"
            "- all: include all events, not just samples.\n"
            "- tod: convert timestamps to wall-clock time.\n"
            "\n"
            "Exactly one of to_json or to_ctf must be specified.\n"
            "Output: returns the output file/directory path."
        ),
    )
    async def perf_data_convert(
        input: str,
        to_json: str | None = None,
        to_ctf: str | None = None,
        verbose: int = 0,
        force: bool = False,
        all: bool = False,
        tod: bool = False,
        time: str | None = None,
    ) -> str:
        params = build_params(locals())
        if "to_json" in params:
            params["to_json"] = executor.validate_output_path(params["to_json"])
        if "to_ctf" in params:
            params["to_ctf"] = executor.validate_output_path(params["to_ctf"])
        cli_args = options_to_cli_args(CONVERT_OPTIONS, params)
        args = ["data", "convert"] + cli_args
        result = await executor.run(args, input_path=input)
        return format_result(result)

    enrich_tool_schema(mcp, "perf_data_convert", CONVERT_OPTIONS)
