"""perf data convert -- convert perf.data to other formats.

Converts perf.data files to JSON or CTF (Common Trace Format) for
processing by external tools. Output paths are validated against
BLOCKED_PREFIXES.
"""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from perf_mcp.executor import PerfExecutor
from perf_mcp.schema import COMMON_OPTIONS, PerfOption, register_perf_tool

CONVERT_OPTIONS = COMMON_OPTIONS + [
    PerfOption("to-json", None, "string", "Convert to JSON format, specify output file path"),
    PerfOption("to-ctf", None, "string", "Convert to CTF format, specify output directory"),
    PerfOption("all", None, "boolean", "Convert all events"),
    PerfOption("tod", None, "boolean", "Convert timestamps to wall clock time"),
    PerfOption("time", None, "string", "Time span to convert"),
]


def register_tools(mcp: FastMCP, executor: PerfExecutor) -> None:
    register_perf_tool(
        mcp,
        executor,
        tool_name="perf_data_convert",
        command=["data", "convert"],
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
        options=CONVERT_OPTIONS,
        output_options=["to_json", "to_ctf"],
    )
