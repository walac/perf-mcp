"""perf script -- dump raw per-sample event data.

Outputs one line per sample event with configurable fields (comm, pid,
tid, timestamp, IP, symbol, DSO, etc.). The raw output is useful for
custom analysis, flamegraph generation, and detailed event inspection.

Dangerous options (--script, --dlfilter, --gen-script) are excluded
as they execute arbitrary code.
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

SCRIPT_OPTIONS = [
    PerfOption("input", "i", "string", "Path to perf.data file"),
    PerfOption("verbose", "v", "incr", "Verbosity level", default=0),
    PerfOption("force", "f", "boolean", "Don't complain, do it"),
    PerfOption(
        "fields",
        "F",
        "string",
        "Comma-separated list of fields to display: "
        "comm,tid,pid,time,cpu,event,trace,ip,sym,dso,addr,symoff,srcline,"
        "period,iregs,uregs,brstack,brstacksym,flags,bpf-output,brstackinsn,"
        "brstackoff,callindent,insn,insnlen,synth,phys_addr,metric,misc,ipc,"
        "tod,data_page_size,code_page_size,ins_lat,machine_pid,vcpu,cgroup,"
        "retire_lat,brstackinsnlen,parallelism,latency",
    ),
    PerfOption("cpu", "C", "string", "List of CPUs to filter"),
    PerfOption("comms", "c", "string", "Only display events for these comms"),
    PerfOption("pid", None, "string", "Only consider symbols in these PIDs"),
    PerfOption("tid", None, "string", "Only consider symbols in these TIDs"),
    PerfOption("symbols", "S", "string", "Only consider these symbols"),
    PerfOption("dsos", "d", "string", "Only consider these DSOs"),
    PerfOption("time", None, "string", "Time span of interest (start,stop)"),
    PerfOption("vmlinux", "k", "string", "vmlinux pathname"),
    PerfOption("kallsyms", None, "string", "kallsyms pathname"),
    PerfOption("symfs", None, "string", "Symbol filesystem root"),
    PerfOption("max-stack", None, "integer", "Maximum stack depth for callchains"),
    PerfOption("show-task-events", None, "boolean", "Display task-related events (fork/comm/exit)"),
    PerfOption("show-mmap-events", None, "boolean", "Display mmap-related events"),
    PerfOption("show-switch-events", None, "boolean", "Display context switch events"),
    PerfOption("show-namespace-events", None, "boolean", "Display namespace events"),
    PerfOption("show-lost-events", None, "boolean", "Display lost events"),
    PerfOption("show-round-events", None, "boolean", "Display finished round events"),
    PerfOption("show-bpf-events", None, "boolean", "Display BPF events"),
    PerfOption("show-cgroup-events", None, "boolean", "Display cgroup events"),
    PerfOption("show-text-poke-events", None, "boolean", "Display text poke events"),
    PerfOption("header", None, "boolean", "Show data header"),
    PerfOption("header-only", None, "boolean", "Show only data header"),
    PerfOption("itrace", None, "string", "Instruction Tracing options"),
    PerfOption("stitch-lbr", None, "boolean", "Enable LBR callgraph stitching"),
    PerfOption("full-source-path", None, "boolean", "Show full source file name path"),
    PerfOption(
        "demangle", None, "boolean", "Symbol demangling (default on)", negatable=True, default=True
    ),
    PerfOption("demangle-kernel", None, "boolean", "Enable kernel symbol demangling"),
    PerfOption("ns", None, "boolean", "Show times in nanoseconds"),
    PerfOption("reltime", None, "boolean", "Show relative time"),
    PerfOption("deltatime", None, "boolean", "Show delta time"),
    PerfOption("per-event-dump", None, "boolean", "Display record as parsed event"),
    PerfOption("hide-call-graph", None, "boolean", "Don't display the callchain"),
    PerfOption("max-events", None, "integer", "Maximum number of events to display"),
    # --script, --gen-script, and --dlfilter are excluded: they execute arbitrary code.
    PerfOption("inline", None, "boolean", "Show inline function"),
    PerfOption("Latency", None, "boolean", "Show latency attributes"),
    PerfOption("addr-range", None, "string", "Filter by address range"),
    PerfOption("all-cpus", "a", "boolean", "System-wide collection from all CPUs"),
    PerfOption("call-ret-trace", None, "boolean", "Show call/return trace"),
    PerfOption("call-trace", None, "boolean", "Show call trace"),
    PerfOption("dump-raw-trace", "D", "boolean", "Dump raw trace in ASCII"),
    PerfOption("graph-function", None, "string", "Show callgraph for specific function(s)"),
    PerfOption("guest-code", None, "boolean", "Display guest code"),
    PerfOption("guestkallsyms", None, "string", "Guest kallsyms file"),
    PerfOption("guestmodules", None, "string", "Guest modules file"),
    PerfOption("guestmount", None, "string", "Guest OS root file system mount point"),
    PerfOption("guestvmlinux", None, "string", "Guest vmlinux pathname"),
    PerfOption("insn-trace", None, "boolean", "Show instruction trace"),
    PerfOption("max-blocks", None, "integer", "Maximum number of code blocks to dump"),
    PerfOption("merge-callchains", None, "boolean", "Merge deferred callchains"),
    PerfOption("show-info", None, "boolean", "Display extended perf.data info"),
    PerfOption(
        "show-kernel-path", None, "boolean", "Show kernel DSO path instead of [kernel.kallsyms]"
    ),
    PerfOption("stop-bt", None, "string", "Stop unwinding callchain at this symbol"),
    PerfOption("xed", None, "boolean", "Use Intel XED disassembler"),
]


def register_tools(mcp: FastMCP, executor: PerfExecutor) -> None:
    @mcp.tool(
        description=(
            "Dump raw per-sample events from perf.data. Each line is one sample with configurable fields.\n"
            "\n"
            "Use this when you need the raw data rather than aggregated histograms — for flamegraph input, custom filtering, or inspecting individual events.\n"
            "\n"
            "Key parameters:\n"
            "- fields: comma-separated output fields. Common sets:\n"
            "  'comm,pid,tid,time,event,ip,sym,dso' (general),\n"
            "  'ip,sym,dso' (flamegraph input),\n"
            "  'comm,tid,time,ip,sym,srcline' (source mapping).\n"
            "  Available: comm,tid,pid,time,cpu,event,trace,ip,sym,dso,addr,symoff,srcline,period,flags,callindent,insn,brstacksym.\n"
            "- symbols/dsos/comms/pid/tid: filter to specific functions/DSOs/processes.\n"
            "- time: restrict to time range 'start,stop'.\n"
            "- max_events: limit number of events returned.\n"
            "- header_only: show file metadata only.\n"
            "- show_task_events/show_mmap_events/show_switch_events: include non-sample events.\n"
            "- call_trace/call_ret_trace/insn_trace: Intel PT trace modes.\n"
            "\n"
            "Output: one line per sample. Format depends on fields parameter.\n"
            "Works on any perf.data from perf record."
        ),
    )
    async def perf_script(
        input: str,
        verbose: int = 0,
        force: bool = False,
        fields: str | None = None,
        cpu: str | None = None,
        comms: str | None = None,
        pid: str | None = None,
        tid: str | None = None,
        symbols: str | None = None,
        dsos: str | None = None,
        time: str | None = None,
        vmlinux: str | None = None,
        kallsyms: str | None = None,
        symfs: str | None = None,
        max_stack: int | None = None,
        show_task_events: bool = False,
        show_mmap_events: bool = False,
        show_switch_events: bool = False,
        show_namespace_events: bool = False,
        show_lost_events: bool = False,
        show_round_events: bool = False,
        show_bpf_events: bool = False,
        show_cgroup_events: bool = False,
        show_text_poke_events: bool = False,
        header: bool = False,
        header_only: bool = False,
        itrace: str | None = None,
        stitch_lbr: bool = False,
        full_source_path: bool = False,
        demangle: bool | None = None,
        demangle_kernel: bool = False,
        ns: bool = False,
        reltime: bool = False,
        deltatime: bool = False,
        per_event_dump: bool = False,
        hide_call_graph: bool = False,
        max_events: int | None = None,
        inline: bool = False,
        Latency: bool = False,
        addr_range: str | None = None,
        all_cpus: bool = False,
        call_ret_trace: bool = False,
        call_trace: bool = False,
        dump_raw_trace: bool = False,
        graph_function: str | None = None,
        guest_code: bool = False,
        guestkallsyms: str | None = None,
        guestmodules: str | None = None,
        guestmount: str | None = None,
        guestvmlinux: str | None = None,
        insn_trace: bool = False,
        max_blocks: int | None = None,
        merge_callchains: bool = False,
        show_info: bool = False,
        show_kernel_path: bool = False,
        stop_bt: str | None = None,
        xed: bool = False,
    ) -> str:
        params = build_params(locals())

        cli_args = options_to_cli_args(SCRIPT_OPTIONS, params)
        args = ["script"] + cli_args
        result = await executor.run(args, input_path=input)
        return format_result(result)

    enrich_tool_schema(mcp, "perf_script", SCRIPT_OPTIONS)
