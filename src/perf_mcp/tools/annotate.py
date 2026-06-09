"""perf annotate -- source and assembly-level annotation.

Shows per-instruction or per-source-line sample percentages for a
specific symbol. Useful for identifying hot loops and cache-unfriendly
code patterns within a function.

Forces --stdio output. Dangerous binary-override options (--objdump,
--addr2line) are excluded.
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

ANNOTATE_OPTIONS = [
    PerfOption("input", "i", "string", "Path to perf.data file"),
    PerfOption("verbose", "v", "incr", "Verbosity level", default=0),
    PerfOption("force", "f", "boolean", "Don't complain, do it"),
    PerfOption("symbol", "s", "string", "Symbol name to annotate"),
    PerfOption("dsos", "d", "string", "Only consider these DSOs"),
    PerfOption("vmlinux", "k", "string", "vmlinux pathname"),
    PerfOption("modules", "m", "boolean", "Load module symbols"),
    PerfOption(
        "source",
        None,
        "boolean",
        "Interleave source code with assembly (default on)",
        negatable=True,
        default=True,
    ),
    PerfOption("asm-raw", None, "boolean", "Display raw encoding of assembly"),
    PerfOption("disassembler-style", "M", "string", "Disassembler style (e.g. 'intel')"),
    PerfOption("cpu", "C", "string", "List of CPUs to filter"),
    PerfOption("symfs", None, "string", "Symbol filesystem root"),
    # --objdump and --addr2line are excluded: they execute arbitrary binaries.
    PerfOption("prefix", None, "string", "Add prefix to source file paths"),
    PerfOption("prefix-strip", None, "string", "Strip first N entries of source file path"),
    PerfOption(
        "demangle", None, "boolean", "Symbol demangling (default on)", negatable=True, default=True
    ),
    PerfOption("demangle-kernel", None, "boolean", "Enable kernel symbol demangling"),
    PerfOption("percent-type", None, "string", "Percent type"),
    PerfOption("group", None, "boolean", "Show event group information"),
    PerfOption("skip-missing", None, "boolean", "Skip symbols that cannot be annotated"),
    PerfOption("ignore-vmlinux", None, "boolean", "Don't load vmlinux even if found"),
    PerfOption("code-with-type", None, "boolean", "Show data type annotation for code"),
    PerfOption("data-type", None, "string", "Name of data type to annotate"),
    PerfOption("dump-raw-trace", "D", "boolean", "Dump raw trace in ASCII"),
    PerfOption("full-paths", None, "boolean", "Display full source file paths"),
    PerfOption("insn-stat", None, "boolean", "Show instruction statistics"),
    PerfOption("itrace", None, "string", "Instruction Tracing options"),
    PerfOption("percent-limit", None, "float", "Don't show entries under this percent"),
    PerfOption("print-line", None, "boolean", "Print source line number"),
    PerfOption("quiet", "q", "boolean", "Do not show any warnings or messages"),
    PerfOption("show-nr-samples", None, "boolean", "Show column with sample count"),
    PerfOption("show-total-period", None, "boolean", "Show column with sum of periods"),
    PerfOption("skip-empty", None, "boolean", "Do not display empty events"),
    PerfOption("type-stat", None, "boolean", "Show type annotation statistics"),
]


def register_tools(mcp: FastMCP, executor: PerfExecutor) -> None:
    @mcp.tool(
        description=(
            "Source/assembly annotation: shows per-line or per-instruction sample percentages inside a specific function.\n"
            "\n"
            "Use this after perf_report to drill into a hot function and see exactly which lines or instructions are consuming time.\n"
            "\n"
            "Key parameters:\n"
            "- symbol: function name to annotate (default: hottest symbol).\n"
            "- dsos: restrict to a specific binary/library.\n"
            "- source: true (default) to interleave source code with assembly.\n"
            "- disassembler_style: 'intel' for Intel syntax (default: AT&T).\n"
            "- percent_type: 'local-period' (default), 'global-period', 'local-hits', 'global-hits'.\n"
            "- data_type: annotate a specific data type (DWARF data-type profiling).\n"
            "- code_with_type: show data type annotations on code.\n"
            "\n"
            "Output: source/assembly listing with % annotations per line.\n"
            "Requires: debuginfo packages for source interleaving. Works on any perf.data from perf record."
        ),
    )
    async def perf_annotate(
        input: str,
        verbose: int = 0,
        force: bool = False,
        symbol: str | None = None,
        dsos: str | None = None,
        vmlinux: str | None = None,
        modules: bool = False,
        source: bool | None = None,
        asm_raw: bool = False,
        disassembler_style: str | None = None,
        cpu: str | None = None,
        symfs: str | None = None,
        prefix: str | None = None,
        prefix_strip: str | None = None,
        demangle: bool | None = None,
        demangle_kernel: bool = False,
        percent_type: str | None = None,
        group: bool = False,
        skip_missing: bool = False,
        ignore_vmlinux: bool = False,
        code_with_type: bool = False,
        data_type: str | None = None,
        dump_raw_trace: bool = False,
        full_paths: bool = False,
        insn_stat: bool = False,
        itrace: str | None = None,
        percent_limit: float | None = None,
        print_line: bool = False,
        quiet: bool = False,
        show_nr_samples: bool = False,
        show_total_period: bool = False,
        skip_empty: bool = False,
        type_stat: bool = False,
    ) -> str:
        params = build_params(locals())

        cli_args = options_to_cli_args(ANNOTATE_OPTIONS, params)
        args = ["annotate", "--stdio"] + cli_args
        result = await executor.run(args, input_path=input)
        return format_result(result)

    enrich_tool_schema(mcp, "perf_annotate", ANNOTATE_OPTIONS)
