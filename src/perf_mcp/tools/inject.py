"""perf inject -- transform perf event streams.

Reads a perf.data file, applies transformations (build-id injection,
Intel PT/ARM SPE decode, scheduler event merging, JIT processing),
and writes a new perf.data file.

This is the only tool that writes a perf.data output file. The output
path is validated against BLOCKED_PREFIXES before execution.
"""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from perf_mcp.executor import PerfExecutor
from perf_mcp.schema import PerfOption, register_perf_tool

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
    register_perf_tool(
        mcp,
        executor,
        tool_name="perf_inject",
        command=["inject"],
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
        options=INJECT_OPTIONS,
        output_options=["output"],
        output_file_param="output",
        required_options={"output"},
    )
