"""perf inject -- transform perf event streams.

Reads a perf.data file, applies transformations (build-id injection,
Intel PT/ARM SPE decode, scheduler event merging, JIT processing),
and writes a new perf.data file.

This is the only tool that writes a perf.data output file. The output
path is validated against BLOCKED_PREFIXES before execution.
"""

from __future__ import annotations

import os

from mcp.server.fastmcp import FastMCP

from perf_mcp.executor import PerfExecutor
from perf_mcp.schema import (
    enrich_tool_schema,
    build_params,
    PerfOption,
    format_result,
    options_to_cli_args,
)

INJECT_OPTIONS = [
    PerfOption("input", "i", "string", "Path to input perf.data file"),
    PerfOption("output", "o", "string", "Path to output perf.data file"),
    PerfOption("verbose", "v", "incr", "Verbosity level", default=0),
    PerfOption("force", "f", "boolean", "Don't complain, do it"),
    PerfOption("build-ids", "b", "boolean", "Inject build IDs into the output file"),
    PerfOption("sched-stat", "s", "boolean", "Merge sched_stat and sched_switch events"),
    PerfOption("jit", None, "boolean", "Process JIT data and inject JIT code"),
    PerfOption(
        "itrace", None, "string", "Decode Instruction Tracing data and inject synthetic events"
    ),
    PerfOption("strip", None, "boolean", "Use with --itrace to strip non-synthesized events"),
    PerfOption("vm-time-correlation", None, "string", "Correlate time between host and guest"),
    PerfOption("guest-data", None, "string", "Inject guest data (path to guest perf.data)"),
    PerfOption("buildid-all", None, "boolean", "Inject build IDs for all DSOs"),
    PerfOption("convert-callchain", None, "boolean", "Convert callchain to dwarf-based"),
    PerfOption("guestmount", None, "string", "Guest OS root file system mount point"),
    PerfOption("ignore-vmlinux", None, "boolean", "Don't load vmlinux even if found"),
    PerfOption("kallsyms", None, "string", "kallsyms pathname"),
    PerfOption("known-build-ids", None, "string", "Known build IDs"),
    PerfOption("mmap2-buildid-all", None, "boolean", "Inject build IDs for all mmap2 events"),
    PerfOption("mmap2-buildids", None, "boolean", "Inject build IDs in mmap2 events"),
    PerfOption("vmlinux", None, "string", "vmlinux pathname"),
]


def register_tools(mcp: FastMCP, executor: PerfExecutor) -> None:
    @mcp.tool(
        description=(
            "Transform a perf.data file: inject build IDs, decode hardware traces, merge scheduler events, or process JIT data. Writes a new perf.data.\n"
            "\n"
            "Use this as a preprocessing step before perf_report or perf_script.\n"
            "\n"
            "Key parameters:\n"
            "- input: source perf.data path (required).\n"
            "- output: destination perf.data path (required).\n"
            "- build_ids: inject build-id headers for symbol resolution.\n"
            "- itrace: decode hardware traces. Values:\n"
            "  'i0ns' = synthesize instructions,\n"
            "  'b' = synthesize branches,\n"
            "  'c' = synthesize calls,\n"
            "  'e' = synthesize errors.\n"
            "- jit: process JIT-compiled code mappings.\n"
            "- sched_stat: merge sched_stat and sched_switch events.\n"
            "\n"
            "Output: writes a new perf.data file, returns path and size."
        ),
    )
    async def perf_inject(
        input: str,
        output: str,
        verbose: int = 0,
        force: bool = False,
        build_ids: bool = False,
        sched_stat: bool = False,
        jit: bool = False,
        itrace: str | None = None,
        strip: bool = False,
        vm_time_correlation: str | None = None,
        guest_data: str | None = None,
        buildid_all: bool = False,
        convert_callchain: bool = False,
        guestmount: str | None = None,
        ignore_vmlinux: bool = False,
        kallsyms: str | None = None,
        known_build_ids: str | None = None,
        mmap2_buildid_all: bool = False,
        mmap2_buildids: bool = False,
        vmlinux: str | None = None,
    ) -> str:
        params = build_params(locals())

        validated_output = executor.validate_output_path(output)
        params["output"] = validated_output
        cli_args = options_to_cli_args(INJECT_OPTIONS, params)
        args = ["inject"] + cli_args
        result = await executor.run(args, input_path=input)
        if result.returncode == 0:
            try:
                size = os.path.getsize(validated_output)
                return f"Output written to: {validated_output} ({size} bytes)"
            except OSError:
                return format_result(result)
        return format_result(result)

    enrich_tool_schema(mcp, "perf_inject", INJECT_OPTIONS)
