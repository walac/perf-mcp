"""perf buildid-list -- list build IDs in a perf.data file."""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from perf_mcp.executor import PerfExecutor
from perf_mcp.schema import COMMON_OPTIONS, PerfOption, register_perf_tool

BUILDID_OPTIONS = COMMON_OPTIONS + [
    PerfOption("with-hits", "H", "boolean", "Show only DSOs with hits"),
    PerfOption("kernel", "k", "boolean", "Show running kernel build id"),
    PerfOption("kernel-maps", None, "boolean", "Show running kernel build-id and map"),
]


def register_tools(mcp: FastMCP, executor: PerfExecutor) -> None:
    register_perf_tool(
        mcp,
        executor,
        tool_name="perf_buildid_list",
        command=["buildid-list"],
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
        options=BUILDID_OPTIONS,
    )
