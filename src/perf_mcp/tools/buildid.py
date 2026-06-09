"""perf buildid-list -- list build IDs in a perf.data file.

Shows the ELF build-id hash and associated DSO path for each binary
referenced in the profile data. Useful for verifying symbol resolution
will work on a different machine.
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

BUILDID_OPTIONS = [
    PerfOption("input", "i", "string", "Path to perf.data file"),
    PerfOption("verbose", "v", "incr", "Verbosity level", default=0),
    PerfOption("force", "f", "boolean", "Don't complain, do it"),
    PerfOption("with-hits", "H", "boolean", "Show only DSOs with hits"),
    PerfOption("kernel", "k", "boolean", "Show running kernel build id"),
    PerfOption("kernel-maps", None, "boolean", "Show running kernel build-id and map"),
]


def register_tools(mcp: FastMCP, executor: PerfExecutor) -> None:
    @mcp.tool(
        description=(
            "List the ELF build-id hashes for binaries referenced in perf.data.\n"
            "\n"
            "Use this to verify symbol resolution will work: compare build IDs against installed debuginfo packages.\n"
            "\n"
            "Key parameters:\n"
            "- with_hits: only show DSOs that have actual samples.\n"
            "- kernel: show the running kernel's build ID.\n"
            "- kernel_maps: show kernel build ID with address map.\n"
            "\n"
            "Output: '<build-id-hash> <dso-path>' per line.\n"
            "Works on any perf.data."
        ),
    )
    async def perf_buildid_list(
        input: str,
        verbose: int = 0,
        force: bool = False,
        with_hits: bool = False,
        kernel: bool = False,
        kernel_maps: bool = False,
    ) -> str:
        params = build_params(locals())
        cli_args = options_to_cli_args(BUILDID_OPTIONS, params)
        args = ["buildid-list"] + cli_args
        result = await executor.run(args, input_path=input)
        return format_result(result)

    enrich_tool_schema(mcp, "perf_buildid_list", BUILDID_OPTIONS)
