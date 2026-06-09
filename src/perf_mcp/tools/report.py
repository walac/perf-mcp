"""perf report -- histogram-based profiling analysis.

The most commonly used perf analysis command. Reads sampling data from
perf.data and produces an overhead histogram showing which functions,
DSOs, or source lines consumed the most CPU time (or other events).
Supports callchain analysis, branch profiling, memory access profiling,
and latency-centric views.

Forces --stdio output (no TUI) for MCP compatibility.
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

REPORT_OPTIONS = [
    PerfOption("input", "i", "string", "Path to perf.data file"),
    PerfOption("verbose", "v", "incr", "Verbosity level (0-2)", default=0),
    PerfOption("force", "f", "boolean", "Don't complain, do it"),
    PerfOption(
        "sort",
        "s",
        "string",
        "Sort by key(s): comm,dso,symbol,parent,cpu,socket,srcline,weight,"
        "local_weight,addr,data_src,mem,snoop,tlb,locked,blocked,local_ins_lat,"
        "global_ins_lat,local_p_stage_cyc,global_p_stage_cyc,cgroup_id,type,"
        "typeoff,symoff,pid,tid,latency,parallelism",
    ),
    PerfOption(
        "fields",
        "F",
        "string",
        "Output field(s): overhead,overhead_sys,overhead_us,overhead_children,"
        "overhead_guest,sample,period",
    ),
    PerfOption(
        "call-graph",
        "g",
        "string",
        "Call graph: print_type,threshold[,print_limit],order,sort_key[,branch],value "
        "(e.g. 'graph,0.5,caller,function,percent')",
    ),
    PerfOption(
        "children",
        None,
        "boolean",
        "Accumulate callchains of children (default on)",
        negatable=True,
        default=True,
    ),
    PerfOption("max-stack", None, "integer", "Maximum stack depth for callchain parsing"),
    PerfOption("header", None, "boolean", "Show data header"),
    PerfOption("header-only", None, "boolean", "Show only data header"),
    PerfOption("percent-limit", None, "float", "Don't show entries under this percent"),
    PerfOption("percentage", None, "string", "How to display percentage"),
    PerfOption("group", None, "boolean", "Show event group information together"),
    PerfOption("group-sort-idx", None, "integer", "Sort output by Nth event in group"),
    PerfOption("branch-stack", "b", "boolean", "Use branch records for per-branch histogram"),
    PerfOption("branch-history", None, "boolean", "Add last branch records to call history"),
    PerfOption("mem-mode", None, "boolean", "Memory access profile"),
    PerfOption("time", None, "string", "Time span of interest (start,stop) in seconds"),
    PerfOption("inline", None, "boolean", "Show inline function"),
    PerfOption("hierarchy", "H", "boolean", "Show entries in a hierarchy"),
    PerfOption("symbol-filter", None, "string", "Only show symbols matching filter"),
    PerfOption("dsos", "d", "string", "Only consider symbols in these DSOs (comma-separated)"),
    PerfOption("comms", "c", "string", "Only consider symbols in these comms (comma-separated)"),
    PerfOption("pid", None, "string", "Only consider symbols in these PIDs"),
    PerfOption("tid", None, "string", "Only consider symbols in these TIDs"),
    PerfOption("symbols", "S", "string", "Only consider these symbols"),
    PerfOption("vmlinux", "k", "string", "vmlinux pathname"),
    PerfOption("kallsyms", None, "string", "kallsyms pathname"),
    PerfOption("modules", "m", "boolean", "Load module symbols"),
    PerfOption("hide-unresolved", "U", "boolean", "Only display entries resolved to a symbol"),
    PerfOption("cpu", "C", "string", "List of CPUs to filter"),
    PerfOption("disassembler-style", "M", "string", "Disassembler style (e.g. 'intel')"),
    PerfOption(
        "source",
        None,
        "boolean",
        "Interleave source code with assembly (default on)",
        negatable=True,
        default=True,
    ),
    PerfOption("asm-raw", None, "boolean", "Display raw encoding of assembly"),
    PerfOption("dump-raw-trace", "D", "boolean", "Dump raw trace in ASCII"),
    PerfOption("stats", None, "boolean", "Display event stats"),
    PerfOption("tasks", None, "boolean", "Display recorded tasks"),
    PerfOption("mmaps", None, "boolean", "Display recorded tasks memory maps"),
    PerfOption("show-nr-samples", "n", "boolean", "Show column with sample count"),
    PerfOption("show-total-period", None, "boolean", "Show column with sum of periods"),
    PerfOption("raw-trace", None, "boolean", "Show raw trace event output"),
    PerfOption("itrace", None, "string", "Instruction Tracing options"),
    PerfOption("stitch-lbr", None, "boolean", "Enable LBR callgraph stitching"),
    PerfOption("socket-filter", None, "integer", "Only show processor socket matching filter"),
    PerfOption("skip-empty", None, "boolean", "Do not display empty events", default=True),
    PerfOption("total-cycles", None, "boolean", "Sort all blocks by 'Sampled Cycles%'"),
    PerfOption("disable-order", None, "boolean", "Disable raw trace ordering"),
    PerfOption(
        "latency", None, "boolean", "Show latency-centric profile (requires perf record --latency)"
    ),
    PerfOption(
        "demangle", None, "boolean", "Symbol demangling (default on)", negatable=True, default=True
    ),
    PerfOption("demangle-kernel", None, "boolean", "Enable kernel symbol demangling"),
    PerfOption("symfs", None, "string", "Symbol filesystem root for offline analysis"),
    PerfOption("percent-type", None, "string", "Percent type"),
    PerfOption("ns", None, "boolean", "Show times in nanoseconds"),
    PerfOption("time-quantum", None, "string", "Time quantum for time sort key (e.g. '100ms')"),
    PerfOption("show-ref-call-graph", None, "boolean", "Show callgraph from reference event"),
    PerfOption("prefix", None, "string", "Add prefix to source file path names"),
    PerfOption("prefix-strip", None, "string", "Strip first N entries of source file path"),
    PerfOption("samples", None, "integer", "Number of samples to save per histogram entry"),
    PerfOption("parallelism", None, "string", "Only consider these parallelism levels"),
    PerfOption("column-widths", "w", "string", "Fixed column widths"),
    PerfOption("field-separator", "t", "string", "Separator for columns"),
    PerfOption("parent", "p", "string", "Regex filter to identify parent"),
    PerfOption("exclude-other", "x", "boolean", "Only display entries with parent-match"),
    PerfOption("show-cpu-utilization", None, "boolean", "Show sample % for different CPU modes"),
    PerfOption("inverted", "G", "boolean", "Inverted call graph"),
    PerfOption("ignore-callees", None, "string", "Regex of callees to ignore in call graphs"),
    # --objdump and --addr2line are excluded: they execute arbitrary binaries.
    PerfOption("ignore-vmlinux", None, "boolean", "Don't load vmlinux even if found"),
    PerfOption("show-info", "I", "boolean", "Display extended information about perf.data"),
    PerfOption("quiet", "q", "boolean", "Do not show any warnings or messages"),
    PerfOption("pretty", None, "string", "Pretty printing style key: normal raw"),
    PerfOption("threads", "T", "boolean", "Show per-thread event counters"),
    PerfOption(
        "full-source-path", None, "boolean", "Show full source file name path for source lines"
    ),
]


def register_tools(mcp: FastMCP, executor: PerfExecutor) -> None:
    @mcp.tool(
        description=(
            "Histogram profiling: shows which functions consumed the most CPU time (or other events) as a ranked overhead table.\n"
            "\n"
            "This is the primary analysis tool. Use it to answer 'where is time spent?'\n"
            "\n"
            "Key parameters:\n"
            "- sort: columns to group by. Default 'comm,dso,symbol'. Use 'srcline' for source lines, 'pid,tid' for threads, 'dso' for libraries.\n"
            "- call_graph: enable callchain. Use 'graph,0.5,caller,function,percent' for a standard caller-based call graph with 0.5% threshold.\n"
            "- percent_limit: hide entries below N% (e.g. 1.0 to show only >1%).\n"
            "- symbols: filter to specific function(s).\n"
            "- dsos: filter to specific DSO(s).\n"
            "- time: restrict to time range 'start,stop' in seconds.\n"
            "- header_only: show file metadata without the histogram.\n"
            "- mem_mode: switch to memory access profiling (needs perf record -d).\n"
            "- branch_stack: switch to branch profiling (needs perf record -b).\n"
            "- latency: show latency-centric view (needs perf record --latency).\n"
            "- children: set to false (--no-children) to show self overhead only.\n"
            "\n"
            "Output: table with columns like '% overhead | command | DSO | symbol'.\n"
            "Works on any perf.data from perf record."
        ),
    )
    async def perf_report(
        input: str,
        verbose: int = 0,
        force: bool = False,
        sort: str | None = None,
        fields: str | None = None,
        call_graph: str | None = None,
        children: bool | None = None,
        max_stack: int | None = None,
        header: bool = False,
        header_only: bool = False,
        percent_limit: float | None = None,
        percentage: str | None = None,
        group: bool = False,
        group_sort_idx: int | None = None,
        branch_stack: bool = False,
        branch_history: bool = False,
        mem_mode: bool = False,
        time: str | None = None,
        inline: bool = False,
        hierarchy: bool = False,
        symbol_filter: str | None = None,
        dsos: str | None = None,
        comms: str | None = None,
        pid: str | None = None,
        tid: str | None = None,
        symbols: str | None = None,
        vmlinux: str | None = None,
        kallsyms: str | None = None,
        modules: bool = False,
        hide_unresolved: bool = False,
        cpu: str | None = None,
        disassembler_style: str | None = None,
        source: bool | None = None,
        asm_raw: bool = False,
        dump_raw_trace: bool = False,
        stats: bool = False,
        tasks: bool = False,
        mmaps: bool = False,
        show_nr_samples: bool = False,
        show_total_period: bool = False,
        raw_trace: bool = False,
        itrace: str | None = None,
        stitch_lbr: bool = False,
        socket_filter: int | None = None,
        skip_empty: bool | None = None,
        total_cycles: bool = False,
        disable_order: bool = False,
        latency: bool = False,
        demangle: bool | None = None,
        demangle_kernel: bool = False,
        symfs: str | None = None,
        percent_type: str | None = None,
        ns: bool = False,
        time_quantum: str | None = None,
        show_ref_call_graph: bool = False,
        prefix: str | None = None,
        prefix_strip: str | None = None,
        samples: int | None = None,
        parallelism: str | None = None,
        column_widths: str | None = None,
        field_separator: str | None = None,
        parent: str | None = None,
        exclude_other: bool = False,
        show_cpu_utilization: bool = False,
        inverted: bool = False,
        ignore_callees: str | None = None,
        ignore_vmlinux: bool = False,
        show_info: bool = False,
        quiet: bool = False,
        pretty: str | None = None,
        threads: bool = False,
        full_source_path: bool = False,
    ) -> str:
        params = build_params(locals())
        cli_args = options_to_cli_args(REPORT_OPTIONS, params)
        args = ["report", "--stdio"] + cli_args
        result = await executor.run(args, input_path=input)
        return format_result(result)

    enrich_tool_schema(mcp, "perf_report", REPORT_OPTIONS)
