"""perf kvm stat report -- KVM virtual machine exit analysis.

Shows VM exit reasons, counts, and time spent per exit type for
KVM-based virtual machines. Useful for diagnosing virtualization
overhead (e.g., excessive HLT, I/O, or EPT violation exits).

Requires data from perf kvm stat record.
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

KVM_OPTIONS = [
    PerfOption("input", "i", "string", "Path to perf.data.guest file"),
    PerfOption("verbose", "v", "incr", "Verbosity level", default=0),
    PerfOption("force", "f", "boolean", "Don't complain, do it"),
    PerfOption("vcpu", None, "string", "Filter by vCPU"),
    PerfOption("event", None, "string", "Filter by KVM exit event type"),
    PerfOption("key", "k", "string", "Sort key"),
    PerfOption("sort", "s", "string", "Sort by key(s)"),
    PerfOption("cpu", "C", "string", "CPUs to filter"),
    PerfOption("pid", "p", "string", "Filter by PID"),
    PerfOption("all-cpus", "a", "boolean", "System-wide collection from all CPUs"),
    PerfOption("display", None, "string", "Events to display"),
    PerfOption("guest", None, "boolean", "Trace guest events"),
    PerfOption("guest-code", None, "boolean", "Display guest code"),
    PerfOption("guestkallsyms", None, "string", "Guest kallsyms file"),
    PerfOption("guestmodules", None, "string", "Guest modules file"),
    PerfOption("guestmount", None, "string", "Guest OS root file system mount point"),
    PerfOption("guestvmlinux", None, "string", "Guest vmlinux pathname"),
    PerfOption("host", None, "boolean", "Trace host events"),
    PerfOption("mmap-pages", "m", "string", "Number of mmap pages"),
    PerfOption("output", "o", "string", "Output file name"),
    PerfOption(
        "proc-map-timeout", None, "integer", "Per-thread proc mmap processing timeout in ms"
    ),
]


def register_tools(mcp: FastMCP, executor: PerfExecutor) -> None:
    @mcp.tool(
        description=(
            "KVM virtual machine exit analysis: shows VM exit reasons, counts, and time per exit type.\n"
            "\n"
            "Use this to diagnose virtualization overhead — excessive HLT exits indicate idle guests, I/O exits indicate slow device emulation, EPT violations indicate memory mapping churn.\n"
            "\n"
            "Key parameters:\n"
            "- key: sort by 'sample' (count), 'time', 'max', 'min'.\n"
            "- event: filter to specific exit type (e.g. 'HLT').\n"
            "- vcpu: filter to specific vCPU.\n"
            "- guest/host: filter to guest or host events.\n"
            "\n"
            "Output: exit reason table with count, time, and percentage.\n"
            "Requires: perf kvm stat record."
        ),
    )
    async def perf_kvm_stat_report(
        input: str,
        verbose: int = 0,
        force: bool = False,
        vcpu: str | None = None,
        event: str | None = None,
        key: str | None = None,
        cpu: str | None = None,
        sort: str | None = None,
        pid: str | None = None,
        all_cpus: bool = False,
        display: str | None = None,
        guest: bool = False,
        guest_code: bool = False,
        guestkallsyms: str | None = None,
        guestmodules: str | None = None,
        guestmount: str | None = None,
        guestvmlinux: str | None = None,
        host: bool = False,
        mmap_pages: str | None = None,
        output: str | None = None,
        proc_map_timeout: int | None = None,
    ) -> str:
        params = build_params(locals())
        if "output" in params:
            params["output"] = executor.validate_output_path(params["output"])
        cli_args = options_to_cli_args(KVM_OPTIONS, params)
        args = ["kvm", "stat", "report"] + cli_args
        result = await executor.run(args, input_path=input)
        return format_result(result)

    enrich_tool_schema(mcp, "perf_kvm_stat_report", KVM_OPTIONS)
