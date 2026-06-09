"""perf lock -- lock contention analysis.

Provides 3 MCP tools for lock analysis:
- perf_lock_report: Lock acquire/contention statistics.
- perf_lock_contention: Detailed contention analysis with BPF.
- perf_lock_info: Lock type information.

Requires data from perf lock record or lock tracepoints.
"""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from perf_mcp.executor import PerfExecutor
from perf_mcp.schema import (
    enrich_tool_schema,
    PerfOption,
    build_params,
    format_result,
    options_to_cli_args,
)

COMMON_LOCK_OPTIONS = [
    PerfOption("input", "i", "string", "Path to perf.data file"),
    PerfOption("verbose", "v", "incr", "Verbosity level", default=0),
    PerfOption("force", "f", "boolean", "Don't complain, do it"),
    PerfOption("cpu", "C", "string", "CPUs to filter"),
    PerfOption("dump-raw-trace", "D", "boolean", "Dump raw trace in ASCII"),
    PerfOption("kallsyms", None, "string", "kallsyms pathname"),
    PerfOption("vmlinux", "k", "string", "vmlinux pathname"),
    PerfOption("quiet", "q", "boolean", "Do not show any warnings"),
    PerfOption("pid", "p", "string", "Filter by PID"),
    PerfOption("tid", None, "string", "Filter by TID"),
]

REPORT_OPTIONS = COMMON_LOCK_OPTIONS + [
    PerfOption(
        "sort",
        "s",
        "string",
        "Sort by key(s): acquired,contended,avg_wait,wait_total,wait_max,wait_min",
    ),
    PerfOption("type-filter", "Y", "string", "Filter by lock type"),
    PerfOption("lock-filter", "L", "string", "Filter by specific lock addr/name"),
    PerfOption("threads", "t", "boolean", "Show per-thread stats"),
    PerfOption("combine-locks", "c", "boolean", "Combine locks by caller"),
    PerfOption("key", "k", "string", "Sort key for contended locks"),
    PerfOption("field", None, "string", "Output field(s)"),
    PerfOption("field-separator", None, "string", "Field separator for output"),
    PerfOption("entries", "E", "integer", "Maximum entries to display"),
]

CONTENTION_OPTIONS = COMMON_LOCK_OPTIONS + [
    PerfOption(
        "sort", "s", "string", "Sort by key(s): contended,wait_total,wait_max,wait_min,avg_wait"
    ),
    PerfOption("type-filter", "Y", "string", "Filter by lock type"),
    PerfOption("lock-filter", "L", "string", "Filter by specific lock addr/name"),
    PerfOption("threads", "t", "boolean", "Show per-thread stats"),
    PerfOption("combine-locks", "c", "boolean", "Combine locks by caller"),
    PerfOption("key", "k", "string", "Sort key"),
    PerfOption("max-stack", None, "integer", "Maximum stack depth"),
    PerfOption("map-nr-entries", "E", "integer", "Max entries for BPF maps"),
    PerfOption("lock-addr", "a", "boolean", "Show lock addresses"),
    PerfOption("lock-owner", "o", "boolean", "Show lock owners"),
    PerfOption("all-cpus", None, "boolean", "System-wide collection"),
    PerfOption("use-bpf", None, "boolean", "Use BPF for contention tracing"),
    PerfOption("callstack-filter", None, "string", "Filter by callstack pattern"),
    PerfOption("cgroup-filter", None, "string", "Filter by cgroup"),
    PerfOption("inject-delay", None, "integer", "Inject delay in microseconds"),
    PerfOption("lock-cgroup", None, "boolean", "Show lock contention per cgroup"),
    PerfOption("map", "M", "boolean", "Show lock map"),
    PerfOption("output", None, "string", "Output file path"),
    PerfOption("stack-skip", None, "integer", "Number of stack frames to skip"),
]


def register_tools(mcp: FastMCP, executor: PerfExecutor) -> None:
    """Register all 3 perf lock MCP tools."""

    @mcp.tool(
        description=(
            "Lock statistics: acquired count, contended count, and wait times per lock.\n"
            "\n"
            "Use this to find the most contended locks in the system.\n"
            "\n"
            "Key parameters:\n"
            "- sort: sort by 'acquired', 'contended', 'avg_wait', 'wait_total', 'wait_max', 'wait_min'.\n"
            "- type_filter: filter by lock type -- 'spinlock', 'mutex', 'rwsem:R', 'rwsem:W'.\n"
            "- threads: show per-thread breakdown.\n"
            "- combine_locks: group locks by caller.\n"
            "\n"
            "Output: per-lock statistics table.\n"
            "Requires: perf lock record or lock tracepoints."
        ),
    )
    async def perf_lock_report(
        input: str,
        verbose: int = 0,
        force: bool = False,
        cpu: str | None = None,
        sort: str | None = None,
        type_filter: str | None = None,
        lock_filter: str | None = None,
        threads: bool = False,
        combine_locks: bool = False,
        key: str | None = None,
        field: str | None = None,
        field_separator: str | None = None,
        entries: int | None = None,
        dump_raw_trace: bool = False,
        kallsyms: str | None = None,
        vmlinux: str | None = None,
        quiet: bool = False,
        pid: str | None = None,
        tid: str | None = None,
    ) -> str:
        params = build_params(locals())
        return format_result(
            await executor.run(
                ["lock", "report"] + options_to_cli_args(REPORT_OPTIONS, params), input_path=input
            )
        )

    @mcp.tool(
        description=(
            "Detailed lock contention analysis showing where threads wait for locks, "
            "with optional BPF-based tracking.\n"
            "\n"
            "Key parameters:\n"
            "- lock_addr: show lock addresses.\n"
            "- lock_owner: show which task holds the lock.\n"
            "- callstack_filter: filter by callstack pattern.\n"
            "- use_bpf: use BPF for live contention tracing.\n"
            "- type_filter: filter by lock type.\n"
            "- stack_skip: skip N stack frames.\n"
            "\n"
            "Output: contention table with wait times and optional stacks.\n"
            "Requires: perf lock record or lock tracepoints."
        ),
    )
    async def perf_lock_contention(
        input: str,
        verbose: int = 0,
        force: bool = False,
        cpu: str | None = None,
        sort: str | None = None,
        type_filter: str | None = None,
        lock_filter: str | None = None,
        threads: bool = False,
        combine_locks: bool = False,
        key: str | None = None,
        max_stack: int | None = None,
        map_nr_entries: int | None = None,
        lock_addr: bool = False,
        lock_owner: bool = False,
        all_cpus: bool = False,
        use_bpf: bool = False,
        callstack_filter: str | None = None,
        cgroup_filter: str | None = None,
        inject_delay: int | None = None,
        lock_cgroup: bool = False,
        map: bool = False,
        output: str | None = None,
        stack_skip: int | None = None,
        dump_raw_trace: bool = False,
        kallsyms: str | None = None,
        vmlinux: str | None = None,
        quiet: bool = False,
        pid: str | None = None,
        tid: str | None = None,
    ) -> str:
        params = build_params(locals())
        if "output" in params:
            params["output"] = executor.validate_output_path(params["output"])
        return format_result(
            await executor.run(
                ["lock", "contention"] + options_to_cli_args(CONTENTION_OPTIONS, params),
                input_path=input,
            )
        )

    @mcp.tool(
        description=(
            "Display general information about locks in perf.data.\n"
            "\n"
            "Shows lock types and configurations found in the recording.\n"
            "\n"
            "Output: lock type and configuration summary.\n"
            "Requires: perf lock record."
        ),
    )
    async def perf_lock_info(
        input: str,
        verbose: int = 0,
        force: bool = False,
        cpu: str | None = None,
        dump_raw_trace: bool = False,
        kallsyms: str | None = None,
        vmlinux: str | None = None,
        quiet: bool = False,
        pid: str | None = None,
        tid: str | None = None,
    ) -> str:
        params = build_params(locals())
        return format_result(
            await executor.run(
                ["lock", "info"] + options_to_cli_args(COMMON_LOCK_OPTIONS, params),
                input_path=input,
            )
        )

    enrich_tool_schema(mcp, "perf_lock_report", REPORT_OPTIONS)
    enrich_tool_schema(mcp, "perf_lock_contention", CONTENTION_OPTIONS)
    enrich_tool_schema(mcp, "perf_lock_info", COMMON_LOCK_OPTIONS)
