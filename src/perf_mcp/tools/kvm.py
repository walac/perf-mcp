"""perf kvm stat report -- KVM virtual machine exit analysis."""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from perf_mcp.executor import PerfExecutor
from perf_mcp.schema import PerfOption, register_perf_tool

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
    register_perf_tool(
        mcp,
        executor,
        tool_name="perf_kvm_stat_report",
        command=["kvm", "stat", "report"],
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
        options=KVM_OPTIONS,
        output_options=["output"],
        input_before_subcommand=1,
    )
